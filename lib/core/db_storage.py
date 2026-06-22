"""数据库存储适配器

将 PostgreSQL 操作适配到 StorageInterface 统一 API。
支持 RLS、行级权限、审计日志。
"""

from typing import Dict, List, Optional, Any
import logging

from .storage_interface import StorageInterface
from .config import StorageConfig, StorageType
from .postgres_manager import PostgreSQLManager
from .sqlite_manager import SQLiteManager
from ..utils.sql_validator import SQLValidator, safe_identifier

logger = logging.getLogger(__name__)


class DatabaseStorage(StorageInterface):
    """数据库模式存储适配器

    将 PostgreSQL 操作适配到统一 API。
    支持 RLS、行级权限、审计日志。
    """

    def __init__(self, config: StorageConfig):
        """初始化数据库存储

        Args:
            config: 数据库配置
        """
        self.config = config
        self.db_manager: Optional[Any] = None
        self._current_user_id: Optional[str] = None
        self._current_user_roles: List[str] = []
        self._in_transaction = False

    @property
    def mode(self) -> str:
        return 'db'

    @property
    def supports_rls(self) -> bool:
        return self.config.type == StorageType.POSTGRES

    async def initialize(self) -> None:
        """初始化存储后端"""
        if self.config.type == StorageType.POSTGRES:
            self.db_manager = PostgreSQLManager(self.config)
        else:
            self.db_manager = SQLiteManager(self.config)
        await self.db_manager.initialize()
        logger.info("DatabaseStorage initialized")

    async def close(self) -> None:
        """关闭存储连接"""
        if self.db_manager:
            await self.db_manager.close()

    def set_current_user(self, user_id: str, roles: List[str]) -> None:
        """设置当前用户上下文（用于 RLS）

        Args:
            user_id: 用户 ID
            roles: 用户角色列表
        """
        self._current_user_id = user_id
        self._current_user_roles = roles
        if hasattr(self.db_manager, 'set_rls_context'):
            self.db_manager.set_rls_context(user_id, roles)
        logger.debug(f"RLS context set: user={user_id}, roles={roles}")

    # ==================== 知识库操作 ====================

    async def create_kb(self, kb_data: Dict) -> int:
        """创建知识库"""
        query = """
            INSERT INTO knowledge_bases (name, description, scope, parent_id, owner_id, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            RETURNING id
        """
        params = [
            kb_data.get('name', 'Untitled'),
            kb_data.get('description', ''),
            kb_data.get('scope', 'personal'),
            kb_data.get('parent_id'),
            kb_data.get('owner_id', self._current_user_id),
        ]
        result = await self.db_manager.fetch_one(query, *params)
        return result['id'] if result else -1

    async def get_kb(self, kb_id: int) -> Optional[Dict]:
        """获取知识库"""
        query = "SELECT * FROM knowledge_bases WHERE id = $1"
        return await self.db_manager.fetch_one(query, kb_id)

    async def list_kbs(self, user_id: Optional[str] = None, scope: Optional[str] = None) -> List[Dict]:
        """列出知识库"""
        conditions = []
        params = []

        if user_id:
            # 使用参数化查询（安全）
            conditions.append(f"owner_id = ${len(params) + 1}")
            params.append(user_id)

        if scope:
            # 验证 scope 值（白名单检查）
            allowed_scopes = ['personal', 'team', 'public', 'enterprise']
            if scope not in allowed_scopes:
                logger.warning(f"Invalid scope value: {scope}, using default")
                scope = 'personal'
            conditions.append(f"scope = ${len(params) + 1}")
            params.append(scope)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        # ORDER BY 使用白名单验证（安全）
        order_by = SQLValidator.build_safe_order_by('updated_at', 'DESC')
        query = f"SELECT * FROM knowledge_bases {where_clause} ORDER BY {order_by}"

        return await self.db_manager.fetch_all(query, *params)

    async def update_kb(self, kb_id: int, kb_data: Dict) -> bool:
        """更新知识库"""
        set_clauses = []
        params = []

        # 允许更新的字段白名单
        allowed_fields = ['name', 'description', 'scope', 'parent_id']

        for key in allowed_fields:
            if key in kb_data:
                # 验证字段名（白名单检查）
                if SQLValidator.validate_column_name(key):
                    set_clauses.append(f"{key} = ${len(params) + 1}")
                    params.append(kb_data[key])
                else:
                    logger.warning(f"Invalid field name: {key}, skipping")

        if not set_clauses:
            return False

        set_clauses.append("updated_at = NOW()")
        params.append(kb_id)

        query = f"""
            UPDATE knowledge_bases
            SET {', '.join(set_clauses)}
            WHERE id = ${len(params)}
            RETURNING id
        """
        result = await self.db_manager.fetch_one(query, *params)
        return result is not None

    async def delete_kb(self, kb_id: int) -> bool:
        """删除知识库"""
        query = "DELETE FROM knowledge_bases WHERE id = $1 RETURNING id"
        result = await self.db_manager.fetch_one(query, kb_id)
        return result is not None

    # ==================== 知识原子操作 ====================

    async def create_atom(self, atom_data: Dict) -> int:
        """创建知识原子"""
        query = """
            INSERT INTO atoms (kb_id, title, content, format, tags, links, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            RETURNING id
        """
        params = [
            atom_data.get('kb_id'),
            atom_data.get('title', 'Untitled'),
            atom_data.get('content', ''),
            atom_data.get('format', 'markdown'),
            atom_data.get('tags', []),
            atom_data.get('links', []),
        ]
        result = await self.db_manager.fetch_one(query, *params)
        return result['id'] if result else -1

    async def get_atom(self, atom_id: int) -> Optional[Dict]:
        """获取知识原子"""
        query = "SELECT * FROM atoms WHERE id = $1"
        return await self.db_manager.fetch_one(query, atom_id)

    async def update_atom(self, atom_id: int, atom_data: Dict) -> bool:
        """更新知识原子"""
        set_clauses = []
        params = []

        # 允许更新的字段白名单
        allowed_fields = ['title', 'content', 'format', 'tags', 'links']

        for key in allowed_fields:
            if key in atom_data:
                # 验证字段名（白名单检查）
                if SQLValidator.validate_column_name(key):
                    set_clauses.append(f"{key} = ${len(params) + 1}")
                    params.append(atom_data[key])
                else:
                    logger.warning(f"Invalid field name: {key}, skipping")

        if not set_clauses:
            return False

        set_clauses.append("updated_at = NOW()")
        params.append(atom_id)

        query = f"""
            UPDATE atoms
            SET {', '.join(set_clauses)}
            WHERE id = ${len(params)}
            RETURNING id
        """
        result = await self.db_manager.fetch_one(query, *params)
        return result is not None

    async def delete_atom(self, atom_id: int) -> bool:
        """删除知识原子"""
        query = "DELETE FROM atoms WHERE id = $1 RETURNING id"
        result = await self.db_manager.fetch_one(query, atom_id)
        return result is not None

    async def list_atoms(self, kb_id: int, **kwargs) -> List[Dict]:
        """列出知识库中的原子"""
        # ORDER BY 使用白名单验证（安全）
        order_by = SQLValidator.build_safe_order_by('updated_at', 'DESC')
        query = f"SELECT * FROM atoms WHERE kb_id = $1 ORDER BY {order_by}"
        return await self.db_manager.fetch_all(query, kb_id)

    # ==================== 搜索操作 ====================

    async def search_atoms(self, query: str, **kwargs) -> List[Dict]:
        """搜索知识原子（全文检索）"""
        sql = """
            SELECT * FROM atoms
            WHERE to_tsvector('simple', title || ' ' || content) @@ plainto_tsquery('simple', $1)
            ORDER BY ts_rank(to_tsvector('simple', title || ' ' || content), plainto_tsquery('simple', $1)) DESC
            LIMIT 50
        """
        return await self.db_manager.fetch_all(sql, query)

    # ==================== 事务支持 ====================

    async def begin_transaction(self) -> None:
        """开始事务"""
        self._in_transaction = True
        if hasattr(self.db_manager, 'begin'):
            await self.db_manager.begin()

    async def commit_transaction(self) -> None:
        """提交事务"""
        if hasattr(self.db_manager, 'commit'):
            await self.db_manager.commit()
        self._in_transaction = False

    async def rollback_transaction(self) -> None:
        """回滚事务"""
        if hasattr(self.db_manager, 'rollback'):
            await self.db_manager.rollback()
        self._in_transaction = False

    # ==================== 统计操作 ====================

    async def get_stats(self, kb_id: Optional[int] = None) -> Dict:
        """获取统计信息"""
        if kb_id:
            query = "SELECT COUNT(*) as count FROM atoms WHERE kb_id = $1"
            result = await self.db_manager.fetch_one(query, kb_id)
            return {'kb_id': kb_id, 'atom_count': result['count'] if result else 0}

        query = "SELECT COUNT(*) as count FROM knowledge_bases"
        result = await self.db_manager.fetch_one(query)
        return {
            'kb_count': result['count'] if result else 0,
            'total_atoms': 0,
        }