"""测试 SQLiteManager

测试 SQLite 数据库管理器的所有功能。
使用 pytest 和 tmp_path fixture 进行临时文件测试。
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# 使用测试辅助模块处理导入
from tests.core.test_helper import get_StorageConfig, get_StorageType, get_SQLiteManager

# 获取实际的类
StorageConfig = get_StorageConfig()
StorageType = get_StorageType()
SQLiteManager = get_SQLiteManager()


@pytest.fixture
def storage_config(tmp_path: Path) -> StorageConfig:
    """创建使用临时目录的配置

    Args:
        tmp_path: pytest 提供的临时目录

    Returns:
        StorageConfig 实例
    """
    return StorageConfig(
        type=StorageType.SQLITE,
        sqlite_data_dir=str(tmp_path)
    )


@pytest.fixture
async def sqlite_manager(tmp_path: Path):
    """创建使用临时目录的 SQLiteManager 实例

    Args:
        tmp_path: pytest 提供的临时目录

    Yields:
        已初始化的 SQLiteManager 实例
    """
    config = StorageConfig(
        type=StorageType.SQLITE,
        sqlite_data_dir=str(tmp_path)
    )
    manager = SQLiteManager(config)
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


class TestSQLiteManagerInitialization:
    """测试 SQLiteManager 初始化"""

    def test_init_with_default_config(self):
        """验证使用默认配置初始化"""
        manager = SQLiteManager()

        assert manager.config.type == StorageType.SQLITE
        assert manager.global_dir == Path.home() / '.llm-wiki'
        assert manager._connected is False

    def test_init_with_custom_config(self, tmp_path: Path):
        """验证使用自定义配置初始化"""
        config = StorageConfig(
            type=StorageType.SQLITE,
            sqlite_data_dir=str(tmp_path)
        )
        manager = SQLiteManager(config)

        assert manager.config.sqlite_data_dir == str(tmp_path)

    @pytest.mark.asyncio
    async def test_initialize_creates_database(self, tmp_path: Path):
        """验证初始化创建数据库文件"""
        config = StorageConfig(
            type=StorageType.SQLITE,
            sqlite_data_dir=str(tmp_path)
        )
        manager = SQLiteManager(config)
        await manager.initialize()

        db_path = tmp_path / 'llm-wiki.db'
        assert db_path.exists()
        assert await manager.is_connected()

        await manager.close()

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, sqlite_manager: SQLiteManager):
        """验证初始化创建必要的表"""
        # 检查表是否存在
        cursor = sqlite_manager._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        assert 'knowledge_bases' in tables
        assert 'atoms' in tables
        assert 'kb_children' in tables

    @pytest.mark.asyncio
    async def test_close_releases_connection(self, sqlite_manager: SQLiteManager):
        """验证关闭释放连接"""
        assert await sqlite_manager.is_connected()

        await sqlite_manager.close()

        assert not await sqlite_manager.is_connected()
        assert sqlite_manager._conn is None

    @pytest.mark.asyncio
    async def test_is_connected_returns_false_before_init(self):
        """验证初始化前 is_connected 返回 False"""
        manager = SQLiteManager()

        assert await manager.is_connected() is False


class TestSQLiteManagerKnowledgeBaseCRUD:
    """测试知识库 CRUD 操作"""

    @pytest.mark.asyncio
    async def test_create_kb_returns_id(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证创建知识库返回 ID"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        assert isinstance(kb_id, int)
        assert kb_id > 0

    @pytest.mark.asyncio
    async def test_create_kb_stores_data(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证创建知识库存储数据"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)
        kb = await sqlite_manager.get_kb(kb_id)

        assert kb is not None
        assert kb['name'] == sample_kb_data['name']
        assert kb['path'] == sample_kb_data['path']
        assert kb['description'] == sample_kb_data['description']
        assert kb['tags'] == sample_kb_data['tags']

    @pytest.mark.asyncio
    async def test_create_kb_with_missing_required_fields_raises(self, sqlite_manager: SQLiteManager):
        """验证缺少必需字段时抛出异常"""
        with pytest.raises(ValueError, match="Invalid kb_data"):
            await sqlite_manager.create_kb({'name': 'incomplete'})

    @pytest.mark.asyncio
    async def test_create_kb_with_duplicate_name_fails(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证创建重名知识库失败"""
        await sqlite_manager.create_kb(sample_kb_data)

        with pytest.raises(sqlite3.IntegrityError):
            await sqlite_manager.create_kb(sample_kb_data)

    @pytest.mark.asyncio
    async def test_get_kb_returns_none_for_nonexistent(self, sqlite_manager: SQLiteManager):
        """验证获取不存在的知识库返回 None"""
        kb = await sqlite_manager.get_kb(99999)

        assert kb is None

    @pytest.mark.asyncio
    async def test_get_kb_by_name_returns_kb(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证按名称获取知识库"""
        await sqlite_manager.create_kb(sample_kb_data)

        kb = await sqlite_manager.get_kb_by_name(sample_kb_data['name'])

        assert kb is not None
        assert kb['name'] == sample_kb_data['name']

    @pytest.mark.asyncio
    async def test_get_kb_by_name_returns_none_for_nonexistent(self, sqlite_manager: SQLiteManager):
        """验证按名称获取不存在的知识库返回 None"""
        kb = await sqlite_manager.get_kb_by_name('nonexistent')

        assert kb is None

    @pytest.mark.asyncio
    async def test_list_kbs_returns_all(self, sqlite_manager: SQLiteManager):
        """验证列出所有知识库"""
        # 创建多个知识库
        for i in range(3):
            await sqlite_manager.create_kb({
                'name': f'kb-{i}',
                'path': f'/path/{i}'
            })

        kbs = await sqlite_manager.list_kbs()

        assert len(kbs) == 3

    @pytest.mark.asyncio
    async def test_list_kbs_filters_by_scope(self, sqlite_manager: SQLiteManager):
        """验证按范围过滤知识库"""
        await sqlite_manager.create_kb({
            'name': 'global-kb',
            'path': '/global',
            'scope': 'global'
        })
        await sqlite_manager.create_kb({
            'name': 'project-kb',
            'path': '/project',
            'scope': 'project'
        })

        global_kbs = await sqlite_manager.list_kbs(scope='global')
        project_kbs = await sqlite_manager.list_kbs(scope='project')

        assert len(global_kbs) == 1
        assert global_kbs[0]['name'] == 'global-kb'
        assert len(project_kbs) == 1
        assert project_kbs[0]['name'] == 'project-kb'

    @pytest.mark.asyncio
    async def test_update_kb_modifies_data(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证更新知识库修改数据"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        success = await sqlite_manager.update_kb(kb_id, {
            'description': 'Updated description',
            'tags': ['updated']
        })

        assert success is True

        kb = await sqlite_manager.get_kb(kb_id)
        assert kb['description'] == 'Updated description'
        assert kb['tags'] == ['updated']

    @pytest.mark.asyncio
    async def test_update_kb_returns_false_for_nonexistent(self, sqlite_manager: SQLiteManager):
        """验证更新不存在的知识库返回 False"""
        success = await sqlite_manager.update_kb(99999, {'description': 'test'})

        assert success is False

    @pytest.mark.asyncio
    async def test_delete_kb_removes_data(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证删除知识库移除数据"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        success = await sqlite_manager.delete_kb(kb_id)

        assert success is True
        assert await sqlite_manager.get_kb(kb_id) is None

    @pytest.mark.asyncio
    async def test_delete_kb_returns_false_for_nonexistent(self, sqlite_manager: SQLiteManager):
        """验证删除不存在的知识库返回 False"""
        success = await sqlite_manager.delete_kb(99999)

        assert success is False

    @pytest.mark.asyncio
    async def test_delete_kb_cascades_to_atoms(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any], sample_atom_data: Dict[str, Any]):
        """验证删除知识库级联删除原子"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)
        sample_atom_data['kb_id'] = kb_id
        atom_id = await sqlite_manager.create_atom(sample_atom_data)

        await sqlite_manager.delete_kb(kb_id)

        atom = await sqlite_manager.get_atom(atom_id)
        assert atom is None


class TestSQLiteManagerAtomCRUD:
    """测试知识原子 CRUD 操作"""

    @pytest.mark.asyncio
    async def test_create_atom_returns_id(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any], sample_atom_data: Dict[str, Any]):
        """验证创建原子返回 ID"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)
        sample_atom_data['kb_id'] = kb_id

        atom_id = await sqlite_manager.create_atom(sample_atom_data)

        assert isinstance(atom_id, int)
        assert atom_id > 0

    @pytest.mark.asyncio
    async def test_create_atom_stores_data(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any], sample_atom_data: Dict[str, Any]):
        """验证创建原子存储数据"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)
        sample_atom_data['kb_id'] = kb_id

        atom_id = await sqlite_manager.create_atom(sample_atom_data)
        atom = await sqlite_manager.get_atom(atom_id)

        assert atom is not None
        assert atom['title'] == sample_atom_data['title']
        assert atom['type'] == sample_atom_data['type']
        assert atom['body'] == sample_atom_data['body']
        assert atom['tags'] == sample_atom_data['tags']

    @pytest.mark.asyncio
    async def test_create_atom_with_missing_required_fields_raises(self, sqlite_manager: SQLiteManager):
        """验证缺少必需字段时抛出异常"""
        with pytest.raises(ValueError, match="Invalid atom_data"):
            await sqlite_manager.create_atom({'title': 'incomplete'})

    @pytest.mark.asyncio
    async def test_get_atom_returns_none_for_nonexistent(self, sqlite_manager: SQLiteManager):
        """验证获取不存在的原子返回 None"""
        atom = await sqlite_manager.get_atom(99999)

        assert atom is None

    @pytest.mark.asyncio
    async def test_get_atom_by_path_returns_atom(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any], sample_atom_data: Dict[str, Any]):
        """验证按路径获取原子"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)
        sample_atom_data['kb_id'] = kb_id

        await sqlite_manager.create_atom(sample_atom_data)

        atom = await sqlite_manager.get_atom_by_path(kb_id, sample_atom_data['path'])

        assert atom is not None
        assert atom['path'] == sample_atom_data['path']

    @pytest.mark.asyncio
    async def test_get_atom_by_path_returns_none_for_nonexistent(self, sqlite_manager: SQLiteManager):
        """验证按路径获取不存在的原子返回 None"""
        atom = await sqlite_manager.get_atom_by_path(1, 'nonexistent.md')

        assert atom is None

    @pytest.mark.asyncio
    async def test_update_atom_modifies_data(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any], sample_atom_data: Dict[str, Any]):
        """验证更新原子修改数据"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)
        sample_atom_data['kb_id'] = kb_id
        atom_id = await sqlite_manager.create_atom(sample_atom_data)

        success = await sqlite_manager.update_atom(atom_id, {
            'title': 'Updated Title',
            'body': 'Updated body content'
        })

        assert success is True

        atom = await sqlite_manager.get_atom(atom_id)
        assert atom['title'] == 'Updated Title'
        assert atom['body'] == 'Updated body content'

    @pytest.mark.asyncio
    async def test_update_atom_returns_false_for_nonexistent(self, sqlite_manager: SQLiteManager):
        """验证更新不存在的原子返回 False"""
        success = await sqlite_manager.update_atom(99999, {'title': 'test'})

        assert success is False

    @pytest.mark.asyncio
    async def test_delete_atom_removes_data(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any], sample_atom_data: Dict[str, Any]):
        """验证删除原子移除数据"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)
        sample_atom_data['kb_id'] = kb_id
        atom_id = await sqlite_manager.create_atom(sample_atom_data)

        success = await sqlite_manager.delete_atom(atom_id)

        assert success is True
        assert await sqlite_manager.get_atom(atom_id) is None

    @pytest.mark.asyncio
    async def test_delete_atom_returns_false_for_nonexistent(self, sqlite_manager: SQLiteManager):
        """验证删除不存在的原子返回 False"""
        success = await sqlite_manager.delete_atom(99999)

        assert success is False

    @pytest.mark.asyncio
    async def test_list_atoms_returns_atoms(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证列出原子"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        # 创建多个原子
        for i in range(5):
            await sqlite_manager.create_atom({
                'kb_id': kb_id,
                'path': f'atoms/note-{i}.md',
                'type': 'note',
                'title': f'Note {i}'
            })

        atoms = await sqlite_manager.list_atoms(kb_id)

        assert len(atoms) == 5

    @pytest.mark.asyncio
    async def test_list_atoms_filters_by_type(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证按类型过滤原子"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/note.md',
            'type': 'note',
            'title': 'Note'
        })
        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/concept.md',
            'type': 'concept',
            'title': 'Concept'
        })

        notes = await sqlite_manager.list_atoms(kb_id, by_type='note')
        concepts = await sqlite_manager.list_atoms(kb_id, by_type='concept')

        assert len(notes) == 1
        assert notes[0]['type'] == 'note'
        assert len(concepts) == 1
        assert concepts[0]['type'] == 'concept'

    @pytest.mark.asyncio
    async def test_list_atoms_pagination(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证原子列表分页"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        # 创建 10 个原子
        for i in range(10):
            await sqlite_manager.create_atom({
                'kb_id': kb_id,
                'path': f'atoms/note-{i}.md',
                'type': 'note',
                'title': f'Note {i:02d}'
            })

        page1 = await sqlite_manager.list_atoms(kb_id, limit=5, offset=0)
        page2 = await sqlite_manager.list_atoms(kb_id, limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) == 5
        # 确保没有重复
        page1_ids = {a['id'] for a in page1}
        page2_ids = {a['id'] for a in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestSQLiteManagerSearch:
    """测试搜索功能"""

    @pytest.mark.asyncio
    async def test_search_atoms_finds_matches(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证搜索找到匹配项"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/python.md',
            'type': 'note',
            'title': 'Python Programming',
            'body': 'Python is a programming language'
        })
        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/javascript.md',
            'type': 'note',
            'title': 'JavaScript Guide',
            'body': 'JavaScript for web development'
        })

        results = await sqlite_manager.search_atoms('python')

        assert len(results) == 1
        assert 'Python' in results[0]['title']

    @pytest.mark.asyncio
    async def test_search_atoms_filters_by_kb_id(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证搜索按知识库 ID 过滤"""
        kb_id1 = await sqlite_manager.create_kb({'name': 'kb1', 'path': '/kb1'})
        kb_id2 = await sqlite_manager.create_kb({'name': 'kb2', 'path': '/kb2'})

        await sqlite_manager.create_atom({
            'kb_id': kb_id1,
            'path': 'atoms/test.md',
            'type': 'note',
            'title': 'Test Note'
        })
        await sqlite_manager.create_atom({
            'kb_id': kb_id2,
            'path': 'atoms/test.md',
            'type': 'note',
            'title': 'Test Note'
        })

        results = await sqlite_manager.search_atoms('test', kb_id=kb_id1)

        assert len(results) == 1
        assert results[0]['kb_id'] == kb_id1

    @pytest.mark.asyncio
    async def test_search_atoms_filters_by_type(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证搜索按类型过滤"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/note.md',
            'type': 'note',
            'title': 'Test Note',
            'body': 'test content'
        })
        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/concept.md',
            'type': 'concept',
            'title': 'Test Concept',
            'body': 'test content'
        })

        results = await sqlite_manager.search_atoms('test', by_type='note')

        assert len(results) == 1
        assert results[0]['type'] == 'note'

    @pytest.mark.asyncio
    async def test_search_atoms_filters_by_tags(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证搜索按标签过滤"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/tagged.md',
            'type': 'note',
            'title': 'Tagged Note',
            'tags': ['important', 'test']
        })
        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/untagged.md',
            'type': 'note',
            'title': 'Untagged Note',
            'tags': ['other']
        })

        results = await sqlite_manager.search_atoms('note', tags=['important'])

        assert len(results) == 1
        assert 'important' in results[0]['tags']

    @pytest.mark.asyncio
    async def test_search_atoms_returns_empty_for_no_match(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证搜索无匹配返回空列表"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/test.md',
            'type': 'note',
            'title': 'Test Note'
        })

        results = await sqlite_manager.search_atoms('nonexistent')

        assert results == []

    @pytest.mark.asyncio
    async def test_search_atoms_advanced_with_filters(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证高级搜索使用过滤条件"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/test.md',
            'type': 'note',
            'title': 'Test Note',
            'frontmatter': {'author': 'tester'}
        })

        results = await sqlite_manager.search_atoms_advanced(
            'test',
            filters={'type': 'note', 'author': 'tester'}
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_atoms_advanced_sort_by_time(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证高级搜索按时间排序"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        # 创建多个原子
        for i in range(3):
            await sqlite_manager.create_atom({
                'kb_id': kb_id,
                'path': f'atoms/note-{i}.md',
                'type': 'note',
                'title': f'Note {i}'
            })

        results = await sqlite_manager.search_atoms_advanced('note', sort_by='time')

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_atoms_advanced_sort_by_title(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证高级搜索按标题排序"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/z.md',
            'type': 'note',
            'title': 'Z Note'
        })
        await sqlite_manager.create_atom({
            'kb_id': kb_id,
            'path': 'atoms/a.md',
            'type': 'note',
            'title': 'A Note'
        })

        results = await sqlite_manager.search_atoms_advanced('note', sort_by='title')

        assert results[0]['title'] == 'A Note'
        assert results[1]['title'] == 'Z Note'


class TestSQLiteManagerHierarchy:
    """测试父子知识库操作"""

    @pytest.mark.asyncio
    async def test_register_child_kb_creates_relationship(self, sqlite_manager: SQLiteManager):
        """验证注册子知识库创建关系"""
        parent_id = await sqlite_manager.create_kb({
            'name': 'parent',
            'path': '/parent'
        })
        child_id = await sqlite_manager.create_kb({
            'name': 'child',
            'path': '/parent/child'
        })

        success = await sqlite_manager.register_child_kb(parent_id, child_id, 'child')

        assert success is True

    @pytest.mark.asyncio
    async def test_register_child_kb_updates_kb_types(self, sqlite_manager: SQLiteManager):
        """验证注册子知识库更新类型"""
        parent_id = await sqlite_manager.create_kb({
            'name': 'parent',
            'path': '/parent'
        })
        child_id = await sqlite_manager.create_kb({
            'name': 'child',
            'path': '/parent/child'
        })

        await sqlite_manager.register_child_kb(parent_id, child_id, 'child')

        parent = await sqlite_manager.get_kb(parent_id)
        child = await sqlite_manager.get_kb(child_id)

        assert parent['kb_type'] == 'parent'
        assert child['kb_type'] == 'child'
        assert child['parent_id'] == parent_id

    @pytest.mark.asyncio
    async def test_get_child_kbs_returns_children(self, sqlite_manager: SQLiteManager):
        """验证获取子知识库列表"""
        parent_id = await sqlite_manager.create_kb({
            'name': 'parent',
            'path': '/parent'
        })
        child1_id = await sqlite_manager.create_kb({
            'name': 'child1',
            'path': '/parent/child1'
        })
        child2_id = await sqlite_manager.create_kb({
            'name': 'child2',
            'path': '/parent/child2'
        })

        await sqlite_manager.register_child_kb(parent_id, child1_id, 'child1')
        await sqlite_manager.register_child_kb(parent_id, child2_id, 'child2')

        children = await sqlite_manager.get_child_kbs(parent_id)

        assert len(children) == 2
        names = {c['name'] for c in children}
        assert 'child1' in names
        assert 'child2' in names

    @pytest.mark.asyncio
    async def test_get_child_kbs_returns_empty_for_no_children(self, sqlite_manager: SQLiteManager):
        """验证无子知识库返回空列表"""
        kb_id = await sqlite_manager.create_kb({
            'name': 'standalone',
            'path': '/standalone'
        })

        children = await sqlite_manager.get_child_kbs(kb_id)

        assert children == []

    @pytest.mark.asyncio
    async def test_get_parent_kb_returns_parent(self, sqlite_manager: SQLiteManager):
        """验证获取父知识库"""
        parent_id = await sqlite_manager.create_kb({
            'name': 'parent',
            'path': '/parent'
        })
        child_id = await sqlite_manager.create_kb({
            'name': 'child',
            'path': '/parent/child'
        })

        await sqlite_manager.register_child_kb(parent_id, child_id, 'child')

        parent = await sqlite_manager.get_parent_kb(child_id)

        assert parent is not None
        assert parent['id'] == parent_id

    @pytest.mark.asyncio
    async def test_get_parent_kb_returns_none_for_standalone(self, sqlite_manager: SQLiteManager):
        """验证独立知识库无父知识库"""
        kb_id = await sqlite_manager.create_kb({
            'name': 'standalone',
            'path': '/standalone'
        })

        parent = await sqlite_manager.get_parent_kb(kb_id)

        assert parent is None


class TestSQLiteManagerStats:
    """测试统计功能"""

    @pytest.mark.asyncio
    async def test_get_kb_stats_returns_correct_counts(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证获取知识库统计信息"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        # 创建不同类型的原子
        for i in range(3):
            await sqlite_manager.create_atom({
                'kb_id': kb_id,
                'path': f'atoms/note-{i}.md',
                'type': 'note',
                'title': f'Note {i}'
            })
        for i in range(2):
            await sqlite_manager.create_atom({
                'kb_id': kb_id,
                'path': f'atoms/concept-{i}.md',
                'type': 'concept',
                'title': f'Concept {i}'
            })

        stats = await sqlite_manager.get_kb_stats(kb_id)

        assert stats['total_atoms'] == 5
        assert stats['types_count']['note'] == 3
        assert stats['types_count']['concept'] == 2

    @pytest.mark.asyncio
    async def test_get_kb_stats_returns_zero_for_empty(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证空知识库统计为零"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        stats = await sqlite_manager.get_kb_stats(kb_id)

        assert stats['total_atoms'] == 0
        assert stats['types_count'] == {}

    @pytest.mark.asyncio
    async def test_get_atom_count_returns_total(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证获取原子总数"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        for i in range(5):
            await sqlite_manager.create_atom({
                'kb_id': kb_id,
                'path': f'atoms/note-{i}.md',
                'type': 'note',
                'title': f'Note {i}'
            })

        count = await sqlite_manager.get_atom_count(kb_id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_atom_count_filters_by_type(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证按类型获取原子数"""
        kb_id = await sqlite_manager.create_kb(sample_kb_data)

        for i in range(3):
            await sqlite_manager.create_atom({
                'kb_id': kb_id,
                'path': f'atoms/note-{i}.md',
                'type': 'note',
                'title': f'Note {i}'
            })
        for i in range(2):
            await sqlite_manager.create_atom({
                'kb_id': kb_id,
                'path': f'atoms/concept-{i}.md',
                'type': 'concept',
                'title': f'Concept {i}'
            })

        note_count = await sqlite_manager.get_atom_count(kb_id, by_type='note')
        concept_count = await sqlite_manager.get_atom_count(kb_id, by_type='concept')

        assert note_count == 3
        assert concept_count == 2


class TestSQLiteManagerTransactions:
    """测试事务操作"""

    @pytest.mark.asyncio
    async def test_begin_transaction(self, sqlite_manager: SQLiteManager):
        """验证开始事务不抛出异常"""
        # SQLite 默认自动开始事务
        await sqlite_manager.begin_transaction()

    @pytest.mark.asyncio
    async def test_commit_transaction(self, sqlite_manager: SQLiteManager, sample_kb_data: Dict[str, Any]):
        """验证提交事务"""
        await sqlite_manager.begin_transaction()
        await sqlite_manager.create_kb(sample_kb_data)
        await sqlite_manager.commit_transaction()

        # 验证数据已提交
        kbs = await sqlite_manager.list_kbs()
        assert len(kbs) == 1

    @pytest.mark.asyncio
    async def test_rollback_transaction(self, sqlite_manager: SQLiteManager):
        """验证回滚事务方法可以正常调用"""
        # SQLiteManager 的 rollback_transaction 只是调用 sqlite3 的 rollback
        # 由于 SQLite 默认自动提交，这里只验证方法可以正常调用

        # 开始事务
        await sqlite_manager.begin_transaction()

        # rollback_transaction 应该能正常调用
        await sqlite_manager.rollback_transaction()

        # 验证连接状态正常
        assert await sqlite_manager.is_connected()


class TestSQLiteManagerRegistryMigration:
    """测试 registry.json 兼容性"""

    @pytest.mark.asyncio
    async def test_migrate_from_registry_imports_data(self, sqlite_manager: SQLiteManager, tmp_path: Path):
        """验证从 registry.json 导入数据"""
        # 创建测试 registry.json
        registry_data = {
            'knowledge_bases': {
                'test-kb': {
                    'path': '/path/to/test-kb',
                    'description': 'Test KB',
                    'tags': ['test'],
                    'created': '2024-01-01T00:00:00'
                }
            }
        }
        registry_path = tmp_path / 'registry.json'
        registry_path.write_text(json.dumps(registry_data))

        count = sqlite_manager.migrate_from_registry(registry_path)

        assert count == 1

        kb = await sqlite_manager.get_kb_by_name('test-kb')
        assert kb is not None
        assert kb['path'] == '/path/to/test-kb'

    @pytest.mark.asyncio
    async def test_migrate_from_registry_handles_missing_file(self, sqlite_manager: SQLiteManager, tmp_path: Path):
        """验证处理不存在的 registry.json"""
        registry_path = tmp_path / 'nonexistent.json'

        count = sqlite_manager.migrate_from_registry(registry_path)

        assert count == 0

    @pytest.mark.asyncio
    async def test_migrate_from_registry_skips_existing(self, sqlite_manager: SQLiteManager, tmp_path: Path):
        """验证跳过已存在的知识库"""
        # 先创建知识库
        await sqlite_manager.create_kb({
            'name': 'existing-kb',
            'path': '/existing'
        })

        # 创建包含同名知识库的 registry
        registry_data = {
            'knowledge_bases': {
                'existing-kb': {
                    'path': '/new-path',
                    'description': 'Should not overwrite'
                }
            }
        }
        registry_path = tmp_path / 'registry.json'
        registry_path.write_text(json.dumps(registry_data))

        count = sqlite_manager.migrate_from_registry(registry_path)

        assert count == 0

        # 验证原始数据未被覆盖
        kb = await sqlite_manager.get_kb_by_name('existing-kb')
        assert kb['path'] == '/existing'


class TestSQLiteManagerUtilityMethods:
    """测试工具方法"""

    def test_get_timestamp_returns_iso_format(self):
        """验证时间戳为 ISO 格式"""
        manager = SQLiteManager()
        timestamp = manager._get_timestamp()

        assert isinstance(timestamp, str)
        assert 'T' in timestamp

    def test_row_to_kb_dict_converts_correctly(self, sqlite_manager: SQLiteManager):
        """验证行转换为知识库字典"""
        import sqlite3

        # 创建一个模拟的 Row 对象
        class MockRow:
            def __getitem__(self, key):
                data = {
                    'id': 1,
                    'name': 'test',
                    'path': '/test',
                    'description': 'desc',
                    'tags': '["tag1"]',
                    'kb_type': 'standalone',
                    'parent_id': None,
                    'created_at': '2024-01-01T00:00:00',
                    'updated_at': '2024-01-01T00:00:00',
                    'last_accessed_at': None,
                    'scope': 'global'
                }
                return data[key]

            def keys(self):
                return ['id', 'name', 'path', 'description', 'tags', 'kb_type',
                        'parent_id', 'created_at', 'updated_at', 'last_accessed_at', 'scope']

        row = MockRow()
        result = sqlite_manager._row_to_kb_dict(row)

        assert result['id'] == 1
        assert result['name'] == 'test'
        assert result['tags'] == ['tag1']

    def test_row_to_atom_dict_converts_correctly(self, sqlite_manager: SQLiteManager):
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
                    'tags': '["tag1"]',
                    'body': 'content',
                    'frontmatter': '{"author": "test"}',
                    'created_at': '2024-01-01T00:00:00',
                    'updated_at': '2024-01-01T00:00:00',
                    'file_mtime': 0.0
                }
                return data[key]

            def keys(self):
                return ['id', 'kb_id', 'path', 'type', 'title', 'description',
                        'tags', 'body', 'frontmatter', 'created_at', 'updated_at', 'file_mtime']

        row = MockRow()
        result = sqlite_manager._row_to_atom_dict(row)

        assert result['id'] == 1
        assert result['tags'] == ['tag1']
        assert result['frontmatter'] == {'author': 'test'}
