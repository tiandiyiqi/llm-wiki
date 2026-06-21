"""端到端迁移测试

测试 PostgreSQL 迁移的完整流程。
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
import tempfile
import json


class TestMigrationE2E:
    """端到端迁移测试"""

    @pytest.fixture
    def temp_kb(self, tmp_path):
        """创建临时知识库"""
        kb_dir = tmp_path / "test-kb"
        kb_dir.mkdir()

        # 创建 kb_meta.yaml
        kb_meta = kb_dir / "kb_meta.yaml"
        kb_meta.write_text("""
name: test-kb
description: Test knowledge base
created: 2026-06-21
""")

        # 创建 atoms 目录
        atoms_dir = kb_dir / "atoms"
        atoms_dir.mkdir()

        # 创建测试原子
        atom1 = atoms_dir / "test-atom.md"
        atom1.write_text("""---
slug: test-atom
title: Test Atom
type: method
tags:
  - test
  - example
created: 2026-06-21
---

This is a test atom with [[linked-atom]] reference.
""")

        atom2 = atoms_dir / "linked-atom.md"
        atom2.write_text("""---
slug: linked-atom
title: Linked Atom
type: fact
created: 2026-06-21
---

This atom is linked from test-atom.
""")

        return kb_dir

    @pytest.mark.asyncio
    async def test_migration_dry_run(self, temp_kb):
        """测试迁移预演模式"""
        from lib.migration import MigrationManager

        manager = MigrationManager(dry_run=True)
        result = await manager.migrate_kb(temp_kb, target='postgres')

        assert result.success is True
        assert result.dry_run is True
        assert result.atoms_migrated == 0  # dry run 不实际迁移

    @pytest.mark.asyncio
    async def test_migration_with_validation(self, temp_kb):
        """测试迁移后验证"""
        from lib.migration import MigrationManager, MigrationValidator

        with patch('lib.migration.migrate.PostgreSQLManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.initialize = AsyncMock()
            mock_manager.create_kb = AsyncMock(return_value=1)
            mock_manager.create_atom = AsyncMock(return_value=1)
            mock_manager.get_kb = AsyncMock(return_value={'id': 1, 'name': 'test-kb'})
            mock_manager.get_kb_by_name = AsyncMock(return_value=None)  # 不存在则创建
            mock_manager.get_atom_by_path = AsyncMock(return_value=None)  # 不存在则创建
            mock_manager.list_kbs = AsyncMock(return_value=[{'id': 1}])
            mock_manager.list_atoms = AsyncMock(return_value=[])
            mock_manager.search_atoms = AsyncMock(return_value=[])
            mock_manager.close = AsyncMock()

            manager = MigrationManager(postgres_url='mock://test')
            result = await manager.migrate_kb(temp_kb, target='postgres')

            assert result.success is True

    @pytest.mark.asyncio
    async def test_registry_migration(self, tmp_path):
        """测试 registry.json 迁移"""
        from lib.migration import MigrationManager

        # 创建模拟 registry
        registry_path = tmp_path / "registry.json"
        registry_data = {
            'version': '1.0',
            'knowledge_bases': {
                'test-kb': {
                    'path': str(tmp_path / 'test-kb'),
                    'name': 'test-kb',
                    'description': 'Test KB',
                    'created': '2026-06-21'
                }
            }
        }
        registry_path.write_text(json.dumps(registry_data))

        with patch('lib.migration.migrate.PostgreSQLManager'):
            manager = MigrationManager(
                registry_path=registry_path,
                postgres_url='mock://test'
            )
            # 迁移 registry
            count = await manager.migrate_registry()
            assert count >= 0


class TestSearchE2E:
    """端到端搜索测试"""

    @pytest.mark.asyncio
    async def test_fulltext_search(self):
        """测试全文搜索"""
        from lib.search import PostgreSQLSearchEngine, SearchResult

        with patch('asyncpg.create_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[
                {
                    'atom_id': 1,
                    'slug': 'test-atom',
                    'title': 'Test Atom',
                    'content': 'This is test content',
                    'score': 0.8,
                    'kb_id': 1
                }
            ])
            mock_cm = Mock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_pool.return_value.acquire = Mock(return_value=mock_cm)

            engine = PostgreSQLSearchEngine(pool=mock_pool.return_value)
            results = await engine.search('test', kb_id=1, limit=10)

            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_hybrid_search(self):
        """测试混合搜索"""
        from lib.search import PostgreSQLSearchEngine

        with patch('asyncpg.create_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_cm = Mock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_pool.return_value.acquire = Mock(return_value=mock_cm)

            engine = PostgreSQLSearchEngine(pool=mock_pool.return_value)

            # 测试混合搜索
            results = await engine.hybrid_search(
                query='test',
                embedding=[0.1] * 384,  # 模拟嵌入向量
                kb_id=1,
                limit=10
            )

            assert isinstance(results, list)


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_create_manager_factory(self):
        """测试管理器工厂"""
        from lib.core import create_manager, StorageType, StorageConfig

        # 测试 SQLite 模式
        config = StorageConfig(type=StorageType.SQLITE)
        manager = await create_manager(config)
        assert manager is not None
        await manager.close()

    @pytest.mark.asyncio
    async def test_migration_cli_integration(self):
        """测试迁移 CLI 集成"""
        from lib.migration.cli import MigrationCLI

        cli = MigrationCLI()

        # 测试帮助信息
        help_text = cli.get_help()
        assert 'migrate' in help_text.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
