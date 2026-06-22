"""权限验证中间件

提供统一的权限检查接口，集成 RBAC 和 RLS 系统。
支持：
- 请求级别的权限验证
- 权限缓存（基于 CacheManager，支持 TTL、标签、主动失效）
- 用户上下文管理
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps

from lib.auth.rbac import RBACManager, Permission
from lib.auth.rls_manager import RLSManager
from lib.auth.cache_manager import (
    CacheManager,
    invalidate_user_permissions,
    invalidate_kb_permissions,
    invalidate_all_permissions,
)

logger = logging.getLogger(__name__)


@dataclass
class UserContext:
    """用户上下文信息"""
    user_id: str
    username: str
    roles: List[str]
    kb_permissions: Dict[int, List[Permission]] = field(default_factory=dict)
    login_at: datetime = field(default_factory=datetime.now)

    def has_permission(self, permission: Permission, kb_id: Optional[int] = None) -> bool:
        """检查用户是否有指定权限

        Args:
            permission: 权限
            kb_id: 知识库 ID（可选）

        Returns:
            是否有权限
        """
        # 检查管理员权限
        if Permission.ADMIN in self.get_all_permissions():
            return True

        # 如果指定了知识库，检查该知识库的权限
        if kb_id is not None:
            kb_perms = self.kb_permissions.get(kb_id, [])
            return permission in kb_perms

        # 否则检查全局权限
        return permission in self.get_all_permissions()

    def get_all_permissions(self) -> List[Permission]:
        """获取用户所有权限"""
        all_perms = []
        for perms in self.kb_permissions.values():
            all_perms.extend(perms)
        return list(set(all_perms))


@dataclass
class PermissionCache:
    """权限缓存"""
    entries: Dict[str, UserContext] = field(default_factory=dict)
    ttl_seconds: int = 300  # 5 分钟缓存

    def get(self, user_id: str) -> Optional[UserContext]:
        """获取缓存的用户上下文

        Args:
            user_id: 用户 ID

        Returns:
            用户上下文，不存在或过期返回 None
        """
        if user_id not in self.entries:
            return None

        context = self.entries[user_id]
        if datetime.now() - context.login_at > timedelta(seconds=self.ttl_seconds):
            del self.entries[user_id]
            return None

        return context

    def set(self, user_id: str, context: UserContext) -> None:
        """设置用户上下文缓存

        Args:
            user_id: 用户 ID
            context: 用户上下文
        """
        self.entries[user_id] = context

    def invalidate(self, user_id: str) -> None:
        """使用户缓存失效

        Args:
            user_id: 用户 ID
        """
        if user_id in self.entries:
            del self.entries[user_id]

    def clear(self) -> None:
        """清空所有缓存"""
        self.entries.clear()


class PermissionMiddleware:
    """权限验证中间件

    提供统一的权限检查接口，集成 RBAC 和 RLS 系统。
    使用 CacheManager 管理权限缓存，支持标签和前缀失效。
    """

    def __init__(
        self,
        rbac_manager: RBACManager,
        rls_manager: RLSManager,
        cache_ttl: int = 300
    ):
        """初始化权限中间件

        Args:
            rbac_manager: RBAC 管理器
            rls_manager: RLS 管理器
            cache_ttl: 缓存有效期（秒）
        """
        self.rbac = rbac_manager
        self.rls = rls_manager
        self.cache = CacheManager(ttl=cache_ttl)

    async def initialize(self) -> None:
        """初始化中间件"""
        await self.rbac.initialize()
        await self.rls.initialize()
        logger.info("PermissionMiddleware initialized")

    def _make_cache_key(self, user_id: str, kb_id: int) -> str:
        """生成权限缓存键.

        格式: perm:{user_id}:{kb_id}
        """
        return f"perm:{user_id}:{kb_id}"

    def _make_cache_tags(self, user_id: str, kb_id: int) -> set:
        """生成缓存标签集合，用于按维度批量失效."""
        return {f"user:{user_id}", f"kb:{kb_id}"}

    async def get_user_context(
        self,
        user_id: str,
        username: str = ""
    ) -> UserContext:
        """获取用户上下文（带缓存）

        Args:
            user_id: 用户 ID
            username: 用户名

        Returns:
            用户上下文
        """
        # 获取用户可访问的知识库
        accessible_kbs = await self.rls.get_accessible_kbs(user_id)

        # 获取每个知识库的权限（优先从缓存读取）
        kb_permissions: Dict[int, List[Permission]] = {}
        for kb_id in accessible_kbs:
            cache_key = self._make_cache_key(user_id, kb_id)
            cached_perms = self.cache.get(cache_key)
            if cached_perms is not None:
                kb_permissions[kb_id] = cached_perms
            else:
                perms = await self.rbac.get_user_permissions(user_id, kb_id)
                perm_list = list(perms)
                kb_permissions[kb_id] = perm_list
                self.cache.set(
                    cache_key,
                    perm_list,
                    tags=self._make_cache_tags(user_id, kb_id),
                )

        # 获取用户角色
        roles = []
        for kb_id in accessible_kbs:
            kb_roles = await self.rbac.get_user_roles(user_id, kb_id)
            roles.extend(kb_roles)
        roles = list(set(roles))

        # 创建用户上下文
        context = UserContext(
            user_id=user_id,
            username=username or user_id,
            roles=roles,
            kb_permissions=kb_permissions
        )

        return context

    async def check_kb_permission(
        self,
        user_id: str,
        kb_id: int,
        permission: Permission,
        auto_cache: bool = True
    ) -> bool:
        """检查用户对知识库的权限

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            permission: 权限
            auto_cache: 是否使用缓存

        Returns:
            是否有权限
        """
        try:
            # 使用缓存
            if auto_cache:
                cache_key = self._make_cache_key(user_id, kb_id)
                cached_perms = self.cache.get(cache_key)
                if cached_perms is not None:
                    return permission in cached_perms or Permission.ADMIN in cached_perms

                # 缓存未命中，从 RBAC 获取并写入缓存
                perms = await self.rbac.get_user_permissions(user_id, kb_id)
                perm_list = list(perms)
                self.cache.set(
                    cache_key,
                    perm_list,
                    tags=self._make_cache_tags(user_id, kb_id),
                )
                return permission in perm_list or Permission.ADMIN in perm_list

            # 不使用缓存，直接检查
            return await self.rbac.check_permission(user_id, kb_id, permission)

        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return False

    async def check_atom_permission(
        self,
        user_id: str,
        atom_id: int,
        kb_id: int,
        permission: Permission,
        auto_cache: bool = True
    ) -> bool:
        """检查用户对知识原子的权限

        Args:
            user_id: 用户 ID
            atom_id: 知识原子 ID
            kb_id: 知识库 ID
            permission: 权限
            auto_cache: 是否使用缓存

        Returns:
            是否有权限
        """
        # 知识原子权限依赖于知识库权限
        return await self.check_kb_permission(
            user_id,
            kb_id,
            permission,
            auto_cache
        )

    async def check_action_permission(
        self,
        user_id: str,
        kb_id: int,
        action: str
    ) -> bool:
        """检查用户是否可以执行操作

        将操作名称映射到权限并检查。

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            action: 操作名称（read/write/delete/manage）

        Returns:
            是否有权限
        """
        # 操作到权限的映射
        action_mapping = {
            'read': Permission.KB_READ,
            'write': Permission.KB_UPDATE,
            'delete': Permission.KB_DELETE,
            'manage': Permission.KB_MANAGE,
            'create': Permission.KB_CREATE,
            'atom_read': Permission.ATOM_READ,
            'atom_create': Permission.ATOM_CREATE,
            'atom_update': Permission.ATOM_UPDATE,
            'atom_delete': Permission.ATOM_DELETE,
        }

        permission = action_mapping.get(action)
        if not permission:
            logger.warning(f"Unknown action: {action}")
            return False

        return await self.check_kb_permission(user_id, kb_id, permission)

    def invalidate_user_cache(self, user_id: str) -> int:
        """使用户缓存失效

        当用户角色变更时调用。

        Args:
            user_id: 用户 ID

        Returns:
            失效的条目数
        """
        count = invalidate_user_permissions(user_id)
        # 同时清除按标签索引的用户条目
        count += self.cache.invalidate_by_tag(f"user:{user_id}")
        logger.debug(f"Cache invalidated for user: {user_id}, {count} entries")
        return count

    def invalidate_kb_cache(self, kb_id: int) -> int:
        """使知识库缓存失效

        当知识库权限策略变更时调用。

        Args:
            kb_id: 知识库 ID

        Returns:
            失效的条目数
        """
        count = invalidate_kb_permissions(str(kb_id))
        count += self.cache.invalidate_by_tag(f"kb:{kb_id}")
        logger.debug(f"Cache invalidated for KB: {kb_id}, {count} entries")
        return count

    def clear_cache(self) -> int:
        """清空所有缓存

        Returns:
            失效的条目数
        """
        count = invalidate_all_permissions()
        logger.info(f"Permission cache cleared, {count} entries")
        return count

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """缓存统计信息."""
        return self.cache.stats

    async def set_request_context(
        self,
        user_id: str,
        roles: List[str]
    ) -> None:
        """设置请求级别的 RLS 上下文

        Args:
            user_id: 用户 ID
            roles: 用户角色列表
        """
        await self.rls.set_user_context(user_id, roles)

    async def close(self) -> None:
        """关闭中间件"""
        await self.rbac.close()
        await self.rls.close()
        self.clear_cache()
        logger.info("PermissionMiddleware closed")


def require_permission(permission: Permission, kb_id_param: str = 'kb_id'):
    """权限检查装饰器

    用于装饰需要权限检查的方法。

    Args:
        permission: 所需权限
        kb_id_param: 知识库 ID 参数名

    示例:
        @require_permission(Permission.KB_READ, 'kb_id')
        async def get_kb(kb_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 从 self 获取中间件
            middleware = getattr(self, 'permission_middleware', None)
            if not middleware:
                logger.error("PermissionMiddleware not found")
                raise PermissionError("Permission system not initialized")

            # 获取用户 ID
            user_id = getattr(self, 'current_user_id', None)
            if not user_id:
                raise PermissionError("User not authenticated")

            # 获取知识库 ID
            kb_id = kwargs.get(kb_id_param)
            if kb_id is None and args:
                # 尝试从位置参数获取
                sig = func.__code__
                var_names = sig.co_varnames[:sig.co_argcount]
                if kb_id_param in var_names:
                    idx = var_names.index(kb_id_param) - 1  # 跳过 self
                    if 0 <= idx < len(args):
                        kb_id = args[idx]

            if kb_id is None:
                raise ValueError(f"Knowledge base ID not found in parameter '{kb_id_param}'")

            # 检查权限
            has_perm = await middleware.check_kb_permission(
                user_id,
                kb_id,
                permission
            )

            if not has_perm:
                raise PermissionError(
                    f"Permission denied: {permission.value} for KB {kb_id}"
                )

            return await func(self, *args, **kwargs)

        return wrapper
    return decorator


def require_kb_access(action: str = 'read'):
    """知识库访问权限装饰器

    Args:
        action: 操作类型

    示例:
        @require_kb_access('read')
        async def list_atoms(kb_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            middleware = getattr(self, 'permission_middleware', None)
            if not middleware:
                raise PermissionError("Permission system not initialized")

            user_id = getattr(self, 'current_user_id', None)
            if not user_id:
                raise PermissionError("User not authenticated")

            kb_id = kwargs.get('kb_id')
            if kb_id is None and args:
                kb_id = args[0] if args else None

            if kb_id is None:
                raise ValueError("Knowledge base ID not found")

            has_access = await middleware.check_action_permission(
                user_id,
                kb_id,
                action
            )

            if not has_access:
                raise PermissionError(
                    f"Access denied: {action} for KB {kb_id}"
                )

            return await func(self, *args, **kwargs)

        return wrapper
    return decorator
