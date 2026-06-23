"""PostgreSQL 搜索引擎测试

测试 PostgreSQLSearchEngine 的全文搜索、tsquery 构建和缓存。
"""

import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from lib.search.postgres_search import PostgreSQLSearchEngine
    from lib.search.engine import SearchResult, SearchFilters

    _IMPORT_OK = True
except ImportError as _e:
    _IMPORT_OK = False
    _IMPORT_ERROR = str(_e)


@pytest.fixture
def mock_pool():
    """Mock asyncpg 连接池"""
    pool = AsyncMock()
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)

    # pool.acquire 返回异步上下文管理器
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=cm)

    return pool, conn


@pytest.fixture
def pg_engine(mock_pool):
    """创建 PostgreSQLSearchEngine 实例"""
    pool, _ = mock_pool
    return PostgreSQLSearchEngine(pool=pool, cache_ttl=300)


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestPostgreSQLSearchEngineInit:
    """搜索引擎初始化测试"""

    def test_init_with_defaults(self, mock_pool):
        """默认参数初始化"""
        pool, _ = mock_pool
        engine = PostgreSQLSearchEngine(pool=pool)
        assert engine.cache_ttl == 300
        assert engine.use_chinese_parser is False
        assert engine._cache == {}

    def test_init_with_custom_params(self, mock_pool):
        """自定义参数初始化"""
        pool, _ = mock_pool
        engine = PostgreSQLSearchEngine(
            pool=pool,
            cache_ttl=600,
            use_chinese_parser=True,
        )
        assert engine.cache_ttl == 600
        assert engine.use_chinese_parser is True


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestBuildTsquery:
    """tsquery 构建测试"""

    def test_build_tsquery_normal(self, pg_engine):
        """正常查询字符串"""
        result = pg_engine._build_tsquery("python tutorial")
        assert result == "python tutorial"

    def test_build_tsquery_strip(self, pg_engine):
        """去除首尾空格"""
        result = pg_engine._build_tsquery("  python  ")
        assert result == "python"

    def test_build_tsquery_empty(self, pg_engine):
        """空查询抛出异常"""
        with pytest.raises(ValueError, match="不能为空"):
            pg_engine._build_tsquery("")

    def test_build_tsquery_whitespace_only(self, pg_engine):
        """仅空格查询抛出异常"""
        with pytest.raises(ValueError, match="不能为空"):
            pg_engine._build_tsquery("   ")


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestContainsChinese:
    """中文检测测试"""

    def test_contains_chinese_true(self, pg_engine):
        """包含中文"""
        assert pg_engine._contains_chinese("测试") is True

    def test_contains_chinese_false(self, pg_engine):
        """不包含中文"""
        assert pg_engine._contains_chinese("english") is False

    def test_contains_chinese_mixed(self, pg_engine):
        """中英混合"""
        assert pg_engine._contains_chinese("Python教程") is True


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestApplyFilters:
    """过滤条件应用测试"""

    def test_apply_filters_no_filters(self, pg_engine):
        """无过滤条件"""
        sql, params, idx = pg_engine._apply_filters(
            "SELECT * FROM atoms WHERE 1=1",
            [], 2, None, None,
        )
        assert "AND" not in sql or "1=1" in sql

    def test_apply_filters_kb_id(self, pg_engine):
        """知识库 ID 过滤"""
        sql, params, idx = pg_engine._apply_filters(
            "SELECT * FROM atoms WHERE 1=1",
            [], 2, 1, None,
        )
        assert "kb_id" in sql
        assert 1 in params

    def test_apply_filters_atom_type(self, pg_engine):
        """原子类型过滤"""
        filters = SearchFilters(atom_type="fact")
        sql, params, idx = pg_engine._apply_filters(
            "SELECT * FROM atoms WHERE 1=1",
            [], 2, None, filters,
        )
        assert "type" in sql
        assert "fact" in params

    def test_apply_filters_tags(self, pg_engine):
        """标签过滤"""
        filters = SearchFilters(tags=["python", "test"])
        sql, params, idx = pg_engine._apply_filters(
            "SELECT * FROM atoms WHERE 1=1",
            [], 2, None, filters,
        )
        assert "tags" in sql

    def test_apply_filters_author(self, pg_engine):
        """作者过滤"""
        filters = SearchFilters(author_id="user1")
        sql, params, idx = pg_engine._apply_filters(
            "SELECT * FROM atoms WHERE 1=1",
            [], 2, None, filters,
        )
        assert "author_id" in sql

    def test_apply_filters_date_range(self, pg_engine):
        """日期范围过滤"""
        now = datetime.now()
        filters = SearchFilters(date_from=now, date_to=now)
        sql, params, idx = pg_engine._apply_filters(
            "SELECT * FROM atoms WHERE 1=1",
            [], 2, None, filters,
        )
        assert "created_at" in sql

    def test_apply_filters_status(self, pg_engine):
        """状态过滤"""
        filters = SearchFilters(status="active")
        sql, params, idx = pg_engine._apply_filters(
            "SELECT * FROM atoms WHERE 1=1",
            [], 2, None, filters,
        )
        assert "status" in sql

    def test_apply_filters_min_confidence(self, pg_engine):
        """最小置信度过滤"""
        filters = SearchFilters(min_confidence=0.8)
        sql, params, idx = pg_engine._apply_filters(
            "SELECT * FROM atoms WHERE 1=1",
            [], 2, None, filters,
        )
        assert "confidence" in sql

    def test_apply_filters_combined(self, pg_engine):
        """组合过滤条件"""
        filters = SearchFilters(
            atom_type="fact",
            author_id="user1",
            status="active",
        )
        sql, params, idx = pg_engine._apply_filters(
            "SELECT * FROM atoms WHERE 1=1",
            [], 2, 1, filters,
        )
        # 应包含多个 AND 条件
        assert sql.count("AND") >= 3


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestCacheManagement:
    """缓存管理测试"""

    def test_cache_key_generation(self, pg_engine):
        """缓存键生成"""
        key = pg_engine._get_cache_key('fulltext', 'python', 1, None, 50, 0)
        assert 'fulltext' in key
        assert 'python' in key

    def test_cache_key_skips_none(self, pg_engine):
        """缓存键跳过 None 值"""
        key = pg_engine._get_cache_key('fulltext', 'python', None, None, 50, 0)
        assert 'None' not in key

    def test_cache_set_and_get(self, pg_engine):
        """缓存设置和获取"""
        results = [_make_result(1, "A", 0.9)]
        pg_engine._set_cache("test_key", results)
        cached = pg_engine._get_from_cache("test_key")
        assert cached is not None
        assert len(cached) == 1

    def test_cache_miss(self, pg_engine):
        """缓存未命中"""
        cached = pg_engine._get_from_cache("nonexistent_key")
        assert cached is None

    def test_cache_expiry(self, pg_engine):
        """缓存过期"""
        pg_engine.cache_ttl = 0  # 立即过期
        results = [_make_result(1, "A", 0.9)]
        pg_engine._set_cache("test_key", results)
        # 手动设置过期时间
        pg_engine._cache["test_key"] = (results, time.monotonic() - 1)
        cached = pg_engine._get_from_cache("test_key")
        assert cached is None

    def test_cache_clear(self, pg_engine):
        """清空缓存"""
        pg_engine._set_cache("key1", [])
        pg_engine._set_cache("key2", [])
        pg_engine.clear_cache()
        assert len(pg_engine._cache) == 0


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestSearchExecution:
    """搜索执行测试"""

    @pytest.mark.asyncio
    async def test_search_empty_query(self, pg_engine):
        """空查询返回空列表"""
        result = await pg_engine.search("")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_whitespace_query(self, pg_engine):
        """仅空格查询返回空列表"""
        result = await pg_engine.search("   ")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_by_embedding_invalid_length(self, pg_engine):
        """无效向量长度返回空列表"""
        result = await pg_engine.search_by_embedding([0.1, 0.2])  # 非 384 维
        assert result == []

    @pytest.mark.asyncio
    async def test_search_by_embedding_empty(self, pg_engine):
        """空向量返回空列表"""
        result = await pg_engine.search_by_embedding([])
        assert result == []

    @pytest.mark.asyncio
    async def test_suggest_short_prefix(self, pg_engine):
        """过短前缀返回空列表"""
        result = await pg_engine.suggest("a")
        assert result == []

    @pytest.mark.asyncio
    async def test_suggest_empty_prefix(self, pg_engine):
        """空前缀返回空列表"""
        result = await pg_engine.suggest("")
        assert result == []


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestRowToResult:
    """数据库行转换测试"""

    def test_row_to_result_fulltext(self, pg_engine):
        """全文搜索行转换"""
        row = {
            'atom_id': 1,
            'slug': 'test-atom',
            'title': '测试',
            'content': '内容',
            'rank': 0.5,
            'metadata': '{}',
            'kb_id': 1,
            'kb_name': 'KB1',
            'atom_type': 'fact',
        }
        result = pg_engine._row_to_result(row, 'fulltext')
        assert result.atom_id == 1
        assert result.title == '测试'
        assert result.match_type == 'fulltext'
        assert result.score == 0.5

    def test_row_to_result_vector(self, pg_engine):
        """向量搜索行转换"""
        row = {
            'atom_id': 2,
            'slug': 'test',
            'title': '标题',
            'content': '内容',
            'similarity': 0.95,
            'metadata': None,
        }
        result = pg_engine._row_to_result(row, 'vector')
        assert result.atom_id == 2
        assert result.match_type == 'vector'
        assert result.score == 0.95

    def test_row_to_result_with_json_metadata(self, pg_engine):
        """JSON 元数据解析"""
        row = {
            'atom_id': 1,
            'slug': 'test',
            'title': '标题',
            'content': '内容',
            'rank': 0.5,
            'metadata': '{"tags": ["python"]}',
        }
        result = pg_engine._row_to_result(row, 'fulltext')
        assert result.metadata == {"tags": ["python"]}

    def test_row_to_result_with_invalid_metadata(self, pg_engine):
        """无效 JSON 元数据回退为空字典"""
        row = {
            'atom_id': 1,
            'slug': 'test',
            'title': '标题',
            'content': '内容',
            'rank': 0.5,
            'metadata': 'not json',
        }
        result = pg_engine._row_to_result(row, 'fulltext')
        assert result.metadata == {}


def _make_result(atom_id, title, score, content="content", match_type="fulltext"):
    """创建测试用 SearchResult"""
    return SearchResult(
        atom_id=atom_id,
        slug=f"slug-{atom_id}",
        title=title,
        content=content,
        score=score,
        match_type=match_type,
    )
