"""搜索迁移测试

验证搜索相关数据库迁移的正确性：
1. pg_trgm 扩展可用
2. 模糊搜索功能（trigram 索引）
3. search_history 表存在
4. pg_trgm 索引已创建

使用 Mock asyncpg 连接池，不依赖真实数据库。
"""

import re
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 绕过 lib/__init__.py 的重量级依赖导入
# ---------------------------------------------------------------------------

def _ensure_lib_package_registered() -> None:
    """预注册空的 lib 包，避免触发 lib/__init__.py 的导入链。

    lib/__init__.py 导入了 sentence_transformers 等依赖，
    在测试环境中可能因 numpy 版本不兼容而失败。
    通过预注册空的 lib 模块，让后续的 lib.search 和 lib.db
    子模块导入能够正常工作。
    """
    if 'lib' not in sys.modules:
        lib_module = types.ModuleType('lib')
        lib_module.__path__ = [str(Path(__file__).parent.parent.parent / 'lib')]
        lib_module.__package__ = 'lib'
        sys.modules['lib'] = lib_module


_ensure_lib_package_registered()


# ---------------------------------------------------------------------------
# 路径常量：直接定位 SQL 文件，避免导入有依赖问题的模块
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DB_DIR = _PROJECT_ROOT / 'lib' / 'db'
SCHEMA_PATH = _DB_DIR / 'schema.sql'
INDEXES_PATH = _DB_DIR / 'indexes.sql'


# ---------------------------------------------------------------------------
# 辅助工具：SQL 文件内容加载
# ---------------------------------------------------------------------------


def _load_sql_file(path: Path) -> str:
    """加载 SQL 文件内容

    Args:
        path: SQL 文件路径

    Returns:
        SQL 文件文本内容

    Raises:
        FileNotFoundError: 文件不存在时
    """
    if not path.exists():
        raise FileNotFoundError(f"SQL 文件不存在：{path}")
    return path.read_text(encoding='utf-8')


def _extract_create_table_block(sql: str, table_name: str) -> Optional[str]:
    """从 SQL 中提取 CREATE TABLE 定义块

    Args:
        sql: SQL 内容
        table_name: 表名

    Returns:
        表定义块文本，未找到则返回 None
    """
    pattern = rf'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{table_name}\s*\((.*?)\);'
    match = re.search(pattern, sql, re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else None


def _get_merged_init_sql() -> str:
    """获取合并后的初始化 SQL（模拟 lib.db.get_init_sql）

    按顺序合并 schema.sql、indexes.sql、functions.sql、rls.sql。
    直接读取文件，避免导入有 numpy 依赖问题的模块。

    Returns:
        合并后的 SQL 内容
    """
    sql_files = ['schema.sql', 'indexes.sql', 'functions.sql', 'rls.sql']
    parts = []
    for filename in sql_files:
        path = _DB_DIR / filename
        if path.exists():
            parts.append(path.read_text(encoding='utf-8'))
    return '\n\n'.join(parts)


# ---------------------------------------------------------------------------
# Mock 工厂：创建 asyncpg 连接池和连接的 Mock
# ---------------------------------------------------------------------------


def _create_mock_connection(
    execute_result: Optional[str] = None,
    fetch_result: Optional[List[Dict[str, Any]]] = None,
    fetchrow_result: Optional[Dict[str, Any]] = None,
) -> AsyncMock:
    """创建 Mock asyncpg 连接

    不可变模式：每次返回新的 Mock 对象，不修改已有 Mock 状态。

    Args:
        execute_result: execute 方法的返回值
        fetch_result: fetch 方法的返回值
        fetchrow_result: fetchrow 方法的返回值

    Returns:
        配置好的 AsyncMock 连接对象
    """
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=execute_result or 'CREATE EXTENSION')
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    conn.fetchrow = AsyncMock(return_value=fetchrow_result or {})
    conn.fetchval = AsyncMock(return_value=None)
    conn.close = AsyncMock()
    return conn


def _create_mock_pool(
    connection: Optional[AsyncMock] = None,
) -> AsyncMock:
    """创建 Mock asyncpg 连接池

    Args:
        connection: 可选的预配置连接 Mock

    Returns:
        配置好的 AsyncMock 连接池对象
    """
    conn = connection or _create_mock_connection()
    pool = AsyncMock()

    # acquire 返回异步上下文管理器
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acquire_cm)

    pool.close = AsyncMock()
    return pool


# ===========================================================================
# 测试类：pg_trgm 扩展可用性
# ===========================================================================


class TestPgTrgmExtension:
    """验证 pg_trgm 扩展定义正确"""

    @pytest.fixture(scope='class')
    @classmethod
    def schema_sql(cls) -> str:
        """加载 schema.sql 内容"""
        return _load_sql_file(SCHEMA_PATH)

    def test_pg_trgm_extension_statement_exists(self, schema_sql: str) -> None:
        """验证 schema.sql 中包含 CREATE EXTENSION pg_trgm 语句"""
        assert 'pg_trgm' in schema_sql, 'pg_trgm 扩展未在 schema.sql 中声明'

    def test_pg_trgm_create_extension_if_not_exists(self, schema_sql: str) -> None:
        """验证 pg_trgm 使用 IF NOT EXISTS 语句，确保幂等性"""
        pattern = r'CREATE\s+EXTENSION\s+IF\s+NOT\s+EXISTS\s+pg_trgm'
        assert re.search(
            pattern, schema_sql, re.IGNORECASE
        ), 'pg_trgm 扩展应使用 CREATE EXTENSION IF NOT EXISTS 语句'

    def test_pg_trgm_extension_before_tables(self, schema_sql: str) -> None:
        """验证 pg_trgm 扩展在表定义之前声明"""
        trgm_pos = schema_sql.find('pg_trgm')
        first_table_pos = schema_sql.find('CREATE TABLE')
        assert trgm_pos > 0, 'pg_trgm 扩展声明未找到'
        assert first_table_pos > 0, 'CREATE TABLE 语句未找到'
        assert trgm_pos < first_table_pos, (
            'pg_trgm 扩展应在表定义之前声明'
        )


# ===========================================================================
# 测试类：模糊搜索功能
# ===========================================================================


class TestFuzzySearch:
    """验证 pg_trgm 模糊搜索索引和查询支持"""

    @pytest.fixture(scope='class')
    @classmethod
    def indexes_sql(cls) -> str:
        """加载 indexes.sql 内容"""
        return _load_sql_file(INDEXES_PATH)

    def test_title_trgm_index_exists(self, indexes_sql: str) -> None:
        """验证标题的 pg_trgm GIN 索引已定义"""
        pattern = (
            r'CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+'
            r'idx_atoms_title_trgm\s+ON\s+atoms\s+'
            r'USING\s+gin\s*\(\s*title\s+gin_trgm_ops\s*\)'
        )
        assert re.search(
            pattern, indexes_sql, re.IGNORECASE
        ), 'atoms.title 的 pg_trgm GIN 索引未定义'

    def test_description_trgm_index_exists(self, indexes_sql: str) -> None:
        """验证描述的 pg_trgm GIN 索引已定义"""
        pattern = (
            r'CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+'
            r'idx_atoms_description_trgm\s+ON\s+atoms\s+'
            r'USING\s+gin\s*\(\s*description\s+gin_trgm_ops\s*\)'
        )
        assert re.search(
            pattern, indexes_sql, re.IGNORECASE
        ), 'atoms.description 的 pg_trgm GIN 索引未定义'

    def test_description_trgm_index_partial(self, indexes_sql: str) -> None:
        """验证描述的 pg_trgm 索引使用了部分索引（WHERE description IS NOT NULL）"""
        pattern = (
            r'idx_atoms_description_trgm.*?'
            r'WHERE\s+description\s+IS\s+NOT\s+NULL'
        )
        assert re.search(
            pattern, indexes_sql, re.IGNORECASE | re.DOTALL
        ), 'atoms.description 的 pg_trgm 索引应使用部分索引（WHERE description IS NOT NULL）'

    def test_search_history_query_trgm_index_exists(self, indexes_sql: str) -> None:
        """验证 search_history.query 的 pg_trgm 索引已定义"""
        pattern = (
            r'CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+'
            r'idx_search_history_query_trgm\s+ON\s+search_history\s+'
            r'USING\s+gin\s*\(\s*query\s+gin_trgm_ops\s*\)'
        )
        assert re.search(
            pattern, indexes_sql, re.IGNORECASE
        ), 'search_history.query 的 pg_trgm GIN 索引未定义'

    def test_trgm_indexes_use_if_not_exists(self, indexes_sql: str) -> None:
        """验证所有 pg_trgm 索引使用 IF NOT EXISTS，确保幂等性"""
        trgm_index_lines = re.findall(
            r'CREATE\s+INDEX\s+.*?gin_trgm_ops',
            indexes_sql,
            re.IGNORECASE,
        )
        assert len(trgm_index_lines) > 0, '未找到任何 pg_trgm 索引定义'

        for line in trgm_index_lines:
            assert 'IF NOT EXISTS' in line, (
                f'pg_trgm 索引应使用 IF NOT EXISTS: {line.strip()}'
            )

    @pytest.mark.asyncio
    async def test_fuzzy_search_with_mock_pool(self) -> None:
        """验证模糊搜索查询能正确通过 Mock 连接池执行"""
        mock_rows = [
            {
                'atom_id': 1,
                'slug': 'test-atom',
                'title': 'Machine Learning Basics',
                'content': 'Introduction to ML',
                'metadata': {},
                'atom_type': 'method',
                'created_at': None,
                'updated_at': None,
                'kb_id': 1,
                'kb_name': 'Test KB',
                'rank': 0.5,
                'similarity': None,
            },
        ]
        mock_conn = _create_mock_connection(fetch_result=mock_rows)
        mock_pool = _create_mock_pool(mock_conn)

        from lib.search.postgres_search import PostgreSQLSearchEngine

        engine = PostgreSQLSearchEngine(pool=mock_pool)
        results = await engine.search('machine', kb_id=1, limit=10)

        # 验证 fetch 被调用
        mock_conn.fetch.assert_called_once()

        # 验证查询 SQL 包含 tsvector 搜索条件
        call_args = mock_conn.fetch.call_args
        sql = call_args.args[0] if call_args.args else call_args.kwargs.get('query', '')
        assert 'content_tsv' in sql, '搜索查询应使用 content_tsv 全文索引'
        assert 'status' in sql, '搜索查询应过滤 status'

    @pytest.mark.asyncio
    async def test_suggest_with_like_query(self) -> None:
        """验证搜索建议使用 LIKE 前缀匹配"""
        mock_rows = [
            {'title': 'Machine Learning'},
            {'title': 'Machine Translation'},
        ]
        mock_conn = _create_mock_connection(fetch_result=mock_rows)
        mock_pool = _create_mock_pool(mock_conn)

        from lib.search.postgres_search import PostgreSQLSearchEngine

        engine = PostgreSQLSearchEngine(pool=mock_pool)
        suggestions = await engine.suggest('Machine', kb_id=1, limit=5)

        # 验证返回结果
        assert len(suggestions) == 2
        assert suggestions[0] == 'Machine Learning'

        # 验证查询使用了 LIKE
        call_args = mock_conn.fetch.call_args
        sql = call_args.args[0] if call_args.args else ''
        assert 'LIKE' in sql.upper(), '搜索建议应使用 LIKE 前缀匹配'


# ===========================================================================
# 测试类：search_history 表
# ===========================================================================


class TestSearchHistoryTable:
    """验证 search_history 表定义正确"""

    @pytest.fixture(scope='class')
    @classmethod
    def indexes_sql(cls) -> str:
        """加载 indexes.sql 内容"""
        return _load_sql_file(INDEXES_PATH)

    def test_search_history_table_exists(self, indexes_sql: str) -> None:
        """验证 search_history 表定义存在"""
        block = _extract_create_table_block(indexes_sql, 'search_history')
        assert block is not None, 'search_history 表定义未在 indexes.sql 中找到'

    def test_search_history_table_if_not_exists(self, indexes_sql: str) -> None:
        """验证 search_history 使用 IF NOT EXISTS 创建，确保幂等性"""
        pattern = r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+search_history'
        assert re.search(
            pattern, indexes_sql, re.IGNORECASE
        ), 'search_history 表应使用 CREATE TABLE IF NOT EXISTS 语句'

    def test_search_history_id_column(self, indexes_sql: str) -> None:
        """验证 search_history.id 字段为 BIGSERIAL PRIMARY KEY"""
        block = _extract_create_table_block(indexes_sql, 'search_history')
        assert block is not None
        assert re.search(r'id\s+BIGSERIAL\s+PRIMARY\s+KEY', block), (
            'search_history.id 应为 BIGSERIAL PRIMARY KEY'
        )

    def test_search_history_query_column(self, indexes_sql: str) -> None:
        """验证 search_history.query 字段为 TEXT NOT NULL"""
        block = _extract_create_table_block(indexes_sql, 'search_history')
        assert block is not None
        assert 'query' in block, 'search_history 缺少 query 字段'
        assert re.search(r'query\s+TEXT\s+NOT\s+NULL', block), (
            'search_history.query 应为 TEXT NOT NULL'
        )

    def test_search_history_user_id_column(self, indexes_sql: str) -> None:
        """验证 search_history.user_id 字段存在"""
        block = _extract_create_table_block(indexes_sql, 'search_history')
        assert block is not None
        assert 'user_id' in block, 'search_history 缺少 user_id 字段'

    def test_search_history_kb_id_foreign_key(self, indexes_sql: str) -> None:
        """验证 search_history.kb_id 有外键约束指向 knowledge_bases"""
        block = _extract_create_table_block(indexes_sql, 'search_history')
        assert block is not None
        assert re.search(
            r'kb_id\s+INTEGER\s+REFERENCES\s+knowledge_bases\s*\(\s*id\s*\)',
            block,
        ), 'search_history.kb_id 应有外键 REFERENCES knowledge_bases(id)'

    def test_search_history_kb_id_on_delete_set_null(self, indexes_sql: str) -> None:
        """验证 search_history.kb_id 外键 ON DELETE 策略为 SET NULL"""
        block = _extract_create_table_block(indexes_sql, 'search_history')
        assert block is not None
        assert 'ON DELETE SET NULL' in block, (
            'search_history.kb_id 外键应为 ON DELETE SET NULL'
        )

    def test_search_history_result_count_column(self, indexes_sql: str) -> None:
        """验证 search_history.result_count 字段存在且默认值为 0"""
        block = _extract_create_table_block(indexes_sql, 'search_history')
        assert block is not None
        assert 'result_count' in block, 'search_history 缺少 result_count 字段'
        assert 'DEFAULT 0' in block, 'result_count 应有 DEFAULT 0'

    def test_search_history_created_at_column(self, indexes_sql: str) -> None:
        """验证 search_history.created_at 字段存在且默认值为 NOW()"""
        block = _extract_create_table_block(indexes_sql, 'search_history')
        assert block is not None
        assert 'created_at' in block, 'search_history 缺少 created_at 字段'
        assert 'DEFAULT NOW()' in block, 'created_at 应有 DEFAULT NOW()'

    def test_search_history_comment_exists(self, indexes_sql: str) -> None:
        """验证 search_history 表和关键列有注释"""
        assert "COMMENT ON TABLE search_history" in indexes_sql, (
            'search_history 表注释未定义'
        )
        assert "COMMENT ON COLUMN search_history.query" in indexes_sql, (
            'search_history.query 列注释未定义'
        )
        assert "COMMENT ON COLUMN search_history.result_count" in indexes_sql, (
            'search_history.result_count 列注释未定义'
        )


# ===========================================================================
# 测试类：pg_trgm 索引完整性
# ===========================================================================


class TestPgTrgmIndexes:
    """验证所有 pg_trgm 索引定义完整"""

    @pytest.fixture(scope='class')
    @classmethod
    def indexes_sql(cls) -> str:
        """加载 indexes.sql 内容"""
        return _load_sql_file(INDEXES_PATH)

    # 预期存在的 pg_trgm 索引列表
    EXPECTED_TRGM_INDEXES = {
        'idx_atoms_title_trgm': {
            'table': 'atoms',
            'column': 'title',
        },
        'idx_atoms_description_trgm': {
            'table': 'atoms',
            'column': 'description',
        },
        'idx_search_history_query_trgm': {
            'table': 'search_history',
            'column': 'query',
        },
    }

    def test_all_expected_trgm_indexes_exist(self, indexes_sql: str) -> None:
        """验证所有预期的 pg_trgm 索引都已定义"""
        for index_name, info in self.EXPECTED_TRGM_INDEXES.items():
            assert index_name in indexes_sql, (
                f'pg_trgm 索引 {index_name} 未在 indexes.sql 中定义'
            )

    def test_trgm_indexes_use_gin_operator(self, indexes_sql: str) -> None:
        """验证所有 pg_trgm 索引使用 GIN 访问方法"""
        gin_trgm_indexes = re.findall(
            r'CREATE\s+INDEX\s+.*?USING\s+gin\s*\([^)]*gin_trgm_ops[^)]*\)',
            indexes_sql,
            re.IGNORECASE,
        )
        assert len(gin_trgm_indexes) >= 3, (
            f'预期至少 3 个 GIN pg_trgm 索引，实际找到 {len(gin_trgm_indexes)} 个'
        )

    def test_search_history_basic_indexes(self, indexes_sql: str) -> None:
        """验证 search_history 的基础 B-tree 索引已创建"""
        expected_basic_indexes = [
            'idx_search_history_query',
            'idx_search_history_user',
            'idx_search_history_kb',
            'idx_search_history_created',
        ]
        for index_name in expected_basic_indexes:
            assert index_name in indexes_sql, (
                f'search_history 基础索引 {index_name} 未定义'
            )

    def test_search_history_query_index_on_query_column(self, indexes_sql: str) -> None:
        """验证 search_history.query 索引确实在 query 列上"""
        pattern = (
            r'CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+'
            r'idx_search_history_query\s+ON\s+search_history\s*\(\s*query\s*\)'
        )
        assert re.search(
            pattern, indexes_sql, re.IGNORECASE
        ), 'idx_search_history_query 应在 search_history(query) 上'

    def test_search_history_user_index_on_user_id(self, indexes_sql: str) -> None:
        """验证 search_history.user_id 索引确实在 user_id 列上"""
        pattern = (
            r'CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+'
            r'idx_search_history_user\s+ON\s+search_history\s*\(\s*user_id\s*\)'
        )
        assert re.search(
            pattern, indexes_sql, re.IGNORECASE
        ), 'idx_search_history_user 应在 search_history(user_id) 上'

    def test_search_history_kb_index_on_kb_id(self, indexes_sql: str) -> None:
        """验证 search_history.kb_id 索引确实在 kb_id 列上"""
        pattern = (
            r'CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+'
            r'idx_search_history_kb\s+ON\s+search_history\s*\(\s*kb_id\s*\)'
        )
        assert re.search(
            pattern, indexes_sql, re.IGNORECASE
        ), 'idx_search_history_kb 应在 search_history(kb_id) 上'

    def test_search_history_created_index_desc(self, indexes_sql: str) -> None:
        """验证 search_history.created_at 索引使用降序排列"""
        pattern = (
            r'CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+'
            r'idx_search_history_created\s+ON\s+search_history\s*\(\s*created_at\s+DESC\s*\)'
        )
        assert re.search(
            pattern, indexes_sql, re.IGNORECASE
        ), 'idx_search_history_created 应在 search_history(created_at DESC) 上'


# ===========================================================================
# 测试类：init_database 迁移执行
# ===========================================================================


class TestMigrationExecution:
    """验证数据库迁移脚本能正确执行搜索相关 SQL"""

    def test_merged_sql_contains_pg_trgm(self) -> None:
        """验证合并 SQL 包含 pg_trgm 扩展和索引定义"""
        init_sql = _get_merged_init_sql()

        # 验证扩展
        assert 'pg_trgm' in init_sql, '合并 SQL 应包含 pg_trgm 扩展'

        # 验证索引
        assert 'idx_atoms_title_trgm' in init_sql, (
            '合并 SQL 应包含标题 trigram 索引'
        )
        assert 'idx_atoms_description_trgm' in init_sql, (
            '合并 SQL 应包含描述 trigram 索引'
        )
        assert 'idx_search_history_query_trgm' in init_sql, (
            '合并 SQL 应包含搜索历史查询 trigram 索引'
        )

        # 验证表
        assert 'search_history' in init_sql, '合并 SQL 应包含 search_history 表'

    def test_schema_before_indexes(self) -> None:
        """验证 schema.sql 在 indexes.sql 之前执行（扩展在索引之前）"""
        schema_sql = _load_sql_file(SCHEMA_PATH)
        indexes_sql = _load_sql_file(INDEXES_PATH)

        # pg_trgm 扩展定义在 schema.sql 中
        assert 'pg_trgm' in schema_sql
        # pg_trgm 索引定义在 indexes.sql 中
        assert 'gin_trgm_ops' in indexes_sql

    def test_search_history_in_indexes_file(self) -> None:
        """验证 search_history 表和索引定义在 indexes.sql 中"""
        indexes_sql = _load_sql_file(INDEXES_PATH)

        assert 'CREATE TABLE' in indexes_sql
        assert 'search_history' in indexes_sql
        assert 'idx_search_history_query' in indexes_sql
        assert 'idx_search_history_user' in indexes_sql
        assert 'idx_search_history_kb' in indexes_sql

    @pytest.mark.asyncio
    async def test_init_database_executes_pg_trgm(self) -> None:
        """验证 init_database 会执行包含 pg_trgm 的 SQL"""
        mock_conn = _create_mock_connection()

        with patch('asyncpg.connect', return_value=mock_conn):
            from lib.db import init_database

            await init_database('postgresql://test:test@localhost/testdb')

            # 验证 execute 被调用
            mock_conn.execute.assert_called()

            # 获取所有执行的 SQL 内容
            executed_sqls = [
                call.args[0] for call in mock_conn.execute.call_args_list
            ]
            combined_sql = '\n'.join(executed_sqls)

            # 验证 pg_trgm 扩展在执行的 SQL 中
            assert 'pg_trgm' in combined_sql, (
                'init_database 执行的 SQL 中应包含 pg_trgm 扩展'
            )

    @pytest.mark.asyncio
    async def test_init_database_closes_connection(self) -> None:
        """验证 init_database 在完成后关闭连接"""
        mock_conn = _create_mock_connection()

        with patch('asyncpg.connect', return_value=mock_conn):
            from lib.db import init_database

            await init_database('postgresql://test:test@localhost/testdb')

            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_database_propagates_connection_error(self) -> None:
        """验证 init_database 在连接失败时传播错误"""
        with patch('asyncpg.connect', side_effect=ConnectionError('Connection refused')):
            from lib.db import init_database

            with pytest.raises(ConnectionError, match='Connection refused'):
                await init_database('postgresql://test:test@localhost/testdb')

    @pytest.mark.asyncio
    async def test_init_database_propagates_sql_error(self) -> None:
        """验证 init_database 在 SQL 执行失败时传播错误并关闭连接"""
        mock_conn = _create_mock_connection()
        mock_conn.execute = AsyncMock(
            side_effect=RuntimeError('SQL execution failed')
        )

        with patch('asyncpg.connect', return_value=mock_conn):
            from lib.db import init_database

            with pytest.raises(RuntimeError, match='SQL execution failed'):
                await init_database('postgresql://test:test@localhost/testdb')

            # 即使 SQL 执行失败，连接也应被关闭
            mock_conn.close.assert_called_once()


# ===========================================================================
# 测试类：搜索引擎与 pg_trgm 集成
# ===========================================================================


class TestSearchEngineTrgmIntegration:
    """验证 PostgreSQLSearchEngine 能利用 pg_trgm 功能"""

    @pytest.mark.asyncio
    async def test_search_returns_empty_for_empty_query(self) -> None:
        """验证空查询返回空结果"""
        mock_pool = _create_mock_pool()
        from lib.search.postgres_search import PostgreSQLSearchEngine

        engine = PostgreSQLSearchEngine(pool=mock_pool)
        results = await engine.search('', kb_id=1)

        assert results == [], '空查询应返回空列表'

    @pytest.mark.asyncio
    async def test_search_returns_empty_for_whitespace_query(self) -> None:
        """验证仅空白字符的查询返回空结果"""
        mock_pool = _create_mock_pool()
        from lib.search.postgres_search import PostgreSQLSearchEngine

        engine = PostgreSQLSearchEngine(pool=mock_pool)
        results = await engine.search('   ', kb_id=1)

        assert results == [], '仅空白字符的查询应返回空列表'

    @pytest.mark.asyncio
    async def test_search_handles_database_error_gracefully(self) -> None:
        """验证搜索在数据库错误时优雅降级"""
        mock_conn = _create_mock_connection()
        mock_conn.fetch = AsyncMock(side_effect=Exception('Database error'))
        mock_pool = _create_mock_pool(mock_conn)

        from lib.search.postgres_search import PostgreSQLSearchEngine

        engine = PostgreSQLSearchEngine(pool=mock_pool)
        results = await engine.search('test', kb_id=1)

        # 搜索应在重试后返回空列表而非抛出异常
        assert results == [], '数据库错误时应返回空列表'

    @pytest.mark.asyncio
    async def test_suggest_returns_empty_for_short_prefix(self) -> None:
        """验证搜索建议在输入过短时返回空结果"""
        mock_pool = _create_mock_pool()
        from lib.search.postgres_search import PostgreSQLSearchEngine

        engine = PostgreSQLSearchEngine(pool=mock_pool)
        results = await engine.suggest('a', kb_id=1)

        assert results == [], '单个字符前缀应返回空列表'

    @pytest.mark.asyncio
    async def test_suggest_returns_empty_for_empty_prefix(self) -> None:
        """验证搜索建议在空前缀时返回空结果"""
        mock_pool = _create_mock_pool()
        from lib.search.postgres_search import PostgreSQLSearchEngine

        engine = PostgreSQLSearchEngine(pool=mock_pool)
        results = await engine.suggest('', kb_id=1)

        assert results == [], '空前缀应返回空列表'

    @pytest.mark.asyncio
    async def test_search_result_immutability(self) -> None:
        """验证搜索结果不修改原始 Mock 对象状态"""
        original_rows = [
            {
                'atom_id': 1,
                'slug': 'test',
                'title': 'Test Title',
                'content': 'Test Content',
                'metadata': {'tags': ['test']},
                'atom_type': 'method',
                'created_at': None,
                'updated_at': None,
                'kb_id': 1,
                'kb_name': 'KB',
                'rank': 0.9,
            },
        ]
        # 记录原始数据快照（不可变：创建副本而非引用）
        original_snapshot = [dict(row) for row in original_rows]

        mock_conn = _create_mock_connection(fetch_result=original_rows)
        mock_pool = _create_mock_pool(mock_conn)

        from lib.search.postgres_search import PostgreSQLSearchEngine

        engine = PostgreSQLSearchEngine(pool=mock_pool)
        results = await engine.search('test', kb_id=1)

        # 验证原始数据未被修改
        for i, original in enumerate(original_snapshot):
            assert original_rows[i] == original, (
                '搜索结果处理不应修改原始 Mock 数据'
            )

        # 验证结果已创建为新对象
        assert len(results) > 0
        assert results[0].title == 'Test Title'
