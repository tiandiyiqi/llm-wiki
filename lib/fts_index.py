"""全文索引模块，基于 SQLite FTS5 实现高效全文检索（Python 内置，零依赖）."""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser

# 可选中文分词
try:
    import jieba  # type: ignore
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


class FTSIndex:
    """SQLite FTS5 全文索引."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.db_path = kb_dir / '.llm-wiki' / 'fts_index.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.yaml_parser = SimpleYAMLParser()
        self._init_db()

    def _init_db(self) -> None:
        """初始化 FTS5 数据库."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # 检查 FTS5 是否可用
            try:
                conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS atoms_fts USING fts5("
                             "atom_id, title, description, body, tags, type, "
                             "path, timestamp, "
                             "content='atoms', content_rowid='rowid')")
            except sqlite3.OperationalError:
                # FTS5 不可用，回退到普通表
                conn.execute("CREATE TABLE IF NOT EXISTS atoms_fts ("
                             "atom_id TEXT, title TEXT, description TEXT, "
                             "body TEXT, tags TEXT, type TEXT, "
                             "path TEXT, timestamp TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS atoms_meta ("
                         "atom_id TEXT PRIMARY KEY, "
                         "path TEXT, mtime REAL, indexed_at TEXT)")

    def index_all(self) -> int:
        """索引所有原子.

        Returns:
            索引的原子数量
        """
        atoms = self._load_all_atoms()
        count = 0
        with sqlite3.connect(str(self.db_path)) as conn:
            # 清空旧索引
            conn.execute("DELETE FROM atoms_fts")
            conn.execute("DELETE FROM atoms_meta")

            for atom in atoms:
                self._index_atom(conn, atom)
                count += 1
            conn.commit()
        return count

    def index_incremental(self) -> Tuple[int, int]:
        """增量索引（仅更新新增/修改的原子）.

        Returns:
            (新增数, 更新数)
        """
        atoms = self._load_all_atoms()
        added = 0
        updated = 0

        with sqlite3.connect(str(self.db_path)) as conn:
            # 获取已索引的原子
            cursor = conn.execute("SELECT atom_id, mtime FROM atoms_meta")
            indexed = {row[0]: row[1] for row in cursor.fetchall()}

            current_ids = set()
            for atom in atoms:
                atom_id = atom['id']
                current_ids.add(atom_id)
                current_mtime = atom.get('file_mtime', 0)

                if atom_id not in indexed:
                    # 新增
                    self._index_atom(conn, atom)
                    added += 1
                elif indexed[atom_id] < current_mtime:
                    # 更新
                    conn.execute("DELETE FROM atoms_fts WHERE atom_id = ?", (atom_id,))
                    self._index_atom(conn, atom)
                    updated += 1

            # 删除已不存在的原子
            for old_id in set(indexed.keys()) - current_ids:
                conn.execute("DELETE FROM atoms_fts WHERE atom_id = ?", (old_id,))
                conn.execute("DELETE FROM atoms_meta WHERE atom_id = ?", (old_id,))

            conn.commit()

        return added, updated

    def search(self, query: str, limit: int = 10,
               by_type: Optional[str] = None) -> List[Dict]:
        """全文搜索.

        Args:
            query: 查询字符串
            limit: 结果数量上限
            by_type: 按类型过滤

        Returns:
            搜索结果列表
        """
        # 分词处理
        tokens = self._tokenize(query)
        if not tokens:
            return []

        # 构建 FTS5 查询
        fts_query = ' AND '.join(f'"{t}"' for t in tokens)

        with sqlite3.connect(str(self.db_path)) as conn:
            try:
                # 尝试 FTS5 查询
                if by_type:
                    sql = ("SELECT atom_id, title, description, path, type, tags, "
                           "snippet(atoms_fts, 3, '>>', '<<', '...', 20) as snippet "
                           "FROM atoms_fts WHERE atoms_fts MATCH ? AND type = ? "
                           "ORDER BY rank LIMIT ?")
                    cursor = conn.execute(sql, (fts_query, by_type, limit))
                else:
                    sql = ("SELECT atom_id, title, description, path, type, tags, "
                           "snippet(atoms_fts, 3, '>>', '<<', '...', 20) as snippet "
                           "FROM atoms_fts WHERE atoms_fts MATCH ? "
                           "ORDER BY rank LIMIT ?")
                    cursor = conn.execute(sql, (fts_query, limit))
            except sqlite3.OperationalError:
                # FTS5 不可用，回退到 LIKE 查询
                like_query = f"%{query}%"
                if by_type:
                    sql = ("SELECT atom_id, title, description, path, type, tags "
                           "FROM atoms_fts WHERE "
                           "(title LIKE ? OR description LIKE ? OR body LIKE ?) "
                           "AND type = ? LIMIT ?")
                    cursor = conn.execute(sql, (like_query, like_query, like_query,
                                                by_type, limit))
                else:
                    sql = ("SELECT atom_id, title, description, path, type, tags "
                           "FROM atoms_fts WHERE "
                           "title LIKE ? OR description LIKE ? OR body LIKE ? LIMIT ?")
                    cursor = conn.execute(sql, (like_query, like_query, like_query, limit))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'path': row[3],
                    'type': row[4],
                    'tags': row[5].split(',') if row[5] else [],
                    'snippet': row[6] if len(row) > 6 else '',
                    'match_type': 'fts',
                })
            return results

    def _index_atom(self, conn: sqlite3.Connection, atom: Dict) -> None:
        """索引单个原子."""
        tags_str = ','.join(atom.get('tags', []))
        try:
            conn.execute(
                "INSERT INTO atoms_fts (atom_id, title, description, body, tags, type, path, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (atom['id'], atom['title'], atom['description'],
                 atom.get('body', ''), tags_str, atom['type'],
                 atom['path'], atom.get('timestamp', ''))
            )
        except sqlite3.OperationalError:
            # FTS5 不可用时使用普通 INSERT
            conn.execute(
                "INSERT INTO atoms_fts (atom_id, title, description, body, tags, type, path, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (atom['id'], atom['title'], atom['description'],
                 atom.get('body', ''), tags_str, atom['type'],
                 atom['path'], atom.get('timestamp', ''))
            )

        conn.execute(
            "INSERT OR REPLACE INTO atoms_meta (atom_id, path, mtime, indexed_at) "
            "VALUES (?, ?, ?, ?)",
            (atom['id'], atom['path'], atom.get('file_mtime', 0),
             datetime.now().isoformat())
        )

    def _tokenize(self, text: str) -> List[str]:
        """分词.

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        if JIEBA_AVAILABLE:
            # 使用 jieba 中文分词
            tokens = [t.strip() for t in jieba.cut(text) if t.strip() and len(t.strip()) > 1]
        else:
            # 简单分词：按空格和标点分割
            tokens = re.findall(r'[\w\u4e00-\u9fff]+', text)
            # 对中文进一步拆分（二元）
            result = []
            for token in tokens:
                if re.match(r'^[\u4e00-\u9fff]+$', token) and len(token) > 2:
                    # 中文二元分词
                    for i in range(len(token) - 1):
                        result.append(token[i:i+2])
                    result.append(token)
                else:
                    result.append(token)
            tokens = result
        return tokens

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
                'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
                'path': str(md_file.relative_to(self.kb_dir)),
                'type': fm.get('type', 'Unknown'),
                'title': fm.get('title', md_file.stem),
                'description': fm.get('description', ''),
                'tags': tags,
                'timestamp': fm.get('timestamp', ''),
                'body': parts[2],
                'file_mtime': md_file.stat().st_mtime,
            })
        return atoms

    def get_stats(self) -> Dict:
        """获取索引统计."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM atoms_fts")
            total = cursor.fetchone()[0]
            cursor = conn.execute("SELECT COUNT(*) FROM atoms_meta")
            meta_count = cursor.fetchone()[0]
        return {
            'total_indexed': total,
            'meta_count': meta_count,
            'jieba_available': JIEBA_AVAILABLE,
            'db_path': str(self.db_path),
        }
