"""测试 SQL 注入防护功能."""

import pytest
from lib.utils.sql_validator import SQLValidator, safe_identifier, build_parameterized_query


class TestSQLValidator:
    """测试 SQLValidator 类."""

    def test_validate_identifier_valid(self):
        """测试合法标识符验证."""
        assert SQLValidator.validate_identifier('user_id')
        assert SQLValidator.validate_identifier('created_at')
        assert SQLValidator.validate_identifier('kb_id')
        assert SQLValidator.validate_identifier('title')

    def test_validate_identifier_invalid(self):
        """测试非法标识符验证."""
        # 包含特殊字符
        assert not SQLValidator.validate_identifier('user-id')
        assert not SQLValidator.validate_identifier('user.id')
        assert not SQLValidator.validate_identifier('user id')

        # 空字符串
        assert not SQLValidator.validate_identifier('')

        # 以数字开头
        assert not SQLValidator.validate_identifier('123user')

        # SQL 注入尝试
        assert not SQLValidator.validate_identifier("users; DROP TABLE users;--")

    def test_validate_table_name_valid(self):
        """测试合法表名验证."""
        assert SQLValidator.validate_table_name('atoms')
        assert SQLValidator.validate_table_name('knowledge_bases')
        assert SQLValidator.validate_table_name('users')

    def test_validate_table_name_invalid(self):
        """测试非法表名验证."""
        # 不在白名单中
        assert not SQLValidator.validate_table_name('malicious_table')
        assert not SQLValidator.validate_table_name('admin')

        # SQL 注入尝试
        assert not SQLValidator.validate_table_name('atoms; DROP TABLE atoms;--')

    def test_validate_column_name_valid(self):
        """测试合法列名验证."""
        assert SQLValidator.validate_column_name('id')
        assert SQLValidator.validate_column_name('title')
        assert SQLValidator.validate_column_name('created_at')

    def test_validate_column_name_invalid(self):
        """测试非法列名验证."""
        # 不在白名单中
        assert not SQLValidator.validate_column_name('malicious_column')

        # SQL 注入尝试
        assert not SQLValidator.validate_column_name("id; DROP TABLE users;--")

    def test_validate_order_direction(self):
        """测试排序方向验证."""
        assert SQLValidator.validate_order_direction('ASC')
        assert SQLValidator.validate_order_direction('DESC')
        assert SQLValidator.validate_order_direction('asc')
        assert SQLValidator.validate_order_direction('desc')

        # 非法值
        assert not SQLValidator.validate_order_direction('INVALID')
        assert not SQLValidator.validate_order_direction('DROP')

    def test_quote_identifier(self):
        """测试标识符引用."""
        assert SQLValidator.quote_identifier('user_id') == '"user_id"'
        assert SQLValidator.quote_identifier('created_at') == '"created_at"'

        # 非法标识符应该抛出异常
        with pytest.raises(ValueError):
            SQLValidator.quote_identifier('user-id')

    def test_build_safe_order_by(self):
        """测试安全的 ORDER BY 构建."""
        order_by = SQLValidator.build_safe_order_by('created_at', 'DESC')
        assert order_by == '"created_at" DESC'

        order_by = SQLValidator.build_safe_order_by('id', 'ASC')
        assert order_by == '"id" ASC'

        # 非法列名应该抛出异常
        with pytest.raises(ValueError):
            SQLValidator.build_safe_order_by('malicious_column', 'ASC')

    def test_detect_sql_injection(self):
        """测试 SQL 注入检测."""
        # 包含 SQL 注入特征的字符串
        assert SQLValidator._contains_sql_injection("'; DROP TABLE users;--")
        assert SQLValidator._contains_sql_injection("1 OR 1=1")
        assert SQLValidator._contains_sql_injection("UNION SELECT * FROM users")
        assert SQLValidator._contains_sql_injection("admin'--")
        assert SQLValidator._contains_sql_injection("1; DELETE FROM atoms")

        # 正常字符串
        assert not SQLValidator._contains_sql_injection("normal title")
        assert not SQLValidator._contains_sql_injection("user@example.com")


class TestSafeIdentifier:
    """测试 safe_identifier 函数."""

    def test_table_identifier(self):
        """测试表标识符."""
        result = safe_identifier('atoms', 'table')
        assert result == '"atoms"'

    def test_column_identifier(self):
        """测试列标识符."""
        result = safe_identifier('id', 'column')
        assert result == '"id"'

    def test_invalid_table(self):
        """测试非法表名."""
        with pytest.raises(ValueError):
            safe_identifier('malicious_table', 'table')

    def test_invalid_column(self):
        """测试非法列名."""
        with pytest.raises(ValueError):
            safe_identifier('malicious_column', 'column')


class TestBuildParameterizedQuery:
    """测试参数化查询构建."""

    def test_simple_query(self):
        """测试简单查询."""
        base_query = "SELECT * FROM users WHERE id = :id"
        params = {'id': 123}

        query, param_list = build_parameterized_query(base_query, params)

        assert query == "SELECT * FROM users WHERE id = $1"
        assert param_list == [123]

    def test_multiple_params(self):
        """测试多参数查询."""
        base_query = "SELECT * FROM atoms WHERE kb_id = :kb_id AND type = :type"
        params = {'kb_id': 1, 'type': 'note'}

        query, param_list = build_parameterized_query(base_query, params)

        assert "$1" in query
        assert "$2" in query
        assert len(param_list) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
