"""向量搜索优化测试

测试 VectorIndexManager 和 BatchEmbeddingUpdater：
- 向量索引状态检查
- 按需创建索引
- 索引参数优化
- 批量嵌入更新
- 搜索参数动态调整
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from lib.search.vector_search import (
    VectorSearchConfig,
    VectorIndexType,
    IndexStatus,
    VectorIndexManager,
    BatchEmbeddingUpdater,
)


# ============================================================================
# Mock 工厂
# ============================================================================


def _create_mock_pool():
    """创建 Mock asyncpg 连接池"""
    mock_conn = AsyncMock()
    # 设置 transaction() 异步上下文管理器
    tx_cm = AsyncMock()
    tx_cm.__aenter__ = AsyncMock(return_value=None)
    tx_cm.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=tx_cm)
    # 设置 fetchrow 默认返回
    mock_conn.fetchrow = AsyncMock(return_value={'count': 0})

    mock_pool = MagicMock()
    acquire_cm = MagicMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)
    mock_pool.acquire = MagicMock(return_value=acquire_cm)
    return mock_pool, mock_conn


# ============================================================================
# 测试 VectorSearchConfig
# ============================================================================


class TestVectorSearchConfig:
    """VectorSearchConfig 数据类测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = VectorSearchConfig()
        assert config.embedding_dim == 384
        assert config.index_type == VectorIndexType.IVFFLAT
        assert config.min_vectors_for_index == 1000
        assert config.default_probe == 10
        assert config.ef_search == 40
        assert config.batch_size == 100

    def test_custom_config(self):
        """测试自定义配置"""
        config = VectorSearchConfig(
            embedding_dim=768,
            index_type=VectorIndexType.HNSW,
            min_vectors_for_index=500,
        )
        assert config.embedding_dim == 768
        assert config.index_type == VectorIndexType.HNSW
        assert config.min_vectors_for_index == 500

    def test_config_is_frozen(self):
        """测试配置不可变性"""
        config = VectorSearchConfig(embedding_dim=384)
        with pytest.raises(AttributeError):
            config.embedding_dim = 768

    def test_invalid_embedding_dim(self):
        """测试无效嵌入维度"""
        with pytest.raises(ValueError):
            VectorSearchConfig(embedding_dim=0)

    def test_invalid_probe(self):
        """测试无效 probe 参数"""
        with pytest.raises(ValueError):
            VectorSearchConfig(default_probe=0)


# ============================================================================
# 测试 IndexStatus
# ============================================================================


class TestIndexStatus:
    """IndexStatus 数据类测试"""

    def test_default_status(self):
        """测试默认状态"""
        status = IndexStatus()
        assert status.exists is False
        assert status.is_valid is False
        assert status.vector_count == 0

    def test_to_dict(self):
        """测试转换为字典"""
        status = IndexStatus(
            index_name='idx_test',
            index_type='ivfflat',
            exists=True,
            is_valid=True,
            vector_count=5000,
        )
        d = status.to_dict()
        assert d['index_name'] == 'idx_test'
        assert d['exists'] is True
        assert d['vector_count'] == 5000


# ============================================================================
# 测试 VectorIndexManager
# ============================================================================


class TestVectorIndexManager:
    """VectorIndexManager 向量索引管理器测试"""

    def setup_method(self):
        """测试前准备"""
        self.manager = VectorIndexManager()
        self.mock_pool, self.mock_conn = _create_mock_pool()

    # ------ 向量数量统计 ------

    @pytest.mark.asyncio
    async def test_get_vector_count_basic(self):
        """测试基本向量数量统计"""
        self.mock_conn.fetchrow = AsyncMock(
            return_value={'count': 5000}
        )

        count = await self.manager.get_vector_count(
            self.mock_pool, 'atoms', 'embedding'
        )

        assert count == 5000

    @pytest.mark.asyncio
    async def test_get_vector_count_zero(self):
        """测试零向量数量"""
        self.mock_conn.fetchrow = AsyncMock(
            return_value={'count': 0}
        )

        count = await self.manager.get_vector_count(
            self.mock_pool, 'atoms', 'embedding'
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_vector_count_invalid_table(self):
        """测试无效表名"""
        with pytest.raises(ValueError):
            await self.manager.get_vector_count(
                self.mock_pool, '', 'embedding'
            )

    # ------ 索引状态检查 ------

    @pytest.mark.asyncio
    async def test_check_index_status_exists(self):
        """测试索引存在时的状态"""
        # Mock fetchrow 返回值链
        self.mock_conn.fetchrow = AsyncMock(side_effect=[
            {'count': 5000},  # vector count
            # ivfflat index check: pg_indexes query
            {'indexname': 'idx_atoms_embedding_ivfflat',
             'indexdef': 'CREATE INDEX ... USING ivfflat'},
            # is_valid check
            {'indisvalid': True},
        ])

        status = await self.manager.check_index_status(
            self.mock_pool, 'atoms', 'embedding'
        )

        assert status.exists is True

    @pytest.mark.asyncio
    async def test_check_index_status_not_exists(self):
        """测试索引不存在时的状态"""
        self.mock_conn.fetchrow = AsyncMock(side_effect=[
            {'count': 5000},  # vector count
            None,  # no ivfflat index in pg_indexes
            None,  # no hnsw index in pg_indexes
        ])

        status = await self.manager.check_index_status(
            self.mock_pool, 'atoms', 'embedding'
        )

        assert status.exists is False

    # ------ 按需创建索引 ------

    @pytest.mark.asyncio
    async def test_create_index_if_needed_enough_vectors(self):
        """测试向量数量足够时创建索引"""
        # Mock: no existing index, 5000 vectors
        self.mock_conn.fetchrow = AsyncMock(side_effect=[
            {'count': 5000},  # vector count
            None,  # no ivfflat index
            None,  # no hnsw index
        ])
        self.mock_conn.execute = AsyncMock(return_value=None)

        config = VectorSearchConfig(min_vectors_for_index=1000)
        created = await self.manager.create_index_if_needed(
            self.mock_pool, 'atoms', 'embedding', config
        )

        assert created is True

    @pytest.mark.asyncio
    async def test_create_index_if_needed_too_few_vectors(self):
        """测试向量数量不足时不创建索引"""
        self.mock_conn.fetchrow = AsyncMock(side_effect=[
            {'count': 500},  # vector count
            None,  # no ivfflat index
            None,  # no hnsw index
        ])

        config = VectorSearchConfig(min_vectors_for_index=1000)
        created = await self.manager.create_index_if_needed(
            self.mock_pool, 'atoms', 'embedding', config
        )

        assert created is False

    @pytest.mark.asyncio
    async def test_create_index_already_exists(self):
        """测试索引已存在时不创建"""
        self.mock_conn.fetchrow = AsyncMock(side_effect=[
            {'count': 5000},  # vector count
            # existing ivfflat index
            {'indexname': 'idx_atoms_embedding_ivfflat',
             'indexdef': 'CREATE INDEX ... USING ivfflat'},
            {'indisvalid': True},  # is_valid check
        ])

        config = VectorSearchConfig()
        created = await self.manager.create_index_if_needed(
            self.mock_pool, 'atoms', 'embedding', config
        )

        assert created is False

    # ------ 重建索引 ------

    @pytest.mark.asyncio
    async def test_rebuild_index(self):
        """测试重建索引"""
        # First call: check status (index exists)
        # Second call: drop index, then create
        self.mock_conn.fetchrow = AsyncMock(side_effect=[
            {'count': 5000},  # vector count for check
            {'indexname': 'idx_atoms_embedding_ivfflat',
             'indexdef': 'CREATE INDEX ... USING ivfflat'},
            {'indisvalid': True},  # is_valid check
            {'count': 5000},  # vector count for rebuild
            None,  # no ivfflat after drop
            None,  # no hnsw
        ])
        self.mock_conn.execute = AsyncMock(return_value=None)

        config = VectorSearchConfig()
        rebuilt = await self.manager.rebuild_index(
            self.mock_pool, 'atoms', 'embedding', config
        )

        assert rebuilt is True

    # ------ 参数优化 ------

    def test_compute_optimal_lists_small(self):
        """测试小数据量 lists 参数"""
        lists = self.manager.compute_optimal_lists(1000)
        assert lists >= 10
        assert lists <= 100

    def test_compute_optimal_lists_medium(self):
        """测试中等数据量 lists 参数"""
        lists = self.manager.compute_optimal_lists(100000)
        assert lists >= 100
        assert lists <= 500

    def test_compute_optimal_lists_large(self):
        """测试大数据量 lists 参数"""
        lists = self.manager.compute_optimal_lists(1000000)
        assert lists >= 500
        assert lists <= 2000

    def test_compute_optimal_probe_small(self):
        """测试小数据量 probe 参数"""
        probe = self.manager.compute_optimal_probe(1000)
        assert probe >= 1
        assert probe <= 20

    def test_compute_optimal_probe_large(self):
        """测试大数据量 probe 参数"""
        probe = self.manager.compute_optimal_probe(1000000)
        assert probe >= 10
        assert probe <= 100

    def test_compute_optimal_probe_zero(self):
        """测试零向量时 probe 参数"""
        probe = self.manager.compute_optimal_probe(0)
        assert probe >= 1


# ============================================================================
# 测试 BatchEmbeddingUpdater
# ============================================================================


class TestBatchEmbeddingUpdater:
    """BatchEmbeddingUpdater 批量嵌入更新器测试"""

    def setup_method(self):
        """测试前准备"""
        self.updater = BatchEmbeddingUpdater()
        self.mock_pool, self.mock_conn = _create_mock_pool()

    # ------ 单个更新 ------

    @pytest.mark.asyncio
    async def test_update_single_basic(self):
        """测试基本单个更新"""
        self.mock_conn.execute = AsyncMock(
            return_value='UPDATE 1'
        )

        embedding = [0.1] * 384
        # 不返回 dict，而是直接执行
        await self.updater.update_single(
            self.mock_pool, atom_id=1, embedding=embedding
        )

        self.mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_single_invalid_dimension(self):
        """测试无效维度嵌入"""
        embedding = [0.1] * 128  # 错误维度

        with pytest.raises(ValueError):
            await self.updater.update_single(
                self.mock_pool, atom_id=1, embedding=embedding,
            )

    @pytest.mark.asyncio
    async def test_update_single_empty_embedding(self):
        """测试空嵌入"""
        with pytest.raises(ValueError):
            await self.updater.update_single(
                self.mock_pool, atom_id=1, embedding=[]
            )

    @pytest.mark.asyncio
    async def test_update_single_invalid_atom_id(self):
        """测试无效 atom_id"""
        embedding = [0.1] * 384

        with pytest.raises(ValueError):
            await self.updater.update_single(
                self.mock_pool, atom_id=0, embedding=embedding,
            )

    # ------ 批量更新 ------

    @pytest.mark.asyncio
    async def test_update_batch_basic(self):
        """测试基本批量更新"""
        self.mock_conn.execute = AsyncMock(return_value='UPDATE 1')

        atom_ids = [1, 2, 3]
        embeddings = [[0.1] * 384, [0.2] * 384, [0.3] * 384]

        count = await self.updater.update_batch(
            self.mock_pool, atom_ids, embeddings, batch_size=2
        )

        assert count == 3

    @pytest.mark.asyncio
    async def test_update_batch_empty(self):
        """测试空批量更新"""
        with pytest.raises(ValueError):
            await self.updater.update_batch(
                self.mock_pool, [], [], batch_size=100
            )

    @pytest.mark.asyncio
    async def test_update_batch_mismatched_lengths(self):
        """测试 ID 和嵌入数量不匹配"""
        atom_ids = [1, 2]
        embeddings = [[0.1] * 384]

        with pytest.raises(ValueError):
            await self.updater.update_batch(
                self.mock_pool, atom_ids, embeddings, batch_size=100
            )

    @pytest.mark.asyncio
    async def test_update_batch_respects_batch_size(self):
        """测试批量大小限制"""
        self.mock_conn.execute = AsyncMock(return_value='UPDATE 1')

        atom_ids = list(range(1, 11))
        embeddings = [[0.1] * 384 for _ in range(10)]

        count = await self.updater.update_batch(
            self.mock_pool, atom_ids, embeddings, batch_size=3
        )

        assert count == 10
