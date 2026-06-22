"""搜索联想增强测试

测试 SearchSuggester 的各种联想功能：
- 前缀匹配联想
- pg_trgm 模糊匹配联想
- 热门搜索词统计
- 搜索历史记录
- 中英文混合联想
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from lib.search.suggest import (
    SuggestConfig,
    SuggestionResult,
    SuggestionType,
    SearchSuggester,
)


# ============================================================================
# Mock 工厂
# ============================================================================


def _create_mock_pool():
    """创建 Mock asyncpg 连接池"""
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    acquire_cm = MagicMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)
    mock_pool.acquire = MagicMock(return_value=acquire_cm)
    return mock_pool, mock_conn


# ============================================================================
# 测试数据类
# ============================================================================


class TestSuggestConfig:
    """SuggestConfig 数据类测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = SuggestConfig()
        assert config.min_prefix_length == 1
        assert config.similarity_threshold == 0.3
        assert config.popular_days == 30
        assert config.max_history_days == 90
        assert config.prefix_weight == 1.0
        assert config.fuzzy_weight == 0.8
        assert config.popular_weight == 0.5
        assert config.history_weight == 0.7

    def test_custom_config(self):
        """测试自定义配置"""
        config = SuggestConfig(
            similarity_threshold=0.5,
            min_prefix_length=2,
            popular_days=7,
        )
        assert config.similarity_threshold == 0.5
        assert config.min_prefix_length == 2
        assert config.popular_days == 7

    def test_config_is_frozen(self):
        """测试配置不可变性"""
        config = SuggestConfig()
        with pytest.raises(AttributeError):
            config.similarity_threshold = 0.9


class TestSuggestionResult:
    """SuggestionResult 数据类测试"""

    def test_basic_result(self):
        """测试基本联想结果"""
        result = SuggestionResult(
            text='machine learning',
            suggestion_type=SuggestionType.PREFIX,
            score=1.0,
        )
        assert result.text == 'machine learning'
        assert result.suggestion_type == SuggestionType.PREFIX
        assert result.score == 1.0

    def test_result_types(self):
        """测试所有联想类型"""
        for stype in SuggestionType:
            result = SuggestionResult(text='test', suggestion_type=stype, score=0.5)
            assert result.suggestion_type == stype

    def test_result_to_dict(self):
        """测试转换为字典"""
        result = SuggestionResult(
            text='test query',
            suggestion_type=SuggestionType.FUZZY,
            score=0.8,
        )
        d = result.to_dict()
        assert d['text'] == 'test query'
        assert d['suggestion_type'] == 'fuzzy'
        assert d['score'] == 0.8

    def test_result_is_frozen(self):
        """测试结果不可变性"""
        result = SuggestionResult(
            text='test', suggestion_type=SuggestionType.PREFIX, score=1.0,
        )
        with pytest.raises(AttributeError):
            result.text = 'changed'


# ============================================================================
# 测试 SearchSuggester
# ============================================================================


class TestSearchSuggester:
    """SearchSuggester 搜索联想器测试"""

    def setup_method(self):
        """测试前准备"""
        self.suggester = SearchSuggester()
        self.mock_pool, self.mock_conn = _create_mock_pool()

    # ------ 前缀匹配联想 ------

    @pytest.mark.asyncio
    async def test_suggest_by_prefix_basic(self):
        """测试基本前缀匹配"""
        self.mock_conn.fetch = AsyncMock(return_value=[
            {'title': 'Machine Learning Basics'},
            {'title': 'Machine Learning Advanced'},
        ])

        results = await self.suggester.suggest_by_prefix(
            self.mock_pool, 'Machine', kb_id=None, limit=5
        )

        assert len(results) == 2
        assert all(isinstance(r, SuggestionResult) for r in results)
        assert results[0].suggestion_type == SuggestionType.PREFIX

    @pytest.mark.asyncio
    async def test_suggest_by_prefix_empty(self):
        """测试空前缀返回空列表"""
        results = await self.suggester.suggest_by_prefix(
            self.mock_pool, '', kb_id=None, limit=5
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_suggest_by_prefix_with_kb_id(self):
        """测试带知识库 ID 的前缀匹配"""
        self.mock_conn.fetch = AsyncMock(return_value=[
            {'title': 'Test Title'},
        ])

        results = await self.suggester.suggest_by_prefix(
            self.mock_pool, 'Test', kb_id=1, limit=5
        )

        assert len(results) == 1

    # ------ 模糊匹配联想 ------

    @pytest.mark.asyncio
    async def test_suggest_by_fuzzy_basic(self):
        """测试基本模糊匹配"""
        self.mock_conn.fetch = AsyncMock(return_value=[
            {'title': 'Machine Learning', 'sim_score': 0.5},
            {'title': 'Deep Learning', 'sim_score': 0.3},
        ])

        results = await self.suggester.suggest_by_fuzzy(
            self.mock_pool, 'machin', kb_id=None, limit=5,
            similarity_threshold=0.3,
        )

        assert len(results) == 2
        assert all(r.suggestion_type == SuggestionType.FUZZY for r in results)

    @pytest.mark.asyncio
    async def test_suggest_by_fuzzy_empty_prefix(self):
        """测试空前缀模糊匹配返回空"""
        results = await self.suggester.suggest_by_fuzzy(
            self.mock_pool, '', kb_id=None, limit=5,
        )
        assert results == []

    # ------ 热门搜索词 ------

    @pytest.mark.asyncio
    async def test_suggest_popular_basic(self):
        """测试热门搜索词"""
        self.mock_conn.fetch = AsyncMock(return_value=[
            {'query': 'machine learning', 'search_count': 100},
            {'query': 'deep learning', 'search_count': 80},
            {'query': 'neural network', 'search_count': 50},
        ])

        results = await self.suggester.suggest_popular(
            self.mock_pool, kb_id=None, limit=5
        )

        assert len(results) == 3
        assert all(r.suggestion_type == SuggestionType.POPULAR for r in results)

    @pytest.mark.asyncio
    async def test_suggest_popular_with_kb(self):
        """测试带知识库的热门搜索词"""
        self.mock_conn.fetch = AsyncMock(return_value=[
            {'query': 'test query', 'search_count': 10},
        ])

        results = await self.suggester.suggest_popular(
            self.mock_pool, kb_id=1, limit=5
        )

        assert len(results) == 1

    # ------ 搜索历史 ------

    @pytest.mark.asyncio
    async def test_suggest_from_history_basic(self):
        """测试用户搜索历史"""
        from datetime import datetime, timezone
        self.mock_conn.fetch = AsyncMock(return_value=[
            {'query': 'python async', 'last_searched': datetime(2026, 6, 20, tzinfo=timezone.utc)},
            {'query': 'python decorator', 'last_searched': datetime(2026, 6, 19, tzinfo=timezone.utc)},
        ])

        results = await self.suggester.suggest_from_history(
            self.mock_pool, user_id='user1', kb_id=None, limit=5
        )

        assert len(results) == 2
        assert all(r.suggestion_type == SuggestionType.HISTORY for r in results)

    @pytest.mark.asyncio
    async def test_suggest_from_history_no_user(self):
        """测试无用户 ID 时返回空"""
        results = await self.suggester.suggest_from_history(
            self.mock_pool, user_id=None, kb_id=None, limit=5
        )
        assert results == []

    # ------ 记录搜索历史 ------

    @pytest.mark.asyncio
    async def test_record_search_basic(self):
        """测试记录搜索历史"""
        self.mock_conn.execute = AsyncMock(return_value=None)

        result = await self.suggester.record_search(
            self.mock_pool,
            query='machine learning',
            user_id='user1',
            kb_id=1,
            result_count=10,
        )

        assert result is True
        self.mock_conn.execute.assert_called_once()
        call_args = self.mock_conn.execute.call_args[0]
        assert 'search_history' in call_args[0].lower()

    @pytest.mark.asyncio
    async def test_record_search_empty_query(self):
        """测试空查询不记录"""
        result = await self.suggester.record_search(
            self.mock_pool,
            query='',
            user_id='user1',
            kb_id=1,
            result_count=0,
        )
        assert result is False

    # ------ 综合联想 ------

    @pytest.mark.asyncio
    async def test_suggest_comprehensive(self):
        """测试综合联想（合并多种来源）"""
        from datetime import datetime
        self.mock_conn.fetch = AsyncMock(side_effect=[
            # 前缀匹配结果
            [{'title': 'Machine Learning Basics'}],
            # 模糊匹配结果
            [{'title': 'Deep Learning', 'sim_score': 0.4}],
            # 热门搜索词
            [{'query': 'machine learning', 'search_count': 50}],
        ])

        config = SuggestConfig()

        results = await self.suggester.suggest(
            self.mock_pool,
            prefix='machin',
            kb_id=None,
            limit=10,
            config=config,
        )

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_suggest_deduplication(self):
        """测试联想结果去重"""
        self.mock_conn.fetch = AsyncMock(side_effect=[
            [{'title': 'Machine Learning'}],
            [{'title': 'Machine Learning', 'sim_score': 0.5}],
            [],
        ])

        config = SuggestConfig()

        results = await self.suggester.suggest(
            self.mock_pool,
            prefix='Machine',
            kb_id=None,
            limit=10,
            config=config,
        )

        texts = [r.text for r in results]
        assert len(texts) == len(set(texts))

    @pytest.mark.asyncio
    async def test_suggest_chinese_prefix(self):
        """测试中文前缀联想"""
        self.mock_conn.fetch = AsyncMock(return_value=[
            {'title': '机器学习基础'},
            {'title': '机器学习进阶'},
        ])

        results = await self.suggester.suggest_by_prefix(
            self.mock_pool, '机器', kb_id=None, limit=5
        )

        assert len(results) == 2
        assert results[0].text == '机器学习基础'

    @pytest.mark.asyncio
    async def test_suggest_mixed_language(self):
        """测试中英文混合联想"""
        self.mock_conn.fetch = AsyncMock(return_value=[
            {'title': 'Python机器学习'},
            {'title': 'Python Machine Learning'},
        ])

        results = await self.suggester.suggest_by_prefix(
            self.mock_pool, 'Python', kb_id=None, limit=5
        )

        assert len(results) == 2

    # ------ 错误处理 ------

    @pytest.mark.asyncio
    async def test_suggest_db_error_returns_empty(self):
        """测试数据库错误时返回空列表"""
        self.mock_conn.fetch = AsyncMock(side_effect=Exception('DB Error'))

        results = await self.suggester.suggest_by_prefix(
            self.mock_pool, 'test', kb_id=None, limit=5
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_record_search_db_error_returns_false(self):
        """测试记录搜索历史时数据库错误返回 False"""
        self.mock_conn.execute = AsyncMock(side_effect=Exception('DB Error'))

        result = await self.suggester.record_search(
            self.mock_pool,
            query='test',
            user_id='user1',
            kb_id=1,
            result_count=5,
        )
        assert result is False
