"""日志脱敏工具，防止敏感信息泄露到日志中."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class LogSanitizer:
    """日志脱敏处理器."""

    # 敏感字段名称模式
    SENSITIVE_FIELDS = {
        'password', 'passwd', 'pwd', 'secret', 'token', 'api_key',
        'apikey', 'access_key', 'secret_key', 'private_key',
        'authorization', 'cookie', 'session_id', 'credit_card',
        'ssn', 'social_security', 'phone', 'email',
    }

    # 敏感值模式（正则表达式）
    SENSITIVE_PATTERNS = [
        # API 密钥（覆盖 sk-、sk-proj-、sk_proj-、pk-、pk_live- 等前缀）
        re.compile(r'(sk|pk)([-_][a-zA-Z0-9_-]+)?-[a-zA-Z0-9]{20,}'),
        # Bearer Token
        re.compile(r'Bearer\s+[a-zA-Z0-9\-._~+/]+=*'),
        # JWT Token
        re.compile(
            r'eyJ[a-zA-Z0-9\-._~+/]+=*\.'
            r'eyJ[a-zA-Z0-9\-._~+/]+=*\.'
            r'[a-zA-Z0-9\-._~+/]+=*'
        ),
        # 邮箱地址
        re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        # IP 地址（可选脱敏）
        re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'),
        # 信用卡号
        re.compile(r'\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}'),
    ]

    @classmethod
    def sanitize_value(cls, key: str, value: Any) -> Any:
        """脱敏单个值.

        Args:
            key: 字段名
            value: 字段值

        Returns:
            脱敏后的值，非字符串类型原样返回
        """
        if not isinstance(value, str):
            return value

        # 检查字段名是否敏感
        key_lower = key.lower()
        for sensitive in cls.SENSITIVE_FIELDS:
            if sensitive in key_lower:
                return cls._mask_value(value)

        # 检查值是否匹配敏感模式
        for pattern in cls.SENSITIVE_PATTERNS:
            if pattern.search(value):
                return cls._mask_value(value)

        return value

    @classmethod
    def _mask_value(cls, value: str) -> str:
        """掩码敏感值.

        Args:
            value: 原始值

        Returns:
            掩码后的值，保留首尾各2字符
        """
        if len(value) <= 4:
            return '****'
        return f"{value[:2]}****{value[-2:]}"

    @classmethod
    def sanitize_dict(cls, data: dict) -> dict:
        """脱敏字典中的敏感值.

        递归处理嵌套字典，对字符串值进行脱敏检查。

        Args:
            data: 原始字典

        Returns:
            脱敏后的新字典（不修改原字典）
        """
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize_value(key, value)
            else:
                sanitized[key] = value
        return sanitized

    @classmethod
    def sanitize_message(cls, message: str) -> str:
        """脱敏日志消息中的敏感信息.

        对消息文本中匹配敏感模式的子串替换为 [REDACTED]。

        Args:
            message: 原始日志消息

        Returns:
            脱敏后的消息
        """
        for pattern in cls.SENSITIVE_PATTERNS:
            message = pattern.sub('[REDACTED]', message)
        return message
