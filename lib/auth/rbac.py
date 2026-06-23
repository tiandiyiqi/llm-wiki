"""RBAC（基于角色的访问控制）系统

实现细粒度的权限管理，支持：
- 角色定义（owner/editor/reader）
- 权限检查（CRUD 操作）
- 角色继承
- 动态权限分配
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限枚举"""
    # 知识库权限
    KB_CREATE = "kb:create"
    KB_READ = "kb:read"
    KB_UPDATE = "kb:update"
    KB_DELETE = "kb:delete"
    KB_MANAGE = "kb:manage"  # 管理成员

    # 知识原子权限
    ATOM_CREATE = "atom:create"
    ATOM_READ = "atom:read"
    ATOM_UPDATE = "atom:update"
    ATOM_DELETE = "atom:delete"

    # 成员权限
    MEMBER_MANAGE = "member:manage"

    # 管理权限
    ADMIN = "admin"


class Role(Enum):
    """角色枚举"""
    OWNER = "owner"
    EDITOR = "editor"
    READER = "reader"


@dataclass
class RoleDefinition:
    """角色定义"""
    name: str
    permissions: Set[Permission]
    description: str
    inherits_from: Optional[str] = None


# 预定义角色
ROLE_DEFINITIONS: Dict[str, RoleDefinition] = {
    Role.OWNER.value: RoleDefinition(
        name="owner",
        permissions={
            Permission.KB_CREATE,
            Permission.KB_READ,
            Permission.KB_UPDATE,
            Permission.KB_DELETE,
            Permission.KB_MANAGE,
            Permission.ATOM_CREATE,
            Permission.ATOM_READ,
            Permission.ATOM_UPDATE,
            Permission.ATOM_DELETE,
            Permission.MEMBER_MANAGE,
            Permission.ADMIN,
        },
        description="所有者：完全控制权限",
        inherits_from=None
    ),

    Role.EDITOR.value: RoleDefinition(
        name="editor",
        permissions={
            Permission.KB_READ,
            Permission.ATOM_CREATE,
            Permission.ATOM_READ,
            Permission.ATOM_UPDATE,
            Permission.ATOM_DELETE,
        },
        description="编辑者：读写权限",
        inherits_from="reader"
    ),

    Role.READER.value: RoleDefinition(
        name="reader",
        permissions={
            Permission.KB_READ,
            Permission.ATOM_READ,
        },
        description="读者：只读权限",
        inherits_from=None
    ),
}


class RBACManager:
    """RBAC 权限管理器

    管理角色和权限的映射关系。
    """

    def __init__(self):
        """初始化 RBAC 管理器"""
        self._user_roles: Dict[str, Dict[int, Set[str]]] = {}  # user_id -> {kb_id -> roles}
        self._role_cache: Dict[str, Set[Permission]] = {}

    async def initialize(self) -> None:
        """初始化 RBAC 系统"""
        # 预加载角色定义
        for role_name, role_def in ROLE_DEFINITIONS.items():
            self._role_cache[role_name] = role_def.permissions

        logger.info("RBACManager initialized")

    def get_role_permissions(self, role_name: str) -> Set[Permission]:
        """获取角色的所有权限（包括继承）

        Args:
            role_name: 角色名称

        Returns:
            权限集合
        """
        if role_name in self._role_cache:
            return self._role_cache[role_name]

        permissions = set()

        # 获取角色定义
        role_def = ROLE_DEFINITIONS.get(role_name)
        if not role_def:
            return permissions

        # 添加角色自身权限
        permissions.update(role_def.permissions)

        # 递归获取继承的权限
        if role_def.inherits_from:
            inherited_perms = self.get_role_permissions(role_def.inherits_from)
            permissions.update(inherited_perms)

        # 缓存结果
        self._role_cache[role_name] = permissions

        return permissions

    def has_permission(self, role_name: str, permission: Permission) -> bool:
        """检查角色是否有指定权限

        Args:
            role_name: 角色名称
            permission: 权限

        Returns:
            是否有权限
        """
        permissions = self.get_role_permissions(role_name)
        return permission in permissions or Permission.ADMIN in permissions

    async def assign_role(self, user_id: str, kb_id: int, role_name: str) -> bool:
        """为用户分配角色

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            role_name: 角色名称

        Returns:
            是否成功
        """
        if role_name not in ROLE_DEFINITIONS:
            logger.error(f"Invalid role: {role_name}")
            return False

        if user_id not in self._user_roles:
            self._user_roles[user_id] = {}

        if kb_id not in self._user_roles[user_id]:
            self._user_roles[user_id][kb_id] = set()

        self._user_roles[user_id][kb_id].add(role_name)
        logger.info(f"Assigned role {role_name} to user {user_id} for KB {kb_id}")

        return True

    async def revoke_role(self, user_id: str, kb_id: int, role_name: str) -> bool:
        """撤销用户的角色

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            role_name: 角色名称

        Returns:
            是否成功
        """
        if user_id not in self._user_roles:
            return False

        if kb_id not in self._user_roles[user_id]:
            return False

        if role_name in self._user_roles[user_id][kb_id]:
            self._user_roles[user_id][kb_id].remove(role_name)
            logger.info(f"Revoked role {role_name} from user {user_id} for KB {kb_id}")
            return True

        return False

    async def get_user_roles(self, user_id: str, kb_id: int) -> Set[str]:
        """获取用户在知识库中的所有角色

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            角色集合
        """
        if user_id not in self._user_roles:
            return set()

        if kb_id not in self._user_roles[user_id]:
            return set()

        return self._user_roles[user_id][kb_id].copy()

    async def check_permission(
        self,
        user_id: str,
        kb_id: int,
        permission: Permission
    ) -> bool:
        """检查用户是否有指定权限

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            permission: 权限

        Returns:
            是否有权限
        """
        roles = await self.get_user_roles(user_id, kb_id)

        # 检查每个角色
        for role_name in roles:
            if self.has_permission(role_name, permission):
                return True

        return False

    async def get_user_permissions(self, user_id: str, kb_id: int) -> Set[Permission]:
        """获取用户在知识库中的所有权限

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            权限集合
        """
        roles = await self.get_user_roles(user_id, kb_id)
        permissions = set()

        for role_name in roles:
            role_perms = self.get_role_permissions(role_name)
            permissions.update(role_perms)

        return permissions

    async def create_custom_role(
        self,
        role_name: str,
        permissions: Set[Permission],
        description: str,
        inherits_from: Optional[str] = None
    ) -> bool:
        """创建自定义角色

        Args:
            role_name: 角色名称
            permissions: 权限集合
            description: 描述
            inherits_from: 继承自哪个角色

        Returns:
            是否成功
        """
        if role_name in ROLE_DEFINITIONS:
            logger.error(f"Role {role_name} already exists")
            return False

        # 创建角色定义
        role_def = RoleDefinition(
            name=role_name,
            permissions=permissions,
            description=description,
            inherits_from=inherits_from
        )

        ROLE_DEFINITIONS[role_name] = role_def
        # 不预填缓存，让 get_role_permissions 首次查询时
        # 自动计算包含继承的完整权限并缓存
        logger.info(f"Created custom role: {role_name}")
        return True

    async def delete_custom_role(self, role_name: str) -> bool:
        """删除自定义角色

        Args:
            role_name: 角色名称

        Returns:
            是否成功
        """
        if role_name not in ROLE_DEFINITIONS:
            return False

        # 不允许删除预定义角色
        if role_name in [r.value for r in Role]:
            logger.error(f"Cannot delete predefined role: {role_name}")
            return False

        del ROLE_DEFINITIONS[role_name]
        if role_name in self._role_cache:
            del self._role_cache[role_name]

        logger.info(f"Deleted custom role: {role_name}")
        return True

    async def close(self) -> None:
        """关闭 RBAC 管理器"""
        self._user_roles.clear()
        self._role_cache.clear()
        logger.info("RBACManager closed")