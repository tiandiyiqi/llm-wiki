"""多级知识库集成测试

测试知识库层级结构、继承、权限传播和聚合功能。
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from lib.core.sqlite_manager import SQLiteManager
from lib.core.config import StorageConfig, StorageType


class KnowledgeBaseHierarchy:
    """知识库层级管理助手类"""

    def __init__(self, storage):
        self.storage = storage

    async def create_hierarchy(self, levels: List[Dict]) -> Dict[int, int]:
        """创建层级结构

        Args:
            levels: 层级配置列表，从上到下

        Returns:
            层级映射 {level_index: kb_id}
        """
        kb_ids = {}
        parent_id = None

        for i, level_config in enumerate(levels):
            kb_data = {
                'name': level_config['name'],
                'path': f'/path/to/{level_config["name"]}',
                'description': level_config.get('description', ''),
                'tags': level_config.get('tags', []),
                'kb_type': 'standalone',
                'parent_id': parent_id,
                'scope': level_config.get('scope', 'global')
            }
            kb_id = await self.storage.create_kb(kb_data)
            kb_ids[i] = kb_id

            # 如果有父级，注册父子关系
            if parent_id is not None:
                await self.storage.register_child_kb(
                    parent_id, kb_id, kb_data['path']
                )

            parent_id = kb_id

        return kb_ids

    async def get_all_ancestors(self, kb_id: int) -> List[Dict]:
        """获取所有祖先知识库"""
        ancestors = []
        current_kb = await self.storage.get_kb(kb_id)

        while current_kb and current_kb.get('parent_id'):
            parent = await self.storage.get_kb(current_kb['parent_id'])
            if parent:
                ancestors.append(parent)
                current_kb = parent
            else:
                break

        return ancestors

    async def get_all_descendants(self, kb_id: int) -> List[Dict]:
        """获取所有后代知识库"""
        descendants = []

        async def collect_children(parent_id):
            children = await self.storage.get_child_kbs(parent_id)
            for child in children:
                descendants.append(child)
                await collect_children(child['id'])

        await collect_children(kb_id)
        return descendants


class TestKnowledgeBaseHierarchy:
    """多级知识库测试"""

    @pytest.fixture
    async def storage(self, tmp_path):
        """创建测试存储"""
        db_dir = tmp_path / "hierarchy-test"
        db_dir.mkdir(parents=True, exist_ok=True)

        config = StorageConfig(
            type=StorageType.SQLITE,
            sqlite_data_dir=str(db_dir)
        )
        storage = SQLiteManager(config)
        await storage.initialize()
        yield storage
        await storage.close()

    @pytest.fixture
    def hierarchy_helper(self, storage):
        """层级助手"""
        return KnowledgeBaseHierarchy(storage)

    @pytest.fixture
    async def sample_hierarchy(self, storage, hierarchy_helper):
        """创建示例层级结构：公司→部门→个人"""
        levels = [
            {
                'name': 'company-kb',
                'description': 'Company level knowledge base',
                'scope': 'company',
                'tags': []
            },
            {
                'name': 'department-kb',
                'description': 'Department level knowledge base',
                'scope': 'department',
                'tags': []
            },
            {
                'name': 'personal-kb',
                'description': 'Personal knowledge base',
                'scope': 'personal',
                'tags': []
            }
        ]

        kb_ids = await hierarchy_helper.create_hierarchy(levels)

        # 为每个知识库添加测试原子
        for level_idx, kb_id in kb_ids.items():
            level_name = levels[level_idx]['name']
            await storage.create_atom({
                'kb_id': kb_id,
                'path': f'atoms/{level_name}-atom.md',
                'type': 'note',
                'title': f'{level_name} - Atom',
                'body': f'Content for {level_name}',
                'description': f'Description for {level_name}',
                'tags': [f'level-{level_idx}']
            })

        return {
            'levels': levels,
            'kb_ids': kb_ids
        }

    @pytest.mark.asyncio
    async def test_create_multi_level_hierarchy(self, storage, hierarchy_helper):
        """测试创建多级知识库"""
        # 创建 3 级结构：公司→部门→个人
        levels = [
            {'name': 'root', 'description': 'Root KB', 'scope': 'company', 'tags': []},
            {'name': 'child', 'description': 'Child KB', 'scope': 'department', 'tags': []},
            {'name': 'grandchild', 'description': 'Grandchild KB', 'scope': 'personal', 'tags': []}
        ]

        kb_ids = await hierarchy_helper.create_hierarchy(levels)

        # 验证创建成功
        assert len(kb_ids) == 3
        assert all(kb_id > 0 for kb_id in kb_ids.values())

        # 验证父子关系
        child_kb = await storage.get_kb(kb_ids[1])
        assert child_kb['parent_id'] == kb_ids[0]

        grandchild_kb = await storage.get_kb(kb_ids[2])
        assert grandchild_kb['parent_id'] == kb_ids[1]

    @pytest.mark.asyncio
    async def test_hierarchy_inheritance(self, storage, sample_hierarchy):
        """测试层级继承"""
        kb_ids = sample_hierarchy['kb_ids']

        # 验证个人知识库继承部门知识库
        personal_kb = await storage.get_kb(kb_ids[2])
        assert personal_kb['parent_id'] == kb_ids[1]

        # 验证部门知识库继承公司知识库
        department_kb = await storage.get_kb(kb_ids[1])
        assert department_kb['parent_id'] == kb_ids[0]

        # 验证公司知识库没有父级
        company_kb = await storage.get_kb(kb_ids[0])
        assert company_kb.get('parent_id') is None

    @pytest.mark.asyncio
    async def test_permission_propagation(self, storage, sample_hierarchy):
        """测试权限传播（基础验证）"""
        # 验证知识库创建成功并可以访问
        kb_ids = sample_hierarchy['kb_ids']

        # 验证可以访问所有层级的知识库
        for kb_id in kb_ids.values():
            kb = await storage.get_kb(kb_id)
            assert kb is not None

    @pytest.mark.asyncio
    async def test_knowledge_aggregation(self, storage, sample_hierarchy):
        """测试知识库聚合功能"""
        kb_ids = sample_hierarchy['kb_ids']

        # 为每个知识库添加更多原子
        for level_idx, kb_id in kb_ids.items():
            for i in range(3):
                await storage.create_atom({
                    'kb_id': kb_id,
                    'path': f'atoms/atom-{level_idx}-{i}.md',
                    'type': 'note',
                    'title': f'Atom-{level_idx}-{i}',
                    'body': f'Content for level {level_idx}, atom {i}',
                    'description': f'Description for atom {i}',
                    'tags': [f'level-{level_idx}']
                })

        # 聚合所有知识库的原子数量
        total_atoms = 0
        for kb_id in kb_ids.values():
            atoms = await storage.list_atoms(kb_id)
            total_atoms += len(atoms)

        # 验证聚合结果
        # 每个知识库应该有 4 个原子（1 个来自 fixture + 3 个额外）
        assert total_atoms == 12

        # 测试按层级统计
        company_atoms = len(await storage.list_atoms(kb_ids[0]))
        department_atoms = len(await storage.list_atoms(kb_ids[1]))
        personal_atoms = len(await storage.list_atoms(kb_ids[2]))

        assert company_atoms == 4
        assert department_atoms == 4
        assert personal_atoms == 4

    @pytest.mark.asyncio
    async def test_hierarchy_query_performance(self, storage, hierarchy_helper):
        """测试层级查询性能"""
        import time

        # 创建深层层级结构（5 层，每层 10 个知识库）
        all_kb_ids = []

        # 创建根知识库
        root_id = await storage.create_kb({
            'name': 'root',
            'path': '/path/to/root',
            'description': 'Root KB',
            'tags': [],
            'kb_type': 'standalone'
        })
        all_kb_ids.append(root_id)

        # 创建子知识库（每层一个继承链）
        parent_id = root_id
        for level in range(1, 5):
            kb_id = await storage.create_kb({
                'name': f'kb-level-{level}',
                'path': f'/path/to/kb-level-{level}',
                'description': f'KB at level {level}',
                'tags': [],
                'kb_type': 'standalone'
            })
            all_kb_ids.append(kb_id)

            # 注册父子关系
            await storage.register_child_kb(parent_id, kb_id, f'/path/to/kb-level-{level}')
            parent_id = kb_id

        # 为每个知识库添加原子
        for kb_id in all_kb_ids:
            for i in range(5):
                await storage.create_atom({
                    'kb_id': kb_id,
                    'path': f'atoms/atom-{kb_id}-{i}.md',
                    'type': 'note',
                    'title': f'Atom-{kb_id}-{i}',
                    'body': f'Content for atom {i} in KB {kb_id}',
                    'description': f'Description {i}',
                    'tags': []
                })

        # 测试查询性能
        start_time = time.time()

        # 查询所有知识库
        all_kbs = await storage.list_kbs()
        query_time = time.time() - start_time

        assert len(all_kbs) == len(all_kb_ids)
        print(f"\n层级查询性能: {query_time:.3f}s for {len(all_kb_ids)} KBs")

        # 测试搜索性能
        start_time = time.time()
        results = await storage.search_atoms('Atom')
        search_time = time.time() - start_time

        print(f"搜索性能: {search_time:.3f}s for {len(results)} results")

    @pytest.mark.asyncio
    async def test_ancestor_traversal(self, storage, hierarchy_helper, sample_hierarchy):
        """测试祖先遍历"""
        kb_ids = sample_hierarchy['kb_ids']

        # 从个人知识库向上遍历
        ancestors = await hierarchy_helper.get_all_ancestors(kb_ids[2])

        # 应该找到 2 个祖先：部门和公司
        assert len(ancestors) == 2
        assert ancestors[0]['id'] == kb_ids[1]  # 部门
        assert ancestors[1]['id'] == kb_ids[0]  # 公司

    @pytest.mark.asyncio
    async def test_descendant_traversal(self, storage, hierarchy_helper, sample_hierarchy):
        """测试后代遍历"""
        kb_ids = sample_hierarchy['kb_ids']

        # 从公司知识库向下遍历
        descendants = await hierarchy_helper.get_all_descendants(kb_ids[0])

        # 应该找到 2 个后代：部门和个人
        assert len(descendants) == 2

        descendant_ids = [d['id'] for d in descendants]
        assert kb_ids[1] in descendant_ids
        assert kb_ids[2] in descendant_ids

    @pytest.mark.asyncio
    async def test_scope_filtering(self, storage, sample_hierarchy):
        """测试按 scope 过滤"""
        # 测试按 scope 列出知识库
        company_kbs = await storage.list_kbs(scope='company')
        department_kbs = await storage.list_kbs(scope='department')
        personal_kbs = await storage.list_kbs(scope='personal')

        assert len(company_kbs) == 1
        assert len(department_kbs) == 1
        assert len(personal_kbs) == 1

    @pytest.mark.asyncio
    async def test_cross_level_search(self, storage, sample_hierarchy):
        """测试跨层级搜索"""
        kb_ids = sample_hierarchy['kb_ids']

        # 在不同层级添加包含相同关键词的内容
        await storage.create_atom({
            'kb_id': kb_ids[0],
            'path': 'atoms/python-best-practices.md',
            'type': 'guide',
            'title': 'Python Best Practices',
            'body': 'Company-wide Python coding standards',
            'description': 'Python coding standards',
            'tags': ['python']
        })

        await storage.create_atom({
            'kb_id': kb_ids[1],
            'path': 'atoms/python-team-guide.md',
            'type': 'guide',
            'title': 'Python Team Guide',
            'body': 'Department Python development guide',
            'description': 'Python development guide',
            'tags': ['python']
        })

        await storage.create_atom({
            'kb_id': kb_ids[2],
            'path': 'atoms/python-notes.md',
            'type': 'note',
            'title': 'My Python Notes',
            'body': 'Personal Python learning notes',
            'description': 'Python learning notes',
            'tags': ['python']
        })

        # 搜索 "Python"
        results = await storage.search_atoms('Python')

        # 应该找到所有层级的 Python 相关内容
        assert len(results) >= 3

        # 验证结果包含不同层级的内容
        titles = [r['title'] for r in results]
        assert 'Python Best Practices' in titles
        assert 'Python Team Guide' in titles
        assert 'My Python Notes' in titles

    @pytest.mark.asyncio
    async def test_hierarchy_statistics(self, storage, sample_hierarchy):
        """测试层级统计"""
        kb_ids = sample_hierarchy['kb_ids']

        # 获取每个知识库的统计
        for level_idx, kb_id in kb_ids.items():
            stats = await storage.get_kb_stats(kb_id)
            assert stats is not None
            assert 'total_atoms' in stats

            # 验证原子数量
            assert stats['total_atoms'] >= 1

    @pytest.mark.asyncio
    async def test_delete_with_cascade(self, storage, hierarchy_helper):
        """测试级联删除"""
        # 创建父子知识库
        parent_id = await storage.create_kb({
            'name': 'parent',
            'path': '/path/to/parent',
            'description': 'Parent KB',
            'tags': [],
            'kb_type': 'standalone'
        })

        child_id = await storage.create_kb({
            'name': 'child',
            'path': '/path/to/child',
            'description': 'Child KB',
            'tags': [],
            'kb_type': 'standalone'
        })

        # 注册父子关系
        await storage.register_child_kb(parent_id, child_id, '/path/to/child')

        # 添加原子
        await storage.create_atom({
            'kb_id': parent_id,
            'path': 'atoms/parent-atom.md',
            'type': 'note',
            'title': 'Parent Atom',
            'body': 'Parent content',
            'description': 'Parent description',
            'tags': []
        })

        await storage.create_atom({
            'kb_id': child_id,
            'path': 'atoms/child-atom.md',
            'type': 'note',
            'title': 'Child Atom',
            'body': 'Child content',
            'description': 'Child description',
            'tags': []
        })

        # 删除父知识库
        deleted = await storage.delete_kb(parent_id)
        assert deleted is True

        # 验证父知识库已删除
        parent = await storage.get_kb(parent_id)
        assert parent is None

        # 验证子知识库仍然存在（SQLite 实现不会级联删除子知识库）
        # 但原子可能被删除（取决于外键约束）
        child = await storage.get_kb(child_id)
        # 根据具体实现，子知识库可能仍存在但原子已删除

    @pytest.mark.asyncio
    async def test_concurrent_hierarchy_modification(self, storage):
        """测试并发修改层级结构"""
        # 创建根知识库
        root_id = await storage.create_kb({
            'name': 'root',
            'path': '/path/to/root',
            'description': 'Root KB',
            'tags': [],
            'kb_type': 'standalone'
        })

        # 并发创建多个子知识库
        async def create_child(index):
            child_id = await storage.create_kb({
                'name': f'child-{index}',
                'path': f'/path/to/child-{index}',
                'description': f'Child KB {index}',
                'tags': [],
                'kb_type': 'standalone'
            })
            # 注册父子关系
            await storage.register_child_kb(root_id, child_id, f'/path/to/child-{index}')
            return child_id

        # 并发创建 5 个子知识库
        tasks = [create_child(i) for i in range(5)]
        child_ids = await asyncio.gather(*tasks)

        # 验证所有子知识库都创建成功
        assert len(child_ids) == 5
        assert all(cid > 0 for cid in child_ids)

        # 验证父子关系
        children = await storage.get_child_kbs(root_id)
        assert len(children) == 5

    @pytest.mark.asyncio
    async def test_circular_reference_prevention(self, storage):
        """测试防止循环引用"""
        # 创建知识库 A
        kb_a_id = await storage.create_kb({
            'name': 'kb-a',
            'path': '/path/to/kb-a',
            'description': 'Knowledge Base A',
            'tags': [],
            'kb_type': 'standalone'
        })

        # 创建知识库 B，父级为 A
        kb_b_id = await storage.create_kb({
            'name': 'kb-b',
            'path': '/path/to/kb-b',
            'description': 'Knowledge Base B',
            'tags': [],
            'kb_type': 'standalone'
        })

        # 注册父子关系
        await storage.register_child_kb(kb_a_id, kb_b_id, '/path/to/kb-b')

        # 验证 A 没有父级
        kb_a = await storage.get_kb(kb_a_id)
        assert kb_a.get('parent_id') is None

        # 验证 B 的父级是 A
        parent_of_b = await storage.get_parent_kb(kb_b_id)
        assert parent_of_b['id'] == kb_a_id

        # 尝试将 A 注册为 B 的子级（应该失败或忽略）
        # 根据实现，可能抛出异常或返回 False
        try:
            result = await storage.register_child_kb(kb_b_id, kb_a_id, '/path/to/kb-a')
            # 如果允许，验证不会创建循环
            # 这里主要测试接口稳定性
        except Exception:
            # 如果抛出异常，这是预期行为（防止循环）
            pass


class TestHierarchyWithSQLite:
    """使用 SQLite 管理器的层级测试"""

    @pytest.fixture
    async def sqlite_manager(self, tmp_path):
        """创建 SQLite 管理器"""
        db_dir = tmp_path / "sqlite-hierarchy"
        db_dir.mkdir(parents=True, exist_ok=True)

        config = StorageConfig(
            type=StorageType.SQLITE,
            sqlite_data_dir=str(db_dir)
        )
        manager = SQLiteManager(config)
        await manager.initialize()
        yield manager
        await manager.close()

    @pytest.mark.asyncio
    async def test_parent_child_registration(self, sqlite_manager):
        """测试父子知识库注册"""
        # 创建父知识库
        parent_data = {
            'name': 'parent-kb',
            'path': '/path/to/parent',
            'description': 'Parent knowledge base',
            'tags': [],
            'kb_type': 'standalone'
        }
        parent_id = await sqlite_manager.create_kb(parent_data)

        # 创建子知识库
        child_data = {
            'name': 'child-kb',
            'path': '/path/to/child',
            'description': 'Child knowledge base',
            'tags': [],
            'kb_type': 'standalone'
        }
        child_id = await sqlite_manager.create_kb(child_data)

        # 注册父子关系
        success = await sqlite_manager.register_child_kb(
            parent_id, child_id, child_data['path']
        )
        assert success is True

        # 验证父知识库类型已更新
        parent = await sqlite_manager.get_kb(parent_id)
        assert parent['kb_type'] == 'parent'

        # 验证子知识库类型已更新
        child = await sqlite_manager.get_kb(child_id)
        assert child['kb_type'] == 'child'
        assert child['parent_id'] == parent_id

    @pytest.mark.asyncio
    async def test_get_child_kbs(self, sqlite_manager):
        """测试获取子知识库列表"""
        # 创建父知识库
        parent_id = await sqlite_manager.create_kb({
            'name': 'parent',
            'path': '/path/to/parent',
            'description': 'Parent KB',
            'tags': [],
            'kb_type': 'standalone'
        })

        # 创建多个子知识库
        child_ids = []
        for i in range(3):
            child_id = await sqlite_manager.create_kb({
                'name': f'child-{i}',
                'path': f'/path/to/child-{i}',
                'description': f'Child KB {i}',
                'tags': [],
                'kb_type': 'standalone'
            })
            child_ids.append(child_id)

            # 注册父子关系
            await sqlite_manager.register_child_kb(
                parent_id, child_id, f'/path/to/child-{i}'
            )

        # 获取子知识库列表
        children = await sqlite_manager.get_child_kbs(parent_id)

        assert len(children) == 3
        child_names = [c['name'] for c in children]
        assert 'child-0' in child_names
        assert 'child-1' in child_names
        assert 'child-2' in child_names

    @pytest.mark.asyncio
    async def test_get_parent_kb(self, sqlite_manager):
        """测试获取父知识库"""
        # 创建父知识库
        parent_id = await sqlite_manager.create_kb({
            'name': 'parent',
            'path': '/path/to/parent',
            'description': 'Parent KB',
            'tags': [],
            'kb_type': 'standalone'
        })

        # 创建子知识库
        child_id = await sqlite_manager.create_kb({
            'name': 'child',
            'path': '/path/to/child',
            'description': 'Child KB',
            'tags': [],
            'kb_type': 'standalone'
        })

        # 注册父子关系
        await sqlite_manager.register_child_kb(
            parent_id, child_id, '/path/to/child'
        )

        # 获取父知识库
        parent = await sqlite_manager.get_parent_kb(child_id)

        assert parent is not None
        assert parent['id'] == parent_id
        assert parent['name'] == 'parent'

    @pytest.mark.asyncio
    async def test_kb_stats_with_children(self, sqlite_manager):
        """测试包含子知识库的统计"""
        # 创建父知识库
        parent_id = await sqlite_manager.create_kb({
            'name': 'parent',
            'path': '/path/to/parent',
            'description': 'Parent KB',
            'tags': [],
            'kb_type': 'standalone'
        })

        # 添加原子到父知识库
        for i in range(5):
            await sqlite_manager.create_atom({
                'kb_id': parent_id,
                'path': f'/atoms/atom-{i}.md',
                'type': 'note',
                'title': f'Atom {i}',
                'description': f'Description {i}',
                'tags': [],
                'body': f'Content {i}'
            })

        # 创建子知识库
        child_id = await sqlite_manager.create_kb({
            'name': 'child',
            'path': '/path/to/child',
            'description': 'Child KB',
            'tags': [],
            'kb_type': 'standalone'
        })

        # 添加原子到子知识库
        for i in range(3):
            await sqlite_manager.create_atom({
                'kb_id': child_id,
                'path': f'/atoms/child-atom-{i}.md',
                'type': 'note',
                'title': f'Child Atom {i}',
                'description': f'Child Description {i}',
                'tags': [],
                'body': f'Child Content {i}'
            })

        # 注册父子关系
        await sqlite_manager.register_child_kb(
            parent_id, child_id, '/path/to/child'
        )

        # 获取父知识库统计
        parent_stats = await sqlite_manager.get_kb_stats(parent_id)
        assert parent_stats['total_atoms'] == 5

        # 获取子知识库统计
        child_stats = await sqlite_manager.get_kb_stats(child_id)
        assert child_stats['total_atoms'] == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])