"""批量操作模块，支持批量摄入、导出、打标签、迁移、删除."""

import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import RESERVED_FILES, TYPE_DIRS
from .yaml_parser import SimpleYAMLParser
from .ingestor import KnowledgeIngestor


class BatchOperations:
    """批量操作知识原子."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()
        self.ingestor = KnowledgeIngestor(kb_dir)

    def batch_ingest(self, source_dir: Path, pattern: str = '*',
                     recursive: bool = True, dry_run: bool = False) -> Tuple[int, int]:
        """批量摄入目录下的文件.

        Args:
            source_dir: 源目录
            pattern: 文件匹配模式（如 '*.md', '*.pdf'）
            recursive: 是否递归子目录
            dry_run: 仅预览不执行

        Returns:
            (成功数, 失败数)
        """
        if not source_dir.exists() or not source_dir.is_dir():
            print(f"❌ 目录不存在: {source_dir}")
            return 0, 0

        # 收集文件
        if recursive:
            files = sorted(source_dir.rglob(pattern))
        else:
            files = sorted(source_dir.glob(pattern))

        # 过滤支持的格式
        supported = MultiFormatParser_supported_exts()
        files = [f for f in files if f.is_file() and f.suffix.lower() in supported]

        if not files:
            print(f"⚠️  未找到匹配文件: {source_dir}/{pattern}")
            return 0, 0

        print(f"📦 批量摄入: {len(files)} 个文件")
        if dry_run:
            print("（预览模式，不实际执行）")
            for f in files:
                print(f"   - {f}")
            return len(files), 0

        success = 0
        failed = 0
        for i, f in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] {f.name}")
            try:
                if self.ingestor.ingest(f):
                    success += 1
                else:
                    failed += 1
            except (IOError, OSError, UnicodeDecodeError) as e:
                print(f"   ❌ 失败: {e}")
                failed += 1

        print(f"\n📊 批量摄入完成: 成功 {success}, 失败 {failed}")
        return success, failed

    def batch_export(self, output_dir: Path, by_type: Optional[str] = None,
                     by_tag: Optional[str] = None, by_status: Optional[str] = None,
                     dry_run: bool = False) -> int:
        """按条件批量导出原子到目录.

        Args:
            output_dir: 输出目录
            by_type: 按类型过滤
            by_tag: 按标签过滤
            by_status: 按状态过滤
            dry_run: 仅预览

        Returns:
            导出文件数
        """
        atoms = self._load_atoms(by_type, by_tag, by_status)
        if not atoms:
            print("⚠️  未找到匹配的原子")
            return 0

        print(f"📤 批量导出: {len(atoms)} 个原子")
        if dry_run:
            for a in atoms:
                print(f"   - [{a['type']}] {a['title']} ({a['path']})")
            return len(atoms)

        output_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for atom in atoms:
            src = self.kb_dir / atom['path']
            if src.exists():
                dst = output_dir / atom['path'].replace('/', '_')
                shutil.copy2(src, dst)
                count += 1
                print(f"   ✅ {atom['path']} → {dst.name}")

        print(f"\n📊 导出完成: {count} 个文件到 {output_dir}")
        return count

    def batch_tag(self, add_tags: Optional[List[str]] = None,
                  remove_tags: Optional[List[str]] = None,
                  by_type: Optional[str] = None, by_tag: Optional[str] = None,
                  dry_run: bool = False) -> int:
        """批量添加或移除标签.

        Args:
            add_tags: 要添加的标签列表
            remove_tags: 要移除的标签列表
            by_type: 按类型过滤
            by_tag: 按标签过滤
            dry_run: 仅预览

        Returns:
            修改的原子数
        """
        atoms = self._load_atoms(by_type, by_tag)
        if not atoms:
            print("⚠️  未找到匹配的原子")
            return 0

        print(f"🏷️  批量打标签: {len(atoms)} 个原子")
        if dry_run:
            print(f"   添加: {add_tags or []}")
            print(f"   移除: {remove_tags or []}")
            for a in atoms:
                print(f"   - [{a['type']}] {a['title']}")
            return len(atoms)

        count = 0
        for atom in atoms:
            file_path = self.kb_dir / atom['path']
            if not file_path.exists():
                continue
            if self._modify_tags(file_path, add_tags, remove_tags):
                count += 1
                print(f"   ✅ {atom['path']}")

        print(f"\n📊 标签更新完成: {count} 个原子")
        return count

    def batch_move(self, target_type: str, by_type: Optional[str] = None,
                   by_tag: Optional[str] = None, dry_run: bool = False) -> int:
        """批量迁移原子类型（移动到对应目录）.

        Args:
            target_type: 目标类型
            by_type: 源类型过滤
            by_tag: 标签过滤
            dry_run: 仅预览

        Returns:
            迁移的原子数
        """
        if target_type not in TYPE_DIRS:
            print(f"❌ 未知类型: {target_type}")
            return 0

        atoms = self._load_atoms(by_type, by_tag)
        if not atoms:
            print("⚠️  未找到匹配的原子")
            return 0

        target_dir = TYPE_DIRS[target_type]
        print(f"📦 批量迁移到 {target_type} ({target_dir}/): {len(atoms)} 个原子")
        if dry_run:
            for a in atoms:
                print(f"   - {a['path']} → atoms/{target_dir}/")
            return len(atoms)

        count = 0
        for atom in atoms:
            src = self.kb_dir / atom['path']
            if not src.exists():
                continue
            # 目标路径
            dst_dir = self.kb_dir / 'atoms' / target_dir
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / src.name
            if src == dst:
                continue
            # 移动文件
            shutil.move(str(src), str(dst))
            # 更新 frontmatter type 字段
            self._update_frontmatter_type(dst, target_type)
            count += 1
            print(f"   ✅ {atom['path']} → atoms/{target_dir}/{src.name}")

        print(f"\n📊 迁移完成: {count} 个原子")
        return count

    def batch_delete(self, by_type: Optional[str] = None, by_tag: Optional[str] = None,
                     by_status: Optional[str] = None, dry_run: bool = True) -> int:
        """批量删除原子（默认 dry_run=True 安全模式）.

        Args:
            by_type: 按类型过滤
            by_tag: 按标签过滤
            by_status: 按状态过滤
            dry_run: 仅预览（默认 True）

        Returns:
            删除的原子数
        """
        atoms = self._load_atoms(by_type, by_tag, by_status)
        if not atoms:
            print("⚠️  未找到匹配的原子")
            return 0

        print(f"🗑️  批量删除: {len(atoms)} 个原子")
        if dry_run:
            print("   ⚠️  预览模式（加 --force 实际执行）")
            for a in atoms:
                print(f"   - [{a['type']}] {a['title']} ({a['path']})")
            return len(atoms)

        count = 0
        for atom in atoms:
            file_path = self.kb_dir / atom['path']
            if file_path.exists():
                file_path.unlink()
                count += 1
                print(f"   🗑️  {atom['path']}")

        print(f"\n📊 删除完成: {count} 个原子")
        return count

    def _load_atoms(self, by_type: Optional[str] = None,
                    by_tag: Optional[str] = None,
                    by_status: Optional[str] = None) -> List[Dict]:
        """加载并过滤原子列表."""
        atoms = []
        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue
            content = md_file.read_text(encoding='utf-8', errors='ignore')
            if not content.startswith('---'):
                continue
            parts = content.split('---', 2)
            if len(parts) < 3:
                continue
            fm = self.yaml_parser.parse(parts[1])
            if not fm:
                continue

            atom_type = fm.get('type', 'Unknown')
            tags = fm.get('tags', [])
            if not isinstance(tags, list):
                tags = [tags] if tags else []
            status = fm.get('status', 'published')

            # 过滤
            if by_type and atom_type != by_type:
                continue
            if by_tag and by_tag.lower() not in [t.lower() for t in tags]:
                continue
            if by_status and status != by_status:
                continue

            atoms.append({
                'path': str(md_file.relative_to(self.kb_dir)),
                'type': atom_type,
                'title': fm.get('title', md_file.stem),
                'tags': tags,
                'status': status,
                'frontmatter': fm,
            })
        return atoms

    def _modify_tags(self, file_path: Path, add_tags: Optional[List[str]],
                     remove_tags: Optional[List[str]]) -> bool:
        """修改原子的标签."""
        content = file_path.read_text(encoding='utf-8')
        if not content.startswith('---'):
            return False
        parts = content.split('---', 2)
        if len(parts) < 3:
            return False
        fm = self.yaml_parser.parse(parts[1])
        if not fm:
            return False

        tags = fm.get('tags', [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []

        # 添加标签
        if add_tags:
            for t in add_tags:
                if t not in tags:
                    tags.append(t)

        # 移除标签
        if remove_tags:
            tags = [t for t in tags if t not in remove_tags]

        fm['tags'] = tags
        yaml_str = self.yaml_parser.dump(fm)
        new_content = f"---\n{yaml_str}\n---\n{parts[2]}"
        file_path.write_text(new_content, encoding='utf-8')
        return True

    def _update_frontmatter_type(self, file_path: Path, new_type: str) -> bool:
        """更新原子的 type 字段."""
        content = file_path.read_text(encoding='utf-8')
        if not content.startswith('---'):
            return False
        parts = content.split('---', 2)
        if len(parts) < 3:
            return False
        fm = self.yaml_parser.parse(parts[1])
        if not fm:
            return False
        fm['type'] = new_type
        yaml_str = self.yaml_parser.dump(fm)
        new_content = f"---\n{yaml_str}\n---\n{parts[2]}"
        file_path.write_text(new_content, encoding='utf-8')
        return True


def MultiFormatParser_supported_exts() -> set:
    """返回支持的文件扩展名集合."""
    from .multi_format_parser import MultiFormatParser
    return MultiFormatParser.SUPPORTED_EXTENSIONS
