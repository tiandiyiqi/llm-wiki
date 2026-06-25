"""Generates timeline view of knowledge atoms."""

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser


class TimelineGenerator:
    """Generates timeline view HTML for knowledge atoms."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()
        self.events: List[Dict] = []

    def generate_json_data(self) -> Dict:
        """Generate timeline JSON data."""
        self._load_events()

        # Sort events by date (newest first)
        self.events.sort(key=lambda x: x['date'], reverse=True)

        # Calculate statistics
        stats = {
            'total': len(self.events),
            'by_type': {},
            'by_month': {}
        }

        for event in self.events:
            # Count by type
            event_type = event['type']
            stats['by_type'][event_type] = stats['by_type'].get(event_type, 0) + 1

            # Count by month (YYYY-MM format)
            month = event['date'][:7] if len(event['date']) >= 7 else event['date']
            stats['by_month'][month] = stats['by_month'].get(month, 0) + 1

        # Sort by_type by count (descending)
        stats['by_type'] = dict(sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True))

        # Sort by_month by month (descending)
        stats['by_month'] = dict(sorted(stats['by_month'].items(), key=lambda x: x[0], reverse=True))

        return {
            'events': self.events,
            'stats': stats
        }

    def generate(self, output_path: Path) -> bool:
        """Generate timeline HTML file."""
        print(f"📅 Generating timeline: {self.kb_dir}")
        print(f"   Output: {output_path}")

        data = self.generate_json_data()

        if not data['events']:
            print("   No events found in knowledge base")
            return False

        print(f"   Events: {data['stats']['total']}")

        # Generate HTML
        html_content = self._generate_html(data)

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding='utf-8')

        print(f"\n✅ Timeline created: {output_path}")
        print(f"   Open in browser to view timeline")

        return True

    def _load_events(self) -> None:
        """Load all knowledge atoms as timeline events."""
        self.events = []

        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue

            content = md_file.read_text(encoding='utf-8')

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    fm = self.yaml_parser.parse(parts[1])
                    if fm:
                        # Extract date from frontmatter
                        date = self._extract_date(fm, md_file)
                        if date:
                            relative_path = str(md_file.relative_to(self.kb_dir))
                            self.events.append({
                                'date': date,
                                'atom_id': relative_path.replace('.md', ''),
                                'title': fm.get('title', md_file.stem),
                                'type': fm.get('type', 'unknown'),
                                'path': relative_path
                            })

    def _extract_date(self, frontmatter: Dict, md_file: Path) -> Optional[str]:
        """Extract date from frontmatter or file modification time."""
        # Try created_at field
        if 'created_at' in frontmatter:
            return self._normalize_date(frontmatter['created_at'])

        # Try date field
        if 'date' in frontmatter:
            return self._normalize_date(frontmatter['date'])

        # Try updated_at field
        if 'updated_at' in frontmatter:
            return self._normalize_date(frontmatter['updated_at'])

        # Fall back to file modification time
        try:
            mtime = md_file.stat().st_mtime
            return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        except (OSError, ValueError):
            return None

    def _normalize_date(self, date_value) -> Optional[str]:
        """Normalize date value to YYYY-MM-DD format."""
        if not date_value:
            return None

        date_str = str(date_value)

        # Already in YYYY-MM-DD format
        if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
            return date_str

        # Handle YYYY-MM-DD HH:MM:SS format
        if len(date_str) >= 10:
            return date_str[:10]

        # Handle other formats
        try:
            # Try parsing with datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            return None

    def _generate_html(self, data: Dict) -> str:
        """Generate single-file HTML timeline view."""
        events = data['events']
        stats = data['stats']

        # Type color mapping（与前端 CSS 变量 theme-classic 保持一致）
        type_colors = {
            'method': '#3b82f6',
            'fact': '#22c55e',
            'definition': '#a855f7',
            'opinion': '#ef4444',
            'data': '#f97316',
            'question': '#14b8a6',
            'reference': '#6b7280'
        }

        # Generate events HTML
        events_html = []
        current_month = None

        for event in events:
            event_month = event['date'][:7] if len(event['date']) >= 7 else event['date']

            # Add month separator
            if event_month != current_month:
                current_month = event_month
                month_label = self._format_month(event_month)
                events_html.append(f'''
        <div class="month-separator">
            <span class="month-label">{html.escape(month_label)}</span>
            <span class="month-count">{stats['by_month'].get(event_month, 0)} items</span>
        </div>''')

            color = type_colors.get(event['type'], '#95a5a6')
            events_html.append(f'''
        <div class="event-item">
            <div class="event-date">{html.escape(event['date'])}</div>
            <div class="event-marker" style="background-color: {color}"></div>
            <div class="event-content">
                <div class="event-title">{html.escape(event['title'])}</div>
                <div class="event-meta">
                    <span class="event-type" style="background-color: {color}">{html.escape(event['type'])}</span>
                    <span class="event-path">{html.escape(event['path'])}</span>
                </div>
            </div>
        </div>''')

        events_html_str = '\n'.join(events_html)

        # Generate type statistics
        type_stats_html = []
        for event_type, count in stats['by_type'].items():
            color = type_colors.get(event_type, '#95a5a6')
            type_stats_html.append(f'''
                <span class="type-badge" style="background-color: {color}">
                    {html.escape(event_type)}: {count}
                </span>''')
        type_stats_html_str = ''.join(type_stats_html)

        # Generate HTML
        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>知识时间线</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
            color: #2c3e50;
        }}
        .stats {{
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .stats h2 {{
            font-size: 16px;
            color: #666;
            margin-bottom: 15px;
        }}
        .total-count {{
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        .type-badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .type-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            color: #fff;
        }}
        .timeline {{
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        .month-separator {{
            display: flex;
            align-items: center;
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        .month-separator:first-child {{
            margin-top: 0;
        }}
        .month-label {{
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
        }}
        .month-count {{
            margin-left: auto;
            font-size: 12px;
            color: #999;
        }}
        .event-item {{
            display: flex;
            align-items: flex-start;
            padding: 15px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .event-item:last-child {{
            border-bottom: none;
        }}
        .event-date {{
            width: 100px;
            flex-shrink: 0;
            font-size: 13px;
            color: #999;
            font-family: monospace;
        }}
        .event-marker {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin: 5px 15px 0 15px;
            flex-shrink: 0;
        }}
        .event-content {{
            flex: 1;
        }}
        .event-title {{
            font-size: 15px;
            font-weight: 500;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .event-meta {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .event-type {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            color: #fff;
            text-transform: uppercase;
        }}
        .event-path {{
            font-size: 12px;
            color: #999;
            font-family: monospace;
        }}
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }}
        #back-link {{
            display: none;  /* iframe 模式下默认隐藏 */
        }}
        /* 独立页面模式显示返回链接 */
        body:not(.iframe-mode) #back-link {{
            position: fixed;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: #fff;
            padding: 6px 12px;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            font-size: 13px;
            color: #666;
            text-decoration: none;
        }}
        body:not(.iframe-mode) #back-link:hover {{ color: #3498db; }}
        /* iframe 模式下隐藏 header 和调整布局 */
        body.iframe-mode .header {{
            display: none;
        }}
        body.iframe-mode .container {{
            padding-top: 20px;
        }}
    </style>
</head>
<body>
    <script>
        // 检测是否在 iframe 中，调整布局
        if (window.self !== window.top) {{
            document.body.classList.add('iframe-mode');
        }}
    </script>
    <a href="index.html" id="back-link">← 返回入口</a>
    <div class="container">
        <div class="header">
            <h1>知识时间线</h1>
            <p>按时间排序的知识原子视图</p>
        </div>

        <div class="stats">
            <h2>统计信息</h2>
            <div class="total-count">总计 {stats['total']} 个知识原子</div>
            <div class="type-badges">{type_stats_html_str}</div>
        </div>

        <div class="timeline">
{events_html_str}
        </div>
    </div>
</body>
</html>'''

        return html_content

    def _format_month(self, month_str: str) -> str:
        """Format month string (YYYY-MM) to display format."""
        try:
            year, month = month_str.split('-')
            month_names = ['一月', '二月', '三月', '四月', '五月', '六月',
                          '七月', '八月', '九月', '十月', '十一月', '十二月']
            month_idx = int(month) - 1
            if 0 <= month_idx < 12:
                return f"{year}年 {month_names[month_idx]}"
        except (ValueError, IndexError):
            pass
        return month_str
