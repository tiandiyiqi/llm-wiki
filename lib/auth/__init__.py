"""认证模块.

提供向后兼容的旧版 API（AuthManager, hash_password, verify_password）
以及新版模块化 API（AuthMiddleware, SessionManager 等）。
"""

# 向后兼容：从旧 auth.py 重新导出
# 新代码应使用 AuthMiddleware + SessionManager 替代
import importlib.util
import os as _os

_legacy_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'auth.py')
_legacy_module = None

if _os.path.exists(_legacy_path):
    try:
        _spec = importlib.util.spec_from_file_location("lib._auth_legacy", _legacy_path)
        if _spec and _spec.loader:
            _legacy_module = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_legacy_module)
    except Exception:
        _legacy_module = None

# 从旧模块导出向后兼容的符号
AuthManager = getattr(_legacy_module, 'AuthManager', None) if _legacy_module else None
hash_password = getattr(_legacy_module, 'hash_password', None) if _legacy_module else None
verify_password = getattr(_legacy_module, 'verify_password', None) if _legacy_module else None

from .auth_middleware import (
    require_auth,
    public_endpoint,
    AuthMiddleware,
)
from .session_manager import Session, SessionManager
from .casdoor_config import CasdoorConfig
from .casdoor_client import CasdoorClient, CasdoorError, CasdoorTokenResponse, CasdoorUserInfo
from .sso_provider import SSOAuthProvider, SSOAuthResult
from .user_sync import UserSyncService, SyncResult, RedisSessionManager, create_session_manager
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
    # 向后兼容
    'AuthManager',
    'hash_password',
    'verify_password',
    # 认证
    'require_auth',
    'public_endpoint',
    'AuthMiddleware',
    # 会话
    'Session',
    'SessionManager',
    # SSO 配置
    'CasdoorConfig',
    # SSO 认证
    'CasdoorClient',
    'CasdoorError',
    'CasdoorTokenResponse',
    'CasdoorUserInfo',
    'SSOAuthProvider',
    'SSOAuthResult',
    # 用户同步
    'UserSyncService',
    'SyncResult',
    # Redis 会话
    'RedisSessionManager',
    'create_session_manager',
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
