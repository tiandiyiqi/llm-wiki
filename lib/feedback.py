"""协同反馈模块，支持评论、收藏、评分、纠错."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .yaml_parser import SimpleYAMLParser


class FeedbackManager:
    """协同反馈管理器."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()
        self.feedback_path = kb_dir / '.llm-wiki' / 'feedback.json'
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)

    def add_comment(self, atom_path: Path, text: str, author: str = '') -> bool:
        """为原子添加评论.

        Args:
            atom_path: 原子文件路径
            text: 评论内容
            author: 评论者

        Returns:
            是否成功
        """
        if not atom_path.exists() or not text:
            return False
        atom_id = self._get_atom_id(atom_path)
        data = self._load()
        comments = data.setdefault('comments', {}).setdefault(atom_id, [])
        comments.append({
            'text': text,
            'author': author or 'anonymous',
            'timestamp': datetime.now().isoformat(),
        })
        self._save(data)
        return True

    def get_comments(self, atom_path: Path) -> List[Dict]:
        """获取原子的评论列表."""
        atom_id = self._get_atom_id(atom_path)
        data = self._load()
        return data.get('comments', {}).get(atom_id, [])

    def add_favorite(self, atom_path: Path, user: str = 'default') -> bool:
        """收藏原子."""
        atom_id = self._get_atom_id(atom_path)
        data = self._load()
        favorites = data.setdefault('favorites', {}).setdefault(user, [])
        if atom_id not in favorites:
            favorites.append(atom_id)
            self._save(data)
        return True

    def remove_favorite(self, atom_path: Path, user: str = 'default') -> bool:
        """取消收藏."""
        atom_id = self._get_atom_id(atom_path)
        data = self._load()
        favorites = data.get('favorites', {}).get(user, [])
        if atom_id in favorites:
            favorites.remove(atom_id)
            self._save(data)
            return True
        return False

    def get_favorites(self, user: str = 'default') -> List[str]:
        """获取用户收藏列表."""
        data = self._load()
        return data.get('favorites', {}).get(user, [])

    def rate(self, atom_path: Path, score: int, user: str = 'default') -> bool:
        """为原子评分.

        Args:
            atom_path: 原子文件路径
            score: 评分（1-5）
            user: 评分者

        Returns:
            是否成功
        """
        if not 1 <= score <= 5:
            return False
        atom_id = self._get_atom_id(atom_path)
        data = self._load()
        ratings = data.setdefault('ratings', {}).setdefault(atom_id, {})
        ratings[user] = {
            'score': score,
            'timestamp': datetime.now().isoformat(),
        }
        self._save(data)
        return True

    def get_rating(self, atom_path: Path) -> Dict:
        """获取原子评分统计.

        Returns:
            {'average': float, 'count': int, 'scores': {user: score}}
        """
        atom_id = self._get_atom_id(atom_path)
        data = self._load()
        ratings = data.get('ratings', {}).get(atom_id, {})
        if not ratings:
            return {'average': 0, 'count': 0, 'scores': {}}
        scores = [r['score'] for r in ratings.values()]
        return {
            'average': sum(scores) / len(scores),
            'count': len(scores),
            'scores': {u: r['score'] for u, r in ratings.items()},
        }

    def submit_correction(self, atom_path: Path, description: str,
                          submitter: str = '') -> bool:
        """提交纠错.

        Args:
            atom_path: 原子文件路径
            description: 纠错描述
            submitter: 提交者

        Returns:
            是否成功
        """
        atom_id = self._get_atom_id(atom_path)
        data = self._load()
        corrections = data.setdefault('corrections', [])
        corrections.append({
            'atom_id': atom_id,
            'description': description,
            'submitter': submitter or 'anonymous',
            'status': 'pending',
            'timestamp': datetime.now().isoformat(),
        })
        self._save(data)
        return True

    def get_corrections(self, status: Optional[str] = None) -> List[Dict]:
        """获取纠错列表."""
        data = self._load()
        corrections = data.get('corrections', [])
        if status:
            return [c for c in corrections if c.get('status') == status]
        return corrections

    def _get_atom_id(self, atom_path: Path) -> str:
        """获取原子的相对路径 ID."""
        try:
            return str(atom_path.relative_to(self.kb_dir))
        except ValueError:
            return str(atom_path)

    def _load(self) -> Dict:
        """加载反馈数据."""
        try:
            return json.loads(self.feedback_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self, data: Dict) -> None:
        """保存反馈数据."""
        self.feedback_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8'
        )
