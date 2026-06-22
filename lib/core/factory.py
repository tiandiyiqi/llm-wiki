"""存储管理器工厂

提供便捷的工厂函数来创建存储管理器实例。
支持 file_mode（文件系统）和 db_mode（数据库）两种模式。
"""

from typing import Optional, Union
from pathlib import Path
import os

from .config import StorageConfig, StorageType
from .db_manager import DatabaseManager
from .sqlite_manager import SQLiteManager
from .postgres_manager import PostgreSQLManager


class StorageMode:
    """存储模式枚举"""
    FILE = "file"
    DB = "db"


class StorageFactory:
    """存储工厂类

    支持两种存储模式：
    - file_mode: 文件系统存储（保留 Skill 特性）
    - db_mode: PostgreSQL 数据库存储（企业模式）
    """

    @staticmethod
    def create(config: Optional[StorageConfig] = None, mode: Optional[str] = None) -> Union['FileSystemStorage', DatabaseManager]:
        """创建存储管理器实例

        Args:
            config: 存储配置（可选，默认从环境变量加载）
            mode: 存储模式 ('file' | 'db')，默认从配置推断

        Returns:
            存储管理器实例

        Raises:
            ValueError: 配置无效时抛出
        """
        config = config or StorageConfig.from_env()

        # 推断模式
        if mode is None:
            mode = os.getenv('LLM_WIKI_STORAGE_MODE', 'file')

        if mode == 'db':
            # 数据库模式：使用现有的 DatabaseManager
            if not config.validate():
                raise ValueError("Invalid storage configuration")
            if config.type == StorageType.POSTGRES:
                return PostgreSQLManager(config)
            else:
                return SQLiteManager(config)
        else:
            # 文件模式：返回 FileSystemStorage
            from .file_storage import FileSystemStorage
            storage_path = config.sqlite_data_dir or os.getenv('LLM_WIKI_STORAGE_PATH', './knowledge-bases')
            return FileSystemStorage(Path(storage_path))

    @staticmethod
    def create_database_manager(config: StorageConfig) -> DatabaseManager:
        """创建数据库管理器（同步版本，不初始化）

        根据配置自动选择 SQLite 或 PostgreSQL 实现。
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

        if config.type == StorageType.POSTGRES:
            return PostgreSQLManager(config)
        else:
            return SQLiteManager(config)


async def create_manager(config: Optional[StorageConfig] = None) -> DatabaseManager:
    """创建数据库管理器

    根据配置自动选择 SQLite 或 PostgreSQL 实现。

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

    if config.type == StorageType.POSTGRES:
        return PostgreSQLManager
    else:
        return SQLiteManager
