"""数据库存储适配器

将 PostgreSQL 操作适配到 StorageInterface 统一 API。
支持 RLS、行级权限、审计日志。
"""

import hashlib
import json
import logging
from typing import Dict, List, Optional, Any

from .storage_interface import StorageInterface, UnsupportedOperationError
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
        # 懒加载服务实例
        self._ocr_task_queue = None
        self._ocr_result_store = None
        self._preview_cache_manager = None
        self._office_viewer_service = None

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

    async def set_current_user(self, user_id: str, roles: List[str]) -> None:
        """设置当前用户上下文（用于 RLS）

        Args:
            user_id: 用户 ID
            roles: 用户角色列表
        """
        self._current_user_id = user_id
        self._current_user_roles = roles
        if hasattr(self.db_manager, 'set_rls_context'):
            await self.db_manager.set_rls_context(user_id, roles)
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
        if hasattr(self.db_manager, 'fetch_one'):
            result = await self.db_manager.fetch_one(
                "SELECT COUNT(*) as count FROM knowledge_bases"
            )
            return {
                'kb_count': result['count'] if result else 0,
                'total_atoms': 0,
            }
        return {'kb_count': 0}

    # ==================== 标签操作 ====================

    async def create_tag(self, kb_id: int, tag_data: Dict) -> int:
        """创建标签

        Args:
            kb_id: 知识库 ID
            tag_data: 标签数据（name, color, description 等）

        Returns:
            标签 ID
        """
        name = tag_data.get('name')
        if not name:
            raise ValueError("tag_data must contain 'name'")

        row = await self.db_manager.fetch_one('''
            INSERT INTO tags (kb_id, name, slug, color, description, parent_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        ''',
            kb_id,
            name,
            tag_data.get('slug', name.lower().replace(' ', '-')),
            tag_data.get('color'),
            tag_data.get('description'),
            tag_data.get('parent_id'),
        )
        return row['id'] if row else 0

    async def get_tag(self, tag_id: int) -> Optional[Dict]:
        """获取标签详情

        Args:
            tag_id: 标签 ID

        Returns:
            标签数据字典
        """
        return await self.db_manager.fetch_one(
            'SELECT * FROM tags WHERE id = $1', tag_id
        )

    async def list_tags(self, kb_id: int) -> List[Dict]:
        """列出知识库的所有标签

        Args:
            kb_id: 知识库 ID

        Returns:
            标签列表
        """
        return await self.db_manager.fetch_all(
            'SELECT * FROM tags WHERE kb_id = $1 ORDER BY name', kb_id
        )

    async def update_tag(self, tag_id: int, tag_data: Dict) -> bool:
        """更新标签

        Args:
            tag_id: 标签 ID
            tag_data: 更新的数据

        Returns:
            是否成功
        """
        allowed_fields = {'name', 'slug', 'color', 'description', 'parent_id'}
        updates = []
        params: List[Any] = [tag_id]
        param_idx = 2

        for field in allowed_fields:
            if field in tag_data:
                updates.append(f"{field} = ${param_idx}")
                params.append(tag_data[field])
                param_idx += 1

        if not updates:
            return False

        sql = f"UPDATE tags SET {', '.join(updates)} WHERE id = $1"
        result = await self.db_manager.execute(sql, *params)
        return result == 'UPDATE 1'

    async def delete_tag(self, tag_id: int) -> bool:
        """删除标签（同时删除 atom_tags 关联）

        Args:
            tag_id: 标签 ID

        Returns:
            是否成功
        """
        # atom_tags 通过 ON DELETE CASCADE 自动清理
        result = await self.db_manager.execute(
            'DELETE FROM tags WHERE id = $1', tag_id
        )
        return result == 'DELETE 1'

    async def add_atom_tag(self, atom_id: int, tag_id: int) -> bool:
        """为原子添加标签

        Args:
            atom_id: 原子 ID
            tag_id: 标签 ID

        Returns:
            是否成功
        """
        try:
            await self.db_manager.execute('''
                INSERT INTO atom_tags (atom_id, tag_id)
                VALUES ($1, $2)
                ON CONFLICT (atom_id, tag_id) DO NOTHING
            ''', atom_id, tag_id)
            return True
        except Exception as e:
            logger.error("Failed to add atom tag: %s", e)
            return False

    async def remove_atom_tag(self, atom_id: int, tag_id: int) -> bool:
        """移除原子的标签

        Args:
            atom_id: 原子 ID
            tag_id: 标签 ID

        Returns:
            是否成功
        """
        result = await self.db_manager.execute('''
            DELETE FROM atom_tags
            WHERE atom_id = $1 AND tag_id = $2
        ''', atom_id, tag_id)
        return result == 'DELETE 1'

    async def get_atom_tags(self, atom_id: int) -> List[Dict]:
        """获取原子的所有标签

        Args:
            atom_id: 原子 ID

        Returns:
            标签列表
        """
        return await self.db_manager.fetch_all('''
            SELECT t.* FROM tags t
            JOIN atom_tags at ON t.id = at.tag_id
            WHERE at.atom_id = $1
            ORDER BY t.name
        ''', atom_id)

    # ==================== 资产操作 ====================

    async def upload_asset(self, atom_id: int, asset_data: bytes,
                           filename: str, mime_type: str,
                           user_id: Optional[str] = None) -> Dict:
        """上传资产（图片/文件）到原子

        Args:
            atom_id: 原子 ID
            asset_data: 资产二进制数据
            filename: 文件名
            mime_type: MIME 类型
            user_id: 上传用户 ID

        Returns:
            资产信息字典（含 asset_id）
        """
        size = len(asset_data)
        checksum = hashlib.sha256(asset_data).hexdigest()

        # 小于 1MB 存储为 inline，否则需要外部存储
        INLINE_THRESHOLD = 1024 * 1024  # 1MB
        if size < INLINE_THRESHOLD:
            storage_type = 'inline'
            data = asset_data
            storage_path = None
            storage_provider = None
        else:
            storage_type = 'external'
            data = None
            storage_path = f"assets/{atom_id}/{filename}"
            storage_provider = 'local'

        row = await self.db_manager.fetch_one('''
            INSERT INTO atom_assets
            (atom_id, filename, original_filename, mime_type, size,
             storage_type, data, storage_path, storage_provider,
             checksum, variant_type, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id, atom_id, filename, original_filename, mime_type,
                      size, storage_type, storage_path, checksum,
                      variant_type, created_at
        ''',
            atom_id,
            filename,
            filename,
            mime_type,
            size,
            storage_type,
            data,
            storage_path,
            storage_provider,
            checksum,
            'original',
            user_id or self._current_user_id,
        )

        if not row:
            raise RuntimeError("Failed to insert asset record")

        return dict(row)

    async def get_asset(self, asset_id: int) -> Optional[Dict]:
        """获取资产详情

        Args:
            asset_id: 资产 ID

        Returns:
            资产信息字典
        """
        return await self.db_manager.fetch_one(
            'SELECT * FROM atom_assets WHERE id = $1', asset_id
        )

    async def list_assets(self, atom_id: int, variant_type: Optional[str] = None,
                          page: int = 1, limit: int = 20) -> Dict:
        """列出原子的资产

        Args:
            atom_id: 原子 ID
            variant_type: 变体类型（original/thumbnail 等）
            page: 页码
            limit: 每页数量

        Returns:
            资产列表字典（含 items, total, page, limit）
        """
        # 构建查询条件
        if variant_type:
            count_row = await self.db_manager.fetch_one('''
                SELECT COUNT(*) as total FROM atom_assets
                WHERE atom_id = $1 AND variant_type = $2
            ''', atom_id, variant_type)

            items = await self.db_manager.fetch_all('''
                SELECT id, atom_id, filename, original_filename, mime_type,
                       size, storage_type, storage_path, checksum,
                       width, height, variant_type, variant_of_id,
                       created_at, created_by
                FROM atom_assets
                WHERE atom_id = $1 AND variant_type = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            ''', atom_id, variant_type, limit, (page - 1) * limit)
        else:
            count_row = await self.db_manager.fetch_one('''
                SELECT COUNT(*) as total FROM atom_assets
                WHERE atom_id = $1
            ''', atom_id)

            items = await self.db_manager.fetch_all('''
                SELECT id, atom_id, filename, original_filename, mime_type,
                       size, storage_type, storage_path, checksum,
                       width, height, variant_type, variant_of_id,
                       created_at, created_by
                FROM atom_assets
                WHERE atom_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            ''', atom_id, limit, (page - 1) * limit)

        total = count_row['total'] if count_row else 0
        return {
            'items': [dict(item) for item in items],
            'total': total,
            'page': page,
            'limit': limit,
        }

    async def delete_asset(self, asset_id: int, user_id: Optional[str] = None) -> bool:
        """删除资产

        Args:
            asset_id: 资产 ID
            user_id: 操作用户 ID

        Returns:
            是否成功
        """
        result = await self.db_manager.execute(
            'DELETE FROM atom_assets WHERE id = $1', asset_id
        )
        return result == 'DELETE 1'

    # ==================== 快照操作 ====================

    async def create_snapshot(self, kb_id: int, name: str,
                              description: str = '',
                              snapshot_type: str = 'manual',
                              user_id: Optional[str] = None) -> int:
        """创建知识库快照

        Args:
            kb_id: 知识库 ID
            name: 快照名称
            description: 快照描述
            snapshot_type: 快照类型（manual/auto）
            user_id: 创建用户 ID

        Returns:
            快照 ID
        """
        # 先获取当前原子的快照数据
        atoms = await self.db_manager.fetch_all('''
            SELECT id, title, content, metadata
            FROM atoms
            WHERE kb_id = $1 AND status = 'active'
            ORDER BY title
        ''', kb_id)

        atom_count = len(atoms)

        # 创建快照记录
        snapshot_row = await self.db_manager.fetch_one('''
            INSERT INTO snapshots (kb_id, name, description, snapshot_type,
                                   atom_count, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        ''',
            kb_id,
            name,
            description,
            snapshot_type,
            atom_count,
            user_id or self._current_user_id,
        )

        if not snapshot_row:
            raise RuntimeError("Failed to create snapshot record")

        snapshot_id = snapshot_row['id']

        # 创建快照条目
        if atoms:
            version_number = 1
            for atom in atoms:
                metadata = atom.get('metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}

                await self.db_manager.execute('''
                    INSERT INTO snapshot_items
                    (snapshot_id, atom_id, version_number, title,
                     content, metadata, change_type)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''',
                    snapshot_id,
                    atom['id'],
                    version_number,
                    atom.get('title', ''),
                    atom.get('content', ''),
                    json.dumps(metadata),
                    'create',
                )
                version_number += 1

        return snapshot_id

    async def get_snapshot(self, snapshot_id: int) -> Optional[Dict]:
        """获取快照详情

        Args:
            snapshot_id: 快照 ID

        Returns:
            快照信息字典
        """
        snapshot = await self.db_manager.fetch_one(
            'SELECT * FROM snapshots WHERE id = $1', snapshot_id
        )
        if not snapshot:
            return None

        result = dict(snapshot)
        # 附加快照条目
        items = await self.db_manager.fetch_all('''
            SELECT * FROM snapshot_items
            WHERE snapshot_id = $1
            ORDER BY version_number
        ''', snapshot_id)
        result['items'] = [dict(item) for item in items]
        return result

    async def list_snapshots(self, kb_id: int, limit: int = 20,
                             offset: int = 0) -> List[Dict]:
        """列出知识库的快照

        Args:
            kb_id: 知识库 ID
            limit: 每页数量
            offset: 偏移量

        Returns:
            快照列表
        """
        rows = await self.db_manager.fetch_all('''
            SELECT * FROM snapshots
            WHERE kb_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        ''', kb_id, limit, offset)
        return [dict(row) for row in rows]

    async def restore_snapshot(self, snapshot_id: int,
                               user_id: Optional[str] = None) -> bool:
        """从快照恢复知识库

        Args:
            snapshot_id: 快照 ID
            user_id: 操作用户 ID

        Returns:
            是否成功
        """
        snapshot = await self.db_manager.fetch_one(
            'SELECT * FROM snapshots WHERE id = $1', snapshot_id
        )
        if not snapshot:
            return False

        kb_id = snapshot['kb_id']

        items = await self.db_manager.fetch_all('''
            SELECT * FROM snapshot_items
            WHERE snapshot_id = $1
        ''', snapshot_id)

        # 在事务中恢复
        await self.begin_transaction()
        try:
            # 软删除当前活跃原子
            await self.db_manager.execute(
                "UPDATE atoms SET status = 'archived' WHERE kb_id = $1 AND status = 'active'",
                kb_id,
            )

            # 恢复快照中的原子
            for item in items:
                item_dict = dict(item)
                metadata = item_dict.get('metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}

                change_type = item_dict.get('change_type', 'update')
                if change_type == 'delete':
                    # 快照中标记为删除的原子不恢复
                    continue

                # 检查原子是否仍存在
                existing = await self.db_manager.fetch_one(
                    'SELECT id FROM atoms WHERE id = $1', item_dict['atom_id']
                )

                if existing:
                    await self.db_manager.execute('''
                        UPDATE atoms
                        SET title = $1, content = $2, metadata = $3,
                            status = 'active'
                        WHERE id = $4
                    ''',
                        item_dict.get('title', ''),
                        item_dict.get('content', ''),
                        json.dumps(metadata),
                        item_dict['atom_id'],
                    )
                else:
                    await self.db_manager.execute('''
                        INSERT INTO atoms (id, kb_id, title, content,
                                           metadata, type, status)
                        VALUES ($1, $2, $3, $4, $5, 'fact', 'active')
                    ''',
                        item_dict['atom_id'],
                        kb_id,
                        item_dict.get('title', ''),
                        item_dict.get('content', ''),
                        json.dumps(metadata),
                    )

            await self.commit_transaction()
            return True
        except Exception as e:
            await self.rollback_transaction()
            logger.error("Failed to restore snapshot %s: %s", snapshot_id, e)
            return False

    async def delete_snapshot(self, snapshot_id: int) -> bool:
        """删除快照

        Args:
            snapshot_id: 快照 ID

        Returns:
            是否成功
        """
        # snapshot_items 通过 ON DELETE CASCADE 自动清理
        result = await self.db_manager.execute(
            'DELETE FROM snapshots WHERE id = $1', snapshot_id
        )
        return result == 'DELETE 1'

    # ==================== OCR 操作 ====================

    def _get_ocr_task_queue(self):
        """懒加载 OCRTaskQueue"""
        if self._ocr_task_queue is None:
            from ..ocr.task_queue import OCRTaskQueue
            self._ocr_task_queue = OCRTaskQueue(db=self.db_manager)
        return self._ocr_task_queue

    def _get_ocr_result_store(self):
        """懒加载 OCRResultStore"""
        if self._ocr_result_store is None:
            from ..ocr.result_store import OCRResultStore
            self._ocr_result_store = OCRResultStore(db=self.db_manager)
        return self._ocr_result_store

    async def submit_ocr_task(self, asset_id: int, image_data: bytes,
                              user_id: Optional[str] = None,
                              language: Optional[str] = None) -> Dict:
        """提交 OCR 识别任务

        委托给 OCRTaskQueue 处理。

        Args:
            asset_id: 资产 ID
            image_data: 图片二进制数据
            user_id: 用户 ID
            language: OCR 语言（默认 chi_sim+eng）

        Returns:
            任务信息字典（含 task_id, status）
        """
        queue = self._get_ocr_task_queue()
        result = await queue.submit_task(
            asset_id=asset_id,
            image_data=image_data,
            user_id=user_id,
            language=language,
        )
        return {
            'task_id': result.task_id,
            'asset_id': result.asset_id,
            'status': result.status,
            'error_message': result.error_message,
        }

    async def get_ocr_result(self, task_id: int) -> Optional[Dict]:
        """获取 OCR 识别结果

        委托给 OCRResultStore 处理。

        Args:
            task_id: OCR 任务 ID

        Returns:
            OCR 结果字典
        """
        store = self._get_ocr_result_store()
        result = await store.get_result(task_id)
        if result is None:
            # 回退到查询任务状态
            queue = self._get_ocr_task_queue()
            task_result = await queue.get_task_status(str(task_id))
            if task_result is None:
                return None
            return {
                'task_id': task_result.task_id,
                'asset_id': task_result.asset_id,
                'status': task_result.status,
                'result_text': task_result.result_text,
                'result_json': task_result.result_json,
                'error_message': task_result.error_message,
            }
        return result

    async def get_ocr_results_by_asset(self, asset_id: int) -> List[Dict]:
        """获取资产的所有 OCR 结果

        委托给 OCRResultStore 处理。

        Args:
            asset_id: 资产 ID

        Returns:
            OCR 结果列表
        """
        store = self._get_ocr_result_store()
        return await store.get_results_by_asset(asset_id)

    # ==================== 预览操作 ====================

    def _get_preview_cache_manager(self):
        """懒加载 PreviewCacheManager"""
        if self._preview_cache_manager is None:
            from ..preview.cache_manager import PreviewCacheManager
            self._preview_cache_manager = PreviewCacheManager(
                db=self.db_manager
            )
        return self._preview_cache_manager

    def _get_office_viewer_service(self):
        """懒加载 OfficeViewerService"""
        if self._office_viewer_service is None:
            from ..preview.office_viewer import OfficeViewerService
            self._office_viewer_service = OfficeViewerService()
        return self._office_viewer_service

    async def get_preview_url(self, atom_id: int, format: str = 'html',
                              source_mime_type: Optional[str] = None) -> Dict:
        """获取原子内容的预览 URL

        使用 PreviewCacheManager + OfficeViewerService。

        Args:
            atom_id: 原子 ID
            format: 预览格式（html/pdf）
            source_mime_type: 源文件 MIME 类型

        Returns:
            预览信息字典（含 url, format, is_available）
        """
        # 先检查缓存
        cache_mgr = self._get_preview_cache_manager()
        cache_entry = await cache_mgr.get(atom_id, format)
        if cache_entry and cache_entry.cache_path:
            return {
                'url': cache_entry.cache_path,
                'format': format,
                'is_available': True,
                'source_mime_type': source_mime_type,
            }

        # 获取原子信息
        atom = await self.get_atom(atom_id)
        if not atom:
            return {
                'url': None,
                'format': format,
                'is_available': False,
                'error': f'Atom {atom_id} not found',
            }

        # 如果有附件，使用 OfficeViewerService 生成预览
        assets_result = await self.list_assets(atom_id, limit=1)
        if assets_result.get('items'):
            asset = assets_result['items'][0]
            mime = asset.get('mime_type', source_mime_type)

            viewer = self._get_office_viewer_service()
            # 构造文件 URL（实际部署中应为可访问的文件 URL）
            file_url = f"/api/assets/{asset['id']}/download"
            preview_url = viewer.get_preview_url(file_url, mime)

            return {
                'url': preview_url.url,
                'format': preview_url.format or format,
                'is_available': preview_url.is_available,
                'source_mime_type': mime,
                'error': str(preview_url.error) if preview_url.error else None,
            }

        # 无附件时，纯文本内容直接返回
        return {
            'url': f"/api/atoms/{atom_id}/content",
            'format': format,
            'is_available': True,
            'source_mime_type': 'text/markdown',
        }

    async def get_preview_cache(self, atom_id: int,
                                format: str = 'html') -> Optional[Dict]:
        """获取预览缓存

        Args:
            atom_id: 原子 ID
            format: 预览格式

        Returns:
            缓存条目字典，不存在返回 None
        """
        cache_mgr = self._get_preview_cache_manager()
        entry = await cache_mgr.get(atom_id, format)
        if entry is None:
            return None
        return {
            'cache_key': entry.cache_key,
            'cache_path': entry.cache_path,
            'atom_id': entry.atom_id,
            'format': entry.format,
            'source_mime_type': entry.source_mime_type,
            'file_size': entry.file_size,
            'created_at': entry.created_at.isoformat() if entry.created_at else None,
            'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
        }

    # ==================== 审计操作 ====================

    async def log_audit(self, event_type: str, user_id: Optional[str] = None,
                        resource: Optional[str] = None,
                        action: Optional[str] = None,
                        details: Optional[Dict] = None) -> None:
        """记录审计事件

        写入 audit_logs 表（预留）。

        Args:
            event_type: 事件类型
            user_id: 用户 ID
            resource: 资源标识
            action: 操作类型
            details: 详细信息
        """
        try:
            # 计算链式哈希（audit_logs 使用 record_hash + prev_hash）
            prev_row = await self.db_manager.fetch_one(
                'SELECT record_hash FROM audit_logs ORDER BY id DESC LIMIT 1'
            )
            prev_hash = prev_row['record_hash'] if prev_row else '0'

            # 构造哈希内容
            hash_content = json.dumps({
                'event_type': event_type,
                'user_id': user_id,
                'resource': resource,
                'action': action,
                'details': details,
                'prev_hash': prev_hash,
            }, sort_keys=True, default=str)
            record_hash = hashlib.sha256(hash_content.encode()).hexdigest()

            await self.db_manager.execute('''
                INSERT INTO audit_logs
                (user_id, action, resource_type, resource_id, details,
                 record_hash, prev_hash)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''',
                user_id or self._current_user_id,
                action or event_type,
                resource.split(':')[0] if resource and ':' in resource else None,
                resource.split(':')[1] if resource and ':' in resource else resource,
                json.dumps(details) if details else None,
                record_hash,
                prev_hash,
            )
        except Exception as e:
            # 审计日志不应阻塞主流程
            logger.error("Failed to log audit event: %s", e)

    async def query_audit(self, event_type: Optional[str] = None,
                          user_id: Optional[str] = None,
                          start_time: Optional[str] = None,
                          end_time: Optional[str] = None,
                          limit: int = 100) -> List[Dict]:
        """查询审计日志

        Args:
            event_type: 事件类型过滤
            user_id: 用户 ID 过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大条数

        Returns:
            审计日志列表
        """
        conditions = []
        params: List[Any] = []
        param_idx = 1

        if event_type:
            conditions.append(f"action = ${param_idx}")
            params.append(event_type)
            param_idx += 1

        if user_id:
            conditions.append(f"user_id = ${param_idx}")
            params.append(user_id)
            param_idx += 1

        if start_time:
            conditions.append(f"created_at >= ${param_idx}")
            params.append(start_time)
            param_idx += 1

        if end_time:
            conditions.append(f"created_at <= ${param_idx}")
            params.append(end_time)
            param_idx += 1

        where_clause = ''
        if conditions:
            where_clause = 'WHERE ' + ' AND '.join(conditions)

        sql = f'''
            SELECT * FROM audit_logs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx}
        '''
        params.append(limit)

        try:
            rows = await self.db_manager.fetch_all(sql, *params)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to query audit logs: %s", e)
            return []
