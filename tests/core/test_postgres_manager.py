"""测试 PostgreSQLManager

测试 PostgreSQL 数据库管理器的所有功能。
使用 pytest-asyncio 和 Mock asyncpg 连接池。
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 使用测试辅助模块处理导入
from tests.core.test_helper import get_StorageConfig, get_StorageType, get_PostgreSQLManager

# 获取实际的类
StorageConfig = get_StorageConfig()
StorageType = get_StorageType()
PostgreSQLManager = get_PostgreSQLManager()


# Mock asyncpg 模块，避免实际安装依赖
@pytest.fixture(autouse=True)
def mock_asyncpg():
    """Mock asyncpg 模块"""
    # 创建 mock asyncpg 模块
    mock_asyncpg_module = MagicMock()
    mock_asyncpg_module.create_pool = AsyncMock()

    # 将 mock 模块添加到 sys.modules
    import sys
    sys.modules['asyncpg'] = mock_asyncpg_module

    yield mock_asyncpg_module

    # 清理
    if 'asyncpg' in sys.modules:
        del sys.modules['asyncpg']


@pytest.fixture
def postgres_config() -> StorageConfig:
    """创建 PostgreSQL 配置

    Returns:
        StorageConfig 实例
    """
    return StorageConfig(
        type=StorageType.POSTGRES,
        postgres_url='postgresql://user:pass@localhost:5432/testdb',
        pool_size=5,
        max_overflow=10
    )


@pytest.fixture
def mock_pool():
    """创建模拟的 asyncpg 连接池"""
    pool = AsyncMock()
    pool.acquire = MagicMock(return_value=AsyncMock())
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def mock_connection():
    """创建模拟的数据库连接"""
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.transaction = MagicMock(return_value=AsyncMock())
    conn.reset = AsyncMock()
    return conn


@pytest.fixture
async def postgres_manager(postgres_config: StorageConfig, mock_pool, mock_connection, mock_asyncpg):
    """创建使用 Mock 连接池的 PostgreSQLManager 实例

    Args:
        postgres_config: PostgreSQL 配置
        mock_pool: 模拟的连接池
        mock_connection: 模拟的连接

    Yields:
        PostgreSQLManager 实例
    """
    # 设置 mock_asyncpg.create_pool 返回 mock_pool
    mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

    manager = PostgreSQLManager(postgres_config)

    # 设置 mock_pool.acquire 返回上下文管理器
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock()

    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
def sample_kb_data() -> Dict[str, Any]:
    """创建示例知识库数据

    Returns:
        知识库数据字典
    """
    return {
        'name': 'test-kb',
        'path': '/path/to/test-kb',
        'description': 'Test knowledge base',
        'tags': ['test', 'example'],
        'kb_type': 'standalone',
        'scope': 'global'
    }


@pytest.fixture
def sample_atom_data() -> Dict[str, Any]:
    """创建示例知识原子数据

    Returns:
        知识原子数据字典
    """
    return {
        'kb_id': 1,
        'path': 'atoms/test-note.md',
        'type': 'note',
        'title': 'Test Note',
        'description': 'A test note for testing',
        'tags': ['test', 'note'],
        'body': '# Test Note\n\nThis is test content.',
        'frontmatter': {'author': 'tester', 'date': '2024-01-01'}
    }


class TestPostgreSQLManagerInitialization:
    """测试 PostgreSQLManager 初始化"""

    def test_init_with_valid_config(self, postgres_config: StorageConfig):
        """验证使用有效配置初始化"""
        manager = PostgreSQLManager(postgres_config)

        assert manager.config == postgres_config
        assert manager.pool is None
        assert manager._connected is False

    def test_init_with_wrong_config_type_raises(self):
        """验证配置类型错误时抛出异常"""
        config = StorageConfig(type=StorageType.SQLITE)

        with pytest.raises(ValueError, match="Config type must be POSTGRES"):
            PostgreSQLManager(config)

    def test_init_with_missing_url_raises(self):
        """验证缺少 URL 时抛出异常"""
        config = StorageConfig(type=StorageType.POSTGRES, postgres_url=None)

        with pytest.raises(ValueError, match="postgres_url is required"):
            PostgreSQLManager(config)

    @pytest.mark.asyncio
    async def test_initialize_creates_pool(self, postgres_config: StorageConfig, mock_pool, mock_asyncpg):
        """验证初始化创建连接池"""
        mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)
        manager = PostgreSQLManager(postgres_config)
        await manager.initialize()

        mock_asyncpg.create_pool.assert_called_once()
        assert manager.pool == mock_pool
        assert manager._connected is True

        await manager.close()

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, postgres_config: StorageConfig, mock_pool, mock_connection, mock_asyncpg):
        """验证初始化创建表"""
        mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)
        manager = PostgreSQLManager(postgres_config)

        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()

        await manager.initialize()

        # 验证执行了建表语句
        assert mock_connection.execute.call_count > 0

        await manager.close()

    @pytest.mark.asyncio
    async def test_close_releases_pool(self, postgres_manager: PostgreSQLManager, mock_pool):
        """验证关闭释放连接池"""
        await postgres_manager.close()

        mock_pool.close.assert_called_once()
        assert postgres_manager._connected is False
        assert postgres_manager.pool is None

    @pytest.mark.asyncio
    async def test_is_connected_returns_true_after_init(self, postgres_manager: PostgreSQLManager):
        """验证初始化后 is_connected 返回 True"""
        assert await postgres_manager.is_connected() is True

    @pytest.mark.asyncio
    async def test_is_connected_returns_false_before_init(self, postgres_config: StorageConfig):
        """验证初始化前 is_connected 返回 False"""
        manager = PostgreSQLManager(postgres_config)

        assert await manager.is_connected() is False

    @pytest.mark.asyncio
    async def test_is_connected_returns_false_after_close(self, postgres_manager: PostgreSQLManager):
        """验证关闭后 is_connected 返回 False"""
        await postgres_manager.close()

        assert await postgres_manager.is_connected() is False


class TestPostgreSQLManagerKnowledgeBaseCRUD:
    """测试知识库 CRUD 操作"""

    @pytest.mark.asyncio
    async def test_create_kb_returns_id(self, postgres_manager: PostgreSQLManager, mock_connection, sample_kb_data: Dict[str, Any]):
        """验证创建知识库返回 ID"""
        mock_row = {'id': 1}
        mock_connection.fetchrow = AsyncMock(return_value=mock_row)

        kb_id = await postgres_manager.create_kb(sample_kb_data)

        assert kb_id == 1

    @pytest.mark.asyncio
    async def test_create_kb_with_missing_required_fields_raises(self, postgres_manager: PostgreSQLManager):
        """验证缺少必需字段时抛出异常"""
        with pytest.raises(ValueError, match="Invalid kb_data"):
            await postgres_manager.create_kb({'name': 'incomplete'})

    @pytest.mark.asyncio
    async def test_get_kb_returns_kb(self, postgres_manager: PostgreSQLManager, mock_connection, sample_kb_data: Dict[str, Any]):
        """验证获取知识库返回数据"""
        mock_row = {
            'id': 1,
            'name': 'test-kb',
            'path': '/path/to/test-kb',
            'description': 'Test knowledge base',
            'tags': ['test', 'example'],
            'kb_type': 'standalone',
            'parent_id': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'last_accessed_at': None,
            'scope': 'global'
        }
        mock_connection.fetchrow = AsyncMock(return_value=mock_row)

        kb = await postgres_manager.get_kb(1)

        assert kb is not None
        assert kb['name'] == 'test-kb'

    @pytest.mark.asyncio
    async def test_get_kb_returns_none_for_nonexistent(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证获取不存在的知识库返回 None"""
        mock_connection.fetchrow = AsyncMock(return_value=None)

        kb = await postgres_manager.get_kb(99999)

        assert kb is None

    @pytest.mark.asyncio
    async def test_get_kb_by_name_returns_kb(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证按名称获取知识库"""
        mock_row = {
            'id': 1,
            'name': 'test-kb',
            'path': '/path/to/test-kb',
            'description': 'Test knowledge base',
            'tags': ['test'],
            'kb_type': 'standalone',
            'parent_id': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'last_accessed_at': None,
            'scope': 'global'
        }
        mock_connection.fetchrow = AsyncMock(return_value=mock_row)

        kb = await postgres_manager.get_kb_by_name('test-kb')

        assert kb is not None
        assert kb['name'] == 'test-kb'

    @pytest.mark.asyncio
    async def test_get_kb_by_name_returns_none_for_nonexistent(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证按名称获取不存在的知识库返回 None"""
        mock_connection.fetchrow = AsyncMock(return_value=None)

        kb = await postgres_manager.get_kb_by_name('nonexistent')

        assert kb is None

    @pytest.mark.asyncio
    async def test_list_kbs_returns_all(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证列出所有知识库"""
        mock_rows = [
            {'id': 1, 'name': 'kb1', 'path': '/kb1', 'description': '', 'tags': [], 'kb_type': 'standalone', 'parent_id': None, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'last_accessed_at': None, 'scope': 'global'},
            {'id': 2, 'name': 'kb2', 'path': '/kb2', 'description': '', 'tags': [], 'kb_type': 'standalone', 'parent_id': None, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'last_accessed_at': None, 'scope': 'global'}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        kbs = await postgres_manager.list_kbs()

        assert len(kbs) == 2

    @pytest.mark.asyncio
    async def test_list_kbs_filters_by_scope(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证按范围过滤知识库"""
        mock_rows = [
            {'id': 1, 'name': 'global-kb', 'path': '/global', 'description': '', 'tags': [], 'kb_type': 'standalone', 'parent_id': None, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'last_accessed_at': None, 'scope': 'global'}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        kbs = await postgres_manager.list_kbs(scope='global')

        assert len(kbs) == 1
        assert kbs[0]['name'] == 'global-kb'

    @pytest.mark.asyncio
    async def test_update_kb_returns_true(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证更新知识库返回 True"""
        mock_connection.execute = AsyncMock(return_value='UPDATE 1')

        success = await postgres_manager.update_kb(1, {'description': 'updated'})

        assert success is True

    @pytest.mark.asyncio
    async def test_update_kb_returns_false_for_nonexistent(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证更新不存在的知识库返回 False"""
        mock_connection.execute = AsyncMock(return_value='UPDATE 0')

        success = await postgres_manager.update_kb(99999, {'description': 'test'})

        assert success is False

    @pytest.mark.asyncio
    async def test_delete_kb_returns_true(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证删除知识库返回 True"""
        mock_connection.execute = AsyncMock(return_value='DELETE 1')

        success = await postgres_manager.delete_kb(1)

        assert success is True

    @pytest.mark.asyncio
    async def test_delete_kb_returns_false_for_nonexistent(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证删除不存在的知识库返回 False"""
        mock_connection.execute = AsyncMock(return_value='DELETE 0')

        success = await postgres_manager.delete_kb(99999)

        assert success is False


class TestPostgreSQLManagerAtomCRUD:
    """测试知识原子 CRUD 操作"""

    @pytest.mark.asyncio
    async def test_create_atom_returns_id(self, postgres_manager: PostgreSQLManager, mock_connection, sample_atom_data: Dict[str, Any]):
        """验证创建原子返回 ID"""
        mock_row = {'id': 1}
        mock_connection.fetchrow = AsyncMock(return_value=mock_row)

        atom_id = await postgres_manager.create_atom(sample_atom_data)

        assert atom_id == 1

    @pytest.mark.asyncio
    async def test_create_atom_with_missing_required_fields_raises(self, postgres_manager: PostgreSQLManager):
        """验证缺少必需字段时抛出异常"""
        with pytest.raises(ValueError, match="Invalid atom_data"):
            await postgres_manager.create_atom({'title': 'incomplete'})

    @pytest.mark.asyncio
    async def test_get_atom_returns_atom(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证获取原子返回数据"""
        mock_row = {
            'id': 1,
            'kb_id': 1,
            'path': 'atoms/test.md',
            'type': 'note',
            'title': 'Test Note',
            'description': 'A test note',
            'tags': ['test'],
            'body': 'content',
            'frontmatter': {'author': 'tester'},
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'file_mtime': 0.0
        }
        mock_connection.fetchrow = AsyncMock(return_value=mock_row)

        atom = await postgres_manager.get_atom(1)

        assert atom is not None
        assert atom['title'] == 'Test Note'

    @pytest.mark.asyncio
    async def test_get_atom_returns_none_for_nonexistent(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证获取不存在的原子返回 None"""
        mock_connection.fetchrow = AsyncMock(return_value=None)

        atom = await postgres_manager.get_atom(99999)

        assert atom is None

    @pytest.mark.asyncio
    async def test_get_atom_by_path_returns_atom(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证按路径获取原子"""
        mock_row = {
            'id': 1,
            'kb_id': 1,
            'path': 'atoms/test.md',
            'type': 'note',
            'title': 'Test Note',
            'description': 'A test note',
            'tags': ['test'],
            'body': 'content',
            'frontmatter': {'author': 'tester'},
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'file_mtime': 0.0
        }
        mock_connection.fetchrow = AsyncMock(return_value=mock_row)

        atom = await postgres_manager.get_atom_by_path(1, 'atoms/test.md')

        assert atom is not None
        assert atom['path'] == 'atoms/test.md'

    @pytest.mark.asyncio
    async def test_get_atom_by_path_returns_none_for_nonexistent(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证按路径获取不存在的原子返回 None"""
        mock_connection.fetchrow = AsyncMock(return_value=None)

        atom = await postgres_manager.get_atom_by_path(1, 'nonexistent.md')

        assert atom is None

    @pytest.mark.asyncio
    async def test_update_atom_returns_true(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证更新原子返回 True"""
        mock_connection.execute = AsyncMock(return_value='UPDATE 1')

        success = await postgres_manager.update_atom(1, {'title': 'updated'})

        assert success is True

    @pytest.mark.asyncio
    async def test_update_atom_returns_false_for_nonexistent(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证更新不存在的原子返回 False"""
        mock_connection.execute = AsyncMock(return_value='UPDATE 0')

        success = await postgres_manager.update_atom(99999, {'title': 'test'})

        assert success is False

    @pytest.mark.asyncio
    async def test_update_atom_returns_false_for_no_updates(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证无更新字段时返回 False"""
        success = await postgres_manager.update_atom(1, {})

        assert success is False

    @pytest.mark.asyncio
    async def test_delete_atom_returns_true(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证删除原子返回 True"""
        mock_connection.execute = AsyncMock(return_value='DELETE 1')

        success = await postgres_manager.delete_atom(1)

        assert success is True

    @pytest.mark.asyncio
    async def test_delete_atom_returns_false_for_nonexistent(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证删除不存在的原子返回 False"""
        mock_connection.execute = AsyncMock(return_value='DELETE 0')

        success = await postgres_manager.delete_atom(99999)

        assert success is False

    @pytest.mark.asyncio
    async def test_list_atoms_returns_atoms(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证列出原子"""
        mock_rows = [
            {'id': 1, 'kb_id': 1, 'path': 'atoms/note-0.md', 'type': 'note', 'title': 'Note 0', 'description': '', 'tags': [], 'body': '', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0},
            {'id': 2, 'kb_id': 1, 'path': 'atoms/note-1.md', 'type': 'note', 'title': 'Note 1', 'description': '', 'tags': [], 'body': '', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        atoms = await postgres_manager.list_atoms(1)

        assert len(atoms) == 2

    @pytest.mark.asyncio
    async def test_list_atoms_filters_by_type(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证按类型过滤原子"""
        mock_rows = [
            {'id': 1, 'kb_id': 1, 'path': 'atoms/note.md', 'type': 'note', 'title': 'Note', 'description': '', 'tags': [], 'body': '', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        atoms = await postgres_manager.list_atoms(1, by_type='note')

        assert len(atoms) == 1
        assert atoms[0]['type'] == 'note'

    @pytest.mark.asyncio
    async def test_list_atoms_pagination(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证原子列表分页"""
        mock_rows = [
            {'id': i, 'kb_id': 1, 'path': f'atoms/note-{i}.md', 'type': 'note', 'title': f'Note {i}', 'description': '', 'tags': [], 'body': '', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0}
            for i in range(5)
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        atoms = await postgres_manager.list_atoms(1, limit=5, offset=0)

        assert len(atoms) == 5


class TestPostgreSQLManagerSearch:
    """测试搜索功能"""

    @pytest.mark.asyncio
    async def test_search_atoms_finds_matches(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证搜索找到匹配项"""
        mock_rows = [
            {'id': 1, 'kb_id': 1, 'path': 'atoms/python.md', 'type': 'note', 'title': 'Python Programming', 'description': '', 'tags': [], 'body': 'Python content', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0, 'kb_name': 'test', 'rank': 0.5}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        results = await postgres_manager.search_atoms('python')

        assert len(results) == 1
        assert 'Python' in results[0]['title']

    @pytest.mark.asyncio
    async def test_search_atoms_filters_by_kb_id(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证搜索按知识库 ID 过滤"""
        mock_rows = [
            {'id': 1, 'kb_id': 1, 'path': 'atoms/test.md', 'type': 'note', 'title': 'Test', 'description': '', 'tags': [], 'body': 'test', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0, 'kb_name': 'kb1', 'rank': 0.5}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        results = await postgres_manager.search_atoms('test', kb_id=1)

        assert len(results) == 1
        assert results[0]['kb_id'] == 1

    @pytest.mark.asyncio
    async def test_search_atoms_filters_by_type(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证搜索按类型过滤"""
        mock_rows = [
            {'id': 1, 'kb_id': 1, 'path': 'atoms/note.md', 'type': 'note', 'title': 'Test', 'description': '', 'tags': [], 'body': 'test', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0, 'kb_name': 'test', 'rank': 0.5}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        results = await postgres_manager.search_atoms('test', by_type='note')

        assert len(results) == 1
        assert results[0]['type'] == 'note'

    @pytest.mark.asyncio
    async def test_search_atoms_filters_by_tags(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证搜索按标签过滤"""
        mock_rows = [
            {'id': 1, 'kb_id': 1, 'path': 'atoms/tagged.md', 'type': 'note', 'title': 'Tagged', 'description': '', 'tags': ['important'], 'body': 'test', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0, 'kb_name': 'test', 'rank': 0.5}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        results = await postgres_manager.search_atoms('test', tags=['important'])

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_atoms_returns_empty_for_no_match(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证搜索无匹配返回空列表"""
        mock_connection.fetch = AsyncMock(return_value=[])

        results = await postgres_manager.search_atoms('nonexistent')

        assert results == []

    @pytest.mark.asyncio
    async def test_search_atoms_advanced_with_filters(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证高级搜索使用过滤条件"""
        mock_rows = [
            {'id': 1, 'kb_id': 1, 'path': 'atoms/test.md', 'type': 'note', 'title': 'Test', 'description': '', 'tags': [], 'body': 'test', 'frontmatter': {'author': 'tester'}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0, 'kb_name': 'test', 'rank': 0.5}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        results = await postgres_manager.search_atoms_advanced(
            'test',
            filters={'type': 'note', 'author': 'tester'}
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_atoms_advanced_sort_by_time(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证高级搜索按时间排序"""
        mock_rows = [
            {'id': i, 'kb_id': 1, 'path': f'atoms/note-{i}.md', 'type': 'note', 'title': f'Note {i}', 'description': '', 'tags': [], 'body': 'test', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0, 'kb_name': 'test', 'rank': 0.5}
            for i in range(3)
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        results = await postgres_manager.search_atoms_advanced('note', sort_by='time')

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_atoms_advanced_sort_by_title(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证高级搜索按标题排序"""
        mock_rows = [
            {'id': 1, 'kb_id': 1, 'path': 'atoms/a.md', 'type': 'note', 'title': 'A Note', 'description': '', 'tags': [], 'body': 'test', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0, 'kb_name': 'test', 'rank': 0.5},
            {'id': 2, 'kb_id': 1, 'path': 'atoms/z.md', 'type': 'note', 'title': 'Z Note', 'description': '', 'tags': [], 'body': 'test', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0, 'kb_name': 'test', 'rank': 0.5}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        results = await postgres_manager.search_atoms_advanced('note', sort_by='title')

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_atoms_advanced_with_date_filters(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证高级搜索使用日期过滤"""
        mock_rows = [
            {'id': 1, 'kb_id': 1, 'path': 'atoms/test.md', 'type': 'note', 'title': 'Test', 'description': '', 'tags': [], 'body': 'test', 'frontmatter': {}, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'file_mtime': 0.0, 'kb_name': 'test', 'rank': 0.5}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        results = await postgres_manager.search_atoms_advanced(
            'test',
            filters={'date_from': '2024-01-01', 'date_to': '2024-12-31'}
        )

        assert len(results) == 1


class TestPostgreSQLManagerHierarchy:
    """测试父子知识库操作"""

    @pytest.mark.asyncio
    async def test_register_child_kb_creates_relationship(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证注册子知识库创建关系"""
        # 模拟事务上下文管理器
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__ = AsyncMock()
        mock_transaction.__aexit__ = AsyncMock()
        mock_connection.transaction = MagicMock(return_value=mock_transaction)

        success = await postgres_manager.register_child_kb(1, 2, 'child')

        assert success is True

    @pytest.mark.asyncio
    async def test_get_child_kbs_returns_children(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证获取子知识库列表"""
        mock_rows = [
            {'id': 2, 'name': 'child1', 'path': '/parent/child1', 'description': '', 'tags': [], 'kb_type': 'child', 'parent_id': 1, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'last_accessed_at': None, 'scope': 'global', 'child_path': 'child1'},
            {'id': 3, 'name': 'child2', 'path': '/parent/child2', 'description': '', 'tags': [], 'kb_type': 'child', 'parent_id': 1, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'last_accessed_at': None, 'scope': 'global', 'child_path': 'child2'}
        ]
        mock_connection.fetch = AsyncMock(return_value=mock_rows)

        children = await postgres_manager.get_child_kbs(1)

        assert len(children) == 2

    @pytest.mark.asyncio
    async def test_get_child_kbs_returns_empty_for_no_children(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证无子知识库返回空列表"""
        mock_connection.fetch = AsyncMock(return_value=[])

        children = await postgres_manager.get_child_kbs(1)

        assert children == []

    @pytest.mark.asyncio
    async def test_get_parent_kb_returns_parent(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证获取父知识库"""
        mock_row = {'id': 1, 'name': 'parent', 'path': '/parent', 'description': '', 'tags': [], 'kb_type': 'parent', 'parent_id': None, 'created_at': datetime.now(), 'updated_at': datetime.now(), 'last_accessed_at': None, 'scope': 'global'}
        mock_connection.fetchrow = AsyncMock(return_value=mock_row)

        parent = await postgres_manager.get_parent_kb(2)

        assert parent is not None
        assert parent['id'] == 1

    @pytest.mark.asyncio
    async def test_get_parent_kb_returns_none_for_standalone(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证独立知识库无父知识库"""
        mock_connection.fetchrow = AsyncMock(return_value=None)

        parent = await postgres_manager.get_parent_kb(1)

        assert parent is None


class TestPostgreSQLManagerStats:
    """测试统计功能"""

    @pytest.mark.asyncio
    async def test_get_kb_stats_returns_correct_counts(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证获取知识库统计信息"""
        # 模拟总数查询
        mock_total_row = {'count': 5}
        # 模拟类型统计查询
        mock_type_rows = [
            {'type': 'note', 'count': 3},
            {'type': 'concept', 'count': 2}
        ]

        def fetchrow_side_effect(*args, **kwargs):
            return mock_total_row

        def fetch_side_effect(*args, **kwargs):
            return mock_type_rows

        mock_connection.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
        mock_connection.fetch = AsyncMock(side_effect=fetch_side_effect)

        stats = await postgres_manager.get_kb_stats(1)

        assert stats['total_atoms'] == 5
        assert stats['types_count']['note'] == 3
        assert stats['types_count']['concept'] == 2

    @pytest.mark.asyncio
    async def test_get_kb_stats_returns_zero_for_empty(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证空知识库统计为零"""
        mock_connection.fetchrow = AsyncMock(return_value={'count': 0})
        mock_connection.fetch = AsyncMock(return_value=[])

        stats = await postgres_manager.get_kb_stats(1)

        assert stats['total_atoms'] == 0
        assert stats['types_count'] == {}

    @pytest.mark.asyncio
    async def test_get_atom_count_returns_total(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证获取原子总数"""
        mock_connection.fetchrow = AsyncMock(return_value={'count': 5})

        count = await postgres_manager.get_atom_count(1)

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_atom_count_filters_by_type(self, postgres_manager: PostgreSQLManager, mock_connection):
        """验证按类型获取原子数"""
        mock_connection.fetchrow = AsyncMock(return_value={'count': 3})

        count = await postgres_manager.get_atom_count(1, by_type='note')

        assert count == 3


class TestPostgreSQLManagerTransactions:
    """测试事务操作"""

    @pytest.mark.asyncio
    async def test_begin_transaction_acquires_connection(self, postgres_manager: PostgreSQLManager, mock_pool, mock_connection):
        """验证开始事务获取连接"""
        mock_pool.acquire = AsyncMock(return_value=mock_connection)

        await postgres_manager.begin_transaction()

        assert postgres_manager._transaction_conn is not None

    @pytest.mark.asyncio
    async def test_commit_transaction_releases_connection(self, postgres_manager: PostgreSQLManager, mock_pool, mock_connection):
        """验证提交事务释放连接"""
        mock_pool.acquire = AsyncMock(return_value=mock_connection)
        mock_pool.release = AsyncMock()
        mock_connection.reset = AsyncMock()

        await postgres_manager.begin_transaction()
        await postgres_manager.commit_transaction()

        mock_pool.release.assert_called_once()
        assert postgres_manager._transaction_conn is None

    @pytest.mark.asyncio
    async def test_rollback_transaction_releases_connection(self, postgres_manager: PostgreSQLManager, mock_pool, mock_connection):
        """验证回滚事务释放连接"""
        mock_pool.acquire = AsyncMock(return_value=mock_connection)
        mock_pool.release = AsyncMock()
        mock_connection.reset = AsyncMock()

        await postgres_manager.begin_transaction()
        await postgres_manager.rollback_transaction()

        mock_pool.release.assert_called_once()
        assert postgres_manager._transaction_conn is None

    @pytest.mark.asyncio
    async def test_commit_transaction_without_begin_does_nothing(self, postgres_manager: PostgreSQLManager):
        """验证未开始事务时提交不做任何操作"""
        # 不应抛出异常
        await postgres_manager.commit_transaction()

    @pytest.mark.asyncio
    async def test_rollback_transaction_without_begin_does_nothing(self, postgres_manager: PostgreSQLManager):
        """验证未开始事务时回滚不做任何操作"""
        # 不应抛出异常
        await postgres_manager.rollback_transaction()


class TestPostgreSQLManagerRetry:
    """测试重试机制"""

    @pytest.mark.asyncio
    async def test_execute_with_retry_succeeds_on_first_try(self, postgres_manager: PostgreSQLManager):
        """验证首次成功不需要重试"""
        operation = AsyncMock(return_value='success')

        result = await postgres_manager._execute_with_retry(operation)

        assert result == 'success'
        operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_retry_retries_on_failure(self, postgres_manager: PostgreSQLManager):
        """验证失败时重试"""
        call_count = 0

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "success"

        result = await postgres_manager._execute_with_retry(failing_operation, max_retries=3, retry_delay=0.01)

        assert result == 'success'
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_raises_after_max_retries(self, postgres_manager: PostgreSQLManager):
        """验证达到最大重试次数后抛出异常"""
        async def always_failing():
            raise Exception("Permanent error")

        with pytest.raises(Exception, match="Permanent error"):
            await postgres_manager._execute_with_retry(always_failing, max_retries=3, retry_delay=0.01)


class TestPostgreSQLManagerErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_create_kb_propagates_pool_error(self, postgres_config: StorageConfig, mock_asyncpg):
        """验证创建知识库传播连接池错误"""
        mock_asyncpg.create_pool = AsyncMock(side_effect=Exception("Connection failed"))
        manager = PostgreSQLManager(postgres_config)

        with pytest.raises(Exception, match="Connection failed"):
            await manager.initialize()

    @pytest.mark.asyncio
    async def test_operation_on_closed_pool_raises(self, postgres_config: StorageConfig, mock_asyncpg, mock_pool):
        """验证在已关闭的连接池上操作抛出异常"""
        mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)
        manager = PostgreSQLManager(postgres_config)
        manager._connected = True
        manager.pool = None

        with pytest.raises(AttributeError):
            await manager.get_kb(1)


class TestPostgreSQLManagerUtilityMethods:
    """测试工具方法"""

    def test_row_to_kb_dict_converts_correctly(self, postgres_manager: PostgreSQLManager):
        """验证行转换为知识库字典"""
        class MockRow:
            def __getitem__(self, key):
                data = {
                    'id': 1,
                    'name': 'test',
                    'path': '/test',
                    'description': 'desc',
                    'tags': ['tag1'],
                    'kb_type': 'standalone',
                    'parent_id': None,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'last_accessed_at': None,
                    'scope': 'global'
                }
                return data[key]

            def keys(self):
                return ['id', 'name', 'path', 'description', 'tags', 'kb_type',
                        'parent_id', 'created_at', 'updated_at', 'last_accessed_at', 'scope']

        row = MockRow()
        result = postgres_manager._row_to_kb_dict(row)

        assert result['id'] == 1
        assert result['name'] == 'test'
        assert result['tags'] == ['tag1']
        assert 'T' in result['created_at']  # ISO 格式

    def test_row_to_kb_dict_handles_json_tags(self, postgres_manager: PostgreSQLManager):
        """验证处理 JSON 格式的标签"""
        class MockRow:
            def __getitem__(self, key):
                data = {
                    'id': 1,
                    'name': 'test',
                    'path': '/test',
                    'description': 'desc',
                    'tags': '["tag1", "tag2"]',  # JSON 字符串
                    'kb_type': 'standalone',
                    'parent_id': None,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'last_accessed_at': None,
                    'scope': 'global'
                }
                return data[key]

            def keys(self):
                return ['id', 'name', 'path', 'description', 'tags', 'kb_type',
                        'parent_id', 'created_at', 'updated_at', 'last_accessed_at', 'scope']

        row = MockRow()
        result = postgres_manager._row_to_kb_dict(row)

        assert result['tags'] == ['tag1', 'tag2']

    def test_row_to_atom_dict_converts_correctly(self, postgres_manager: PostgreSQLManager):
        """验证行转换为原子字典"""
        class MockRow:
            def __getitem__(self, key):
                data = {
                    'id': 1,
                    'kb_id': 1,
                    'path': 'test.md',
                    'type': 'note',
                    'title': 'Test',
                    'description': 'desc',
                    'tags': ['tag1'],
                    'body': 'content',
                    'frontmatter': {'author': 'test'},
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'file_mtime': 0.0
                }
                return data[key]

            def keys(self):
                return ['id', 'kb_id', 'path', 'type', 'title', 'description',
                        'tags', 'body', 'frontmatter', 'created_at', 'updated_at', 'file_mtime']

        row = MockRow()
        result = postgres_manager._row_to_atom_dict(row)

        assert result['id'] == 1
        assert result['tags'] == ['tag1']
        assert result['frontmatter'] == {'author': 'test'}

    def test_row_to_atom_dict_includes_kb_name(self, postgres_manager: PostgreSQLManager):
        """验证原子字典包含知识库名称"""
        class MockRow:
            def __getitem__(self, key):
                data = {
                    'id': 1,
                    'kb_id': 1,
                    'path': 'test.md',
                    'type': 'note',
                    'title': 'Test',
                    'description': 'desc',
                    'tags': ['tag1'],
                    'body': 'content',
                    'frontmatter': {'author': 'test'},
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'file_mtime': 0.0,
                    'kb_name': 'test-kb'
                }
                return data[key]

            def keys(self):
                return ['id', 'kb_id', 'path', 'type', 'title', 'description',
                        'tags', 'body', 'frontmatter', 'created_at', 'updated_at',
                        'file_mtime', 'kb_name']

        row = MockRow()
        result = postgres_manager._row_to_atom_dict(row)

        assert result['kb_name'] == 'test-kb'

    def test_row_to_atom_dict_includes_rank(self, postgres_manager: PostgreSQLManager):
        """验证原子字典包含搜索排名"""
        class MockRow:
            def __getitem__(self, key):
                data = {
                    'id': 1,
                    'kb_id': 1,
                    'path': 'test.md',
                    'type': 'note',
                    'title': 'Test',
                    'description': 'desc',
                    'tags': ['tag1'],
                    'body': 'content',
                    'frontmatter': {'author': 'test'},
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'file_mtime': 0.0,
                    'rank': 0.95
                }
                return data[key]

            def keys(self):
                return ['id', 'kb_id', 'path', 'type', 'title', 'description',
                        'tags', 'body', 'frontmatter', 'created_at', 'updated_at',
                        'file_mtime', 'rank']

        row = MockRow()
        result = postgres_manager._row_to_atom_dict(row)

        assert result['rank'] == 0.95

    def test_row_to_atom_dict_handles_json_frontmatter(self, postgres_manager: PostgreSQLManager):
        """验证处理 JSON 格式的 frontmatter"""
        class MockRow:
            def __getitem__(self, key):
                data = {
                    'id': 1,
                    'kb_id': 1,
                    'path': 'test.md',
                    'type': 'note',
                    'title': 'Test',
                    'description': 'desc',
                    'tags': [],
                    'body': 'content',
                    'frontmatter': '{"author": "test", "date": "2024-01-01"}',  # JSON 字符串
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'file_mtime': 0.0
                }
                return data[key]

            def keys(self):
                return ['id', 'kb_id', 'path', 'type', 'title', 'description',
                        'tags', 'body', 'frontmatter', 'created_at', 'updated_at', 'file_mtime']

        row = MockRow()
        result = postgres_manager._row_to_atom_dict(row)

        assert result['frontmatter'] == {'author': 'test', 'date': '2024-01-01'}

    def test_row_to_atom_dict_handles_null_values(self, postgres_manager: PostgreSQLManager):
        """验证处理 NULL 值"""
        class MockRow:
            def __getitem__(self, key):
                data = {
                    'id': 1,
                    'kb_id': 1,
                    'path': 'test.md',
                    'type': 'note',
                    'title': 'Test',
                    'description': None,
                    'tags': None,
                    'body': None,
                    'frontmatter': None,
                    'created_at': None,
                    'updated_at': None,
                    'file_mtime': 0.0
                }
                return data[key]

            def keys(self):
                return ['id', 'kb_id', 'path', 'type', 'title', 'description',
                        'tags', 'body', 'frontmatter', 'created_at', 'updated_at', 'file_mtime']

        row = MockRow()
        result = postgres_manager._row_to_atom_dict(row)

        # PostgreSQLManager 的 _row_to_atom_dict 方法不转换 NULL 为空值
        # 它保留 None 值，只有 tags 和 frontmatter 有特殊处理
        assert result['description'] is None
        assert result['tags'] == []  # tags 有特殊处理
        assert result['body'] is None
        assert result['frontmatter'] == {}  # frontmatter 有特殊处理
        assert result['frontmatter'] == {}
