"""PostgreSQL 数据库模块

包含 Schema 定义、索引、RLS 策略和存储过程。

文件结构：
- schema.sql: 核心表结构定义
- indexes.sql: 索引定义（全文索引、向量索引、B-tree 索引）
- functions.sql: 存储过程和函数（RLS 辅助、审计日志、版本管理）
- rls.sql: 行级安全策略定义

使用方式：
1. 初始化数据库：
   psql -d llmwiki -f schema.sql
   psql -d llmwiki -f indexes.sql
   psql -d llmwiki -f functions.sql
   psql -d llmwiki -f rls.sql

2. 或者通过 Python 调用：
   from lib.db import init_database
   await init_database(db_url)

注意事项：
- 需要 PostgreSQL 15+
- 需要启用 pgvector 扩展
- 向量索引应在数据量 >= 1000 后创建
"""

import os
from pathlib import Path

# SQL 文件路径
SQL_FILES = {
    'schema': 'schema.sql',
    'indexes': 'indexes.sql',
    'functions': 'functions.sql',
    'rls': 'rls.sql',
}

__all__ = ['SQL_FILES', 'get_sql_path', 'init_database', 'get_init_sql']


def get_sql_path(filename: str) -> Path:
    """获取 SQL 文件的绝对路径

    Args:
        filename: SQL 文件名（如 'schema.sql'）

    Returns:
        文件的绝对路径
    """
    db_dir = Path(__file__).parent
    return db_dir / filename


async def init_database(db_url: str) -> None:
    """初始化数据库（执行所有 SQL 文件）

    Args:
        db_url: PostgreSQL 连接 URL
                格式：postgresql://user:pass@host:port/dbname

    Raises:
        ImportError: 如果 asyncpg 未安装
        RuntimeError: 如果 SQL 文件不存在
    """
    try:
        import asyncpg
    except ImportError:
        raise ImportError(
            "asyncpg 未安装，请执行：pip install asyncpg"
        )

    conn = await asyncpg.connect(db_url)

    try:
        # 按顺序执行 SQL 文件
        for key in ['schema', 'indexes', 'functions', 'rls']:
            sql_path = get_sql_path(SQL_FILES[key])

            if not sql_path.exists():
                raise RuntimeError(f"SQL 文件不存在：{sql_path}")

            sql_content = sql_path.read_text(encoding='utf-8')

            # 执行 SQL
            await conn.execute(sql_content)

    finally:
        await conn.close()


def get_init_sql() -> str:
    """获取初始化 SQL（合并所有文件）

    Returns:
        合并后的 SQL 内容
    """
    sql_parts = []

    for key in ['schema', 'indexes', 'functions', 'rls']:
        sql_path = get_sql_path(SQL_FILES[key])
        if sql_path.exists():
            sql_parts.append(sql_path.read_text(encoding='utf-8'))

    return '\n\n'.join(sql_parts)