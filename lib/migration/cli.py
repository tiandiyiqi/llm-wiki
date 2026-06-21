"""迁移 CLI 命令

提供迁移相关的命令行接口。
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from .migrate import MigrationManager, MigrationResult
from .validators import MigrationValidator


def register_migrate_commands(subparsers, parent_parser) -> None:
    """注册迁移命令

    Args:
        subparsers: argparse 子解析器
        parent_parser: 父解析器（用于继承通用参数）
    """
    # migrate 命令
    migrate_parser = subparsers.add_parser(
        'migrate',
        help='迁移知识库到 PostgreSQL',
        description='将文件系统数据迁移到 PostgreSQL 数据库',
    )
    migrate_parser.add_argument(
        'knowledge_base',
        nargs='?',
        help='知识库名称或路径（不指定则迁移所有）',
    )
    migrate_parser.add_argument(
        '--to',
        dest='target',
        choices=['postgres'],
        default='postgres',
        help='目标存储类型（默认: postgres）',
    )
    migrate_parser.add_argument(
        '--postgres-url',
        default='postgresql://localhost/llmwiki',
        help='PostgreSQL 连接 URL',
    )
    migrate_parser.add_argument(
        '--all',
        action='store_true',
        help='迁移所有已注册的知识库',
    )
    migrate_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预演模式（不实际写入）',
    )
    migrate_parser.add_argument(
        '--validate',
        action='store_true',
        help='迁移后验证数据一致性',
    )
    migrate_parser.add_argument(
        '--incremental',
        action='store_true',
        help='增量迁移（只迁移变更）',
    )
    migrate_parser.set_defaults(func=cmd_migrate)


async def _run_migrate(args) -> None:
    """执行迁移（异步）"""
    from ..registry import KBRegistry

    # 解析 PostgreSQL URL
    postgres_url = args.postgres_url
    if not postgres_url.startswith('postgresql://'):
        print(f"❌ 无效的 PostgreSQL URL: {postgres_url}")
        sys.exit(1)

    # 创建迁移管理器
    manager = MigrationManager(postgres_url, dry_run=args.dry_run)

    try:
        # dry-run 模式不需要连接数据库
        if not args.dry_run:
            await manager.initialize()

        if args.dry_run:
            print("🔍 预演模式（DRY-RUN）- 不实际写入数据\n")

        # 迁移所有知识库
        if getattr(args, 'all', False):
            print("📦 迁移所有知识库...\n")
            count = await manager.migrate_registry()
            print(f"\n✅ 迁移完成: {count} 个知识库")
            return

        # 迁移单个知识库
        kb_path = _resolve_kb_path(args)
        if not kb_path:
            print("❌ 未找到知识库")
            sys.exit(1)

        result = await manager.migrate_kb(kb_path, target=args.target)

        # 验证
        if getattr(args, 'validate', False) and result.success:
            print("\n🔍 验证迁移结果...\n")
            validator = MigrationValidator(manager.db, kb_path)
            await validator.validate_all(result.kb_id)

        sys.exit(0 if result.success else 1)

    finally:
        await manager.close()


def cmd_migrate(args) -> None:
    """迁移命令入口"""
    asyncio.run(_run_migrate(args))


def _resolve_kb_path(args) -> Optional[Path]:
    """解析知识库路径

    Args:
        args: 命令参数

    Returns:
        知识库路径
    """
    from ..registry import KBRegistry

    registry = KBRegistry(project_dir=Path.cwd())

    if hasattr(args, 'knowledge_base') and args.knowledge_base:
        # 尝试作为名称解析
        kb = registry.get(args.knowledge_base)
        if kb:
            return Path(kb['path'])

        # 尝试作为路径
        path = Path(args.knowledge_base)
        if path.exists():
            return path

        print(f"❌ 知识库不存在: {args.knowledge_base}")
        return None

    # 使用当前知识库
    current = registry.get_current()
    if current:
        kb = registry.get(current)
        if kb:
            return Path(kb['path'])

    print("❌ 未指定知识库，请使用 'llm-wiki use <name>' 设置当前知识库")
    return None


# ============================================================================
# 辅助命令
# ============================================================================

def cmd_migrate_status(args) -> None:
    """查看迁移状态"""
    asyncio.run(_run_migrate_status(args))


async def _run_migrate_status(args) -> None:
    """执行状态查询（异步）"""
    from ..core.factory import create_database_manager
    from ..core.config import StorageConfig, StorageType

    postgres_url = args.postgres_url

    config = StorageConfig(
        type=StorageType.POSTGRES,
        postgres_url=postgres_url,
    )

    db = create_database_manager(config)

    try:
        await db.initialize()

        # 列出所有知识库
        kbs = await db.list_kbs()

        if not kbs:
            print("📊 PostgreSQL 中无知识库")
            return

        print(f"📊 PostgreSQL 知识库状态\n")
        print(f"{'ID':<6} {'名称':<20} {'原子数':<10} {'类型':<12} {'创建时间'}")
        print("-" * 70)

        for kb in kbs:
            kb_id = kb['id']
            atom_count = await db.get_atom_count(kb_id)
            print(f"{kb_id:<6} {kb['name']:<20} {atom_count:<10} {kb.get('kb_type', 'standalone'):<12} {kb.get('created_at', '')[:10]}")

    finally:
        await db.close()


def cmd_migrate_rollback(args) -> None:
    """回滚迁移"""
    print("⚠️  回滚功能尚未实现")
    print("   请手动删除 PostgreSQL 中的数据:")
    print(f"   DELETE FROM knowledge_bases WHERE name = '{args.kb_name}';")
    sys.exit(1)


def cmd_migrate_compare(args) -> None:
    """比较源和目标数据"""
    asyncio.run(_run_migrate_compare(args))


class MigrationCLI:
    """迁移 CLI 封装类，提供编程式访问接口"""

    def get_help(self) -> str:
        """返回迁移命令帮助信息"""
        return (
            "migrate: 将文件系统数据迁移到 PostgreSQL 数据库\n"
            "用法: llm-wiki migrate [knowledge_base] [选项]\n"
            "选项:\n"
            "  --to postgres        目标存储类型\n"
            "  --postgres-url URL   PostgreSQL 连接 URL\n"
            "  --all                迁移所有知识库\n"
            "  --dry-run            预演模式（不实际写入）\n"
            "  --validate           迁移后验证数据\n"
        )


async def _run_migrate_compare(args) -> None:
    """执行比较（异步）"""
    from ..core.factory import create_database_manager
    from ..core.config import StorageConfig, StorageType

    kb_path = _resolve_kb_path(args)
    if not kb_path:
        sys.exit(1)

    postgres_url = args.postgres_url

    config = StorageConfig(
        type=StorageType.POSTGRES,
        postgres_url=postgres_url,
    )

    db = create_database_manager(config)

    try:
        await db.initialize()

        # 获取知识库 ID
        kb_name = kb_path.name
        kb = await db.get_kb_by_name(kb_name)

        if not kb:
            print(f"❌ PostgreSQL 中未找到知识库: {kb_name}")
            sys.exit(1)

        kb_id = kb['id']

        # 创建验证器
        validator = MigrationValidator(db, kb_path)

        # 比较统计
        source_stats = await validator._get_source_stats()
        target_stats = await validator._get_target_stats(kb_id)

        print(f"📊 数据比较: {kb_name}\n")

        print("源数据统计:")
        for key, value in source_stats.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

        print("\n目标数据统计:")
        for key, value in target_stats.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

        # 差异分析
        print("\n差异分析:")
        for key in set(source_stats.keys()) | set(target_stats.keys()):
            source_val = source_stats.get(key, 0)
            target_val = target_stats.get(key, 0)

            if isinstance(source_val, dict) and isinstance(target_val, dict):
                # 类型统计比较
                all_types = set(source_val.keys()) | set(target_val.keys())
                for t in all_types:
                    s = source_val.get(t, 0)
                    t_val = target_val.get(t, 0)
                    if s != t_val:
                        print(f"  {key}.{t}: 源 {s} -> 目标 {t_val} (差异: {t_val - s:+d})")
            elif source_val != target_val:
                diff = target_val - source_val if isinstance(target_val, int) and isinstance(source_val, int) else 'N/A'
                print(f"  {key}: 源 {source_val} -> 目标 {target_val} (差异: {diff:+d if isinstance(diff, int) else diff})")

    finally:
        await db.close()
