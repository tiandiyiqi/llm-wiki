"""内容生命周期管理模块，支持 draft/review/published/archived/deprecated 状态流转."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .yaml_parser import SimpleYAMLParser


# 有效状态及流转规则
VALID_STATUSES = ['draft', 'review', 'published', 'archived', 'deprecated']

# 状态流转图：key 可流转到 value 列表中的任一状态
STATUS_TRANSITIONS = {
    'draft': ['review', 'published', 'archived', 'deprecated'],
    'review': ['published', 'draft', 'deprecated'],
    'published': ['archived', 'deprecated', 'review'],
    'archived': ['published', 'deprecated'],
    'deprecated': ['published', 'archived'],
}


class LifecycleManager:
    """原子生命周期管理器."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()

    def get_status(self, atom_path: Path) -> str:
        """获取原子当前状态.

        Args:
            atom_path: 原子文件路径

        Returns:
            状态字符串（默认 published）
        """
        fm = self._read_frontmatter(atom_path)
        return fm.get('status', 'published') if fm else 'published'

    def change_status(self, atom_path: Path, new_status: str,
                      force: bool = False) -> bool:
        """修改原子状态.

        Args:
            atom_path: 原子文件路径
            new_status: 新状态
            force: 是否强制跳过流转规则校验

        Returns:
            是否成功
        """
        if new_status not in VALID_STATUSES:
            return False

        if not atom_path.exists():
            return False

        fm = self._read_frontmatter(atom_path)
        if not fm:
            return False

        current_status = fm.get('status', 'published')

        # 校验流转规则
        if not force and current_status != new_status:
            allowed = STATUS_TRANSITIONS.get(current_status, [])
            if new_status not in allowed:
                return False

        # 更新状态
        fm['status'] = new_status
        fm['status_updated'] = datetime.now().isoformat()

        # 写回文件
        return self._write_frontmatter(atom_path, fm)

    def publish(self, atom_path: Path) -> bool:
        """发布原子."""
        return self.change_status(atom_path, 'published')

    def archive(self, atom_path: Path) -> bool:
        """归档原子."""
        return self.change_status(atom_path, 'archived')

    def deprecate(self, atom_path: Path) -> bool:
        """废弃原子."""
        return self.change_status(atom_path, 'deprecated')

    def submit_for_review(self, atom_path: Path) -> bool:
        """提交审核."""
        return self.change_status(atom_path, 'review')

    def revert_to_draft(self, atom_path: Path) -> bool:
        """回退到草稿."""
        return self.change_status(atom_path, 'draft')

    def _read_frontmatter(self, atom_path: Path) -> Optional[dict]:
        """读取原子的 frontmatter."""
        content = atom_path.read_text(encoding='utf-8')
        if not content.startswith('---'):
            return None
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None
        return self.yaml_parser.parse(parts[1])

    def _write_frontmatter(self, atom_path: Path, fm: dict) -> bool:
        """写回 frontmatter."""
        content = atom_path.read_text(encoding='utf-8')
        parts = content.split('---', 2)
        if len(parts) < 3:
            return False
        yaml_str = self.yaml_parser.dump(fm)
        new_content = f"---\n{yaml_str}\n---\n{parts[2]}"
        atom_path.write_text(new_content, encoding='utf-8')
        return True
