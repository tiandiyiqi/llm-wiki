"""数据库管理核心模块

提供存储抽象层，支持 SQLite 和 PostgreSQL 双模式。

使用示例:
    from lib.core import StorageConfig, StorageType
    from lib.core import SQLiteManager, PostgreSQLManager

    # SQLite 模式
    config = StorageConfig(type=StorageType.SQLITE)
    manager = SQLiteManager(config)
    await manager.initialize()

    # PostgreSQL 模式
    config = StorageConfig(
        type=StorageType.POSTGRES,
        postgres_url="postgresql://user:pass@localhost/llm_wiki"
    )
    manager = PostgreSQLManager(config)
    await manager.initialize()

    # 从环境变量加载配置
    config = StorageConfig.from_env()

    # 使用工厂函数（推荐）
    from lib.core import create_manager
    manager = await create_manager()  # 自动从环境变量加载配置
"""

from .config import StorageConfig, StorageType
from .db_manager import DatabaseManager
from .sqlite_manager import SQLiteManager
from .postgres_manager import PostgreSQLManager
from .factory import create_manager, StorageFactory, get_manager_class
from .transaction import TransactionContext, TransactionError, transaction, with_retry

__all__ = [
    'DatabaseManager',
    'SQLiteManager',
    'PostgreSQLManager',
    'StorageConfig',
    'StorageType',
    'create_manager',
    'StorageFactory',
    'get_manager_class',
    'TransactionContext',
    'TransactionError',
    'transaction',
    'with_retry',
]
