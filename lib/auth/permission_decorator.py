"""权限检查装饰器，简化权限验证并集成审计日志.

整合 auth_middleware 和 permission_middleware 中的权限装饰器，
提供统一的装饰器接口，支持：
- 基于角色的权限检查（require_role）
- 基于操作的权限检查（require_permission）
- 基于知识库访问的权限检查（require_kb_access）
- 审计日志自动记录
- 统一错误处理
"""

import functools
import logging
from typing import Any, Callable, List, Optional, Set

from lib.auth.rbac import Permission, Role

logger = logging.getLogger(__name__)

# 角色等级系统：数值越高权限越大
ROLE_LEVELS: dict[str, int] = {
    Role.READER.value: 1,
    Role.EDITOR.value: 2,
    Role.OWNER.value: 3,
}

# 操作所需最低等级
ACTION_LEVELS: dict[str, int] = {
    'view': 1,
    'read': 1,
    'query': 1,
    'edit': 2,
    'write': 2,
    'create': 2,
    'update': 2,
    'delete': 3,
    'manage': 3,
    'admin': 3,
}

# 操作名到 Permission 枚举的映射
ACTION_PERMISSION_MAP: dict[str, Permission] = {
    'read': Permission.KB_READ,
    'view': Permission.KB_READ,
    'query': Permission.KB_READ,
    'write': Permission.KB_UPDATE,
    'edit': Permission.KB_UPDATE,
    'update': Permission.KB_UPDATE,
    'create': Permission.KB_CREATE,
    'delete': Permission.KB_DELETE,
    'manage': Permission.KB_MANAGE,
    'atom_read': Permission.ATOM_READ,
    'atom_create': Permission.ATOM_CREATE,
    'atom_update': Permission.ATOM_UPDATE,
    'atom_delete': Permission.ATOM_DELETE,
}


class PermissionDeniedError(PermissionError):
    """权限拒绝异常，携带结构化上下文信息."""

    def __init__(
        self,
        message: str,
        *,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        role: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.user_id = user_id
        self.action = action
        self.resource = resource
        self.role = role


def _get_current_user(instance: Any) -> Optional[dict[str, Any]]:
    """从实例中获取当前用户信息.

    兼容多种属性命名：current_user / _current_user / current_user_id + current_role.

    Args:
        instance: API handler 实例

    Returns:
        用户信息字典，未认证返回 None
    """
    # 优先使用结构化的 current_user
    current_user = getattr(instance, 'current_user', None)
    if isinstance(current_user, dict):
        return current_user

    # 兼容：current_user 是字符串（username）
    if isinstance(current_user, str):
        user_id = current_user
        role = getattr(instance, 'current_role', 'guest')
        return {'user_id': user_id, 'username': user_id, 'role': role}

    # 兼容：current_user_id + current_role
    user_id = getattr(instance, 'current_user_id', None)
    if user_id:
        role = getattr(instance, 'current_role', 'guest')
        return {'user_id': user_id, 'role': role}

    return None


def _get_permission_middleware(instance: Any) -> Any:
    """从实例中获取权限中间件.

    兼容多种属性命名：permission_middleware / _permission_middleware.

    Args:
        instance: API handler 实例

    Returns:
        PermissionMiddleware 实例，不存在返回 None
    """
    middleware = getattr(instance, 'permission_middleware', None)
    if middleware is not None:
        return middleware

    middleware = getattr(instance, '_permission_middleware', None)
    return middleware


def _get_auth_manager(instance: Any) -> Any:
    """从实例中获取认证管理器.

    Args:
        instance: API handler 实例

    Returns:
        认证管理器实例，不存在返回 None
    """
    if hasattr(instance, '_get_auth_manager'):
        return instance._get_auth_manager()

    auth_manager = getattr(instance, '_auth_manager', None)
    if auth_manager is not None:
        return auth_manager

    return getattr(instance, 'auth_manager', None)


def _log_audit(
    action: str,
    target: str = '',
    user: str = '',
    detail: str = '',
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """记录审计日志.

    优先使用 AuditLogger 实例，回退到标准 logging.

    Args:
        action: 操作类型
        target: 操作目标
        user: 操作用户
        detail: 操作详情
        extra: 额外信息
    """
    try:
        from lib.audit import AuditLogger
        from pathlib import Path

        # 尝试获取知识库目录
        audit_logger = _get_audit_logger()
        if audit_logger is not None:
            audit_logger.log(
                action=action,
                target=target,
                user=user,
                detail=detail,
                extra=extra,
            )
            return
    except (ImportError, Exception) as exc:
        logger.debug(f"AuditLogger unavailable, falling back to logging: {exc}")

    # 回退到标准 logging
    log_entry = f"audit: action={action}, target={target}, user={user}"
    if detail:
        log_entry += f", detail={detail}"
    if extra:
        log_entry += f", extra={extra}"
    logger.info(log_entry)


# 模块级审计日志记录器缓存
_audit_logger_instance: Optional[Any] = None


def _get_audit_logger() -> Any:
    """获取审计日志记录器单例.

    Returns:
        AuditLogger 实例，无法创建时返回 None
    """
    global _audit_logger_instance

    if _audit_logger_instance is not None:
        return _audit_logger_instance

    try:
        from lib.audit import AuditLogger
        from pathlib import Path

        # 使用默认路径
        default_dir = Path('.')
        _audit_logger_instance = AuditLogger(default_dir)
        return _audit_logger_instance
    except Exception:
        return None


def set_audit_logger(audit_logger: Any) -> None:
    """设置审计日志记录器实例.

    用于在应用启动时注入配置好的 AuditLogger.

    Args:
        audit_logger: AuditLogger 实例
    """
    global _audit_logger_instance
    _audit_logger_instance = audit_logger


def _log_permission_granted(
    user_id: Optional[str],
    action: str,
    resource: Optional[str],
) -> None:
    """记录权限授予事件."""
    _log_audit(
        action='permission_granted',
        target=resource or '',
        user=user_id or 'unknown',
        detail=f"Action '{action}' granted",
        extra={'permission_action': action, 'resource': resource},
    )


def _log_permission_denied(
    user_id: Optional[str],
    action: str,
    resource: Optional[str],
    reason: str,
) -> None:
    """记录权限拒绝事件."""
    _log_audit(
        action='permission_denied',
        target=resource or '',
        user=user_id or 'unknown',
        detail=f"Action '{action}' denied: {reason}",
        extra={'permission_action': action, 'resource': resource, 'reason': reason},
    )


def _check_role_level(user_role: str, action: str) -> bool:
    """基于角色等级系统检查权限.

    Args:
        user_role: 用户角色
        action: 操作名称

    Returns:
        是否有权限
    """
    user_level = ROLE_LEVELS.get(user_role, 0)
    action_level = ACTION_LEVELS.get(action, 3)  # 未知操作默认需要最高等级
    return user_level >= action_level


def require_permission(
    action: str,
    resource: Optional[str] = None,
    roles: Optional[List[str]] = None,
) -> Callable:
    """权限检查装饰器（基于操作和角色等级）.

    支持两种权限检查模式：
    1. 角色等级模式：根据 action 自动推断所需等级
    2. 显式角色模式：指定允许的角色列表

    Args:
        action: 所需操作（如 'view', 'edit', 'delete'）
        resource: 资源名称（可选，默认从函数名推断）
        roles: 允许的角色列表（可选，默认根据 action 推断等级）

    Usage:
        @require_permission('edit', resource='knowledge_base')
        async def update_kb(self, kb_id: str, data: dict):
            ...

        @require_permission('delete', roles=['owner', 'admin'])
        async def delete_kb(self, kb_id: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            instance = args[0] if args else None
            resource_name = resource or func.__name__

            # 获取当前用户
            current_user = _get_current_user(instance)
            if current_user is None:
                _log_permission_denied(
                    user_id=None,
                    action=action,
                    resource=resource_name,
                    reason="Not authenticated",
                )
                raise PermissionDeniedError(
                    "Authentication required",
                    action=action,
                    resource=resource_name,
                )

            user_id = current_user.get('user_id') or current_user.get('username', 'unknown')
            user_role = current_user.get('role', 'reader')

            # 检查权限
            has_permission = False

            if roles is not None:
                # 显式角色模式
                has_permission = user_role in roles
            else:
                # 角色等级模式
                has_permission = _check_role_level(user_role, action)

            if not has_permission:
                reason = (
                    f"Role '{user_role}' not in {roles}"
                    if roles is not None
                    else f"Role '{user_role}' (level {ROLE_LEVELS.get(user_role, 0)}) "
                         f"insufficient for action '{action}' "
                         f"(requires level {ACTION_LEVELS.get(action, 3)})"
                )
                _log_permission_denied(
                    user_id=user_id,
                    action=action,
                    resource=resource_name,
                    reason=reason,
                )
                raise PermissionDeniedError(
                    f"Permission denied: '{user_role}' cannot perform '{action}' on '{resource_name}'",
                    user_id=user_id,
                    action=action,
                    resource=resource_name,
                    role=user_role,
                )

            # 记录审计日志（成功）
            _log_permission_granted(
                user_id=user_id,
                action=action,
                resource=resource_name,
            )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(*required_roles: str) -> Callable:
    """角色检查装饰器（简化版）.

    仅检查用户角色是否在允许列表中，不涉及操作等级。

    Args:
        required_roles: 允许的角色列表

    Usage:
        @require_role('owner', 'editor')
        async def delete_kb(self, kb_id: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            instance = args[0] if args else None
            current_user = _get_current_user(instance)

            if current_user is None:
                _log_permission_denied(
                    user_id=None,
                    action=func.__name__,
                    resource=None,
                    reason="Not authenticated",
                )
                raise PermissionDeniedError(
                    "Authentication required",
                    action=func.__name__,
                )

            user_id = current_user.get('user_id') or current_user.get('username', 'unknown')
            user_role = current_user.get('role', 'reader')

            if user_role not in required_roles:
                _log_permission_denied(
                    user_id=user_id,
                    action=func.__name__,
                    resource=None,
                    reason=f"Role '{user_role}' not in {required_roles}",
                )
                raise PermissionDeniedError(
                    f"Role '{user_role}' not allowed. Required: {required_roles}",
                    user_id=user_id,
                    action=func.__name__,
                    role=user_role,
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_kb_permission(
    permission: Permission,
    kb_id_param: str = 'kb_id',
) -> Callable:
    """知识库权限检查装饰器（基于 Permission 枚举）.

    使用 PermissionMiddleware 进行细粒度的知识库级别权限检查。

    Args:
        permission: 所需权限枚举值
        kb_id_param: 知识库 ID 参数名

    Usage:
        @require_kb_permission(Permission.KB_READ, 'kb_id')
        async def get_kb(self, kb_id: int):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            instance = args[0] if args else None

            # 获取权限中间件
            middleware = _get_permission_middleware(instance)
            if middleware is None:
                logger.error(f"PermissionMiddleware not found for {func.__name__}")
                raise PermissionDeniedError(
                    "Permission system not initialized",
                    action=permission.value,
                )

            # 获取当前用户
            current_user = _get_current_user(instance)
            if current_user is None:
                _log_permission_denied(
                    user_id=None,
                    action=permission.value,
                    resource=None,
                    reason="Not authenticated",
                )
                raise PermissionDeniedError(
                    "Authentication required",
                    action=permission.value,
                )

            user_id = current_user.get('user_id') or current_user.get('username', 'unknown')

            # 获取知识库 ID
            kb_id = kwargs.get(kb_id_param)
            if kb_id is None and len(args) > 1:
                # 尝试从位置参数获取
                sig = func.__code__
                var_names = sig.co_varnames[:sig.co_argcount]
                if kb_id_param in var_names:
                    idx = var_names.index(kb_id_param) - 1  # 跳过 self
                    if 0 <= idx < len(args) - 1:
                        kb_id = args[idx + 1]

            if kb_id is None:
                raise ValueError(
                    f"Knowledge base ID not found in parameter '{kb_id_param}'"
                )

            # 检查权限
            has_perm = await middleware.check_kb_permission(
                user_id,
                kb_id,
                permission,
            )

            if not has_perm:
                _log_permission_denied(
                    user_id=user_id,
                    action=permission.value,
                    resource=f"kb:{kb_id}",
                    reason=f"Permission {permission.value} denied for KB {kb_id}",
                )
                raise PermissionDeniedError(
                    f"Permission denied: {permission.value} for KB {kb_id}",
                    user_id=user_id,
                    action=permission.value,
                    resource=f"kb:{kb_id}",
                    role=current_user.get('role'),
                )

            # 记录审计日志（成功）
            _log_permission_granted(
                user_id=user_id,
                action=permission.value,
                resource=f"kb:{kb_id}",
            )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_kb_access(action: str = 'read') -> Callable:
    """知识库访问权限装饰器（基于操作名称）.

    将操作名称映射到 Permission 枚举，通过 PermissionMiddleware 检查。

    Args:
        action: 操作类型（read/write/delete/manage/create 等）

    Usage:
        @require_kb_access('read')
        async def list_atoms(self, kb_id: int):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            instance = args[0] if args else None

            # 获取权限中间件
            middleware = _get_permission_middleware(instance)
            if middleware is None:
                logger.error(f"PermissionMiddleware not found for {func.__name__}")
                raise PermissionDeniedError(
                    "Permission system not initialized",
                    action=action,
                )

            # 获取当前用户
            current_user = _get_current_user(instance)
            if current_user is None:
                _log_permission_denied(
                    user_id=None,
                    action=action,
                    resource=None,
                    reason="Not authenticated",
                )
                raise PermissionDeniedError(
                    "Authentication required",
                    action=action,
                )

            user_id = current_user.get('user_id') or current_user.get('username', 'unknown')

            # 获取知识库 ID
            kb_id = kwargs.get('kb_id')
            if kb_id is None and len(args) > 1:
                kb_id = args[1]

            if kb_id is None:
                raise ValueError("Knowledge base ID not found")

            # 检查权限
            has_access = await middleware.check_action_permission(
                user_id,
                kb_id,
                action,
            )

            if not has_access:
                _log_permission_denied(
                    user_id=user_id,
                    action=action,
                    resource=f"kb:{kb_id}",
                    reason=f"Access denied for action '{action}' on KB {kb_id}",
                )
                raise PermissionDeniedError(
                    f"Access denied: {action} for KB {kb_id}",
                    user_id=user_id,
                    action=action,
                    resource=f"kb:{kb_id}",
                    role=current_user.get('role'),
                )

            # 记录审计日志（成功）
            _log_permission_granted(
                user_id=user_id,
                action=action,
                resource=f"kb:{kb_id}",
            )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_permission_sync(permission_name: str) -> Callable:
    """同步权限检查装饰器（兼容旧接口）.

    用于非异步的 API handler 方法，保持与 auth_middleware.require_permission
    相同的接口，但增加审计日志和统一错误处理。

    Args:
        permission_name: 权限名称（如 'kb:read', 'kb:delete'）

    Usage:
        @require_permission_sync('kb:delete')
        def handle_delete_kb(self, kb_id):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # 获取当前用户
            current_user = _get_current_user(self)
            if current_user is None:
                _log_permission_denied(
                    user_id=None,
                    action=permission_name,
                    resource=None,
                    reason="Not authenticated",
                )
                if hasattr(self, '_json_response'):
                    self._json_response({
                        'success': False,
                        'error': 'Authentication required',
                        'code': 401,
                    }, 401)
                return None

            user_id = current_user.get('user_id') or current_user.get('username', 'unknown')
            user_role = current_user.get('role', 'guest')

            # 获取认证管理器
            auth_manager = _get_auth_manager(self)
            if auth_manager is None:
                logger.error("Auth manager not available")
                _log_permission_denied(
                    user_id=user_id,
                    action=permission_name,
                    resource=None,
                    reason="Auth system unavailable",
                )
                if hasattr(self, '_json_response'):
                    self._json_response({
                        'success': False,
                        'error': 'Authentication system unavailable',
                        'code': 500,
                    }, 500)
                return None

            # 检查权限
            if not auth_manager.check_permission(user_role, permission_name):
                _log_permission_denied(
                    user_id=user_id,
                    action=permission_name,
                    resource=None,
                    reason=f"Role '{user_role}' cannot perform '{permission_name}'",
                )
                if hasattr(self, '_json_response'):
                    self._json_response({
                        'success': False,
                        'error': f'Permission denied: {permission_name}',
                        'code': 403,
                    }, 403)
                return None

            # 记录审计日志（成功）
            _log_permission_granted(
                user_id=user_id,
                action=permission_name,
                resource=None,
            )

            return func(self, *args, **kwargs)

        return wrapper

    return decorator
