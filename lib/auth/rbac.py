"""RBAC（基于角色的访问控制）系统

实现细粒度的权限管理，支持：
- 角色定义（owner/editor/reader）
- 权限检查（CRUD 操作）
- 角色继承
- 动态权限分配
- 数据库持久化
- 缓存机制
"""

import logging
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from lib.core.db_manager import DatabaseManager

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
    支持数据库持久化和内存缓存。
    """

    def __init__(self, db_manager: Optional['DatabaseManager'] = None):
        """初始化 RBAC 管理器

        Args:
            db_manager: 数据库管理器实例（可选，用于持久化）
        """
        self._user_roles: Dict[str, Dict[int, Set[str]]] = {}  # user_id -> {kb_id -> roles}
        self._role_cache: Dict[str, Set[Permission]] = {}
        self._db_manager = db_manager
        self._cache_valid: Dict[str, bool] = {}  # 缓存有效性标记

    async def initialize(self) -> None:
        """初始化 RBAC 系统"""
        # 预加载角色定义
        for role_name, role_def in ROLE_DEFINITIONS.items():
            self._role_cache[role_name] = role_def.permissions

        # 如果有数据库管理器，从数据库加载角色
        if self._db_manager:
            await self._load_roles_from_db()

        logger.info("RBACManager initialized")

    async def _load_roles_from_db(self) -> None:
        """从数据库加载所有角色到内存缓存"""
        if not self._db_manager:
            return

        try:
            query = "SELECT user_id, kb_id, role FROM kb_members"
            results = await self._db_manager.fetch_all(query)

            for row in results:
                user_id = row['user_id']
                kb_id = row['kb_id']
                role = row['role']

                if user_id not in self._user_roles:
                    self._user_roles[user_id] = {}
                if kb_id not in self._user_roles[user_id]:
                    self._user_roles[user_id][kb_id] = set()
                self._user_roles[user_id][kb_id].add(role)

            logger.info(f"Loaded {len(results)} role assignments from database")
        except Exception as e:
            logger.error(f"Failed to load roles from database: {e}")

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
        """为用户分配角色（写入数据库并更新缓存）

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

        # 写入数据库（如果启用持久化）
        if self._db_manager:
            try:
                query = """
                    INSERT INTO kb_members (kb_id, user_id, role, joined_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (kb_id, user_id) DO UPDATE SET role = $3
                """
                await self._db_manager.execute(query, kb_id, user_id, role_name)
                logger.info(f"Assigned role {role_name} to user {user_id} for KB {kb_id} in database")
            except Exception as e:
                logger.error(f"Failed to assign role in database: {e}")
                return False

        # 更新内存缓存
        if user_id not in self._user_roles:
            self._user_roles[user_id] = {}
        if kb_id not in self._user_roles[user_id]:
            self._user_roles[user_id][kb_id] = set()
        self._user_roles[user_id][kb_id].add(role_name)

        # 标记缓存有效
        cache_key = f"{user_id}:{kb_id}"
        self._cache_valid[cache_key] = True

        logger.info(f"Assigned role {role_name} to user {user_id} for KB {kb_id}")

        return True

    async def revoke_role(self, user_id: str, kb_id: int, role_name: str) -> bool:
        """撤销用户的角色（从数据库删除并更新缓存）

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            role_name: 角色名称

        Returns:
            是否成功
        """
        # 从数据库删除（如果启用持久化）
        if self._db_manager:
            try:
                query = """
                    DELETE FROM kb_members
                    WHERE kb_id = $1 AND user_id = $2 AND role = $3
                """
                result = await self._db_manager.execute(query, kb_id, user_id, role_name)
                logger.info(f"Revoked role {role_name} from user {user_id} for KB {kb_id} in database")
            except Exception as e:
                logger.error(f"Failed to revoke role from database: {e}")
                return False

        # 更新内存缓存
        if user_id not in self._user_roles:
            return False

        if kb_id not in self._user_roles[user_id]:
            return False

        if role_name in self._user_roles[user_id][kb_id]:
            self._user_roles[user_id][kb_id].remove(role_name)

            # 如果该用户在该 KB 没有角色了，清理缓存
            if not self._user_roles[user_id][kb_id]:
                del self._user_roles[user_id][kb_id]
                cache_key = f"{user_id}:{kb_id}"
                if cache_key in self._cache_valid:
                    del self._cache_valid[cache_key]

            logger.info(f"Revoked role {role_name} from user {user_id} for KB {kb_id}")
            return True

        return False

    async def get_user_roles(self, user_id: str, kb_id: int, force_reload: bool = False) -> Set[str]:
        """获取用户在知识库中的所有角色（从缓存或数据库加载）

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            force_reload: 是否强制从数据库重新加载

        Returns:
            角色集合
        """
        cache_key = f"{user_id}:{kb_id}"

        # 检查缓存是否有效
        if not force_reload and cache_key in self._cache_valid and self._cache_valid.get(cache_key):
            if user_id in self._user_roles and kb_id in self._user_roles[user_id]:
                return self._user_roles[user_id][kb_id].copy()

        # 从数据库加载（如果启用持久化）
        if self._db_manager:
            try:
                query = "SELECT role FROM kb_members WHERE kb_id = $1 AND user_id = $2"
                results = await self._db_manager.fetch_all(query, kb_id, user_id)

                roles = {row['role'] for row in results}

                # 更新缓存
                if user_id not in self._user_roles:
                    self._user_roles[user_id] = {}
                self._user_roles[user_id][kb_id] = roles
                self._cache_valid[cache_key] = True

                return roles.copy()
            except Exception as e:
                logger.error(f"Failed to load roles from database: {e}")
                # 降级到内存缓存
                pass

        # 从内存缓存返回
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

    async def invalidate_user_cache(self, user_id: str) -> None:
        """使用户的所有角色缓存失效

        Args:
            user_id: 用户 ID
        """
        if user_id in self._user_roles:
            # 标记所有相关的缓存为无效
            for kb_id in self._user_roles[user_id].keys():
                cache_key = f"{user_id}:{kb_id}"
                self._cache_valid[cache_key] = False

            # 清除内存缓存
            del self._user_roles[user_id]

        logger.info(f"Invalidated cache for user {user_id}")

    async def invalidate_kb_cache(self, kb_id: int) -> None:
        """使知识库的所有角色缓存失效

        Args:
            kb_id: 知识库 ID
        """
        # 遍历所有用户，清除该 KB 的缓存
        for user_id in list(self._user_roles.keys()):
            if kb_id in self._user_roles[user_id]:
                cache_key = f"{user_id}:{kb_id}"
                self._cache_valid[cache_key] = False
                del self._user_roles[user_id][kb_id]

                # 如果用户没有任何角色了，删除整个用户条目
                if not self._user_roles[user_id]:
                    del self._user_roles[user_id]

        logger.info(f"Invalidated cache for KB {kb_id}")

    async def invalidate_all_cache(self) -> None:
        """清除所有缓存"""
        self._user_roles.clear()
        self._cache_valid.clear()
        logger.info("Invalidated all role cache")

    async def reload_from_db(self) -> None:
        """从数据库重新加载所有角色"""
        if self._db_manager:
            await self._load_roles_from_db()
            logger.info("Reloaded all roles from database")

    async def close(self) -> None:
        """关闭 RBAC 管理器"""
        self._user_roles.clear()
        self._role_cache.clear()
        logger.info("RBACManager closed")