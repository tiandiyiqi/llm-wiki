"""迁移工具模块

提供从文件系统到 PostgreSQL 的数据迁移功能。

支持迁移：
- registry.json -> knowledge_bases 表
- atoms/*.md -> atoms 表
- wikilinks -> atom_links 表
- ChromaDB -> pgvector
"""

from .migrate import MigrationManager, MigrationResult
from .validators import MigrationValidator, ValidationResult
from .cli import register_migrate_commands

__all__ = [
    'MigrationManager',
    'MigrationResult',
    'MigrationValidator',
    'ValidationResult',
    'register_migrate_commands',
]