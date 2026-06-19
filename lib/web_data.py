"""静态 Web UI 数据导出

将知识库数据导出为静态 JSON 文件，供前端页面读取。
"""

import json
from pathlib import Path
from typing import Dict, List

from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser


class WebDataExporter:
    """导出知识库数据为静态 JSON"""

    def __init__(self, kb_dir: Path):
        self.kb_dir = Path(kb_dir)
        self.output_dir = self.kb_dir / "views" / "data"
        self.yaml_parser = SimpleYAMLParser()

    def export_all(self) -> Dict[str, int]:
        """导出所有数据"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        atoms_count = self.export_atoms()
        gaps_count = self.export_gaps()

        print(f"✅ 已导出静态数据到 {self.output_dir}")
        print(f"   atoms.json: {atoms_count} 个原子")
        print(f"   gaps.json: {gaps_count} 个缺口")

        return {'atoms': atoms_count, 'gaps': gaps_count}

    def export_atoms(self) -> int:
        """导出原子列表为 atoms.json"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        atoms: List[Dict] = []
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
                        atoms.append({
                            'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
                            'path': str(md_file.relative_to(self.kb_dir)),
                            'type': fm.get('type', 'Unknown'),
                            'title': fm.get('title', md_file.stem),
                            'description': fm.get('description', ''),
                            'tags': fm.get('tags', []),
                            'timestamp': fm.get('timestamp', fm.get('created', '')),
                            'confidence': fm.get('confidence', 0),
                            'content': body.strip()[:500]
                        })

        output_file = self.output_dir / 'atoms.json'
        output_file.write_text(
            json.dumps(atoms, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        return len(atoms)

    def export_gaps(self) -> int:
        """导出缺口为 gaps.json"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            from .discovery import DiscoveryEngine
            finder = DiscoveryEngine(self.kb_dir)
            raw_gaps = finder.find_gaps()

            gap_list = []
            for gap in raw_gaps:
                gap_list.append({
                    'type': gap.get('type', 'unknown'),
                    'severity': gap.get('severity', 'medium'),
                    'title': gap.get('title', ''),
                    'description': gap.get('description', ''),
                    'path': gap.get('path', ''),
                    'suggestion': gap.get('suggestion', '')
                })

        except Exception:
            gap_list = []

        output_file = self.output_dir / 'gaps.json'
        output_file.write_text(
            json.dumps(gap_list, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        return len(gap_list)
