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

# KB Meta Schema for parent-child knowledge base architecture
KB_META_SCHEMA = {
    'kb_type': 'standalone',  # standalone / parent / child
    'name': '',
    'children': [],           # List of child KB names (for parent)
    'children_paths': {},     # Dict of child_name -> relative_path (for parent)
    'parent': None,           # Parent KB name (for child)
    'parent_path': None       # Relative path to parent (for child)
}


class KBRegistry:
    """知识库注册表管理（支持全局和项目本地两级）"""

    GLOBAL_DIR = Path.home() / '.llm-wiki'
    GLOBAL_REGISTRY = GLOBAL_DIR / 'registry.json'
    GLOBAL_CONFIG = GLOBAL_DIR / 'config.json'

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir
        self.project_registry = project_dir / '.llm-wiki' / 'registry.json' if project_dir else None
        self.project_config = project_dir / '.llm-wiki' / 'config.json' if project_dir else None
        self._ensure_registries()

    def _ensure_registries(self):
        """确保注册表目录和文件存在"""
        # 全局注册表
        self.GLOBAL_DIR.mkdir(parents=True, exist_ok=True)

        if not self.GLOBAL_REGISTRY.exists():
            self._write_registry(self.GLOBAL_REGISTRY, {'version': '1.0', 'knowledge_bases': {}})

        if not self.GLOBAL_CONFIG.exists():
            self._write_config(self.GLOBAL_CONFIG, {'current_kb': None})

        # 项目级注册表（可选）
        if self.project_dir:
            project_llm_dir = self.project_dir / '.llm-wiki'
            project_llm_dir.mkdir(parents=True, exist_ok=True)

            if self.project_registry and not self.project_registry.exists():
                self._write_registry(self.project_registry, {'version': '1.0', 'knowledge_bases': {}})

            if self.project_config and not self.project_config.exists():
                self._write_config(self.project_config, {'current_kb': None})

    def _read_registry(self, path: Path) -> Dict:
        """读取注册表"""
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except:
            return {'version': '1.0', 'knowledge_bases': {}}

    def _write_registry(self, path: Path, data: Dict):
        """写入注册表"""
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    def _read_config(self, path: Path) -> Dict:
        """读取配置"""
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except:
            return {'current_kb': None}

    def _write_config(self, path: Path, data: Dict):
        """写入配置"""
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    def _get_registry_for_scope(self, scope: str) -> Tuple[Path, Dict]:
        """获取指定范围的注册表路径和数据"""
        if scope == 'project' and self.project_registry:
            return self.project_registry, self._read_registry(self.project_registry)
        elif scope == 'global':
            return self.GLOBAL_REGISTRY, self._read_registry(self.GLOBAL_REGISTRY)
        else:  # auto
            # 优先项目级
            if self.project_registry and self.project_registry.exists():
                data = self._read_registry(self.project_registry)
                if data.get('knowledge_bases'):
                    return self.project_registry, data
            return self.GLOBAL_REGISTRY, self._read_registry(self.GLOBAL_REGISTRY)

    def register(self, path: Path, name: str, description: str = "", tags: List[str] = None,
                 scope: str = 'auto', kb_type: str = 'standalone', parent: str = None) -> bool:
        """注册知识库

        Args:
            path: 知识库路径
            name: 知识库名称/别名
            description: 描述
            tags: 标签列表
            scope: 注册范围 (auto/project/global)
            kb_type: 知识库类型 (standalone/parent/child)
            parent: 父知识库名称（仅当 kb_type=child 时使用）
        """
        if not path.exists():
            print(f"❌ Path does not exist: {path}")
            return False

        registry_path, registry = self._get_registry_for_scope(scope)

        # 检查名称是否已存在
        if name in registry.get('knowledge_bases', {}):
            print(f"❌ Knowledge base '{name}' already registered")
            return False

        # 统计知识库信息
        validator = OKFValidator()
        validator.validate_bundle(path)

        # 添加注册信息
        kb_info = {
            'path': str(path.resolve()),
            'alias': name,
            'created': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'description': description,
            'tags': tags or [],
            'kb_type': kb_type,
            'parent': parent,
            'children': [],
            'children_paths': {},
            'statistics': {
                'concepts': len(validator.concepts),
                'types': validator._count_types() if hasattr(validator, '_count_types') else {}
            }
        }

        registry.setdefault('knowledge_bases', {})[name] = kb_info
        self._write_registry(registry_path, registry)

        # 如果是子知识库，更新父知识库的 children 列表
        if kb_type == 'child' and parent:
            self.register_child(parent, name, path.name + '/')
            # 更新父知识库的注册信息
            parent_kb = self.get(parent)
            if parent_kb:
                parent_info = registry['knowledge_bases'].get(parent, {})
                if name not in parent_info.get('children', []):
                    parent_info.setdefault('children', []).append(name)
                parent_info.setdefault('children_paths', {})[name] = path.name + '/'
                parent_info['kb_type'] = 'parent'
                self._write_registry(registry_path, registry)

        print(f"✅ Registered knowledge base: {name}")
        print(f"   Path: {path}")
        print(f"   Scope: {scope}")
        if kb_type != 'standalone':
            print(f"   Type: {kb_type}")
            if parent:
                print(f"   Parent: {parent}")
        return True

    def unregister(self, name: str, scope: str = 'all') -> bool:
        """注销知识库"""
        found = False

        if scope in ('all', 'project') and self.project_registry:
            registry = self._read_registry(self.project_registry)
            if name in registry.get('knowledge_bases', {}):
                del registry['knowledge_bases'][name]
                self._write_registry(self.project_registry, registry)
                found = True
                print(f"✅ Unregistered from project: {name}")

        if scope in ('all', 'global'):
            registry = self._read_registry(self.GLOBAL_REGISTRY)
            if name in registry.get('knowledge_bases', {}):
                del registry['knowledge_bases'][name]
                self._write_registry(self.GLOBAL_REGISTRY, registry)
                found = True
                print(f"✅ Unregistered from global: {name}")

        if not found:
            print(f"❌ Knowledge base not found: {name}")
            return False

        return True

    def list(self, scope: str = 'all') -> List[Dict]:
        """列出所有知识库"""
        kbs = []

        if scope in ('all', 'project') and self.project_registry:
            registry = self._read_registry(self.project_registry)
            for name, info in registry.get('knowledge_bases', {}).items():
                kbs.append({'name': name, 'scope': 'project', **info})

        if scope in ('all', 'global'):
            registry = self._read_registry(self.GLOBAL_REGISTRY)
            for name, info in registry.get('knowledge_bases', {}).items():
                # 避免重复（项目级优先）
                if not any(kb['name'] == name for kb in kbs):
                    kbs.append({'name': name, 'scope': 'global', **info})

        return kbs

    def get(self, name: str) -> Optional[Dict]:
        """获取知识库信息"""
        # 优先项目级
        if self.project_registry:
            registry = self._read_registry(self.project_registry)
            if name in registry.get('knowledge_bases', {}):
                return {'name': name, 'scope': 'project', **registry['knowledge_bases'][name]}

        # 全局
        registry = self._read_registry(self.GLOBAL_REGISTRY)
        if name in registry.get('knowledge_bases', {}):
            return {'name': name, 'scope': 'global', **registry['knowledge_bases'][name]}

        return None

    def set_current(self, name: str, scope: str = 'auto') -> bool:
        """设置当前知识库"""
        kb = self.get(name)
        if not kb:
            print(f"❌ Knowledge base not found: {name}")
            return False

        # 确定配置文件
        if scope == 'project' and self.project_config:
            config_path = self.project_config
        elif scope == 'global':
            config_path = self.GLOBAL_CONFIG
        else:  # auto
            config_path = self.project_config if self.project_config and kb['scope'] == 'project' else self.GLOBAL_CONFIG

        config = self._read_config(config_path)
        config['current_kb'] = name
        self._write_config(config_path, config)
        return True

    def get_current(self) -> Optional[str]:
        """获取当前知识库名称"""
        # 优先项目级
        if self.project_config:
            config = self._read_config(self.project_config)
            if config.get('current_kb'):
                return config['current_kb']

        # 全局
        config = self._read_config(self.GLOBAL_CONFIG)
        return config.get('current_kb')

    def resolve_path(self, name_or_path: str) -> Optional[Path]:
        """解析名称或路径为实际路径"""
        # 尝试作为名称解析
        kb = self.get(name_or_path)
        if kb:
            return Path(kb['path'])

        # 尝试作为路径
        path = Path(name_or_path)
        if path.exists():
            return path

        return None

    # ========== 父子知识库支持方法 ==========

    def _read_kb_meta(self, kb_path: Path) -> Dict:
        """读取知识库的 .kb-meta.json 文件"""
        meta_path = kb_path / '.kb-meta.json'
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text(encoding='utf-8'))
            except:
                pass
        # 返回默认 schema
        return KB_META_SCHEMA.copy()

    def _write_kb_meta(self, kb_path: Path, meta: Dict):
        """写入知识库的 .kb-meta.json 文件"""
        meta_path = kb_path / '.kb-meta.json'
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')

    def get_children(self, name: str) -> List[str]:
        """获取知识库的所有子知识库名称"""
        kb = self.get(name)
        if not kb:
            return []
        kb_path = Path(kb['path'])
        meta = self._read_kb_meta(kb_path)
        return meta.get('children', [])

    def get_parent(self, name: str) -> Optional[str]:
        """获取知识库的父知识库名称"""
        kb = self.get(name)
        if not kb:
            return None
        kb_path = Path(kb['path'])
        meta = self._read_kb_meta(kb_path)
        return meta.get('parent')

    def get_kb_type(self, name: str) -> str:
        """获取知识库类型（standalone/parent/child）"""
        kb = self.get(name)
        if not kb:
            return 'standalone'
        kb_path = Path(kb['path'])
        meta = self._read_kb_meta(kb_path)
        return meta.get('kb_type', 'standalone')

    def register_child(self, parent_name: str, child_name: str, child_path: str):
        """注册子知识库到父知识库"""
        parent_kb = self.get(parent_name)
        if not parent_kb:
            return False
        parent_path = Path(parent_kb['path'])
        meta = self._read_kb_meta(parent_path)

        if child_name not in meta.get('children', []):
            meta.setdefault('children', []).append(child_name)
        meta.setdefault('children_paths', {})[child_name] = child_path
        meta['kb_type'] = 'parent'

        self._write_kb_meta(parent_path, meta)
        return True


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
    """Exports knowledge base to OKF bundle.

    Supports:
    - Standalone knowledge base export
    - Child knowledge base independent export
    - Parent knowledge base export with optional children
    """

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
            except:
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
            except:
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

    def _create_tarball(self):
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
    """Initializes knowledge base directory structure.

    Supports three modes:
    - standalone: Regular knowledge base (default)
    - parent: Parent knowledge base that can contain child knowledge bases
    - child: Child knowledge base nested under a parent
    """

    def __init__(self, kb_dir: Path, is_parent: bool = False,
                 is_child: bool = False, parent_kb: Optional[Path] = None,
                 name: str = None):
        self.kb_dir = kb_dir
        self.is_parent = is_parent
        self.is_child = is_child
        self.parent_kb = parent_kb
        self.name = name or kb_dir.name

    def init(self) -> bool:
        """Initialize knowledge base based on mode."""
        if self.is_parent:
            return self._init_parent()
        elif self.is_child:
            return self._init_child()
        else:
            return self._init_standalone()

    def _init_standalone(self) -> bool:
        """Initialize a standalone knowledge base."""
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

    def _init_parent(self) -> bool:
        """Initialize a parent knowledge base."""
        print(f"📦 Initializing parent knowledge base: {self.kb_dir}")

        if self.kb_dir.exists() and any(self.kb_dir.iterdir()):
            print(f"❌ Error: Directory not empty: {self.kb_dir}")
            return False

        # Create standard directory structure (parent also has its own atoms)
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

        # Create .kb-meta.json for parent
        meta = {
            'kb_type': 'parent',
            'name': self.name,
            'children': [],
            'children_paths': {},
            'parent': None,
            'parent_path': None
        }
        meta_path = self.kb_dir / '.kb-meta.json'
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"   Created: .kb-meta.json (parent)")

        # Create root index.md
        index_content = f"""---
okf_version: "0.1"
---

# {self.name} - Parent Knowledge Base

This is a **parent knowledge base** that can contain multiple child knowledge bases.

## Structure

- `atoms/` - Common knowledge shared across all child knowledge bases
- Child knowledge bases will be created as subdirectories

## Statistics

- Total atoms: 0
- Child knowledge bases: 0

## Quick Start

1. Add common knowledge to `atoms/`
2. Create child knowledge bases: `llm-wiki init <path> --child --parent-kb {self.kb_dir}`
3. Query across all knowledge bases: `llm-wiki query {self.name} "search term"`
"""

        (self.kb_dir / 'index.md').write_text(index_content)
        print(f"   Created: index.md")

        # Create log.md
        log_content = f"""# Knowledge Base Log

## {datetime.now().strftime('%Y-%m-%d')}

* **Initialization**: Created parent knowledge base structure.
"""

        (self.kb_dir / 'log.md').write_text(log_content)
        print(f"   Created: log.md")

        print(f"\n✅ Parent knowledge base initialized!")
        print(f"   Path: {self.kb_dir}")
        print(f"   Name: {self.name}")
        print(f"\nNext steps:")
        print(f"   1. Add common knowledge to atoms/")
        print(f"   2. Create child knowledge bases with --child flag")

        return True

    def _init_child(self) -> bool:
        """Initialize a child knowledge base under a parent."""
        if not self.parent_kb:
            print(f"❌ Error: --parent-kb is required for child knowledge base")
            return False

        parent_path = Path(self.parent_kb)
        if not parent_path.exists():
            print(f"❌ Error: Parent knowledge base not found: {self.parent_kb}")
            return False

        # Check parent is a valid parent knowledge base
        parent_meta_path = parent_path / '.kb-meta.json'
        if not parent_meta_path.exists():
            print(f"❌ Error: Parent is not a parent knowledge base (missing .kb-meta.json)")
            return False

        print(f"📦 Initializing child knowledge base: {self.kb_dir}")
        print(f"   Parent: {self.parent_kb}")

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

        # Create .kb-meta.json for child
        rel_path = self.kb_dir.name + '/'  # Relative path from parent
        meta = {
            'kb_type': 'child',
            'name': self.name,
            'children': [],
            'children_paths': {},
            'parent': parent_path.name,
            'parent_path': '..'  # Relative path to parent
        }
        meta_path = self.kb_dir / '.kb-meta.json'
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"   Created: .kb-meta.json (child)")

        # Update parent's .kb-meta.json
        parent_meta = json.loads(parent_meta_path.read_text(encoding='utf-8'))
        if self.name not in parent_meta.get('children', []):
            parent_meta.setdefault('children', []).append(self.name)
        parent_meta.setdefault('children_paths', {})[self.name] = rel_path
        parent_meta_path.write_text(json.dumps(parent_meta, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"   Updated parent's .kb-meta.json")

        # Create root index.md
        index_content = f"""---
okf_version: "0.1"
---

# {self.name} - Child Knowledge Base

This is a **child knowledge base** under the parent: {parent_path.name}.

## Statistics

- Total atoms: 0

## Quick Start

1. Add knowledge specific to this domain
2. Query will automatically search across parent and siblings
"""

        (self.kb_dir / 'index.md').write_text(index_content)
        print(f"   Created: index.md")

        # Create log.md
        log_content = f"""# Knowledge Base Log

## {datetime.now().strftime('%Y-%m-%d')}

* **Initialization**: Created child knowledge base under {parent_path.name}.
"""

        (self.kb_dir / 'log.md').write_text(log_content)
        print(f"   Created: log.md")

        print(f"\n✅ Child knowledge base initialized!")
        print(f"   Path: {self.kb_dir}")
        print(f"   Name: {self.name}")
        print(f"   Parent: {parent_path.name}")

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


class AggregatedQuerier:
    """聚合查询父知识库及其所有子知识库."""

    def __init__(self, kb_dir: Path, registry: KBRegistry):
        self.kb_dir = kb_dir
        self.registry = registry
        self.children = []
        self.all_concepts: List[Dict] = []

    def discover_children(self) -> List[Tuple[Path, str]]:
        """发现并加载所有子知识库路径."""
        child_paths = []

        # 从 .kb-meta.json 获取子知识库信息
        meta_path = self.kb_dir / '.kb-meta.json'
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                for child_name, rel_path in meta.get('children_paths', {}).items():
                    child_full_path = self.kb_dir / rel_path.rstrip('/')
                    if child_full_path.exists():
                        child_paths.append((child_full_path, child_name))
            except:
                pass

        # 也检查注册表中的子知识库
        kb_name = self.kb_dir.name
        kb_info = self.registry.get(kb_name)
        if kb_info:
            for child_name in kb_info.get('children', []):
                child_kb = self.registry.get(child_name)
                if child_kb:
                    child_full_path = Path(child_kb['path'])
                    if child_full_path.exists():
                        # 避免重复
                        if not any(p[1] == child_name for p in child_paths):
                            child_paths.append((child_full_path, child_name))

        self.children = child_paths
        return child_paths

    def aggregate_query(self, query_str: str, limit: int = 10, by_type: Optional[str] = None,
                        child_filter: Optional[str] = None) -> bool:
        """聚合搜索所有知识库."""
        print(f"🔍 Aggregated query: '{query_str}'")
        print(f"   Parent knowledge base: {self.kb_dir}")

        # 发现子知识库
        children = self.discover_children()
        if children:
            print(f"   Child knowledge bases: {len(children)}")
            for path, name in children:
                print(f"      - {name}")
        else:
            print(f"   (No child knowledge bases)")

        print()

        # 加载父知识库的概念
        parent_querier = KnowledgeQuerier(self.kb_dir)
        parent_querier._load_concepts()

        # 为父知识库概念添加来源标记
        for concept in parent_querier.concepts:
            concept['source'] = self.kb_dir.name
            concept['source_type'] = 'parent'

        self.all_concepts = parent_querier.concepts

        # 加载每个子知识库的概念
        for child_path, child_name in children:
            # 如果指定了 child_filter，只查询该子知识库
            if child_filter and child_name != child_filter:
                continue

            child_querier = KnowledgeQuerier(child_path)
            child_querier._load_concepts()

            for concept in child_querier.concepts:
                concept['source'] = child_name
                concept['source_type'] = 'child'
                # 调整路径以显示相对位置
                concept['display_path'] = f"{child_name}/{concept['path']}"
                self.all_concepts.append(concept)

        print(f"   Total concepts (aggregated): {len(self.all_concepts)}")

        if not self.all_concepts:
            print("   No concepts found")
            return False

        # 搜索
        results = self._search(query_str, by_type)

        # 去重（相同 atom_id）
        seen_ids = set()
        unique_results = []
        for result in results:
            result_id = result.get('id', result['path'])
            if result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)

        # 限制结果数量
        unique_results = unique_results[:limit]

        if not unique_results:
            print(f"\n   No results found for '{query_str}'")
            return True

        # 显示结果
        print(f"\n📋 Results ({len(unique_results)}):")
        for i, result in enumerate(unique_results, 1):
            source_marker = " [子知识库]" if result.get('source_type') == 'child' else " [父知识库]"
            print(f"\n{i}. [{result['type']}] {result['title']}")
            print(f"   Source: {result.get('source', 'unknown')}{source_marker}")
            display_path = result.get('display_path', result['path'])
            print(f"   Path: {display_path}")
            if result['description']:
                desc = result['description'][:80]
                print(f"   {desc}...")
            if result['tags']:
                print(f"   Tags: {', '.join(result['tags'])}")

        return True

    def _search(self, query_str: str, by_type: Optional[str] = None) -> List[Dict]:
        """Search all concepts by query string."""
        query_lower = query_str.lower()
        results = []

        for concept in self.all_concepts:
            # Filter by type if specified
            if by_type and concept['type'] != by_type:
                continue

            # Calculate relevance score
            score = 0

            # Title match (highest weight)
            if query_lower in concept['title'].lower():
                score += 10

            # Description match
            if query_lower in concept['description'].lower():
                score += 5

            # Tags match
            for tag in concept.get('tags', []):
                if query_lower in tag.lower():
                    score += 3

            # Body match
            if query_lower in concept.get('body', '').lower():
                score += 1

            if score > 0:
                concept['score'] = score
                results.append(concept)

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results


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

def resolve_kb(args) -> Optional[Path]:
    """解析知识库路径，支持名称、路径或当前知识库"""
    registry = KBRegistry(project_dir=Path.cwd())

    if hasattr(args, 'knowledge_base') and args.knowledge_base:
        # 尝试作为名称解析，失败则作为路径
        resolved = registry.resolve_path(args.knowledge_base)
        if resolved:
            return resolved
        # 作为路径
        path = Path(args.knowledge_base)
        if path.exists():
            return path
        print(f"❌ Knowledge base not found: {args.knowledge_base}")
        return None

    # 使用当前知识库
    current = registry.get_current()
    if current:
        kb = registry.get(current)
        if kb:
            return Path(kb['path'])

    print("❌ 未指定知识库，请使用 'llm-wiki use <name>' 设置当前知识库")
    return None


def cmd_register(args):
    """注册知识库"""
    registry = KBRegistry(project_dir=Path.cwd())
    path = Path(args.path).resolve()

    # 检查是否有 --parent 参数
    parent = getattr(args, 'parent', None)
    kb_type = 'child' if parent else 'standalone'

    # 检查知识库是否有 .kb-meta.json 以确定类型
    meta_path = path / '.kb-meta.json'
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            kb_type = meta.get('kb_type', 'standalone')
            if not parent and meta.get('parent'):
                parent = meta.get('parent')
        except:
            pass

    success = registry.register(
        path=path,
        name=args.name or path.name,
        description=args.description or "",
        tags=args.tags.split(',') if args.tags else [],
        scope=args.scope,
        kb_type=kb_type,
        parent=parent
    )
    sys.exit(0 if success else 1)


def cmd_unregister(args):
    """注销知识库"""
    registry = KBRegistry(project_dir=Path.cwd())
    success = registry.unregister(args.name, scope=args.scope)
    sys.exit(0 if success else 1)


def cmd_list(args):
    """列出所有知识库"""
    registry = KBRegistry(project_dir=Path.cwd())
    kbs = registry.list(scope=args.scope)
    current = registry.get_current()

    if not kbs:
        print("📚 No registered knowledge bases")
        print("\nUse 'llm-wiki register <path> --name <name>' to register a knowledge base")
        return

    print("📚 Registered Knowledge Bases:\n")

    # 按 kb_type 分组显示
    parents = [kb for kb in kbs if kb.get('kb_type') == 'parent']
    children = [kb for kb in kbs if kb.get('kb_type') == 'child']
    standalone = [kb for kb in kbs if kb.get('kb_type', 'standalone') == 'standalone']

    # 先显示父知识库及其子知识库
    for parent in parents:
        marker = " (current)" if parent['name'] == current else ""
        scope_marker = " [project]" if parent.get('scope') == 'project' else " [global]"
        print(f"  📁 {parent['name']}{marker}{scope_marker}")
        print(f"     Path: {parent['path']}")
        stats = parent.get('statistics', {})
        concepts = stats.get('concepts', 'N/A')
        children_list = parent.get('children', [])
        print(f"     Type: parent | Concepts: {concepts} | Children: {len(children_list)}")

        # 显示子知识库
        for child_name in children_list:
            child_kb = next((kb for kb in children if kb['name'] == child_name), None)
            if child_kb:
                child_marker = " (current)" if child_kb['name'] == current else ""
                print(f"     └─ 📄 {child_name}{child_marker}")
                if args.verbose:
                    child_stats = child_kb.get('statistics', {})
                    child_concepts = child_stats.get('concepts', 'N/A')
                    print(f"        Concepts: {child_concepts}")
        print()

    # 显示独立的子知识库（未找到父级）
    displayed_children = set()
    for parent in parents:
        displayed_children.update(parent.get('children', []))

    orphan_children = [kb for kb in children if kb['name'] not in displayed_children]
    for child in orphan_children:
        marker = " (current)" if child['name'] == current else ""
        scope_marker = " [project]" if child.get('scope') == 'project' else " [global]"
        parent_name = child.get('parent', 'N/A')
        print(f"  📄 {child['name']}{marker}{scope_marker}")
        print(f"     Path: {child['path']}")
        print(f"     Type: child | Parent: {parent_name}")
        print()

    # 显示独立知识库
    for kb in standalone:
        marker = " (current)" if kb['name'] == current else ""
        scope_marker = " [project]" if kb.get('scope') == 'project' else " [global]"
        print(f"  📦 {kb['name']}{marker}{scope_marker}")
        print(f"     Path: {kb['path']}")

        stats = kb.get('statistics', {})
        concepts = stats.get('concepts', 'N/A')
        if args.verbose:
            types = stats.get('types', {})
            types_str = ', '.join(f"{t}({n})" for t, n in types.items()) if types else 'N/A'
            print(f"     Concepts: {concepts} | Types: {types_str}")
            print(f"     Description: {kb.get('description', 'N/A')}")
            print(f"     Tags: {', '.join(kb.get('tags', [])) or 'N/A'}")
            print(f"     Last accessed: {kb.get('last_accessed', 'N/A')[:10]}")
        else:
            print(f"     Concepts: {concepts}")
        print()


def cmd_use(args):
    """设置当前知识库"""
    registry = KBRegistry(project_dir=Path.cwd())
    success = registry.set_current(args.name, scope=args.scope)
    if success:
        print(f"✅ Current knowledge base: {args.name}")
    sys.exit(0 if success else 1)


def cmd_info(args):
    """查看知识库详情"""
    registry = KBRegistry(project_dir=Path.cwd())
    name = args.name or registry.get_current()

    if not name:
        print("❌ No knowledge base specified and no current knowledge base set")
        sys.exit(1)

    kb = registry.get(name)
    if not kb:
        print(f"❌ Knowledge base not found: {name}")
        sys.exit(1)

    print(f"\n📚 Knowledge Base: {name}\n")
    print(f"  Scope: {kb.get('scope', 'unknown')}")
    print(f"  Path: {kb['path']}")
    print(f"  Description: {kb.get('description', 'N/A')}")
    print(f"  Tags: {', '.join(kb.get('tags', [])) or 'N/A'}")
    print(f"  Created: {kb.get('created', 'N/A')[:10]}")
    print(f"  Last accessed: {kb.get('last_accessed', 'N/A')[:10]}")

    # 显示父子知识库关系
    kb_type = kb.get('kb_type', 'standalone')
    if kb_type == 'parent':
        print(f"\n  🔗 Parent Knowledge Base")
        children = kb.get('children', [])
        children_paths = kb.get('children_paths', {})
        print(f"     Children: {len(children)}")
        for child_name in children:
            child_path = children_paths.get(child_name, 'N/A')
            print(f"       - {child_name} → {child_path}")
    elif kb_type == 'child':
        print(f"\n  🔗 Child Knowledge Base")
        print(f"     Parent: {kb.get('parent', 'N/A')}")
        print(f"     Parent path: {kb.get('parent_path', 'N/A')}")
    else:
        print(f"\n  📦 Standalone Knowledge Base")

    stats = kb.get('statistics', {})

    # 如果是父知识库，聚合所有子知识库的统计
    if kb_type == 'parent':
        total_concepts = stats.get('concepts', 0)
        children = kb.get('children', [])
        for child_name in children:
            child_kb = registry.get(child_name)
            if child_kb:
                child_stats = child_kb.get('statistics', {})
                total_concepts += child_stats.get('concepts', 0)
        print(f"\n  Statistics:")
        print(f"    Concepts (parent only): {stats.get('concepts', 'N/A')}")
        print(f"    Concepts (aggregated): {total_concepts}")
    else:
        print(f"\n  Statistics:")
        print(f"    Concepts: {stats.get('concepts', 'N/A')}")

    types = stats.get('types', {})
    if types:
        print(f"    Types:")
        for t, n in sorted(types.items()):
            print(f"      - {t}: {n}")

    # 检查路径是否存在
    kb_path = Path(kb['path'])
    if kb_path.exists():
        print(f"\n  ✅ Path exists")

        # 检查是否有嵌入
        chroma_dir = kb_path / '.chroma'
        if chroma_dir.exists():
            print(f"  ✅ Semantic embeddings available")
        else:
            print(f"  ⚠️  No semantic embeddings (run 'llm-wiki embed {name}')")
    else:
        print(f"\n  ❌ Path does not exist")


def cmd_init(args):
    kb_dir = Path(args.knowledge_base)

    # 检查是否是父/子知识库模式
    is_parent = getattr(args, 'parent', False)
    is_child = getattr(args, 'child', False)
    parent_kb = Path(args.parent_kb) if getattr(args, 'parent_kb', None) else None

    initializer = KBInitializer(
        kb_dir=kb_dir,
        is_parent=is_parent,
        is_child=is_child,
        parent_kb=parent_kb,
        name=args.name
    )
    success = initializer.init()

    # 如果初始化成功且指定了 --register
    if success and args.register:
        registry = KBRegistry(project_dir=Path.cwd())

        # 确定 kb_type
        kb_type = 'parent' if is_parent else ('child' if is_child else 'standalone')
        parent_name = None
        if is_child and parent_kb:
            # 尝试从父知识库的 .kb-meta.json 获取名称
            parent_meta_path = parent_kb / '.kb-meta.json'
            if parent_meta_path.exists():
                parent_meta = json.loads(parent_meta_path.read_text(encoding='utf-8'))
                parent_name = parent_meta.get('name', parent_kb.name)

        registry.register(
            path=kb_dir,
            name=args.name or kb_dir.name,
            description=args.description or "",
            tags=args.tags.split(',') if args.tags else [],
            scope=args.scope,
            kb_type=kb_type,
            parent=parent_name
        )

    sys.exit(0 if success else 1)


def cmd_ingest(args):
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    source_path = Path(args.source)

    ingestor = KnowledgeIngestor(kb_dir, source_path)
    success = ingestor.ingest(
        auto_detect_type=args.auto_type,
        default_type=args.type
    )
    sys.exit(0 if success else 1)


def cmd_embed(args):
    """Generate embeddings for semantic search."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    engine = SemanticSearchEngine(kb_dir)
    success = engine.embed_all()
    sys.exit(0 if success else 1)


def cmd_query(args):
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    # 检查是否是父知识库（需要聚合查询）
    meta_path = kb_dir / '.kb-meta.json'
    is_parent = False
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            is_parent = meta.get('kb_type') == 'parent'
        except:
            pass

    # 也从注册表检查
    registry = KBRegistry(project_dir=Path.cwd())
    kb_name = kb_dir.name
    kb_info = registry.get(kb_name)
    if kb_info and kb_info.get('kb_type') == 'parent':
        is_parent = True

    # 如果是父知识库，使用聚合查询
    if is_parent and not args.semantic:
        # 获取 child_filter 参数
        child_filter = getattr(args, 'child', None)

        agg_querier = AggregatedQuerier(kb_dir, registry)
        success = agg_querier.aggregate_query(
            query_str=args.query,
            limit=args.limit,
            by_type=args.type,
            child_filter=child_filter
        )
        sys.exit(0 if success else 1)

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
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

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
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    directory = Path(args.directory) if args.directory else None

    generator = IndexGenerator(kb_dir)
    success = generator.generate(directory)
    sys.exit(0 if success else 1)


def cmd_export(args):
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    output_path = Path(args.output) if args.output else None
    include_children = getattr(args, 'include_children', False)

    exporter = OKFExporter(kb_dir, output_path, include_children=include_children)
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
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
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
    init_parser.add_argument('--register', action='store_true', help='初始化后注册')
    init_parser.add_argument('--name', '-n', help='知识库别名')
    init_parser.add_argument('--description', '-d', help='描述')
    init_parser.add_argument('--tags', '-t', help='标签（逗号分隔）')
    init_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global'], default='auto', help='注册范围')
    # 父子知识库参数
    init_parser.add_argument('--parent', action='store_true', help='创建父知识库')
    init_parser.add_argument('--child', action='store_true', help='创建子知识库')
    init_parser.add_argument('--parent-kb', type=Path, help='父知识库路径（创建子知识库时必需）')
    init_parser.set_defaults(func=cmd_init)

    # register command
    register_parser = subparsers.add_parser('register', help='注册知识库')
    register_parser.add_argument('path', type=Path, help='知识库路径')
    register_parser.add_argument('--name', '-n', help='知识库别名')
    register_parser.add_argument('--description', '-d', help='描述')
    register_parser.add_argument('--tags', '-t', help='标签（逗号分隔）')
    register_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global'], default='auto', help='注册范围')
    register_parser.add_argument('--parent', '-p', help='父知识库名称（注册子知识库时使用）')
    register_parser.set_defaults(func=cmd_register)

    # unregister command
    unregister_parser = subparsers.add_parser('unregister', help='注销知识库')
    unregister_parser.add_argument('name', help='知识库别名')
    unregister_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global', 'all'], default='all', help='注销范围')
    unregister_parser.set_defaults(func=cmd_unregister)

    # list command
    list_parser = subparsers.add_parser('list', help='列出所有知识库')
    list_parser.add_argument('--scope', '-s', choices=['all', 'project', 'global'], default='all', help='列出范围')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    list_parser.set_defaults(func=cmd_list)

    # use command
    use_parser = subparsers.add_parser('use', help='设置当前知识库')
    use_parser.add_argument('name', help='知识库别名')
    use_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global'], default='auto', help='设置范围')
    use_parser.set_defaults(func=cmd_use)

    # info command
    info_parser = subparsers.add_parser('info', help='查看知识库详情')
    info_parser.add_argument('name', nargs='?', help='知识库别名（默认当前）')
    info_parser.set_defaults(func=cmd_info)

    # ingest command
    ingest_parser = subparsers.add_parser('ingest', help='摄入资料提取原子')
    ingest_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    ingest_parser.add_argument('source', type=Path, help='源文件路径')
    ingest_parser.add_argument('--type', '-t', default='method', help='原子类型（默认: method）')
    ingest_parser.add_argument('--auto-type', action='store_true', default=True, help='自动检测类型')
    ingest_parser.set_defaults(func=cmd_ingest)

    # embed command
    embed_parser = subparsers.add_parser('embed', help='生成向量嵌入（语义搜索）')
    embed_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    embed_parser.set_defaults(func=cmd_embed)

    # query command
    query_parser = subparsers.add_parser('query', help='搜索查询知识')
    query_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    query_parser.add_argument('query', help='查询关键词或问题')
    query_parser.add_argument('--type', '-t', help='按类型过滤')
    query_parser.add_argument('--limit', '-l', type=int, default=10, help='结果数量限制')
    query_parser.add_argument('--semantic', '-s', action='store_true', help='启用语义搜索（需要先运行 embed）')
    query_parser.add_argument('--child', '-c', help='仅搜索指定子知识库')
    query_parser.set_defaults(func=cmd_query)

    # lint command
    lint_parser = subparsers.add_parser('lint', help='OKF 兼容性检查')
    lint_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    lint_parser.add_argument('--okf-check', action='store_true', help='显示 OKF 规范检查详情')
    lint_parser.set_defaults(func=cmd_lint)

    # index command
    index_parser = subparsers.add_parser('index', help='生成目录索引')
    index_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    index_parser.add_argument('--directory', '-d', type=Path, help='指定目录')
    index_parser.set_defaults(func=cmd_index)

    # export command
    export_parser = subparsers.add_parser('export', help='导出为 OKF Bundle')
    export_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    export_parser.add_argument('--output', '-o', type=Path, help='输出文件路径')
    export_parser.add_argument('--validate', '-v', action='store_true', default=True, help='验证 OKF 符合性')
    export_parser.add_argument('--no-validate', action='store_true', help='跳过验证')
    export_parser.add_argument('--force', '-f', action='store_true', help='强制导出')
    export_parser.add_argument('--include-children', action='store_true', help='包含子知识库（仅父知识库）')
    export_parser.set_defaults(func=cmd_export)

    # import command
    import_parser = subparsers.add_parser('import', help='导入 OKF Bundle')
    import_parser.add_argument('bundle', type=Path, help='Bundle 文件路径')
    import_parser.add_argument('--output', '-o', type=Path, default=Path('.'), help='输出目录')
    import_parser.add_argument('--overwrite', action='store_true', help='覆盖现有文件')
    import_parser.set_defaults(func=cmd_import)

    # visualize command
    visualize_parser = subparsers.add_parser('visualize', help='生成知识图谱可视化')
    visualize_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
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