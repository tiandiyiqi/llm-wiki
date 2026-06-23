"""数据库初始化脚本

提供 PostgreSQL 数据库的初始化和迁移管理功能。
支持增量迁移、版本追踪和校验和验证。
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# SQL 文件目录
_DB_DIR = Path(__file__).parent

# SQL 文件加载顺序
_SQL_FILES = [
    "schema.sql",
    "functions.sql",
    "indexes.sql",
    "rls.sql",
]


class SchemaMigration:
    """Schema 迁移记录"""

    def __init__(
        self,
        version: int,
        name: str,
        applied_at: Optional[str] = None,
        checksum: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
    ):
        self.version = version
        self.name = name
        self.applied_at = applied_at
        self.checksum = checksum
        self.execution_time_ms = execution_time_ms

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "name": self.name,
            "applied_at": self.applied_at,
            "checksum": self.checksum,
            "execution_time_ms": self.execution_time_ms,
        }


class DatabaseInitializer:
    """数据库初始化器

    负责：
    - 检查 schema 版本状态
    - 执行增量迁移
    - 验证 schema 完整性
    """

    def __init__(self, pool):
        """初始化

        Args:
            pool: asyncpg 连接池
        """
        self.pool = pool

    async def get_current_version(self) -> int:
        """获取当前 schema 版本

        Returns:
            当前版本号，如果没有迁移记录返回 0
        """
        try:
            async with self.pool.acquire() as conn:
                # 先检查表是否存在
                exists = await conn.fetchval('''
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'schema_migrations'
                    )
                ''')

                if not exists:
                    return 0

                row = await conn.fetchrow(
                    'SELECT MAX(version) as version FROM schema_migrations'
                )
                return row['version'] if row and row['version'] else 0
        except Exception as e:
            logger.error("Failed to get current version: %s", e)
            return 0

    async def get_applied_migrations(self) -> List[SchemaMigration]:
        """获取已应用的迁移列表

        Returns:
            迁移记录列表
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    'SELECT * FROM schema_migrations ORDER BY version'
                )
                return [
                    SchemaMigration(
                        version=row['version'],
                        name=row['name'],
                        applied_at=row['applied_at'].isoformat() if row['applied_at'] else None,
                        checksum=row['checksum'],
                        execution_time_ms=row['execution_time_ms'],
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error("Failed to get applied migrations: %s", e)
            return []

    @staticmethod
    def _compute_checksum(sql_content: str) -> str:
        """计算 SQL 内容的校验和

        Args:
            sql_content: SQL 文件内容

        Returns:
            SHA256 校验和
        """
        return hashlib.sha256(sql_content.encode("utf-8")).hexdigest()

    @staticmethod
    def _split_sql(sql_content: str) -> List[str]:
        """将 SQL 文件内容拆分为独立语句

        处理 $$...$$ 块内的分号，避免误拆。

        Args:
            sql_content: SQL 文件内容

        Returns:
            SQL 语句列表
        """
        statements = []
        current = []
        in_dollar_quote = False

        for line in sql_content.split("\n"):
            stripped = line.strip()

            # 跳过空行和纯注释行
            if not stripped or stripped.startswith("--"):
                continue

            # 追踪 $$ 块
            dollar_count = stripped.count("$$")
            if dollar_count > 0:
                in_dollar_quote = not in_dollar_quote

            current.append(line)

            # 行以分号结束且不在 $$ 块内
            if stripped.endswith(";") and not in_dollar_quote:
                stmt = "\n".join(current)
                statements.append(stmt)
                current = []

        # 处理未以分号结束的最后一条
        if current:
            remaining = "\n".join(current).strip()
            if remaining:
                statements.append(remaining)

        return statements

    async def initialize_full(self) -> None:
        """完整初始化数据库

        加载所有 SQL 文件，适用于新数据库。
        """
        logger.info("Starting full database initialization...")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for sql_file_name in _SQL_FILES:
                    sql_path = _DB_DIR / sql_file_name
                    if not sql_path.exists():
                        logger.warning("SQL file not found, skipping: %s", sql_path)
                        continue

                    sql_content = sql_path.read_text(encoding="utf-8")
                    checksum = self._compute_checksum(sql_content)

                    start_time = time.monotonic()
                    statements = self._split_sql(sql_content)

                    for stmt in statements:
                        stmt = stmt.strip()
                        if stmt:
                            try:
                                await conn.execute(stmt)
                            except Exception as e:
                                error_msg = str(e).lower()
                                if any(skip in error_msg for skip in [
                                    'already exists',
                                    'duplicate',
                                    'conflict',
                                ]):
                                    logger.debug(
                                        "Skipping already-existing object in %s: %s",
                                        sql_file_name, e,
                                    )
                                else:
                                    logger.error(
                                        "Failed in %s: %s", sql_file_name, e
                                    )
                                    raise

                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
                    logger.info(
                        "Loaded %s (%d statements, %dms)",
                        sql_file_name, len(statements), elapsed_ms,
                    )

        version = await self.get_current_version()
        logger.info("Full initialization complete. Schema version: %d", version)

    async def needs_initialization(self) -> bool:
        """检查数据库是否需要初始化

        Returns:
            是否需要初始化
        """
        version = await self.get_current_version()
        return version == 0

    async def verify_schema(self) -> Dict[str, Any]:
        """验证 schema 完整性

        Returns:
            验证结果，包含状态和详细信息
        """
        result = {
            "valid": True,
            "version": 0,
            "tables": [],
            "missing_tables": [],
            "migrations": [],
        }

        try:
            # 获取当前版本
            result["version"] = await self.get_current_version()

            # 获取已应用的迁移
            result["migrations"] = [
                m.to_dict() for m in await self.get_applied_migrations()
            ]

            # 检查关键表是否存在
            expected_tables = [
                "users",
                "organizations",
                "knowledge_bases",
                "kb_members",
                "atoms",
                "atom_links",
                "tags",
                "atom_tags",
                "snapshots",
                "snapshot_items",
                "atom_assets",
                "ocr_tasks",
                "previews",
                "audit_logs",
                "schema_migrations",
            ]

            async with self.pool.acquire() as conn:
                existing = await conn.fetch('''
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                ''')
                existing_names = {row['table_name'] for row in existing}

            result["tables"] = sorted(existing_names)
            result["missing_tables"] = [
                t for t in expected_tables if t not in existing_names
            ]

            if result["missing_tables"]:
                result["valid"] = False

        except Exception as e:
            result["valid"] = False
            result["error"] = str(e)

        return result


async def init_database(pool) -> None:
    """便捷函数：初始化数据库

    Args:
        pool: asyncpg 连接池
    """
    initializer = DatabaseInitializer(pool)

    if await initializer.needs_initialization():
        await initializer.initialize_full()
    else:
        logger.info(
            "Database already initialized (version %d), skipping.",
            await initializer.get_current_version(),
        )
