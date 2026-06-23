"""迁移数据验证器测试

测试 MigrationValidator 的数据验证和 Schema 兼容性。
"""

import json
import math
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    from lib.migration.validators import MigrationValidator, ValidationResult

    _IMPORT_OK = True
except ImportError as _e:
    _IMPORT_OK = False
    _IMPORT_ERROR = str(_e)


@pytest.fixture
def mock_db():
    """Mock 数据库管理器"""
    db = AsyncMock()
    db.get_atom_count = AsyncMock(return_value=10)
    db.get_kb_stats = AsyncMock(return_value={'types_count': {'fact': 5, 'method': 5}})
    db.list_atoms = AsyncMock(return_value=[])
    db.search_atoms = AsyncMock(return_value=[])

    # Mock pool
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={'count': 5})
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    db.pool = MagicMock()
    db.pool.acquire = MagicMock(return_value=cm)

    return db


@pytest.fixture
def kb_path(tmp_path):
    """创建临时知识库目录"""
    kb = tmp_path / "test_kb"
    kb.mkdir()
    (kb / "atoms").mkdir()
    return kb


@pytest.fixture
def validator(mock_db, kb_path):
    """创建验证器实例"""
    return MigrationValidator(db_manager=mock_db, kb_path=kb_path)


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestValidationResult:
    """验证结果测试"""

    def test_validation_result_defaults(self):
        """ValidationResult 默认值"""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.details == {}

    def test_validation_result_with_errors(self):
        """ValidationResult 包含错误"""
        result = ValidationResult(
            valid=False,
            errors=["错误1"],
            warnings=["警告1"],
        )
        assert result.valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_validation_result_str(self):
        """ValidationResult 字符串表示"""
        result = ValidationResult(valid=True, details={'checked': 10})
        s = str(result)
        assert "通过" in s

    def test_validation_result_str_with_errors(self):
        """ValidationResult 包含错误时的字符串表示"""
        result = ValidationResult(valid=False, errors=["错误1"])
        s = str(result)
        assert "失败" in s


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestValidateCounts:
    """记录数验证测试"""

    def test_counts_match(self, validator):
        """记录数一致"""
        source = {'atoms': 10, 'links': 5}
        target = {'atoms': 10, 'links': 5}
        result = validator.validate_counts(source, target)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_counts_mismatch(self, validator):
        """记录数不一致"""
        source = {'atoms': 10, 'links': 5}
        target = {'atoms': 8, 'links': 5}
        result = validator.validate_counts(source, target)

        assert result.valid is False
        assert len(result.errors) > 0

    def test_counts_missing_key_in_target(self, validator):
        """目标缺少键"""
        source = {'atoms': 10, 'links': 5}
        target = {'atoms': 10}
        result = validator.validate_counts(source, target)

        assert result.valid is False

    def test_counts_extra_key_in_target(self, validator):
        """目标多出键"""
        source = {'atoms': 10}
        target = {'atoms': 10, 'extra': 5}
        result = validator.validate_counts(source, target)

        assert result.valid is False

    def test_counts_empty(self, validator):
        """空统计"""
        result = validator.validate_counts({}, {})
        assert result.valid is True


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestValidateContent:
    """内容一致性验证测试"""

    @pytest.mark.asyncio
    async def test_content_match(self, validator):
        """内容一致"""
        source = [{'path': 'a.md', 'title': 'A', 'type': 'fact'}]
        target = [{'path': 'a.md', 'title': 'A', 'type': 'fact'}]
        result = await validator.validate_content(source, target)

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_content_title_mismatch(self, validator):
        """标题不匹配"""
        source = [{'path': 'a.md', 'title': 'A', 'type': 'fact'}]
        target = [{'path': 'a.md', 'title': 'B', 'type': 'fact'}]
        result = await validator.validate_content(source, target)

        assert result.valid is False
        assert any('标题' in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_content_missing_in_target(self, validator):
        """目标缺少原子"""
        source = [{'path': 'a.md', 'title': 'A', 'type': 'fact'}]
        target = []
        result = await validator.validate_content(source, target)

        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_content_extra_in_target(self, validator):
        """目标多出原子"""
        source = []
        target = [{'path': 'b.md', 'title': 'B', 'type': 'method'}]
        result = await validator.validate_content(source, target)

        assert len(result.warnings) > 0


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestValidateLinks:
    """链接关系验证测试"""

    @pytest.mark.asyncio
    async def test_links_match(self, validator):
        """链接一致"""
        source = [{'source_id': 1, 'target_id': 2, 'link_type': 'reference'}]
        target = [{'source_id': 1, 'target_id': 2, 'link_type': 'reference'}]
        result = await validator.validate_links(source, target)

        assert result.details['match_rate'] == 100.0

    @pytest.mark.asyncio
    async def test_links_missing(self, validator):
        """目标缺少链接"""
        source = [
            {'source_id': 1, 'target_id': 2, 'link_type': 'reference'},
            {'source_id': 2, 'target_id': 3, 'link_type': 'reference'},
        ]
        target = [
            {'source_id': 1, 'target_id': 2, 'link_type': 'reference'},
        ]
        result = await validator.validate_links(source, target)

        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_links_empty(self, validator):
        """空链接列表"""
        result = await validator.validate_links([], [])
        assert result.valid is True
        assert result.details['match_rate'] == 0.0


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestValidateSearch:
    """搜索功能验证测试"""

    @pytest.mark.asyncio
    async def test_search_with_results(self, validator, mock_db):
        """搜索有结果"""
        mock_db.search_atoms = AsyncMock(return_value=[
            {'title': '安装指南', 'score': 0.9},
        ])
        result = await validator.validate_search(1, ['安装'])

        assert result.valid is True
        assert result.details['queries'] == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, validator, mock_db):
        """搜索无结果"""
        mock_db.search_atoms = AsyncMock(return_value=[])
        result = await validator.validate_search(1, ['不存在的查询'])

        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_search_failure(self, validator, mock_db):
        """搜索失败"""
        mock_db.search_atoms = AsyncMock(side_effect=Exception("DB error"))
        result = await validator.validate_search(1, ['test'])

        assert result.valid is False
        assert len(result.errors) > 0


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestCompareEmbeddings:
    """向量嵌入比较测试"""

    def test_identical_embeddings(self, validator):
        """完全相同的向量"""
        source = [{'id': '1', 'embedding': [1.0, 0.0, 0.0]}]
        target = [{'id': '1', 'embedding': [1.0, 0.0, 0.0]}]
        result = validator.compare_embeddings(source, target)

        assert result.valid is True

    def test_different_count(self, validator):
        """向量数量不一致"""
        source = [{'id': '1', 'embedding': [1.0, 0.0]}]
        target = []
        result = validator.compare_embeddings(source, target)

        assert len(result.warnings) > 0

    def test_empty_embeddings(self, validator):
        """空向量列表"""
        result = validator.compare_embeddings([], [])
        assert result.valid is True


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestCosineSimilarity:
    """余弦相似度测试"""

    def test_identical_vectors(self, validator):
        """完全相同的向量"""
        sim = validator._cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert abs(sim - 1.0) < 0.001

    def test_orthogonal_vectors(self, validator):
        """正交向量"""
        sim = validator._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(sim) < 0.001

    def test_opposite_vectors(self, validator):
        """相反向量"""
        sim = validator._cosine_similarity([1.0, 0.0], [-1.0, 0.0])
        assert abs(sim - (-1.0)) < 0.001

    def test_different_dimensions(self, validator):
        """不同维度返回 0"""
        sim = validator._cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])
        assert sim == 0.0

    def test_zero_vector(self, validator):
        """零向量返回 0"""
        sim = validator._cosine_similarity([0.0, 0.0], [1.0, 0.0])
        assert sim == 0.0


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestGetSourceStats:
    """源数据统计测试"""

    @pytest.mark.asyncio
    async def test_empty_kb(self, validator, kb_path):
        """空知识库统计"""
        stats = await validator._get_source_stats()
        assert stats['atoms'] == 0
        assert stats['links'] == 0

    @pytest.mark.asyncio
    async def test_kb_with_atoms(self, validator, kb_path):
        """有原子的知识库统计"""
        atoms_dir = kb_path / "atoms"
        (atoms_dir / "fact-1.md").write_text(
            "---\ntitle: 事实\ntype: fact\n---\n\n内容 [[method-1]]",
            encoding='utf-8',
        )
        stats = await validator._get_source_stats()
        assert stats['atoms'] == 1
        assert stats['links'] == 1  # 一个 wikilink
