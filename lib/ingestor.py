"""Ingests source materials and extracts knowledge atoms."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from .constants import TYPE_DIRS
from .yaml_parser import SimpleYAMLParser
from .multi_format_parser import MultiFormatParser, LongDocumentSplitter


class KnowledgeIngestor:
    """Ingests source materials and extracts knowledge atoms."""

    # 长文档拆分阈值
    SPLIT_THRESHOLD = 2000

    def __init__(self, kb_dir: Path, source_path: Optional[Path] = None):
        self.kb_dir = kb_dir
        self.source_path = source_path or Path('.')
        self.yaml_parser = SimpleYAMLParser()
        self.format_parser = MultiFormatParser()
        self.splitter = LongDocumentSplitter()

    def ingest(self, source_path: Optional[Path] = None, auto_detect_type: bool = True,
               default_type: str = 'method', split_long: bool = True) -> bool:
        """摄入源文件并提取知识原子.

        Args:
            source_path: 源文件路径（可选，覆盖构造时的 source_path）
            auto_detect_type: 是否自动检测类型
            default_type: 默认类型
            split_long: 是否拆分长文档

        Returns:
            是否成功
        """
        if source_path is not None:
            self.source_path = source_path

        print(f"📦 Ingesting source: {self.source_path}")
        print(f"   Knowledge base: {self.kb_dir}")

        if not self.source_path.exists():
            print(f"❌ Error: Source not found: {self.source_path}")
            return False

        # 多格式解析
        title, content = self.format_parser.parse(self.source_path)
        if self.format_parser.warnings:
            for w in self.format_parser.warnings:
                print(f"   ⚠️  {w}")

        print(f"   Title: {title}")

        # 检测来源类型
        source_type = self._detect_source_type()
        print(f"   Source type: {source_type}")

        # 长文档拆分
        if split_long and len(content) > self.SPLIT_THRESHOLD:
            sections = self.splitter.split(title, content)
            if len(sections) > 1:
                print(f"   📄 长文档拆分为 {len(sections)} 个知识原子")
                success_count = 0
                for i, (sub_title, sub_content) in enumerate(sections, 1):
                    atom_type = self._determine_type(sub_content, auto_detect_type, default_type)
                    tags = self._extract_tags(sub_content)
                    atom_id = self._generate_atom_id(f"{title}-{sub_title}" if sub_title else title)
                    if self._create_atom_file(
                        title=sub_title or f"{title}（{i}）",
                        description=self._extract_description(sub_content),
                        atom_type=atom_type,
                        tags=tags,
                        source_path=self.source_path,
                        source_type=source_type,
                        original_content=sub_content,
                        atom_id=atom_id,
                    ):
                        success_count += 1
                print(f"\n✅ Created {success_count}/{len(sections)} atoms")
                self._update_log(title, '', '', count=success_count)
                return success_count > 0

        # 单原子创建
        description = self._extract_description(content)
        tags = self._extract_tags(content)
        atom_type = self._determine_type(content, auto_detect_type, default_type)
        print(f"   Atom type: {atom_type}")
        atom_id = self._generate_atom_id(title)

        if self._create_atom_file(
            title=title,
            description=description,
            atom_type=atom_type,
            tags=tags,
            source_path=self.source_path,
            source_type=source_type,
            original_content=content,
            atom_id=atom_id,
        ):
            print(f"\n✅ Atom created: {atom_id}")
            self._update_log(title, atom_id, atom_type)
            return True
        return False

    def _create_atom_file(self, title: str, description: str, atom_type: str,
                          tags: List[str], source_path: Path, source_type: str,
                          original_content: str, atom_id: str) -> bool:
        """创建原子文件并写入磁盘.

        Args:
            title: 标题
            description: 描述
            atom_type: 原子类型
            tags: 标签列表
            source_path: 源文件路径
            source_type: 来源类型
            original_content: 原始内容
            atom_id: 原子 ID

        Returns:
            是否成功
        """
        target_dir = TYPE_DIRS.get(atom_type, 'methods')
        target_path = self.kb_dir / 'atoms' / target_dir / f"{atom_id}.md"
        atom_content = self._create_atom_content(
            title=title,
            description=description,
            atom_type=atom_type,
            tags=tags,
            source_path=source_path,
            source_type=source_type,
            original_content=original_content,
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(atom_content, encoding='utf-8')
        print(f"   → {target_path.relative_to(self.kb_dir)}")
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

    def _update_log(self, title: str, atom_id: str, atom_type: str, count: int = 0) -> None:
        """Update log.md with new atom.

        Args:
            title: 原子标题
            atom_id: 原子 ID
            atom_type: 原子类型
            count: 批量创建时的数量（>0 表示批量）
        """
        log_path = self.kb_dir / 'log.md'

        if log_path.exists():
            log_content = log_path.read_text(encoding='utf-8')
        else:
            log_content = "# Knowledge Base Log\n\n"

        today = datetime.now().strftime('%Y-%m-%d')
        if count > 0:
            new_entry = f"\n## {today}\n\n* **Ingest**: Added {count} atoms from [{title}]({self.source_path.name}) (split)\n"
        else:
            new_entry = f"\n## {today}\n\n* **Ingest**: Added [{title}](atoms/{TYPE_DIRS.get(atom_type, 'methods')}/{atom_id}.md) ({atom_type})\n"

        if f"## {today}" in log_content:
            log_content = log_content.replace(f"## {today}\n", f"## {today}\n{new_entry.strip()}\n")
        else:
            log_content += new_entry

        log_path.write_text(log_content, encoding='utf-8')