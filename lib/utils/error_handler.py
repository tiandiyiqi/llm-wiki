"""统一错误处理模块.

提供标准化错误响应、异常处理和日志记录。
"""

import logging
import traceback
from typing import Any, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """错误代码枚举."""

    # 通用错误 (1000-1999)
    UNKNOWN_ERROR = 1000
    INVALID_REQUEST = 1001
    MISSING_PARAMETER = 1002
    INVALID_PARAMETER = 1003

    # 认证错误 (2000-2999)
    UNAUTHORIZED = 2000
    INVALID_TOKEN = 2001
    TOKEN_EXPIRED = 2002
    PERMISSION_DENIED = 2003

    # 资源错误 (3000-3999)
    NOT_FOUND = 3000
    ALREADY_EXISTS = 3001
    RESOURCE_DELETED = 3002

    # 限制错误 (4000-4999)
    RATE_LIMIT_EXCEEDED = 4000
    QUOTA_EXCEEDED = 4001

    # 服务器错误 (5000-5999)
    INTERNAL_ERROR = 5000
    DATABASE_ERROR = 5001
    EXTERNAL_SERVICE_ERROR = 5002


class APIError(Exception):
    """API 错误基类.

    所有 API 错误都应该继承此类。
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化 API 错误.

        Args:
            message: 错误消息
            error_code: 错误代码
            status_code: HTTP 状态码
            details: 详细信息
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式.

        Returns:
            错误信息字典
        """
        error_dict = {
            'success': False,
            'error': {
                'code': self.error_code.value,
                'message': self.message,
                'type': self.error_code.name,
            }
        }

        if self.details:
            error_dict['error']['details'] = self.details

        return error_dict


class ValidationError(APIError):
    """验证错误."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """初始化验证错误.

        Args:
            message: 错误消息
            field: 字段名
            details: 详细信息
        """
        error_details = details or {}
        if field:
            error_details['field'] = field

        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_PARAMETER,
            status_code=400,
            details=error_details
        )


class AuthenticationError(APIError):
    """认证错误."""

    def __init__(
        self,
        message: str = "Authentication required",
        error_code: ErrorCode = ErrorCode.UNAUTHORIZED
    ):
        """初始化认证错误.

        Args:
            message: 错误消息
            error_code: 错误代码
        """
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401
        )


class PermissionError(APIError):
    """权限错误."""

    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: Optional[str] = None
    ):
        """初始化权限错误.

        Args:
            message: 错误消息
            required_permission: 所需权限
        """
        details = {}
        if required_permission:
            details['required_permission'] = required_permission

        super().__init__(
            message=message,
            error_code=ErrorCode.PERMISSION_DENIED,
            status_code=403,
            details=details
        )


class NotFoundError(APIError):
    """资源未找到错误."""

    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None
    ):
        """初始化资源未找到错误.

        Args:
            resource_type: 资源类型
            resource_id: 资源 ID
        """
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} with id '{resource_id}' not found"

        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            status_code=404,
            details={
                'resource_type': resource_type,
                'resource_id': resource_id
            }
        )


class RateLimitError(APIError):
    """速率限制错误."""

    def __init__(
        self,
        retry_after: int,
        limit: int,
        window_seconds: int
    ):
        """初始化速率限制错误.

        Args:
            retry_after: 重试等待时间（秒）
            limit: 限制数量
            window_seconds: 时间窗口（秒）
        """
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details={
                'retry_after': retry_after,
                'limit': limit,
                'window_seconds': window_seconds
            }
        )


def handle_error(
    error: Exception,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """处理错误并返回标准化响应.

    Args:
        error: 异常对象
        include_traceback: 是否包含堆栈跟踪（仅调试模式）

    Returns:
        错误响应字典
    """
    if isinstance(error, APIError):
        # 已知的 API 错误
        response = error.to_dict()

        # 记录错误
        logger.error(
            f"API Error [{error.error_code.name}]: {error.message}",
            extra={'details': error.details}
        )

    else:
        # 未知错误
        response = {
            'success': False,
            'error': {
                'code': ErrorCode.UNKNOWN_ERROR.value,
                'message': 'An unexpected error occurred',
                'type': 'UNKNOWN_ERROR',
            }
        }

        # 记录详细错误
        logger.error(
            f"Unexpected error: {str(error)}",
            exc_info=True
        )

        # 调试模式下包含堆栈跟踪
        if include_traceback:
            response['error']['traceback'] = traceback.format_exc()

    return response


def safe_execute(func):
    """安全执行装饰器.

    自动捕获异常并返回标准化错误响应。

    使用方式：
        @safe_execute
        def handle_api_request(self, *args, **kwargs):
            # 业务逻辑
            pass

    Args:
        func: 要包装的函数

    Returns:
        包装后的函数
    """
    from functools import wraps

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except APIError as e:
            # API 错误
            if hasattr(self, '_json_response'):
                self._json_response(e.to_dict(), e.status_code)
            return None
        except Exception as e:
            # 未知错误
            logger.exception(f"Unexpected error in {func.__name__}")
            if hasattr(self, '_json_response'):
                self._json_response({
                    'success': False,
                    'error': {
                        'code': ErrorCode.UNKNOWN_ERROR.value,
                        'message': 'Internal server error',
                        'type': 'INTERNAL_ERROR',
                    }
                }, 500)
            return None

    return wrapper
