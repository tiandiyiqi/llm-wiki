"""存储接口抽象层

定义统一的存储接口，支持 file_mode 和 db_mode 透明切换。

设计决策（PLAN-004 Phase 2）：
- 策略A：全扩展接口，file_mode 不支持的方法抛出 NotImplementedError
- OCR/Preview：file_mode 不支持（纯 db_mode 功能）
- 标签：独立表 (tags/atom_tags) + 兼容 JSONB (metadata->tags)
- Snapshot：仅 db_mode 支持（PostgreSQL 表）
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pathlib import Path


class UnsupportedOperationError(NotImplementedError):
    """当前存储模式不支持的操作

    file_mode 下调用仅 db_mode 支持的方法时抛出。
    """

    def __init__(self, operation: str, mode: str = 'file'):
        self.operation = operation
        self.mode = mode
        super().__init__(
            f"Operation '{operation}' is not supported in {mode}_mode"
        )


class StorageInterface(ABC):
    """存储接口抽象基类

    统一 file_mode 和 db_mode 的 API 接口。
    实现类：
    - FileSystemStorage: 文件系统模式（保留 Skill 特性）
    - DatabaseStorage: 数据库模式（PostgreSQL + RLS）

    方法分类：
    - 基础操作：KB/Atom CRUD（两种模式均支持）
    - 搜索操作：全文搜索（两种模式均支持，实现不同）
    - 标签操作：独立标签表 + JSONB 兼容（file_mode 降级为 metadata 操作）
    - 资产操作：图片/文件管理（file_mode 不支持）
    - 快照操作：版本管理（file_mode 不支持）
    - OCR 操作：文档识别（file_mode 不支持）
    - 预览操作：在线预览（file_mode 不支持）
    - 审计操作：审计日志（两种模式均支持，存储不同）
    """

    @property
    @abstractmethod
    def mode(self) -> str:
        """存储模式：'file' 或 'db'"""
        pass

    @property
    @abstractmethod
    def supports_rls(self) -> bool:
        """是否支持行级安全策略 (RLS)"""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """初始化存储后端"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭存储连接"""
        pass

    # ==================== 知识库操作 ====================

    @abstractmethod
    async def create_kb(self, kb_data: Dict) -> int:
        """创建知识库

        Args:
            kb_data: 知识库数据，包含 name, description, scope 等

        Returns:
            知识库 ID
        """
        pass

    @abstractmethod
    async def get_kb(self, kb_id: int) -> Optional[Dict]:
        """获取知识库详情

        Args:
            kb_id: 知识库 ID

        Returns:
            知识库数据字典，不存在返回 None
        """
        pass

    @abstractmethod
    async def list_kbs(self, user_id: Optional[str] = None, scope: Optional[str] = None) -> List[Dict]:
        """列出知识库

        Args:
            user_id: 用户 ID（可选，用于权限过滤）
            scope: 知识库范围（personal/department/project/company）

        Returns:
            知识库列表
        """
        pass

    @abstractmethod
    async def update_kb(self, kb_id: int, kb_data: Dict) -> bool:
        """更新知识库

        Args:
            kb_id: 知识库 ID
            kb_data: 更新的数据

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def delete_kb(self, kb_id: int) -> bool:
        """删除知识库

        Args:
            kb_id: 知识库 ID

        Returns:
            是否成功
        """
        pass

    # ==================== 知识原子操作 ====================

    @abstractmethod
    async def create_atom(self, atom_data: Dict) -> int:
        """创建知识原子

        Args:
            atom_data: 原子数据，包含 kb_id, title, content 等

        Returns:
            原子 ID
        """
        pass

    @abstractmethod
    async def get_atom(self, atom_id: int) -> Optional[Dict]:
        """获取知识原子

        Args:
            atom_id: 原子 ID

        Returns:
            原子数据字典
        """
        pass

    @abstractmethod
    async def update_atom(self, atom_id: int, atom_data: Dict) -> bool:
        """更新知识原子

        Args:
            atom_id: 原子 ID
            atom_data: 更新的数据

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def delete_atom(self, atom_id: int) -> bool:
        """删除知识原子

        Args:
            atom_id: 原子 ID

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def list_atoms(self, kb_id: int, **kwargs) -> List[Dict]:
        """列出知识库中的原子

        Args:
            kb_id: 知识库 ID
            **kwargs: 其他过滤参数

        Returns:
            原子列表
        """
        pass

    # ==================== 搜索操作 ====================

    @abstractmethod
    async def search_atoms(self, query: str, **kwargs) -> List[Dict]:
        """搜索知识原子

        Args:
            query: 搜索关键词
            **kwargs: 其他搜索参数

        Returns:
            匹配的原子列表
        """
        pass

    # ==================== 标签操作 ====================

    async def create_tag(self, kb_id: int, tag_data: Dict) -> int:
        """创建标签

        db_mode: 写入 tags 表
        file_mode: 写入知识库 metadata

        Args:
            kb_id: 知识库 ID
            tag_data: 标签数据（name, color, description 等）

        Returns:
            标签 ID
        """
        raise UnsupportedOperationError('create_tag', self.mode)

    async def get_tag(self, tag_id: int) -> Optional[Dict]:
        """获取标签详情

        Args:
            tag_id: 标签 ID

        Returns:
            标签数据字典
        """
        raise UnsupportedOperationError('get_tag', self.mode)

    async def list_tags(self, kb_id: int) -> List[Dict]:
        """列出知识库的所有标签

        db_mode: 查询 tags 表
        file_mode: 从所有原子的 metadata.tags 聚合

        Args:
            kb_id: 知识库 ID

        Returns:
            标签列表
        """
        # file_mode 默认实现：从 atoms metadata 中聚合标签
        tags_set = set()
        atoms = await self.list_atoms(kb_id)
        for atom in atoms:
            for tag in atom.get('tags', []):
                tags_set.add(tag)
        return [{'name': tag, 'kb_id': kb_id} for tag in sorted(tags_set)]

    async def update_tag(self, tag_id: int, tag_data: Dict) -> bool:
        """更新标签

        Args:
            tag_id: 标签 ID
            tag_data: 更新的数据

        Returns:
            是否成功
        """
        raise UnsupportedOperationError('update_tag', self.mode)

    async def delete_tag(self, tag_id: int) -> bool:
        """删除标签

        db_mode: 从 tags 表删除，同时删除 atom_tags 关联
        file_mode: 从所有原子的 metadata.tags 移除

        Args:
            tag_id: 标签 ID

        Returns:
            是否成功
        """
        raise UnsupportedOperationError('delete_tag', self.mode)

    async def add_atom_tag(self, atom_id: int, tag_id: int) -> bool:
        """为原子添加标签

        db_mode: 写入 atom_tags 关联表
        file_mode: 更新原子 metadata.tags

        Args:
            atom_id: 原子 ID
            tag_id: 标签 ID（db_mode）或标签名称（file_mode）

        Returns:
            是否成功
        """
        raise UnsupportedOperationError('add_atom_tag', self.mode)

    async def remove_atom_tag(self, atom_id: int, tag_id: int) -> bool:
        """移除原子的标签

        db_mode: 从 atom_tags 关联表删除
        file_mode: 从原子 metadata.tags 移除

        Args:
            atom_id: 原子 ID
            tag_id: 标签 ID（db_mode）或标签名称（file_mode）

        Returns:
            是否成功
        """
        raise UnsupportedOperationError('remove_atom_tag', self.mode)

    async def get_atom_tags(self, atom_id: int) -> List[Dict]:
        """获取原子的所有标签

        db_mode: 查询 atom_tags + tags 表
        file_mode: 从原子 metadata.tags 读取

        Args:
            atom_id: 原子 ID

        Returns:
            标签列表
        """
        # 两种模式都有默认实现
        atom = await self.get_atom(atom_id)
        if not atom:
            return []
        tags = atom.get('tags', [])
        return [{'name': tag} for tag in tags]

    # ==================== 资产操作（仅 db_mode）====================

    async def upload_asset(self, atom_id: int, asset_data: bytes,
                           filename: str, mime_type: str,
                           user_id: Optional[str] = None) -> Dict:
        """上传资产（图片/文件）到原子

        仅 db_mode 支持。使用 atom_assets 表存储。

        Args:
            atom_id: 原子 ID
            asset_data: 资产二进制数据
            filename: 文件名
            mime_type: MIME 类型
            user_id: 上传用户 ID

        Returns:
            资产信息字典（含 asset_id）

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('upload_asset', self.mode)

    async def get_asset(self, asset_id: int) -> Optional[Dict]:
        """获取资产详情

        仅 db_mode 支持。

        Args:
            asset_id: 资产 ID

        Returns:
            资产信息字典

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('get_asset', self.mode)

    async def list_assets(self, atom_id: int, variant_type: Optional[str] = None,
                          page: int = 1, limit: int = 20) -> Dict:
        """列出原子的资产

        仅 db_mode 支持。

        Args:
            atom_id: 原子 ID
            variant_type: 变体类型（original/thumbnail 等）
            page: 页码
            limit: 每页数量

        Returns:
            资产列表字典（含 items, total, page, limit）

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('list_assets', self.mode)

    async def delete_asset(self, asset_id: int, user_id: Optional[str] = None) -> bool:
        """删除资产

        仅 db_mode 支持。

        Args:
            asset_id: 资产 ID
            user_id: 操作用户 ID

        Returns:
            是否成功

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('delete_asset', self.mode)

    # ==================== 快照操作（仅 db_mode）====================

    async def create_snapshot(self, kb_id: int, name: str,
                              description: str = '',
                              snapshot_type: str = 'manual',
                              user_id: Optional[str] = None) -> int:
        """创建知识库快照

        仅 db_mode 支持。使用 snapshots + snapshot_items 表。

        Args:
            kb_id: 知识库 ID
            name: 快照名称
            description: 快照描述
            snapshot_type: 快照类型（manual/auto）
            user_id: 创建用户 ID

        Returns:
            快照 ID

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('create_snapshot', self.mode)

    async def get_snapshot(self, snapshot_id: int) -> Optional[Dict]:
        """获取快照详情

        仅 db_mode 支持。

        Args:
            snapshot_id: 快照 ID

        Returns:
            快照信息字典

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('get_snapshot', self.mode)

    async def list_snapshots(self, kb_id: int, limit: int = 20,
                             offset: int = 0) -> List[Dict]:
        """列出知识库的快照

        仅 db_mode 支持。

        Args:
            kb_id: 知识库 ID
            limit: 每页数量
            offset: 偏移量

        Returns:
            快照列表

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('list_snapshots', self.mode)

    async def restore_snapshot(self, snapshot_id: int,
                               user_id: Optional[str] = None) -> bool:
        """从快照恢复知识库

        仅 db_mode 支持。

        Args:
            snapshot_id: 快照 ID
            user_id: 操作用户 ID

        Returns:
            是否成功

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('restore_snapshot', self.mode)

    async def delete_snapshot(self, snapshot_id: int) -> bool:
        """删除快照

        仅 db_mode 支持。

        Args:
            snapshot_id: 快照 ID

        Returns:
            是否成功

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('delete_snapshot', self.mode)

    # ==================== OCR 操作（仅 db_mode）====================

    async def submit_ocr_task(self, asset_id: int, image_data: bytes,
                              user_id: Optional[str] = None,
                              language: Optional[str] = None) -> Dict:
        """提交 OCR 识别任务

        仅 db_mode 支持。使用 ocr_tasks 表 + PaddleOCRService。

        Args:
            asset_id: 资产 ID
            image_data: 图片二进制数据
            user_id: 用户 ID
            language: OCR 语言（默认 chi_sim+eng）

        Returns:
            任务信息字典（含 task_id, status）

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('submit_ocr_task', self.mode)

    async def get_ocr_result(self, task_id: int) -> Optional[Dict]:
        """获取 OCR 识别结果

        仅 db_mode 支持。

        Args:
            task_id: OCR 任务 ID

        Returns:
            OCR 结果字典

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('get_ocr_result', self.mode)

    async def get_ocr_results_by_asset(self, asset_id: int) -> List[Dict]:
        """获取资产的所有 OCR 结果

        仅 db_mode 支持。

        Args:
            asset_id: 资产 ID

        Returns:
            OCR 结果列表

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('get_ocr_results_by_asset', self.mode)

    # ==================== 预览操作（仅 db_mode）====================

    async def get_preview_url(self, atom_id: int, format: str = 'html',
                              source_mime_type: Optional[str] = None) -> Dict:
        """获取原子内容的预览 URL

        仅 db_mode 支持。使用 PreviewCacheManager + OfficeViewerService。

        Args:
            atom_id: 原子 ID
            format: 预览格式（html/pdf）
            source_mime_type: 源文件 MIME 类型

        Returns:
            预览信息字典（含 url, format, is_available）

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('get_preview_url', self.mode)

    async def get_preview_cache(self, atom_id: int,
                                format: str = 'html') -> Optional[Dict]:
        """获取预览缓存

        仅 db_mode 支持。

        Args:
            atom_id: 原子 ID
            format: 预览格式

        Returns:
            缓存条目字典，不存在返回 None

        Raises:
            UnsupportedOperationError: file_mode 不支持
        """
        raise UnsupportedOperationError('get_preview_cache', self.mode)

    # ==================== 审计操作 ====================

    async def log_audit(self, event_type: str, user_id: Optional[str] = None,
                        resource: Optional[str] = None,
                        action: Optional[str] = None,
                        details: Optional[Dict] = None) -> None:
        """记录审计事件

        两种模式均支持：
        - db_mode: 写入 audit_logs 表（预留）
        - file_mode: 写入 JSONL 文件

        Args:
            event_type: 事件类型
            user_id: 用户 ID
            resource: 资源标识
            action: 操作类型
            details: 详细信息
        """
        # 默认空实现，子类可选覆盖
        pass

    async def query_audit(self, event_type: Optional[str] = None,
                          user_id: Optional[str] = None,
                          start_time: Optional[str] = None,
                          end_time: Optional[str] = None,
                          limit: int = 100) -> List[Dict]:
        """查询审计日志

        两种模式均支持：
        - db_mode: 查询 audit_logs 表
        - file_mode: 查询 JSONL 文件

        Args:
            event_type: 事件类型过滤
            user_id: 用户 ID 过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大条数

        Returns:
            审计日志列表
        """
        # 默认空实现，子类可选覆盖
        return []

    # ==================== 事务支持 ====================

    @abstractmethod
    async def begin_transaction(self) -> None:
        """开始事务"""
        pass

    @abstractmethod
    async def commit_transaction(self) -> None:
        """提交事务"""
        pass

    @abstractmethod
    async def rollback_transaction(self) -> None:
        """回滚事务"""
        pass

    # ==================== 统计操作 ====================

    @abstractmethod
    async def get_stats(self, kb_id: Optional[int] = None) -> Dict:
        """获取统计信息

        Args:
            kb_id: 知识库 ID（可选）

        Returns:
            统计信息字典
        """
        pass