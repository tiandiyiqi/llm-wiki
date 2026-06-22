"""SQLite 数据库管理器

封装现有的文件存储操作，兼容 registry.json 和 Markdown 文件。
使用 SQLite FTS5 实现全文检索。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db_manager import DatabaseManager
from .config import StorageConfig, StorageType


class SQLiteManager(DatabaseManager):
    """SQLite 数据库管理器

    封装现有的文件存储操作：
    - 读取 ~/.llm-wiki/registry.json
    - 读取 Markdown 文件（atoms/ 目录）
    - 使用 FTS5 全文检索

    保持与现有 lib/registry.py 和 lib/querier.py 的兼容性。
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        """初始化 SQLite 管理器

        Args:
            config: 存储配置（可选）
        """
        self.config = config or StorageConfig(type=StorageType.SQLITE)
        self.global_dir = Path.home() / '.llm-wiki'
        self.global_registry = self.global_dir / 'registry.json'
        self.global_config = self.global_dir / 'config.json'

        # 数据库连接
        self._db_path: Optional[Path] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._connected: bool = False

    async def initialize(self) -> None:
        """初始化数据库连接"""
        # 确保目录存在
        self.global_dir.mkdir(parents=True, exist_ok=True)

        # 设置数据库路径
        if self.config.sqlite_data_dir:
            self._db_path = Path(self.config.sqlite_data_dir) / 'llm-wiki.db'
        else:
            self._db_path = self.global_dir / 'llm-wiki.db'

        # 创建连接
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row

        # 初始化表结构
        self._init_tables()
        self._connected = True

    def _init_tables(self) -> None:
        """初始化表结构"""
        # 知识库表
        self._conn.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                description TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                kb_type TEXT DEFAULT 'standalone',
                parent_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_accessed_at TEXT,
                scope TEXT DEFAULT 'global',
                FOREIGN KEY (parent_id) REFERENCES knowledge_bases(id)
            )
        ''')

        # 知识原子表
        self._conn.execute('''
            CREATE TABLE IF NOT EXISTS atoms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kb_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                body TEXT DEFAULT '',
                frontmatter TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                file_mtime REAL DEFAULT 0,
                UNIQUE(kb_id, path),
                FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id)
            )
        ''')

        # FTS5 全文索引
        try:
            self._conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS atoms_fts USING fts5(
                    atom_id,
                    title,
                    description,
                    body,
                    tags,
                    type,
                    content='atoms',
                    content_rowid='id'
                )
            ''')
        except sqlite3.OperationalError:
            # FTS5 不可用，创建普通索引
            self._conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_atoms_title ON atoms(title)
            ''')
            self._conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_atoms_body ON atoms(body)
            ''')

        # 子知识库关系表
        self._conn.execute('''
            CREATE TABLE IF NOT EXISTS kb_children (
                parent_id INTEGER NOT NULL,
                child_id INTEGER NOT NULL,
                child_path TEXT NOT NULL,
                PRIMARY KEY (parent_id, child_id),
                FOREIGN KEY (parent_id) REFERENCES knowledge_bases(id),
                FOREIGN KEY (child_id) REFERENCES knowledge_bases(id)
            )
        ''')

        self._conn.commit()

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
        self._connected = False

    async def is_connected(self) -> bool:
        """检查数据库连接状态"""
        return self._connected

    # ========== 知识库操作 ==========

    async def create_kb(self, kb_data: Dict[str, Any]) -> int:
        """创建知识库"""
        if not self._validate_kb_data(kb_data):
            raise ValueError("Invalid kb_data: missing required fields")

        now = self._get_timestamp()
        tags_json = json.dumps(kb_data.get('tags', []), ensure_ascii=False)

        cursor = self._conn.execute('''
            INSERT INTO knowledge_bases
            (name, path, description, tags, kb_type, parent_id, created_at, updated_at, scope)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            kb_data['name'],
            kb_data['path'],
            kb_data.get('description', ''),
            tags_json,
            kb_data.get('kb_type', 'standalone'),
            kb_data.get('parent_id'),
            now,
            now,
            kb_data.get('scope', 'global'),
        ))
        self._conn.commit()
        return cursor.lastrowid

    async def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]:
        """获取知识库信息"""
        cursor = self._conn.execute(
            'SELECT * FROM knowledge_bases WHERE id = ?', (kb_id,)
        )
        row = cursor.fetchone()
        return self._row_to_kb_dict(row) if row else None

    async def get_kb_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取知识库信息"""
        cursor = self._conn.execute(
            'SELECT * FROM knowledge_bases WHERE name = ?', (name,)
        )
        row = cursor.fetchone()
        return self._row_to_kb_dict(row) if row else None

    async def list_kbs(self, user_id: Optional[str] = None,
                       scope: str = 'all') -> List[Dict[str, Any]]:
        """列出知识库"""
        if scope == 'all':
            cursor = self._conn.execute(
                'SELECT * FROM knowledge_bases ORDER BY name'
            )
        else:
            cursor = self._conn.execute(
                'SELECT * FROM knowledge_bases WHERE scope = ? ORDER BY name',
                (scope,)
            )

        return [self._row_to_kb_dict(row) for row in cursor.fetchall()]

    async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool:
        """更新知识库"""
        now = self._get_timestamp()
        tags_json = json.dumps(kb_data.get('tags', []), ensure_ascii=False)

        cursor = self._conn.execute('''
            UPDATE knowledge_bases SET
                name = COALESCE(?, name),
                path = COALESCE(?, path),
                description = COALESCE(?, description),
                tags = COALESCE(?, tags),
                kb_type = COALESCE(?, kb_type),
                updated_at = ?
            WHERE id = ?
        ''', (
            kb_data.get('name'),
            kb_data.get('path'),
            kb_data.get('description'),
            tags_json,
            kb_data.get('kb_type'),
            now,
            kb_id,
        ))
        self._conn.commit()
        return cursor.rowcount > 0

    async def delete_kb(self, kb_id: int) -> bool:
        """删除知识库"""
        # 先删除关联的原子
        self._conn.execute('DELETE FROM atoms WHERE kb_id = ?', (kb_id,))
        # 删除子关系
        self._conn.execute(
            'DELETE FROM kb_children WHERE parent_id = ? OR child_id = ?',
            (kb_id, kb_id)
        )
        # 删除知识库
        cursor = self._conn.execute(
            'DELETE FROM knowledge_bases WHERE id = ?', (kb_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    # ========== 知识原子操作 ==========

    async def create_atom(self, atom_data: Dict[str, Any]) -> int:
        """创建知识原子"""
        if not self._validate_atom_data(atom_data):
            raise ValueError("Invalid atom_data: missing required fields")

        now = self._get_timestamp()
        tags_json = json.dumps(atom_data.get('tags', []), ensure_ascii=False)
        frontmatter_json = json.dumps(
            atom_data.get('frontmatter', {}), ensure_ascii=False
        )

        cursor = self._conn.execute('''
            INSERT INTO atoms
            (kb_id, path, type, title, description, tags, body, frontmatter,
             created_at, updated_at, file_mtime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            atom_data['kb_id'],
            atom_data['path'],
            atom_data['type'],
            atom_data['title'],
            atom_data.get('description', ''),
            tags_json,
            atom_data.get('body', ''),
            frontmatter_json,
            now,
            now,
            atom_data.get('file_mtime', 0),
        ))
        self._conn.commit()
        return cursor.lastrowid

    async def get_atom(self, atom_id: int) -> Optional[Dict[str, Any]]:
        """获取知识原子"""
        cursor = self._conn.execute(
            'SELECT * FROM atoms WHERE id = ?', (atom_id,)
        )
        row = cursor.fetchone()
        return self._row_to_atom_dict(row) if row else None

    async def get_atom_by_path(self, kb_id: int, path: str) -> Optional[Dict[str, Any]]:
        """根据路径获取知识原子"""
        cursor = self._conn.execute(
            'SELECT * FROM atoms WHERE kb_id = ? AND path = ?',
            (kb_id, path)
        )
        row = cursor.fetchone()
        return self._row_to_atom_dict(row) if row else None

    async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool:
        """更新知识原子"""
        now = self._get_timestamp()
        tags_json = json.dumps(atom_data.get('tags', []), ensure_ascii=False) if 'tags' in atom_data else None
        frontmatter_json = json.dumps(
            atom_data.get('frontmatter', {}), ensure_ascii=False
        ) if 'frontmatter' in atom_data else None

        cursor = self._conn.execute('''
            UPDATE atoms SET
                type = COALESCE(?, type),
                title = COALESCE(?, title),
                description = COALESCE(?, description),
                tags = COALESCE(?, tags),
                body = COALESCE(?, body),
                frontmatter = COALESCE(?, frontmatter),
                file_mtime = COALESCE(?, file_mtime),
                updated_at = ?
            WHERE id = ?
        ''', (
            atom_data.get('type'),
            atom_data.get('title'),
            atom_data.get('description'),
            tags_json,
            atom_data.get('body'),
            frontmatter_json,
            atom_data.get('file_mtime'),
            now,
            atom_id,
        ))
        self._conn.commit()
        return cursor.rowcount > 0

    async def delete_atom(self, atom_id: int) -> bool:
        """删除知识原子"""
        cursor = self._conn.execute(
            'DELETE FROM atoms WHERE id = ?', (atom_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    async def list_atoms(self, kb_id: int, by_type: Optional[str] = None,
                         limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """列出知识原子"""
        if by_type:
            cursor = self._conn.execute('''
                SELECT * FROM atoms
                WHERE kb_id = ? AND type = ?
                ORDER BY title
                LIMIT ? OFFSET ?
            ''', (kb_id, by_type, limit, offset))
        else:
            cursor = self._conn.execute('''
                SELECT * FROM atoms
                WHERE kb_id = ?
                ORDER BY title
                LIMIT ? OFFSET ?
            ''', (kb_id, limit, offset))

        return [self._row_to_atom_dict(row) for row in cursor.fetchall()]

    # ========== 搜索操作 ==========

    async def search_atoms(self, query: str, kb_id: Optional[int] = None,
                           by_type: Optional[str] = None,
                           tags: Optional[List[str]] = None,
                           limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索知识原子"""
        # 构建基础查询
        sql = '''
            SELECT a.*, kb.name as kb_name
            FROM atoms a
            LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id
            WHERE (a.title LIKE ? OR a.description LIKE ? OR a.body LIKE ?)
        '''
        params = [f'%{query}%', f'%{query}%', f'%{query}%']

        if kb_id:
            sql += ' AND a.kb_id = ?'
            params.append(kb_id)

        if by_type:
            sql += ' AND a.type = ?'
            params.append(by_type)

        if tags:
            for tag in tags:
                sql += ' AND a.tags LIKE ?'
                params.append(f'%{tag}%')

        sql += ' ORDER BY a.title LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor = self._conn.execute(sql, params)
        return [self._row_to_atom_dict(row) for row in cursor.fetchall()]

    async def search_atoms_advanced(self, query: str,
                                     filters: Optional[Dict[str, Any]] = None,
                                     sort_by: str = 'relevance',
                                     limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """高级搜索知识原子"""
        filters = filters or {}

        sql = '''
            SELECT a.*, kb.name as kb_name
            FROM atoms a
            LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id
            WHERE (a.title LIKE ? OR a.description LIKE ? OR a.body LIKE ?)
        '''
        params = [f'%{query}%', f'%{query}%', f'%{query}%']

        # 应用过滤条件
        if 'kb_id' in filters:
            sql += ' AND a.kb_id = ?'
            params.append(filters['kb_id'])

        if 'type' in filters:
            sql += ' AND a.type = ?'
            params.append(filters['type'])

        if 'tags' in filters and filters['tags']:
            for tag in filters['tags']:
                sql += ' AND a.tags LIKE ?'
                params.append(f'%{tag}%')

        if 'author' in filters:
            sql += ' AND a.frontmatter LIKE ?'
            params.append(f'%"author": "%{filters["author"]}"%')

        if 'date_from' in filters:
            sql += ' AND a.created_at >= ?'
            params.append(filters['date_from'])

        if 'date_to' in filters:
            sql += ' AND a.created_at <= ?'
            params.append(filters['date_to'])

        # 排序
        if sort_by == 'time':
            sql += ' ORDER BY a.created_at DESC'
        elif sort_by == 'title':
            sql += ' ORDER BY a.title'
        else:  # relevance
            sql += ' ORDER BY a.title'

        sql += ' LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor = self._conn.execute(sql, params)
        return [self._row_to_atom_dict(row) for row in cursor.fetchall()]

    # ========== 父子知识库操作 ==========

    async def register_child_kb(self, parent_id: int, child_id: int,
                                 child_path: str) -> bool:
        """注册子知识库到父知识库"""
        try:
            self._conn.execute('''
                INSERT INTO kb_children (parent_id, child_id, child_path)
                VALUES (?, ?, ?)
            ''', (parent_id, child_id, child_path))

            # 更新父知识库类型
            self._conn.execute(
                'UPDATE knowledge_bases SET kb_type = ? WHERE id = ?',
                ('parent', parent_id)
            )

            # 更新子知识库类型和父 ID
            self._conn.execute(
                'UPDATE knowledge_bases SET kb_type = ?, parent_id = ? WHERE id = ?',
                ('child', parent_id, child_id)
            )

            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]:
        """获取子知识库列表"""
        cursor = self._conn.execute('''
            SELECT kb.*, kbc.child_path
            FROM knowledge_bases kb
            JOIN kb_children kbc ON kb.id = kbc.child_id
            WHERE kbc.parent_id = ?
            ORDER BY kb.name
        ''', (parent_id,))

        return [self._row_to_kb_dict(row) for row in cursor.fetchall()]

    async def get_parent_kb(self, child_id: int) -> Optional[Dict[str, Any]]:
        """获取父知识库信息"""
        cursor = self._conn.execute('''
            SELECT kb.*
            FROM knowledge_bases kb
            JOIN kb_children kbc ON kb.id = kbc.parent_id
            WHERE kbc.child_id = ?
        ''', (child_id,))
        row = cursor.fetchone()
        return self._row_to_kb_dict(row) if row else None

    # ========== 统计操作 ==========

    async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]:
        """获取知识库统计信息"""
        # 总原子数
        cursor = self._conn.execute(
            'SELECT COUNT(*) FROM atoms WHERE kb_id = ?', (kb_id,)
        )
        total_atoms = cursor.fetchone()[0]

        # 按类型统计
        cursor = self._conn.execute('''
            SELECT type, COUNT(*) as count
            FROM atoms
            WHERE kb_id = ?
            GROUP BY type
        ''', (kb_id,))
        types_count = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            'total_atoms': total_atoms,
            'types_count': types_count,
        }

    async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int:
        """获取知识原子数量"""
        if by_type:
            cursor = self._conn.execute(
                'SELECT COUNT(*) FROM atoms WHERE kb_id = ? AND type = ?',
                (kb_id, by_type)
            )
        else:
            cursor = self._conn.execute(
                'SELECT COUNT(*) FROM atoms WHERE kb_id = ?', (kb_id,)
            )
        return cursor.fetchone()[0]

    # ========== 事务操作 ==========

    async def begin_transaction(self) -> None:
        """开始事务，显式声明 BEGIN."""
        self._conn.execute('BEGIN')
        logger.debug("SQLite transaction started")

    async def commit_transaction(self) -> None:
        """提交事务."""
        self._conn.commit()
        logger.debug("SQLite transaction committed")

    async def rollback_transaction(self) -> None:
        """回滚事务."""
        self._conn.rollback()
        logger.debug("SQLite transaction rolled back")

    # ========== 工具方法 ==========

    def _row_to_kb_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为知识库字典"""
        return {
            'id': row['id'],
            'name': row['name'],
            'path': row['path'],
            'description': row['description'],
            'tags': json.loads(row['tags']) if row['tags'] else [],
            'kb_type': row['kb_type'],
            'parent_id': row['parent_id'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'last_accessed_at': row['last_accessed_at'],
            'scope': row['scope'],
        }

    def _row_to_atom_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为知识原子字典"""
        result = {
            'id': row['id'],
            'kb_id': row['kb_id'],
            'path': row['path'],
            'type': row['type'],
            'title': row['title'],
            'description': row['description'],
            'tags': json.loads(row['tags']) if row['tags'] else [],
            'body': row['body'],
            'frontmatter': json.loads(row['frontmatter']) if row['frontmatter'] else {},
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'file_mtime': row['file_mtime'],
        }
        if 'kb_name' in row.keys():
            result['kb_name'] = row['kb_name']
        return result

    # ========== 兼容性方法 ==========

    def migrate_from_registry(self, registry_path: Optional[Path] = None) -> int:
        """从 registry.json 迁移数据

        Args:
            registry_path: registry.json 路径（可选，默认使用全局路径）

        Returns:
            迁移的知识库数量
        """
        registry_path = registry_path or self.global_registry
        if not registry_path.exists():
            return 0

        data = json.loads(registry_path.read_text(encoding='utf-8'))
        kbs = data.get('knowledge_bases', {})
        count = 0

        for name, info in kbs.items():
            # 检查是否已存在
            cursor = self._conn.execute(
                'SELECT id FROM knowledge_bases WHERE name = ?', (name,)
            )
            if cursor.fetchone():
                continue

            # 插入知识库
            self._conn.execute('''
                INSERT INTO knowledge_bases
                (name, path, description, tags, kb_type, parent_id,
                 created_at, updated_at, last_accessed_at, scope)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name,
                info.get('path', ''),
                info.get('description', ''),
                json.dumps(info.get('tags', []), ensure_ascii=False),
                info.get('kb_type', 'standalone'),
                None,  # parent_id 需要后续处理
                info.get('created', self._get_timestamp()),
                info.get('created', self._get_timestamp()),
                info.get('last_accessed'),
                'global',
            ))
            count += 1

        self._conn.commit()
        return count
