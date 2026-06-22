"""层级管理模块

管理多级知识库的层级关系（个人/部门/项目/公司）。
支持层级继承、权限传播、知识库聚合。
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class KBLevel(Enum):
    """知识库层级"""
    PERSONAL = "personal"      # 个人知识库
    DEPARTMENT = "department"  # 部门知识库
    PROJECT = "project"        # 项目知识库
    COMPANY = "company"        # 公司知识库


@dataclass
class HierarchyNode:
    """层级节点"""
    kb_id: int
    name: str
    level: KBLevel
    parent_id: Optional[int] = None
    children: List[int] = field(default_factory=list)
    organization_id: Optional[int] = None
    department_id: Optional[int] = None
    project_id: Optional[int] = None


class HierarchyManager:
    """层级管理器

    管理知识库的层级关系，支持：
    - 层级查询（获取父/子知识库）
    - 权限继承（子知识库继承父知识库的读取权限）
    - 知识库聚合（公司知识库聚合所有子知识库）
    - 层级验证（确保层级关系正确）
    """

    def __init__(self, db_manager):
        """初始化层级管理器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self._hierarchy_cache: Dict[int, HierarchyNode] = {}

    async def initialize(self) -> None:
        """初始化层级缓存"""
        await self._load_hierarchy()
        logger.info("HierarchyManager initialized")

    async def _load_hierarchy(self) -> None:
        """从数据库加载层级关系"""
        query = """
            SELECT
                id, name, type, organization_id, department_id, project_id,
                (
                    SELECT ARRAY_AGG(child_kb_id)
                    FROM kb_aggregations
                    WHERE parent_kb_id = knowledge_bases.id
                ) as children
            FROM knowledge_bases
            WHERE type IN ('personal', 'department', 'project', 'company')
        """

        results = await self.db_manager.fetch_all(query)

        for row in results:
            node = HierarchyNode(
                kb_id=row['id'],
                name=row['name'],
                level=KBLevel(row['type']),
                organization_id=row['organization_id'],
                department_id=row['department_id'],
                project_id=row['project_id'],
                children=row['children'] or []
            )
            self._hierarchy_cache[node.kb_id] = node

        logger.debug(f"Loaded {len(self._hierarchy_cache)} hierarchy nodes")

    async def get_kb_level(self, kb_id: int) -> Optional[KBLevel]:
        """获取知识库层级

        Args:
            kb_id: 知识库 ID

        Returns:
            知识库层级，不存在返回 None
        """
        node = self._hierarchy_cache.get(kb_id)
        return node.level if node else None

    async def get_parent_kb(self, kb_id: int) -> Optional[int]:
        """获取父知识库

        Args:
            kb_id: 知识库 ID

        Returns:
            父知识库 ID，不存在返回 None
        """
        node = self._hierarchy_cache.get(kb_id)
        if not node:
            return None

        # 根据层级推断父知识库
        if node.level == KBLevel.PERSONAL:
            # 个人知识库可能属于部门或项目
            if node.department_id:
                # 查找部门知识库
                for parent_id, parent_node in self._hierarchy_cache.items():
                    if parent_node.level == KBLevel.DEPARTMENT and \
                       parent_node.department_id == node.department_id:
                        return parent_id
            elif node.project_id:
                # 查找项目知识库
                for parent_id, parent_node in self._hierarchy_cache.items():
                    if parent_node.level == KBLevel.PROJECT and \
                       parent_node.project_id == node.project_id:
                        return parent_id

        elif node.level == KBLevel.DEPARTMENT:
            # 部门知识库可能属于公司
            if node.organization_id:
                # 查找公司知识库
                for parent_id, parent_node in self._hierarchy_cache.items():
                    if parent_node.level == KBLevel.COMPANY and \
                       parent_node.organization_id == node.organization_id:
                        return parent_id

        return None

    async def get_child_kbs(self, kb_id: int) -> List[int]:
        """获取所有子知识库

        Args:
            kb_id: 知识库 ID

        Returns:
            子知识库 ID 列表
        """
        node = self._hierarchy_cache.get(kb_id)
        return node.children if node else []

    async def get_all_ancestors(self, kb_id: int) -> List[int]:
        """获取所有祖先知识库（递归）

        Args:
            kb_id: 知识库 ID

        Returns:
            祖先知识库 ID 列表（从父到根）
        """
        ancestors = []
        current_kb_id = kb_id

        while True:
            parent_id = await self.get_parent_kb(current_kb_id)
            if not parent_id or parent_id in ancestors:
                break
            ancestors.append(parent_id)
            current_kb_id = parent_id

        return ancestors

    async def get_all_descendants(self, kb_id: int) -> List[int]:
        """获取所有后代知识库（递归）

        Args:
            kb_id: 知识库 ID

        Returns:
            后代知识库 ID 列表
        """
        descendants = []
        children = await self.get_child_kbs(kb_id)

        for child_id in children:
            descendants.append(child_id)
            # 递归获取孙知识库
            grand_children = await self.get_all_descendants(child_id)
            descendants.extend(grand_children)

        return descendants

    async def can_inherit_permission(self, kb_id: int, parent_kb_id: int) -> bool:
        """判断是否可以继承权限

        Args:
            kb_id: 子知识库 ID
            parent_kb_id: 父知识库 ID

        Returns:
            是否可以继承权限
        """
        node = self._hierarchy_cache.get(kb_id)
        parent_node = self._hierarchy_cache.get(parent_kb_id)

        if not node or not parent_node:
            return False

        # 验证层级关系是否正确
        valid_hierarchy = {
            KBLevel.PERSONAL: [KBLevel.DEPARTMENT, KBLevel.PROJECT],
            KBLevel.DEPARTMENT: [KBLevel.COMPANY],
            KBLevel.PROJECT: [KBLevel.COMPANY],
            KBLevel.COMPANY: []  # 公司知识库无父级
        }

        return parent_node.level in valid_hierarchy.get(node.level, [])

    async def aggregate_kbs(self, kb_ids: List[int]) -> Dict:
        """聚合多个知识库的内容

        Args:
            kb_ids: 知识库 ID 列表

        Returns:
            聚合结果（包含所有知识库的内容）
        """
        aggregated = {
            'kb_count': len(kb_ids),
            'atom_count': 0,
            'unique_tags': set(),
            'knowledge_bases': []
        }

        for kb_id in kb_ids:
            # 获取知识库信息
            kb_query = "SELECT * FROM knowledge_bases WHERE id = $1"
            kb_info = await self.db_manager.fetch_one(kb_query, kb_id)

            if kb_info:
                aggregated['knowledge_bases'].append(kb_info)

            # 获取原子数量
            atom_query = "SELECT COUNT(*) as count FROM atoms WHERE kb_id = $1"
            atom_count = await self.db_manager.fetch_one(atom_query, kb_id)
            aggregated['atom_count'] += atom_count['count'] if atom_count else 0

            # 获取标签
            tag_query = """
                SELECT DISTINCT jsonb_array_elements_text(metadata->'tags') as tag
                FROM atoms WHERE kb_id = $1
            """
            tags = await self.db_manager.fetch_all(tag_query, kb_id)
            for tag_row in tags:
                if tag_row['tag']:
                    aggregated['unique_tags'].add(tag_row['tag'])

        aggregated['unique_tags'] = list(aggregated['unique_tags'])
        return aggregated

    async def validate_hierarchy(self) -> Dict:
        """验证层级关系完整性

        Returns:
            验证结果（包含错误列表）
        """
        errors = []

        for kb_id, node in self._hierarchy_cache.items():
            # 验证个人知识库的关联
            if node.level == KBLevel.PERSONAL:
                if not node.department_id and not node.project_id:
                    errors.append({
                        'kb_id': kb_id,
                        'error': 'Personal KB must belong to a department or project'
                    })

            # 验证部门知识库的关联
            elif node.level == KBLevel.DEPARTMENT:
                if not node.organization_id:
                    errors.append({
                        'kb_id': kb_id,
                        'error': 'Department KB must belong to an organization'
                    })

            # 验证项目知识库的关联
            elif node.level == KBLevel.PROJECT:
                if not node.project_id:
                    errors.append({
                        'kb_id': kb_id,
                        'error': 'Project KB must have a project_id'
                    })

        return {
            'total_kbs': len(self._hierarchy_cache),
            'error_count': len(errors),
            'errors': errors
        }

    async def refresh_cache(self) -> None:
        """刷新层级缓存"""
        self._hierarchy_cache.clear()
        await self._load_hierarchy()
        logger.info("Hierarchy cache refreshed")

    def get_level_order(self) -> List[KBLevel]:
        """获取层级顺序（从低到高）

        Returns:
            层级顺序列表
        """
        return [
            KBLevel.PERSONAL,
            KBLevel.DEPARTMENT,
            KBLevel.PROJECT,
            KBLevel.COMPANY
        ]

    async def close(self) -> None:
        """关闭层级管理器"""
        self._hierarchy_cache.clear()
        logger.info("HierarchyManager closed")