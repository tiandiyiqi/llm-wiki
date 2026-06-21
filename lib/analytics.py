"""数据统计分析模块，提供知识库统计、热门文档、高频搜索词、趋势分析、报表导出."""

import csv
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser


class AnalyticsEngine:
    """统计分析引擎."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()
        self.analytics_path = kb_dir / '.llm-wiki' / 'analytics.json'
        self.analytics_path.parent.mkdir(parents=True, exist_ok=True)

    def get_stats(self) -> Dict:
        """获取完整统计数据.

        Returns:
            统计数据字典
        """
        atoms = self._load_all_atoms()
        search_history = self._load_search_history()

        # 类型分布
        by_type: Dict[str, int] = Counter(a.get('type', 'Unknown') for a in atoms)

        # 状态分布
        by_status: Dict[str, int] = Counter(a.get('status', 'published') for a in atoms)

        # 标签统计
        all_tags = []
        for a in atoms:
            all_tags.extend(a.get('tags', []))
        by_tag: Dict[str, int] = Counter(all_tags)

        # 作者统计
        by_author: Dict[str, int] = Counter(
            a.get('author', 'unknown') for a in atoms if a.get('author')
        )

        # 时间趋势（按月）
        by_month: Dict[str, int] = Counter()
        for a in atoms:
            ts = a.get('timestamp', '')
            if ts and len(ts) >= 7:
                by_month[ts[:7]] += 1

        # 热门文档（按访问量，如果有）
        views = self._load_views()
        popular = sorted(views.items(), key=lambda x: x[1], reverse=True)[:10]

        # 高频搜索词
        hot_queries: Dict[str, int] = Counter(
            item.get('query', '') for item in search_history if item.get('query')
        )

        # 无结果搜索词
        no_result = [
            item.get('query', '') for item in search_history
            if item.get('result_count', 0) == 0 and item.get('query')
        ]

        # 最近活动
        recent_activity = self._get_recent_activity(atoms)

        return {
            'total_atoms': len(atoms),
            'by_type': dict(by_type),
            'by_status': dict(by_status),
            'by_tag': dict(by_tag),
            'total_tags': len(by_tag),
            'by_author': dict(by_author),
            'total_authors': len(by_author),
            'by_month': dict(sorted(by_month.items())),
            'popular_docs': [{'path': p, 'views': v} for p, v in popular],
            'hot_queries': [{'query': q, 'count': c} for q, c in hot_queries.most_common(10)],
            'no_result_queries': no_result[-10:],
            'recent_activity': recent_activity,
            'generated_at': datetime.now().isoformat(),
        }

    def record_view(self, atom_path: str) -> None:
        """记录一次原子访问.

        Args:
            atom_path: 原子路径
        """
        views = self._load_views()
        views[atom_path] = views.get(atom_path, 0) + 1
        self._save_views(views)

    def export_report(self, output_path: Path) -> None:
        """导出统计报告到 CSV.

        Args:
            output_path: 输出路径
        """
        stats = self.get_stats()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['LLM Wiki 统计报告'])
            writer.writerow(['生成时间', stats.get('generated_at', '')])
            writer.writerow([])
            writer.writerow(['原子总数', stats.get('total_atoms', 0)])
            writer.writerow([])
            writer.writerow(['类型分布'])
            writer.writerow(['类型', '数量'])
            for t, n in stats.get('by_type', {}).items():
                writer.writerow([t, n])
            writer.writerow([])
            writer.writerow(['状态分布'])
            writer.writerow(['状态', '数量'])
            for s, n in stats.get('by_status', {}).items():
                writer.writerow([s, n])
            writer.writerow([])
            writer.writerow(['标签统计'])
            writer.writerow(['标签', '数量'])
            for t, n in stats.get('by_tag', {}).items():
                writer.writerow([t, n])
            writer.writerow([])
            writer.writerow(['月度趋势'])
            writer.writerow(['月份', '新增数量'])
            for m, n in stats.get('by_month', {}).items():
                writer.writerow([m, n])
            writer.writerow([])
            writer.writerow(['热门文档'])
            writer.writerow(['路径', '访问量'])
            for doc in stats.get('popular_docs', []):
                writer.writerow([doc['path'], doc['views']])
            writer.writerow([])
            writer.writerow(['高频搜索词'])
            writer.writerow(['查询词', '搜索次数'])
            for q in stats.get('hot_queries', []):
                writer.writerow([q['query'], q['count']])

    def _load_all_atoms(self) -> List[Dict]:
        """加载所有原子."""
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
            tags = fm.get('tags', [])
            if not isinstance(tags, list):
                tags = [tags] if tags else []
            atoms.append({
                'path': str(md_file.relative_to(self.kb_dir)),
                'type': fm.get('type', 'Unknown'),
                'title': fm.get('title', md_file.stem),
                'tags': tags,
                'author': fm.get('author', ''),
                'status': fm.get('status', 'published'),
                'timestamp': fm.get('timestamp', ''),
            })
        return atoms

    def _load_search_history(self) -> List[Dict]:
        """加载搜索历史."""
        history_path = self.kb_dir / '.llm-wiki' / 'search-history.json'
        try:
            return json.loads(history_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _load_views(self) -> Dict[str, int]:
        """加载访问量数据."""
        try:
            return json.loads(self.analytics_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_views(self, views: Dict[str, int]) -> None:
        """保存访问量数据."""
        self.analytics_path.write_text(
            json.dumps(views, indent=2, ensure_ascii=False), encoding='utf-8'
        )

    def _get_recent_activity(self, atoms: List[Dict]) -> List[str]:
        """获取最近活动."""
        sorted_atoms = sorted(atoms, key=lambda x: x.get('timestamp', ''), reverse=True)
        return [
            f"[{a.get('timestamp', '')[:10]}] {a.get('type', '?')} - {a.get('title', '')}"
            for a in sorted_atoms[:10]
            if a.get('timestamp')
        ]
