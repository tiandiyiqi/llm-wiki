"""LLM 摘要生成模块

使用 OpenAI 兼容 API 从搜索结果中抽取摘要，支持批量生成、缓存和降级策略。

使用示例:
    import os
    from lib.search.summary import LLMSummarizer, SummaryConfig

    config = SummaryConfig(
        llm_base_url="https://api.openai.com/v1",
        llm_api_key=os.environ["OPENAI_API_KEY"],
        llm_model="gpt-4o-mini",
    )
    async with LLMSummarizer(config) as summarizer:
        # 单个摘要
        result = await summarizer.summarize(search_result, query="机器学习")

        # 批量摘要
        results = await summarizer.summarize_batch(search_results, query="机器学习")
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx

from .engine import SearchResult

logger = logging.getLogger(__name__)

# 超长内容截断阈值，避免超出 LLM 上下文窗口
_MAX_LLM_CONTENT_LENGTH = 12000


@dataclass(frozen=True)
class SummaryConfig:
    """摘要配置

    Attributes:
        max_length: 摘要最大长度（字数），默认 200
        timeout: LLM 调用超时时间（秒），默认 5
        cache_ttl: 缓存过期时间（秒），默认 3600
        llm_model: LLM 模型名称
        llm_base_url: API 基础 URL
        llm_api_key: API 密钥（必填）
        max_concurrent: 最大并发数，默认 5
        fallback_to_truncate: 降级策略开关，默认 True
    """

    max_length: int = 200
    timeout: int = 5
    cache_ttl: int = 3600
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    max_concurrent: int = 5
    fallback_to_truncate: bool = True


@dataclass(frozen=True)
class SummaryResult:
    """摘要结果

    Attributes:
        summary: 摘要文本
        source_id: 来源搜索结果的 atom_id
        from_cache: 是否缓存命中
        is_fallback: 是否降级（截断原文）
    """

    summary: str
    source_id: int
    from_cache: bool = False
    is_fallback: bool = False


class LLMSummarizer:
    """LLM 摘要生成器

    特性：
    - 调用 OpenAI 兼容 API 生成摘要
    - 批量摘要并行生成（信号量控制并发）
    - 基于内容 hash 的摘要缓存（异步锁保护）
    - 超时控制和降级策略
    - 支持异步上下文管理器协议

    用法:
        async with LLMSummarizer(config) as summarizer:
            results = await summarizer.summarize_batch(search_results, query="AI")
    """

    def __init__(self, config: SummaryConfig) -> None:
        """初始化摘要生成器

        Args:
            config: 摘要配置

        Raises:
            ValueError: llm_api_key 为空时抛出
        """
        if not config.llm_api_key:
            raise ValueError("llm_api_key is required and cannot be empty")

        self._config = config
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._cache_lock = asyncio.Lock()
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._client: Optional[httpx.AsyncClient] = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """延迟创建信号量，避免事件循环绑定问题"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._config.max_concurrent)
        return self._semaphore

    async def _ensure_client(self) -> httpx.AsyncClient:
        """确保 httpx 客户端可用（复用连接池）"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._config.timeout)
        return self._client

    async def close(self) -> None:
        """关闭 HTTP 客户端连接"""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "LLMSummarizer":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def summarize(
        self, result: SearchResult, query: str = ""
    ) -> SummaryResult:
        """为单个搜索结果生成摘要

        Args:
            result: 搜索结果
            query: 搜索查询（用于聚焦摘要方向）

        Returns:
            摘要结果
        """
        cache_key = self._compute_cache_key(result.content, query)

        # 检查缓存
        cached_summary = await self._get_from_cache(cache_key)
        if cached_summary is not None:
            return SummaryResult(
                summary=cached_summary,
                source_id=result.atom_id,
                from_cache=True,
                is_fallback=False,
            )

        # 调用 LLM 生成摘要
        try:
            summary = await asyncio.wait_for(
                self._call_llm(result.content, query),
                timeout=self._config.timeout,
            )
            await self._set_cache(cache_key, summary)
            return SummaryResult(
                summary=summary,
                source_id=result.atom_id,
                from_cache=False,
                is_fallback=False,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"LLM summary timeout for atom_id={result.atom_id}"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403, 402):
                logger.error(
                    f"LLM API auth/quota error ({e.response.status_code}): {e}"
                )
                raise
            logger.error(
                f"LLM API HTTP error for atom_id={result.atom_id}: {e}"
            )
        except (httpx.HTTPError, ValueError) as e:
            logger.error(f"LLM summary failed for atom_id={result.atom_id}: {e}")

        # 降级策略
        return self._create_fallback_result(result)

    async def summarize_batch(
        self, results: List[SearchResult], query: str = ""
    ) -> List[SummaryResult]:
        """为多个搜索结果并行生成摘要

        使用信号量控制最大并发数，避免 LLM API 过载。

        Args:
            results: 搜索结果列表
            query: 搜索查询（用于聚焦摘要方向）

        Returns:
            摘要结果列表（与输入顺序一致）
        """
        if not results:
            return []

        tasks = [self._summarize_with_semaphore(r, query) for r in results]
        return await asyncio.gather(*tasks)

    async def _summarize_with_semaphore(
        self, result: SearchResult, query: str
    ) -> SummaryResult:
        """在信号量控制下生成单个摘要"""
        async with self._get_semaphore():
            return await self.summarize(result, query)

    async def _call_llm(self, content: str, query: str) -> str:
        """调用 LLM API 生成摘要

        使用 OpenAI 兼容的 chat/completions 接口。

        Args:
            content: 待摘要的原文
            query: 搜索查询（用于聚焦摘要方向）

        Returns:
            生成的摘要文本

        Raises:
            ValueError: 内容为空或 API 响应异常
            httpx.HTTPStatusError: HTTP 状态码错误
            httpx.HTTPError: 网络请求失败
        """
        if not content.strip():
            raise ValueError("Content cannot be empty for summarization")

        # 截断超长内容，避免超出上下文窗口
        if len(content) > _MAX_LLM_CONTENT_LENGTH:
            logger.warning(
                f"Content length {len(content)} exceeds "
                f"{_MAX_LLM_CONTENT_LENGTH}, truncating"
            )
            content = content[:_MAX_LLM_CONTENT_LENGTH]

        url = f"{self._config.llm_base_url.rstrip('/')}/chat/completions"
        system_prompt = (
            f"你是一个知识摘要生成器。请根据搜索查询，从给定内容中提取关键信息，"
            f"生成简洁的摘要。摘要长度不超过 {self._config.max_length} 字。"
        )
        user_prompt = f"搜索查询：{query}\n\n内容：{content}"

        payload = {
            "model": self._config.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": self._config.max_length * 2,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.llm_api_key}",
        }

        client = await self._ensure_client()
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return self._extract_summary_from_response(response.json())

    @staticmethod
    def _extract_summary_from_response(data: Dict) -> str:
        """从 LLM API 响应中提取摘要文本

        Args:
            data: API 响应 JSON

        Returns:
            摘要文本

        Raises:
            ValueError: 响应格式异常或内容为空
        """
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("LLM API returned empty choices")

        message = choices[0].get("message", {})
        summary_text = message.get("content", "").strip()

        if not summary_text:
            raise ValueError("LLM API returned empty content")

        return summary_text

    def _truncate_fallback(self, content: str, max_length: int) -> str:
        """降级截断策略

        当 LLM 不可用时，直接截断原文作为摘要。

        Args:
            content: 原始内容
            max_length: 最大长度

        Returns:
            截断后的文本
        """
        if len(content) <= max_length:
            return content

        truncated = content[:max_length]
        # 在最后一个句号/问号/叹号处截断，保持语义完整
        for sep in ["。", "？", "！", ".", "?", "!"]:
            last_sep = truncated.rfind(sep)
            if last_sep > max_length // 2:
                return truncated[: last_sep + 1]

        return truncated + "..."

    def _compute_cache_key(self, content: str, query: str) -> str:
        """计算缓存键

        基于内容和查询的 SHA-256 hash，确保相同输入命中同一缓存。

        Args:
            content: 原文内容
            query: 搜索查询

        Returns:
            缓存键字符串
        """
        raw = f"{content}||{query}||{self._config.max_length}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def _get_from_cache(self, key: str) -> Optional[str]:
        """从缓存获取摘要（异步锁保护）

        Args:
            key: 缓存键

        Returns:
            缓存的摘要文本，未命中或已过期返回 None
        """
        async with self._cache_lock:
            if key not in self._cache:
                return None

            cached_summary, cached_ts = self._cache[key]
            if time.monotonic() - cached_ts > self._config.cache_ttl:
                del self._cache[key]
                return None

            return cached_summary

    async def _set_cache(self, key: str, summary: str) -> None:
        """设置缓存（异步锁保护）

        Args:
            key: 缓存键
            summary: 摘要文本
        """
        async with self._cache_lock:
            self._cache[key] = (summary, time.monotonic())

            if len(self._cache) > 1000:
                self._clean_cache_locked()

    def _clean_cache_locked(self) -> None:
        """清理过期缓存项（必须在持有 _cache_lock 时调用）"""
        now = time.monotonic()
        ttl = self._config.cache_ttl
        self._cache = {
            k: v for k, v in self._cache.items() if now - v[1] <= ttl
        }
        logger.debug("Cache cleanup completed")

    async def _clean_cache(self) -> None:
        """清理过期缓存项（异步锁保护）"""
        async with self._cache_lock:
            self._clean_cache_locked()

    async def clear_cache(self) -> None:
        """清空所有缓存"""
        async with self._cache_lock:
            self._cache.clear()
        logger.debug("Cache cleared")

    def _create_fallback_result(self, result: SearchResult) -> SummaryResult:
        """创建降级结果

        Args:
            result: 搜索结果

        Returns:
            降级摘要结果（截断原文）
        """
        if not self._config.fallback_to_truncate:
            return SummaryResult(
                summary="",
                source_id=result.atom_id,
                from_cache=False,
                is_fallback=True,
            )

        truncated = self._truncate_fallback(
            result.content, self._config.max_length
        )
        return SummaryResult(
            summary=truncated,
            source_id=result.atom_id,
            from_cache=False,
            is_fallback=True,
        )
