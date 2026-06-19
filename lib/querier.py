"""Queries knowledge atoms (single and aggregated)."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser


class AggregatedQuerier:
    """聚合查询父知识库及其所有子知识库."""

    def __init__(self, kb_dir: Path, registry: 'KBRegistry'):
        self.kb_dir = kb_dir
        self.registry = registry
        self.children: List[Tuple[Path, str]] = []
        self.all_concepts: List[Dict] = []

    def discover_children(self) -> List[Tuple[Path, str]]:
        """发现并加载所有子知识库路径."""
        child_paths = []

        # 从 .kb-meta.json 获取子知识库信息
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

        # 也检查注册表中的子知识库
        kb_name = self.kb_dir.name
        kb_info = self.registry.get(kb_name)
        if kb_info and kb_info.get('children'):
            for child_name in kb_info.get('children', []):
                child_kb = self.registry.get(child_name)
                if child_kb and child_kb.get('path'):
                    child_full_path = Path(child_kb['path'])
                    if child_full_path.exists():
                        # 避免重复
                        if not any(p[1] == child_name for p in child_paths):
                            child_paths.append((child_full_path, child_name))

        self.children = child_paths
        return child_paths

    def aggregate_query(self, query_str: str, limit: int = 10, by_type: Optional[str] = None,
                        child_filter: Optional[str] = None) -> bool:
        """聚合搜索所有知识库."""
        print(f"🔍 Aggregated query: '{query_str}'")
        print(f"   Parent knowledge base: {self.kb_dir}")

        # 发现子知识库
        children = self.discover_children()
        if children:
            print(f"   Child knowledge bases: {len(children)}")
            for path, name in children:
                print(f"      - {name}")
        else:
            print(f"   (No child knowledge bases)")

        print()

        # 加载父知识库的概念
        parent_querier = KnowledgeQuerier(self.kb_dir)
        parent_querier._load_concepts()

        # 为父知识库概念添加来源标记
        for concept in parent_querier.concepts:
            concept['source'] = self.kb_dir.name
            concept['source_type'] = 'parent'

        self.all_concepts = parent_querier.concepts

        # 加载每个子知识库的概念
        for child_path, child_name in children:
            # 如果指定了 child_filter，只查询该子知识库
            if child_filter and child_name != child_filter:
                continue

            child_querier = KnowledgeQuerier(child_path)
            child_querier._load_concepts()

            for concept in child_querier.concepts:
                concept['source'] = child_name
                concept['source_type'] = 'child'
                # 调整路径以显示相对位置
                concept['display_path'] = f"{child_name}/{concept['path']}"
                self.all_concepts.append(concept)

        print(f"   Total concepts (aggregated): {len(self.all_concepts)}")

        if not self.all_concepts:
            print("   No concepts found")
            return False

        # 搜索
        results = self._search(query_str, by_type)

        # 去重（相同 atom_id）
        seen_ids = set()
        unique_results = []
        for result in results:
            result_id = result.get('id', result['path'])
            if result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)

        # 限制结果数量
        unique_results = unique_results[:limit]

        if not unique_results:
            print(f"\n   No results found for '{query_str}'")
            return True

        # 显示结果
        print(f"\n📋 Results ({len(unique_results)}):")
        for i, result in enumerate(unique_results, 1):
            source_marker = " [子知识库]" if result.get('source_type') == 'child' else " [父知识库]"
            print(f"\n{i}. [{result['type']}] {result['title']}")
            print(f"   Source: {result.get('source', 'unknown')}{source_marker}")
            display_path = result.get('display_path', result['path'])
            print(f"   Path: {display_path}")
            if result['description']:
                desc = result['description'][:80]
                print(f"   {desc}...")
            if result['tags']:
                print(f"   Tags: {', '.join(result['tags'])}")

        return True

    def _search(self, query_str: str, by_type: Optional[str] = None) -> List[Dict]:
        """Search all concepts by query string."""
        query_lower = query_str.lower()
        results = []

        for concept in self.all_concepts:
            # Filter by type if specified
            if by_type and concept['type'] != by_type:
                continue

            # Calculate relevance score
            score = 0

            # Title match (highest weight)
            if query_lower in concept['title'].lower():
                score += 10

            # Description match
            if query_lower in concept['description'].lower():
                score += 5

            # Tags match
            for tag in concept.get('tags', []):
                if query_lower in tag.lower():
                    score += 3

            # Body match
            if query_lower in concept.get('body', '').lower():
                score += 1

            if score > 0:
                concept['score'] = score
                results.append(concept)

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results


class KnowledgeQuerier:
    """Searches and queries knowledge atoms."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()
        self.concepts: List[Dict] = []

    def query(self, query_str: str, limit: int = 10, by_type: Optional[str] = None) -> bool:
        print(f"🔍 Querying: '{query_str}'")
        print(f"   Knowledge base: {self.kb_dir}")

        # Load all concepts
        self._load_concepts()

        if not self.concepts:
            print("   No concepts found in knowledge base")
            return False

        print(f"   Total concepts: {len(self.concepts)}")

        # Search
        results = self._search(query_str, by_type)

        # Limit results
        results = results[:limit]

        if not results:
            print(f"\n   No results found for '{query_str}'")
            return True

        # Display results
        print(f"\n📋 Results ({len(results)}):")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. [{result['type']}] {result['title']}")
            print(f"   Path: {result['path']}")
            print(f"   {result['description'][:80]}...")
            if result['tags']:
                print(f"   Tags: {', '.join(result['tags'])}")

        return True

    def _load_concepts(self) -> None:
        """Load all concepts from knowledge base."""
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
                            'tags': fm.get('tags', []),
                            'frontmatter': fm,
                            'body': body
                        })

    def _search(self, query_str: str, by_type: Optional[str] = None) -> List[Dict]:
        """Search concepts by query string."""
        query_lower = query_str.lower()
        results = []

        for concept in self.concepts:
            # Filter by type if specified
            if by_type and concept['type'] != by_type:
                continue

            # Calculate relevance score
            score = 0

            # Title match (highest priority)
            if query_lower in concept['title'].lower():
                score += 100

            # Description match
            if query_lower in concept['description'].lower():
                score += 50

            # Tags match
            for tag in concept['tags']:
                if query_lower in tag.lower():
                    score += 30

            # Body match
            if query_lower in concept['body'].lower():
                score += 10

            # Type match
            if query_lower == concept['type'].lower():
                score += 20

            if score > 0:
                results.append({
                    **concept,
                    'score': score,
                    'match_type': 'keyword'
                })

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        return results