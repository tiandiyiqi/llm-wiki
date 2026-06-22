"""PostgreSQL 搜索引擎实现

使用 PostgreSQL tsvector 全文检索和 pgvector 向量检索。
"""

import asyncio
import json
import logging
import re
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from .engine import SearchEngine, SearchResult, SearchFilters
from .hybrid_search import HybridSearchOptimizer


logger = logging.getLogger(__name__)


class PostgreSQLSearchEngine(SearchEngine):
    """PostgreSQL 搜索引擎实现

    特性：
    - 使用 tsvector + tsquery 全文搜索
    - 使用 pgvector 余弦相似度向量搜索
    - 使用 ts_rank 计算相关性
    - 使用 ts_headline 生成高亮片段
    - 支持 websearch_to_tsquery（用户友好查询语法）
    - 支持 RRF 混合搜索
    - 内置查询缓存

    Attributes:
        pool: asyncpg 连接池
        cache_ttl: 缓存过期时间（秒）
        use_chinese_parser: 是否使用中文分词器
    """

    def __init__(
        self,
        pool: Any,
        cache_ttl: int = 300,
        use_chinese_parser: bool = False,
    ):
        """初始化 PostgreSQL 搜索引擎

        Args:
            pool: asyncpg 连接池
            cache_ttl: 缓存过期时间（秒），默认 5 分钟
            use_chinese_parser: 是否使用 zhparser 中文分词
        """
        self.pool = pool
        self.cache_ttl = cache_ttl
        self.use_chinese_parser = use_chinese_parser
        self._cache: Dict[str, Tuple[List[SearchResult], datetime]] = {}
        self._optimizer = HybridSearchOptimizer()

    # ========== 全文搜索 ==========

    async def search(
        self,
        query: str,
        kb_id: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SearchResult]:
        """执行全文搜索

        使用 PostgreSQL tsvector 全文索引：
        - websearch_to_tsquery 支持用户友好语法
        - ts_rank 计算相关性得分
        - ts_headline 生成高亮片段
        """
        if not query or not query.strip():
            return []

        # 检查缓存
        cache_key = self._get_cache_key('fulltext', query, kb_id, filters, limit, offset)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for query: {query}")
            return cached

        async def _search():
            async with self.pool.acquire() as conn:
                # 构建查询
                ts_query = self._build_tsquery(query)
                params: List[Any] = [ts_query]
                param_idx = 2

                # 基础 SQL
                sql = '''
                    SELECT
                        a.id as atom_id,
                        a.slug,
                        a.title,
                        a.content,
                        a.metadata,
                        a.type as atom_type,
                        a.created_at,
                        a.updated_at,
                        kb.id as kb_id,
                        kb.name as kb_name,
                        ts_rank(a.content_tsv, plainto_tsquery('simple', $1)) as rank,
                        ts_headline(
                            'english',
                            a.content,
                            plainto_tsquery('simple', $1),
                            'MaxWords=50, MinWords=10, StartSel=<mark>, StopSel=</mark>'
                        ) as highlight
                    FROM atoms a
                    LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id
                    WHERE a.content_tsv @@ plainto_tsquery('simple', $1)
                      AND a.status = 'active'
                '''

                # 应用过滤条件
                sql, params, param_idx = self._apply_filters(
                    sql, params, param_idx, kb_id, filters
                )

                # 排序和分页
                sql += f'''
                    ORDER BY rank DESC
                    LIMIT ${param_idx} OFFSET ${param_idx + 1}
                '''
                params.extend([limit, offset])

                # 执行查询
                rows = await conn.fetch(sql, *params)

                # 转换结果
                results = [self._row_to_result(row, 'fulltext') for row in rows]

                # 设置缓存
                self._set_cache(cache_key, results)

                return results

        try:
            return await self._execute_with_retry(_search)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def search_with_highlights(
        self,
        query: str,
        kb_id: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
        limit: int = 50,
        offset: int = 0,
        highlight_config: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """执行全文搜索并生成高亮片段

        使用 ts_headline 生成高亮片段。
        """
        config = highlight_config or {}
        max_words = max(1, min(500, int(config.get('max_words', 50))))
        max_fragments = max(1, min(10, int(config.get('max_fragments', 3))))
        _ALLOWED_DELIM = {'<mark>', '<strong>', '<b>', '<em>', '**', '__'}
        start_sel = config.get('start_delimiter', '<mark>')
        if start_sel not in _ALLOWED_DELIM:
            start_sel = '<mark>'
        stop_sel = config.get('end_delimiter', '</mark>')
        if stop_sel not in _ALLOWED_DELIM:
            stop_sel = '</mark>'

        # 检查缓存
        cache_key = self._get_cache_key(
            'highlight', query, kb_id, filters, limit, offset,
            max_words, max_fragments
        )
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        async def _search():
            async with self.pool.acquire() as conn:
                ts_query = self._build_tsquery(query)
                params: List[Any] = [ts_query]
                param_idx = 2

                headline_options = f'MaxWords={max_words}, MinWords=10, ' \
                                   f'MaxFragments={max_fragments}, ' \
                                   f'StartSel={start_sel}, StopSel={stop_sel}'

                sql = '''
                    SELECT
                        a.id as atom_id,
                        a.slug,
                        a.title,
                        a.content,
                        a.metadata,
                        a.type as atom_type,
                        a.created_at,
                        a.updated_at,
                        kb.id as kb_id,
                        kb.name as kb_name,
                        ts_rank(a.content_tsv, plainto_tsquery('simple', $1)) as rank,
                        ts_headline('english', a.title, plainto_tsquery('simple', $1), $2) as title_highlight,
                        ts_headline('english', a.content, plainto_tsquery('simple', $1), $2) as content_highlight,
                        ts_headline('english', a.description, plainto_tsquery('simple', $1), $2) as desc_highlight
                    FROM atoms a
                    LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id
                    WHERE a.content_tsv @@ plainto_tsquery('simple', $1)
                      AND a.status = 'active'
                '''

                params.append(headline_options)
                param_idx += 1

                sql, params, param_idx = self._apply_filters(
                    sql, params, param_idx, kb_id, filters
                )

                sql += f'''
                    ORDER BY rank DESC
                    LIMIT ${param_idx} OFFSET ${param_idx + 1}
                '''
                params.extend([limit, offset])

                rows = await conn.fetch(sql, *params)

                results = []
                for row in rows:
                    result = self._row_to_result(row, 'fulltext')
                    highlights = []
                    if row.get('title_highlight'):
                        highlights.append(row['title_highlight'])
                    if row.get('desc_highlight'):
                        highlights.append(row['desc_highlight'])
                    if row.get('content_highlight'):
                        highlights.append(row['content_highlight'])
                    result.highlights = highlights
                    results.append(result)

                self._set_cache(cache_key, results)
                return results

        try:
            return await self._execute_with_retry(_search)
        except Exception as e:
            logger.error(f"Search with highlights failed: {e}")
            return []

    # ========== 向量搜索 ==========

    async def search_by_embedding(
        self,
        embedding: List[float],
        kb_id: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
        limit: int = 50,
    ) -> List[SearchResult]:
        """执行向量相似度搜索

        使用 pgvector 余弦相似度运算符 <=>。
        """
        if not embedding or len(embedding) != 384:
            logger.warning(f"Invalid embedding length: {len(embedding) if embedding else 0}")
            return []

        async def _search():
            async with self.pool.acquire() as conn:
                # 将向量转换为字符串格式
                embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
                params: List[Any] = [embedding_str]
                param_idx = 2

                sql = '''
                    SELECT
                        a.id as atom_id,
                        a.slug,
                        a.title,
                        a.content,
                        a.metadata,
                        a.type as atom_type,
                        a.created_at,
                        a.updated_at,
                        kb.id as kb_id,
                        kb.name as kb_name,
                        1 - (a.embedding <=> $1::vector) as similarity
                    FROM atoms a
                    LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id
                    WHERE a.embedding IS NOT NULL
                      AND a.status = 'active'
                '''

                sql, params, param_idx = self._apply_filters(
                    sql, params, param_idx, kb_id, filters
                )

                # 按相似度排序（余弦距离越小越相似）
                sql += f'''
                    ORDER BY a.embedding <=> $1::vector
                    LIMIT ${param_idx}
                '''
                params.append(limit)

                rows = await conn.fetch(sql, *params)

                results = [self._row_to_result(row, 'vector') for row in rows]
                # 调整分数：相似度转换为 0-1 范围
                for result in results:
                    result.score = max(0, min(1, result.score))

                return results

        try:
            return await self._execute_with_retry(_search)
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    # ========== 混合搜索 ==========

    async def hybrid_search(
        self,
        query: str,
        embedding: List[float],
        kb_id: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
        text_weight: float = 0.5,
        vector_weight: float = 0.5,
        limit: int = 50,
    ) -> List[SearchResult]:
        """执行混合搜索（全文 + 向量）

        使用 RRF (Reciprocal Rank Fusion) 合并结果。

        策略：
        1. 分别执行全文搜索和向量搜索
        2. 使用 RRF 算法合并排名
        3. 按合并得分排序返回
        """
        # 并行执行两种搜索
        text_limit = limit * 2  # 获取更多候选结果
        vector_limit = limit * 2

        try:
            text_results, vector_results = await asyncio.gather(
                self.search(query, kb_id, filters, text_limit),
                self.search_by_embedding(embedding, kb_id, filters, vector_limit),
            )
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

        # 使用 RRF 合并结果
        k = 60  # RRF 常数
        merged = self._optimizer.reciprocal_rank_fusion(
            [text_results, vector_results],
            weights=[text_weight, vector_weight],
            k=k,
        )

        # 截取指定数量
        return merged[:limit]

    # ========== 搜索建议 ==========

    async def suggest(
        self,
        prefix: str,
        kb_id: Optional[int] = None,
        limit: int = 5,
    ) -> List[str]:
        """获取搜索联想建议

        基于标题和描述的前缀匹配。
        """
        if not prefix or len(prefix) < 2:
            return []

        # 检查缓存
        cache_key = self._get_cache_key('suggest', prefix, kb_id, limit)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        async def _suggest():
            async with self.pool.acquire() as conn:
                params: List[Any] = [prefix + '%']  # 前缀匹配
                param_idx = 2

                sql = '''
                    SELECT DISTINCT title
                    FROM atoms
                    WHERE status = 'active'
                      AND LOWER(title) LIKE LOWER($1)
                '''

                if kb_id:
                    sql += f" AND kb_id = ${param_idx}"
                    params.append(kb_id)
                    param_idx += 1

                sql += f'''
                    ORDER BY title
                    LIMIT ${param_idx}
                '''
                params.append(limit)

                rows = await conn.fetch(sql, *params)
                suggestions = [row['title'] for row in rows]

                self._set_cache(cache_key, suggestions)
                return suggestions

        try:
            return await self._execute_with_retry(_suggest)
        except Exception as e:
            logger.error(f"Suggest failed: {e}")
            return []

    # ========== 统计信息 ==========

    async def get_search_stats(
        self,
        kb_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """获取搜索统计信息"""
        async def _stats():
            async with self.pool.acquire() as conn:
                stats: Dict[str, Any] = {}

                # 总原子数
                if kb_id:
                    row = await conn.fetchrow(
                        'SELECT COUNT(*) as total FROM atoms WHERE kb_id = $1 AND status = $2',
                        kb_id, 'active'
                    )
                else:
                    row = await conn.fetchrow(
                        'SELECT COUNT(*) as total FROM atoms WHERE status = $1',
                        'active'
                    )
                stats['total_atoms'] = row['total']

                # 有嵌入的原子数
                if kb_id:
                    row = await conn.fetchrow(
                        'SELECT COUNT(*) as count FROM atoms WHERE kb_id = $1 '
                        'AND embedding IS NOT NULL AND status = $2',
                        kb_id, 'active'
                    )
                else:
                    row = await conn.fetchrow(
                        'SELECT COUNT(*) as count FROM atoms '
                        'WHERE embedding IS NOT NULL AND status = $1',
                        'active'
                    )
                stats['atoms_with_embedding'] = row['count']

                # 按类型统计
                if kb_id:
                    rows = await conn.fetch(
                        'SELECT type, COUNT(*) as count FROM atoms '
                        'WHERE kb_id = $1 AND status = $2 GROUP BY type',
                        kb_id, 'active'
                    )
                else:
                    rows = await conn.fetch(
                        'SELECT type, COUNT(*) as count FROM atoms '
                        'WHERE status = $1 GROUP BY type',
                        'active'
                    )
                stats['by_type'] = {row['type']: row['count'] for row in rows}

                return stats

        try:
            return await self._execute_with_retry(_stats)
        except Exception as e:
            logger.error(f"Get stats failed: {e}")
            return {}

    # ========== 工具方法 ==========

    def _build_tsquery(self, query: str) -> str:
        """构建传入 plainto_tsquery 的查询字符串。

        plainto_tsquery 会自动处理所有特殊字符和语言分词，
        因此这里只需 strip 并保证非空即可。
        """
        q = query.strip()
        if not q:
            raise ValueError("查询字符串不能为空")
        return q

    def _contains_chinese(self, text: str) -> bool:
        """检查文本是否包含中文"""
        return bool(re.search(r'[一-鿿]', text))

    def _apply_filters(
        self,
        sql: str,
        params: List[Any],
        param_idx: int,
        kb_id: Optional[int],
        filters: Optional[SearchFilters],
    ) -> Tuple[str, List[Any], int]:
        """应用过滤条件到 SQL 查询

        Args:
            sql: SQL 查询字符串
            params: 参数列表
            param_idx: 当前参数索引
            kb_id: 知识库 ID
            filters: 过滤条件

        Returns:
            (修改后的 SQL, 参数列表, 新参数索引)
        """
        # 知识库过滤
        if kb_id:
            sql += f" AND a.kb_id = ${param_idx}"
            params.append(kb_id)
            param_idx += 1

        # 其他过滤条件
        if filters:
            # 原子类型
            if filters.atom_type:
                sql += f" AND a.type = ${param_idx}"
                params.append(filters.atom_type)
                param_idx += 1

            # 标签过滤（JSONB 包含）
            if filters.tags:
                sql += f" AND a.metadata->'tags' @> ${param_idx}::jsonb"
                params.append(json.dumps(filters.tags))
                param_idx += 1

            # 作者过滤
            if filters.author_id:
                sql += f" AND a.author_id = ${param_idx}"
                params.append(filters.author_id)
                param_idx += 1

            # 日期范围
            if filters.date_from:
                sql += f" AND a.created_at >= ${param_idx}"
                params.append(filters.date_from)
                param_idx += 1

            if filters.date_to:
                sql += f" AND a.created_at <= ${param_idx}"
                params.append(filters.date_to)
                param_idx += 1

            # 状态
            if filters.status:
                sql += f" AND a.status = ${param_idx}"
                params.append(filters.status)
                param_idx += 1

            # 置信度
            if filters.min_confidence is not None:
                sql += f" AND (a.metadata->>'confidence')::float >= ${param_idx}"
                params.append(filters.min_confidence)
                param_idx += 1

        return sql, params, param_idx

    def _row_to_result(self, row: Any, match_type: str) -> SearchResult:
        """将数据库行转换为 SearchResult

        Args:
            row: asyncpg Record
            match_type: 匹配类型

        Returns:
            SearchResult 对象
        """
        raw_meta = row.get('metadata') or {}
        if isinstance(raw_meta, str):
            try:
                metadata = json.loads(raw_meta)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        else:
            metadata = raw_meta

        return SearchResult(
            atom_id=row.get('atom_id') or row.get('id') or 0,
            slug=row.get('slug') or '',
            title=row['title'],
            content=row['content'],
            score=float(row.get('rank', 0) or row.get('similarity', 0)),
            highlights=[row.get('highlight')] if row.get('highlight') else [],
            metadata=metadata,
            kb_id=row.get('kb_id'),
            kb_name=row.get('kb_name'),
            atom_type=row.get('atom_type'),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            match_type=match_type,
        )

    # ========== 缓存管理 ==========

    def _get_cache_key(self, *args) -> str:
        """生成缓存键"""
        parts = [str(arg) for arg in args if arg is not None]
        return ':'.join(parts)

    def _get_from_cache(self, key: str) -> Optional[List[SearchResult]]:
        """从缓存获取结果"""
        if key not in self._cache:
            return None

        cached_data, cached_ts = self._cache[key]
        if time.monotonic() - cached_ts > self.cache_ttl:
            del self._cache[key]
            return None

        return cached_data

    def _set_cache(self, key: str, results: List[Any]) -> None:
        """设置缓存"""
        self._cache[key] = (results, time.monotonic())

        # 清理过期缓存（超过 1000 条时）
        if len(self._cache) > 1000:
            now = time.monotonic()
            expired_keys = [
                k for k, (_, t) in self._cache.items()
                if now - t > self.cache_ttl
            ]
            for k in expired_keys:
                del self._cache[k]

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()

    # ========== 重试机制 ==========

    async def _execute_with_retry(
        self,
        operation: Any,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ) -> Any:
        """带重试的操作执行

        Args:
            operation: 异步操作函数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）

        Returns:
            操作结果
        """
        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))

        raise last_error if last_error else RuntimeError("Operation failed")

    # ========== 解释查询 ==========

    async def explain_search(
        self,
        query: str,
        kb_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """解释搜索查询（调试用）

        Returns:
            查询解释信息，包括 tsquery 解析结果
        """
        ts_query = self._build_tsquery(query)

        async def _explain():
            async with self.pool.acquire() as conn:
                # 解释 tsquery
                row = await conn.fetchrow(
                    "SELECT plainto_tsquery('simple', $1) as tsquery, "
                    "to_tsquery('english', $1) as tsquery_en",
                    ts_query
                )

                return {
                    'original_query': query,
                    'tsquery': ts_query,
                    'parsed_tsquery': str(row.get('tsquery', '')),
                    'parsed_tsquery_en': str(row.get('tsquery_en', '')),
                    'kb_id': kb_id,
                    'use_chinese_parser': self.use_chinese_parser,
                }

        try:
            return await self._execute_with_retry(_explain)
        except Exception as e:
            logger.error(f"Explain search failed: {e}")
            return {
                'original_query': query,
                'error': str(e),
            }