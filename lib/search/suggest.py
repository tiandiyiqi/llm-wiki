"""搜索联想增强模块

提供多种搜索联想来源：
- 前缀匹配（prefix）：基于标题的 LIKE 前缀匹配
- 模糊匹配（fuzzy）：基于 pg_trgm 相似度的模糊搜索
- 热门搜索词（popular）：基于 search_history 统计
- 搜索历史（history）：用户个人搜索历史

使用示例:
    from lib.search.suggest import SearchSuggester, SuggestConfig

    suggester = SearchSuggester()
    results = await suggester.suggest(pool, "mach", kb_id=1, limit=10)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SuggestionType(str, Enum):
    """联想建议类型

    Attributes:
        PREFIX: 前缀匹配结果
        FUZZY: pg_trgm 模糊匹配结果
        POPULAR: 热门搜索词
        HISTORY: 用户搜索历史
    """

    PREFIX = "prefix"
    FUZZY = "fuzzy"
    POPULAR = "popular"
    HISTORY = "history"


@dataclass(frozen=True)
class SuggestionResult:
    """联想建议结果

    Attributes:
        text: 建议文本
        suggestion_type: 建议类型
        score: 相关性得分（0-1）
        source: 来源描述（如知识库名称）
        metadata: 额外元数据
    """

    text: str
    suggestion_type: SuggestionType
    score: float = 0.0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "text": self.text,
            "suggestion_type": self.suggestion_type.value,
            "score": self.score,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class SuggestConfig:
    """联想配置

    Attributes:
        min_prefix_length: 最小前缀长度（低于此值不触发联想）
        similarity_threshold: pg_trgm 相似度阈值（0-1）
        popular_days: 热门搜索词统计天数
        max_history_days: 搜索历史最大天数
        prefix_weight: 前缀匹配结果权重
        fuzzy_weight: 模糊匹配结果权重
        popular_weight: 热门搜索词权重
        history_weight: 搜索历史权重
    """

    min_prefix_length: int = 1
    similarity_threshold: float = 0.3
    popular_days: int = 30
    max_history_days: int = 90
    prefix_weight: float = 1.0
    fuzzy_weight: float = 0.8
    popular_weight: float = 0.5
    history_weight: float = 0.7


def _validate_prefix(prefix: str, min_length: int = 1) -> str:
    """校验并清理前缀输入

    Args:
        prefix: 原始前缀
        min_length: 最小长度

    Returns:
        清理后的前缀

    Raises:
        ValueError: 前缀为空或长度不足
    """
    if not prefix or not prefix.strip():
        raise ValueError("prefix 不能为空")
    cleaned = prefix.strip()
    if len(cleaned) < min_length:
        raise ValueError(f"prefix 长度不能小于 {min_length}")
    return cleaned


def _validate_limit(limit: int) -> int:
    """校验 limit 参数

    Args:
        limit: 返回数量上限

    Returns:
        校验后的 limit

    Raises:
        ValueError: limit 非正整数
    """
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit 必须为正整数")
    return min(limit, 100)


def _build_kb_filter(
    param_idx: int, kb_id: Optional[int] = None
) -> tuple:
    """构建知识库过滤 SQL 片段

    Args:
        param_idx: 当前参数索引
        kb_id: 知识库 ID

    Returns:
        (sql_fragment, params, new_param_idx)
    """
    if kb_id is None:
        return ("", [], param_idx)
    return (f" AND kb_id = ${param_idx}", [kb_id], param_idx + 1)


class SearchSuggester:
    """搜索联想器

    整合多种联想来源，提供统一的搜索建议接口。
    所有方法均为 async，接受 asyncpg pool 参数。
    """

    async def suggest(
        self,
        pool: Any,
        prefix: str,
        kb_id: Optional[int] = None,
        limit: int = 10,
        config: Optional[SuggestConfig] = None,
    ) -> List[SuggestionResult]:
        """综合联想（合并多种来源）

        按权重合并前缀匹配、模糊匹配、热门搜索词的结果。

        Args:
            pool: asyncpg 连接池
            prefix: 输入前缀
            kb_id: 知识库 ID
            limit: 返回数量上限
            config: 联想配置

        Returns:
            去重并排序后的联想结果列表
        """
        cfg = config or SuggestConfig()
        try:
            cleaned = _validate_prefix(prefix, cfg.min_prefix_length)
        except ValueError:
            return []

        validated_limit = _validate_limit(limit)
        per_source_limit = max(validated_limit * 2, 20)

        try:
            prefix_results, fuzzy_results, popular_results = await _fetch_all_sources(
                pool, cleaned, kb_id, per_source_limit, cfg
            )
        except Exception as e:
            logger.error(f"Comprehensive suggest failed: {e}")
            return []

        merged = _merge_and_deduplicate(
            prefix_results,
            fuzzy_results,
            popular_results,
            cfg,
            validated_limit,
        )
        return merged

    async def suggest_by_prefix(
        self,
        pool: Any,
        prefix: str,
        kb_id: Optional[int] = None,
        limit: int = 5,
    ) -> List[SuggestionResult]:
        """前缀匹配联想

        使用 LIKE 前缀匹配 atoms 表的标题。

        Args:
            pool: asyncpg 连接池
            prefix: 输入前缀
            kb_id: 知识库 ID
            limit: 返回数量上限

        Returns:
            前缀匹配结果列表
        """
        try:
            cleaned = _validate_prefix(prefix)
            validated_limit = _validate_limit(limit)
        except ValueError:
            return []

        try:
            return await _query_prefix(pool, cleaned, kb_id, validated_limit)
        except Exception as e:
            logger.error(f"Prefix suggest failed: {e}")
            return []

    async def suggest_by_fuzzy(
        self,
        pool: Any,
        prefix: str,
        kb_id: Optional[int] = None,
        limit: int = 5,
        similarity_threshold: float = 0.3,
    ) -> List[SuggestionResult]:
        """pg_trgm 模糊匹配联想

        使用 pg_trgm 的相似度搜索替代纯 LIKE 前缀匹配，
        支持中英文混合输入的容错匹配。

        Args:
            pool: asyncpg 连接池
            prefix: 输入前缀
            kb_id: 知识库 ID
            limit: 返回数量上限
            similarity_threshold: 相似度阈值（0-1）

        Returns:
            模糊匹配结果列表
        """
        try:
            cleaned = _validate_prefix(prefix)
            validated_limit = _validate_limit(limit)
            threshold = max(0.0, min(1.0, similarity_threshold))
        except ValueError:
            return []

        try:
            return await _query_fuzzy(
                pool, cleaned, kb_id, validated_limit, threshold
            )
        except Exception as e:
            logger.error(f"Fuzzy suggest failed: {e}")
            return []

    async def suggest_popular(
        self,
        pool: Any,
        kb_id: Optional[int] = None,
        limit: int = 10,
        days: int = 30,
    ) -> List[SuggestionResult]:
        """热门搜索词联想

        基于 search_history 表统计指定天数内的热门搜索词。

        Args:
            pool: asyncpg 连接池
            kb_id: 知识库 ID
            limit: 返回数量上限
            days: 统计天数

        Returns:
            热门搜索词结果列表
        """
        validated_limit = _validate_limit(limit)
        validated_days = max(1, min(365, days))

        try:
            return await _query_popular(pool, kb_id, validated_limit, validated_days)
        except Exception as e:
            logger.error(f"Popular suggest failed: {e}")
            return []

    async def suggest_from_history(
        self,
        pool: Any,
        user_id: str,
        kb_id: Optional[int] = None,
        limit: int = 10,
        max_days: int = 90,
    ) -> List[SuggestionResult]:
        """用户搜索历史联想

        从 search_history 表查询用户的搜索历史记录。

        Args:
            pool: asyncpg 连接池
            user_id: 用户 ID
            kb_id: 知识库 ID
            limit: 返回数量上限
            max_days: 最大历史天数

        Returns:
            用户搜索历史结果列表
        """
        if not user_id or not user_id.strip():
            return []

        validated_limit = _validate_limit(limit)
        validated_days = max(1, min(365, max_days))

        try:
            return await _query_history(
                pool, user_id.strip(), kb_id, validated_limit, validated_days
            )
        except Exception as e:
            logger.error(f"History suggest failed: {e}")
            return []

    async def record_search(
        self,
        pool: Any,
        query: str,
        user_id: Optional[str] = None,
        kb_id: Optional[int] = None,
        result_count: int = 0,
    ) -> bool:
        """记录搜索历史

        将搜索行为写入 search_history 表，用于热门搜索词统计
        和用户搜索历史联想。

        Args:
            pool: asyncpg 连接池
            query: 搜索查询字符串
            user_id: 用户 ID（可选）
            kb_id: 知识库 ID（可选）
            result_count: 搜索结果数量

        Returns:
            是否记录成功
        """
        if not query or not query.strip():
            return False

        try:
            return await _insert_search_record(
                pool, query.strip(), user_id, kb_id, result_count
            )
        except Exception as e:
            logger.error(f"Record search failed: {e}")
            return False


# ============================================================
# 内部查询函数
# ============================================================


async def _fetch_all_sources(
    pool: Any,
    prefix: str,
    kb_id: Optional[int],
    per_source_limit: int,
    config: SuggestConfig,
) -> tuple:
    """并行获取所有联想来源

    Args:
        pool: asyncpg 连接池
        prefix: 清理后的前缀
        kb_id: 知识库 ID
        per_source_limit: 每个来源的最大数量
        config: 联想配置

    Returns:
        (prefix_results, fuzzy_results, popular_results)
    """
    import asyncio

    prefix_task = _query_prefix(pool, prefix, kb_id, per_source_limit)
    fuzzy_task = _query_fuzzy(
        pool, prefix, kb_id, per_source_limit, config.similarity_threshold
    )
    popular_task = _query_popular(
        pool, kb_id, per_source_limit, config.popular_days
    )

    return await asyncio.gather(prefix_task, fuzzy_task, popular_task)


async def _query_prefix(
    pool: Any, prefix: str, kb_id: Optional[int], limit: int
) -> List[SuggestionResult]:
    """执行前缀匹配查询

    Args:
        pool: asyncpg 连接池
        prefix: 清理后的前缀
        kb_id: 知识库 ID
        limit: 返回数量上限

    Returns:
        前缀匹配结果列表
    """
    kb_filter, kb_params, next_idx = _build_kb_filter(3, kb_id)

    sql = f"""
        SELECT DISTINCT title
        FROM atoms
        WHERE status = 'active'
          AND (LOWER(title) LIKE LOWER($1) OR LOWER(title) LIKE LOWER($2))
          {kb_filter}
        ORDER BY title
        LIMIT ${next_idx}
    """

    params = [prefix + "%", "%" + prefix + "%"] + kb_params + [limit]

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    return [
        SuggestionResult(
            text=row["title"],
            suggestion_type=SuggestionType.PREFIX,
            score=1.0,
        )
        for row in rows
    ]


async def _query_fuzzy(
    pool: Any,
    prefix: str,
    kb_id: Optional[int],
    limit: int,
    similarity_threshold: float,
) -> List[SuggestionResult]:
    """执行 pg_trgm 模糊匹配查询

    使用 similarity() 函数计算标题与输入的相似度，
    支持中英文混合的容错匹配。

    Args:
        pool: asyncpg 连接池
        prefix: 清理后的前缀
        kb_id: 知识库 ID
        limit: 返回数量上限
        similarity_threshold: 相似度阈值

    Returns:
        模糊匹配结果列表
    """
    kb_filter, kb_params, next_idx = _build_kb_filter(3, kb_id)

    sql = f"""
        SELECT DISTINCT title,
               similarity(title, $1) AS sim_score
        FROM atoms
        WHERE status = 'active'
          AND similarity(title, $1) > $2
          AND title % $1
          {kb_filter}
        ORDER BY sim_score DESC
        LIMIT ${next_idx}
    """

    params = [prefix, similarity_threshold] + kb_params + [limit]

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    return [
        SuggestionResult(
            text=row["title"],
            suggestion_type=SuggestionType.FUZZY,
            score=float(row["sim_score"]),
        )
        for row in rows
    ]


async def _query_popular(
    pool: Any,
    kb_id: Optional[int],
    limit: int,
    days: int,
) -> List[SuggestionResult]:
    """查询热门搜索词

    基于 search_history 表统计指定天数内的热门搜索词，
    按搜索次数降序排列。

    Args:
        pool: asyncpg 连接池
        kb_id: 知识库 ID
        limit: 返回数量上限
        days: 统计天数

    Returns:
        热门搜索词结果列表
    """
    kb_filter, kb_params, next_idx = _build_kb_filter(3, kb_id)

    sql = f"""
        SELECT query, COUNT(*) AS search_count
        FROM search_history
        WHERE created_at >= NOW() - INTERVAL '{days} days'
          AND result_count > 0
          {kb_filter}
        GROUP BY query
        ORDER BY search_count DESC
        LIMIT ${next_idx}
    """

    params = kb_params + [limit]

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    max_count = max((row["search_count"] for row in rows), default=1)

    return [
        SuggestionResult(
            text=row["query"],
            suggestion_type=SuggestionType.POPULAR,
            score=row["search_count"] / max_count if max_count > 0 else 0.0,
            metadata={"search_count": row["search_count"]},
        )
        for row in rows
    ]


async def _query_history(
    pool: Any,
    user_id: str,
    kb_id: Optional[int],
    limit: int,
    max_days: int,
) -> List[SuggestionResult]:
    """查询用户搜索历史

    从 search_history 表查询用户最近的搜索记录，
    按时间倒序排列并去重。

    Args:
        pool: asyncpg 连接池
        user_id: 用户 ID
        kb_id: 知识库 ID
        limit: 返回数量上限
        max_days: 最大历史天数

    Returns:
        用户搜索历史结果列表
    """
    kb_filter, kb_params, next_idx = _build_kb_filter(3, kb_id)

    sql = f"""
        SELECT DISTINCT query,
               MAX(created_at) AS last_searched
        FROM search_history
        WHERE user_id = $1
          AND created_at >= NOW() - INTERVAL '{max_days} days'
          {kb_filter}
        GROUP BY query
        ORDER BY last_searched DESC
        LIMIT ${next_idx}
    """

    params = [user_id] + kb_params + [limit]

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    return _rows_to_history_results(rows, max_days)


def _rows_to_history_results(
    rows: Any, max_days: int
) -> List[SuggestionResult]:
    """将搜索历史行转换为 SuggestionResult 列表

    基于最后搜索时间计算时间衰减分数。

    Args:
        rows: 数据库查询结果行
        max_days: 最大历史天数（用于分数归一化）

    Returns:
        搜索历史结果列表
    """
    now = datetime.now(timezone.utc)
    results: List[SuggestionResult] = []
    for row in rows:
        last_searched = row["last_searched"]
        age_days = (now - last_searched).days if last_searched else max_days
        recency_score = max(0.0, 1.0 - age_days / max_days)

        results.append(
            SuggestionResult(
                text=row["query"],
                suggestion_type=SuggestionType.HISTORY,
                score=recency_score,
                metadata={"last_searched": last_searched.isoformat()},
            )
        )
    return results


async def _insert_search_record(
    pool: Any,
    query: str,
    user_id: Optional[str],
    kb_id: Optional[int],
    result_count: int,
) -> bool:
    """插入搜索历史记录

    Args:
        pool: asyncpg 连接池
        query: 搜索查询字符串
        user_id: 用户 ID
        kb_id: 知识库 ID
        result_count: 搜索结果数量

    Returns:
        是否插入成功
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO search_history (query, user_id, kb_id, result_count)
            VALUES ($1, $2, $3, $4)
            """,
            query,
            user_id,
            kb_id,
            result_count,
        )
    return True


def _apply_weight(
    results: List[SuggestionResult], weight: float
) -> List[SuggestionResult]:
    """对结果列表应用权重系数

    Args:
        results: 原始结果列表
        weight: 权重系数

    Returns:
        应用权重后的新结果列表
    """
    return [
        SuggestionResult(
            text=r.text,
            suggestion_type=r.suggestion_type,
            score=r.score * weight,
            source=r.source,
            metadata=r.metadata,
        )
        for r in results
    ]


def _merge_and_deduplicate(
    prefix_results: List[SuggestionResult],
    fuzzy_results: List[SuggestionResult],
    popular_results: List[SuggestionResult],
    config: SuggestConfig,
    limit: int,
) -> List[SuggestionResult]:
    """合并并去重多来源联想结果

    按权重调整分数后合并，去重（保留得分最高的），
    最终按得分降序排列。

    Args:
        prefix_results: 前缀匹配结果
        fuzzy_results: 模糊匹配结果
        popular_results: 热门搜索词结果
        config: 联想配置（含权重）
        limit: 返回数量上限

    Returns:
        去重并排序后的联想结果列表
    """
    weighted = [
        *_apply_weight(prefix_results, config.prefix_weight),
        *_apply_weight(fuzzy_results, config.fuzzy_weight),
        *_apply_weight(popular_results, config.popular_weight),
    ]

    # 去重：同一文本保留得分最高的
    seen: Dict[str, SuggestionResult] = {}
    for result in weighted:
        key = result.text.lower()
        if key not in seen or result.score > seen[key].score:
            seen = {**seen, key: result}

    sorted_results = sorted(seen.values(), key=lambda r: r.score, reverse=True)
    return sorted_results[:limit]
