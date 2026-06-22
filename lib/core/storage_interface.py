"""存储接口抽象层

定义统一的存储接口，支持 file_mode 和 db_mode 透明切换。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pathlib import Path


class StorageInterface(ABC):
    """存储接口抽象基类

    统一 file_mode 和 db_mode 的 API 接口。
    实现类：
    - FileSystemStorage: 文件系统模式（保留 Skill 特性）
    - DatabaseStorage: 数据库模式（PostgreSQL + RLS）
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