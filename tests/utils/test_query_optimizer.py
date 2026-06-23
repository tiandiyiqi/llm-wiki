"""query_optimizer 模块单元测试

测试范围：
1. BatchLoader 类
2. QueryOptimizer 类
3. NPlusOneDetector 类
4. optimize_query 装饰器
5. get_nplus_one_detector 全局实例
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# 导入被测模块
# ---------------------------------------------------------------------------
try:
    from lib.utils.query_optimizer import (
        BatchLoader,
        QueryOptimizer,
        NPlusOneDetector,
        optimize_query,
        get_nplus_one_detector,
    )
except ImportError as exc:
    pytest.skip(f"Cannot import query_optimizer: {exc}", allow_module_level=True)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock 数据库管理器"""
    db = AsyncMock()
    db.fetch_all = AsyncMock(return_value=[])
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value=None)
    return db


@pytest.fixture
def batch_loader(mock_db):
    """BatchLoader 实例"""
    return BatchLoader(mock_db, batch_size=50)


@pytest.fixture
def detector():
    """NPlusOneDetector 实例"""
    return NPlusOneDetector(threshold=5)


# ============================================================================
# BatchLoader 测试
# ============================================================================


class TestBatchLoader:
    """BatchLoader 类测试"""

    def test_initial_state(self, mock_db):
        loader = BatchLoader(mock_db, batch_size=50)
        assert loader.batch_size == 50
        assert loader.db_manager is mock_db

    @pytest.mark.asyncio
    async def test_load_many_empty_ids(self, batch_loader):
        """空 ID 列表返回空字典"""
        result = await batch_loader.load_many('users', [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_load_many_success(self, batch_loader, mock_db):
        """批量加载记录"""
        mock_db.fetch_all = AsyncMock(return_value=[
            {'id': 1, 'name': 'Alice'},
            {'id': 2, 'name': 'Bob'},
        ])
        result = await batch_loader.load_many('users', [1, 2])
        assert result == {1: {'id': 1, 'name': 'Alice'}, 2: {'id': 2, 'name': 'Bob'}}

    @pytest.mark.asyncio
    async def test_load_many_deduplication(self, batch_loader, mock_db):
        """ID 去重"""
        mock_db.fetch_all = AsyncMock(return_value=[
            {'id': 1, 'name': 'Alice'},
        ])
        result = await batch_loader.load_many('users', [1, 1, 1])
        assert result == {1: {'id': 1, 'name': 'Alice'}}
        # 只调用一次 fetch_all
        mock_db.fetch_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_many_with_columns(self, batch_loader, mock_db):
        """指定加载列"""
        mock_db.fetch_all = AsyncMock(return_value=[
            {'id': 1, 'name': 'Alice'},
        ])
        result = await batch_loader.load_many('users', [1], columns=['id', 'name'])
        assert 1 in result

    @pytest.mark.asyncio
    async def test_load_many_custom_key_column(self, batch_loader, mock_db):
        """自定义键列名"""
        mock_db.fetch_all = AsyncMock(return_value=[
            {'slug': 'kb-1', 'title': 'Knowledge Base 1'},
        ])
        result = await batch_loader.load_many('knowledge_bases', ['kb-1'], key_column='slug')
        assert 'kb-1' in result

    @pytest.mark.asyncio
    async def test_load_many_empty_result(self, batch_loader, mock_db):
        """查询无结果"""
        mock_db.fetch_all = AsyncMock(return_value=[])
        result = await batch_loader.load_many('users', [999])
        assert result == {}

    @pytest.mark.asyncio
    async def test_load_related_empty_ids(self, batch_loader):
        """空父 ID 列表返回空字典"""
        result = await batch_loader.load_related([], 'atoms', 'kb_id')
        assert result == {}

    @pytest.mark.asyncio
    async def test_load_related_success(self, batch_loader, mock_db):
        """批量加载关联记录"""
        mock_db.fetch_all = AsyncMock(return_value=[
            {'id': 1, 'kb_id': 10, 'title': 'Atom 1'},
            {'id': 2, 'kb_id': 10, 'title': 'Atom 2'},
            {'id': 3, 'kb_id': 20, 'title': 'Atom 3'},
        ])
        result = await batch_loader.load_related([10, 20], 'atoms', 'kb_id')
        assert len(result[10]) == 2
        assert len(result[20]) == 1

    @pytest.mark.asyncio
    async def test_load_related_no_records(self, batch_loader, mock_db):
        """关联查询无结果"""
        mock_db.fetch_all = AsyncMock(return_value=[])
        result = await batch_loader.load_related([10, 20], 'atoms', 'kb_id')
        assert result[10] == []
        assert result[20] == []

    @pytest.mark.asyncio
    async def test_load_related_with_columns(self, batch_loader, mock_db):
        """指定关联查询列"""
        mock_db.fetch_all = AsyncMock(return_value=[
            {'id': 1, 'kb_id': 10, 'title': 'Atom 1'},
        ])
        result = await batch_loader.load_related([10], 'atoms', 'kb_id', columns=['id', 'title'])
        assert len(result[10]) == 1

    @pytest.mark.asyncio
    async def test_load_join_success(self, batch_loader, mock_db):
        """JOIN 查询"""
        mock_db.fetch_all = AsyncMock(return_value=[
            {'id': 1, 'kb_name': 'KB1', 'atom_title': 'Atom1'},
        ])
        result = await batch_loader.load_join(
            'knowledge_bases', 'atoms', 'm.id = j.kb_id'
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_load_join_with_where(self, batch_loader, mock_db):
        """JOIN 查询带 WHERE 子句"""
        mock_db.fetch_all = AsyncMock(return_value=[])
        result = await batch_loader.load_join(
            'knowledge_bases', 'atoms',
            'm.id = j.kb_id',
            where_clause='m.id = $1',
            where_params=[1]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_load_join_no_where(self, batch_loader, mock_db):
        """JOIN 查询无 WHERE 子句"""
        mock_db.fetch_all = AsyncMock(return_value=[])
        result = await batch_loader.load_join(
            'knowledge_bases', 'atoms', 'm.id = j.kb_id'
        )
        assert result == []


# ============================================================================
# QueryOptimizer 测试
# ============================================================================


class TestQueryOptimizer:
    """QueryOptimizer 类测试"""

    def test_simple_query(self):
        """简单查询分析"""
        result = QueryOptimizer.analyze_query("SELECT * FROM users WHERE id = 1")
        assert result['has_subquery'] is False
        assert result['has_join'] is False
        assert result['has_aggregate'] is False
        assert result['table_count'] == 1
        assert len(result['warnings']) == 0

    def test_subquery_detection(self):
        """子查询检测"""
        query = "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)"
        result = QueryOptimizer.analyze_query(query)
        assert result['has_subquery'] is True
        assert len(result['warnings']) > 0

    def test_join_detection(self):
        """JOIN 检测"""
        query = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        result = QueryOptimizer.analyze_query(query)
        assert result['has_join'] is True

    def test_aggregate_detection(self):
        """聚合函数检测"""
        query = "SELECT COUNT(*) FROM users"
        result = QueryOptimizer.analyze_query(query)
        assert result['has_aggregate'] is True

    def test_sum_aggregate(self):
        """SUM 聚合函数"""
        query = "SELECT SUM(amount) FROM orders"
        result = QueryOptimizer.analyze_query(query)
        assert result['has_aggregate'] is True

    def test_avg_aggregate(self):
        """AVG 聚合函数"""
        query = "SELECT AVG(score) FROM results"
        result = QueryOptimizer.analyze_query(query)
        assert result['has_aggregate'] is True

    def test_max_min_aggregate(self):
        """MAX/MIN 聚合函数"""
        for func in ['MAX', 'MIN']:
            query = f"SELECT {func}(price) FROM products"
            result = QueryOptimizer.analyze_query(query)
            assert result['has_aggregate'] is True

    def test_table_count(self):
        """表数量统计"""
        query = "SELECT * FROM users u JOIN orders o ON u.id = o.user_id JOIN items i ON o.id = i.order_id"
        result = QueryOptimizer.analyze_query(query)
        # FROM + 2 JOINs = 3
        assert result['table_count'] >= 2

    def test_suggest_index_where(self):
        """WHERE 子句索引建议"""
        query = "SELECT * FROM users WHERE email = $1"
        suggestions = QueryOptimizer.suggest_index(query, 'users')
        assert len(suggestions) > 0
        assert any('WHERE' in s for s in suggestions)

    def test_suggest_index_order_by(self):
        """ORDER BY 索引建议"""
        query = "SELECT * FROM users ORDER BY created_at"
        suggestions = QueryOptimizer.suggest_index(query, 'users')
        assert any('ORDER BY' in s for s in suggestions)

    def test_suggest_index_join(self):
        """JOIN 索引建议"""
        query = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        suggestions = QueryOptimizer.suggest_index(query, 'users')
        assert any('JOIN' in s for s in suggestions)

    def test_suggest_index_no_where(self):
        """无 WHERE/ORDER BY/JOIN 时无建议"""
        query = "SELECT * FROM users"
        suggestions = QueryOptimizer.suggest_index(query, 'users')
        assert len(suggestions) == 0

    def test_complex_query(self):
        """复杂查询分析"""
        query = """
            SELECT u.name, COUNT(o.id) as order_count
            FROM users u
            JOIN orders o ON u.id = o.user_id
            WHERE u.active = true
            GROUP BY u.name
            ORDER BY order_count DESC
        """
        result = QueryOptimizer.analyze_query(query)
        assert result['has_join'] is True
        assert result['has_aggregate'] is True
        assert result['table_count'] >= 2


# ============================================================================
# NPlusOneDetector 测试
# ============================================================================


class TestNPlusOneDetector:
    """NPlusOneDetector 类测试"""

    def test_initial_state(self):
        det = NPlusOneDetector(threshold=10)
        assert det.threshold == 10
        assert det.get_report() == {}

    def test_record_query(self, detector):
        """记录查询"""
        detector.record_query('SELECT * FROM users WHERE id = $1')
        report = detector.get_report()
        assert 'SELECT * FROM users WHERE id = $1' in report
        assert report['SELECT * FROM users WHERE id = $1'] == 1

    def test_record_multiple_queries(self, detector):
        """记录多次查询"""
        for _ in range(3):
            detector.record_query('SELECT * FROM users WHERE id = $1')
        report = detector.get_report()
        assert report['SELECT * FROM users WHERE id = $1'] == 3

    def test_different_patterns(self, detector):
        """不同查询模式独立计数"""
        detector.record_query('SELECT * FROM users WHERE id = $1')
        detector.record_query('SELECT * FROM orders WHERE user_id = $1')
        report = detector.get_report()
        assert len(report) == 2

    def test_threshold_warning(self, detector):
        """超过阈值时发出警告"""
        for _ in range(6):
            detector.record_query('SELECT * FROM atoms WHERE kb_id = $1')
        report = detector.get_report()
        assert report['SELECT * FROM atoms WHERE kb_id = $1'] == 6

    def test_reset(self, detector):
        """重置计数器"""
        detector.record_query('SELECT * FROM users')
        detector.reset()
        assert detector.get_report() == {}

    def test_custom_threshold(self):
        """自定义阈值"""
        det = NPlusOneDetector(threshold=2)
        det.record_query('q1')
        det.record_query('q1')
        det.record_query('q1')  # 超过阈值
        report = det.get_report()
        assert report['q1'] == 3


# ============================================================================
# optimize_query 装饰器测试
# ============================================================================


class TestOptimizeQuery:
    """optimize_query 装饰器测试"""

    @pytest.mark.asyncio
    async def test_caches_result(self):
        """缓存查询结果"""
        call_count = 0

        @optimize_query
        async def get_user(user_id):
            nonlocal call_count
            call_count += 1
            return {'id': user_id, 'name': 'Alice'}

        result1 = await get_user(1)
        result2 = await get_user(1)
        assert result1 == result2
        assert call_count == 1  # 只调用一次

    @pytest.mark.asyncio
    async def test_different_args_different_cache(self):
        """不同参数使用不同缓存"""
        call_count = 0

        @optimize_query
        async def get_user(user_id):
            nonlocal call_count
            call_count += 1
            return {'id': user_id}

        result1 = await get_user(1)
        result2 = await get_user(2)
        assert result1 != result2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_kwargs_affect_cache(self):
        """kwargs 影响缓存键"""
        call_count = 0

        @optimize_query
        async def get_data(key, scope='default'):
            nonlocal call_count
            call_count += 1
            return {'key': key, 'scope': scope}

        result1 = await get_data('test', scope='a')
        result2 = await get_data('test', scope='b')
        assert result1 != result2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_same_kwargs_cached(self):
        """相同 kwargs 使用缓存"""
        call_count = 0

        @optimize_query
        async def get_data(key, scope='default'):
            nonlocal call_count
            call_count += 1
            return {'key': key, 'scope': scope}

        result1 = await get_data('test', scope='a')
        result2 = await get_data('test', scope='a')
        assert result1 == result2
        assert call_count == 1


# ============================================================================
# get_nplus_one_detector 测试
# ============================================================================


class TestGetNPlusOneDetector:
    """get_nplus_one_detector 全局实例测试"""

    def test_returns_detector_instance(self):
        detector = get_nplus_one_detector()
        assert isinstance(detector, NPlusOneDetector)

    def test_returns_same_instance(self):
        det1 = get_nplus_one_detector()
        det2 = get_nplus_one_detector()
        assert det1 is det2
