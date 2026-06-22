"""迁移主逻辑

实现从文件系统到 PostgreSQL 的数据迁移。
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.factory import StorageFactory
from ..core.config import StorageConfig, StorageType
from ..core.config import StorageConfig, StorageType
from ..core.postgres_manager import PostgreSQLManager
from ..yaml_parser import SimpleYAMLParser
from ..constants import RESERVED_FILES


@dataclass
class MigrationResult:
    """迁移结果"""
    success: bool
    kb_id: Optional[int] = None
    atoms_migrated: int = 0
    atoms_failed: int = 0
    links_migrated: int = 0
    embeddings_migrated: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    dry_run: bool = False

    def __str__(self) -> str:
        status = "✅ 成功" if self.success else "❌ 失败"
        lines = [
            f"迁移结果: {status}",
            f"  知识库 ID: {self.kb_id}",
            f"  原子迁移: {self.atoms_migrated} 成功, {self.atoms_failed} 失败",
            f"  链接迁移: {self.links_migrated}",
            f"  向量迁移: {self.embeddings_migrated}",
            f"  耗时: {self.duration_seconds:.2f} 秒",
        ]
        if self.errors:
            lines.append(f"  错误 ({len(self.errors)}):")
            for e in self.errors[:5]:
                lines.append(f"    - {e}")
        if self.warnings:
            lines.append(f"  警告 ({len(self.warnings)}):")
            for w in self.warnings[:5]:
                lines.append(f"    - {w}")
        return '\n'.join(lines)


class MigrationManager:
    """迁移管理器

    负责将文件系统数据迁移到 PostgreSQL。

    支持功能：
    - 迁移 registry.json
    - 迁移 atoms/ 目录
    - 迁移 wikilinks
    - 迁移 ChromaDB 向量到 pgvector
    - 构建全文索引
    - 增量迁移
    - dry-run 模式
    """

    def __init__(self, postgres_url: str = '', dry_run: bool = False,
                 registry_path: Optional[Path] = None):
        """初始化迁移管理器

        Args:
            postgres_url: PostgreSQL 连接 URL（dry_run 模式下可省略）
            dry_run: 是否为预演模式（不实际写入）
            registry_path: registry.json 路径（可选，默认使用 ~/.llm-wiki/registry.json）
        """
        self.postgres_url = postgres_url
        self.dry_run = dry_run
        self.registry_path = registry_path
        self.db = None
        self.yaml_parser = SimpleYAMLParser()

    async def initialize(self) -> None:
        """初始化数据库连接"""
        config = StorageConfig(
            type=StorageType.POSTGRES,
            postgres_url=self.postgres_url,
        )
        self.db = PostgreSQLManager(config)
        await self.db.initialize()

    async def close(self) -> None:
        """关闭数据库连接"""
        if self.db:
            await self.db.close()

    async def migrate_kb(self, kb_path: Path, target: str = 'postgres') -> MigrationResult:
        """迁移单个知识库

        Args:
            kb_path: 知识库路径
            target: 目标存储类型（默认 postgres）

        Returns:
            迁移结果
        """
        start_time = datetime.now()
        result = MigrationResult(success=False, dry_run=self.dry_run)

        if not kb_path.exists():
            result.errors.append(f"知识库路径不存在: {kb_path}")
            return result

        print(f"🚀 开始迁移知识库: {kb_path}")

        if self.dry_run:
            print("  [DRY-RUN] 预演模式，不实际写入数据")

        try:
            if self.dry_run:
                # 预演模式：扫描但不写入
                result.kb_id = 1
                result.success = True
                result.duration_seconds = (datetime.now() - start_time).total_seconds()
                print(result)
                return result

            # 懒初始化：如果 db 尚未初始化则自动初始化
            if self.db is None:
                await self.initialize()

            # 1. 迁移知识库元数据
            print("  [1/5] 迁移知识库元数据...")
            kb_id = await self._migrate_kb_meta(kb_path, result)
            if not kb_id:
                return result
            result.kb_id = kb_id

            # 2. 迁移知识原子
            print("  [2/5] 迁移知识原子...")
            atoms_success, atoms_failed = await self.migrate_atoms(kb_path, kb_id)
            result.atoms_migrated = atoms_success
            result.atoms_failed = atoms_failed

            # 3. 迁移链接关系
            print("  [3/5] 迁移链接关系...")
            try:
                result.links_migrated = await self.migrate_links(kb_id)
            except Exception as e:
                result.warnings.append(f"链接迁移跳过: {e}")

            # 4. 迁移向量嵌入
            print("  [4/5] 迁移向量嵌入...")
            chroma_path = kb_path / '.chroma'
            if chroma_path.exists():
                try:
                    result.embeddings_migrated = await self.migrate_embeddings(kb_id, chroma_path)
                except Exception as e:
                    result.warnings.append(f"向量迁移跳过: {e}")
            else:
                result.warnings.append("未找到 ChromaDB 数据，跳过向量迁移")

            # 5. 构建全文索引
            print("  [5/5] 构建全文索引...")
            try:
                await self.build_fulltext_index(kb_id)
            except Exception as e:
                result.warnings.append(f"全文索引构建跳过: {e}")

            result.success = True

        except Exception as e:
            result.errors.append(f"迁移失败: {str(e)}")

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        print(result)
        return result

    async def _migrate_kb_meta(self, kb_path: Path, result: MigrationResult) -> Optional[int]:
        """迁移知识库元数据

        Args:
            kb_path: 知识库路径
            result: 迁移结果（用于记录错误）

        Returns:
            知识库 ID
        """
        # 读取 .kb-meta.json
        meta_path = kb_path / '.kb-meta.json'
        kb_data = {
            'name': kb_path.name,
            'path': str(kb_path.resolve()),
            'description': '',
            'tags': [],
            'kb_type': 'standalone',
        }

        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                kb_data.update({
                    'name': meta.get('name', kb_path.name),
                    'description': meta.get('description', ''),
                    'tags': meta.get('tags', []),
                    'kb_type': meta.get('kb_type', 'standalone'),
                })
            except (json.JSONDecodeError, KeyError) as e:
                result.warnings.append(f"解析 .kb-meta.json 失败: {e}")

        if self.dry_run:
            print(f"    [DRY-RUN] 将创建知识库: {kb_data['name']}")
            return 1  # 模拟 ID

        # 检查是否已存在
        existing = await self.db.get_kb_by_name(kb_data['name'])
        if existing:
            print(f"    知识库已存在，更新: {kb_data['name']}")
            await self.db.update_kb(existing['id'], kb_data)
            return existing['id']

        # 创建新知识库
        kb_id = await self.db.create_kb(kb_data)
        print(f"    创建知识库: {kb_data['name']} (ID: {kb_id})")
        return kb_id

    async def migrate_registry(self) -> int:
        """迁移 registry.json 到 knowledge_bases 表

        Returns:
            迁移的知识库数量
        """
        registry_path = self.registry_path or (Path.home() / '.llm-wiki' / 'registry.json')
        if not registry_path.exists():
            print("❌ 未找到 registry.json")
            return 0

        registry = json.loads(registry_path.read_text(encoding='utf-8'))
        knowledge_bases = registry.get('knowledge_bases', {})

        if not knowledge_bases:
            print("⚠️  registry.json 中无知识库记录")
            return 0

        print(f"📋 迁移 {len(knowledge_bases)} 个知识库...")

        migrated = 0
        for name, info in knowledge_bases.items():
            kb_path = Path(info['path'])
            if not kb_path.exists():
                print(f"  ⚠️  跳过（路径不存在）: {name}")
                continue

            kb_data = {
                'name': name,
                'path': info['path'],
                'description': info.get('description', ''),
                'tags': info.get('tags', []),
                'kb_type': info.get('kb_type', 'standalone'),
            }

            if self.dry_run:
                print(f"  [DRY-RUN] 将迁移: {name}")
                migrated += 1
                continue

            # 懒初始化（只在实际写入前初始化）
            if self.db is None:
                await self.initialize()

            existing = await self.db.get_kb_by_name(name)
            if existing:
                await self.db.update_kb(existing['id'], kb_data)
            else:
                await self.db.create_kb(kb_data)

            print(f"  ✅ {name}")
            migrated += 1

        print(f"\n✅ 迁移完成: {migrated}/{len(knowledge_bases)}")
        return migrated

    async def migrate_atoms(self, kb_path: Path, kb_id: int) -> Tuple[int, int]:
        """迁移 atoms/ 目录到 atoms 表

        Args:
            kb_path: 知识库路径
            kb_id: 知识库 ID

        Returns:
            (成功数, 失败数)
        """
        atoms_dir = kb_path / 'atoms'
        if not atoms_dir.exists():
            print("    ⚠️  未找到 atoms/ 目录")
            return 0, 0

        # 收集所有原子文件
        atom_files = []
        for md_file in atoms_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue
            atom_files.append(md_file)

        if not atom_files:
            print("    ⚠️  atoms/ 目录为空")
            return 0, 0

        print(f"    发现 {len(atom_files)} 个原子文件")

        success_count = 0
        failed_count = 0

        for i, atom_file in enumerate(atom_files, 1):
            try:
                atom_data = await self._parse_atom_file(atom_file, kb_path, kb_id)
                if not atom_data:
                    failed_count += 1
                    continue

                if self.dry_run:
                    print(f"    [DRY-RUN] [{i}/{len(atom_files)}] {atom_data['title']}")
                    success_count += 1
                    continue

                # 检查是否已存在，存在则更新
                existing = await self.db.get_atom_by_path(kb_id, atom_data['path'])
                if existing:
                    await self.db.update_atom(existing['id'], atom_data)
                else:
                    await self.db.create_atom(atom_data)

                success_count += 1
                if i % 50 == 0:
                    print(f"    进度: {i}/{len(atom_files)}")

            except Exception as e:
                print(f"    ❌ [{i}/{len(atom_files)}] {atom_file.name}: {e}")
                failed_count += 1

        print(f"    完成: {success_count} 成功, {failed_count} 失败")
        return success_count, failed_count

    async def _parse_atom_file(self, atom_file: Path, kb_path: Path, kb_id: int) -> Optional[Dict[str, Any]]:
        """解析原子文件

        Args:
            atom_file: 原子文件路径
            kb_path: 知识库路径
            kb_id: 知识库 ID

        Returns:
            原子数据字典
        """
        content = atom_file.read_text(encoding='utf-8')
        relative_path = str(atom_file.relative_to(kb_path))

        # 解析 frontmatter
        frontmatter = {}
        body = content

        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = self.yaml_parser.parse(parts[1]) or {}
                body = parts[2].strip()

        # 提取标题
        title = frontmatter.get('title', atom_file.stem)
        if not title:
            # 尝试从正文提取
            title_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else atom_file.stem

        # 提取类型
        atom_type = frontmatter.get('type', 'method')

        # 提取描述
        description = frontmatter.get('description', '')
        if not description:
            # 尝试从正文提取
            desc_match = re.search(r'^##\s+概述\s*\n+(.+?)(?:\n\n|\n#|$)', body, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()[:200]

        # 提取标签
        tags = frontmatter.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]

        return {
            'kb_id': kb_id,
            'path': relative_path,
            'type': atom_type,
            'title': title,
            'description': description,
            'tags': tags,
            'body': body,
            'frontmatter': frontmatter,
            'file_mtime': atom_file.stat().st_mtime,
        }

    async def migrate_links(self, kb_id: int) -> int:
        """迁移 wikilinks 到 atom_links 表

        Args:
            kb_id: 知识库 ID

        Returns:
            迁移的链接数量
        """
        if self.dry_run:
            print("    [DRY-RUN] 将迁移链接关系")
            return 0

        # 获取所有原子
        atoms = await self.db.list_atoms(kb_id, limit=10000)
        if not atoms:
            return 0

        # 构建路径到 ID 的映射
        path_to_id = {atom['path']: atom['id'] for atom in atoms}

        # 解析 wikilinks
        wikilink_pattern = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')
        links_count = 0

        for atom in atoms:
            body = atom.get('body', '')
            links = wikilink_pattern.findall(body)

            for link_target in links:
                # 解析目标路径
                target_path = self._resolve_link_target(link_target, atom['path'])
                if not target_path:
                    continue

                target_id = path_to_id.get(target_path)
                if not target_id:
                    continue

                # 创建链接（ON CONFLICT DO NOTHING 已处理重复，其余异常向上抛出）
                await self._create_link(atom['id'], target_id, 'reference')
                links_count += 1

        print(f"    迁移 {links_count} 个链接")
        return links_count

    def _resolve_link_target(self, link_target: str, source_path: str) -> Optional[str]:
        """解析链接目标路径

        Args:
            link_target: 链接目标（如 "method/foo" 或 "foo"）
            source_path: 源原子路径

        Returns:
            目标原子路径
        """
        # 简化处理：假设链接目标就是相对路径
        if link_target.startswith('atoms/'):
            return link_target

        # 尝试添加 atoms/ 前缀
        if not link_target.startswith('methods/') and not link_target.startswith('facts/'):
            # 根据类型目录推断
            return f"atoms/methods/{link_target}.md"

        return f"atoms/{link_target}.md"

    async def _create_link(self, source_id: int, target_id: int, link_type: str) -> None:
        """创建原子链接

        Args:
            source_id: 源原子 ID
            target_id: 目标原子 ID
            link_type: 链接类型
        """
        # 使用原生 SQL 插入（PostgreSQLManager 的扩展方法）
        async with self.db.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO atom_links (source_atom_id, target_atom_id, link_type)
                VALUES ($1, $2, $3)
                ON CONFLICT (source_atom_id, target_atom_id, link_type) DO NOTHING
            ''', source_id, target_id, link_type)

    async def migrate_embeddings(self, kb_id: int, chroma_path: Path) -> int:
        """迁移 ChromaDB 向量嵌入到 pgvector

        Args:
            kb_id: 知识库 ID
            chroma_path: ChromaDB 路径

        Returns:
            迁移的向量数量
        """
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            print("    ⚠️  chromadb 未安装，跳过向量迁移")
            return 0

        if not chroma_path.exists():
            print("    ⚠️  ChromaDB 路径不存在")
            return 0

        if self.dry_run:
            print("    [DRY-RUN] 将迁移向量嵌入")
            return 0

        try:
            # 连接 ChromaDB
            client = chromadb.PersistentClient(path=str(chroma_path))
            collection = client.get_collection(name='knowledge_atoms')

            # 获取所有向量
            results = collection.get(include=['embeddings', 'metadatas'])

            if not results['ids']:
                print("    ⚠️  ChromaDB 中无向量数据")
                return 0

            # 获取原子路径映射
            atoms = await self.db.list_atoms(kb_id, limit=10000)
            path_to_id = {atom['path']: atom['id'] for atom in atoms}

            migrated = 0
            for i, (vec_id, embedding, metadata) in enumerate(zip(
                results['ids'],
                results['embeddings'],
                results['metadatas']
            )):
                # 从 metadata 获取路径
                vec_path = metadata.get('path', '')
                atom_id = path_to_id.get(vec_path)

                if not atom_id:
                    continue

                # 更新向量
                await self._update_embedding(atom_id, embedding)
                migrated += 1

                if (i + 1) % 100 == 0:
                    print(f"    向量进度: {i + 1}/{len(results['ids'])}")

            print(f"    迁移 {migrated} 个向量")
            return migrated

        except Exception as e:
            print(f"    ❌ 向量迁移失败: {e}")
            return 0

    async def _update_embedding(self, atom_id: int, embedding: List[float]) -> None:
        """更新原子向量

        Args:
            atom_id: 原子 ID
            embedding: 向量数据
        """
        async with self.db.pool.acquire() as conn:
            # pgvector 使用数组格式
            await conn.execute(
                'UPDATE atoms SET embedding = $1 WHERE id = $2',
                embedding,
                atom_id
            )

    async def build_fulltext_index(self, kb_id: int) -> None:
        """构建全文索引（tsvector）

        PostgreSQL 的 atoms 表已有 GENERATED ALWAYS 的 content_tsv 列，
        会自动更新全文索引。此方法仅用于重建或验证。

        Args:
            kb_id: 知识库 ID
        """
        if self.dry_run:
            print("    [DRY-RUN] 将构建全文索引")
            return

        # 触发更新（通过更新 updated_at）
        async with self.db.pool.acquire() as conn:
            # 对于 GENERATED ALWAYS 列，无需手动更新
            # 但可以重建索引以优化查询性能
            await conn.execute('''
                REINDEX INDEX IF EXISTS idx_atoms_title_fts;
                REINDEX INDEX IF EXISTS idx_atoms_body_fts;
                REINDEX INDEX IF EXISTS idx_atoms_description_fts;
            ''')

        print("    全文索引已更新")

    async def migrate_incremental(self, kb_path: Path, kb_id: int) -> Tuple[int, int]:
        """增量迁移（只迁移变更文件）

        Args:
            kb_path: 知识库路径
            kb_id: 知识库 ID

        Returns:
            (更新数, 删除数)
        """
        atoms_dir = kb_path / 'atoms'
        if not atoms_dir.exists():
            return 0, 0

        # 获取数据库中的所有原子
        db_atoms = await self.db.list_atoms(kb_id, limit=10000)
        db_paths = {atom['path']: atom for atom in db_atoms}

        # 收集文件系统中的所有原子
        file_atoms = {}
        for md_file in atoms_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue
            relative_path = str(md_file.relative_to(kb_path))
            file_atoms[relative_path] = md_file

        updated = 0
        deleted = 0

        # 检查需要更新或新增的
        for path, file_path in file_atoms.items():
            file_mtime = file_path.stat().st_mtime
            db_atom = db_paths.get(path)

            if db_atom:
                # 检查是否需要更新
                if file_mtime > db_atom.get('file_mtime', 0):
                    atom_data = await self._parse_atom_file(file_path, kb_path, kb_id)
                    if atom_data:
                        await self.db.update_atom(db_atom['id'], atom_data)
                        updated += 1
            else:
                # 新增
                atom_data = await self._parse_atom_file(file_path, kb_path, kb_id)
                if atom_data:
                    await self.db.create_atom(atom_data)
                    updated += 1

        # 检查需要删除的
        for path in db_paths:
            if path not in file_atoms:
                await self.db.delete_atom(db_paths[path]['id'])
                deleted += 1

        print(f"    增量迁移: {updated} 更新, {deleted} 删除")
        return updated, deleted
