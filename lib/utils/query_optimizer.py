"""查询优化工具.

提供批量加载、预加载等工具，消除 N+1 查询问题。
"""

import logging
from typing import Any, Dict, List, Optional, Set, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class BatchLoader:
    """批量加载器.

    解决 N+1 查询问题的核心工具。
    """

    def __init__(self, db_manager, batch_size: int = 100):
        """初始化批量加载器.

        Args:
            db_manager: 数据库管理器
            batch_size: 批量大小
        """
        self.db_manager = db_manager
        self.batch_size = batch_size
        self._cache: Dict[str, Dict[Any, Any]] = {}

    async def load_many(
        self,
        table: str,
        ids: List[Any],
        key_column: str = 'id',
        columns: Optional[List[str]] = None
    ) -> Dict[Any, Dict]:
        """批量加载记录.

        Args:
            table: 表名
            ids: ID 列表
            key_column: 键列名
            columns: 要加载的列（None 表示所有列）

        Returns:
            {id: record} 字典
        """
        if not ids:
            return {}

        # 去重
        unique_ids = list(set(ids))

        # 构建查询
        select_columns = ', '.join(columns) if columns else '*'

        # 使用 IN 子句批量查询
        query = f"""
            SELECT {select_columns}
            FROM {table}
            WHERE {key_column} = ANY($1)
        """

        results = await self.db_manager.fetch_all(query, unique_ids)

        # 构建 {id: record} 字典
        records = {}
        for record in results:
            key = record[key_column]
            records[key] = record

        return records

    async def load_related(
        self,
        parent_ids: List[Any],
        related_table: str,
        foreign_key: str,
        columns: Optional[List[str]] = None
    ) -> Dict[Any, List[Dict]]:
        """批量加载关联记录（一对多）.

        Args:
            parent_ids: 父记录 ID 列表
            related_table: 关联表名
            foreign_key: 外键列名
            columns: 要加载的列

        Returns:
            {parent_id: [related_records]} 字典
        """
        if not parent_ids:
            return {}

        unique_ids = list(set(parent_ids))
        select_columns = ', '.join(columns) if columns else '*'

        query = f"""
            SELECT {select_columns}
            FROM {related_table}
            WHERE {foreign_key} = ANY($1)
        """

        results = await self.db_manager.fetch_all(query, unique_ids)

        # 构建 {parent_id: [records]} 字典
        related_records: Dict[Any, List[Dict]] = {pid: [] for pid in unique_ids}

        for record in results:
            parent_id = record[foreign_key]
            if parent_id not in related_records:
                related_records[parent_id] = []
            related_records[parent_id].append(record)

        return related_records

    async def load_join(
        self,
        main_table: str,
        join_table: str,
        join_condition: str,
        where_clause: Optional[str] = None,
        where_params: Optional[List] = None
    ) -> List[Dict]:
        """使用 JOIN 一次性加载关联数据.

        Args:
            main_table: 主表名
            join_table: 连接表名
            join_condition: 连接条件
            where_clause: WHERE 子句
            where_params: WHERE 参数

        Returns:
            连接后的记录列表
        """
        query = f"""
            SELECT *
            FROM {main_table} m
            INNER JOIN {join_table} j ON {join_condition}
        """

        if where_clause:
            query += f" WHERE {where_clause}"

        return await self.db_manager.fetch_all(query, *(where_params or []))


def optimize_query(loader_func: Callable) -> Callable:
    """查询优化装饰器.

    自动缓存查询结果，避免重复查询。

    使用方式：
        @optimize_query
        async def get_user(user_id):
            return await db.fetch_one(...)

    Args:
        loader_func: 加载函数

    Returns:
        优化后的函数
    """
    cache: Dict[str, Any] = {}

    @wraps(loader_func)
    async def wrapper(*args, **kwargs):
        # 生成缓存键
        cache_key = str((args, sorted(kwargs.items())))

        # 检查缓存
        if cache_key in cache:
            logger.debug(f"Cache hit for {loader_func.__name__}")
            return cache[cache_key]

        # 执行查询
        result = await loader_func(*args, **kwargs)

        # 缓存结果
        cache[cache_key] = result

        return result

    return wrapper


class QueryOptimizer:
    """查询优化器.

    分析和优化 SQL 查询。
    """

    @staticmethod
    def analyze_query(query: str) -> Dict[str, Any]:
        """分析 SQL 查询.

        Args:
            query: SQL 查询字符串

        Returns:
            分析结果
        """
        analysis = {
            'has_subquery': False,
            'has_join': False,
            'has_aggregate': False,
            'table_count': 0,
            'warnings': [],
        }

        query_upper = query.upper()

        # 检查子查询
        if query_upper.count('SELECT') > 1:
            analysis['has_subquery'] = True
            analysis['warnings'].append('Query contains subqueries, consider using JOINs')

        # 检查 JOIN
        if 'JOIN' in query_upper:
            analysis['has_join'] = True

        # 检查聚合函数
        aggregate_funcs = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']
        for func in aggregate_funcs:
            if func in query_upper:
                analysis['has_aggregate'] = True
                break

        # 统计表数量（简单估计）
        analysis['table_count'] = query_upper.count('FROM') + query_upper.count('JOIN')

        return analysis

    @staticmethod
    def suggest_index(query: str, table: str) -> List[str]:
        """建议创建索引.

        Args:
            query: SQL 查询字符串
            table: 表名

        Returns:
            索引建议列表
        """
        suggestions = []

        query_upper = query.upper()

        # 检查 WHERE 子句中的列
        if 'WHERE' in query_upper:
            suggestions.append(
                f"Consider adding index on columns used in WHERE clause for table '{table}'"
            )

        # 检查 ORDER BY
        if 'ORDER BY' in query_upper:
            suggestions.append(
                f"Consider adding index on columns used in ORDER BY for table '{table}'"
            )

        # 检查 JOIN 条件
        if 'JOIN' in query_upper and 'ON' in query_upper:
            suggestions.append(
                f"Consider adding index on JOIN columns for table '{table}'"
            )

        return suggestions


class NPlusOneDetector:
    """N+1 查询检测器.

    检测代码中的 N+1 查询问题。
    """

    def __init__(self, threshold: int = 10):
        """初始化检测器.

        Args:
            threshold: 触发警告的阈值
        """
        self.threshold = threshold
        self._query_counts: Dict[str, int] = {}

    def record_query(self, query_pattern: str) -> None:
        """记录查询.

        Args:
            query_pattern: 查询模式（去除具体参数）
        """
        self._query_counts[query_pattern] = self._query_counts.get(query_pattern, 0) + 1

        # 检查是否超过阈值
        if self._query_counts[query_pattern] > self.threshold:
            logger.warning(
                f"Potential N+1 query detected: '{query_pattern}' "
                f"executed {self._query_counts[query_pattern]} times"
            )

    def get_report(self) -> Dict[str, int]:
        """获取检测报告.

        Returns:
            查询次数报告
        """
        return dict(self._query_counts)

    def reset(self) -> None:
        """重置计数器."""
        self._query_counts.clear()


# 全局 N+1 检测器
_nplus_one_detector = NPlusOneDetector()


def get_nplus_one_detector() -> NPlusOneDetector:
    """获取全局 N+1 检测器.

    Returns:
        N+1 检测器实例
    """
    return _nplus_one_detector
