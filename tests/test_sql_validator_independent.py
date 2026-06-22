#!/usr/bin/env python3
"""完全独立的 SQL 注入防护测试（不导入任何项目模块）."""

import re
from typing import List, Optional, Set


class SQLValidator:
    """SQL 验证器（独立版本用于测试）."""

    ALLOWED_TABLES: Set[str] = {
        'atoms', 'knowledge_bases', 'users', 'roles', 'permissions',
        'kb_permissions', 'user_roles', 'role_permissions', 'sessions',
        'audit_logs', 'metadata', 'segments', 'embeddings',
    }

    ALLOWED_COLUMNS: Set[str] = {
        'id', 'uuid', 'name', 'title', 'description', 'content',
        'type', 'status', 'created_at', 'updated_at', 'deleted_at',
        'owner_id', 'kb_id', 'user_id', 'role_id', 'permission_id',
        'path', 'tags', 'metadata', 'embedding', 'segment',
        'username', 'password_hash', 'email', 'is_active',
        'token', 'expires_at', 'last_login', 'ip_address',
        'action', 'resource', 'details',
    }

    ALLOWED_ORDER_DIRECTIONS: Set[str] = {'ASC', 'DESC'}
    IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    @classmethod
    def validate_identifier(cls, identifier: str) -> bool:
        if not identifier:
            return False
        if not cls.IDENTIFIER_PATTERN.match(identifier):
            return False
        if len(identifier) > 63:
            return False
        return True

    @classmethod
    def validate_table_name(cls, table_name: str) -> bool:
        if not cls.validate_identifier(table_name):
            return False
        return table_name.lower() in cls.ALLOWED_TABLES

    @classmethod
    def validate_column_name(cls, column_name: str) -> bool:
        if not cls.validate_identifier(column_name):
            return False
        return column_name.lower() in cls.ALLOWED_COLUMNS

    @classmethod
    def validate_order_direction(cls, direction: str) -> bool:
        return direction.upper() in cls.ALLOWED_ORDER_DIRECTIONS

    @classmethod
    def quote_identifier(cls, identifier: str) -> str:
        if not cls.validate_identifier(identifier):
            raise ValueError(f"Invalid identifier: {identifier}")
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    @classmethod
    def build_safe_order_by(cls, column: str, direction: str = 'ASC') -> str:
        if not cls.validate_column_name(column):
            raise ValueError(f"Invalid column name: {column}")
        if not cls.validate_order_direction(direction):
            raise ValueError(f"Invalid order direction: {direction}")
        quoted_column = cls.quote_identifier(column)
        return f"{quoted_column} {direction.upper()}"

    @classmethod
    def _contains_sql_injection(cls, value: str) -> bool:
        upper_value = value.upper()
        dangerous_patterns = [
            r';\s*DROP',
            r';\s*DELETE',
            r';\s*UPDATE',
            r';\s*INSERT',
            r'UNION\s+SELECT',
            r'OR\s+1\s*=\s*1',
            r"'\s*OR\s*'",
            r'--',
            r'/\*',
            r'\*/',
            r'EXEC\s',
            r'EXECUTE\s',
            r'xp_cmdshell',
            r'WAITFOR\s+DELAY',
            r'BENCHMARK\s*\(',
            r'SLEEP\s*\(',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, upper_value, re.IGNORECASE):
                return True
        return False


def test_validate_identifier():
    print("\n=== 测试标识符验证 ===")
    assert SQLValidator.validate_identifier('user_id')
    assert SQLValidator.validate_identifier('created_at')
    print("✅ 合法标识符验证通过")
    assert not SQLValidator.validate_identifier('user-id')
    assert not SQLValidator.validate_identifier('user.id')
    assert not SQLValidator.validate_identifier('')
    assert not SQLValidator.validate_identifier('123user')
    print("✅ 非法标识符验证通过")
    assert not SQLValidator.validate_identifier("users; DROP TABLE users;--")
    print("✅ SQL 注入检测通过")


def test_validate_table_name():
    print("\n=== 测试表名验证 ===")
    assert SQLValidator.validate_table_name('atoms')
    assert SQLValidator.validate_table_name('knowledge_bases')
    print("✅ 合法表名验证通过")
    assert not SQLValidator.validate_table_name('malicious_table')
    assert not SQLValidator.validate_table_name('admin')
    print("✅ 非法表名验证通过")
    assert not SQLValidator.validate_table_name('atoms; DROP TABLE atoms;--')
    print("✅ SQL 注入检测通过")


def test_validate_column_name():
    print("\n=== 测试列名验证 ===")
    assert SQLValidator.validate_column_name('id')
    assert SQLValidator.validate_column_name('title')
    print("✅ 合法列名验证通过")
    assert not SQLValidator.validate_column_name('malicious_column')
    print("✅ 非法列名验证通过")


def test_quote_identifier():
    print("\n=== 测试标识符引用 ===")
    assert SQLValidator.quote_identifier('user_id') == '"user_id"'
    print("✅ 标识符引用验证通过")
    try:
        SQLValidator.quote_identifier('user-id')
        assert False
    except ValueError:
        print("✅ 非法标识符正确抛出异常")


def test_build_safe_order_by():
    print("\n=== 测试安全的 ORDER BY 构建 ===")
    order_by = SQLValidator.build_safe_order_by('created_at', 'DESC')
    assert order_by == '"created_at" DESC'
    print(f"✅ ORDER BY 构建成功: {order_by}")
    try:
        SQLValidator.build_safe_order_by('malicious_column', 'ASC')
        assert False
    except ValueError:
        print("✅ 非法列名正确抛出异常")


def test_sql_injection_detection():
    print("\n=== 测试 SQL 注入检测 ===")
    assert SQLValidator._contains_sql_injection("'; DROP TABLE users;--")
    assert SQLValidator._contains_sql_injection("1 OR 1=1")
    assert SQLValidator._contains_sql_injection("UNION SELECT * FROM users")
    assert SQLValidator._contains_sql_injection("admin'--")
    assert SQLValidator._contains_sql_injection("1; DELETE FROM atoms")
    print("✅ SQL 注入特征检测通过")
    assert not SQLValidator._contains_sql_injection("normal title")
    assert not SQLValidator._contains_sql_injection("user@example.com")
    print("✅ 正常字符串验证通过")


def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("SQL 注入防护功能测试（独立版本）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        test_validate_identifier()
        test_validate_table_name()
        test_validate_column_name()
        test_quote_identifier()
        test_build_safe_order_by()
        test_sql_injection_detection()

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