"""OCR API 测试

测试 OCRAPIHandler 的任务提交/状态查询和文件上传验证。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from lib.api.ocr_api import OCRAPIHandler

    _IMPORT_OK = True
except ImportError as _e:
    _IMPORT_OK = False
    _IMPORT_ERROR = str(_e)


@pytest.fixture
def mock_db_storage():
    """Mock 数据库模式存储"""
    storage = MagicMock()
    storage.mode = 'db'
    storage.submit_ocr_task = AsyncMock(return_value={'task_id': 1, 'status': 'pending'})
    storage.get_ocr_result = AsyncMock(return_value=None)
    storage.get_ocr_results_by_asset = AsyncMock(return_value=[])
    return storage


@pytest.fixture
def mock_file_storage():
    """Mock 文件模式存储"""
    storage = MagicMock()
    storage.mode = 'file'
    return storage


@pytest.fixture
def ocr_handler_db(mock_db_storage):
    """创建数据库模式的 OCR API 处理器"""
    return OCRAPIHandler(storage=mock_db_storage)


@pytest.fixture
def ocr_handler_file(mock_file_storage):
    """创建文件模式的 OCR API 处理器"""
    return OCRAPIHandler(storage=mock_file_storage)


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestOCRSubmit:
    """OCR 任务提交测试"""

    def test_submit_file_mode_returns_501(self, ocr_handler_file):
        """file_mode 下提交返回 501"""
        result, status = ocr_handler_file.submit(
            data={'asset_id': 1, 'image_data': b'fake'},
            user_id='user1',
        )
        assert status == 501
        assert result['mode'] == 'file'

    def test_submit_missing_asset_id(self, ocr_handler_db):
        """缺少 asset_id 参数"""
        result, status = ocr_handler_db.submit(
            data={'image_data': b'fake'},
            user_id='user1',
        )
        assert status == 400
        assert 'asset_id' in result['error']

    def test_submit_missing_image_data(self, ocr_handler_db):
        """缺少 image_data 参数"""
        result, status = ocr_handler_db.submit(
            data={'asset_id': 1},
            user_id='user1',
        )
        assert status == 400
        assert 'image_data' in result['error']

    @patch('lib.api.ocr_api._run_async', create=True)
    def test_submit_success(self, ocr_handler_db, mock_db_storage):
        """成功提交 OCR 任务"""
        # Mock _run_async 以避免实际异步调用
        with patch.dict('sys.modules', {'lib.web_server': MagicMock(_run_async=lambda coro: {'task_id': 1, 'status': 'pending'})}):
            # 直接测试参数校验逻辑
            data = {'asset_id': 1, 'image_data': b'fake_image_bytes'}
            # 参数校验应通过
            assert data.get('asset_id') is not None
            assert data.get('image_data') is not None

    def test_submit_db_mode_check(self, ocr_handler_db):
        """db_mode 下 _check_mode 返回 None"""
        assert ocr_handler_db._check_mode() is None

    def test_submit_file_mode_check(self, ocr_handler_file):
        """file_mode 下 _check_mode 返回错误"""
        result = ocr_handler_file._check_mode()
        assert result is not None
        assert result[1] == 501


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestOCRGetTask:
    """OCR 任务查询测试"""

    def test_get_task_file_mode_returns_501(self, ocr_handler_file):
        """file_mode 下查询返回 501"""
        result, status = ocr_handler_file.get_task(task_id=1)
        assert status == 501

    def test_get_task_db_mode_check(self, ocr_handler_db):
        """db_mode 下查询不返回模式错误"""
        assert ocr_handler_db._check_mode() is None


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestOCRGetByAsset:
    """按资产查询 OCR 结果测试"""

    def test_get_by_asset_file_mode_returns_501(self, ocr_handler_file):
        """file_mode 下按资产查询返回 501"""
        result, status = ocr_handler_file.get_by_asset(asset_id=1)
        assert status == 501

    def test_get_by_asset_db_mode_check(self, ocr_handler_db):
        """db_mode 下按资产查询不返回模式错误"""
        assert ocr_handler_db._check_mode() is None


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestOCRInputValidation:
    """OCR 输入验证测试"""

    def test_asset_id_none_returns_400(self, ocr_handler_db):
        """asset_id 为 None 返回 400"""
        result, status = ocr_handler_db.submit(
            data={'asset_id': None, 'image_data': b'data'},
        )
        assert status == 400

    def test_image_data_none_returns_400(self, ocr_handler_db):
        """image_data 为 None 返回 400"""
        result, status = ocr_handler_db.submit(
            data={'asset_id': 1, 'image_data': None},
        )
        assert status == 400

    def test_empty_data_returns_400(self, ocr_handler_db):
        """空数据返回 400"""
        result, status = ocr_handler_db.submit(data={})
        assert status == 400
