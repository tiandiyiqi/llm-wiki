"""工具函数模块."""

from .sql_validator import SQLValidator, safe_identifier, build_parameterized_query
from .input_validator import InputValidator, sanitize_input
from .rate_limiter import RateLimiter, get_rate_limiter, rate_limit, IPWhitelist, get_ip_whitelist
from .error_handler import (
    APIError,
    ValidationError,
    AuthenticationError,
    PermissionError,
    NotFoundError,
    RateLimitError,
    ErrorCode,
    handle_error,
    safe_execute,
)
from .query_optimizer import (
    BatchLoader,
    optimize_query,
    QueryOptimizer,
    NPlusOneDetector,
    get_nplus_one_detector,
)

__all__ = [
    # SQL 验证
    'SQLValidator',
    'safe_identifier',
    'build_parameterized_query',

    # 输入验证
    'InputValidator',
    'sanitize_input',

    # 速率限制
    'RateLimiter',
    'get_rate_limiter',
    'rate_limit',
    'IPWhitelist',
    'get_ip_whitelist',

    # 错误处理
    'APIError',
    'ValidationError',
    'AuthenticationError',
    'PermissionError',
    'NotFoundError',
    'RateLimitError',
    'ErrorCode',
    'handle_error',
    'safe_execute',

    # 查询优化
    'BatchLoader',
    'optimize_query',
    'QueryOptimizer',
    'NPlusOneDetector',
    'get_nplus_one_detector',
]

