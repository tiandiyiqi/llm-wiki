"""认证模块."""

from .auth_middleware import (
    require_auth,
    public_endpoint,
    AuthMiddleware,
)
from .session_manager import Session, SessionManager
from .cache_manager import (
    CacheManager,
    get_permission_cache,
    invalidate_user_permissions,
    invalidate_kb_permissions,
    invalidate_all_permissions,
)
from .permission_decorator import (
    require_permission,
    require_role,
    require_kb_permission,
    require_kb_access,
    require_permission_sync,
    PermissionDeniedError,
    ROLE_LEVELS,
    ACTION_LEVELS,
    ACTION_PERMISSION_MAP,
    set_audit_logger,
)

__all__ = [
    # 认证
    'require_auth',
    'public_endpoint',
    'AuthMiddleware',
    # 会话
    'Session',
    'SessionManager',
    # 缓存
    'CacheManager',
    'get_permission_cache',
    'invalidate_user_permissions',
    'invalidate_kb_permissions',
    'invalidate_all_permissions',
    # 权限装饰器
    'require_permission',
    'require_role',
    'require_kb_permission',
    'require_kb_access',
    'require_permission_sync',
    'PermissionDeniedError',
    # 权限常量
    'ROLE_LEVELS',
    'ACTION_LEVELS',
    'ACTION_PERMISSION_MAP',
    # 审计集成
    'set_audit_logger',
]
