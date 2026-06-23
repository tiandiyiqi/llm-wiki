"""搜索引擎抽象基类测试

测试 SearchEngine 的数据结构、SearchResult 和 SearchFilters。
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    from lib.search.engine import SearchEngine, SearchResult, SearchFilters

    _IMPORT_OK = True
except ImportError as _e:
    _IMPORT_OK = False
    _IMPORT_ERROR = str(_e)


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestSearchResult:
    """SearchResult 数据结构测试"""

    def test_search_result_creation(self):
        """创建 SearchResult"""
        result = SearchResult(
            atom_id=1,
            slug="test-atom",
            title="测试原子",
            content="内容",
            score=0.95,
        )
        assert result.atom_id == 1
        assert result.slug == "test-atom"
        assert result.title == "测试原子"
        assert result.score == 0.95
        assert result.match_type == 'fulltext'

    def test_search_result_with_highlights(self):
        """SearchResult 包含高亮片段"""
        result = SearchResult(
            atom_id=1,
            slug="test",
            title="标题",
            content="内容",
            score=0.8,
            highlights=["<mark>高亮</mark>片段"],
        )
        assert len(result.highlights) == 1
        assert '<mark>' in result.highlights[0]

    def test_search_result_to_dict(self):
        """SearchResult 转换为字典"""
        result = SearchResult(
            atom_id=1,
            slug="test",
            title="标题",
            content="内容",
            score=0.9,
            kb_id=5,
            atom_type="fact",
        )
        d = result.to_dict()
        assert d['atom_id'] == 1
        assert d['kb_id'] == 5
        assert d['atom_type'] == "fact"
        assert d['match_type'] == 'fulltext'

    def test_search_result_to_dict_with_datetime(self):
        """SearchResult 包含日期时间时转换为字典"""
        now = datetime.now()
        result = SearchResult(
            atom_id=1,
            slug="test",
            title="标题",
            content="内容",
            score=0.9,
            created_at=now,
        )
        d = result.to_dict()
        assert d['created_at'] == now.isoformat()

    def test_search_result_default_values(self):
        """SearchResult 默认值"""
        result = SearchResult(
            atom_id=1,
            slug="test",
            title="标题",
            content="内容",
            score=0.5,
        )
        assert result.highlights == []
        assert result.metadata == {}
        assert result.kb_id is None
        assert result.kb_name is None
        assert result.atom_type is None
        assert result.match_type == 'fulltext'


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestSearchFilters:
    """SearchFilters 数据结构测试"""

    def test_search_filters_default_values(self):
        """SearchFilters 默认值"""
        filters = SearchFilters()
        assert filters.kb_id is None
        assert filters.atom_type is None
        assert filters.tags is None
        assert filters.author_id is None
        assert filters.status is None

    def test_search_filters_with_values(self):
        """SearchFilters 设置值"""
        filters = SearchFilters(
            kb_id=1,
            atom_type="fact",
            tags=["python", "test"],
            author_id="user1",
        )
        assert filters.kb_id == 1
        assert filters.atom_type == "fact"
        assert filters.tags == ["python", "test"]

    def test_search_filters_to_dict(self):
        """SearchFilters 转换为字典"""
        filters = SearchFilters(
            kb_id=1,
            atom_type="method",
            tags=["test"],
        )
        d = filters.to_dict()
        assert d['kb_id'] == 1
        assert d['type'] == "method"
        assert d['tags'] == ["test"]

    def test_search_filters_to_dict_empty(self):
        """空 SearchFilters 转换为空字典"""
        filters = SearchFilters()
        d = filters.to_dict()
        assert d == {}

    def test_search_filters_to_dict_with_dates(self):
        """SearchFilters 包含日期范围"""
        now = datetime.now()
        filters = SearchFilters(
            date_from=now,
            date_to=now,
        )
        d = filters.to_dict()
        assert 'date_from' in d
        assert 'date_to' in d

    def test_search_filters_min_confidence(self):
        """SearchFilters 包含最小置信度"""
        filters = SearchFilters(min_confidence=0.8)
        d = filters.to_dict()
        assert d['min_confidence'] == 0.8


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestSearchEngineABC:
    """SearchEngine 抽象基类测试"""

    def test_search_engine_is_abstract(self):
        """SearchEngine 是抽象类，不能直接实例化"""
        with pytest.raises(TypeError):
            SearchEngine()

    def test_search_engine_abstract_methods(self):
        """SearchEngine 定义了必要的抽象方法"""
        abstract_methods = SearchEngine.__abstractmethods__
        assert 'search' in abstract_methods
        assert 'search_by_embedding' in abstract_methods
        assert 'hybrid_search' in abstract_methods
        assert 'suggest' in abstract_methods
        assert 'get_search_stats' in abstract_methods

    def test_search_engine_concrete_implementation(self):
        """具体实现类可以实例化"""
        class ConcreteSearchEngine(SearchEngine):
            async def search(self, query, kb_id=None, filters=None, limit=50, offset=0):
                return []
            async def search_by_embedding(self, embedding, kb_id=None, filters=None, limit=50):
                return []
            async def hybrid_search(self, query, embedding, kb_id=None, filters=None, text_weight=0.5, vector_weight=0.5, limit=50):
                return []
            async def suggest(self, prefix, kb_id=None, limit=5):
                return []
            async def get_search_stats(self, kb_id=None):
                return {}

        engine = ConcreteSearchEngine()
        assert isinstance(engine, SearchEngine)

    @pytest.mark.asyncio
    async def test_search_engine_default_explain(self):
        """默认 explain_search 实现"""
        class ConcreteSearchEngine(SearchEngine):
            async def search(self, query, kb_id=None, filters=None, limit=50, offset=0):
                return []
            async def search_by_embedding(self, embedding, kb_id=None, filters=None, limit=50):
                return []
            async def hybrid_search(self, query, embedding, kb_id=None, filters=None, text_weight=0.5, vector_weight=0.5, limit=50):
                return []
            async def suggest(self, prefix, kb_id=None, limit=5):
                return []
            async def get_search_stats(self, kb_id=None):
                return {}

        engine = ConcreteSearchEngine()
        result = await engine.explain_search("test query", kb_id=1)
        assert result['query'] == "test query"
        assert result['kb_id'] == 1
