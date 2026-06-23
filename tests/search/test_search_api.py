"""搜索 API 集成测试

测试 lib.api.search_api.SearchAPI 的核心功能：
- search: 全文搜索、参数验证、权限控制、高亮、分页
- suggest: 搜索联想、参数验证、知识库过滤
- summary: LLM 摘要生成、参数验证、降级处理
- 异常处理与错误响应格式
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from lib.api.search_api import SearchAPI
from lib.search.engine import SearchResult, SearchFilters
from lib.search.suggest import SuggestionResult, SuggestionType
from lib.search.summary import SummaryResult


# ============================================================================
# Mock 工厂
# ============================================================================


def _create_sample_search_results():
    """创建示例 SearchResult 对象列表"""
    return [
        SearchResult(
            atom_id=1,
            slug='python-guide',
            title='Python Guide',
            content='Python is a great programming language for beginners',
            score=0.95,
            highlights=['<mark>Python</mark> is great'],
            kb_id=1,
            kb_name='Engineering',
            atom_type='article',
            created_at=datetime(2024, 1, 15),
            updated_at=datetime(2024, 1, 20),
            match_type='fulltext',
        ),
        SearchResult(
            atom_id=2,
            slug='java-guide',
            title='Java Guide',
            content='Java is a popular programming language',
            score=0.85,
            highlights=[],
            kb_id=1,
            kb_name='Engineering',
            atom_type='article',
            created_at=datetime(2024, 2, 10),
            updated_at=datetime(2024, 2, 15),
            match_type='fulltext',
        ),
    ]


def _create_sample_suggestions():
    """创建示例 SuggestionResult 对象列表"""
    return [
        SuggestionResult(
            text='Python',
            suggestion_type=SuggestionType.PREFIX,
            score=1.0,
        ),
        SuggestionResult(
            text='Python async',
            suggestion_type=SuggestionType.HISTORY,
            score=0.8,
        ),
    ]


def _create_mock_search_engine():
    """创建 Mock SearchEngine"""
    engine = AsyncMock()
    engine.search = AsyncMock(return_value=_create_sample_search_results())
    engine.search_by_embedding = AsyncMock(return_value=[])
    engine.hybrid_search = AsyncMock(return_value=[])
    return engine


def _create_mock_suggester():
    """创建 Mock SearchSuggester"""
    suggester = AsyncMock()
    suggester.suggest = AsyncMock(return_value=_create_sample_suggestions())
    suggester.record_search = AsyncMock(return_value=True)
    return suggester


def _create_mock_highlighter():
    """创建 Mock HighlightGenerator"""
    highlighter = MagicMock()
    highlighter.generate_highlights = MagicMock(return_value=[
        '<mark>Python</mark> is great',
    ])
    return highlighter


def _create_mock_summarizer():
    """创建 Mock LLMSummarizer"""
    summarizer = AsyncMock()
    summarizer.summarize_batch = AsyncMock(return_value=[
        SummaryResult(
            summary='Python is a versatile programming language.',
            source_id=1,
            from_cache=False,
            is_fallback=False,
        ),
    ])
    summarizer.close = AsyncMock()
    return summarizer


def _create_mock_rbac(allowed=True):
    """创建 Mock RBAC 权限检查器"""
    rbac = AsyncMock()
    rbac.check_permission = AsyncMock(return_value=allowed)
    return rbac


def _create_search_api(
    search_engine=None,
    suggester=None,
    highlighter=None,
    summarizer=None,
    rbac=None,
):
    """创建 SearchAPI 实例，所有依赖均可选注入"""
    return SearchAPI(
        search_engine=search_engine or _create_mock_search_engine(),
        suggester=suggester or _create_mock_suggester(),
        highlighter=highlighter or _create_mock_highlighter(),
        summarizer=summarizer,
        rbac=rbac or _create_mock_rbac(allowed=True),
    )


# ============================================================================
# SearchAPI.search 测试
# ============================================================================


class TestSearchAPISearch:
    """SearchAPI.search 方法测试"""

    @pytest.mark.asyncio
    async def test_search_fulltext_success(self):
        """全文搜索成功返回正确格式"""
        api = _create_search_api()

        result = await api.search(
            user_id='user-1',
            query='Python',
            search_type='fulltext',
        )

        assert result['success'] is True
        assert 'data' in result
        assert 'results' in result['data']
        assert result['data']['total'] == 2
        assert result['data']['query'] == 'Python'
        assert result['data']['search_type'] == 'fulltext'
        assert result['code'] == 200

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        """空查询返回 400 错误"""
        api = _create_search_api()

        result = await api.search(
            user_id='user-1',
            query='',
        )

        assert result['success'] is False
        assert result['code'] == 400

    @pytest.mark.asyncio
    async def test_search_invalid_type(self):
        """无效搜索类型返回 400 错误"""
        api = _create_search_api()

        result = await api.search(
            user_id='user-1',
            query='Python',
            search_type='invalid_type',
        )

        assert result['success'] is False
        assert result['code'] == 400

    @pytest.mark.asyncio
    async def test_search_permission_denied(self):
        """权限不足返回 403 错误"""
        rbac = _create_mock_rbac(allowed=False)
        api = _create_search_api(rbac=rbac)

        result = await api.search(
            user_id='user-1',
            query='Python',
        )

        assert result['success'] is False
        assert result['code'] == 403

    @pytest.mark.asyncio
    async def test_search_with_highlights(self):
        """搜索结果包含高亮片段"""
        highlighter = _create_mock_highlighter()
        api = _create_search_api(highlighter=highlighter)

        result = await api.search(
            user_id='user-1',
            query='Python',
        )

        assert result['success'] is True
        highlighter.generate_highlights.assert_called()

    @pytest.mark.asyncio
    async def test_search_with_kb_filter(self):
        """带知识库过滤参数传递给搜索引擎"""
        engine = _create_mock_search_engine()
        api = _create_search_api(search_engine=engine)

        result = await api.search(
            user_id='user-1',
            query='Python',
            kb_id=42,
        )

        assert result['success'] is True
        engine.search.assert_called_once()
        call_kwargs = engine.search.call_args[1]
        assert call_kwargs.get('kb_id') == 42

    @pytest.mark.asyncio
    async def test_search_with_pagination(self):
        """分页参数正确传递给搜索引擎"""
        engine = _create_mock_search_engine()
        api = _create_search_api(search_engine=engine)

        result = await api.search(
            user_id='user-1',
            query='Python',
            limit=10,
            offset=20,
        )

        assert result['success'] is True
        engine.search.assert_called_once()
        call_kwargs = engine.search.call_args[1]
        assert call_kwargs.get('limit') == 10
        assert call_kwargs.get('offset') == 20

    @pytest.mark.asyncio
    async def test_search_engine_error(self):
        """搜索引擎异常返回 500 错误"""
        engine = _create_mock_search_engine()
        engine.search = AsyncMock(side_effect=Exception('Engine crashed'))
        api = _create_search_api(search_engine=engine)

        result = await api.search(
            user_id='user-1',
            query='Python',
        )

        assert result['success'] is False
        assert result['code'] == 500


# ============================================================================
# SearchAPI.suggest 测试
# ============================================================================


class TestSearchAPISuggest:
    """SearchAPI.suggest 方法测试"""

    @pytest.mark.asyncio
    async def test_suggest_success(self):
        """搜索联想成功返回正确格式"""
        api = _create_search_api()

        result = await api.suggest(
            user_id='user-1',
            prefix='Py',
        )

        assert result['success'] is True
        assert 'data' in result
        assert 'suggestions' in result['data']
        assert result['data']['query'] == 'Py'
        assert result['code'] == 200

    @pytest.mark.asyncio
    async def test_suggest_empty_prefix(self):
        """空前缀返回 400 错误"""
        api = _create_search_api()

        result = await api.suggest(
            user_id='user-1',
            prefix='',
        )

        assert result['success'] is False
        assert result['code'] == 400

    @pytest.mark.asyncio
    async def test_suggest_with_kb_filter(self):
        """带知识库过滤参数传递给联想器"""
        suggester = _create_mock_suggester()
        api = _create_search_api(suggester=suggester)

        result = await api.suggest(
            user_id='user-1',
            prefix='Py',
            kb_id=7,
        )

        assert result['success'] is True
        suggester.suggest.assert_called_once()
        call_kwargs = suggester.suggest.call_args[1]
        assert call_kwargs.get('kb_id') == 7

    @pytest.mark.asyncio
    async def test_suggest_error(self):
        """联想器异常返回 500 错误"""
        suggester = _create_mock_suggester()
        suggester.suggest = AsyncMock(side_effect=Exception('Suggest failed'))
        api = _create_search_api(suggester=suggester)

        result = await api.suggest(
            user_id='user-1',
            prefix='Py',
        )

        assert result['success'] is False
        assert result['code'] == 500


# ============================================================================
# SearchAPI.summary 测试
# ============================================================================


class TestSearchAPISummary:
    """SearchAPI.summary 方法测试"""

    @pytest.mark.asyncio
    async def test_summary_success(self):
        """摘要生成成功返回正确格式"""
        summarizer = _create_mock_summarizer()
        engine = _create_mock_search_engine()
        api = _create_search_api(
            summarizer=summarizer,
            search_engine=engine,
        )

        result = await api.summary(
            user_id='user-1',
            atom_ids=[1],
            query='Python',
        )

        assert result['success'] is True
        assert 'data' in result
        assert 'summaries' in result['data']
        assert result['code'] == 200

    @pytest.mark.asyncio
    async def test_summary_empty_atom_ids(self):
        """空 atom_ids 返回 400 错误"""
        api = _create_search_api()

        result = await api.summary(
            user_id='user-1',
            atom_ids=[],
        )

        assert result['success'] is False
        assert result['code'] == 400

    @pytest.mark.asyncio
    async def test_summary_no_summarizer(self):
        """无 summarizer 时返回空摘要（降级模式）"""
        engine = _create_mock_search_engine()
        api = _create_search_api(summarizer=None, search_engine=engine)

        result = await api.summary(
            user_id='user-1',
            atom_ids=[1],
        )

        assert result['success'] is True
        assert 'summaries' in result['data']
        # 降级模式下每个 atom 返回空摘要
        for s in result['data']['summaries']:
            assert s.get('is_fallback') is True

    @pytest.mark.asyncio
    async def test_summary_error(self):
        """摘要器异常返回 500 错误"""
        summarizer = _create_mock_summarizer()
        summarizer.summarize_batch = AsyncMock(
            side_effect=Exception('LLM timeout'),
        )
        engine = _create_mock_search_engine()
        api = _create_search_api(
            summarizer=summarizer,
            search_engine=engine,
        )

        result = await api.summary(
            user_id='user-1',
            atom_ids=[1],
        )

        assert result['success'] is False
        assert result['code'] == 500
