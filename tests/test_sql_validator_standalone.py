#!/usr/bin/env python3
"""独立测试 SQL 注入防护功能（不依赖完整环境）."""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接导入 SQL 验证器模块（不通过 lib.__init__）
from lib.utils.sql_validator import SQLValidator, safe_identifier

def test_validate_identifier():
    """测试标识符验证."""
    print("\n=== 测试标识符验证 ===")

    # 合法标识符
    assert SQLValidator.validate_identifier('user_id'), "user_id 应该合法"
    assert SQLValidator.validate_identifier('created_at'), "created_at 应该合法"
    print("✅ 合法标识符验证通过")

    # 非法标识符
    assert not SQLValidator.validate_identifier('user-id'), "user-id 应该非法"
    assert not SQLValidator.validate_identifier('user.id'), "user.id 应该非法"
    assert not SQLValidator.validate_identifier(''), "空字符串应该非法"
    assert not SQLValidator.validate_identifier('123user'), "以数字开头应该非法"
    print("✅ 非法标识符验证通过")

    # SQL 注入尝试
    assert not SQLValidator.validate_identifier("users; DROP TABLE users;--"), "SQL 注入应该被阻止"
    print("✅ SQL 注入检测通过")


def test_validate_table_name():
    """测试表名验证."""
    print("\n=== 测试表名验证 ===")

    # 合法表名（在白名单中）
    assert SQLValidator.validate_table_name('atoms'), "atoms 应该合法"
    assert SQLValidator.validate_table_name('knowledge_bases'), "knowledge_bases 应该合法"
    assert SQLValidator.validate_table_name('users'), "users 应该合法"
    print("✅ 合法表名验证通过")

    # 非法表名（不在白名单中）
    assert not SQLValidator.validate_table_name('malicious_table'), "malicious_table 应该非法"
    assert not SQLValidator.validate_table_name('admin'), "admin 应该非法"
    print("✅ 非法表名验证通过")

    # SQL 注入尝试
    assert not SQLValidator.validate_table_name('atoms; DROP TABLE atoms;--'), "SQL 注入应该被阻止"
    print("✅ SQL 注入检测通过")


def test_validate_column_name():
    """测试列名验证."""
    print("\n=== 测试列名验证 ===")

    # 合法列名
    assert SQLValidator.validate_column_name('id'), "id 应该合法"
    assert SQLValidator.validate_column_name('title'), "title 应该合法"
    assert SQLValidator.validate_column_name('created_at'), "created_at 应该合法"
    print("✅ 合法列名验证通过")

    # 非法列名
    assert not SQLValidator.validate_column_name('malicious_column'), "malicious_column 应该非法"
    print("✅ 非法列名验证通过")


def test_quote_identifier():
    """测试标识符引用."""
    print("\n=== 测试标识符引用 ===")

    assert SQLValidator.quote_identifier('user_id') == '"user_id"', "标识符应该被正确引用"
    assert SQLValidator.quote_identifier('created_at') == '"created_at"', "标识符应该被正确引用"
    print("✅ 标识符引用验证通过")

    # 非法标识符应该抛出异常
    try:
        SQLValidator.quote_identifier('user-id')
        assert False, "应该抛出 ValueError"
    except ValueError:
        print("✅ 非法标识符正确抛出异常")


def test_build_safe_order_by():
    """测试安全的 ORDER BY 构建."""
    print("\n=== 测试安全的 ORDER BY 构建 ===")

    order_by = SQLValidator.build_safe_order_by('created_at', 'DESC')
    assert order_by == '"created_at" DESC', f"期望 '\"created_at\" DESC'，得到 '{order_by}'"
    print(f"✅ ORDER BY 构建成功: {order_by}")

    # 非法列名应该抛出异常
    try:
        SQLValidator.build_safe_order_by('malicious_column', 'ASC')
        assert False, "应该抛出 ValueError"
    except ValueError:
        print("✅ 非法列名正确抛出异常")


def test_sql_injection_detection():
    """测试 SQL 注入检测."""
    print("\n=== 测试 SQL 注入检测 ===")

    # 包含 SQL 注入特征的字符串
    assert SQLValidator._contains_sql_injection("'; DROP TABLE users;--"), "DROP 应该被检测"
    assert SQLValidator._contains_sql_injection("1 OR 1=1"), "OR 1=1 应该被检测"
    assert SQLValidator._contains_sql_injection("UNION SELECT * FROM users"), "UNION 应该被检测"
    assert SQLValidator._contains_sql_injection("admin'--"), "注释应该被检测"
    assert SQLValidator._contains_sql_injection("1; DELETE FROM atoms"), "DELETE 应该被检测"
    print("✅ SQL 注入特征检测通过")

    # 正常字符串
    assert not SQLValidator._contains_sql_injection("normal title"), "正常标题应该通过"
    assert not SQLValidator._contains_sql_injection("user@example.com"), "邮箱应该通过"
    print("✅ 正常字符串验证通过")


def test_safe_identifier_function():
    """测试 safe_identifier 函数."""
    print("\n=== 测试 safe_identifier 函数 ===")

    result = safe_identifier('atoms', 'table')
    assert result == '"atoms"', f"期望 '\"atoms\"'，得到 '{result}'"
    print(f"✅ 表标识符验证通过: {result}")

    result = safe_identifier('id', 'column')
    assert result == '"id"', f"期望 '\"id\"'，得到 '{result}'"
    print(f"✅ 列标识符验证通过: {result}")


def main():
    """运行所有测试."""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("SQL 注入防护功能测试")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        test_validate_identifier()
        test_validate_table_name()
        test_validate_column_name()
        test_quote_identifier()
        test_build_safe_order_by()
        test_sql_injection_detection()
        test_safe_identifier_function()

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("✅ 所有测试通过！")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 意外错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
