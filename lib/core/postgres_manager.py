"""PostgreSQL 数据库管理器

使用 asyncpg 连接池实现高性能异步数据库操作。
支持事务、重试机制和错误处理。
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .db_manager import DatabaseManager
from .config import StorageConfig, StorageType


class PostgreSQLManager(DatabaseManager):
    """PostgreSQL 数据库管理器

    使用 asyncpg 连接池实现：
    - 连接池管理
    - 事务处理
    - 错误处理
    - 重试机制

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
        """初始化数据库连接池"""
        import asyncpg

        self.pool = await asyncpg.create_pool(
            self.config.postgres_url,
            min_size=2,
            max_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            command_timeout=60,
        )

        # 初始化表结构
        async with self.pool.acquire() as conn:
            await self._init_tables(conn)

        self._connected = True

    async def _init_tables(self, conn) -> None:
        """初始化表结构

        Args:
            conn: asyncpg 连接
        """
        # 启用 pgvector 扩展
        await conn.execute('CREATE EXTENSION IF NOT EXISTS vector')

        # 知识库表
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                description TEXT DEFAULT '',
                tags JSONB DEFAULT '[]'::jsonb,
                kb_type TEXT DEFAULT 'standalone',
                parent_id INTEGER REFERENCES knowledge_bases(id),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_accessed_at TIMESTAMPTZ,
                scope TEXT DEFAULT 'global'
            )
        ''')

        # 知识原子表
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS atoms (
                id SERIAL PRIMARY KEY,
                kb_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                path TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                tags JSONB DEFAULT '[]'::jsonb,
                body TEXT DEFAULT '',
                frontmatter JSONB DEFAULT '{}'::jsonb,
                embedding vector(384),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                file_mtime REAL DEFAULT 0,
                UNIQUE(kb_id, path)
            )
        ''')

        # 原子链接表
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS atom_links (
                id SERIAL PRIMARY KEY,
                source_atom_id INTEGER NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,
                target_atom_id INTEGER NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,
                link_type TEXT DEFAULT 'reference',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(source_atom_id, target_atom_id, link_type)
            )
        ''')

        # 子知识库关系表
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS kb_children (
                parent_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                child_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                child_path TEXT NOT NULL,
                PRIMARY KEY (parent_id, child_id)
            )
        ''')

        # 全文索引（使用 PostgreSQL 全文搜索）
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_atoms_title_fts ON atoms
            USING gin(to_tsvector('simple', title))
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_atoms_body_fts ON atoms
            USING gin(to_tsvector('simple', body))
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_atoms_description_fts ON atoms
            USING gin(to_tsvector('simple', description))
        ''')

        # 普通索引
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_atoms_kb_id ON atoms(kb_id)
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_atoms_type ON atoms(type)
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_atoms_tags ON atoms USING gin(tags)
        ''')

        # 更新时间触发器
        await conn.execute('''
            CREATE OR REPLACE FUNCTION update_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        ''')

        await conn.execute('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'knowledge_bases_updated_at'
                ) THEN
                    CREATE TRIGGER knowledge_bases_updated_at
                    BEFORE UPDATE ON knowledge_bases
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'atoms_updated_at'
                ) THEN
                    CREATE TRIGGER atoms_updated_at
                    BEFORE UPDATE ON atoms
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
                END IF;
            END;
            $$
        ''')

    async def close(self) -> None:
        """关闭数据库连接池"""
        if self.pool:
            await self.pool.close()
            self.pool = None
        self._connected = False

    async def is_connected(self) -> bool:
        """检查数据库连接状态"""
        return self._connected and self.pool is not None

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
        if not self._validate_kb_data(kb_data):
            raise ValueError("Invalid kb_data: missing required fields")

        async def _create():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    INSERT INTO knowledge_bases
                    (name, path, description, tags, kb_type, parent_id, scope)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                ''',
                kb_data['name'],
                kb_data['path'],
                kb_data.get('description', ''),
                json.dumps(kb_data.get('tags', [])),
                kb_data.get('kb_type', 'standalone'),
                kb_data.get('parent_id'),
                kb_data.get('scope', 'global'),
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
                        'SELECT * FROM knowledge_bases WHERE scope = $1 ORDER BY name',
                        scope
                    )
                return [self._row_to_kb_dict(row) for row in rows]

        return await self._execute_with_retry(_list)

    async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool:
        """更新知识库"""
        async def _update():
            async with self.pool.acquire() as conn:
                result = await conn.execute('''
                    UPDATE knowledge_bases SET
                        name = COALESCE($2, name),
                        path = COALESCE($3, path),
                        description = COALESCE($4, description),
                        tags = COALESCE($5, tags),
                        kb_type = COALESCE($6, kb_type)
                    WHERE id = $1
                ''',
                kb_id,
                kb_data.get('name'),
                kb_data.get('path'),
                kb_data.get('description'),
                json.dumps(kb_data.get('tags')) if 'tags' in kb_data else None,
                kb_data.get('kb_type'),
                )
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
        if not self._validate_atom_data(atom_data):
            raise ValueError("Invalid atom_data: missing required fields")

        async def _create():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    INSERT INTO atoms
                    (kb_id, path, type, title, description, tags, body, frontmatter, file_mtime)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                ''',
                atom_data['kb_id'],
                atom_data['path'],
                atom_data['type'],
                atom_data['title'],
                atom_data.get('description', ''),
                json.dumps(atom_data.get('tags', [])),
                atom_data.get('body', ''),
                json.dumps(atom_data.get('frontmatter', {})),
                atom_data.get('file_mtime', 0),
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
        """根据路径获取知识原子"""
        async def _get():
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM atoms WHERE kb_id = $1 AND path = $2',
                    kb_id, path
                )
                return self._row_to_atom_dict(row) if row else None

        return await self._execute_with_retry(_get)

    async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool:
        """更新知识原子"""
        async def _update():
            async with self.pool.acquire() as conn:
                # 构建动态更新
                updates = []
                params = [atom_id]
                param_idx = 2

                field_mapping = {
                    'type': 'type',
                    'title': 'title',
                    'description': 'description',
                    'body': 'body',
                    'file_mtime': 'file_mtime',
                }

                for field, column in field_mapping.items():
                    if field in atom_data:
                        updates.append(f"{column} = ${param_idx}")
                        params.append(atom_data[field])
                        param_idx += 1

                if 'tags' in atom_data:
                    updates.append(f"tags = ${param_idx}")
                    params.append(json.dumps(atom_data['tags']))
                    param_idx += 1

                if 'frontmatter' in atom_data:
                    updates.append(f"frontmatter = ${param_idx}")
                    params.append(json.dumps(atom_data['frontmatter']))
                    param_idx += 1

                if not updates:
                    return False

                sql = f"UPDATE atoms SET {', '.join(updates)} WHERE id = $1"
                result = await conn.execute(sql, *params)
                return result == 'UPDATE 1'

        return await self._execute_with_retry(_update)

    async def delete_atom(self, atom_id: int) -> bool:
        """删除知识原子"""
        async def _delete():
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    'DELETE FROM atoms WHERE id = $1', atom_id
                )
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
                        WHERE kb_id = $1 AND type = $2
                        ORDER BY title
                        LIMIT $3 OFFSET $4
                    ''', kb_id, by_type, limit, offset)
                else:
                    rows = await conn.fetch('''
                        SELECT * FROM atoms
                        WHERE kb_id = $1
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
        """搜索知识原子（使用 PostgreSQL 全文搜索）"""
        async def _search():
            async with self.pool.acquire() as conn:
                # 使用 PostgreSQL 全文搜索
                ts_query = ' & '.join(query.split())

                sql = '''
                    SELECT a.*, kb.name as kb_name,
                           ts_rank(
                               to_tsvector('simple', a.title || ' ' || a.description || ' ' || a.body),
                               to_tsquery('simple', $1)
                           ) as rank
                    FROM atoms a
                    LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id
                    WHERE to_tsvector('simple', a.title || ' ' || a.description || ' ' || a.body)
                          @@ to_tsquery('simple', $1)
                '''
                params = [ts_query]
                param_idx = 2

                if kb_id:
                    sql += f" AND a.kb_id = ${param_idx}"
                    params.append(kb_id)
                    param_idx += 1

                if by_type:
                    sql += f" AND a.type = ${param_idx}"
                    params.append(by_type)
                    param_idx += 1

                if tags:
                    sql += f" AND a.tags @> ${param_idx}::jsonb"
                    params.append(json.dumps(tags))
                    param_idx += 1

                sql += f" ORDER BY rank DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
                params.extend([limit, offset])

                rows = await conn.fetch(sql, *params)
                return [self._row_to_atom_dict(row) for row in rows]

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
                           ts_rank(
                               to_tsvector('simple', a.title || ' ' || a.description || ' ' || a.body),
                               to_tsquery('simple', $1)
                           ) as rank
                    FROM atoms a
                    LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id
                    WHERE to_tsvector('simple', a.title || ' ' || a.description || ' ' || a.body)
                          @@ to_tsquery('simple', $1)
                '''
                params = [ts_query]
                param_idx = 2

                # 应用过滤条件
                if 'kb_id' in filters:
                    sql += f" AND a.kb_id = ${param_idx}"
                    params.append(filters['kb_id'])
                    param_idx += 1

                if 'type' in filters:
                    sql += f" AND a.type = ${param_idx}"
                    params.append(filters['type'])
                    param_idx += 1

                if 'tags' in filters and filters['tags']:
                    sql += f" AND a.tags @> ${param_idx}::jsonb"
                    params.append(json.dumps(filters['tags']))
                    param_idx += 1

                if 'author' in filters:
                    sql += f" AND a.frontmatter->>'author' = ${param_idx}"
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

                # 排序
                if sort_by == 'time':
                    sql += " ORDER BY a.created_at DESC"
                elif sort_by == 'title':
                    sql += " ORDER BY a.title"
                else:  # relevance
                    sql += " ORDER BY rank DESC"

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
                    await conn.execute('''
                        INSERT INTO kb_children (parent_id, child_id, child_path)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (parent_id, child_id) DO UPDATE SET child_path = $3
                    ''', parent_id, child_id, child_path)

                    # 更新父知识库类型
                    await conn.execute(
                        'UPDATE knowledge_bases SET kb_type = $1 WHERE id = $2',
                        ('parent', parent_id)
                    )

                    # 更新子知识库类型和父 ID
                    await conn.execute(
                        'UPDATE knowledge_bases SET kb_type = $1, parent_id = $2 WHERE id = $3',
                        ('child', parent_id, child_id)
                    )

                    return True

        return await self._execute_with_retry(_register)

    async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]:
        """获取子知识库列表"""
        async def _get():
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT kb.*, kbc.child_path
                    FROM knowledge_bases kb
                    JOIN kb_children kbc ON kb.id = kbc.child_id
                    WHERE kbc.parent_id = $1
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
                    JOIN kb_children kbc ON kb.id = kbc.parent_id
                    WHERE kbc.child_id = $1
                ''', child_id)

                return self._row_to_kb_dict(row) if row else None

        return await self._execute_with_retry(_get)

    # ========== 统计操作 ==========

    async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]:
        """获取知识库统计信息"""
        async def _stats():
            async with self.pool.acquire() as conn:
                # 总原子数
                total_row = await conn.fetchrow(
                    'SELECT COUNT(*) as count FROM atoms WHERE kb_id = $1', kb_id
                )
                total_atoms = total_row['count']

                # 按类型统计
                type_rows = await conn.fetch('''
                    SELECT type, COUNT(*) as count
                    FROM atoms
                    WHERE kb_id = $1
                    GROUP BY type
                ''', kb_id)
                types_count = {row['type']: row['count'] for row in type_rows}

                return {
                    'total_atoms': total_atoms,
                    'types_count': types_count,
                }

        return await self._execute_with_retry(_stats)

    async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int:
        """获取知识原子数量"""
        async def _count():
            async with self.pool.acquire() as conn:
                if by_type:
                    row = await conn.fetchrow(
                        'SELECT COUNT(*) as count FROM atoms WHERE kb_id = $1 AND type = $2',
                        kb_id, by_type
                    )
                else:
                    row = await conn.fetchrow(
                        'SELECT COUNT(*) as count FROM atoms WHERE kb_id = $1', kb_id
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

    def _row_to_kb_dict(self, row) -> Dict[str, Any]:
        """将数据库行转换为知识库字典"""
        return {
            'id': row['id'],
            'name': row['name'],
            'path': row['path'],
            'description': row['description'],
            'tags': row['tags'] if isinstance(row['tags'], list) else json.loads(row['tags']) if row['tags'] else [],
            'kb_type': row['kb_type'],
            'parent_id': row['parent_id'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
            'last_accessed_at': row['last_accessed_at'].isoformat() if row['last_accessed_at'] else None,
            'scope': row['scope'],
        }

    def _row_to_atom_dict(self, row) -> Dict[str, Any]:
        """将数据库行转换为知识原子字典"""
        result = {
            'id': row['id'],
            'kb_id': row['kb_id'],
            'path': row['path'],
            'type': row['type'],
            'title': row['title'],
            'description': row['description'],
            'tags': row['tags'] if isinstance(row['tags'], list) else json.loads(row['tags']) if row['tags'] else [],
            'body': row['body'],
            'frontmatter': row['frontmatter'] if isinstance(row['frontmatter'], dict) else json.loads(row['frontmatter']) if row['frontmatter'] else {},
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
            'file_mtime': row['file_mtime'],
        }
        if 'kb_name' in row.keys():
            result['kb_name'] = row['kb_name']
        if 'rank' in row.keys():
            result['rank'] = float(row['rank'])
        return result
