"""统一搜索 API

提供搜索、联想、摘要的统一接口，支持：
- 全文搜索（fulltext）
- 向量搜索（vector）
- 混合搜索（hybrid）
- 搜索联想建议（suggest）
- LLM 摘要生成（summary）
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..search.engine import SearchEngine, SearchFilters, SearchResult
from ..search.suggest import SearchSuggester, SuggestionResult
from ..search.highlight import HighlightGenerator, HighlightConfig
from ..search.summary import LLMSummarizer, SummaryResult
from ..auth.rbac import RBACManager, Permission

logger = logging.getLogger(__name__)


@dataclass
class SearchRequest:
    """搜索请求

    Attributes:
        query: 搜索查询字符串
        search_type: 搜索类型（fulltext/vector/hybrid）
        kb_id: 知识库 ID（可选，不指定则全局搜索）
        limit: 返回数量上限
        offset: 偏移量（分页）
        filters: 过滤条件
        embedding: 查询向量（vector/hybrid 搜索时必填）
    """
    query: str
    search_type: str = 'fulltext'
    kb_id: Optional[int] = None
    limit: int = 20
    offset: int = 0
    filters: Optional[SearchFilters] = None
    embedding: Optional[List[float]] = None


@dataclass
class SuggestRequest:
    """联想建议请求

    Attributes:
        prefix: 输入前缀
        kb_id: 知识库 ID（可选）
        limit: 返回数量上限
    """
    prefix: str
    kb_id: Optional[int] = None
    limit: int = 10


@dataclass
class SummaryRequest:
    """摘要请求

    Attributes:
        atom_ids: 知识原子 ID 列表
        query: 搜索查询（用于聚焦摘要方向）
    """
    atom_ids: List[int] = field(default_factory=list)
    query: str = ''


class SearchAPI:
    """统一搜索 API

    整合 SearchEngine、SearchSuggester、HighlightGenerator、LLMSummarizer，
    提供统一的搜索接口，包含权限检查、参数验证和错误处理。
    """

    def __init__(
        self,
        search_engine: SearchEngine,
        suggester: SearchSuggester,
        highlighter: HighlightGenerator,
        rbac: RBACManager,
        summarizer: Optional[LLMSummarizer] = None,
    ) -> None:
        """初始化搜索 API

        Args:
            search_engine: 搜索引擎实例
            suggester: 搜索联想器实例
            highlighter: 高亮生成器实例
            rbac: RBAC 权限管理器
            summarizer: LLM 摘要生成器（可选，不可用时摘要功能降级）
        """
        self._search_engine = search_engine
        self._suggester = suggester
        self._highlighter = highlighter
        self._rbac = rbac
        self._summarizer = summarizer

    async def initialize(self) -> None:
        """初始化 API"""
        logger.info("SearchAPI initialized")

    async def close(self) -> None:
        """关闭 API，释放资源"""
        if self._summarizer is not None:
            await self._summarizer.close()
        logger.info("SearchAPI closed")

    async def search(
        self,
        user_id: str,
        query: str,
        search_type: str = 'fulltext',
        kb_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[SearchFilters] = None,
        embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """执行搜索

        Args:
            user_id: 用户 ID
            query: 搜索查询字符串
            search_type: 搜索类型（fulltext/vector/hybrid）
            kb_id: 知识库 ID（可选）
            limit: 返回数量上限
            offset: 偏移量（分页）
            filters: 过滤条件
            embedding: 查询向量（vector/hybrid 时必填）

        Returns:
            搜索结果，包含 results、total、query、search_type
        """
        try:
            # 权限检查
            if not await self._rbac.check_permission(
                user_id, kb_id or 0, Permission.ATOM_READ
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403,
                }

            # 参数验证
            validation = self._validate_search_params(
                query, search_type, limit, offset, embedding,
            )
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error'],
                    'code': 400,
                }

            # 执行搜索
            results = await self._execute_search(
                query, search_type, kb_id, filters, limit, offset, embedding,
            )

            # 生成高亮
            results = self._apply_highlights(results, query)

            # 记录搜索历史
            await self._record_search_history(user_id, query, kb_id, len(results))

            # 序列化结果
            result_dicts = [r.to_dict() for r in results]

            return {
                'success': True,
                'data': {
                    'results': result_dicts,
                    'total': len(result_dicts),
                    'query': query,
                    'search_type': search_type,
                },
                'code': 200,
            }

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    async def suggest(
        self,
        user_id: str,
        prefix: str,
        kb_id: Optional[int] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """获取搜索联想建议

        Args:
            user_id: 用户 ID
            prefix: 输入前缀
            kb_id: 知识库 ID（可选）
            limit: 返回数量上限

        Returns:
            联想建议列表
        """
        try:
            # 权限检查
            if not await self._rbac.check_permission(
                user_id, kb_id or 0, Permission.ATOM_READ
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403,
                }

            # 参数验证
            if not prefix or not prefix.strip():
                return {
                    'success': False,
                    'error': 'prefix must not be empty',
                    'code': 400,
                }

            # 调用联想器
            suggestions = await self._suggester.suggest(
                pool=None,
                prefix=prefix.strip(),
                kb_id=kb_id,
                limit=limit,
            )

            # 序列化结果
            suggestion_dicts = [s.to_dict() for s in suggestions]

            return {
                'success': True,
                'data': {
                    'suggestions': suggestion_dicts,
                    'query': prefix,
                },
                'code': 200,
            }

        except Exception as e:
            logger.error(f"Suggest failed for prefix '{prefix}': {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    async def summary(
        self,
        user_id: str,
        atom_ids: List[int],
        query: str = '',
    ) -> Dict[str, Any]:
        """生成搜索结果摘要

        Args:
            user_id: 用户 ID
            atom_ids: 知识原子 ID 列表
            query: 搜索查询（用于聚焦摘要方向）

        Returns:
            摘要结果列表
        """
        try:
            # 参数验证
            if not atom_ids:
                return {
                    'success': False,
                    'error': 'atom_ids must not be empty',
                    'code': 400,
                }

            # 权限检查
            if not await self._rbac.check_permission(
                user_id, 0, Permission.ATOM_READ
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403,
                }

            # 获取搜索结果用于摘要
            search_results = await self._fetch_results_by_ids(atom_ids)

            # 生成摘要
            summaries = await self._generate_summaries(search_results, query)

            # 序列化结果
            summary_dicts = [self._serialize_summary(s) for s in summaries]

            return {
                'success': True,
                'data': {
                    'summaries': summary_dicts,
                },
                'code': 200,
            }

        except Exception as e:
            logger.error(f"Summary failed for atom_ids {atom_ids}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    # ========== 内部方法 ==========

    def _validate_search_params(
        self,
        query: str,
        search_type: str,
        limit: int,
        offset: int,
        embedding: Optional[List[float]],
    ) -> Dict[str, Any]:
        """验证搜索参数

        Args:
            query: 查询字符串
            search_type: 搜索类型
            limit: 返回数量上限
            offset: 偏移量
            embedding: 查询向量

        Returns:
            验证结果，包含 valid 和 error 字段
        """
        if not query or not query.strip():
            return {'valid': False, 'error': 'query must not be empty'}

        valid_types = ('fulltext', 'vector', 'hybrid')
        if search_type not in valid_types:
            return {
                'valid': False,
                'error': f'Invalid search_type: {search_type}, '
                         f'must be one of {valid_types}',
            }

        if search_type in ('vector', 'hybrid') and not embedding:
            return {
                'valid': False,
                'error': f'embedding is required for {search_type} search',
            }

        if limit < 1 or limit > 100:
            return {'valid': False, 'error': 'limit must be between 1 and 100'}

        if offset < 0:
            return {'valid': False, 'error': 'offset must be non-negative'}

        return {'valid': True, 'error': ''}

    async def _execute_search(
        self,
        query: str,
        search_type: str,
        kb_id: Optional[int],
        filters: Optional[SearchFilters],
        limit: int,
        offset: int,
        embedding: Optional[List[float]],
    ) -> List[SearchResult]:
        """根据搜索类型调用对应的搜索引擎方法

        Args:
            query: 查询字符串
            search_type: 搜索类型
            kb_id: 知识库 ID
            filters: 过滤条件
            limit: 返回数量上限
            offset: 偏移量
            embedding: 查询向量

        Returns:
            搜索结果列表
        """
        if search_type == 'fulltext':
            return await self._search_engine.search(
                query=query,
                kb_id=kb_id,
                filters=filters,
                limit=limit,
                offset=offset,
            )

        if search_type == 'vector':
            return await self._search_engine.search_by_embedding(
                embedding=embedding,
                kb_id=kb_id,
                filters=filters,
                limit=limit,
            )

        # hybrid
        return await self._search_engine.hybrid_search(
            query=query,
            embedding=embedding,
            kb_id=kb_id,
            filters=filters,
            limit=limit,
        )

    def _apply_highlights(
        self,
        results: List[SearchResult],
        query: str,
    ) -> List[SearchResult]:
        """为搜索结果生成高亮片段

        对已有高亮的结果跳过，仅对无高亮的结果生成。

        Args:
            results: 原始搜索结果列表
            query: 查询字符串

        Returns:
            包含高亮片段的搜索结果列表（新列表，不修改原对象）
        """
        highlighted = []
        for result in results:
            if result.highlights:
                highlighted.append(result)
                continue

            highlights = self._highlighter.generate_highlights(
                text=result.content,
                query=query,
            )
            # 不可变性：创建新对象而非修改原对象
            highlighted.append(SearchResult(
                atom_id=result.atom_id,
                slug=result.slug,
                title=result.title,
                content=result.content,
                score=result.score,
                highlights=highlights,
                metadata=result.metadata,
                kb_id=result.kb_id,
                kb_name=result.kb_name,
                atom_type=result.atom_type,
                created_at=result.created_at,
                updated_at=result.updated_at,
                match_type=result.match_type,
            ))

        return highlighted

    async def _record_search_history(
        self,
        user_id: str,
        query: str,
        kb_id: Optional[int],
        result_count: int,
    ) -> None:
        """记录搜索历史

        Args:
            user_id: 用户 ID
            query: 查询字符串
            kb_id: 知识库 ID
            result_count: 结果数量
        """
        try:
            await self._suggester.record_search(
                pool=None,
                query=query,
                user_id=user_id,
                kb_id=kb_id,
                result_count=result_count,
            )
        except Exception as e:
            # 搜索历史记录失败不影响搜索结果
            logger.warning(f"Failed to record search history: {e}")

    async def _fetch_results_by_ids(
        self,
        atom_ids: List[int],
    ) -> List[SearchResult]:
        """根据 atom_id 列表获取搜索结果

        使用搜索引擎的 search 方法逐个获取，
        后续可优化为批量查询。

        Args:
            atom_ids: 知识原子 ID 列表

        Returns:
            搜索结果列表
        """
        results: List[SearchResult] = []
        for atom_id in atom_ids:
            try:
                # 使用 search 方法按 ID 过滤
                # TODO: 优化为批量查询接口
                search_results = await self._search_engine.search(
                    query=str(atom_id),
                    filters=SearchFilters(kb_id=None),
                    limit=1,
                    offset=0,
                )
                matched = [
                    r for r in search_results if r.atom_id == atom_id
                ]
                if matched:
                    results.append(matched[0])
            except Exception as e:
                logger.warning(f"Failed to fetch atom {atom_id}: {e}")

        return results

    async def _generate_summaries(
        self,
        results: List[SearchResult],
        query: str,
    ) -> List[Dict[str, Any]]:
        """为搜索结果生成摘要

        如果 summarizer 可用则调用 LLM 生成摘要，
        否则返回空摘要。

        Args:
            results: 搜索结果列表
            query: 搜索查询

        Returns:
            摘要结果字典列表
        """
        if self._summarizer is None:
            return [
                {
                    'atom_id': r.atom_id,
                    'summary': '',
                    'from_cache': False,
                    'is_fallback': True,
                }
                for r in results
            ]

        summary_results = await self._summarizer.summarize_batch(
            results, query=query,
        )

        return [
            {
                'atom_id': s.source_id,
                'summary': s.summary,
                'from_cache': s.from_cache,
                'is_fallback': s.is_fallback,
            }
            for s in summary_results
        ]

    @staticmethod
    def _serialize_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
        """序列化摘要结果

        Args:
            summary: 摘要字典

        Returns:
            序列化后的摘要字典
        """
        return {
            'atom_id': summary.get('atom_id'),
            'summary': summary.get('summary', ''),
            'from_cache': summary.get('from_cache', False),
            'is_fallback': summary.get('is_fallback', False),
        }
