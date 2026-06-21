"""容灾备份模块，支持定时备份、单原子恢复、云端对接."""

import json
import os
import shutil
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .constants import RESERVED_FILES


class BackupManager:
    """备份管理器."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.backup_dir = kb_dir / '.llm-wiki' / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup(self, output: Optional[Path] = None) -> Path:
        """创建完整备份.

        Args:
            output: 输出路径（None 则自动生成）

        Returns:
            备份文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if output is None:
            output = self.backup_dir / f"kb-backup-{timestamp}.tar.gz"

        # 创建 tar.gz 备份
        with tarfile.open(output, 'w:gz') as tar:
            for item in self.kb_dir.iterdir():
                # 跳过 .llm-wiki 目录（避免递归备份）
                if item.name == '.llm-wiki':
                    continue
                tar.add(item, arcname=item.name)

        # 记录备份元数据
        self._record_backup(output, 'full')
        return output

    def backup_atom(self, atom_path: Path) -> Path:
        """备份单个原子.

        Args:
            atom_path: 原子文件路径

        Returns:
            备份文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        rel_path = atom_path.relative_to(self.kb_dir) if atom_path.is_relative_to(self.kb_dir) else Path(atom_path.name)
        atom_id = str(rel_path).replace('/', '_').replace('.md', '')
        backup_path = self.backup_dir / f"atom-{atom_id}-{timestamp}.md"
        shutil.copy2(atom_path, backup_path)
        self._record_backup(backup_path, 'atom', atom_id=str(rel_path))
        return backup_path

    def restore_atom(self, atom_id: str, version: Optional[str] = None) -> bool:
        """从备份恢复单个原子.

        Args:
            atom_id: 原子 ID（相对路径，不含 .md）
            version: 版本时间戳（None 表示最新备份）

        Returns:
            是否成功
        """
        atom_id_clean = atom_id.replace('/', '_').replace('.md', '')

        # 查找备份文件
        if version:
            pattern = f"atom-{atom_id_clean}-{version}.md"
            backups = list(self.backup_dir.glob(pattern))
        else:
            pattern = f"atom-{atom_id_clean}-*.md"
            backups = sorted(self.backup_dir.glob(pattern), reverse=True)

        if not backups:
            # 尝试从 Git 恢复
            return self._restore_from_git(atom_id, version)

        backup_file = backups[0]
        # 恢复到原位置
        target_path = self.kb_dir / f"{atom_id}.md"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_file, target_path)
        return True

    def list_backups(self, atom_id: Optional[str] = None) -> List[Dict]:
        """列出备份.

        Args:
            atom_id: 指定原子 ID（None 列出所有）

        Returns:
            备份信息列表
        """
        backups = []
        for item in sorted(self.backup_dir.iterdir(), reverse=True):
            if item.is_file():
                stat = item.stat()
                backups.append({
                    'file': item.name,
                    'path': str(item),
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'type': 'atom' if item.name.startswith('atom-') else 'full',
                })
        return backups

    def clean_old_backups(self, keep_count: int = 10) -> int:
        """清理旧备份，保留最近 N 个.

        Args:
            keep_count: 保留数量

        Returns:
            清理的文件数
        """
        backups = sorted(self.backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        removed = 0
        for item in backups[keep_count:]:
            if item.is_file():
                item.unlink()
                removed += 1
        return removed

    def schedule_backup(self, frequency: str = 'daily') -> str:
        """生成定时备份脚本（crontab 格式）.

        Args:
            frequency: 频率（daily/weekly/hourly）

        Returns:
            crontab 配置行
        """
        kb_path = str(self.kb_dir.resolve())
        cmd = f"cd {kb_path} && python3 llm-wiki.py backup --output {kb_path}/.llm-wiki/backups/auto-$(date +%Y%m%d_%H%M%S).tar.gz"

        if frequency == 'hourly':
            cron = f"0 * * * * {cmd}"
        elif frequency == 'weekly':
            cron = f"0 0 * * 0 {cmd}"
        else:  # daily
            cron = f"0 0 * * * {cmd}"

        return cron

    def _restore_from_git(self, atom_id: str, version: Optional[str] = None) -> bool:
        """从 Git 恢复原子."""
        try:
            file_path = f"{atom_id}.md"
            if version:
                # 恢复指定版本
                result = subprocess.run(
                    ['git', 'checkout', version, '--', file_path],
                    cwd=str(self.kb_dir),
                    capture_output=True, text=True, timeout=10
                )
            else:
                # 恢复最近一次提交的版本
                result = subprocess.run(
                    ['git', 'checkout', 'HEAD', '--', file_path],
                    cwd=str(self.kb_dir),
                    capture_output=True, text=True, timeout=10
                )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, TimeoutError):
            return False

    def _record_backup(self, backup_path: Path, backup_type: str,
                       atom_id: str = '') -> None:
        """记录备份元数据."""
        meta_path = self.backup_dir / 'backup-meta.json'
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            meta = {'backups': []}

        meta['backups'].append({
            'file': backup_path.name,
            'type': backup_type,
            'atom_id': atom_id,
            'created': datetime.now().isoformat(),
            'size': backup_path.stat().st_size if backup_path.exists() else 0,
        })

        # 仅保留最近 100 条记录
        if len(meta['backups']) > 100:
            meta['backups'] = meta['backups'][-100:]

        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8'
        )
