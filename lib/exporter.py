"""Exports knowledge base to OKF bundle.

Supports:
- Standalone knowledge base export
- Child knowledge base independent export
- Parent knowledge base export with optional children
"""

import json
import tarfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .validator import OKFValidator


class OKFExporter:
    """Exports knowledge base to OKF bundle."""

    def __init__(self, kb_dir: Path, output_path: Optional[Path] = None, include_children: bool = False):
        self.kb_dir = kb_dir
        self.output_path = output_path or Path(f"{kb_dir.name}-okf-bundle.tar.gz")
        self.include_children = include_children
        self.validator = OKFValidator()
        self.manifest: Dict = {
            'okf_version': '0.1',
            'export_time': datetime.now().isoformat(),
            'source_dir': str(kb_dir),
            'kb_type': 'standalone',
            'children': [],
            'concepts': [],
            'statistics': {}
        }

    def _detect_kb_type(self) -> str:
        """检测知识库类型."""
        meta_path = self.kb_dir / '.kb-meta.json'
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                return meta.get('kb_type', 'standalone')
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        return 'standalone'

    def _get_children_paths(self) -> List[Tuple[str, Path]]:
        """获取子知识库路径列表."""
        children = []
        meta_path = self.kb_dir / '.kb-meta.json'
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                for child_name, rel_path in meta.get('children_paths', {}).items():
                    child_full_path = self.kb_dir / rel_path.rstrip('/')
                    if child_full_path.exists():
                        children.append((child_name, child_full_path))
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        return children

    def export(self, validate: bool = True, force: bool = False) -> bool:
        kb_type = self._detect_kb_type()
        self.manifest['kb_type'] = kb_type

        print(f"📦 Exporting OKF bundle from: {self.kb_dir}")
        print(f"   Type: {kb_type}")

        if kb_type == 'parent' and self.include_children:
            children = self._get_children_paths()
            self.manifest['children'] = [name for name, _ in children]
            print(f"   Including children: {len(children)}")
            for name, _ in children:
                print(f"      - {name}")

        if validate:
            is_valid, errors, warnings = self.validator.validate_bundle(self.kb_dir)
            print(f"\n📊 Validation Results:")
            print(f"   Concepts: {len(self.validator.concepts)}")
            print(f"   Errors: {len(errors)}")
            print(f"   Warnings: {len(warnings)}")

            if errors:
                print("\n❌ Conformance Errors:")
                for file_path, error in errors[:20]:
                    print(f"   {file_path}: {error}")
                if len(errors) > 20:
                    print(f"   ... and {len(errors) - 20} more")
                if not force:
                    print("\nUse --force to export anyway.")
                    return False

            if warnings:
                print("\n⚠️  Warnings:")
                for file_path, warning in warnings[:10]:
                    print(f"   {file_path}: {warning}")
                if len(warnings) > 10:
                    print(f"   ... and {len(warnings) - 10} more")

        self.manifest['concepts'] = self.validator.concepts
        self.manifest['statistics'] = {
            'total_concepts': len(self.validator.concepts),
            'types': self._count_types(),
            'files_processed': len(list(self.kb_dir.rglob('*.md')))
        }

        print(f"\n📦 Creating bundle: {self.output_path}")
        self._create_tarball()

        size_kb = self.output_path.stat().st_size / 1024
        print(f"\n✅ Export complete!")
        print(f"   Bundle: {self.output_path}")
        print(f"   Concepts: {len(self.validator.concepts)}")
        print(f"   Size: {size_kb:.1f} KB")

        return True

    def _count_types(self) -> Dict[str, int]:
        types: Dict[str, int] = {}
        for concept in self.validator.concepts:
            t = concept['type']
            types[t] = types.get(t, 0) + 1
        return types

    def _create_tarball(self) -> None:
        with tarfile.open(self.output_path, 'w:gz') as tar:
            # Add manifest
            manifest_bytes = json.dumps(self.manifest, indent=2).encode('utf-8')
            manifest_info = tarfile.TarInfo('manifest.json')
            manifest_info.size = len(manifest_bytes)
            manifest_info.mtime = datetime.now().timestamp()
            tar.addfile(manifest_info, BytesIO(manifest_bytes))

            # Add .kb-meta.json if exists
            meta_path = self.kb_dir / '.kb-meta.json'
            if meta_path.exists():
                tar.add(meta_path, arcname='.kb-meta.json')

            # Add all md files from parent
            for md_file in self.kb_dir.rglob('*.md'):
                rel_path = md_file.relative_to(self.kb_dir)
                tar.add(md_file, arcname=str(rel_path))

            # Add support files
            for support_file in self.kb_dir.rglob('*'):
                if support_file.is_file() and support_file.suffix != '.md':
                    if any(part.startswith('.') for part in support_file.parts):
                        continue
                    rel_path = support_file.relative_to(self.kb_dir)
                    tar.add(support_file, arcname=str(rel_path))

            # Add children if include_children is True
            if self.include_children and self.manifest['kb_type'] == 'parent':
                children = self._get_children_paths()
                for child_name, child_path in children:
                    # Add child's .kb-meta.json
                    child_meta = child_path / '.kb-meta.json'
                    if child_meta.exists():
                        tar.add(child_meta, arcname=f"{child_name}/.kb-meta.json")

                    # Add child's md files
                    for md_file in child_path.rglob('*.md'):
                        rel_path = md_file.relative_to(self.kb_dir)
                        tar.add(md_file, arcname=str(rel_path))

                    # Add child's support files
                    for support_file in child_path.rglob('*'):
                        if support_file.is_file() and support_file.suffix != '.md':
                            if any(part.startswith('.') for part in support_file.parts):
                                continue
                            rel_path = support_file.relative_to(self.kb_dir)
                            tar.add(support_file, arcname=str(rel_path))