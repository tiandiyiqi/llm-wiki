"""input_validator 模块单元测试

测试范围：
1. InputValidator 类的所有验证方法
2. sanitize_input 顶层函数
3. 边界情况和注入攻击防护
"""

import pytest
from typing import Any, Dict


# ---------------------------------------------------------------------------
# 导入被测模块
# ---------------------------------------------------------------------------
try:
    from lib.utils.input_validator import InputValidator, sanitize_input
except ImportError as exc:
    pytest.skip(f"Cannot import input_validator: {exc}", allow_module_level=True)


# ============================================================================
# InputValidator.validate_email 测试
# ============================================================================


class TestValidateEmail:
    """邮箱验证测试"""

    def test_valid_email(self):
        assert InputValidator.validate_email('user@example.com') is True

    def test_valid_email_with_dots(self):
        assert InputValidator.validate_email('user.name@example.co.uk') is True

    def test_valid_email_with_plus(self):
        assert InputValidator.validate_email('user+tag@example.com') is True

    def test_invalid_no_at(self):
        assert InputValidator.validate_email('userexample.com') is False

    def test_invalid_no_domain(self):
        assert InputValidator.validate_email('user@') is False

    def test_invalid_no_tld(self):
        assert InputValidator.validate_email('user@example') is False

    def test_invalid_short_tld(self):
        assert InputValidator.validate_email('user@example.c') is False

    def test_invalid_spaces(self):
        assert InputValidator.validate_email('user @example.com') is False

    def test_empty_string(self):
        assert InputValidator.validate_email('') is False

    def test_none_input(self):
        assert InputValidator.validate_email(None) is False

    def test_too_long_email(self):
        assert InputValidator.validate_email('a' * 255 + '@example.com') is False


# ============================================================================
# InputValidator.validate_username 测试
# ============================================================================


class TestValidateUsername:
    """用户名验证测试"""

    def test_valid_username(self):
        assert InputValidator.validate_username('alice_123') is True

    def test_valid_alphanumeric(self):
        assert InputValidator.validate_username('bob123') is True

    def test_valid_underscores(self):
        assert InputValidator.validate_username('user_name') is True

    def test_too_short(self):
        assert InputValidator.validate_username('ab') is False

    def test_too_long(self):
        assert InputValidator.validate_username('a' * 51) is False

    def test_min_length_boundary(self):
        assert InputValidator.validate_username('abc') is True

    def test_max_length_boundary(self):
        assert InputValidator.validate_username('a' * 50) is True

    def test_invalid_special_chars(self):
        assert InputValidator.validate_username('user-name') is False

    def test_invalid_spaces(self):
        assert InputValidator.validate_username('user name') is False

    def test_empty_string(self):
        assert InputValidator.validate_username('') is False

    def test_none_input(self):
        assert InputValidator.validate_username(None) is False


# ============================================================================
# InputValidator.validate_uuid 测试
# ============================================================================


class TestValidateUuid:
    """UUID 验证测试"""

    def test_valid_uuid(self):
        assert InputValidator.validate_uuid('550e8400-e29b-41d4-a716-446655440000') is True

    def test_valid_uuid_uppercase(self):
        assert InputValidator.validate_uuid('550E8400-E29B-41D4-A716-446655440000') is True

    def test_invalid_uuid_format(self):
        assert InputValidator.validate_uuid('not-a-uuid') is False

    def test_invalid_uuid_too_short(self):
        assert InputValidator.validate_uuid('550e8400-e29b-41d4') is False

    def test_empty_string(self):
        assert InputValidator.validate_uuid('') is False

    def test_none_input(self):
        assert InputValidator.validate_uuid(None) is False


# ============================================================================
# InputValidator.validate_url 测试
# ============================================================================


class TestValidateUrl:
    """URL 验证测试"""

    def test_valid_http(self):
        assert InputValidator.validate_url('http://example.com') is True

    def test_valid_https(self):
        assert InputValidator.validate_url('https://example.com') is True

    def test_valid_with_path(self):
        assert InputValidator.validate_url('https://example.com/path/to/page') is True

    def test_valid_with_query(self):
        assert InputValidator.validate_url('https://example.com?q=test') is True

    def test_invalid_ftp(self):
        assert InputValidator.validate_url('ftp://example.com') is False

    def test_invalid_javascript(self):
        assert InputValidator.validate_url('javascript:alert(1)') is False

    def test_invalid_no_scheme(self):
        assert InputValidator.validate_url('example.com') is False

    def test_invalid_no_host(self):
        assert InputValidator.validate_url('http://') is False

    def test_custom_allowed_schemes(self):
        assert InputValidator.validate_url('ftp://files.example.com', allowed_schemes=['ftp']) is True

    def test_empty_string(self):
        assert InputValidator.validate_url('') is False

    def test_none_input(self):
        assert InputValidator.validate_url(None) is False


# ============================================================================
# InputValidator.sanitize_html 测试
# ============================================================================


class TestSanitizeHtml:
    """HTML 净化测试"""

    def test_removes_script_tag(self):
        result = InputValidator.sanitize_html('<script>alert("xss")</script>')
        assert '<script' not in result.lower()
        assert '</script>' not in result.lower()

    def test_removes_iframe_tag(self):
        result = InputValidator.sanitize_html('<iframe src="evil.com"></iframe>')
        assert '<iframe' not in result.lower()

    def test_removes_onclick_attr(self):
        result = InputValidator.sanitize_html('<div onclick="alert(1)">text</div>')
        # sanitize_html 做的是 HTML 转义，onclick 被转义为不可执行
        assert '<div onclick=' not in result  # 原始 HTML 标签被转义

    def test_removes_onerror_attr(self):
        result = InputValidator.sanitize_html('<img onerror="alert(1)">')
        # sanitize_html 做的是 HTML 转义，onerror 被转义为不可执行
        assert '<img onerror=' not in result  # 原始 HTML 标签被转义

    def test_empty_string(self):
        assert InputValidator.sanitize_html('') == ''

    def test_none_input(self):
        assert InputValidator.sanitize_html(None) == ''

    def test_safe_text_preserved(self):
        result = InputValidator.sanitize_html('Hello World')
        assert 'Hello World' in result

    def test_escapes_html_entities(self):
        result = InputValidator.sanitize_html('<b>bold</b>')
        # html.escape 会转义 < 和 >
        assert '&lt;' in result or '<b>' not in result


# ============================================================================
# InputValidator.sanitize_text 测试
# ============================================================================


class TestSanitizeText:
    """文本净化测试"""

    def test_removes_control_chars(self):
        result = InputValidator.sanitize_text('hello\x00world')
        assert '\x00' not in result
        assert 'hello' in result
        assert 'world' in result

    def test_preserves_newlines(self):
        result = InputValidator.sanitize_text('line1\nline2')
        assert '\n' in result

    def test_preserves_tabs(self):
        result = InputValidator.sanitize_text('col1\tcol2')
        assert '\t' in result

    def test_removes_script_injection(self):
        result = InputValidator.sanitize_text('<script>alert(1)</script>')
        assert '<script' not in result.lower()

    def test_max_length(self):
        result = InputValidator.sanitize_text('a' * 200, max_length=100)
        assert len(result) == 100

    def test_no_max_length(self):
        text = 'a' * 1000
        result = InputValidator.sanitize_text(text)
        assert len(result) == 1000

    def test_empty_string(self):
        assert InputValidator.sanitize_text('') == ''

    def test_none_input(self):
        assert InputValidator.sanitize_text(None) == ''

    def test_strips_whitespace(self):
        result = InputValidator.sanitize_text('  hello  ')
        assert result == 'hello'


# ============================================================================
# InputValidator.validate_int 测试
# ============================================================================


class TestValidateInt:
    """整数验证测试"""

    def test_valid_int(self):
        assert InputValidator.validate_int(42) == 42

    def test_valid_string_int(self):
        assert InputValidator.validate_int('42') == 42

    def test_min_val(self):
        assert InputValidator.validate_int(5, min_val=1) == 5
        assert InputValidator.validate_int(0, min_val=1) is None

    def test_max_val(self):
        assert InputValidator.validate_int(50, max_val=100) == 50
        assert InputValidator.validate_int(101, max_val=100) is None

    def test_min_max_combined(self):
        assert InputValidator.validate_int(50, min_val=1, max_val=100) == 50
        assert InputValidator.validate_int(0, min_val=1, max_val=100) is None
        assert InputValidator.validate_int(101, min_val=1, max_val=100) is None

    def test_invalid_string(self):
        assert InputValidator.validate_int('not_a_number') is None

    def test_none_input(self):
        assert InputValidator.validate_int(None) is None

    def test_float_input(self):
        assert InputValidator.validate_int(3.7) == 3

    def test_boundary_values(self):
        assert InputValidator.validate_int(1, min_val=1) == 1
        assert InputValidator.validate_int(100, max_val=100) == 100


# ============================================================================
# InputValidator.validate_str 测试
# ============================================================================


class TestValidateStr:
    """字符串验证测试"""

    def test_valid_string(self):
        assert InputValidator.validate_str('hello') == 'hello'

    def test_min_length(self):
        assert InputValidator.validate_str('ab', min_length=3) is None
        assert InputValidator.validate_str('abc', min_length=3) == 'abc'

    def test_max_length(self):
        assert InputValidator.validate_str('a' * 101, max_length=100) is None
        assert InputValidator.validate_str('a' * 100, max_length=100) == 'a' * 100

    def test_pattern(self):
        assert InputValidator.validate_str('abc', pattern=r'^[a-z]+$') == 'abc'
        assert InputValidator.validate_str('ABC', pattern=r'^[a-z]+$') is None

    def test_non_string_input(self):
        assert InputValidator.validate_str(123) is None
        assert InputValidator.validate_str(None) is None
        assert InputValidator.validate_str([]) is None

    def test_empty_string_with_min_length(self):
        assert InputValidator.validate_str('', min_length=1) is None

    def test_empty_string_no_min_length(self):
        assert InputValidator.validate_str('') == ''


# ============================================================================
# InputValidator.validate_dict 测试
# ============================================================================


class TestValidateDict:
    """字典验证测试"""

    def test_simple_schema(self):
        schema = {
            'name': {'type': 'str', 'required': True, 'min_length': 1},
        }
        result = InputValidator.validate_dict({'name': 'Alice'}, schema)
        assert result == {'name': 'Alice'}

    def test_missing_required_field(self):
        schema = {
            'name': {'type': 'str', 'required': True},
        }
        with pytest.raises(ValueError, match="Missing required field"):
            InputValidator.validate_dict({}, schema)

    def test_optional_field_with_default(self):
        schema = {
            'role': {'type': 'str', 'required': False, 'default': 'reader'},
        }
        result = InputValidator.validate_dict({}, schema)
        assert result == {'role': 'reader'}

    def test_int_type(self):
        schema = {
            'age': {'type': 'int', 'required': True, 'min_val': 0, 'max_val': 150},
        }
        result = InputValidator.validate_dict({'age': 25}, schema)
        assert result == {'age': 25}

    def test_int_type_invalid(self):
        schema = {
            'age': {'type': 'int', 'required': True},
        }
        with pytest.raises(ValueError, match="Invalid value"):
            InputValidator.validate_dict({'age': 'not_a_number'}, schema)

    def test_email_type(self):
        schema = {
            'email': {'type': 'email', 'required': True},
        }
        result = InputValidator.validate_dict({'email': 'user@example.com'}, schema)
        assert result == {'email': 'user@example.com'}

    def test_email_type_invalid(self):
        schema = {
            'email': {'type': 'email', 'required': True},
        }
        with pytest.raises(ValueError, match="Invalid value"):
            InputValidator.validate_dict({'email': 'not-an-email'}, schema)

    def test_url_type(self):
        schema = {
            'website': {'type': 'url', 'required': True},
        }
        result = InputValidator.validate_dict({'website': 'https://example.com'}, schema)
        assert result == {'website': 'https://example.com'}

    def test_url_type_invalid(self):
        schema = {
            'website': {'type': 'url', 'required': True},
        }
        with pytest.raises(ValueError, match="Invalid value"):
            InputValidator.validate_dict({'website': 'not-a-url'}, schema)

    def test_bool_type(self):
        schema = {
            'active': {'type': 'bool', 'required': True},
        }
        result = InputValidator.validate_dict({'active': True}, schema)
        assert result == {'active': True}

    def test_bool_type_from_string(self):
        schema = {
            'active': {'type': 'bool', 'required': True},
        }
        result = InputValidator.validate_dict({'active': 'true'}, schema)
        assert result == {'active': True}

    def test_bool_type_from_int(self):
        schema = {
            'active': {'type': 'bool', 'required': True},
        }
        result = InputValidator.validate_dict({'active': 1}, schema)
        assert result == {'active': True}

    def test_bool_type_invalid(self):
        schema = {
            'active': {'type': 'bool', 'required': True},
        }
        with pytest.raises(ValueError, match="Invalid value"):
            InputValidator.validate_dict({'active': [1, 2]}, schema)

    def test_optional_field_not_provided(self):
        schema = {
            'name': {'type': 'str', 'required': True},
            'nickname': {'type': 'str', 'required': False},
        }
        result = InputValidator.validate_dict({'name': 'Alice'}, schema)
        assert 'name' in result
        assert 'nickname' not in result

    def test_invalid_optional_with_default(self):
        schema = {
            'age': {'type': 'int', 'required': False, 'default': 0},
        }
        result = InputValidator.validate_dict({'age': 'invalid'}, schema)
        assert result == {'age': 0}

    def test_str_with_pattern(self):
        schema = {
            'code': {'type': 'str', 'required': True, 'pattern': r'^[A-Z]{3}$'},
        }
        result = InputValidator.validate_dict({'code': 'ABC'}, schema)
        assert result == {'code': 'ABC'}

    def test_str_with_pattern_invalid(self):
        schema = {
            'code': {'type': 'str', 'required': True, 'pattern': r'^[A-Z]{3}$'},
        }
        with pytest.raises(ValueError, match="Invalid value"):
            InputValidator.validate_dict({'code': 'abc'}, schema)


# ============================================================================
# InputValidator.check_xss 测试
# ============================================================================


class TestCheckXss:
    """XSS 检测测试"""

    def test_detect_script_tag(self):
        assert InputValidator.check_xss('<script>alert(1)</script>') is True

    def test_detect_iframe_tag(self):
        assert InputValidator.check_xss('<iframe src="evil.com">') is True

    def test_detect_onclick(self):
        assert InputValidator.check_xss('<div onclick="alert(1)">') is True

    def test_detect_onerror(self):
        assert InputValidator.check_xss('<img onerror="alert(1)">') is True

    def test_detect_javascript_protocol(self):
        assert InputValidator.check_xss('javascript:alert(1)') is True

    def test_detect_data_protocol(self):
        assert InputValidator.check_xss('data:text/html,<script>alert(1)</script>') is True

    def test_safe_text(self):
        assert InputValidator.check_xss('Hello World') is False

    def test_safe_html_b_tag(self):
        assert InputValidator.check_xss('<b>bold</b>') is False

    def test_empty_string(self):
        assert InputValidator.check_xss('') is False

    def test_none_input(self):
        assert InputValidator.check_xss(None) is False

    def test_case_insensitive_script(self):
        assert InputValidator.check_xss('<SCRIPT>alert(1)</SCRIPT>') is True

    def test_case_insensitive_onclick(self):
        assert InputValidator.check_xss('<div ONCLICK="alert(1)">') is True


# ============================================================================
# sanitize_input 顶层函数测试
# ============================================================================


class TestSanitizeInput:
    """sanitize_input 顶层函数测试"""

    def test_string_input(self):
        result = sanitize_input('hello\x00world')
        assert '\x00' not in result
        assert 'hello' in result

    def test_dict_input(self):
        result = sanitize_input({'key': 'value\x00'})
        assert isinstance(result, dict)
        assert '\x00' not in result['key']

    def test_list_input(self):
        result = sanitize_input(['hello\x00', 'world'])
        assert isinstance(result, list)
        assert '\x00' not in result[0]

    def test_nested_dict(self):
        result = sanitize_input({'outer': {'inner': 'value\x00'}})
        assert '\x00' not in result['outer']['inner']

    def test_nested_list(self):
        result = sanitize_input([['hello\x00', 'world']])
        assert '\x00' not in result[0][0]

    def test_non_string_passthrough(self):
        result = sanitize_input(42)
        assert result == 42

    def test_max_length_on_string(self):
        result = sanitize_input('a' * 200, max_length=100)
        assert len(result) == 100

    def test_max_length_on_dict_values(self):
        result = sanitize_input({'key': 'a' * 200}, max_length=100)
        assert len(result['key']) == 100

    def test_empty_dict(self):
        result = sanitize_input({})
        assert result == {}

    def test_empty_list(self):
        result = sanitize_input([])
        assert result == []

    def test_mixed_types_in_list(self):
        result = sanitize_input(['text', 42, None])
        assert result[0] == 'text'
        assert result[1] == 42
        assert result[2] is None
