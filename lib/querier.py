"""查询知识原子（单库与聚合查询），支持关键词高亮、多维筛选、排序、无结果推荐、联想提示、段落溯源."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser


# ANSI 颜色码常量，用于终端关键词高亮
ANSI_RESET = '\033[0m'
ANSI_HIGHLIGHT = '\033[93;1m'  # 亮黄色加粗


def highlight_text(text: str, keywords: List[str]) -> str:
    """高亮文本中的关键词（ANSI 色码）.

    Args:
        text: 原始文本
        keywords: 需要高亮的关键词列表

    Returns:
        带 ANSI 高亮码的文本
    """
    if not keywords:
        return text
    result = text
    for kw in keywords:
        if not kw:
            continue
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        result = pattern.sub(lambda m: f"{ANSI_HIGHLIGHT}{m.group()}{ANSI_RESET}", result)
    return result


def extract_snippet(body: str, keywords: List[str], context_chars: int = 80) -> str:
    """从正文中提取匹配关键词的片段（带上下文）.

    Args:
        body: 原子正文
        keywords: 查询关键词列表
        context_chars: 上下文字符数

    Returns:
        匹配片段字符串，无匹配时返回空字符串
    """
    if not body or not keywords:
        return ''
    body_lower = body.lower()
    for kw in keywords:
        if not kw:
            continue
        idx = body_lower.find(kw.lower())
        if idx >= 0:
            start = max(0, idx - context_chars)
            end = min(len(body), idx + len(kw) + context_chars)
            snippet = body[start:end]
            if start > 0:
                snippet = '...' + snippet
            if end < len(body):
                snippet = snippet + '...'
            return snippet
    return ''


class SearchHistory:
    """搜索历史记录，用于联想提示和高频词统计."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.history_path = kb_dir / '.llm-wiki' / 'search-history.json'
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, query: str, result_count: int) -> None:
        """记录一次搜索查询.

        Args:
            query: 查询字符串
            result_count: 结果数量
        """
        history = self._load()
        history.append({
            'query': query,
            'result_count': result_count,
            'timestamp': datetime.now().isoformat()
        })
        # 仅保留最近 1000 条
        if len(history) > 1000:
            history = history[-1000:]
        self._save(history)

    def get_suggestions(self, prefix: str, limit: int = 5) -> List[str]:
        """根据前缀获取搜索联想建议.

        Args:
            prefix: 输入前缀
            limit: 返回数量上限

        Returns:
            联想建议列表
        """
        if not prefix:
            return []
        history = self._load()
        prefix_lower = prefix.lower()
        # 统计频次
        freq: Dict[str, int] = {}
        for item in history:
            q = item.get('query', '')
            if q.lower().startswith(prefix_lower) and len(q) > len(prefix):
                freq[q] = freq.get(q, 0) + 1
        # 按频次排序
        sorted_items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [item[0] for item in sorted_items[:limit]]

    def get_hot_queries(self, limit: int = 10) -> List[Tuple[str, int]]:
        """获取高频搜索词.

        Args:
            limit: 返回数量上限

        Returns:
            (查询词, 频次) 列表
        """
        history = self._load()
        freq: Dict[str, int] = {}
        for item in history:
            q = item.get('query', '')
            if q:
                freq[q] = freq.get(q, 0) + 1
        sorted_items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:limit]

    def get_no_result_queries(self, limit: int = 10) -> List[str]:
        """获取无结果的搜索词.

        Args:
            limit: 返回数量上限

        Returns:
            无结果查询词列表
        """
        history = self._load()
        no_result = [item.get('query', '') for item in history
                     if item.get('result_count', 0) == 0 and item.get('query')]
        return no_result[-limit:] if no_result else []

    def _load(self) -> List[Dict]:
        """加载搜索历史."""
        try:
            return json.loads(self.history_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save(self, data: List[Dict]) -> None:
        """保存搜索历史."""
        self.history_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8'
        )


class AggregatedQuerier:
    """聚合查询父知识库及其所有子知识库."""

    def __init__(self, kb_dir: Path, registry: Optional['KBRegistry'] = None):
        self.kb_dir = kb_dir
        self.registry = registry
        self.children: List[Tuple[Path, str]] = []
        self.all_concepts: List[Dict] = []

    def discover_children(self) -> List[Tuple[Path, str]]:
        """发现并加载所有子知识库路径."""
        child_paths: List[Tuple[Path, str]] = []
        meta_path = self.kb_dir / '.kb-meta.json'
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                for child_name, rel_path in meta.get('children_paths', {}).items():
                    child_full_path = self.kb_dir / rel_path.rstrip('/')
                    if child_full_path.exists():
                        child_paths.append((child_full_path, child_name))
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        if self.registry:
            kb_name = self.kb_dir.name
            kb_info = self.registry.get(kb_name)
            if kb_info and kb_info.get('children'):
                for child_name in kb_info.get('children', []):
                    child_kb = self.registry.get(child_name)
                    if child_kb and child_kb.get('path'):
                        child_full_path = Path(child_kb['path'])
                        if child_full_path.exists():
                            if not any(p[1] == child_name for p in child_paths):
                                child_paths.append((child_full_path, child_name))

        self.children = child_paths
        return child_paths

    def aggregate_query(self, query_str: str, limit: int = 10, by_type: Optional[str] = None,
                        child_filter: Optional[str] = None, **filters) -> List[Dict]:
        """聚合搜索所有知识库.

        Args:
            query_str: 查询字符串
            limit: 结果数量上限
            by_type: 按类型过滤
            child_filter: 仅搜索指定子知识库
            **filters: 其他过滤条件（tag, author, date_from, date_to, source_type, status）

        Returns:
            搜索结果列表
        """
        children = self.discover_children()

        # 加载父知识库概念
        parent_querier = KnowledgeQuerier(self.kb_dir)
        parent_querier._load_concepts()
        for concept in parent_querier.concepts:
            concept['source'] = self.kb_dir.name
            concept['source_type_label'] = 'parent'

        self.all_concepts = list(parent_querier.concepts)

        # 加载子知识库概念
        for child_path, child_name in children:
            if child_filter and child_name != child_filter:
                continue
            child_querier = KnowledgeQuerier(child_path)
            child_querier._load_concepts()
            for concept in child_querier.concepts:
                concept['source'] = child_name
                concept['source_type_label'] = 'child'
                concept['display_path'] = f"{child_name}/{concept['path']}"
                self.all_concepts.append(concept)

        # 搜索
        results = self._search(query_str, by_type, **filters)
        results = results[:limit]
        return results

    def query_child(self, child_name: str, query_str: str, **filters) -> List[Dict]:
        """仅查询指定子知识库.

        Args:
            child_name: 子知识库名称
            query_str: 查询字符串
            **filters: 过滤条件

        Returns:
            搜索结果列表
        """
        return self.aggregate_query(query_str, child_filter=child_name, **filters)

    def _search(self, query_str: str, by_type: Optional[str] = None, **filters) -> List[Dict]:
        """搜索所有概念并按相关性排序."""
        query_lower = query_str.lower()
        keywords = [k for k in query_str.split() if k]
        results = []

        for concept in self.all_concepts:
            if by_type and concept['type'] != by_type:
                continue
            if not _match_filters(concept, filters):
                continue

            score = _calculate_score(concept, query_lower, keywords)
            if score > 0:
                results.append({
                    **concept,
                    'score': score,
                    'match_type': 'keyword',
                    'snippet': extract_snippet(concept.get('body', ''), keywords),
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results


class KnowledgeQuerier:
    """搜索和查询知识原子，支持关键词高亮、多维筛选、排序、段落溯源."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()
        self.concepts: List[Dict] = []
        self.history = SearchHistory(kb_dir)

    def query(self, query_str: str, limit: int = 10, by_type: Optional[str] = None,
              semantic: bool = False, sort_by: str = 'relevance',
              highlight: bool = True, **filters) -> List[Dict]:
        """查询知识原子.

        Args:
            query_str: 查询字符串
            limit: 结果数量上限
            by_type: 按类型过滤
            semantic: 是否启用语义搜索
            sort_by: 排序方式（relevance|time|title|popularity）
            highlight: 是否高亮关键词
            **filters: 其他过滤条件（tag, author, date_from, date_to, source_type, status）

        Returns:
            搜索结果列表
        """
        # 语义搜索
        if semantic:
            return self._semantic_query(query_str, limit, by_type, **filters)

        # 关键词搜索
        self._load_concepts()
        if not self.concepts:
            return []

        keywords = [k for k in query_str.split() if k]
        results = self._search(query_str, by_type, keywords, **filters)

        # 排序
        results = _sort_results(results, sort_by)

        # 限制数量
        results = results[:limit]

        # 高亮处理
        if highlight and results:
            for r in results:
                r['title_highlighted'] = highlight_text(r['title'], keywords)
                r['description_highlighted'] = highlight_text(r['description'], keywords)
                if r.get('snippet'):
                    r['snippet_highlighted'] = highlight_text(r['snippet'], keywords)

        # 记录搜索历史
        self.history.record(query_str, len(results))

        # 无结果时推荐
        if not results:
            self._suggest_on_empty(query_str)

        return results

    def get_suggestions(self, prefix: str, limit: int = 5) -> List[str]:
        """获取搜索联想建议."""
        return self.history.get_suggestions(prefix, limit)

    def get_hot_queries(self, limit: int = 10) -> List[Tuple[str, int]]:
        """获取高频搜索词."""
        return self.history.get_hot_queries(limit)

    def get_no_result_queries(self, limit: int = 10) -> List[str]:
        """获取无结果搜索词."""
        return self.history.get_no_result_queries(limit)

    def _semantic_query(self, query_str: str, limit: int, by_type: Optional[str], **filters) -> List[Dict]:
        """语义搜索查询."""
        try:
            from .semantic import SemanticSearchEngine
            engine = SemanticSearchEngine(self.kb_dir)
            if not engine.is_available():
                print("   ⚠️  语义搜索依赖未安装，回退到关键词搜索")
                return self.query(query_str, limit, by_type, semantic=False, **filters)

            results = engine.search(query_str, limit=limit, by_type=by_type)
            # 应用额外过滤
            if filters:
                self._load_concepts()
                concepts_map = {c['id']: c for c in self.concepts}
                filtered = []
                for r in results:
                    concept = concepts_map.get(r['id'])
                    if concept and _match_filters(concept, filters):
                        filtered.append(r)
                results = filtered
            return results
        except (ImportError, RuntimeError, OSError) as e:
            print(f"   ⚠️  语义搜索失败，回退到关键词搜索: {e}")
            return self.query(query_str, limit, by_type, semantic=False, **filters)

    def _load_concepts(self) -> None:
        """加载知识库中的所有概念（幂等：已加载则直接返回）."""
        if self.concepts:
            return
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
                        self.concepts.append({
                            'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
                            'path': str(md_file.relative_to(self.kb_dir)),
                            'type': fm.get('type', 'Unknown'),
                            'title': fm.get('title', md_file.stem),
                            'description': fm.get('description', ''),
                            'tags': fm.get('tags', []) if isinstance(fm.get('tags'), list) else [],
                            'author': fm.get('author', ''),
                            'source_type': fm.get('source_type', ''),
                            'status': fm.get('status', 'published'),
                            'timestamp': fm.get('timestamp', ''),
                            'frontmatter': fm,
                            'body': body,
                            'file_mtime': md_file.stat().st_mtime,
                        })

    def _search(self, query_str: str, by_type: Optional[str],
                keywords: List[str], **filters) -> List[Dict]:
        """关键词搜索概念."""
        query_lower = query_str.lower()
        results = []

        for concept in self.concepts:
            if by_type and concept['type'] != by_type:
                continue
            if not _match_filters(concept, filters):
                continue

            score = _calculate_score(concept, query_lower, keywords)
            if score > 0:
                results.append({
                    **concept,
                    'score': score,
                    'match_type': 'keyword',
                    'snippet': extract_snippet(concept.get('body', ''), keywords),
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    def _suggest_on_empty(self, query_str: str) -> None:
        """无结果时推荐相似内容."""
        if not self.concepts:
            return
        # 基于关键词重叠推荐 Top 3
        keywords = set(query_str.lower().split())
        scored = []
        for concept in self.concepts:
            concept_words = set(concept['title'].lower().split())
            concept_words.update(w.lower() for w in concept.get('tags', []))
            overlap = len(keywords & concept_words)
            if overlap > 0:
                scored.append((overlap, concept))
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored:
            print(f"\n💡 未找到精确匹配，推荐以下相关内容：")
            for _, concept in scored[:3]:
                print(f"   - [{concept['type']}] {concept['title']}")
                print(f"     {concept['path']}")


def _calculate_score(concept: Dict, query_lower: str, keywords: List[str]) -> int:
    """计算概念与查询的相关性得分.

    Args:
        concept: 概念字典
        query_lower: 小写查询字符串
        keywords: 关键词列表

    Returns:
        相关性得分
    """
    score = 0
    # 标题匹配（最高权重）
    if query_lower in concept['title'].lower():
        score += 100
    for kw in keywords:
        if kw.lower() in concept['title'].lower():
            score += 50
    # 描述匹配
    if query_lower in concept['description'].lower():
        score += 50
    for kw in keywords:
        if kw.lower() in concept['description'].lower():
            score += 25
    # 标签匹配
    for tag in concept.get('tags', []):
        if query_lower in tag.lower():
            score += 30
        for kw in keywords:
            if kw.lower() in tag.lower():
                score += 15
    # 正文匹配
    body = concept.get('body', '').lower()
    if query_lower in body:
        score += 10
    for kw in keywords:
        if kw.lower() in body:
            score += 5
    # 类型匹配
    if query_lower == concept['type'].lower():
        score += 20
    return score


def _match_filters(concept: Dict, filters: Dict) -> bool:
    """检查概念是否匹配过滤条件.

    Args:
        concept: 概念字典
        filters: 过滤条件字典（tag, author, date_from, date_to, source_type, status）

    Returns:
        是否匹配所有过滤条件
    """
    if not filters:
        return True
    # 标签过滤
    tag_filter = filters.get('tag')
    if tag_filter:
        concept_tags = [t.lower() for t in concept.get('tags', [])]
        if tag_filter.lower() not in concept_tags:
            return False
    # 作者过滤
    author_filter = filters.get('author')
    if author_filter:
        if concept.get('author', '').lower() != author_filter.lower():
            return False
    # 来源类型过滤
    source_type_filter = filters.get('source_type')
    if source_type_filter:
        if concept.get('source_type', '').lower() != source_type_filter.lower():
            return False
    # 状态过滤
    status_filter = filters.get('status')
    if status_filter:
        if concept.get('status', 'published').lower() != status_filter.lower():
            return False
    # 日期范围过滤
    date_from = filters.get('date_from')
    date_to = filters.get('date_to')
    if date_from or date_to:
        ts = concept.get('timestamp', '')
        if ts:
            try:
                ts_date = ts[:10] if len(ts) >= 10 else ts
                if date_from and ts_date < date_from:
                    return False
                if date_to and ts_date > date_to:
                    return False
            except (ValueError, TypeError):
                pass
        # 无 timestamp 的原子不被日期过滤器排除
    return True


def _sort_results(results: List[Dict], sort_by: str) -> List[Dict]:
    """按指定方式排序结果.

    Args:
        results: 结果列表
        sort_by: 排序方式（relevance|time|title|popularity）

    Returns:
        排序后的结果列表
    """
    if sort_by == 'time':
        return sorted(results, key=lambda x: x.get('timestamp', ''), reverse=True)
    elif sort_by == 'title':
        return sorted(results, key=lambda x: x.get('title', '').lower())
    elif sort_by == 'popularity':
        # 简单实现：按文件修改时间倒序（近似热度）
        return sorted(results, key=lambda x: x.get('file_mtime', 0), reverse=True)
    else:  # relevance
        return sorted(results, key=lambda x: x.get('score', 0), reverse=True)
