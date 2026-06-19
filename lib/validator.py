"""Validates OKF bundle conformance (§9)."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from .constants import RESERVED_FILES, RECOMMENDED_FIELDS
from .yaml_parser import SimpleYAMLParser


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

    def _validate_reserved_file(self, file_path: Path, rel_path: Path) -> None:
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
                    except (ValueError, KeyError, TypeError):
                        # YAML 解析错误或字段缺失，继续检查
                        pass
                self.warnings.append((str(rel_path), "index.md typically should not have frontmatter (§6)"))

        if file_path.name == 'log.md':
            if not content.strip():
                self.warnings.append((str(rel_path), "Empty log.md file"))

    def _validate_concept_file(self, file_path: Path, rel_path: Path) -> None:
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
                except (ValueError, TypeError):
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

        except (ValueError, KeyError, TypeError) as e:
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

    def _count_types(self) -> Dict[str, int]:
        """Count concepts by type."""
        type_counts: Dict[str, int] = {}
        for concept in self.concepts:
            t = concept.get('type', 'unknown')
            type_counts[t] = type_counts.get(t, 0) + 1
        return type_counts