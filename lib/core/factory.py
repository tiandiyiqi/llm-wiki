"""数据库管理器工厂

提供便捷的工厂函数来创建数据库管理器实例。
"""

from typing import Optional

from .config import StorageConfig, StorageType
from .db_manager import DatabaseManager
from .sqlite_manager import SQLiteManager
from .postgres_manager import PostgreSQLManager


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
