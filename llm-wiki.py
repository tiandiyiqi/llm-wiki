#!/usr/bin/env python3
"""
LLM Wiki CLI - OKF 知识库管理工具

基于 Open Knowledge Format (OKF) v0.1 规范的知识库管理命令行工具。

Usage:
    llm-wiki <command> [options]

Commands:
    init        初始化知识库目录结构
    export      导出知识库为 OKF Bundle
    import      导入 OKF Bundle 到知识库
    lint        检查 OKF 兼容性
    index       生成目录索引

Examples:
    llm-wiki init ./my-kb
    llm-wiki export ./my-kb --output bundle.tar.gz
    llm-wiki import bundle.tar.gz --output ./my-kb
    llm-wiki lint ./my-kb --okf-check
"""

import argparse
import json
import os
import re
import sys
import tarfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


# OKF Reserved filenames (§3.1)
RESERVED_FILES = {'index.md', 'log.md'}

# OKF Required frontmatter fields (§4.1)
REQUIRED_FIELDS = {'type'}

# OKF Recommended frontmatter fields (§4.1)
RECOMMENDED_FIELDS = ['title', 'description', 'resource', 'tags', 'timestamp']


class SimpleYAMLParser:
    """Minimal YAML parser for OKF frontmatter."""

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        if not text.strip():
            return None

        result: Dict[str, Any] = {}
        lines = text.strip().split('\n')
        current_key: Optional[str] = None
        current_list: Optional[List[str]] = None

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                if current_list and current_key:
                    result[current_key] = current_list
                    current_key = None
                    current_list = None
                continue

            if stripped.startswith('- '):
                if current_key:
                    if current_list is None:
                        current_list = []
                    value = stripped[2:].strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    current_list.append(value)
                continue

            if ':' in line:
                if current_list and current_key:
                    result[current_key] = current_list
                    current_key = None
                    current_list = None

                colon_pos = line.find(':')
                key = line[:colon_pos].strip()
                value = line[colon_pos + 1:].strip()

                if not value:
                    current_key = key
                    current_list = None
                elif value.startswith('[') and value.endswith(']'):
                    items = value[1:-1].split(',')
                    result[key] = [item.strip().strip('"\'') for item in items if item.strip()]
                elif value.lower() in ('true', 'false'):
                    result[key] = value.lower() == 'true'
                elif value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                    result[key] = int(value)
                elif re.match(r'^-?\d+\.?\d*$', value):
                    result[key] = float(value)
                else:
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    result[key] = value

        if current_list and current_key:
            result[current_key] = current_list

        return result if result else None


class OKFValidator:
    """Validates OKF bundle conformance (§9)."""

    def __init__(self):
        self.yaml_parser = SimpleYAMLParser()
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []
        self.concepts: List[Dict] = []

    def validate_bundle(self, bundle_dir: Path) -> Tuple[bool, List, List]:
        self.errors = []
        self.warnings = []
        self.concepts = []

        for md_file in bundle_dir.rglob('*.md'):
            rel_path = md_file.relative_to(bundle_dir)
            if md_file.name in RESERVED_FILES:
                self._validate_reserved_file(md_file, rel_path)
            else:
                self._validate_concept_file(md_file, rel_path)

        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_reserved_file(self, file_path: Path, rel_path: Path):
        content = file_path.read_text(encoding='utf-8')
        if file_path.name == 'index.md':
            if content.startswith('---'):
                if str(rel_path) == 'index.md':
                    try:
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            fm = self.yaml_parser.parse(parts[1])
                            if fm and 'okf_version' in fm:
                                return
                    except:
                        pass
                self.warnings.append((str(rel_path), "index.md typically should not have frontmatter (§6)"))

        if file_path.name == 'log.md':
            if not content.strip():
                self.warnings.append((str(rel_path), "Empty log.md file"))

    def _validate_concept_file(self, file_path: Path, rel_path: Path):
        content = file_path.read_text(encoding='utf-8')
        if not content.startswith('---'):
            self.errors.append((str(rel_path), "Missing YAML frontmatter (§4.1)"))
            return

        try:
            parts = content.split('---', 2)
            if len(parts) < 3:
                self.errors.append((str(rel_path), "Malformed frontmatter - missing closing ---"))
                return

            frontmatter = self.yaml_parser.parse(parts[1])
            if not frontmatter:
                self.errors.append((str(rel_path), "Empty frontmatter"))
                return

            if 'type' not in frontmatter or not frontmatter['type']:
                self.errors.append((str(rel_path), "Missing required 'type' field (§4.1, §9.2)"))
                return

            for field in RECOMMENDED_FIELDS:
                if field not in frontmatter:
                    self.warnings.append((str(rel_path), f"Missing recommended '{field}' field (§4.1)"))

            if 'timestamp' in frontmatter:
                try:
                    ts = frontmatter['timestamp']
                    if isinstance(ts, str):
                        datetime.fromisoformat(ts.replace('Z', '+00:00'))
                except:
                    self.warnings.append((str(rel_path), "timestamp not in ISO 8601 format"))

            self.concepts.append({
                'id': str(rel_path).replace('.md', ''),
                'path': str(rel_path),
                'type': frontmatter.get('type'),
                'title': frontmatter.get('title', rel_path.stem),
                'description': frontmatter.get('description', ''),
                'tags': frontmatter.get('tags', []),
                'frontmatter': frontmatter
            })

        except Exception as e:
            self.errors.append((str(rel_path), f"Parse error: {e}"))


class OKFExporter:
    """Exports knowledge base to OKF bundle."""

    def __init__(self, kb_dir: Path, output_path: Optional[Path] = None):
        self.kb_dir = kb_dir
        self.output_path = output_path or Path(f"{kb_dir.name}-okf-bundle.tar.gz")
        self.validator = OKFValidator()
        self.manifest: Dict = {
            'okf_version': '0.1',
            'export_time': datetime.now().isoformat(),
            'source_dir': str(kb_dir),
            'concepts': [],
            'statistics': {}
        }

    def export(self, validate: bool = True, force: bool = False) -> bool:
        print(f"📦 Exporting OKF bundle from: {self.kb_dir}")

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

    def _create_tarball(self):
        with tarfile.open(self.output_path, 'w:gz') as tar:
            manifest_bytes = json.dumps(self.manifest, indent=2).encode('utf-8')
            manifest_info = tarfile.TarInfo('manifest.json')
            manifest_info.size = len(manifest_bytes)
            manifest_info.mtime = datetime.now().timestamp()
            tar.addfile(manifest_info, BytesIO(manifest_bytes))

            for md_file in self.kb_dir.rglob('*.md'):
                rel_path = md_file.relative_to(self.kb_dir)
                tar.add(md_file, arcname=str(rel_path))

            for support_file in self.kb_dir.rglob('*'):
                if support_file.is_file() and support_file.suffix != '.md':
                    if any(part.startswith('.') for part in support_file.parts):
                        continue
                    rel_path = support_file.relative_to(self.kb_dir)
                    tar.add(support_file, arcname=str(rel_path))


class OKFImporter:
    """Imports OKF bundle into knowledge base."""

    def __init__(self, bundle_path: Path, output_dir: Path):
        self.bundle_path = bundle_path
        self.output_dir = output_dir
        self.manifest: Optional[Dict] = None
        self.imported_files: List[str] = []

    def import_bundle(self, overwrite: bool = False) -> bool:
        print(f"📦 Importing OKF bundle: {self.bundle_path}")

        if not self.bundle_path.exists():
            print(f"❌ Error: Bundle not found: {self.bundle_path}")
            return False

        if not tarfile.is_tarfile(self.bundle_path):
            print(f"❌ Error: Not a valid tar file: {self.bundle_path}")
            return False

        if self.output_dir.exists() and not overwrite:
            if any(self.output_dir.iterdir()):
                print(f"❌ Error: Output directory not empty: {self.output_dir}")
                print("   Use --overwrite to replace existing content")
                return False

        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📦 Extracting to: {self.output_dir}")
        with tarfile.open(self.bundle_path, 'r:gz') as tar:
            try:
                manifest_member = tar.getmember('manifest.json')
                manifest_file = tar.extractfile(manifest_member)
                if manifest_file:
                    self.manifest = json.load(manifest_file)
            except KeyError:
                print("⚠️  Warning: No manifest.json in bundle")
                self.manifest = None

            for member in tar.getmembers():
                if member.name == 'manifest.json':
                    continue
                if member.name.startswith('/') or '..' in member.name:
                    print(f"⚠️  Skipping suspicious path: {member.name}")
                    continue
                tar.extract(member, self.output_dir)
                self.imported_files.append(member.name)

        self._print_summary()
        return True

    def _print_summary(self):
        print(f"\n✅ Import complete!")
        print(f"   Files imported: {len(self.imported_files)}")

        if self.manifest:
            print(f"\n📊 Bundle Info:")
            print(f"   OKF Version: {self.manifest.get('okf_version', 'unknown')}")
            print(f"   Concepts: {self.manifest.get('statistics', {}).get('total_concepts', 0)}")
            types = self.manifest.get('statistics', {}).get('types', {})
            if types:
                print(f"   Types:")
                for t, count in sorted(types.items()):
                    print(f"     - {t}: {count}")
            export_time = self.manifest.get('export_time')
            if export_time:
                print(f"   Original export: {export_time}")

        print(f"\n📁 Output: {self.output_dir}")


class KBInitializer:
    """Initializes knowledge base directory structure."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir

    def init(self) -> bool:
        print(f"📦 Initializing knowledge base: {self.kb_dir}")

        if self.kb_dir.exists() and any(self.kb_dir.iterdir()):
            print(f"❌ Error: Directory not empty: {self.kb_dir}")
            return False

        # Create directory structure
        dirs = [
            'atoms/methods',
            'atoms/facts',
            'atoms/definitions',
            'atoms/opinions',
            'atoms/data',
            'atoms/questions',
            'atoms/references',
            'raw/reference',
            'raw/observations',
            'views'
        ]

        for d in dirs:
            path = self.kb_dir / d
            path.mkdir(parents=True, exist_ok=True)
            print(f"   Created: {d}")

        # Create root index.md
        index_content = """---
okf_version: "0.1"
---

# Knowledge Base Index

This knowledge base follows the Open Knowledge Format (OKF) v0.1 specification.

## Statistics

- Total atoms: 0

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `atoms/methods/` | How-to guides and procedures |
| `atoms/facts/` | Verifiable facts |
| `atoms/definitions/` | Concept definitions |
| `atoms/opinions/` | Subjective opinions |
| `atoms/data/` | Numerical data and statistics |
| `atoms/questions/` | Open questions |
| `atoms/references/` | External references |
| `raw/` | Source materials |
| `views/` | Generated views and visualizations |

## Quick Start

1. Add source materials to `raw/`
2. Extract knowledge atoms to `atoms/`
3. Run `llm-wiki lint` to validate
4. Run `llm-wiki export` to create bundle
"""

        (self.kb_dir / 'index.md').write_text(index_content)
        print(f"   Created: index.md")

        # Create log.md
        log_content = f"""# Knowledge Base Log

## {datetime.now().strftime('%Y-%m-%d')}

* **Initialization**: Created knowledge base directory structure.
"""

        (self.kb_dir / 'log.md').write_text(log_content)
        print(f"   Created: log.md")

        print(f"\n✅ Knowledge base initialized!")
        print(f"   Path: {self.kb_dir}")
        print(f"\nNext steps:")
        print(f"   1. Add source materials to raw/")
        print(f"   2. Run 'llm-wiki lint' to validate")
        print(f"   3. Run 'llm-wiki export' to create bundle")

        return True


class IndexGenerator:
    """Generates index.md files for directories."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()

    def generate(self, directory: Optional[Path] = None) -> bool:
        target_dir = directory or self.kb_dir
        print(f"📦 Generating index.md for: {target_dir}")

        concepts: List[Dict] = []

        for md_file in target_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue

            rel_path = md_file.relative_to(target_dir)
            content = md_file.read_text(encoding='utf-8')

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    fm = self.yaml_parser.parse(parts[1])
                    if fm:
                        concepts.append({
                            'path': str(rel_path),
                            'type': fm.get('type', 'Unknown'),
                            'title': fm.get('title', rel_path.stem),
                            'description': fm.get('description', 'No description')
                        })

        if not concepts:
            print("   No concepts found in directory")
            return False

        # Generate index
        lines = [f"# Knowledge Concepts Index\n\n"]
        lines.append(f"## Statistics\n\n")
        lines.append(f"- Total concepts: {len(concepts)}\n\n")

        by_type: Dict[str, List[Dict]] = {}
        for c in concepts:
            t = c['type']
            by_type[t] = by_type.get(t, []) + [c]

        lines.append("## Concepts\n\n")
        for type_name, type_concepts in sorted(by_type.items()):
            lines.append(f"### {type_name}\n\n")
            for c in sorted(type_concepts, key=lambda x: x['title']):
                lines.append(f"* [{c['title']}](/{c['path']}) - {c['description']}\n")

        index_path = target_dir / 'index.md'
        index_path.write_text(''.join(lines))
        print(f"   Generated: {index_path}")
        print(f"   Concepts: {len(concepts)}")

        return True


def cmd_init(args):
    kb_dir = Path(args.knowledge_base)
    initializer = KBInitializer(kb_dir)
    success = initializer.init()
    sys.exit(0 if success else 1)


def cmd_export(args):
    kb_dir = Path(args.knowledge_base)
    output_path = Path(args.output) if args.output else None

    exporter = OKFExporter(kb_dir, output_path)
    success = exporter.export(
        validate=args.validate and not args.no_validate,
        force=args.force
    )
    sys.exit(0 if success else 1)


def cmd_import(args):
    bundle_path = Path(args.bundle)
    output_dir = Path(args.output) if args.output else Path('.')

    importer = OKFImporter(bundle_path, output_dir)
    success = importer.import_bundle(overwrite=args.overwrite)
    sys.exit(0 if success else 1)


def cmd_lint(args):
    kb_dir = Path(args.knowledge_base)
    validator = OKFValidator()

    print(f"📦 Validating OKF conformance: {kb_dir}")

    is_valid, errors, warnings = validator.validate_bundle(kb_dir)

    print(f"\n📊 Results:")
    print(f"   Concepts: {len(validator.concepts)}")
    print(f"   Valid: {'✅ Yes' if is_valid else '❌ No'}")

    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for file_path, error in errors:
            print(f"   {file_path}: {error}")

    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for file_path, warning in warnings[:10]:
            print(f"   {file_path}: {warning}")
        if len(warnings) > 10:
            print(f"   ... and {len(warnings) - 10} more")

    if args.okf_check:
        print(f"\n📋 OKF v0.1 Conformance Check:")
        print(f"   ✅ All .md files have frontmatter: {len(errors) == 0 or all('frontmatter' not in e[1] for e in errors)}")
        print(f"   ✅ All frontmatter have 'type': {all('type' in e[1] for e in errors) == False}")
        print(f"   ✅ Reserved files valid: {all('index.md' not in e[0] and 'log.md' not in e[0] for e in errors)}")

    sys.exit(0 if is_valid else 1)


def cmd_index(args):
    kb_dir = Path(args.knowledge_base)
    directory = Path(args.directory) if args.directory else None

    generator = IndexGenerator(kb_dir)
    success = generator.generate(directory)
    sys.exit(0 if success else 1)


def main():
    parser = argparse.ArgumentParser(
        prog='llm-wiki',
        description='OKF 知识库管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # init command
    init_parser = subparsers.add_parser('init', help='初始化知识库')
    init_parser.add_argument('knowledge_base', type=Path, help='知识库目录路径')
    init_parser.set_defaults(func=cmd_init)

    # export command
    export_parser = subparsers.add_parser('export', help='导出为 OKF Bundle')
    export_parser.add_argument('knowledge_base', type=Path, help='知识库目录路径')
    export_parser.add_argument('--output', '-o', type=Path, help='输出文件路径')
    export_parser.add_argument('--validate', '-v', action='store_true', default=True, help='验证 OKF 符合性')
    export_parser.add_argument('--no-validate', action='store_true', help='跳过验证')
    export_parser.add_argument('--force', '-f', action='store_true', help='强制导出')
    export_parser.set_defaults(func=cmd_export)

    # import command
    import_parser = subparsers.add_parser('import', help='导入 OKF Bundle')
    import_parser.add_argument('bundle', type=Path, help='Bundle 文件路径')
    import_parser.add_argument('--output', '-o', type=Path, default=Path('.'), help='输出目录')
    import_parser.add_argument('--overwrite', action='store_true', help='覆盖现有文件')
    import_parser.set_defaults(func=cmd_import)

    # lint command
    lint_parser = subparsers.add_parser('lint', help='OKF 兼容性检查')
    lint_parser.add_argument('knowledge_base', type=Path, help='知识库目录路径')
    lint_parser.add_argument('--okf-check', action='store_true', help='显示 OKF 规范检查详情')
    lint_parser.set_defaults(func=cmd_lint)

    # index command
    index_parser = subparsers.add_parser('index', help='生成目录索引')
    index_parser.add_argument('knowledge_base', type=Path, help='知识库目录路径')
    index_parser.add_argument('--directory', '-d', type=Path, help='指定目录')
    index_parser.set_defaults(func=cmd_index)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()