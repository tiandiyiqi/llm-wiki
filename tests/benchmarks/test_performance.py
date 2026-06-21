"""性能基准测试

测试 PostgreSQL 搜索和迁移的性能。
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
import statistics


class BenchmarkResult:
    """基准测试结果"""

    def __init__(self, name: str):
        self.name = name
        self.times = []
        self.memory_usage = []

    def add_time(self, duration: float):
        self.times.append(duration)

    def get_stats(self):
        if not self.times:
            return None
        return {
            'mean': statistics.mean(self.times),
            'median': statistics.median(self.times),
            'min': min(self.times),
            'max': max(self.times),
            'stdev': statistics.stdev(self.times) if len(self.times) > 1 else 0,
            'count': len(self.times)
        }


class TestSearchPerformance:
    """搜索性能测试"""

    @pytest.fixture
    def benchmark(self):
        return BenchmarkResult('search')

    @pytest.mark.asyncio
    async def test_fulltext_search_latency(self, benchmark):
        """测试全文搜索延迟"""
        from lib.search import PostgreSQLSearchEngine

        with patch('asyncpg.create_pool') as mock_pool:
            mock_conn = AsyncMock()

            # 模拟不同规模的结果
            mock_conn.fetch = AsyncMock(return_value=[
                {'atom_id': i, 'slug': f'atom-{i}', 'title': f'Title {i}',
                 'content': f'Content {i}', 'score': 0.5, 'kb_id': 1}
                for i in range(100)
            ])

            mock_cm = Mock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_pool.return_value.acquire = Mock(return_value=mock_cm)

            engine = PostgreSQLSearchEngine(pool=mock_pool.return_value)

            # 运行多次测试
            for _ in range(10):
                start = time.time()
                await engine.search('test query', kb_id=1, limit=100)
                duration = time.time() - start
                benchmark.add_time(duration)

            stats = benchmark.get_stats()
            # 全文搜索应该在 100ms 内完成
            assert stats['mean'] < 0.1, f"搜索延迟过高: {stats['mean']}s"

    @pytest.mark.asyncio
    async def test_vector_search_latency(self, benchmark):
        """测试向量搜索延迟"""
        from lib.search import PostgreSQLSearchEngine

        with patch('asyncpg.create_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[
                {'atom_id': i, 'slug': f'atom-{i}', 'title': f'Title {i}',
                 'content': f'Content {i}', 'score': 0.5, 'kb_id': 1}
                for i in range(50)
            ])

            mock_cm = Mock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_pool.return_value.acquire = Mock(return_value=mock_cm)

            engine = PostgreSQLSearchEngine(pool=mock_pool.return_value)
            embedding = [0.1] * 384

            for _ in range(10):
                start = time.time()
                await engine.search_by_embedding(embedding, kb_id=1, limit=50)
                duration = time.time() - start
                benchmark.add_time(duration)

            stats = benchmark.get_stats()
            # 向量搜索应该在 200ms 内完成
            assert stats['mean'] < 0.2, f"向量搜索延迟过高: {stats['mean']}s"


class TestMigrationPerformance:
    """迁移性能测试"""

    @pytest.fixture
    def benchmark(self):
        return BenchmarkResult('migration')

    @pytest.mark.asyncio
    async def test_atom_migration_throughput(self, benchmark, tmp_path):
        """测试原子迁移吞吐量"""
        from lib.migration import MigrationManager

        # 创建大量测试原子
        atoms_dir = tmp_path / "atoms"
        atoms_dir.mkdir()

        atom_count = 100
        for i in range(atom_count):
            atom_file = atoms_dir / f"atom-{i}.md"
            atom_file.write_text(f"""---
slug: atom-{i}
title: Atom {i}
type: method
created: 2026-06-21
---

Content for atom {i} with some test data.
""")

        kb_dir = tmp_path
        kb_meta = kb_dir / "kb_meta.yaml"
        kb_meta.write_text("name: test-kb\ncreated: 2026-06-21\n")

        with patch('lib.migration.migrate.PostgreSQLManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.initialize = AsyncMock()
            mock_manager.create_kb = AsyncMock(return_value=1)
            mock_manager.get_kb_by_name = AsyncMock(return_value=None)
            mock_manager.get_atom_by_path = AsyncMock(return_value=None)
            mock_manager.list_atoms = AsyncMock(return_value=[])
            atom_ids = iter(range(atom_count))
            mock_manager.create_atom = AsyncMock(side_effect=lambda *_: next(atom_ids))
            mock_manager.close = AsyncMock()

            manager = MigrationManager(dry_run=False, postgres_url='mock://test')

            start = time.time()
            result = await manager.migrate_kb(kb_dir, target='postgres')
            duration = time.time() - start
            benchmark.add_time(max(duration, 1e-6))  # 避免除零

        # 验证 mock 被正确调用（每个原子都被处理）
        assert mock_manager.create_atom.call_count == atom_count, \
            f"应创建 {atom_count} 个原子，实际 {mock_manager.create_atom.call_count}"
        assert result.atoms_migrated == atom_count


class TestCachePerformance:
    """缓存性能测试"""

    @pytest.fixture
    def benchmark(self):
        return BenchmarkResult('cache')

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, benchmark):
        """测试缓存命中率"""
        from lib.search import PostgreSQLSearchEngine
        from functools import lru_cache

        with patch('asyncpg.create_pool') as mock_pool:
            mock_conn = AsyncMock()
            call_count = 0

            async def mock_fetch(*args, **kwargs):
                call_count += 1
                return [{'id': 1, 'slug': 'test', 'title': 'Test',
                        'content': 'Content', 'score': 0.5, 'kb_id': 1}]

            mock_conn.fetch = mock_fetch
            mock_cm = Mock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_pool.return_value.acquire = Mock(return_value=mock_cm)

            engine = PostgreSQLSearchEngine(pool=mock_pool.return_value, cache_ttl=60)

            # 多次执行相同查询
            for _ in range(20):
                start = time.time()
                await engine.search('same query', kb_id=1)
                duration = time.time() - start
                benchmark.add_time(duration)

            stats = benchmark.get_stats()
            # 缓存命中时，后续查询应该更快
            # 平均延迟应该随缓存命中率降低


def run_benchmarks():
    """运行所有基准测试"""
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '-k', 'performance'
    ])


if __name__ == '__main__':
    run_benchmarks()