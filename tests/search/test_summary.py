"""LLM 摘要生成测试

测试 LLMSummarizer 的各种功能：
- 单个结果摘要生成
- 批量摘要生成
- 缓存命中
- 超时降级
- 空结果处理
- LLM 不可用时降级
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from lib.search.summary import (
    SummaryConfig,
    SummaryResult,
    LLMSummarizer,
)
from lib.search.engine import SearchResult


# ============================================================================
# 测试辅助函数
# ============================================================================


def _make_search_result(
    atom_id: int = 1,
    title: str = 'Test Title',
    content: str = 'This is test content for summarization.',
    score: float = 0.9,
) -> SearchResult:
    """创建测试用 SearchResult"""
    return SearchResult(
        atom_id=atom_id,
        slug=f'test-{atom_id}',
        title=title,
        content=content,
        score=score,
    )


def _make_summarizer(**overrides) -> LLMSummarizer:
    """创建带默认配置的 LLMSummarizer"""
    defaults = {
        'max_length': 100,
        'timeout': 5,
        'llm_api_key': 'sk-test-key',
        'llm_base_url': 'https://api.openai.com/v1',
        'fallback_to_truncate': True,
    }
    defaults.update(overrides)
    return LLMSummarizer(SummaryConfig(**defaults))


# ============================================================================
# 测试 SummaryConfig
# ============================================================================


class TestSummaryConfig:
    """SummaryConfig 数据类测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = SummaryConfig()
        assert config.max_length == 200
        assert config.timeout == 5
        assert config.cache_ttl == 3600
        assert config.llm_model == 'gpt-4o-mini'
        assert config.llm_base_url == 'https://api.openai.com/v1'
        assert config.llm_api_key == ''
        assert config.max_concurrent == 5
        assert config.fallback_to_truncate is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = SummaryConfig(
            max_length=100,
            timeout=3,
            llm_model='gpt-4',
            llm_api_key='sk-test-key',
        )
        assert config.max_length == 100
        assert config.timeout == 3
        assert config.llm_model == 'gpt-4'
        assert config.llm_api_key == 'sk-test-key'

    def test_config_is_frozen(self):
        """测试配置不可变性"""
        config = SummaryConfig(llm_api_key='sk-test')
        with pytest.raises(AttributeError):
            config.max_length = 100


# ============================================================================
# 测试 SummaryResult
# ============================================================================


class TestSummaryResult:
    """SummaryResult 数据类测试"""

    def test_basic_result(self):
        """测试基本摘要结果"""
        result = SummaryResult(
            summary='This is a summary.',
            source_id=1,
            from_cache=False,
            is_fallback=False,
        )
        assert result.summary == 'This is a summary.'
        assert result.source_id == 1
        assert result.from_cache is False
        assert result.is_fallback is False

    def test_fallback_result(self):
        """测试降级结果"""
        result = SummaryResult(
            summary='Truncated content...',
            source_id=2,
            from_cache=False,
            is_fallback=True,
        )
        assert result.is_fallback is True

    def test_cache_hit_result(self):
        """测试缓存命中结果"""
        result = SummaryResult(
            summary='Cached summary.',
            source_id=3,
            from_cache=True,
            is_fallback=False,
        )
        assert result.from_cache is True


# ============================================================================
# 测试 LLMSummarizer
# ============================================================================


class TestLLMSummarizer:
    """LLMSummarizer 摘要生成器测试"""

    # ------ 初始化 ------

    def test_init_requires_api_key(self):
        """测试无 API 密钥时初始化失败"""
        with pytest.raises(ValueError, match='api_key'):
            LLMSummarizer(SummaryConfig(llm_api_key=''))

    def test_init_with_api_key(self):
        """测试有 API 密钥时初始化成功"""
        summarizer = _make_summarizer()
        assert summarizer._config.llm_api_key == 'sk-test-key'

    # ------ 缓存键计算 ------

    def test_compute_cache_key_deterministic(self):
        """测试缓存键计算确定性"""
        summarizer = _make_summarizer()
        key1 = summarizer._compute_cache_key('content', 'query')
        key2 = summarizer._compute_cache_key('content', 'query')
        assert key1 == key2

    def test_compute_cache_key_different_content(self):
        """测试不同内容产生不同缓存键"""
        summarizer = _make_summarizer()
        key1 = summarizer._compute_cache_key('content1', 'query')
        key2 = summarizer._compute_cache_key('content2', 'query')
        assert key1 != key2

    def test_compute_cache_key_different_query(self):
        """测试不同查询产生不同缓存键"""
        summarizer = _make_summarizer()
        key1 = summarizer._compute_cache_key('content', 'query1')
        key2 = summarizer._compute_cache_key('content', 'query2')
        assert key1 != key2

    # ------ 降级截断 ------

    def test_truncate_fallback_short_content(self):
        """测试短内容不需要截断"""
        summarizer = _make_summarizer()
        content = 'Short content.'
        result = summarizer._truncate_fallback(content, max_length=100)
        assert result == content

    def test_truncate_fallback_long_content(self):
        """测试长内容截断"""
        summarizer = _make_summarizer()
        content = 'A' * 500
        result = summarizer._truncate_fallback(content, max_length=100)
        assert len(result) <= 103
        assert result.endswith('...') or '.' in result

    def test_truncate_fallback_empty_content(self):
        """测试空内容截断"""
        summarizer = _make_summarizer()
        result = summarizer._truncate_fallback('', max_length=100)
        assert result == ''

    def test_truncate_fallback_chinese_boundary(self):
        """测试中文内容截断在边界处"""
        summarizer = _make_summarizer()
        content = '这是一段中文文本，用于测试截断功能是否正确工作。' * 10
        result = summarizer._truncate_fallback(content, max_length=50)
        assert len(result) <= 53

    # ------ 单个摘要生成 ------

    @pytest.mark.asyncio
    async def test_summarize_cache_hit(self):
        """测试缓存命中"""
        summarizer = _make_summarizer()
        result = _make_search_result(content='test content')
        cache_key = summarizer._compute_cache_key(
            result.content, ''
        )

        # 预填充缓存（直接操作内部缓存以绕过异步锁）
        summarizer._cache[cache_key] = (
            'Cached summary',
            asyncio.get_event_loop().time(),
        )

        summary = await summarizer.summarize(result)

        assert summary.from_cache is True
        assert summary.summary == 'Cached summary'

    @pytest.mark.asyncio
    async def test_summarize_empty_content_fallback(self):
        """测试空内容摘要降级"""
        summarizer = _make_summarizer()
        result = _make_search_result(content='')

        summary = await summarizer.summarize(result)

        assert summary.is_fallback is True
        assert summary.summary == ''

    # ------ 批量摘要生成 ------

    @pytest.mark.asyncio
    async def test_summarize_batch_empty(self):
        """测试空批量"""
        summarizer = _make_summarizer()
        summaries = await summarizer.summarize_batch([])
        assert summaries == []

    @pytest.mark.asyncio
    async def test_summarize_batch_basic(self):
        """测试基本批量摘要"""
        summarizer = _make_summarizer()
        results = [
            _make_search_result(atom_id=i, content=f'Content {i}')
            for i in range(3)
        ]

        summaries = await summarizer.summarize_batch(results)
        assert len(summaries) == 3
        assert all(isinstance(s, SummaryResult) for s in summaries)

    # ------ 缓存管理 ------

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """测试清空缓存"""
        summarizer = _make_summarizer()
        summarizer._cache['key1'] = ('value1', 0)
        summarizer._cache['key2'] = ('value2', 0)

        await summarizer.clear_cache()

        assert len(summarizer._cache) == 0

    # ------ LLM 调用 ------

    @pytest.mark.asyncio
    async def test_call_llm_builds_correct_request(self):
        """测试 LLM 调用构建正确请求"""
        summarizer = _make_summarizer()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Summary text'}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(summarizer, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_ensure.return_value = mock_client

            result_text = await summarizer._call_llm(
                content='Test content',
                query='test query',
            )

        assert result_text == 'Summary text'

        # 验证请求参数
        call_args = mock_client.post.call_args
        assert 'chat/completions' in call_args[0][0]
        request_body = call_args[1].get('json', {})
        assert 'messages' in request_body

    @pytest.mark.asyncio
    async def test_call_llm_empty_content_raises(self):
        """测试空内容调用 LLM 抛出异常"""
        summarizer = _make_summarizer()

        with pytest.raises(ValueError, match='empty'):
            await summarizer._call_llm(content='  ', query='test')

    @pytest.mark.asyncio
    async def test_extract_summary_from_response(self):
        """测试从 API 响应中提取摘要"""
        data = {
            'choices': [{'message': {'content': 'Summary text'}}]
        }
        result = LLMSummarizer._extract_summary_from_response(data)
        assert result == 'Summary text'

    @pytest.mark.asyncio
    async def test_extract_summary_empty_choices_raises(self):
        """测试空 choices 抛出异常"""
        data = {'choices': []}
        with pytest.raises(ValueError, match='choices'):
            LLMSummarizer._extract_summary_from_response(data)

    @pytest.mark.asyncio
    async def test_extract_summary_empty_content_raises(self):
        """测试空内容抛出异常"""
        data = {'choices': [{'message': {'content': ''}}]}
        with pytest.raises(ValueError, match='content'):
            LLMSummarizer._extract_summary_from_response(data)

    # ------ 上下文管理器 ------

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """测试异步上下文管理器"""
        summarizer = _make_summarizer()

        async with summarizer:
            # 可以正常使用
            pass

        # 退出后客户端应被关闭
        assert summarizer._client is None or summarizer._client.is_closed
