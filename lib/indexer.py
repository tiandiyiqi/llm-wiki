"""Generates index.md files for directories."""

from pathlib import Path
from typing import Dict, List, Optional

from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser


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
        lines = ["# Knowledge Concepts Index\n\n"]
        lines.append("## Statistics\n\n")
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