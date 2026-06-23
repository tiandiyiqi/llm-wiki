"""数据库管理抽象基类

定义统一的数据库操作接口，支持 SQLite 和 PostgreSQL 双实现。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class DatabaseManager(ABC):
    """数据库管理抽象基类

    提供知识库和知识原子的 CRUD 操作接口。
    所有方法均为异步，支持高并发场景。
    """

    @abstractmethod
    async def initialize(self) -> None:
        """初始化数据库连接

        创建连接池、建表等初始化操作。
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭数据库连接

        释放连接池资源。
        """
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """检查数据库连接状态

        Returns:
            是否已连接
        """
        pass

    # ========== 知识库操作 ==========

    @abstractmethod
    async def create_kb(self, kb_data: Dict[str, Any]) -> int:
        """创建知识库

        Args:
            kb_data: 知识库数据
                - name: 知识库名称
                - path: 知识库路径
                - description: 描述
                - tags: 标签列表
                - kb_type: 类型 (standalone/parent/child)
                - parent: 父知识库名称（可选）

        Returns:
            kb_id: 知识库 ID
        """
        pass

    @abstractmethod
    async def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]:
        """获取知识库信息

        Args:
            kb_id: 知识库 ID

        Returns:
            知识库信息字典，不存在返回 None
        """
        pass

    @abstractmethod
    async def get_kb_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取知识库信息

        Args:
            name: 知识库名称

        Returns:
            知识库信息字典，不存在返回 None
        """
        pass

    @abstractmethod
    async def list_kbs(self, user_id: Optional[str] = None,
                       scope: str = 'all') -> List[Dict[str, Any]]:
        """列出知识库

        Args:
            user_id: 用户 ID（可选，用于权限过滤）
            scope: 范围 (all/project/global)

        Returns:
            知识库列表
        """
        pass

    @abstractmethod
    async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool:
        """更新知识库

        Args:
            kb_id: 知识库 ID
            kb_data: 更新数据

        Returns:
            是否更新成功
        """
        pass

    @abstractmethod
    async def delete_kb(self, kb_id: int) -> bool:
        """删除知识库

        Args:
            kb_id: 知识库 ID

        Returns:
            是否删除成功
        """
        pass

    # ========== 知识原子操作 ==========

    @abstractmethod
    async def create_atom(self, atom_data: Dict[str, Any]) -> int:
        """创建知识原子

        Args:
            atom_data: 知识原子数据
                - kb_id: 知识库 ID
                - path: 原子路径
                - type: 原子类型
                - title: 标题
                - description: 描述
                - tags: 标签列表
                - body: 正文内容
                - frontmatter: YAML 元数据

        Returns:
            atom_id: 知识原子 ID
        """
        pass

    @abstractmethod
    async def get_atom(self, atom_id: int) -> Optional[Dict[str, Any]]:
        """获取知识原子

        Args:
            atom_id: 知识原子 ID

        Returns:
            知识原子字典，不存在返回 None
        """
        pass

    @abstractmethod
    async def get_atom_by_path(self, kb_id: int, path: str) -> Optional[Dict[str, Any]]:
        """根据路径获取知识原子

        Args:
            kb_id: 知识库 ID
            path: 原子路径

        Returns:
            知识原子字典，不存在返回 None
        """
        pass

    @abstractmethod
    async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool:
        """更新知识原子

        Args:
            atom_id: 知识原子 ID
            atom_data: 更新数据

        Returns:
            是否更新成功
        """
        pass

    @abstractmethod
    async def delete_atom(self, atom_id: int, hard_delete: bool = False) -> bool:
        """删除知识原子

        Args:
            atom_id: 知识原子 ID
            hard_delete: 是否硬删除（默认软删除）

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    async def list_atoms(self, kb_id: int, by_type: Optional[str] = None,
                         limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """列出知识原子

        Args:
            kb_id: 知识库 ID
            by_type: 按类型过滤（可选）
            limit: 返回数量上限
            offset: 偏移量

        Returns:
            知识原子列表
        """
        pass

    # ========== 搜索操作 ==========

    @abstractmethod
    async def search_atoms(self, query: str, kb_id: Optional[int] = None,
                           by_type: Optional[str] = None,
                           tags: Optional[List[str]] = None,
                           limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索知识原子

        Args:
            query: 查询字符串
            kb_id: 知识库 ID（可选，不指定则全局搜索）
            by_type: 按类型过滤（可选）
            tags: 按标签过滤（可选）
            limit: 返回数量上限
            offset: 偏移量

        Returns:
            搜索结果列表
        """
        pass

    @abstractmethod
    async def search_atoms_advanced(self, query: str,
                                     filters: Optional[Dict[str, Any]] = None,
                                     sort_by: str = 'relevance',
                                     limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """高级搜索知识原子

        Args:
            query: 查询字符串
            filters: 过滤条件
                - kb_id: 知识库 ID
                - type: 类型
                - tags: 标签列表
                - author: 作者
                - date_from: 起始日期
                - date_to: 结束日期
                - source_type: 来源类型
                - status: 状态
            sort_by: 排序方式 (relevance/time/title)
            limit: 返回数量上限
            offset: 偏移量

        Returns:
            搜索结果列表
        """
        pass

    # ========== 父子知识库操作 ==========

    @abstractmethod
    async def register_child_kb(self, parent_id: int, child_id: int,
                                 child_path: str) -> bool:
        """注册子知识库到父知识库

        Args:
            parent_id: 父知识库 ID
            child_id: 子知识库 ID
            child_path: 子知识库相对路径

        Returns:
            是否注册成功
        """
        pass

    @abstractmethod
    async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]:
        """获取子知识库列表

        Args:
            parent_id: 父知识库 ID

        Returns:
            子知识库列表
        """
        pass

    @abstractmethod
    async def get_parent_kb(self, child_id: int) -> Optional[Dict[str, Any]]:
        """获取父知识库信息

        Args:
            child_id: 子知识库 ID

        Returns:
            父知识库信息，不存在返回 None
        """
        pass

    # ========== 统计操作 ==========

    @abstractmethod
    async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]:
        """获取知识库统计信息

        Args:
            kb_id: 知识库 ID

        Returns:
            统计信息字典
        """
        pass

    @abstractmethod
    async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int:
        """获取知识原子数量

        Args:
            kb_id: 知识库 ID
            by_type: 按类型过滤（可选）

        Returns:
            原子数量
        """
        pass

    # ========== 事务操作 ==========

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

    # ========== 工具方法 ==========

    def _get_timestamp(self) -> str:
        """获取当前时间戳

        Returns:
            ISO 格式时间戳
        """
        return datetime.now().isoformat()

    def _validate_kb_data(self, kb_data: Dict[str, Any]) -> bool:
        """验证知识库数据

        Args:
            kb_data: 知识库数据

        Returns:
            是否有效
        """
        # name 是唯一必填字段（slug 可自动生成）
        return 'name' in kb_data

    def _validate_atom_data(self, atom_data: Dict[str, Any]) -> bool:
        """验证知识原子数据

        Args:
            atom_data: 知识原子数据

        Returns:
            是否有效
        """
        # kb_id, title, content, type 是必填字段
        required_fields = ['kb_id', 'title', 'content', 'type']
        return all(field in atom_data for field in required_fields)
