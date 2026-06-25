"""统一错误处理模块.

提供安全的错误响应,避免泄露敏感信息。
"""

import uuid
import logging
from enum import Enum
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """错误代码枚举."""
    
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_INPUT = "invalid_input"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SERVICE_UNAVAILABLE = "service_unavailable"


def safe_error_response(
    error: Exception,
    default_message: str = "Internal error",
    error_code: Optional[ErrorCode] = None,
    status_code: int = 500
) -> Dict[str, Any]:
    """生成安全的错误响应.
    
    避免泄露内部错误细节,生成唯一错误 ID 用于追踪。
    
    Args:
        error: 异常对象
        default_message: 用户友好的错误消息
        error_code: 错误代码枚举
        status_code: HTTP 状态码
        
    Returns:
        错误响应字典
    """
    error_id = str(uuid.uuid4())
    
    # 记录详细错误日志
    logger.error(
        f"[{error_id}] Error occurred: {type(error).__name__}: {error}",
        exc_info=True,
        extra={
            'error_id': error_id,
            'error_type': type(error).__name__,
            'status_code': status_code
        }
    )
    
    # 构建安全的错误响应
    response = {
        'success': False,
        'error': default_message,
        'code': status_code,
        'error_id': error_id
    }
    
    if error_code:
        response['error_code'] = error_code.value
    
    return response


def create_error_response(
    message: str,
    status_code: int = 400,
    error_code: Optional[ErrorCode] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """创建自定义错误响应.
    
    Args:
        message: 错误消息
        status_code: HTTP 状态码
        error_code: 错误代码枚举
        details: 额外的错误详情
        
    Returns:
        错误响应字典
    """
    response = {
        'success': False,
        'error': message,
        'code': status_code
    }
    
    if error_code:
        response['error_code'] = error_code.value
    
    if details:
        response['details'] = details
    
    return response


def handle_validation_error(error: Exception) -> Dict[str, Any]:
    """处理验证错误.
    
    Args:
        error: Pydantic 验证错误
        
    Returns:
        错误响应字典
    """
    from pydantic import ValidationError
    
    if isinstance(error, ValidationError):
        errors = error.errors()
        return {
            'success': False,
            'error': 'Invalid input parameters',
            'code': 400,
            'error_code': ErrorCode.INVALID_INPUT.value,
            'details': [
                {
                    'field': '.'.join(str(loc) for loc in e['loc']),
                    'message': e['msg'],
                    'type': e['type']
                }
                for e in errors
            ]
        }
    
    return safe_error_response(error, "Validation error", ErrorCode.INVALID_INPUT, 400)


def handle_not_found_error(resource_type: str, resource_id: str) -> Dict[str, Any]:
    """处理资源未找到错误.
    
    Args:
        resource_type: 资源类型（如 'knowledge_base', 'atom'）
        resource_id: 资源 ID
        
    Returns:
        错误响应字典
    """
    return {
        'success': False,
        'error': f'{resource_type.capitalize()} not found',
        'code': 404,
        'error_code': ErrorCode.NOT_FOUND.value,
        'resource_type': resource_type,
        'resource_id': resource_id
    }


def handle_permission_denied(
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None
) -> Dict[str, Any]:
    """处理权限拒绝错误.
    
    Args:
        action: 尝试执行的操作
        resource_type: 资源类型
        resource_id: 资源 ID
        
    Returns:
        错误响应字典
    """
    message = f"Permission denied for action: {action}"
    
    if resource_type:
        message += f" on {resource_type}"
    
    response = {
        'success': False,
        'error': message,
        'code': 403,
        'error_code': ErrorCode.PERMISSION_DENIED.value,
        'action': action
    }
    
    if resource_type:
        response['resource_type'] = resource_type
    if resource_id:
        response['resource_id'] = resource_id
    
    return response


def handle_rate_limit_exceeded(
    retry_after: int,
    limit: int,
    window: str = "minute"
) -> Dict[str, Any]:
    """处理速率限制错误.
    
    Args:
        retry_after: 重试等待时间（秒）
        limit: 限制次数
        window: 时间窗口
        
    Returns:
        错误响应字典
    """
    return {
        'success': False,
        'error': f'Rate limit exceeded. Max {limit} requests per {window}',
        'code': 429,
        'error_code': ErrorCode.RATE_LIMIT_EXCEEDED.value,
        'retry_after': retry_after,
        'limit': limit,
        'window': window
    }
