"""PostgreSQL 数据库管理器

使用 asyncpg 连接池实现高性能异步数据库操作。
支持事务、重试机制、RLS 上下文管理和错误处理。
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db_manager import DatabaseManager
from .config import StorageConfig, StorageType

logger = logging.getLogger(__name__)

# SQL 文件目录
_DB_DIR = Path(__file__).parent.parent / "db"


class PostgreSQLManager(DatabaseManager):
    """PostgreSQL 数据库管理器

    使用 asyncpg 连接池实现：
    - 连接池管理
    - 事务处理
    - RLS 上下文管理
    - 错误处理
    - 重试机制
    - Schema 版本管理

    Attributes:
        config: 存储配置
        pool: asyncpg 连接池
    """

    def __init__(self, config: StorageConfig):
        """初始化 PostgreSQL 管理器

        Args:
            config: 存储配置（必须包含 postgres_url）
        """
        if config.type != StorageType.POSTGRES:
            raise ValueError("Config type must be POSTGRES")

        if not config.postgres_url:
            raise ValueError("postgres_url is required")

        self.config = config
        self.pool = None
        self._connected = False
        self._transaction_conn = None

    async def initialize(self) -> None:
        """初始化数据库连接池和表结构"""
        import asyncpg

        self.pool = await asyncpg.create_pool(
            self.config.postgres_url,
            min_size=2,
            max_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            command_timeout=60,
        )

        # 加载完整 schema 初始化表结构
        async with self.pool.acquire() as conn:
            await self._init_schema(conn)

        self._connected = True

    async def _init_schema(self, conn) -> None:
        """从 SQL 文件加载完整 schema 初始化

        加载顺序: schema.sql → functions.sql → indexes.sql → rls.sql

        Args:
            conn: asyncpg 连接
        """
        sql_files = [
            _DB_DIR / "schema.sql",
            _DB_DIR / "functions.sql",
            _DB_DIR / "indexes.sql",
            _DB_DIR / "rls.sql",
        ]

        for sql_file in sql_files:
            if not sql_file.exists():
                logger.warning("SQL file not found, skipping: %s", sql_file)
                continue

            sql_content = sql_file.read_text(encoding="utf-8")
            # 移除注释行（以 -- 开头的单行注释）
            # asyncpg 不支持在 execute 中包含注释
            statements = self._split_sql(sql_content)
            for stmt in statements:
                stmt = stmt.strip()
                if stmt:
                    try:
                        await conn.execute(stmt)
                    except Exception as e:
                        # 某些语句可能因为对象已存在而失败（IF NOT EXISTS 不适用于所有场景）
                        error_msg = str(e).lower()
                        if any(skip in error_msg for skip in [
                            'already exists',
                            'duplicate',
                            'conflict',
                        ]):
                            logger.debug("Skipping already-existing object: %s", e)
                        else:
                            logger.error("Failed to execute SQL from %s: %s", sql_file.name, e)
                            raise

        logger.info("Schema initialized from SQL files")

    @staticmethod
    def _split_sql(sql_content: str) -> List[str]:
        """将 SQL 文件内容拆分为独立语句

        处理 $$...$$ 块内的分号，避免误拆。

        Args:
            sql_content: SQL 文件内容

        Returns:
            SQL 语句列表
        """
        statements = []
        current = []
        in_dollar_quote = False

        for line in sql_content.split("\n"):
            stripped = line.strip()

            # 跳过空行和纯注释行
            if not stripped or stripped.startswith("--"):
                continue

            # 追踪 $$ 块
            dollar_count = stripped.count("$$")
            if dollar_count > 0:
                in_dollar_quote = not in_dollar_quote

            current.append(line)

            # 行以分号结束且不在 $$ 块内
            if stripped.endswith(";") and not in_dollar_quote:
                stmt = "\n".join(current)
                statements.append(stmt)
                current = []

        # 处理未以分号结束的最后一条
        if current:
            remaining = "\n".join(current).strip()
            if remaining:
                statements.append(remaining)

        return statements

    async def close(self) -> None:
        """关闭数据库连接池"""
        if self.pool:
            await self.pool.close()
            self.pool = None
        self._connected = False

    async def is_connected(self) -> bool:
        """检查数据库连接状态"""
        return self._connected and self.pool is not None

    # ========== 通用数据访问方法 ==========

    async def execute(self, query: str, *args) -> str:
        """执行 SQL 语句

        Args:
            query: SQL 语句
            *args: 参数

        Returns:
            执行结果字符串
        """
        async def _exec():
            async with self.pool.acquire() as conn:
                return await conn.execute(query, *args)

        return await self._execute_with_retry(_exec)

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """查询单条记录

        Args:
            query: SQL 查询
            *args: 参数

        Returns:
            记录字典，不存在返回 None
        """
        async def _fetch():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None

        return await self._execute_with_retry(_fetch)

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """查询多条记录

        Args:
            query: SQL 查询
            *args: 参数

        Returns:
            记录字典列表
        """
        async def _fetch():
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]

        return await self._execute_with_retry(_fetch)

    # ========== RLS 上下文管理 ==========

    async def set_rls_context(self, user_id: str, roles: Optional[List[str]] = None) -> None:
        """设置 RLS 用户上下文

        在每个请求开始时调用，设置当前用户 ID，
        使 RLS 策略基于此 ID 进行权限过滤。

        Args:
            user_id: 用户 ID
            roles: 用户角色列表（可选，Python 层 RBAC 使用）
        """
        async def _set():
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT set_current_user_id($1)", user_id)

        await self._execute_with_retry(_set)
        logger.debug("RLS context set: user_id=%s", user_id)

    async def clear_rls_context(self) -> None:
        """清除 RLS 用户上下文

        在请求结束后调用，清除用户上下文，
        避免连接归还池后保留上一个用户的信息。
        """
        async def _clear():
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT clear_current_user_id()")

        await self._execute_with_retry(_clear)

    # ========== 重试机制 ==========

    async def _execute_with_retry(self, operation, max_retries: int = 3,
                                   retry_delay: float = 0.1) -> Any:
        """带重试的操作执行

        Args:
            operation: 异步操作函数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）

        Returns:
            操作结果
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
        raise last_error

    # ========== 知识库操作 ==========

    async def create_kb(self, kb_data: Dict[str, Any]) -> int:
        """创建知识库"""
        required_fields = ['name']
        if not all(field in kb_data for field in required_fields):
            raise ValueError("Invalid kb_data: missing required fields (name)")

        async def _create():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    INSERT INTO knowledge_bases
                    (name, slug, type, description, organization_id,
                     owner_id, department_id, project_id,
                     visibility, storage_mode, settings, created_by)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    RETURNING id
                ''',
                kb_data['name'],
                kb_data.get('slug', kb_data['name'].lower().replace(' ', '-')),
                kb_data.get('type', 'personal'),
                kb_data.get('description', ''),
                kb_data.get('organization_id'),
                kb_data.get('owner_id'),
                kb_data.get('department_id'),
                kb_data.get('project_id'),
                kb_data.get('visibility', 'private'),
                kb_data.get('storage_mode', 'db'),
                json.dumps(kb_data.get('settings', {})),
                kb_data.get('created_by'),
                )
                return row['id']

        return await self._execute_with_retry(_create)

    async def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]:
        """获取知识库信息"""
        async def _get():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM knowledge_bases WHERE id = $1', kb_id
                )
                return self._row_to_kb_dict(row) if row else None

        return await self._execute_with_retry(_get)

    async def get_kb_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取知识库信息"""
        async def _get():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM knowledge_bases WHERE name = $1', name
                )
                return self._row_to_kb_dict(row) if row else None

        return await self._execute_with_retry(_get)

    async def list_kbs(self, user_id: Optional[str] = None,
                       scope: str = 'all') -> List[Dict[str, Any]]:
        """列出知识库"""
        async def _list():
            async with self.pool.acquire() as conn:
                if scope == 'all':
                    rows = await conn.fetch(
                        'SELECT * FROM knowledge_bases ORDER BY name'
                    )
                else:
                    rows = await conn.fetch(
                        'SELECT * FROM knowledge_bases WHERE type = $1 ORDER BY name',
                        scope
                    )
                return [self._row_to_kb_dict(row) for row in rows]

        return await self._execute_with_retry(_list)

    async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool:
        """更新知识库"""
        async def _update():
            async with self.pool.acquire() as conn:
                # 允许更新的字段白名单
                allowed_fields = {
                    'name', 'slug', 'type', 'description',
                    'visibility', 'storage_mode', 'settings',
                    'organization_id', 'department_id', 'project_id',
                }

                updates = []
                params = [kb_id]
                param_idx = 2

                for field in allowed_fields:
                    if field in kb_data:
                        updates.append(f"{field} = ${param_idx}")
                        value = kb_data[field]
                        # JSONB 字段需要序列化
                        if field == 'settings' and isinstance(value, dict):
                            value = json.dumps(value)
                        params.append(value)
                        param_idx += 1

                if not updates:
                    return False

                sql = f"UPDATE knowledge_bases SET {', '.join(updates)} WHERE id = $1"
                result = await conn.execute(sql, *params)
                return result == 'UPDATE 1'

        return await self._execute_with_retry(_update)

    async def delete_kb(self, kb_id: int) -> bool:
        """删除知识库"""
        async def _delete():
            async with self.pool.acquire() as conn:
                # ON DELETE CASCADE 会自动删除关联的原子和子关系
                result = await conn.execute(
                    'DELETE FROM knowledge_bases WHERE id = $1', kb_id
                )
                return result == 'DELETE 1'

        return await self._execute_with_retry(_delete)

    # ========== 知识原子操作 ==========

    async def create_atom(self, atom_data: Dict[str, Any]) -> int:
        """创建知识原子"""
        required_fields = ['kb_id', 'title', 'content', 'type']
        if not all(field in atom_data for field in required_fields):
            raise ValueError("Invalid atom_data: missing required fields (kb_id, title, content, type)")

        async def _create():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    INSERT INTO atoms
                    (kb_id, title, slug, type, description,
                     content, metadata, author_id, embedding, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                ''',
                atom_data['kb_id'],
                atom_data['title'],
                atom_data.get('slug'),
                atom_data['type'],
                atom_data.get('description', ''),
                atom_data.get('content', ''),
                json.dumps(atom_data.get('metadata', {})),
                atom_data.get('author_id'),
                atom_data.get('embedding'),
                atom_data.get('status', 'active'),
                )
                return row['id']

        return await self._execute_with_retry(_create)

    async def get_atom(self, atom_id: int) -> Optional[Dict[str, Any]]:
        """获取知识原子"""
        async def _get():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM atoms WHERE id = $1', atom_id
                )
                return self._row_to_atom_dict(row) if row else None

        return await self._execute_with_retry(_get)

    async def get_atom_by_path(self, kb_id: int, path: str) -> Optional[Dict[str, Any]]:
        """根据 slug 获取知识原子（兼容旧 path 参数）"""
        async def _get():
            async with self.pool.acquire() as conn:
                # 优先按 slug 查找，兼容旧系统用 path 查找
                row = await conn.fetchrow(
                    'SELECT * FROM atoms WHERE kb_id = $1 AND slug = $2',
                    kb_id, path
                )
                if not row:
                    # 兼容：也检查 metadata->>'path'
                    row = await conn.fetchrow(
                        '''SELECT * FROM atoms
                        WHERE kb_id = $1 AND metadata->>'path' = $2''',
                        kb_id, path
                    )
                return self._row_to_atom_dict(row) if row else None

        return await self._execute_with_retry(_get)

    async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool:
        """更新知识原子"""
        async def _update():
            async with self.pool.acquire() as conn:
                # 检查锁定状态
                current = await conn.fetchrow(
                    'SELECT is_locked FROM atoms WHERE id = $1', atom_id
                )
                if not current:
                    return False
                if current['is_locked']:
                    raise RuntimeError(f"Atom {atom_id} is locked and cannot be updated")

                # 允许更新的字段白名单
                allowed_fields = {
                    'title', 'slug', 'type', 'description',
                    'content', 'metadata', 'author_id',
                    'embedding', 'status',
                }

                updates = []
                params = [atom_id]
                param_idx = 2

                for field in allowed_fields:
                    if field in atom_data:
                        updates.append(f"{field} = ${param_idx}")
                        value = atom_data[field]
                        # JSONB 字段需要序列化
                        if field == 'metadata' and isinstance(value, dict):
                            value = json.dumps(value)
                        params.append(value)
                        param_idx += 1

                if not updates:
                    return False

                sql = f"UPDATE atoms SET {', '.join(updates)} WHERE id = $1"
                result = await conn.execute(sql, *params)
                return result == 'UPDATE 1'

        return await self._execute_with_retry(_update)

    async def delete_atom(self, atom_id: int) -> bool:
        """删除知识原子（支持软删除）"""
        async def _delete():
            async with self.pool.acquire() as conn:
                # 默认软删除（标记为 archived）
                hard_delete = False
                if 'hard_delete' in str(atom_id):
                    hard_delete = True

                if hard_delete:
                    result = await conn.execute(
                        'DELETE FROM atoms WHERE id = $1', atom_id
                    )
                else:
                    result = await conn.execute(
                        "UPDATE atoms SET status = 'archived' WHERE id = $1", atom_id
                    )
                    return result == 'UPDATE 1'

                return result == 'DELETE 1'

        return await self._execute_with_retry(_delete)

    async def list_atoms(self, kb_id: int, by_type: Optional[str] = None,
                         limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """列出知识原子"""
        async def _list():
            async with self.pool.acquire() as conn:
                if by_type:
                    rows = await conn.fetch('''
                        SELECT * FROM atoms
                        WHERE kb_id = $1 AND type = $2 AND status = 'active'
                        ORDER BY title
                        LIMIT $3 OFFSET $4
                    ''', kb_id, by_type, limit, offset)
                else:
                    rows = await conn.fetch('''
                        SELECT * FROM atoms
                        WHERE kb_id = $1 AND status = 'active'
                        ORDER BY title
                        LIMIT $2 OFFSET $3
                    ''', kb_id, limit, offset)

                return [self._row_to_atom_dict(row) for row in rows]

        return await self._execute_with_retry(_list)

    # ========== 搜索操作 ==========

    async def search_atoms(self, query: str, kb_id: Optional[int] = None,
                           by_type: Optional[str] = None,
                           tags: Optional[List[str]] = None,
                           limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索知识原子（使用 PostgreSQL 全文搜索 + pg_trgm 模糊搜索）"""
        async def _search():
            async with self.pool.acquire() as conn:
                # 优先使用全文搜索
                ts_query = ' & '.join(query.split())

                sql = '''
                    SELECT a.*, kb.name as kb_name,
                           ts_rank(a.content_tsv, websearch_to_tsquery('english', $1)) as rank
                    FROM atoms a
                    LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id
                    WHERE a.status = 'active'
                      AND a.content_tsv @@ websearch_to_tsquery('english', $1)
                '''
                params = [query]
                param_idx = 2

                if kb_id:
                    sql += f" AND a.kb_id = ${param_idx}"
                    params.append(kb_id)
                    param_idx += 1

                if by_type:
                    sql += f" AND a.type = ${param_idx}::atom_type"
                    params.append(by_type)
                    param_idx += 1

                if tags:
                    sql += f" AND a.metadata->'tags' @> ${param_idx}::jsonb"
                    params.append(json.dumps(tags))
                    param_idx += 1

                sql += f" ORDER BY rank DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
                params.extend([limit, offset])

                rows = await conn.fetch(sql, *params)
                results = [self._row_to_atom_dict(row) for row in rows]

                # 如果全文搜索无结果，回退到 pg_trgm 模糊搜索
                if not results:
                    fallback_sql = '''
                        SELECT a.*, kb.name as kb_name,
                               similarity(a.title, $1) +
                               similarity(coalesce(a.description, ''), $1) as rank
                        FROM atoms a
                        LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id
                        WHERE a.status = 'active'
                          AND (a.title % $1 OR a.description % $1)
                    '''
                    fb_params = [query]
                    fb_idx = 2

                    if kb_id:
                        fallback_sql += f" AND a.kb_id = ${fb_idx}"
                        fb_params.append(kb_id)
                        fb_idx += 1

                    fallback_sql += f" ORDER BY rank DESC LIMIT ${fb_idx} OFFSET ${fb_idx + 1}"
                    fb_params.extend([limit, offset])

                    rows = await conn.fetch(fallback_sql, *fb_params)
                    results = [self._row_to_atom_dict(row) for row in rows]

                return results

        return await self._execute_with_retry(_search)

    async def search_atoms_advanced(self, query: str,
                                     filters: Optional[Dict[str, Any]] = None,
                                     sort_by: str = 'relevance',
                                     limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """高级搜索知识原子"""
        filters = filters or {}

        async def _search():
            async with self.pool.acquire() as conn:
                ts_query = ' & '.join(query.split())

                sql = '''
                    SELECT a.*, kb.name as kb_name,
                           ts_rank(a.content_tsv, websearch_to_tsquery('english', $1)) as rank
                    FROM atoms a
                    LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id
                    WHERE a.status = 'active'
                      AND a.content_tsv @@ websearch_to_tsquery('english', $1)
                '''
                params = [query]
                param_idx = 2

                # 应用过滤条件
                if 'kb_id' in filters:
                    sql += f" AND a.kb_id = ${param_idx}"
                    params.append(filters['kb_id'])
                    param_idx += 1

                if 'type' in filters:
                    sql += f" AND a.type = ${param_idx}::atom_type"
                    params.append(filters['type'])
                    param_idx += 1

                if 'tags' in filters and filters['tags']:
                    sql += f" AND a.metadata->'tags' @> ${param_idx}::jsonb"
                    params.append(json.dumps(filters['tags']))
                    param_idx += 1

                if 'author' in filters:
                    sql += f" AND a.author_id = ${param_idx}"
                    params.append(filters['author'])
                    param_idx += 1

                if 'date_from' in filters:
                    sql += f" AND a.created_at >= ${param_idx}"
                    params.append(filters['date_from'])
                    param_idx += 1

                if 'date_to' in filters:
                    sql += f" AND a.created_at <= ${param_idx}"
                    params.append(filters['date_to'])
                    param_idx += 1

                if 'status' in filters:
                    sql += f" AND a.status = ${param_idx}::atom_status"
                    params.append(filters['status'])
                    param_idx += 1

                # 排序
                safe_sort = {
                    'time': 'a.created_at DESC',
                    'title': 'a.title',
                    'relevance': 'rank DESC',
                }
                sql += f" ORDER BY {safe_sort.get(sort_by, 'rank DESC')}"

                sql += f" LIMIT ${param_idx} OFFSET ${param_idx + 1}"
                params.extend([limit, offset])

                rows = await conn.fetch(sql, *params)
                return [self._row_to_atom_dict(row) for row in rows]

        return await self._execute_with_retry(_search)

    # ========== 父子知识库操作 ==========

    async def register_child_kb(self, parent_id: int, child_id: int,
                                 child_path: str) -> bool:
        """注册子知识库到父知识库"""
        async def _register():
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # 使用聚合表替代 kb_children
                    await conn.execute('''
                        INSERT INTO kb_aggregations (parent_kb_id, child_kb_id)
                        VALUES ($1, $2)
                        ON CONFLICT (parent_kb_id, child_kb_id) DO NOTHING
                    ''', parent_id, child_id)

                    # 标记父知识库为聚合知识库
                    await conn.execute(
                        'UPDATE knowledge_bases SET is_aggregated = true WHERE id = $1',
                        parent_id
                    )

                    return True

        return await self._execute_with_retry(_register)

    async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]:
        """获取子知识库列表"""
        async def _get():
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT kb.*, kbagg.include_private, kbagg.priority
                    FROM knowledge_bases kb
                    JOIN kb_aggregations kbagg ON kb.id = kbagg.child_kb_id
                    WHERE kbagg.parent_kb_id = $1
                    ORDER BY kb.name
                ''', parent_id)

                return [self._row_to_kb_dict(row) for row in rows]

        return await self._execute_with_retry(_get)

    async def get_parent_kb(self, child_id: int) -> Optional[Dict[str, Any]]:
        """获取父知识库信息"""
        async def _get():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT kb.*
                    FROM knowledge_bases kb
                    JOIN kb_aggregations kbagg ON kb.id = kbagg.parent_kb_id
                    WHERE kbagg.child_kb_id = $1
                ''', child_id)

                return self._row_to_kb_dict(row) if row else None

        return await self._execute_with_retry(_get)

    # ========== 统计操作 ==========

    async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]:
        """获取知识库统计信息"""
        async def _stats():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT
                        COUNT(*) AS total_atoms,
                        COUNT(*) FILTER (WHERE status = 'active') AS active_atoms,
                        COUNT(*) FILTER (WHERE status = 'archived') AS archived_atoms,
                        COUNT(*) FILTER (WHERE status = 'draft') AS draft_atoms
                    FROM atoms WHERE kb_id = $1
                ''', kb_id)

                return {
                    'total_atoms': row['total_atoms'] if row else 0,
                    'active_atoms': row['active_atoms'] if row else 0,
                    'archived_atoms': row['archived_atoms'] if row else 0,
                    'draft_atoms': row['draft_atoms'] if row else 0,
                }

        return await self._execute_with_retry(_stats)

    async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int:
        """获取知识原子数量"""
        async def _count():
            async with self.pool.acquire() as conn:
                if by_type:
                    row = await conn.fetchrow(
                        "SELECT COUNT(*) as count FROM atoms WHERE kb_id = $1 AND type = $2::atom_type AND status = 'active'",
                        kb_id, by_type
                    )
                else:
                    row = await conn.fetchrow(
                        "SELECT COUNT(*) as count FROM atoms WHERE kb_id = $1 AND status = 'active'",
                        kb_id
                    )
                return row['count']

        return await self._execute_with_retry(_count)

    # ========== 事务操作 ==========

    async def begin_transaction(self) -> None:
        """开始事务，获取独占连接."""
        if self._transaction_conn is not None:
            logger.warning("Transaction already active, nesting not supported")
            return
        self._transaction_conn = await self.pool.acquire()
        await self._transaction_conn.execute('BEGIN')
        logger.debug("PostgreSQL transaction started")

    async def commit_transaction(self) -> None:
        """提交事务并释放连接."""
        if self._transaction_conn is None:
            logger.warning("No active transaction to commit")
            return
        try:
            await self._transaction_conn.execute('COMMIT')
            logger.debug("PostgreSQL transaction committed")
        except Exception as e:
            logger.error("PostgreSQL commit failed: %s", e)
            await self._transaction_conn.execute('ROLLBACK')
            raise
        finally:
            await self.pool.release(self._transaction_conn)
            self._transaction_conn = None

    async def rollback_transaction(self) -> None:
        """回滚事务并释放连接."""
        if self._transaction_conn is None:
            logger.warning("No active transaction to rollback")
            return
        try:
            await self._transaction_conn.execute('ROLLBACK')
            logger.debug("PostgreSQL transaction rolled back")
        except Exception as e:
            logger.error("PostgreSQL rollback failed: %s", e)
            raise
        finally:
            await self.pool.release(self._transaction_conn)
            self._transaction_conn = None

    # ========== 工具方法 ==========

    @staticmethod
    def _row_to_kb_dict(row) -> Dict[str, Any]:
        """将数据库行转换为知识库字典"""
        if row is None:
            return {}
        return {
            'id': row['id'],
            'name': row['name'],
            'slug': row.get('slug'),
            'type': row.get('type'),
            'description': row.get('description', ''),
            'organization_id': row.get('organization_id'),
            'owner_id': row.get('owner_id'),
            'department_id': row.get('department_id'),
            'project_id': row.get('project_id'),
            'visibility': row.get('visibility', 'private'),
            'is_aggregated': row.get('is_aggregated', False),
            'storage_mode': row.get('storage_mode', 'db'),
            'settings': row.get('settings', {}),
            'created_by': row.get('created_by'),
            'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
            'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
        }

    @staticmethod
    def _row_to_atom_dict(row) -> Dict[str, Any]:
        """将数据库行转换为知识原子字典"""
        if row is None:
            return {}
        metadata = row.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        elif metadata is None:
            metadata = {}

        result = {
            'id': row['id'],
            'kb_id': row['kb_id'],
            'title': row['title'],
            'slug': row.get('slug'),
            'type': row.get('type'),
            'description': row.get('description', ''),
            'content': row.get('content', ''),
            'metadata': metadata,
            'author_id': row.get('author_id'),
            'status': row.get('status', 'active'),
            'is_locked': row.get('is_locked', False),
            'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
            'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
        }

        # 兼容旧字段名
        result['body'] = result['content']
        result['frontmatter'] = result['metadata']
        result['tags'] = metadata.get('tags', [])

        # 附加搜索相关字段
        if 'kb_name' in (row.keys() if hasattr(row, 'keys') else {}):
            result['kb_name'] = row['kb_name']
        if 'rank' in (row.keys() if hasattr(row, 'keys') else {}):
            result['rank'] = float(row['rank'])

        return result
