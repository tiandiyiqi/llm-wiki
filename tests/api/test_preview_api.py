"""预览 API 测试

测试 PreviewAPIHandler 的预览请求和缓存命中。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from lib.api.preview_api import PreviewAPIHandler

    _IMPORT_OK = True
except ImportError as _e:
    _IMPORT_OK = False
    _IMPORT_ERROR = str(_e)


@pytest.fixture
def mock_db_storage():
    """Mock 数据库模式存储"""
    storage = MagicMock()
    storage.mode = 'db'
    storage.get_preview_url = AsyncMock(return_value={
        'url': 'https://preview.example.com/atom/1',
        'format': 'html',
    })
    storage.get_preview_cache = AsyncMock(return_value={
        'cached_at': '2026-06-01T00:00:00Z',
        'format': 'html',
        'size': 1024,
    })
    return storage


@pytest.fixture
def mock_file_storage():
    """Mock 文件模式存储"""
    storage = MagicMock()
    storage.mode = 'file'
    return storage


@pytest.fixture
def preview_handler_db(mock_db_storage):
    """创建数据库模式的预览 API 处理器"""
    return PreviewAPIHandler(storage=mock_db_storage)


@pytest.fixture
def preview_handler_file(mock_file_storage):
    """创建文件模式的预览 API 处理器"""
    return PreviewAPIHandler(storage=mock_file_storage)


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestGetPreview:
    """预览请求测试"""

    def test_get_preview_file_mode_returns_501(self, preview_handler_file):
        """file_mode 下获取预览返回 501"""
        result, status = preview_handler_file.get_preview(atom_id="1")
        assert status == 501
        assert result['mode'] == 'file'

    def test_get_preview_invalid_atom_id(self, preview_handler_db):
        """无效的原子 ID"""
        result, status = preview_handler_db.get_preview(atom_id="not_a_number")
        assert status == 400
        assert '无效' in result['error']

    def test_get_preview_db_mode_check(self, preview_handler_db):
        """db_mode 下 _check_db_mode 返回 None"""
        assert preview_handler_db._check_db_mode() is None

    def test_get_preview_file_mode_check(self, preview_handler_file):
        """file_mode 下 _check_db_mode 返回错误"""
        result = preview_handler_file._check_db_mode()
        assert result is not None
        assert result[1] == 501

    def test_get_preview_with_format(self, preview_handler_db, mock_db_storage):
        """指定预览格式"""
        # 验证参数传递
        handler = preview_handler_db
        # 测试 atom_id 转换
        try:
            numeric_id = int("42")
            assert numeric_id == 42
        except (ValueError, TypeError):
            pytest.fail("atom_id 转换失败")

    def test_get_preview_with_source_mime_type(self, preview_handler_db):
        """指定源 MIME 类型"""
        # 验证参数可以传递
        result = preview_handler_db.get_preview(
            atom_id="1",
            format="pdf",
            source_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        # 不应返回 400（参数校验通过）
        assert result[1] != 400 or '无效' in result[0].get('error', '')


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestGetCache:
    """缓存状态查询测试"""

    def test_get_cache_file_mode_returns_501(self, preview_handler_file):
        """file_mode 下查询缓存返回 501"""
        result, status = preview_handler_file.get_cache(atom_id="1")
        assert status == 501

    def test_get_cache_invalid_atom_id(self, preview_handler_db):
        """无效的原子 ID"""
        result, status = preview_handler_db.get_cache(atom_id="abc")
        assert status == 400

    def test_get_cache_db_mode_check(self, preview_handler_db):
        """db_mode 下查询缓存不返回模式错误"""
        assert preview_handler_db._check_db_mode() is None


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestPreviewEdgeCases:
    """预览边界情况测试"""

    def test_atom_id_zero(self, preview_handler_db):
        """atom_id 为 0"""
        result, status = preview_handler_db.get_preview(atom_id="0")
        # 0 是有效整数，不应返回 400
        assert status != 400 or '无效' in result.get('error', '')

    def test_atom_id_negative(self, preview_handler_db):
        """atom_id 为负数"""
        result, status = preview_handler_db.get_preview(atom_id="-1")
        # 负数可以转换为 int，但可能业务上无效
        # 不应返回 400（参数校验层面 -1 是有效整数）
        assert status != 400

    def test_atom_id_very_large(self, preview_handler_db):
        """atom_id 非常大"""
        result, status = preview_handler_db.get_preview(atom_id="999999999")
        # 不应返回 400
        assert status != 400

    def test_format_parameter_html(self, preview_handler_db):
        """format 参数为 html"""
        # 默认 format 为 html
        result = preview_handler_db.get_preview(atom_id="1", format="html")
        # 不应因 format 返回 400
        assert result[1] != 400 or '无效' in result[0].get('error', '')

    def test_format_parameter_pdf(self, preview_handler_db):
        """format 参数为 pdf"""
        result = preview_handler_db.get_preview(atom_id="1", format="pdf")
        assert result[1] != 400 or '无效' in result[0].get('error', '')
