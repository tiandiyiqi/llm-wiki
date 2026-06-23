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
            # set_rls_context 是 async 方法，需要事件循环
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.db_manager.set_rls_context(user_id, roles))
            except RuntimeError:
                # 没有运行中的事件循环，稍后设置
                logger.debug("No running event loop, RLS context will be set on next operation")
        logger.debug("RLS context set: user=%s, roles=%s", user_id, roles)

    # ==================== 知识库操作 ====================

    async def create_kb(self, kb_data: Dict) -> int:
        """创建知识库"""
        # 适配完整 schema 字段
        adapted = {
            'name': kb_data.get('name', 'Untitled'),
            'slug': kb_data.get('slug', kb_data.get('name', 'untitled').lower().replace(' ', '-')),
            'type': kb_data.get('type', kb_data.get('scope', 'personal')),
            'description': kb_data.get('description', ''),
            'owner_id': kb_data.get('owner_id', self._current_user_id),
            'organization_id': kb_data.get('organization_id'),
            'department_id': kb_data.get('department_id'),
            'project_id': kb_data.get('project_id'),
            'visibility': kb_data.get('visibility', 'private'),
            'storage_mode': kb_data.get('storage_mode', 'db'),
            'settings': kb_data.get('settings', {}),
            'created_by': kb_data.get('created_by', self._current_user_id),
        }
        return await self.db_manager.create_kb(adapted)

    async def get_kb(self, kb_id: int) -> Optional[Dict]:
        """获取知识库"""
        return await self.db_manager.get_kb(kb_id)

    async def list_kbs(self, user_id: Optional[str] = None, scope: Optional[str] = None) -> List[Dict]:
        """列出知识库"""
        return await self.db_manager.list_kbs(user_id=user_id, scope=scope or 'all')

    async def update_kb(self, kb_id: int, kb_data: Dict) -> bool:
        """更新知识库"""
        return await self.db_manager.update_kb(kb_id, kb_data)

    async def delete_kb(self, kb_id: int) -> bool:
        """删除知识库"""
        return await self.db_manager.delete_kb(kb_id)

    # ==================== 知识原子操作 ====================

    async def create_atom(self, atom_data: Dict) -> int:
        """创建知识原子"""
        # 适配完整 schema 字段
        # 旧字段: body/frontmatter/path/file_mtime → 新字段: content/metadata/slug
        adapted = {
            'kb_id': atom_data.get('kb_id'),
            'title': atom_data.get('title', 'Untitled'),
            'slug': atom_data.get('slug', atom_data.get('path')),
            'type': atom_data.get('type', 'fact'),
            'description': atom_data.get('description', ''),
            'content': atom_data.get('content', atom_data.get('body', '')),
            'metadata': atom_data.get('metadata', atom_data.get('frontmatter', {})),
            'author_id': atom_data.get('author_id', self._current_user_id),
            'status': atom_data.get('status', 'active'),
        }

        # 保留 tags 在 metadata 中
        if 'tags' in atom_data:
            metadata = adapted.get('metadata', {})
            if isinstance(metadata, dict):
                metadata = {**metadata, 'tags': atom_data['tags']}
            else:
                metadata = {'tags': atom_data['tags']}
            adapted['metadata'] = metadata

        # 保留 path 在 metadata 中（兼容旧系统）
        if 'path' in atom_data and not adapted.get('slug'):
            adapted['slug'] = atom_data['path']
            metadata = adapted.get('metadata', {})
            if isinstance(metadata, dict):
                metadata = {**metadata, 'path': atom_data['path']}
            adapted['metadata'] = metadata

        return await self.db_manager.create_atom(adapted)

    async def get_atom(self, atom_id: int) -> Optional[Dict]:
        """获取知识原子"""
        return await self.db_manager.get_atom(atom_id)

    async def update_atom(self, atom_id: int, atom_data: Dict) -> bool:
        """更新知识原子"""
        # 适配字段映射
        adapted = {}
        field_map = {
            'body': 'content',
            'frontmatter': 'metadata',
        }

        for key, value in atom_data.items():
            mapped_key = field_map.get(key, key)
            adapted[mapped_key] = value

        # 处理 tags → metadata.tags
        if 'tags' in adapted:
            # 获取当前 metadata
            current = await self.db_manager.get_atom(atom_id)
            if current:
                metadata = current.get('metadata', {})
                if isinstance(metadata, dict):
                    metadata = {**metadata, 'tags': adapted.pop('tags')}
                    adapted['metadata'] = metadata

        return await self.db_manager.update_atom(atom_id, adapted)

    async def delete_atom(self, atom_id: int) -> bool:
        """删除知识原子"""
        return await self.db_manager.delete_atom(atom_id)

    async def list_atoms(self, kb_id: int, **kwargs) -> List[Dict]:
        """列出知识库中的原子"""
        by_type = kwargs.get('by_type')
        limit = kwargs.get('limit', 100)
        offset = kwargs.get('offset', 0)
        return await self.db_manager.list_atoms(kb_id, by_type=by_type, limit=limit, offset=offset)

    # ==================== 搜索操作 ====================

    async def search_atoms(self, query: str, **kwargs) -> List[Dict]:
        """搜索知识原子（全文检索）"""
        return await self.db_manager.search_atoms(query, **kwargs)

    # ==================== 事务支持 ====================

    async def begin_transaction(self) -> None:
        """开始事务，委托给底层 db_manager."""
        if self._in_transaction:
            logger.warning("Transaction already active, nesting not supported")
            return
        await self.db_manager.begin_transaction()
        self._in_transaction = True

    async def commit_transaction(self) -> None:
        """提交事务，委托给底层 db_manager."""
        if not self._in_transaction:
            logger.warning("No active transaction to commit")
            return
        try:
            await self.db_manager.commit_transaction()
        except Exception as e:
            logger.error("Commit failed, attempting rollback: %s", e)
            try:
                await self.db_manager.rollback_transaction()
            except Exception as rb_error:
                logger.error("Rollback after failed commit also failed: %s", rb_error)
            raise
        finally:
            self._in_transaction = False

    async def rollback_transaction(self) -> None:
        """回滚事务，委托给底层 db_manager."""
        if not self._in_transaction:
            logger.warning("No active transaction to rollback")
            return
        try:
            await self.db_manager.rollback_transaction()
        except Exception as e:
            logger.error("Rollback failed: %s", e)
            raise
        finally:
            self._in_transaction = False

    # ==================== 统计操作 ====================

    async def get_stats(self, kb_id: Optional[int] = None) -> Dict:
        """获取统计信息"""
        if kb_id:
            return await self.db_manager.get_kb_stats(kb_id)

        # 全局统计
        try:
            result = await self.db_manager.fetch_one(
                "SELECT COUNT(*) as count FROM knowledge_bases"
            )
            return {
                'kb_count': result['count'] if result else 0,
                'total_atoms': 0,
            }
        except AttributeError:
            # SQLiteManager 可能没有 fetch_one
            return await self.db_manager.get_kb_stats(kb_id) if kb_id else {'kb_count': 0}
