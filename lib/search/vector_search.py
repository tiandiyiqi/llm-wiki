"""向量搜索优化模块

提供向量索引管理、批量嵌入更新和搜索参数优化功能。

基于 pgvector 扩展，支持 IVFFlat 和 HNSW 两种索引类型：
- IVFFlat：适合 < 1M 向量，lists 参数建议 sqrt(行数)
- HNSW：适合 > 1M 向量，更高精度但内存占用大

使用示例:
    from lib.search.vector_search import VectorSearchConfig, VectorIndexManager

    # 检查索引状态
    status = await VectorIndexManager.check_index_status(pool, 'atoms', 'embedding')

    # 按需创建索引
    config = VectorSearchConfig()
    await VectorIndexManager.create_index_if_needed(pool, 'atoms', 'embedding', config)

    # 批量更新嵌入
    updater = BatchEmbeddingUpdater()
    await updater.update_batch(pool, atom_ids, embeddings)
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VectorIndexType(str, Enum):
    """向量索引类型枚举

    Attributes:
        IVFFLAT: IVFFlat 索引，适合 < 1M 向量
        HNSW: HNSW 索引，适合 > 1M 向量，更高精度
    """
    IVFFLAT = 'ivfflat'
    HNSW = 'hnsw'


@dataclass(frozen=True)
class VectorSearchConfig:
    """向量搜索配置（不可变数据类）

    Attributes:
        embedding_dim: 嵌入维度，默认 384（对应 all-MiniLM-L6-v2）
        index_type: 索引类型（ivfflat/hnsw）
        min_vectors_for_index: 创建索引所需的最小向量数
        default_probe: IVFFlat 默认 probe 参数
        ef_search: HNSW ef_search 参数
        batch_size: 批量嵌入更新大小
    """
    embedding_dim: int = 384
    index_type: VectorIndexType = VectorIndexType.IVFFLAT
    min_vectors_for_index: int = 1000
    default_probe: int = 10
    ef_search: int = 40
    batch_size: int = 100

    def __post_init__(self) -> None:
        """校验配置参数"""
        if self.embedding_dim <= 0:
            raise ValueError(f"embedding_dim 必须为正数，当前值: {self.embedding_dim}")
        if self.min_vectors_for_index < 0:
            raise ValueError(
                f"min_vectors_for_index 不能为负数，当前值: {self.min_vectors_for_index}"
            )
        if self.default_probe <= 0:
            raise ValueError(f"default_probe 必须为正数，当前值: {self.default_probe}")
        if self.ef_search <= 0:
            raise ValueError(f"ef_search 必须为正数，当前值: {self.ef_search}")
        if self.batch_size <= 0:
            raise ValueError(f"batch_size 必须为正数，当前值: {self.batch_size}")


@dataclass(frozen=True)
class IndexStatus:
    """向量索引状态（不可变数据类）

    Attributes:
        index_name: 索引名称
        index_type: 索引类型
        exists: 索引是否存在
        is_valid: 索引是否有效（非 invalid 状态）
        vector_count: 表中非空向量数量
    """
    index_name: str = ''
    index_type: str = ''
    exists: bool = False
    is_valid: bool = False
    vector_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'index_name': self.index_name,
            'index_type': self.index_type,
            'exists': self.exists,
            'is_valid': self.is_valid,
            'vector_count': self.vector_count,
        }


class VectorIndexManager:
    """向量索引管理器

    提供向量索引的检查、创建、重建功能，
    并根据数据量动态计算最优索引参数。

    所有方法均为类方法，无需实例化。
    """

    @staticmethod
    def _build_index_name(table_name: str, column_name: str) -> str:
        """构建索引名称

        Args:
            table_name: 表名
            column_name: 列名

        Returns:
            索引名称字符串
        """
        return f'idx_{table_name}_{column_name}_ivfflat'

    @staticmethod
    def _build_hnsw_index_name(table_name: str, column_name: str) -> str:
        """构建 HNSW 索引名称

        Args:
            table_name: 表名
            column_name: 列名

        Returns:
            HNSW 索引名称字符串
        """
        return f'idx_{table_name}_{column_name}_hnsw'

    @staticmethod
    def compute_optimal_lists(count: int) -> int:
        """计算 IVFFlat 最优 lists 参数

        经验公式：lists = sqrt(行数)，并设置合理上下限。

        Args:
            count: 向量数量

        Returns:
            最优 lists 参数值
        """
        if count <= 0:
            return 1
        lists = int(math.sqrt(count))
        return max(1, min(lists, 4096))

    @staticmethod
    def compute_optimal_probe(count: int) -> int:
        """计算 IVFFlat 最优 probe 参数

        经验公式：probe = lists / 10，并设置合理上下限。
        probe 越大搜索越精确但越慢。

        Args:
            count: 向量数量

        Returns:
            最优 probe 参数值
        """
        if count <= 0:
            return 1
        lists = VectorIndexManager.compute_optimal_lists(count)
        probe = max(1, lists // 10)
        return min(probe, lists)

    @staticmethod
    async def get_vector_count(
        pool: Any,
        table_name: str,
        column_name: str,
    ) -> int:
        """获取表中非空向量数量

        Args:
            pool: asyncpg 连接池
            table_name: 表名
            column_name: 向量列名

        Returns:
            非空向量数量

        Raises:
            ValueError: 表名或列名为空
        """
        _validate_table_column(table_name, column_name)

        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    f'SELECT COUNT(*) as count FROM {table_name} '
                    f'WHERE {column_name} IS NOT NULL'
                )
                return row['count'] if row else 0
        except Exception as e:
            logger.error(f"获取向量数量失败: {e}")
            raise

    @staticmethod
    async def check_index_status(
        pool: Any,
        table_name: str,
        column_name: str,
    ) -> IndexStatus:
        """检查向量索引状态

        查询 pg_indexes 系统表获取索引信息，
        同时检查索引是否处于 invalid 状态。

        Args:
            pool: asyncpg 连接池
            table_name: 表名
            column_name: 向量列名

        Returns:
            IndexStatus 对象

        Raises:
            ValueError: 表名或列名为空
        """
        _validate_table_column(table_name, column_name)

        try:
            async with pool.acquire() as conn:
                return await _resolve_index_status(conn, table_name, column_name)
        except Exception as e:
            logger.error(f"检查索引状态失败: {e}")
            raise

    @staticmethod
    async def create_index_if_needed(
        pool: Any,
        table_name: str,
        column_name: str,
        config: Optional[VectorSearchConfig] = None,
    ) -> bool:
        """按需创建向量索引

        当向量数量达到 min_vectors_for_index 阈值时自动创建索引。
        如果索引已存在且有效，则跳过创建。

        Args:
            pool: asyncpg 连接池
            table_name: 表名
            column_name: 向量列名
            config: 向量搜索配置，为 None 时使用默认配置

        Returns:
            是否创建了新索引

        Raises:
            ValueError: 表名或列名为空
        """
        _validate_table_column(table_name, column_name)
        cfg = config or VectorSearchConfig()

        try:
            status = await VectorIndexManager.check_index_status(pool, table_name, column_name)

            if status.exists and status.is_valid:
                logger.info(f"向量索引已存在且有效: {status.index_name}")
                return False

            if status.vector_count < cfg.min_vectors_for_index:
                logger.info(
                    f"向量数量不足，跳过索引创建: "
                    f"{status.vector_count} < {cfg.min_vectors_for_index}"
                )
                return False

            await _create_vector_index(pool, table_name, column_name, cfg, status.vector_count)
            return True
        except Exception as e:
            logger.error(f"创建向量索引失败: {e}")
            raise

    @staticmethod
    async def rebuild_index(
        pool: Any,
        table_name: str,
        column_name: str,
        config: Optional[VectorSearchConfig] = None,
    ) -> bool:
        """重建向量索引

        先删除旧索引（如果存在），再根据当前数据量创建新索引。
        适用于数据量大幅变化后需要调整索引参数的场景。

        Args:
            pool: asyncpg 连接池
            table_name: 表名
            column_name: 向量列名
            config: 向量搜索配置，为 None 时使用默认配置

        Returns:
            是否成功重建索引

        Raises:
            ValueError: 表名或列名为空
        """
        _validate_table_column(table_name, column_name)
        cfg = config or VectorSearchConfig()

        try:
            status = await VectorIndexManager.check_index_status(pool, table_name, column_name)

            if status.exists:
                await _drop_index(pool, status.index_name)
                logger.info(f"已删除旧索引: {status.index_name}")

            if status.vector_count < cfg.min_vectors_for_index:
                logger.info(
                    f"向量数量不足，跳过索引重建: "
                    f"{status.vector_count} < {cfg.min_vectors_for_index}"
                )
                return False

            await _create_vector_index(pool, table_name, column_name, cfg, status.vector_count)
            return True
        except Exception as e:
            logger.error(f"重建向量索引失败: {e}")
            raise


class BatchEmbeddingUpdater:
    """批量嵌入更新器

    提供单个和批量更新向量嵌入的功能，
    支持分批提交以避免单次事务过大。
    """

    def __init__(self, config: Optional[VectorSearchConfig] = None) -> None:
        """初始化批量嵌入更新器

        Args:
            config: 向量搜索配置，为 None 时使用默认配置
        """
        self._config = config or VectorSearchConfig()

    async def update_single(
        self,
        pool: Any,
        atom_id: int,
        embedding: List[float],
    ) -> None:
        """更新单个原子的嵌入向量

        Args:
            pool: asyncpg 连接池
            atom_id: 原子 ID
            embedding: 嵌入向量

        Raises:
            ValueError: atom_id 无效或 embedding 维度不匹配
        """
        _validate_atom_id(atom_id)
        _validate_embedding(embedding, self._config.embedding_dim)

        embedding_str = _embedding_to_str(embedding)

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    'UPDATE atoms SET embedding = $1::vector WHERE id = $2',
                    embedding_str,
                    atom_id,
                )
                logger.debug(f"已更新原子 {atom_id} 的嵌入向量")
        except Exception as e:
            logger.error(f"更新原子 {atom_id} 嵌入向量失败: {e}")
            raise

    async def update_batch(
        self,
        pool: Any,
        atom_ids: List[int],
        embeddings: List[List[float]],
        batch_size: Optional[int] = None,
    ) -> int:
        """批量更新原子的嵌入向量

        将更新操作按 batch_size 分批执行，
        每批使用独立事务，避免单次事务过大。

        Args:
            pool: asyncpg 连接池
            atom_ids: 原子 ID 列表
            embeddings: 嵌入向量列表（与 atom_ids 一一对应）
            batch_size: 批量大小，为 None 时使用配置值

        Returns:
            成功更新的数量

        Raises:
            ValueError: atom_ids 为空、长度不匹配或 embedding 维度不匹配
        """
        _validate_batch_inputs(atom_ids, embeddings, self._config.embedding_dim)
        size = batch_size or self._config.batch_size
        updated_count = 0

        pairs = list(zip(atom_ids, embeddings))
        batches = _split_into_batches(pairs, size)

        for batch in batches:
            count = await _execute_batch_update(pool, batch, self._config.embedding_dim)
            updated_count += count

        logger.info(f"批量更新完成: {updated_count}/{len(atom_ids)}")
        return updated_count


# ========== 内部辅助函数 ==========


def _validate_table_column(table_name: str, column_name: str) -> None:
    """校验表名和列名

    Args:
        table_name: 表名
        column_name: 列名

    Raises:
        ValueError: 表名或列名为空
    """
    if not table_name or not table_name.strip():
        raise ValueError("表名不能为空")
    if not column_name or not column_name.strip():
        raise ValueError("列名不能为空")


def _validate_atom_id(atom_id: int) -> None:
    """校验原子 ID

    Args:
        atom_id: 原子 ID

    Raises:
        ValueError: atom_id 无效
    """
    if not isinstance(atom_id, int) or atom_id <= 0:
        raise ValueError(f"atom_id 必须为正整数，当前值: {atom_id}")


def _validate_embedding(embedding: List[float], expected_dim: int) -> None:
    """校验嵌入向量

    Args:
        embedding: 嵌入向量
        expected_dim: 期望维度

    Raises:
        ValueError: embedding 为空或维度不匹配
    """
    if not embedding:
        raise ValueError("embedding 不能为空")
    if len(embedding) != expected_dim:
        raise ValueError(
            f"embedding 维度不匹配: 期望 {expected_dim}，实际 {len(embedding)}"
        )


def _validate_batch_inputs(
    atom_ids: List[int],
    embeddings: List[List[float]],
    expected_dim: int,
) -> None:
    """校验批量更新输入

    Args:
        atom_ids: 原子 ID 列表
        embeddings: 嵌入向量列表
        expected_dim: 期望维度

    Raises:
        ValueError: 输入无效
    """
    if not atom_ids:
        raise ValueError("atom_ids 不能为空")
    if len(atom_ids) != len(embeddings):
        raise ValueError(
            f"atom_ids 和 embeddings 长度不匹配: "
            f"{len(atom_ids)} != {len(embeddings)}"
        )
    for i, (aid, emb) in enumerate(zip(atom_ids, embeddings)):
        if not isinstance(aid, int) or aid <= 0:
            raise ValueError(f"atom_ids[{i}] 无效: {aid}")
        if not emb:
            raise ValueError(f"embeddings[{i}] 不能为空")
        if len(emb) != expected_dim:
            raise ValueError(
                f"embeddings[{i}] 维度不匹配: 期望 {expected_dim}，实际 {len(emb)}"
            )


def _embedding_to_str(embedding: List[float]) -> str:
    """将嵌入向量转换为 PostgreSQL vector 字符串格式

    Args:
        embedding: 嵌入向量

    Returns:
        格式化的向量字符串，如 '[0.1,0.2,0.3]'
    """
    return '[' + ','.join(str(x) for x in embedding) + ']'


def _split_into_batches(
    pairs: List[Tuple[int, List[float]]],
    batch_size: int,
) -> List[List[Tuple[int, List[float]]]]:
    """将数据对列表按批次大小分割

    Args:
        pairs: (atom_id, embedding) 数据对列表
        batch_size: 批次大小

    Returns:
        分批后的列表
    """
    return [
        pairs[i:i + batch_size]
        for i in range(0, len(pairs), batch_size)
    ]


async def _fetch_vector_count(
    conn: Any,
    table_name: str,
    column_name: str,
) -> int:
    """从连接中获取向量数量

    Args:
        conn: asyncpg 连接
        table_name: 表名
        column_name: 列名

    Returns:
        非空向量数量
    """
    row = await conn.fetchrow(
        f'SELECT COUNT(*) as count FROM {table_name} '
        f'WHERE {column_name} IS NOT NULL'
    )
    return row['count'] if row else 0


async def _resolve_index_status(
    conn: Any,
    table_name: str,
    column_name: str,
) -> IndexStatus:
    """解析向量索引状态

    依次检查 IVFFlat 和 HNSW 索引是否存在及有效。

    Args:
        conn: asyncpg 连接
        table_name: 表名
        column_name: 列名

    Returns:
        IndexStatus 对象
    """
    vector_count = await _fetch_vector_count(conn, table_name, column_name)

    ivfflat_name = VectorIndexManager._build_index_name(table_name, column_name)
    hnsw_name = VectorIndexManager._build_hnsw_index_name(table_name, column_name)

    ivfflat_row = await _fetch_index_row(conn, table_name, ivfflat_name)
    if ivfflat_row:
        return IndexStatus(
            index_name=ivfflat_name,
            index_type='ivfflat',
            exists=True,
            is_valid=ivfflat_row.get('is_valid', True),
            vector_count=vector_count,
        )

    hnsw_row = await _fetch_index_row(conn, table_name, hnsw_name)
    if hnsw_row:
        return IndexStatus(
            index_name=hnsw_name,
            index_type='hnsw',
            exists=True,
            is_valid=hnsw_row.get('is_valid', True),
            vector_count=vector_count,
        )

    return IndexStatus(
        index_name='',
        index_type='',
        exists=False,
        is_valid=False,
        vector_count=vector_count,
    )


async def _fetch_index_row(
    conn: Any,
    table_name: str,
    index_name: str,
) -> Optional[Dict[str, Any]]:
    """查询索引信息

    Args:
        conn: asyncpg 连接
        table_name: 表名
        index_name: 索引名

    Returns:
        索引信息字典，不存在则返回 None
    """
    row = await conn.fetchrow(
        'SELECT indexname, indexdef FROM pg_indexes '
        'WHERE tablename = $1 AND indexname = $2',
        table_name,
        index_name,
    )
    if not row:
        return None

    is_valid = await _check_index_validity(conn, index_name)
    return {
        'indexname': row['indexname'],
        'indexdef': row['indexdef'],
        'is_valid': is_valid,
    }


async def _check_index_validity(conn: Any, index_name: str) -> bool:
    """检查索引是否有效（非 invalid 状态）

    CONCURRENTLY 创建失败的索引会标记为 invalid。

    Args:
        conn: asyncpg 连接
        index_name: 索引名

    Returns:
        索引是否有效
    """
    row = await conn.fetchrow(
        'SELECT indisvalid FROM pg_index i '
        'JOIN pg_class c ON i.indexrelid = c.oid '
        'WHERE c.relname = $1',
        index_name,
    )
    if not row:
        return False
    return row['indisvalid']


async def _drop_index(pool: Any, index_name: str) -> None:
    """删除索引

    Args:
        pool: asyncpg 连接池
        index_name: 索引名
    """
    async with pool.acquire() as conn:
        await conn.execute(f'DROP INDEX IF EXISTS {index_name}')


async def _create_vector_index(
    pool: Any,
    table_name: str,
    column_name: str,
    config: VectorSearchConfig,
    vector_count: int,
) -> None:
    """根据配置创建向量索引

    Args:
        pool: asyncpg 连接池
        table_name: 表名
        column_name: 列名
        config: 向量搜索配置
        vector_count: 当前向量数量
    """
    if config.index_type == VectorIndexType.HNSW:
        await _create_hnsw_index(pool, table_name, column_name)
    else:
        await _create_ivfflat_index(pool, table_name, column_name, vector_count)


async def _create_ivfflat_index(
    pool: Any,
    table_name: str,
    column_name: str,
    vector_count: int,
) -> None:
    """创建 IVFFlat 向量索引

    Args:
        pool: asyncpg 连接池
        table_name: 表名
        column_name: 列名
        vector_count: 向量数量（用于计算 lists 参数）
    """
    lists = VectorIndexManager.compute_optimal_lists(vector_count)
    index_name = VectorIndexManager._build_index_name(table_name, column_name)

    async with pool.acquire() as conn:
        await conn.execute(
            f'CREATE INDEX {index_name} ON {table_name} '
            f'USING ivfflat ({column_name} vector_cosine_ops) '
            f'WITH (lists = {lists})'
        )
    logger.info(f"已创建 IVFFlat 索引: {index_name}, lists = {lists}")


async def _create_hnsw_index(
    pool: Any,
    table_name: str,
    column_name: str,
) -> None:
    """创建 HNSW 向量索引

    Args:
        pool: asyncpg 连接池
        table_name: 表名
        column_name: 列名
    """
    index_name = VectorIndexManager._build_hnsw_index_name(table_name, column_name)

    async with pool.acquire() as conn:
        await conn.execute(
            f'CREATE INDEX {index_name} ON {table_name} '
            f'USING hnsw ({column_name} vector_cosine_ops) '
            f"WITH (m = 16, ef_construction = 64)"
        )
    logger.info(f"已创建 HNSW 索引: {index_name}")


async def _execute_batch_update(
    pool: Any,
    batch: List[Tuple[int, List[float]]],
    expected_dim: int,
) -> int:
    """执行单批次嵌入更新

    Args:
        pool: asyncpg 连接池
        batch: (atom_id, embedding) 数据对列表
        expected_dim: 期望维度

    Returns:
        成功更新的数量
    """
    updated = 0
    async with pool.acquire() as conn:
        async with conn.transaction():
            for atom_id, embedding in batch:
                embedding_str = _embedding_to_str(embedding)
                result = await conn.execute(
                    'UPDATE atoms SET embedding = $1::vector WHERE id = $2',
                    embedding_str,
                    atom_id,
                )
                if result and result.endswith('1'):
                    updated += 1
    return updated
