#!/usr/bin/env python3
"""独立测试输入验证功能."""

import re
import html
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse


class InputValidator:
    """输入验证器（独立版本用于测试）."""

    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,50}$')
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    DANGEROUS_TAGS = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'meta', 'link', 'style']
    DANGEROUS_ATTRS = ['onclick', 'onerror', 'onload', 'onmouseover', 'onfocus', 'onblur', 'onsubmit', 'onchange']

    @classmethod
    def validate_email(cls, email: str) -> bool:
        if not email or len(email) > 254:
            return False
        return bool(cls.EMAIL_PATTERN.match(email))

    @classmethod
    def validate_username(cls, username: str) -> bool:
        if not username:
            return False
        return bool(cls.USERNAME_PATTERN.match(username))

    @classmethod
    def sanitize_html(cls, text: str) -> str:
        if not text:
            return ''
        sanitized = html.escape(text)
        for tag in cls.DANGEROUS_TAGS:
            sanitized = re.sub(rf'<{tag}[^>]*>', '', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(rf'</{tag}>', '', sanitized, flags=re.IGNORECASE)
        for attr in cls.DANGEROUS_ATTRS:
            sanitized = re.sub(rf'\s+{attr}\s*=\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)
        return sanitized

    @classmethod
    def sanitize_text(cls, text: str, max_length: Optional[int] = None) -> str:
        if not text:
            return ''
        sanitized = ''.join(char for char in text if char.isprintable() or char in '\n\t')
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        return sanitized.strip()

    @classmethod
    def validate_int(cls, value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> Optional[int]:
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
    def check_xss(cls, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        for tag in cls.DANGEROUS_TAGS:
            if f'<{tag}' in text_lower or f'</{tag}' in text_lower:
                return True
        for attr in cls.DANGEROUS_ATTRS:
            if f'{attr}=' in text_lower:
                return True
        if 'javascript:' in text_lower or 'data:' in text_lower:
            return True
        return False


def test_validate_email():
    print("\n=== 测试邮箱验证 ===")
    assert InputValidator.validate_email('user@example.com')
    assert InputValidator.validate_email('test.user@domain.org')
    print("✅ 合法邮箱验证通过")
    assert not InputValidator.validate_email('invalid-email')
    assert not InputValidator.validate_email('@example.com')
    assert not InputValidator.validate_email('user@')
    print("✅ 非法邮箱验证通过")


def test_validate_username():
    print("\n=== 测试用户名验证 ===")
    assert InputValidator.validate_username('john_doe')
    assert InputValidator.validate_username('user123')
    print("✅ 合法用户名验证通过")
    assert not InputValidator.validate_username('ab')  # 太短
    assert not InputValidator.validate_username('user@name')  # 非法字符
    print("✅ 非法用户名验证通过")


def test_sanitize_html():
    print("\n=== 测试 HTML 净化 ===")
    text = "<script>alert('XSS')</script>Hello"
    sanitized = InputValidator.sanitize_html(text)
    assert '<script>' not in sanitized
    print(f"✅ HTML 净化成功: {sanitized}")


def test_sanitize_text():
    print("\n=== 测试文本净化 ===")
    text = "Hello\x00World\nNew Line"
    sanitized = InputValidator.sanitize_text(text)
    assert '\x00' not in sanitized
    assert '\n' in sanitized  # 保留换行符
    print(f"✅ 文本净化成功: {sanitized}")

    # 测试长度限制
    long_text = "A" * 1000
    sanitized = InputValidator.sanitize_text(long_text, max_length=100)
    assert len(sanitized) == 100
    print("✅ 长度限制成功")


def test_validate_int():
    print("\n=== 测试整数验证 ===")
    assert InputValidator.validate_int(42) == 42
    assert InputValidator.validate_int("123") == 123
    assert InputValidator.validate_int(5, min_val=1, max_val=10) == 5
    print("✅ 合法整数验证通过")

    assert InputValidator.validate_int("abc") is None
    assert InputValidator.validate_int(15, min_val=1, max_val=10) is None
    print("✅ 非法整数验证通过")


def test_check_xss():
    print("\n=== 测试 XSS 检测 ===")
    assert InputValidator.check_xss("<script>alert('XSS')</script>")
    assert InputValidator.check_xss("<img onerror='alert(1)' src=x>")
    assert InputValidator.check_xss("<a onclick='evil()'>Click</a>")
    assert InputValidator.check_xss("javascript:alert(1)")
    print("✅ XSS 特征检测通过")

    assert not InputValidator.check_xss("Normal text")
    assert not InputValidator.check_xss("user@example.com")
    print("✅ 正常文本验证通过")


def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("输入验证功能测试（独立版本）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        test_validate_email()
        test_validate_username()
        test_sanitize_html()
        test_sanitize_text()
        test_validate_int()
        test_check_xss()

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("✅ 所有测试通过！")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
