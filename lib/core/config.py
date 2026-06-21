"""存储配置模块

定义存储类型和配置参数，支持从环境变量加载。
"""

import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class StorageType(Enum):
    """存储类型枚举"""
    SQLITE = "sqlite"
    POSTGRES = "postgres"


@dataclass
class StorageConfig:
    """存储配置

    Attributes:
        type: 存储类型（SQLite 或 PostgreSQL）
        postgres_url: PostgreSQL 连接 URL
        pool_size: 连接池大小
        max_overflow: 最大溢出连接数
        sqlite_data_dir: SQLite 数据目录
    """
    type: StorageType = StorageType.SQLITE
    postgres_url: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20
    sqlite_data_dir: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'StorageConfig':
        """从环境变量加载配置

        环境变量:
            LLM_WIKI_STORAGE_TYPE: 存储类型 (sqlite/postgres)
            LLM_WIKI_POSTGRES_URL: PostgreSQL 连接 URL
            LLM_WIKI_POOL_SIZE: 连接池大小
            LLM_WIKI_MAX_OVERFLOW: 最大溢出连接数
            LLM_WIKI_SQLITE_DATA_DIR: SQLite 数据目录

        Returns:
            StorageConfig 实例
        """
        storage_type_str = os.getenv('LLM_WIKI_STORAGE_TYPE', 'sqlite').lower()
        try:
            storage_type = StorageType(storage_type_str)
        except ValueError:
            storage_type = StorageType.SQLITE

        postgres_url = os.getenv('LLM_WIKI_POSTGRES_URL')
        pool_size = int(os.getenv('LLM_WIKI_POOL_SIZE', '10'))
        max_overflow = int(os.getenv('LLM_WIKI_MAX_OVERFLOW', '20'))
        sqlite_data_dir = os.getenv('LLM_WIKI_SQLITE_DATA_DIR')

        return cls(
            type=storage_type,
            postgres_url=postgres_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            sqlite_data_dir=sqlite_data_dir,
        )

    @classmethod
    def from_dict(cls, data: dict) -> 'StorageConfig':
        """从字典加载配置

        Args:
            data: 配置字典

        Returns:
            StorageConfig 实例
        """
        storage_type_str = data.get('type', 'sqlite')
        try:
            storage_type = StorageType(storage_type_str)
        except ValueError:
            storage_type = StorageType.SQLITE

        return cls(
            type=storage_type,
            postgres_url=data.get('postgres_url'),
            pool_size=data.get('pool_size', 10),
            max_overflow=data.get('max_overflow', 20),
            sqlite_data_dir=data.get('sqlite_data_dir'),
        )

    def to_dict(self) -> dict:
        """转换为字典

        Returns:
            配置字典
        """
        return {
            'type': self.type.value,
            'postgres_url': self.postgres_url,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'sqlite_data_dir': self.sqlite_data_dir,
        }

    def validate(self) -> bool:
        """验证配置有效性

        Returns:
            是否有效
        """
        if self.type == StorageType.POSTGRES:
            if not self.postgres_url:
                return False
            if not self.postgres_url.startswith('postgresql'):
                return False
        return True