"""SQL 验证工具，防止 SQL 注入攻击.

提供标识符验证、参数化查询构建等功能。
"""

import re
from typing import List, Optional, Set


class SQLValidator:
    """SQL 验证器，用于防止 SQL 注入."""

    # 允许的表名白名单（知识库相关表）
    ALLOWED_TABLES: Set[str] = {
        'atoms',
        'knowledge_bases',
        'kb_members',
        'users',
        'roles',
        'permissions',
        'kb_permissions',
        'user_roles',
        'role_permissions',
        'sessions',
        'audit_logs',
        'metadata',
        'segments',
        'embeddings',
    }

    # 允许的列名白名单（常见列名）
    ALLOWED_COLUMNS: Set[str] = {
        'id', 'uuid', 'name', 'title', 'description', 'content',
        'type', 'status', 'created_at', 'updated_at', 'deleted_at',
        'owner_id', 'kb_id', 'user_id', 'role_id', 'permission_id',
        'path', 'tags', 'metadata', 'embedding', 'segment',
        'username', 'password_hash', 'email', 'is_active',
        'token', 'expires_at', 'last_login', 'ip_address',
        'action', 'resource', 'details',
    }

    # 允许的排序方向
    ALLOWED_ORDER_DIRECTIONS: Set[str] = {'ASC', 'DESC'}

    # 允许的 SQL 关键字（用于 ORDER BY 等）
    ALLOWED_KEYWORDS: Set[str] = {
        'ASC', 'DESC', 'NULLS', 'FIRST', 'LAST',
        'AND', 'OR', 'NOT', 'IN', 'IS',
    }

    # 标识符正则：只允许字母、数字、下划线
    IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    @classmethod
    def validate_identifier(cls, identifier: str) -> bool:
        """验证标识符是否合法（防止注入）.

        Args:
            identifier: 要验证的标识符（表名、列名等）

        Returns:
            是否合法
        """
        if not identifier:
            return False

        # 检查格式
        if not cls.IDENTIFIER_PATTERN.match(identifier):
            return False

        # 检查长度
        if len(identifier) > 63:  # PostgreSQL 标识符最大长度
            return False

        return True

    @classmethod
    def validate_table_name(cls, table_name: str) -> bool:
        """验证表名是否合法且在白名单中.

        Args:
            table_name: 表名

        Returns:
            是否合法
        """
        if not cls.validate_identifier(table_name):
            return False

        # 转换为小写检查（PostgreSQL 表名不区分大小写）
        return table_name.lower() in cls.ALLOWED_TABLES

    @classmethod
    def validate_column_name(cls, column_name: str) -> bool:
        """验证列名是否合法且在白名单中.

        Args:
            column_name: 列名

        Returns:
            是否合法
        """
        if not cls.validate_identifier(column_name):
            return False

        # 转换为小写检查
        return column_name.lower() in cls.ALLOWED_COLUMNS

    @classmethod
    def validate_order_direction(cls, direction: str) -> bool:
        """验证排序方向是否合法.

        Args:
            direction: 排序方向（ASC/DESC）

        Returns:
            是否合法
        """
        return direction.upper() in cls.ALLOWED_ORDER_DIRECTIONS

    @classmethod
    def sanitize_identifier(cls, identifier: str) -> Optional[str]:
        """清理并验证标识符，返回安全的标识符.

        Args:
            identifier: 原始标识符

        Returns:
            清理后的标识符，如果不合法返回 None
        """
        # 去除前后空格
        identifier = identifier.strip()

        # 转换为小写
        identifier = identifier.lower()

        # 验证
        if not cls.validate_identifier(identifier):
            return None

        return identifier

    @classmethod
    def quote_identifier(cls, identifier: str) -> str:
        """引用标识符以防止 SQL 注入.

        使用 PostgreSQL 的双引号引用标识符。

        Args:
            identifier: 标识符

        Returns:
            引用后的标识符
        """
        # 先验证
        if not cls.validate_identifier(identifier):
            raise ValueError(f"Invalid identifier: {identifier}")

        # 转义双引号
        escaped = identifier.replace('"', '""')

        # 用双引号包裹
        return f'"{escaped}"'

    @classmethod
    def build_safe_order_by(
        cls,
        column: str,
        direction: str = 'ASC'
    ) -> str:
        """构建安全的 ORDER BY 子句.

        Args:
            column: 列名
            direction: 排序方向

        Returns:
            安全的 ORDER BY 子句

        Raises:
            ValueError: 如果参数不合法
        """
        if not cls.validate_column_name(column):
            raise ValueError(f"Invalid column name: {column}")

        if not cls.validate_order_direction(direction):
            raise ValueError(f"Invalid order direction: {direction}")

        # 使用引用标识符
        quoted_column = cls.quote_identifier(column)

        return f"{quoted_column} {direction.upper()}"

    @classmethod
    def validate_list_values(cls, values: List[str]) -> bool:
        """验证 IN 子句的值列表是否安全.

        Args:
            values: 值列表

        Returns:
            是否安全
        """
        if not values:
            return False

        # 检查每个值
        for value in values:
            if not isinstance(value, str):
                continue
            # 检查是否包含 SQL 注入特征
            if cls._contains_sql_injection(value):
                return False

        return True

    @classmethod
    def _contains_sql_injection(cls, value: str) -> bool:
        """检测字符串是否包含 SQL 注入特征.

        Args:
            value: 要检查的字符串

        Returns:
            是否包含注入特征
        """
        # 转换为大写检查
        upper_value = value.upper()

        # 检查危险模式
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


def safe_identifier(identifier: str, identifier_type: str = 'column') -> str:
    """获取安全的标识符（带验证）.

    Args:
        identifier: 原始标识符
        identifier_type: 标识符类型（'table' 或 'column'）

    Returns:
        安全的标识符

    Raises:
        ValueError: 如果标识符不合法
    """
    if identifier_type == 'table':
        if not SQLValidator.validate_table_name(identifier):
            raise ValueError(f"Invalid table name: {identifier}")
    elif identifier_type == 'column':
        if not SQLValidator.validate_column_name(identifier):
            raise ValueError(f"Invalid column name: {identifier}")
    else:
        if not SQLValidator.validate_identifier(identifier):
            raise ValueError(f"Invalid identifier: {identifier}")

    return SQLValidator.quote_identifier(identifier)


def build_parameterized_query(
    base_query: str,
    params: dict
) -> tuple:
    """构建参数化查询.

    Args:
        base_query: 基础查询（使用 $1, $2 占位符）
        params: 参数字典

    Returns:
        (query, param_list) 元组
    """
    param_list = []
    param_index = 1

    # 替换命名参数为位置参数
    for key, value in sorted(params.items()):
        placeholder = f":{key}"
        if placeholder in base_query:
            base_query = base_query.replace(placeholder, f"${param_index}")
            param_list.append(value)
            param_index += 1

    return base_query, param_list
