"""增量更新与缓存模块，提供概念加载缓存、embed 增量更新、分页查询."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser


class ConceptCache:
    """概念加载缓存，基于文件 mtime 判断是否需要重新加载."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.cache_path = kb_dir / '.llm-wiki' / 'concept-cache.json'
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.yaml_parser = SimpleYAMLParser()

    def get_concepts(self, force_reload: bool = False) -> List[Dict]:
        """获取所有概念（带缓存）.

        Args:
            force_reload: 强制重新加载

        Returns:
            概念列表
        """
        cache = self._load_cache() if not force_reload else {'concepts': [], 'files': {}}
        cached_files = cache.get('files', {})
        concepts = list(cache.get('concepts', []))

        # 检查哪些文件需要更新
        current_files = {}
        files_to_reload = set()
        files_removed = set()

        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue
            rel_path = str(md_file.relative_to(self.kb_dir))
            mtime = md_file.stat().st_mtime
            current_files[rel_path] = mtime

            if rel_path not in cached_files or cached_files[rel_path] < mtime:
                files_to_reload.add(rel_path)

        # 检查被删除的文件
        for rel_path in cached_files:
            if rel_path not in current_files:
                files_removed.add(rel_path)

        # 如果没有变化，直接返回缓存
        if not files_to_reload and not files_removed and concepts:
            return concepts

        # 如果变化太大（超过50%），全量重载
        total_files = len(current_files)
        if len(files_to_reload) > total_files * 0.5 or not concepts:
            return self._full_reload(current_files)

        # 增量更新
        # 移除被删除和需要更新的旧概念
        concepts = [c for c in concepts
                    if c['path'] not in files_to_reload
                    and c['path'] not in files_removed]

        # 加载需要更新的文件
        for rel_path in files_to_reload:
            md_file = self.kb_dir / rel_path
            concept = self._load_concept(md_file)
            if concept:
                concepts.append(concept)

        # 保存缓存
        self._save_cache(concepts, current_files)
        return concepts

    def _full_reload(self, current_files: Dict[str, float]) -> List[Dict]:
        """全量重载."""
        concepts = []
        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue
            concept = self._load_concept(md_file)
            if concept:
                concepts.append(concept)
        self._save_cache(concepts, current_files)
        return concepts

    def _load_concept(self, md_file: Path) -> Optional[Dict]:
        """加载单个概念."""
        content = md_file.read_text(encoding='utf-8', errors='ignore')
        if not content.startswith('---'):
            return None
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None
        fm = self.yaml_parser.parse(parts[1])
        if not fm:
            return None
        tags = fm.get('tags', [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []
        return {
            'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
            'path': str(md_file.relative_to(self.kb_dir)),
            'type': fm.get('type', 'Unknown'),
            'title': fm.get('title', md_file.stem),
            'description': fm.get('description', ''),
            'tags': tags,
            'author': fm.get('author', ''),
            'source_type': fm.get('source_type', ''),
            'status': fm.get('status', 'published'),
            'timestamp': fm.get('timestamp', ''),
            'frontmatter': fm,
            'body': parts[2],
            'file_mtime': md_file.stat().st_mtime,
        }

    def _load_cache(self) -> Dict:
        """加载缓存."""
        try:
            return json.loads(self.cache_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return {'concepts': [], 'files': {}}

    def _save_cache(self, concepts: List[Dict], files: Dict[str, float]) -> None:
        """保存缓存."""
        # 移除 body 字段减小缓存体积
        slim_concepts = []
        for c in concepts:
            slim = {k: v for k, v in c.items() if k != 'body'}
            slim_concepts.append(slim)
        cache = {
            'concepts': slim_concepts,
            'files': files,
            'updated_at': datetime.now().isoformat(),
        }
        self.cache_path.write_text(
            json.dumps(cache, ensure_ascii=False), encoding='utf-8'
        )

    def clear(self) -> None:
        """清空缓存."""
        if self.cache_path.exists():
            self.cache_path.unlink()


class EmbedIncremental:
    """embed 向量增量更新管理器."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.state_path = kb_dir / '.llm-wiki' / 'embed-state.json'
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def get_pending_atoms(self) -> Tuple[List[str], List[str]]:
        """获取需要新增/更新 embed 的原子.

        Returns:
            (新增的原子 ID 列表, 需要更新的原子 ID 列表)
        """
        state = self._load_state()
        embedded_files = state.get('embedded_files', {})

        added = []
        updated = []
        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue
            rel_path = str(md_file.relative_to(self.kb_dir))
            mtime = md_file.stat().st_mtime

            if rel_path not in embedded_files:
                added.append(rel_path)
            elif embedded_files[rel_path] < mtime:
                updated.append(rel_path)

        return added, updated

    def mark_embedded(self, file_paths: List[str]) -> None:
        """标记文件已 embed.

        Args:
            file_paths: 已 embed 的文件路径列表
        """
        state = self._load_state()
        embedded_files = state.setdefault('embedded_files', {})
        for path in file_paths:
            md_file = self.kb_dir / path
            if md_file.exists():
                embedded_files[path] = md_file.stat().st_mtime
        state['last_embed_at'] = datetime.now().isoformat()
        self._save_state(state)

    def remove_embedded(self, file_paths: List[str]) -> None:
        """移除已 embed 的文件记录（文件被删除时调用）."""
        state = self._load_state()
        embedded_files = state.get('embedded_files', {})
        for path in file_paths:
            embedded_files.pop(path, None)
        self._save_state(state)

    def _load_state(self) -> Dict:
        """加载 embed 状态."""
        try:
            return json.loads(self.state_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return {'embedded_files': {}}

    def _save_state(self, state: Dict) -> None:
        """保存 embed 状态."""
        self.state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8'
        )


class PaginatedQuerier:
    """分页查询器."""

    def __init__(self, kb_dir: Path, page_size: int = 20):
        self.kb_dir = kb_dir
        self.page_size = page_size
        self.cache = ConceptCache(kb_dir)

    def query_paginated(self, query_str: str = '', by_type: Optional[str] = None,
                        page: int = 1, sort_by: str = 'relevance') -> Dict:
        """分页查询.

        Args:
            query_str: 查询字符串（空表示列出全部）
            by_type: 类型过滤
            page: 页码（从1开始）
            sort_by: 排序方式

        Returns:
            {'results': [], 'page': int, 'total_pages': int, 'total_count': int}
        """
        concepts = self.cache.get_concepts()

        # 过滤
        if by_type:
            concepts = [c for c in concepts if c['type'] == by_type]

        if query_str:
            query_lower = query_str.lower()
            keywords = [k for k in query_str.split() if k]
            scored = []
            for concept in concepts:
                score = self._calculate_score(concept, query_lower, keywords)
                if score > 0:
                    concept['score'] = score
                    scored.append(concept)
            concepts = scored

        # 排序
        if sort_by == 'time':
            concepts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        elif sort_by == 'title':
            concepts.sort(key=lambda x: x.get('title', '').lower())
        elif sort_by == 'relevance':
            concepts.sort(key=lambda x: x.get('score', 0), reverse=True)

        # 分页
        total = len(concepts)
        total_pages = (total + self.page_size - 1) // self.page_size if total > 0 else 0
        start = (page - 1) * self.page_size
        end = start + self.page_size
        page_results = concepts[start:end]

        return {
            'results': page_results,
            'page': page,
            'page_size': self.page_size,
            'total_pages': total_pages,
            'total_count': total,
        }

    def _calculate_score(self, concept: Dict, query_lower: str, keywords: List[str]) -> int:
        """计算相关性得分."""
        score = 0
        if query_lower in concept['title'].lower():
            score += 100
        for kw in keywords:
            if kw.lower() in concept['title'].lower():
                score += 50
        if query_lower in concept['description'].lower():
            score += 50
        for tag in concept.get('tags', []):
            if query_lower in tag.lower():
                score += 30
        return score
