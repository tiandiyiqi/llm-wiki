"""存储管理器工厂

提供便捷的工厂函数来创建存储管理器实例。
支持 file_mode（文件系统）和 db_mode（数据库）两种模式。

PLAN-004 Phase 2 改造：
- create() 统一返回 StorageInterface 类型
- db_mode 返回 DatabaseStorage（而非 DatabaseManager）
- 配置驱动切换（LLM_WIKI_STORAGE_MODE 环境变量）
"""

from typing import Optional
from pathlib import Path
import os
import logging

from .config import StorageConfig, StorageType
from .storage_interface import StorageInterface

logger = logging.getLogger(__name__)


class StorageMode:
    """存储模式枚举"""
    FILE = "file"
    DB = "db"


class StorageFactory:
    """存储工厂类

    支持两种存储模式：
    - file_mode: 文件系统存储（保留 Skill 特性）
    - db_mode: PostgreSQL 数据库存储（企业模式）

    返回统一的 StorageInterface，实现双模式透明切换。
    """

    @staticmethod
    def create(config: Optional[StorageConfig] = None,
               mode: Optional[str] = None) -> StorageInterface:
        """创建存储实例（统一返回 StorageInterface）

        根据配置和环境变量自动选择 file_mode 或 db_mode。

        模式推断优先级：
        1. 显式 mode 参数
        2. LLM_WIKI_STORAGE_MODE 环境变量
        3. 配置中的 type（postgres → db, sqlite → file）
        4. 默认 file_mode

        Args:
            config: 存储配置（可选，默认从环境变量加载）
            mode: 存储模式 ('file' | 'db')，优先级最高

        Returns:
            StorageInterface 实例（FileSystemStorage 或 DatabaseStorage）

        Raises:
            ValueError: 配置无效时抛出
        """
        config = config or StorageConfig.from_env()

        # 推断模式（优先级：显式参数 > 环境变量 > 配置推断）
        if mode is None:
            mode = os.getenv('LLM_WIKI_STORAGE_MODE')

        if mode is None:
            # 根据配置类型推断
            if config.type == StorageType.POSTGRES and config.postgres_url:
                mode = StorageMode.DB
            else:
                mode = StorageMode.FILE

        if mode == StorageMode.DB:
            from .db_storage import DatabaseStorage
            if not config.validate():
                raise ValueError("Invalid storage configuration for db_mode")
            return DatabaseStorage(config)
        else:
            from .file_storage import FileSystemStorage
            storage_path = config.sqlite_data_dir or os.getenv(
                'LLM_WIKI_STORAGE_PATH', './knowledge-bases'
            )
            return FileSystemStorage(Path(storage_path))

    @staticmethod
    def create_database_manager(config: StorageConfig):
        """创建数据库管理器（底层管理器，不经过 StorageInterface）

        用于需要直接操作 PostgreSQLManager/SQLiteManager 的场景。
        调用者需要手动调用 initialize()。

        Args:
            config: 存储配置

        Returns:
            数据库管理器实例（未初始化）

        Raises:
            ValueError: 配置无效时抛出
        """
        if not config.validate():
            raise ValueError("Invalid storage configuration")

        from .db_manager import DatabaseManager
        from .sqlite_manager import SQLiteManager
        from .postgres_manager import PostgreSQLManager

        if config.type == StorageType.POSTGRES:
            return PostgreSQLManager(config)
        else:
            return SQLiteManager(config)


async def create_storage(config: Optional[StorageConfig] = None,
                         mode: Optional[str] = None) -> StorageInterface:
    """创建并初始化存储实例

    便捷函数：创建 + 初始化一步完成。

    Args:
        config: 存储配置（可选，默认从环境变量加载）
        mode: 存储模式 ('file' | 'db')

    Returns:
        已初始化的 StorageInterface 实例

    Raises:
        ValueError: 配置无效时抛出
    """
    storage = StorageFactory.create(config, mode)
    await storage.initialize()
    return storage


async def create_manager(config: Optional[StorageConfig] = None):
    """创建数据库管理器（兼容旧接口）

    根据配置自动选择 SQLite 或 PostgreSQL 实现。
    推荐使用 create_storage() 代替。

    Args:
        config: 存储配置（可选，默认从环境变量加载）

    Returns:
        已初始化的数据库管理器实例

    Raises:
        ValueError: 配置无效时抛出
    """
    config = config or StorageConfig.from_env()

    if not config.validate():
        raise ValueError("Invalid storage configuration")

    from .sqlite_manager import SQLiteManager
    from .postgres_manager import PostgreSQLManager

    if config.type == StorageType.POSTGRES:
        manager = PostgreSQLManager(config)
    else:
        manager = SQLiteManager(config)

    await manager.initialize()
    return manager


def get_manager_class(config: Optional[StorageConfig] = None) -> type:
    """获取数据库管理器类

    用于延迟初始化场景。

    Args:
        config: 存储配置（可选，默认从环境变量加载）

    Returns:
        数据库管理器类
    """
    config = config or StorageConfig.from_env()

    from .sqlite_manager import SQLiteManager
    from .postgres_manager import PostgreSQLManager

    if config.type == StorageType.POSTGRES:
        return PostgreSQLManager
    else:
        return SQLiteManager
