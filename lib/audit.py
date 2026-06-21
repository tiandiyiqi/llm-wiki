"""操作日志审计模块，记录全操作留痕到 .kb-audit.log（JSON Lines 格式）."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class AuditLogger:
    """审计日志记录器，使用 JSON Lines 格式存储."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.log_path = kb_dir / '.kb-audit.log'

    def log(self, action: str, target: str = '', user: str = '',
            detail: str = '', extra: Optional[Dict[str, Any]] = None) -> None:
        """记录一条审计日志.

        Args:
            action: 操作类型（view/query/ingest/edit/delete/export/share/comment等）
            target: 操作目标（文件路径或原子 ID）
            user: 操作用户
            detail: 操作详情
            extra: 额外信息
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'target': target,
            'user': user,
            'detail': detail,
        }
        if extra:
            entry.update(extra)

        # 追加写入 JSON Lines
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def query(self, since: Optional[str] = None, action: Optional[str] = None,
              user: Optional[str] = None, target: Optional[str] = None,
              limit: int = 50) -> List[Dict]:
        """查询审计日志.

        Args:
            since: 起始时间（ISO 格式或日期）
            action: 按操作类型过滤
            user: 按用户过滤
            target: 按目标过滤
            limit: 返回数量上限

        Returns:
            审计日志条目列表（按时间倒序）
        """
        if not self.log_path.exists():
            return []

        entries = []
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # 过滤
                if since and entry.get('timestamp', '') < since:
                    continue
                if action and entry.get('action') != action:
                    continue
                if user and entry.get('user') != user:
                    continue
                if target and target not in entry.get('target', ''):
                    continue

                entries.append(entry)

        # 按时间倒序，取最近 limit 条
        entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return entries[:limit]

    def get_stats(self) -> Dict[str, int]:
        """获取审计日志统计."""
        if not self.log_path.exists():
            return {'total': 0}

        stats: Dict[str, int] = {'total': 0}
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                stats['total'] += 1
                action = entry.get('action', 'unknown')
                stats[action] = stats.get(action, 0) + 1
        return stats

    def export(self, output_path: Path, since: Optional[str] = None) -> int:
        """导出审计日志到文件.

        Args:
            output_path: 输出路径
            since: 起始时间

        Returns:
            导出的条目数
        """
        entries = self.query(since=since, limit=100000)
        output_path.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False), encoding='utf-8'
        )
        return len(entries)

    def clear(self, before: Optional[str] = None) -> int:
        """清理审计日志.

        Args:
            before: 清理此时间之前的日志（None 表示清空所有）

        Returns:
            清理的条目数
        """
        if not self.log_path.exists():
            return 0

        if before is None:
            # 清空所有
            count = 0
            with open(self.log_path, 'r', encoding='utf-8') as f:
                count = sum(1 for line in f if line.strip())
            self.log_path.write_text('', encoding='utf-8')
            return count

        # 保留指定时间之后的日志
        kept = []
        removed = 0
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get('timestamp', '') < before:
                    removed += 1
                else:
                    kept.append(line)

        with open(self.log_path, 'w', encoding='utf-8') as f:
            for line in kept:
                f.write(line + '\n')

        return removed
