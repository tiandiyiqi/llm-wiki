#!/usr/bin/env python3
"""
LLM Wiki CLI - OKF 知识库管理工具

基于 Open Knowledge Format (OKF) v0.1 规范的知识库管理命令行工具。

Usage:
    llm-wiki <command> [options]

Commands:
    init        初始化知识库目录结构
    ingest      摄入资料提取知识原子
    query       搜索查询知识（支持语义搜索）
    embed       生成向量嵌入（需要 chromadb）
    lint        检查 OKF 兼容性
    index       生成目录索引
    export      导出知识库为 OKF Bundle
    import      导入 OKF Bundle 到知识库
    visualize   生成知识图谱可视化 HTML

Examples:
    llm-wiki init ./my-kb
    llm-wiki ingest ./my-kb raw/doc.md
    llm-wiki embed ./my-kb                    # 生成向量嵌入
    llm-wiki query ./my-kb "installation"     # 关键词搜索
    llm-wiki query ./my-kb "如何部署" --semantic  # 语义搜索
    llm-wiki lint ./my-kb --okf-check
    llm-wiki visualize ./my-kb --output views/graph.html
    llm-wiki export ./my-kb --output bundle.tar.gz
"""

import argparse
import json
import os
import re
import sys
import tarfile
import html
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Optional: semantic search dependencies
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


# OKF Reserved filenames (§3.1)
RESERVED_FILES = {'index.md', 'log.md'}

# OKF Required frontmatter fields (§4.1)
REQUIRED_FIELDS = {'type'}

# OKF Recommended frontmatter fields (§4.1)
RECOMMENDED_FIELDS = ['title', 'description', 'resource', 'tags', 'timestamp']

# Knowledge types mapping
TYPE_DIRS = {
    'fact': 'facts',
    'opinion': 'opinions',
    'definition': 'definitions',
    'method': 'methods',
    'data': 'data',
    'question': 'questions',
    'reference': 'references'
}


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

    def dump(self, data: Dict[str, Any]) -> str:
        """Convert dict to YAML string."""
        lines = []
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, bool):
                lines.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, (int, float)):
                lines.append(f"{key}: {value}")
            else:
                # Escape quotes in string values
                escaped = str(value).replace('"', '\\"')
                lines.append(f"{key}: \"{escaped}\"")
        return '\n'.join(lines)


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

            # Extract body content
            body = parts[2].strip() if len(parts) >= 3 else ''

            # Extract links for graph
            links = self._extract_links(body)

            self.concepts.append({
                'id': str(rel_path).replace('.md', ''),
                'path': str(rel_path),
                'type': frontmatter.get('type'),
                'title': frontmatter.get('title', rel_path.stem),
                'description': frontmatter.get('description', ''),
                'tags': frontmatter.get('tags', []),
                'frontmatter': frontmatter,
                'body': body,
                'links': links
            })

        except Exception as e:
            self.errors.append((str(rel_path), f"Parse error: {e}"))

    def _extract_links(self, body: str) -> List[str]:
        """Extract markdown links from body."""
        # Match [[link]] and [text](link) formats
        wiki_links = re.findall(r'\[\[([^\]]+)\]\]', body)
        md_links = re.findall(r'\]\(([^\)]+)\)', body)

        all_links = []
        for link in wiki_links:
            all_links.append(link)
        for link in md_links:
            if link.startswith('/') or link.startswith('./') or not link.startswith('http'):
                all_links.append(link)

        return all_links


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
2. Run `llm-wiki ingest` to extract atoms
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
        print(f"   2. Run 'llm-wiki ingest' to extract atoms")
        print(f"   3. Run 'llm-wiki lint' to validate")

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


class KnowledgeIngestor:
    """Ingests source materials and extracts knowledge atoms."""

    def __init__(self, kb_dir: Path, source_path: Path):
        self.kb_dir = kb_dir
        self.source_path = source_path
        self.yaml_parser = SimpleYAMLParser()

    def ingest(self, auto_detect_type: bool = True, default_type: str = 'method') -> bool:
        print(f"📦 Ingesting source: {self.source_path}")
        print(f"   Knowledge base: {self.kb_dir}")

        # Check source exists
        if not self.source_path.exists():
            print(f"❌ Error: Source not found: {self.source_path}")
            return False

        # Read source content
        try:
            content = self.source_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"❌ Error reading source: {e}")
            return False

        # Detect source type
        source_type = self._detect_source_type()
        print(f"   Source type: {source_type}")

        # Extract title from first heading or filename
        title = self._extract_title(content)
        print(f"   Title: {title}")

        # Extract description from first paragraph
        description = self._extract_description(content)

        # Extract keywords/tags
        tags = self._extract_tags(content)

        # Determine atom type
        atom_type = self._determine_type(content, auto_detect_type, default_type)
        print(f"   Atom type: {atom_type}")

        # Generate atom_id
        atom_id = self._generate_atom_id(title)

        # Determine target directory
        target_dir = TYPE_DIRS.get(atom_type, 'methods')
        target_path = self.kb_dir / 'atoms' / target_dir / f"{atom_id}.md"

        # Create atom file
        atom_content = self._create_atom_content(
            title=title,
            description=description,
            atom_type=atom_type,
            tags=tags,
            source_path=self.source_path,
            source_type=source_type,
            original_content=content
        )

        # Write atom
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(atom_content)

        print(f"\n✅ Atom created: {target_path}")
        print(f"   atom_id: {atom_id}")

        # Update log
        self._update_log(title, atom_id, atom_type)

        return True

    def _detect_source_type(self) -> str:
        """Detect source type from file/path."""
        path_str = str(self.source_path).lower()

        if 'official' in path_str or 'docs' in path_str:
            return 'official'
        if 'blog' in path_str:
            return 'blog'
        if self.source_path.suffix == '.pdf':
            return 'document'
        if 'README' in self.source_path.name:
            return 'official'

        return 'user'

    def _extract_title(self, content: str) -> str:
        """Extract title from content."""
        # Try first heading
        heading_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if heading_match:
            return heading_match.group(1).strip()

        # Try title in frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                fm = self.yaml_parser.parse(parts[1])
                if fm and 'title' in fm:
                    return fm['title']

        # Use filename
        return self.source_path.stem

    def _extract_description(self, content: str) -> str:
        """Extract description from first meaningful paragraph."""
        # Remove frontmatter if present
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]

        # Remove headings and code blocks
        lines = content.split('\n')
        clean_lines = []
        in_code_block = False

        for line in lines:
            if line.startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if line.startswith('#'):
                continue
            if line.strip():
                clean_lines.append(line.strip())

        # Get first meaningful paragraph
        if clean_lines:
            first_para = ' '.join(clean_lines[:5])  # First 5 non-empty lines
            # Limit to ~100 chars
            if len(first_para) > 100:
                first_para = first_para[:97] + '...'
            return first_para

        return 'No description available'

    def _extract_tags(self, content: str) -> List[str]:
        """Extract keywords/tags from content."""
        tags = []

        # Common tech keywords
        tech_keywords = [
            'installation', 'config', 'setup', 'deploy', 'security',
            'ubuntu', 'linux', 'windows', 'macos', 'docker', 'kubernetes',
            'python', 'javascript', 'golang', 'rust', 'java',
            'database', 'api', 'rest', 'graphql', 'web',
            'nextcloud', 'apache', 'nginx', 'mysql', 'postgresql'
        ]

        content_lower = content.lower()
        for keyword in tech_keywords:
            if keyword in content_lower:
                tags.append(keyword)

        # Limit tags
        return tags[:5] if tags else ['general']

    def _determine_type(self, content: str, auto_detect: bool, default_type: str) -> str:
        """Determine knowledge atom type."""
        if not auto_detect:
            return default_type

        content_lower = content.lower()

        # Detect method (how-to, steps)
        if any(word in content_lower for word in ['步骤', 'step', 'how to', '安装', 'install', '配置', 'configure', 'setup']):
            return 'method'

        # Detect fact (statements, requirements)
        if any(word in content_lower for word in ['要求', 'requirement', '支持', 'support', '版本', 'version', '限制', 'limit']):
            return 'fact'

        # Detect definition
        if any(word in content_lower for word in ['定义', 'definition', '是什么', '什么是', '概念', 'concept']):
            return 'definition'

        # Detect data
        if any(word in content_lower for word in ['统计', 'statistics', '数据', 'data', '性能', 'performance', '指标', 'metric']):
            return 'data'

        return default_type

    def _generate_atom_id(self, title: str) -> str:
        """Generate atom_id from title."""
        # Convert to lowercase, replace spaces with hyphens
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug)

        # Add timestamp suffix for uniqueness
        timestamp = datetime.now().strftime('%Y%m%d%H%M')

        return f"{slug}-{timestamp}"

    def _create_atom_content(
        self,
        title: str,
        description: str,
        atom_type: str,
        tags: List[str],
        source_path: Path,
        source_type: str,
        original_content: str
    ) -> str:
        """Create atom markdown content."""

        # Build frontmatter
        frontmatter = {
            'type': atom_type,
            'title': title,
            'description': description,
            'resource': str(source_path),
            'tags': tags,
            'timestamp': datetime.now().isoformat(),
            'source': str(source_path.relative_to(self.kb_dir) if source_path.is_relative_to(self.kb_dir) else source_path),
            'source_type': source_type
        }

        # Build body
        body_parts = [f"# {title}\n\n"]
        body_parts.append(f"## 概述\n\n{description}\n\n")

        # Extract main content sections
        if original_content.startswith('---'):
            parts = original_content.split('---', 2)
            if len(parts) >= 3:
                main_content = parts[2]
                # Clean and format
                body_parts.append("## 详细内容\n\n")
                body_parts.append(main_content.strip())
                body_parts.append("\n\n")

        # Add citations section
        body_parts.append("# Citations\n\n")
        body_parts.append(f"[1] [{source_path.name}]({source_path})\n")

        # Combine
        yaml_str = self.yaml_parser.dump(frontmatter)

        return f"---\n{yaml_str}\n---\n{''.join(body_parts)}"

    def _update_log(self, title: str, atom_id: str, atom_type: str):
        """Update log.md with new atom."""
        log_path = self.kb_dir / 'log.md'

        if log_path.exists():
            log_content = log_path.read_text(encoding='utf-8')
        else:
            log_content = "# Knowledge Base Log\n\n"

        # Add entry
        today = datetime.now().strftime('%Y-%m-%d')
        new_entry = f"\n## {today}\n\n* **Ingest**: Added [{title}](atoms/{TYPE_DIRS.get(atom_type, 'methods')}/{atom_id}.md) ({atom_type})\n"

        # Check if today's section exists
        if f"## {today}" in log_content:
            # Append to existing section
            log_content = log_content.replace(f"## {today}\n", f"## {today}\n{new_entry.strip()}\n")
        else:
            log_content += new_entry

        log_path.write_text(log_content)


class KnowledgeQuerier:
    """Searches and queries knowledge atoms."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()
        self.concepts: List[Dict] = []

    def query(self, query_str: str, limit: int = 10, by_type: Optional[str] = None) -> bool:
        print(f"🔍 Querying: '{query_str}'")
        print(f"   Knowledge base: {self.kb_dir}")

        # Load all concepts
        self._load_concepts()

        if not self.concepts:
            print("   No concepts found in knowledge base")
            return False

        print(f"   Total concepts: {len(self.concepts)}")

        # Search
        results = self._search(query_str, by_type)

        # Limit results
        results = results[:limit]

        if not results:
            print(f"\n   No results found for '{query_str}'")
            return True

        # Display results
        print(f"\n📋 Results ({len(results)}):")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. [{result['type']}] {result['title']}")
            print(f"   Path: {result['path']}")
            print(f"   {result['description'][:80]}...")
            if result['tags']:
                print(f"   Tags: {', '.join(result['tags'])}")

        return True

    def _load_concepts(self):
        """Load all concepts from knowledge base."""
        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue

            content = md_file.read_text(encoding='utf-8')

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    fm = self.yaml_parser.parse(parts[1])
                    if fm:
                        body = parts[2] if len(parts) >= 3 else ''
                        self.concepts.append({
                            'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
                            'path': str(md_file.relative_to(self.kb_dir)),
                            'type': fm.get('type', 'Unknown'),
                            'title': fm.get('title', md_file.stem),
                            'description': fm.get('description', ''),
                            'tags': fm.get('tags', []),
                            'frontmatter': fm,
                            'body': body
                        })

    def _search(self, query_str: str, by_type: Optional[str] = None) -> List[Dict]:
        """Search concepts by query string."""
        query_lower = query_str.lower()
        results = []

        for concept in self.concepts:
            # Filter by type if specified
            if by_type and concept['type'] != by_type:
                continue

            # Calculate relevance score
            score = 0

            # Title match (highest priority)
            if query_lower in concept['title'].lower():
                score += 100

            # Description match
            if query_lower in concept['description'].lower():
                score += 50

            # Tags match
            for tag in concept['tags']:
                if query_lower in tag.lower():
                    score += 30

            # Body match
            if query_lower in concept['body'].lower():
                score += 10

            # Type match
            if query_lower == concept['type'].lower():
                score += 20

            if score > 0:
                results.append({
                    **concept,
                    'score': score,
                    'match_type': 'keyword'
                })

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        return results


class SemanticSearchEngine:
    """Semantic search using ChromaDB and sentence-transformers."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()
        self.chroma_dir = kb_dir / '.chroma'
        self.collection_name = 'knowledge_atoms'
        self.model = None
        self.collection = None
        self.concepts: List[Dict] = []

    def is_available(self) -> bool:
        """Check if semantic search dependencies are available."""
        return CHROMA_AVAILABLE and EMBEDDINGS_AVAILABLE

    def check_dependencies(self) -> Tuple[bool, str]:
        """Check and report dependency status."""
        missing = []
        if not CHROMA_AVAILABLE:
            missing.append('chromadb')
        if not EMBEDDINGS_AVAILABLE:
            missing.append('sentence-transformers')

        if missing:
            return False, f"Missing dependencies: {', '.join(missing)}. Install with: pip install {' '.join(missing)}"
        return True, "All dependencies available"

    def initialize(self) -> bool:
        """Initialize the embedding model and ChromaDB."""
        if not self.is_available():
            return False

        try:
            # Initialize embedding model (download if needed)
            print("   Loading embedding model (first run may take a while)...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')

            # Initialize ChromaDB
            self.chroma_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.chroma_dir))

            # Get or create collection
            self.collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            return True
        except Exception as e:
            print(f"   ❌ Error initializing semantic search: {e}")
            return False

    def embed_all(self) -> bool:
        """Generate embeddings for all concepts in the knowledge base."""
        available, msg = self.check_dependencies()
        if not available:
            print(f"❌ {msg}")
            return False

        print(f"📊 Generating embeddings for: {self.kb_dir}")

        # Load all concepts
        self._load_concepts()

        if not self.concepts:
            print("   No concepts found in knowledge base")
            return False

        print(f"   Concepts to embed: {len(self.concepts)}")

        # Initialize
        if not self.initialize():
            return False

        # Prepare documents for embedding
        ids = []
        documents = []
        metadatas = []

        for concept in self.concepts:
            # Create document text for embedding
            doc_text = self._create_embedding_text(concept)
            ids.append(concept['id'])
            documents.append(doc_text)
            metadatas.append({
                'type': concept['type'],
                'title': concept['title'],
                'path': concept['path']
            })

        # Generate embeddings
        print("   Generating embeddings...")
        embeddings = self.model.encode(documents, show_progress_bar=True)

        # Upsert to ChromaDB
        print("   Storing in ChromaDB...")
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=documents,
            metadatas=metadatas
        )

        print(f"\n✅ Embeddings generated for {len(self.concepts)} concepts")
        print(f"   Stored in: {self.chroma_dir}")

        return True

    def search(self, query_str: str, limit: int = 10, by_type: Optional[str] = None) -> List[Dict]:
        """Perform semantic search."""
        if not self.is_available():
            return []

        # Initialize if needed
        if self.collection is None:
            if not self.initialize():
                return []

        # Check if collection has data
        if self.collection.count() == 0:
            print("   ⚠️  No embeddings found. Run 'llm-wiki embed' first.")
            return []

        # Generate query embedding
        query_embedding = self.model.encode([query_str])[0].tolist()

        # Build where filter
        where_filter = None
        if by_type:
            where_filter = {"type": by_type}

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter,
            include=['documents', 'metadatas', 'distances']
        )

        # Format results
        formatted_results = []
        for i, doc_id in enumerate(results['ids'][0]):
            distance = results['distances'][0][i] if 'distances' in results else 0
            similarity = 1 - distance  # Convert distance to similarity

            formatted_results.append({
                'id': doc_id,
                'path': results['metadatas'][0][i].get('path', ''),
                'type': results['metadatas'][0][i].get('type', 'Unknown'),
                'title': results['metadatas'][0][i].get('title', ''),
                'description': results['documents'][0][i][:200] if results['documents'] else '',
                'score': int(similarity * 100),
                'match_type': 'semantic',
                'similarity': round(similarity, 3)
            })

        return formatted_results

    def _load_concepts(self):
        """Load all concepts from knowledge base."""
        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue

            content = md_file.read_text(encoding='utf-8')

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    fm = self.yaml_parser.parse(parts[1])
                    if fm:
                        body = parts[2] if len(parts) >= 3 else ''
                        self.concepts.append({
                            'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
                            'path': str(md_file.relative_to(self.kb_dir)),
                            'type': fm.get('type', 'Unknown'),
                            'title': fm.get('title', md_file.stem),
                            'description': fm.get('description', ''),
                            'tags': fm.get('tags', []),
                            'body': body
                        })

    def _create_embedding_text(self, concept: Dict) -> str:
        """Create text for embedding from concept."""
        parts = []

        # Title is most important
        parts.append(f"Title: {concept['title']}")

        # Type
        parts.append(f"Type: {concept['type']}")

        # Description
        if concept['description']:
            parts.append(f"Description: {concept['description']}")

        # Tags
        if concept['tags']:
            parts.append(f"Tags: {', '.join(concept['tags'])}")

        # Body (truncated)
        body_clean = re.sub(r'[#*\[\]]', '', concept['body'][:500])
        parts.append(f"Content: {body_clean}")

        return '\n'.join(parts)


class KnowledgeVisualizer:
    """Generates interactive knowledge graph HTML."""

    def __init__(self, kb_dir: Path, output_path: Path):
        self.kb_dir = kb_dir
        self.output_path = output_path
        self.validator = OKFValidator()

    def visualize(self, name: Optional[str] = None) -> bool:
        print(f"📊 Generating knowledge graph: {self.kb_dir}")
        print(f"   Output: {self.output_path}")

        # Validate and load concepts
        is_valid, errors, warnings = self.validator.validate_bundle(self.kb_dir)

        if not self.validator.concepts:
            print("   No concepts found in knowledge base")
            return False

        print(f"   Concepts: {len(self.validator.concepts)}")

        # Generate HTML
        html_content = self._generate_html(name or self.kb_dir.name)

        # Write output
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(html_content, encoding='utf-8')

        print(f"\n✅ Visualization created: {self.output_path}")
        print(f"   Open in browser to view interactive graph")

        return True

    def _generate_html(self, name: str) -> str:
        """Generate single-file HTML visualization."""

        # Prepare nodes and edges for Cytoscape.js
        nodes = []
        edges = []

        # Color mapping for types
        type_colors = {
            'method': '#3498db',
            'fact': '#2ecc71',
            'definition': '#9b59b6',
            'opinion': '#e74c3c',
            'data': '#f39c12',
            'question': '#1abc9c',
            'reference': '#34495e'
        }

        for concept in self.validator.concepts:
            node_id = concept['id']
            node_type = concept['type']
            color = type_colors.get(node_type, '#95a5a6')

            nodes.append({
                'data': {
                    'id': node_id,
                    'label': concept['title'][:30],
                    'type': node_type,
                    'description': concept['description'],
                    'path': concept['path'],
                    'color': color
                }
            })

            # Add edges from links
            for link in concept.get('links', []):
                # Normalize link to node id
                target_id = link.replace('.md', '').replace('/', '').replace('./', '')
                if target_id:
                    edges.append({
                        'data': {
                            'id': f"{node_id}->{target_id}",
                            'source': node_id,
                            'target': target_id
                        }
                    })

        # Build nodes JSON
        nodes_json = json.dumps(nodes)
        edges_json = json.dumps(edges)
        escaped_name = html.escape(name)

        # Generate HTML template using string concatenation to avoid f-string issues
        html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>''' + escaped_name + ''' - Knowledge Graph</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            height: 100vh;
            display: flex;
        }
        #sidebar {
            width: 300px;
            background: #fff;
            border-right: 1px solid #ddd;
            display: flex;
            flex-direction: column;
        }
        #header {
            padding: 20px;
            border-bottom: 1px solid #ddd;
        }
        #header h1 { font-size: 18px; margin-bottom: 5px; }
        #header p { color: #666; font-size: 14px; }
        #search { padding: 10px 20px; border-bottom: 1px solid #ddd; }
        #search input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        #filters { padding: 10px 20px; border-bottom: 1px solid #ddd; }
        #filters label {
            display: inline-block;
            margin: 2px 4px;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
        }
        #stats { padding: 10px 20px; border-bottom: 1px solid #ddd; font-size: 12px; color: #666; }
        #detail {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        #detail h2 { margin-bottom: 10px; }
        #detail .meta { color: #666; font-size: 14px; margin-bottom: 10px; }
        #graph { flex: 1; background: #fff; }
        .type-method { background: #3498db; color: #fff; }
        .type-fact { background: #2ecc71; color: #fff; }
        .type-definition { background: #9b59b6; color: #fff; }
        .type-opinion { background: #e74c3c; color: #fff; }
        .type-data { background: #f39c12; color: #fff; }
        .type-question { background: #1abc9c; color: #fff; }
        .type-reference { background: #34495e; color: #fff; }
    </style>
</head>
<body>
    <div id="sidebar">
        <div id="header">
            <h1>''' + escaped_name + '''</h1>
            <p>Knowledge Graph Visualization</p>
        </div>
        <div id="search">
            <input type="text" placeholder="Search..." id="searchInput">
        </div>
        <div id="filters">
            <label class="type-method"><input type="checkbox" checked data-type="method"> method</label>
            <label class="type-fact"><input type="checkbox" checked data-type="fact"> fact</label>
            <label class="type-definition"><input type="checkbox" checked data-type="definition"> definition</label>
            <label class="type-opinion"><input type="checkbox" checked data-type="opinion"> opinion</label>
            <label class="type-data"><input type="checkbox" checked data-type="data"> data</label>
            <label class="type-question"><input type="checkbox" checked data-type="question"> question</label>
            <label class="type-reference"><input type="checkbox" checked data-type="reference"> reference</label>
        </div>
        <div id="stats">
            Concepts: ''' + str(len(nodes)) + ''' | Links: ''' + str(len(edges)) + '''
        </div>
        <div id="detail">
            <p style="color: #999;">Click a node to view details</p>
        </div>
    </div>
    <div id="graph"></div>
    <script>
        var nodes = ''' + nodes_json + ''';
        var edges = ''' + edges_json + ''';
        var cy = cytoscape({
            container: document.getElementById('graph'),
            elements: nodes.concat(edges),
            style: [
                {selector: 'node', style: {
                    'label': 'data(label)',
                    'background-color': 'data(color)',
                    'width': 60, 'height': 60,
                    'font-size': 10,
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'color': '#fff'
                }},
                {selector: 'edge', style: {
                    'width': 1,
                    'line-color': '#ccc',
                    'curve-style': 'bezier'
                }}
            ],
            layout: {name: 'cose', animate: true, animationDuration: 500}
        });
        cy.on('tap', 'node', function(evt) {
            var node = evt.target;
            var data = node.data();
            document.getElementById('detail').innerHTML =
                '<h2>' + data.label + '</h2>' +
                '<div class="meta"><span class="type-' + data.type + '">' + data.type + '</span> | ' + data.path + '</div>' +
                '<p>' + data.description + '</p>';
        });
        document.getElementById('searchInput').addEventListener('input', function(e) {
            var query = e.target.value.toLowerCase();
            cy.nodes().forEach(function(node) {
                var label = node.data('label').toLowerCase();
                node.style('display', (query && label.indexOf(query) === -1) ? 'none' : 'element');
            });
        });
        document.querySelectorAll('#filters input').forEach(function(input) {
            input.addEventListener('change', function() {
                var type = this.dataset.type;
                var checked = this.checked;
                cy.nodes().forEach(function(node) {
                    if (node.data('type') === type) {
                        node.style('display', checked ? 'element' : 'none');
                    }
                });
            });
        });
    </script>
</body>
</html>'''

        return html_content


# === Command Functions ===

def cmd_init(args):
    kb_dir = Path(args.knowledge_base)
    initializer = KBInitializer(kb_dir)
    success = initializer.init()
    sys.exit(0 if success else 1)


def cmd_ingest(args):
    kb_dir = Path(args.knowledge_base)
    source_path = Path(args.source)

    ingestor = KnowledgeIngestor(kb_dir, source_path)
    success = ingestor.ingest(
        auto_detect_type=args.auto_type,
        default_type=args.type
    )
    sys.exit(0 if success else 1)


def cmd_embed(args):
    """Generate embeddings for semantic search."""
    kb_dir = Path(args.knowledge_base)

    engine = SemanticSearchEngine(kb_dir)
    success = engine.embed_all()
    sys.exit(0 if success else 1)


def cmd_query(args):
    kb_dir = Path(args.knowledge_base)

    # Check if semantic search requested
    if args.semantic:
        engine = SemanticSearchEngine(kb_dir)

        # Check dependencies
        available, msg = engine.check_dependencies()
        if not available:
            print(f"❌ {msg}")
            sys.exit(1)

        # Perform semantic search
        results = engine.search(
            query_str=args.query,
            limit=args.limit,
            by_type=args.type
        )

        if not results:
            print(f"\n   No results found for '{args.query}'")
            sys.exit(0)

        # Display results
        print(f"\n🔍 Semantic search results ({len(results)}):")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. [{result['type']}] {result['title']}")
            print(f"   Path: {result['path']}")
            print(f"   Similarity: {result['similarity']:.3f}")
            print(f"   {result['description'][:80]}...")
    else:
        # Keyword search (default)
        querier = KnowledgeQuerier(kb_dir)
        success = querier.query(
            query_str=args.query,
            limit=args.limit,
            by_type=args.type
        )
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
        # Check if any errors relate to frontmatter
        has_frontmatter_errors = any('frontmatter' in e[1].lower() for e in errors)
        print(f"   ✅ All .md files have frontmatter: {'✅ Yes' if not has_frontmatter_errors else '❌ No'}")

        # Check if any errors relate to missing type field
        has_type_errors = any('type' in e[1].lower() and 'missing' in e[1].lower() for e in errors)
        print(f"   ✅ All frontmatter have 'type': {'✅ Yes' if not has_type_errors else '❌ No'}")

        # Check if reserved files have errors
        has_reserved_errors = any('index.md' in e[0] or 'log.md' in e[0] for e in errors)
        print(f"   ✅ Reserved files valid: {'✅ Yes' if not has_reserved_errors else '❌ No'}")

    sys.exit(0 if is_valid else 1)


def cmd_index(args):
    kb_dir = Path(args.knowledge_base)
    directory = Path(args.directory) if args.directory else None

    generator = IndexGenerator(kb_dir)
    success = generator.generate(directory)
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


def cmd_visualize(args):
    kb_dir = Path(args.knowledge_base)
    output_path = Path(args.output) if args.output else kb_dir / 'views' / 'knowledge-graph.html'

    visualizer = KnowledgeVisualizer(kb_dir, output_path)
    success = visualizer.visualize(name=args.name)
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

    # ingest command
    ingest_parser = subparsers.add_parser('ingest', help='摄入资料提取原子')
    ingest_parser.add_argument('knowledge_base', type=Path, help='知识库目录路径')
    ingest_parser.add_argument('source', type=Path, help='源文件路径')
    ingest_parser.add_argument('--type', '-t', default='method', help='原子类型（默认: method）')
    ingest_parser.add_argument('--auto-type', action='store_true', default=True, help='自动检测类型')
    ingest_parser.set_defaults(func=cmd_ingest)

    # embed command
    embed_parser = subparsers.add_parser('embed', help='生成向量嵌入（语义搜索）')
    embed_parser.add_argument('knowledge_base', type=Path, help='知识库目录路径')
    embed_parser.set_defaults(func=cmd_embed)

    # query command
    query_parser = subparsers.add_parser('query', help='搜索查询知识')
    query_parser.add_argument('knowledge_base', type=Path, help='知识库目录路径')
    query_parser.add_argument('query', help='查询关键词或问题')
    query_parser.add_argument('--type', '-t', help='按类型过滤')
    query_parser.add_argument('--limit', '-l', type=int, default=10, help='结果数量限制')
    query_parser.add_argument('--semantic', '-s', action='store_true', help='启用语义搜索（需要先运行 embed）')
    query_parser.set_defaults(func=cmd_query)

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

    # visualize command
    visualize_parser = subparsers.add_parser('visualize', help='生成知识图谱可视化')
    visualize_parser.add_argument('knowledge_base', type=Path, help='知识库目录路径')
    visualize_parser.add_argument('--output', '-o', type=Path, help='输出 HTML 文件路径')
    visualize_parser.add_argument('--name', '-n', help='图谱名称')
    visualize_parser.set_defaults(func=cmd_visualize)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()