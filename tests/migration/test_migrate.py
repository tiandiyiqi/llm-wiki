"""数据迁移测试

测试 MigrationManager 的迁移执行和回滚机制。
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from lib.migration.migrate import MigrationManager, MigrationResult, MIGRATION_VERSION, MIGRATION_NAME

    _IMPORT_OK = True
except ImportError as _e:
    _IMPORT_OK = False
    _IMPORT_ERROR = str(_e)


@pytest.fixture
def mock_db():
    """Mock PostgreSQLManager"""
    db = AsyncMock()
    db.initialize = AsyncMock()
    db.close = AsyncMock()
    db.create_kb = AsyncMock(return_value=1)
    db.get_kb_by_name = AsyncMock(return_value=None)
    db.update_kb = AsyncMock(return_value=True)
    db.create_atom = AsyncMock(return_value=1)
    db.get_atom_by_path = AsyncMock(return_value=None)
    db.update_atom = AsyncMock(return_value=True)
    db.list_atoms = AsyncMock(return_value=[])
    db.get_atom_count = AsyncMock(return_value=0)
    db.get_kb_stats = AsyncMock(return_value={})
    db.search_atoms = AsyncMock(return_value=[])
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_all = AsyncMock(return_value=[])
    db.execute = AsyncMock(return_value=None)

    # Mock pool
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    db.pool = MagicMock()
    db.pool.acquire = MagicMock(return_value=cm)

    return db


@pytest.fixture
def kb_path(tmp_path):
    """创建临时知识库目录"""
    kb = tmp_path / "test_kb"
    kb.mkdir()
    (kb / "atoms").mkdir()
    (kb / "facts").mkdir()
    return kb


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestMigrationResult:
    """迁移结果测试"""

    def test_migration_result_defaults(self):
        """MigrationResult 默认值"""
        result = MigrationResult(success=False)
        assert result.success is False
        assert result.kb_id is None
        assert result.atoms_migrated == 0
        assert result.atoms_failed == 0
        assert result.errors == []
        assert result.warnings == []
        assert result.dry_run is False

    def test_migration_result_str(self):
        """MigrationResult 字符串表示"""
        result = MigrationResult(success=True, kb_id=1, atoms_migrated=10)
        s = str(result)
        assert "成功" in s
        assert "10" in s

    def test_migration_result_with_errors(self):
        """MigrationResult 包含错误"""
        result = MigrationResult(
            success=False,
            errors=["错误1", "错误2"],
            warnings=["警告1"],
        )
        s = str(result)
        assert "失败" in s
        assert "错误" in s


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestMigrationVersion:
    """迁移版本测试"""

    def test_migration_version_defined(self):
        """迁移版本已定义"""
        assert MIGRATION_VERSION >= 1
        assert MIGRATION_NAME is not None
        assert len(MIGRATION_NAME) > 0


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestMigrationManagerInit:
    """迁移管理器初始化测试"""

    def test_init_defaults(self):
        """默认参数初始化"""
        manager = MigrationManager()
        assert manager.dry_run is False
        assert manager.db is None
        assert manager.postgres_url == ''

    def test_init_dry_run(self):
        """dry_run 模式初始化"""
        manager = MigrationManager(dry_run=True)
        assert manager.dry_run is True

    def test_init_with_registry_path(self, tmp_path):
        """指定 registry 路径"""
        registry = tmp_path / "registry.json"
        manager = MigrationManager(registry_path=registry)
        assert manager.registry_path == registry


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestMigrateKBDryRun:
    """dry-run 模式迁移测试"""

    @pytest.mark.asyncio
    async def test_dry_run_nonexistent_path(self, kb_path):
        """dry-run 路径不存在"""
        manager = MigrationManager(dry_run=True)
        result = await manager.migrate_kb(Path("/nonexistent/path"))
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_dry_run_success(self, kb_path):
        """dry-run 成功"""
        manager = MigrationManager(dry_run=True)
        result = await manager.migrate_kb(kb_path)
        assert result.success is True
        assert result.dry_run is True
        assert result.kb_id == 1


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestMigrateAtoms:
    """原子迁移测试"""

    @pytest.mark.asyncio
    async def test_migrate_atoms_empty_dir(self, kb_path):
        """空 atoms 目录"""
        manager = MigrationManager(dry_run=True)
        success, failed = await manager.migrate_atoms(kb_path, 1)
        assert success == 0
        assert failed == 0

    @pytest.mark.asyncio
    async def test_migrate_atoms_no_dir(self, tmp_path):
        """无 atoms 目录"""
        kb = tmp_path / "kb_no_atoms"
        kb.mkdir()
        manager = MigrationManager(dry_run=True)
        success, failed = await manager.migrate_atoms(kb, 1)
        assert success == 0
        assert failed == 0

    @pytest.mark.asyncio
    async def test_migrate_atoms_with_files(self, kb_path):
        """有原子文件的 dry-run 迁移"""
        atoms_dir = kb_path / "atoms"
        (atoms_dir / "fact-test.md").write_text(
            "---\ntitle: 测试事实\ntype: fact\n---\n\n这是测试内容",
            encoding='utf-8',
        )
        manager = MigrationManager(dry_run=True)
        success, failed = await manager.migrate_atoms(kb_path, 1)
        assert success == 1
        assert failed == 0


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestParseAtomFile:
    """原子文件解析测试"""

    @pytest.mark.asyncio
    async def test_parse_atom_with_frontmatter(self, kb_path):
        """解析带 frontmatter 的原子文件"""
        atoms_dir = kb_path / "atoms"
        atom_file = atoms_dir / "method-test.md"
        atom_file.write_text(
            "---\ntitle: 测试方法\ntype: method\ntags: [python, test]\n---\n\n## 概述\n\n这是测试内容",
            encoding='utf-8',
        )
        manager = MigrationManager(dry_run=True)
        result = await manager._parse_atom_file(atom_file, kb_path, 1)

        assert result is not None
        assert result['title'] == '测试方法'
        assert result['type'] == 'method'
        assert 'python' in result['tags']

    @pytest.mark.asyncio
    async def test_parse_atom_without_frontmatter(self, kb_path):
        """解析无 frontmatter 的原子文件，标题取自文件名"""
        atoms_dir = kb_path / "atoms"
        atom_file = atoms_dir / "simple.md"
        atom_file.write_text("# 简单标题\n\n简单内容", encoding='utf-8')
        manager = MigrationManager(dry_run=True)
        result = await manager._parse_atom_file(atom_file, kb_path, 1)

        assert result is not None
        # 无 frontmatter 时，标题取自文件名 stem
        assert result['title'] == 'simple'
        assert result['type'] == 'method'  # 默认类型

    @pytest.mark.asyncio
    async def test_parse_atom_with_description(self, kb_path):
        """解析带描述的原子文件"""
        atoms_dir = kb_path / "atoms"
        atom_file = atoms_dir / "desc-test.md"
        atom_file.write_text(
            "---\ntitle: 带描述\ndescription: 这是描述\n---\n\n正文",
            encoding='utf-8',
        )
        manager = MigrationManager(dry_run=True)
        result = await manager._parse_atom_file(atom_file, kb_path, 1)

        assert result is not None
        assert result['description'] == '这是描述'


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestMigrateRegistry:
    """registry 迁移测试"""

    @pytest.mark.asyncio
    async def test_migrate_registry_no_file(self, tmp_path):
        """registry.json 不存在"""
        manager = MigrationManager(
            dry_run=True,
            registry_path=tmp_path / "nonexistent.json",
        )
        count = await manager.migrate_registry()
        assert count == 0

    @pytest.mark.asyncio
    async def test_migrate_registry_empty(self, tmp_path):
        """registry.json 为空"""
        registry = tmp_path / "registry.json"
        registry.write_text('{"knowledge_bases": {}}', encoding='utf-8')
        manager = MigrationManager(dry_run=True, registry_path=registry)
        count = await manager.migrate_registry()
        assert count == 0

    @pytest.mark.asyncio
    async def test_migrate_registry_dry_run(self, tmp_path, kb_path):
        """dry-run 模式迁移 registry"""
        registry = tmp_path / "registry.json"
        registry.write_text(json.dumps({
            'knowledge_bases': {
                'test_kb': {
                    'path': str(kb_path),
                    'description': '测试知识库',
                }
            }
        }), encoding='utf-8')
        manager = MigrationManager(dry_run=True, registry_path=registry)
        count = await manager.migrate_registry()
        assert count == 1


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestResolveLinkTarget:
    """链接目标解析测试"""

    def test_resolve_atoms_prefix(self):
        """atoms/ 前缀的链接"""
        manager = MigrationManager(dry_run=True)
        result = manager._resolve_link_target("atoms/methods/foo", "source")
        assert result == "atoms/methods/foo"

    def test_resolve_bare_name(self):
        """裸名称链接"""
        manager = MigrationManager(dry_run=True)
        result = manager._resolve_link_target("foo", "source")
        assert "foo" in result
        assert result.endswith(".md")

    def test_resolve_methods_prefix(self):
        """methods/ 前缀的链接"""
        manager = MigrationManager(dry_run=True)
        result = manager._resolve_link_target("methods/foo", "source")
        assert "methods/foo" in result


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestSchemaChecksum:
    """Schema 校验和测试"""

    def test_compute_checksum(self):
        """计算 schema 校验和"""
        checksum = MigrationManager._compute_schema_checksum()
        assert isinstance(checksum, str)
        assert len(checksum) == 16
