"""输入验证与净化工具.

提供输入验证、XSS 防护、类型检查等功能。
"""

import re
import html
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse


class InputValidator:
    """输入验证器，用于验证和净化用户输入."""

    # 邮箱正则
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    # 用户名正则（字母、数字、下划线）
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,50}$')

    # UUID 正则
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )

    # 危险的 HTML 标签
    DANGEROUS_TAGS = [
        'script', 'iframe', 'object', 'embed', 'form',
        'input', 'button', 'meta', 'link', 'style',
    ]

    # 危险的 HTML 属性
    DANGEROUS_ATTRS = [
        'onclick', 'onerror', 'onload', 'onmouseover',
        'onfocus', 'onblur', 'onsubmit', 'onchange',
    ]

    @classmethod
    def validate_email(cls, email: str) -> bool:
        """验证邮箱格式.

        Args:
            email: 邮箱地址

        Returns:
            是否合法
        """
        if not email or len(email) > 254:
            return False
        return bool(cls.EMAIL_PATTERN.match(email))

    @classmethod
    def validate_username(cls, username: str) -> bool:
        """验证用户名格式.

        Args:
            username: 用户名

        Returns:
            是否合法
        """
        if not username:
            return False
        return bool(cls.USERNAME_PATTERN.match(username))

    @classmethod
    def validate_uuid(cls, uuid_str: str) -> bool:
        """验证 UUID 格式.

        Args:
            uuid_str: UUID 字符串

        Returns:
            是否合法
        """
        if not uuid_str:
            return False
        return bool(cls.UUID_PATTERN.match(uuid_str))

    @classmethod
    def validate_url(
        cls,
        url: str,
        allowed_schemes: Optional[List[str]] = None
    ) -> bool:
        """验证 URL 格式和协议.

        Args:
            url: URL 字符串
            allowed_schemes: 允许的协议列表（默认 ['http', 'https']）

        Returns:
            是否合法
        """
        if not url:
            return False

        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']

        try:
            parsed = urlparse(url)
            # 检查协议
            if parsed.scheme.lower() not in allowed_schemes:
                return False
            # 检查主机名
            if not parsed.netloc:
                return False
            return True
        except Exception:
            return False

    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """净化 HTML，移除危险标签和属性.

        Args:
            text: 原始文本

        Returns:
            净化后的文本
        """
        if not text:
            return ''

        # 转义 HTML 实体
        sanitized = html.escape(text)

        # 移除危险标签
        for tag in cls.DANGEROUS_TAGS:
            # 移除开标签
            sanitized = re.sub(
                rf'<{tag}[^>]*>',
                '',
                sanitized,
                flags=re.IGNORECASE
            )
            # 移除闭标签
            sanitized = re.sub(
                rf'</{tag}>',
                '',
                sanitized,
                flags=re.IGNORECASE
            )

        # 移除危险属性
        for attr in cls.DANGEROUS_ATTRS:
            sanitized = re.sub(
                rf'\s+{attr}\s*=\s*["\'][^"\']*["\']',
                '',
                sanitized,
                flags=re.IGNORECASE
            )

        return sanitized

    @classmethod
    def sanitize_text(cls, text: str, max_length: Optional[int] = None) -> str:
        """净化纯文本，移除控制字符和危险内容.

        Args:
            text: 原始文本
            max_length: 最大长度限制

        Returns:
            净化后的文本
        """
        if not text:
            return ''

        # 移除控制字符（保留换行符和制表符）
        sanitized = ''.join(
            char for char in text
            if char.isprintable() or char in '\n\t'
        )

        # 移除潜在的脚本注入
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        # 长度限制
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized.strip()

    @classmethod
    def validate_int(
        cls,
        value: Any,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None
    ) -> Optional[int]:
        """验证并转换为整数.

        Args:
            value: 原始值
            min_val: 最小值
            max_val: 最大值

        Returns:
            验证后的整数，失败返回 None
        """
        try:
            int_val = int(value)

            if min_val is not None and int_val < min_val:
                return None

            if max_val is not None and int_val > max_val:
                return None

            return int_val
        except (TypeError, ValueError):
            return None

    @classmethod
    def validate_str(
        cls,
        value: Any,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None
    ) -> Optional[str]:
        """验证字符串.

        Args:
            value: 原始值
            min_length: 最小长度
            max_length: 最大长度
            pattern: 正则模式

        Returns:
            验证后的字符串，失败返回 None
        """
        if not isinstance(value, str):
            return None

        # 长度检查
        if min_length is not None and len(value) < min_length:
            return None

        if max_length is not None and len(value) > max_length:
            return None

        # 模式检查
        if pattern and not re.match(pattern, value):
            return None

        return value

    @classmethod
    def validate_dict(
        cls,
        data: Dict[str, Any],
        schema: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """验证字典数据.

        Args:
            data: 原始数据
            schema: 验证模式
                {
                    'field_name': {
                        'type': 'str',  # str, int, email, url, bool
                        'required': True,
                        'min_length': 1,
                        'max_length': 100,
                        'pattern': r'^[a-z]+$',
                        'default': 'default_value',
                    }
                }

        Returns:
            验证后的数据
        """
        validated = {}

        for field, rules in schema.items():
            value = data.get(field)

            # 检查必需字段
            if value is None:
                if rules.get('required', False):
                    raise ValueError(f"Missing required field: {field}")
                # 使用默认值
                if 'default' in rules:
                    validated[field] = rules['default']
                continue

            # 类型验证
            field_type = rules.get('type', 'str')

            if field_type == 'str':
                value = cls.validate_str(
                    value,
                    min_length=rules.get('min_length'),
                    max_length=rules.get('max_length'),
                    pattern=rules.get('pattern')
                )
            elif field_type == 'int':
                value = cls.validate_int(
                    value,
                    min_val=rules.get('min_val'),
                    max_val=rules.get('max_val')
                )
            elif field_type == 'email':
                if not cls.validate_email(value):
                    value = None
            elif field_type == 'url':
                if not cls.validate_url(value):
                    value = None
            elif field_type == 'bool':
                if not isinstance(value, bool):
                    if isinstance(value, str):
                        value = value.lower() in ('true', '1', 'yes')
                    elif isinstance(value, int):
                        value = value == 1
                    else:
                        value = None

            if value is None:
                if rules.get('required', False):
                    raise ValueError(f"Invalid value for field: {field}")
                if 'default' in rules:
                    value = rules['default']

            validated[field] = value

        return validated

    @classmethod
    def check_xss(cls, text: str) -> bool:
        """检查文本是否包含 XSS 攻击特征.

        Args:
            text: 要检查的文本

        Returns:
            是否包含 XSS 特征
        """
        if not text:
            return False

        text_lower = text.lower()

        # 检查危险的 HTML 标签
        for tag in cls.DANGEROUS_TAGS:
            if f'<{tag}' in text_lower or f'</{tag}' in text_lower:
                return True

        # 检查危险的属性
        for attr in cls.DANGEROUS_ATTRS:
            if f'{attr}=' in text_lower:
                return True

        # 检查 javascript: 协议
        if 'javascript:' in text_lower:
            return True

        # 检查 data: 协议（可能用于注入）
        if 'data:' in text_lower:
            return True

        return False


def sanitize_input(
    data: Union[str, Dict, List],
    max_length: Optional[int] = None
) -> Union[str, Dict, List]:
    """净化输入数据（递归）.

    Args:
        data: 原始数据
        max_length: 最大长度限制

    Returns:
        净化后的数据
    """
    if isinstance(data, str):
        return InputValidator.sanitize_text(data, max_length)
    elif isinstance(data, dict):
        return {
            key: sanitize_input(value, max_length)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_input(item, max_length) for item in data]
    else:
        return data
