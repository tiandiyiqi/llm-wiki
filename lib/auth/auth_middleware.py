"""认证中间件，为 API 端点提供认证保护.

提供 require_auth 装饰器，用于保护需要认证的 API 端点。
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


def require_auth(func: Callable) -> Callable:
    """认证装饰器，保护需要认证的 API 端点.

    使用方式：
        @require_auth
        def handle_api_request(self, *args, **kwargs):
            # 此方法需要认证才能访问
            pass

    Args:
        func: 要保护的函数

    Returns:
        包装后的函数
    """
    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Optional[Any]:
        """认证检查包装器."""
        # 检查是否启用认证
        if hasattr(self, '_auth_manager') and self._auth_manager:
            auth_manager = self._auth_manager

            # 检查是否启用权限控制
            if not auth_manager.is_enabled():
                # 未启用权限控制，直接执行
                return func(self, *args, **kwargs)

        # 获取 Authorization header
        auth_header = None
        if hasattr(self, 'headers'):
            auth_header = self.headers.get('Authorization', '')
        elif hasattr(self, 'get_header'):
            auth_header = self.get_header('Authorization', '')

        # 检查 Authorization header 格式
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("Missing or invalid Authorization header")
            if hasattr(self, '_json_response'):
                self._json_response({
                    'success': False,
                    'error': 'Missing authentication token',
                    'code': 401
                }, 401)
            return None

        # 提取 Token
        token = auth_header[7:]  # 移除 "Bearer " 前缀

        # 验证 Token
        auth_manager = None
        if hasattr(self, '_get_auth_manager'):
            auth_manager = self._get_auth_manager()
        elif hasattr(self, '_auth_manager'):
            auth_manager = self._auth_manager

        if not auth_manager:
            logger.error("Auth manager not available")
            if hasattr(self, '_json_response'):
                self._json_response({
                    'success': False,
                    'error': 'Authentication system unavailable',
                    'code': 500
                }, 500)
            return None

        # 验证 Token 并获取角色
        role = auth_manager.validate_token(token)
        if not role:
            logger.warning(f"Invalid token: {token[:8]}...")
            if hasattr(self, '_json_response'):
                self._json_response({
                    'success': False,
                    'error': 'Invalid or expired token',
                    'code': 401
                }, 401)
            return None

        # 获取用户信息（从 Token）
        token_info = auth_manager.config.get('tokens', {}).get(token, {})
        username = token_info.get('username', 'unknown')

        # 设置用户上下文
        if hasattr(self, 'current_user'):
            self.current_user = username
        if hasattr(self, 'current_role'):
            self.current_role = role

        # 记录认证成功
        logger.info(f"User authenticated: {username} (role: {role})")

        # 执行原函数
        return func(self, *args, **kwargs)

    return wrapper


def require_permission(permission_name: str) -> Callable:
    """权限检查装饰器，检查用户是否有指定权限.

    使用方式：
        @require_permission('kb:delete')
        def handle_delete_kb(self, kb_id):
            # 此方法需要 kb:delete 权限
            pass

    Args:
        permission_name: 权限名称（如 'kb:read', 'kb:delete'）

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Optional[Any]:
            """权限检查包装器."""
            # 先检查认证
            if not hasattr(self, 'current_user') or not self.current_user:
                logger.warning("User not authenticated")
                if hasattr(self, '_json_response'):
                    self._json_response({
                        'success': False,
                        'error': 'Authentication required',
                        'code': 401
                    }, 401)
                return None

            # 获取认证管理器
            auth_manager = None
            if hasattr(self, '_get_auth_manager'):
                auth_manager = self._get_auth_manager()
            elif hasattr(self, '_auth_manager'):
                auth_manager = self._auth_manager

            if not auth_manager:
                logger.error("Auth manager not available")
                if hasattr(self, '_json_response'):
                    self._json_response({
                        'success': False,
                        'error': 'Authentication system unavailable',
                        'code': 500
                    }, 500)
                return None

            # 检查权限
            role = getattr(self, 'current_role', 'guest')
            if not auth_manager.check_permission(role, permission_name):
                logger.warning(
                    f"Permission denied: {self.current_user} cannot {permission_name}"
                )
                if hasattr(self, '_json_response'):
                    self._json_response({
                        'success': False,
                        'error': f'Permission denied: {permission_name}',
                        'code': 403
                    }, 403)
                return None

            # 记录权限检查成功
            logger.info(
                f"Permission granted: {self.current_user} can {permission_name}"
            )

            # 执行原函数
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def public_endpoint(func: Callable) -> Callable:
    """公开端点装饰器，标记无需认证的端点.

    使用方式：
        @public_endpoint
        def handle_health_check(self):
            # 此方法无需认证
            pass

    Args:
        func: 公开函数

    Returns:
        原函数（无包装）
    """
    # 标记为公开端点
    func._public_endpoint = True
    return func


class AuthMiddleware:
    """认证中间件类，用于集中管理认证逻辑."""

    def __init__(self, auth_manager: Any):
        """初始化认证中间件.

        Args:
            auth_manager: 认证管理器实例
        """
        self.auth_manager = auth_manager

    def check_auth(self, request: Any) -> Optional[Dict]:
        """检查请求的认证状态.

        Args:
            request: HTTP 请求对象

        Returns:
            用户信息字典，失败返回 None
        """
        # 获取 Authorization header
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header[7:]
        role = self.auth_manager.validate_token(token)

        if not role:
            return None

        token_info = self.auth_manager.config.get('tokens', {}).get(token, {})
        return {
            'username': token_info.get('username', 'unknown'),
            'role': role,
            'token': token
        }

    def check_permission(
        self,
        user_info: Dict,
        permission_name: str
    ) -> bool:
        """检查用户是否有指定权限.

        Args:
            user_info: 用户信息字典
            permission_name: 权限名称

        Returns:
            是否有权限
        """
        role = user_info.get('role', 'guest')
        return self.auth_manager.check_permission(role, permission_name)