"""数据验证器

验证迁移前后的数据一致性。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..yaml_parser import SimpleYAMLParser
from ..constants import RESERVED_FILES


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "✅ 通过" if self.valid else "❌ 失败"
        lines = [f"验证结果: {status}"]
        if self.details:
            for key, value in self.details.items():
                lines.append(f"  {key}: {value}")
        if self.errors:
            lines.append(f"  错误 ({len(self.errors)}):")
            for e in self.errors[:5]:
                lines.append(f"    - {e}")
        if self.warnings:
            lines.append(f"  警告 ({len(self.warnings)}):")
            for w in self.warnings[:5]:
                lines.append(f"    - {w}")
        return '\n'.join(lines)


class MigrationValidator:
    """迁移验证器

    验证迁移前后的数据一致性：
    - 记录数量
    - 内容完整性
    - 链接关系
    - 搜索功能
    """

    def __init__(self, db_manager, kb_path: Path):
        """初始化验证器

        Args:
            db_manager: 数据库管理器
            kb_path: 知识库路径
        """
        self.db = db_manager
        self.kb_path = kb_path
        self.yaml_parser = SimpleYAMLParser()

    def validate_counts(self, source: Dict[str, Any], target: Dict[str, Any]) -> ValidationResult:
        """验证记录数一致

        Args:
            source: 源数据统计（如 {'atoms': 100, 'links': 50}）
            target: 目标数据统计

        Returns:
            验证结果
        """
        result = ValidationResult(valid=True)
        mismatches = []

        for key in set(source.keys()) | set(target.keys()):
            source_count = source.get(key, 0)
            target_count = target.get(key, 0)

            if source_count != target_count:
                mismatches.append(f"{key}: 源 {source_count} -> 目标 {target_count}")
                result.valid = False

        result.details['source'] = source
        result.details['target'] = target

        if mismatches:
            result.errors.append("记录数不一致:")
            result.errors.extend(mismatches)

        return result

    async def validate_content(self, source_atoms: List[Dict], target_atoms: List[Dict]) -> ValidationResult:
        """验证内容一致性

        Args:
            source_atoms: 源原子列表
            target_atoms: 目标原子列表

        Returns:
            验证结果
        """
        result = ValidationResult(valid=True)

        # 构建路径映射
        source_map = {atom['path']: atom for atom in source_atoms}
        target_map = {atom['path']: atom for atom in target_atoms}

        # 检查路径一致性
        source_paths = set(source_map.keys())
        target_paths = set(target_map.keys())

        missing_in_target = source_paths - target_paths
        extra_in_target = target_paths - source_paths

        if missing_in_target:
            result.warnings.append(f"目标缺少 {len(missing_in_target)} 个原子")
            result.details['missing'] = list(missing_in_target)[:10]

        if extra_in_target:
            result.warnings.append(f"目标多出 {len(extra_in_target)} 个原子")
            result.details['extra'] = list(extra_in_target)[:10]

        # 检查内容一致性（抽样）
        sample_size = min(10, len(source_atoms))
        content_errors = []

        import random
        samples = random.sample(list(source_paths), sample_size) if len(source_paths) > sample_size else list(source_paths)

        for path in samples:
            if path not in target_map:
                continue

            source_atom = source_map[path]
            target_atom = target_map[path]

            # 检查标题
            if source_atom.get('title') != target_atom.get('title'):
                content_errors.append(f"{path}: 标题不匹配")
                result.valid = False

            # 检查类型
            if source_atom.get('type') != target_atom.get('type'):
                content_errors.append(f"{path}: 类型不匹配")
                result.warnings.append(f"{path}: 类型差异 (源: {source_atom.get('type')}, 目标: {target_atom.get('type')})")

        if content_errors:
            result.errors.extend(content_errors)

        result.details['checked'] = len(samples)
        result.details['total'] = len(source_atoms)

        return result

    async def validate_links(self, source_links: List[Dict], target_links: List[Dict]) -> ValidationResult:
        """验证链接关系完整性

        Args:
            source_links: 源链接列表
            target_links: 目标链接列表

        Returns:
            验证结果
        """
        result = ValidationResult(valid=True)

        # 构建链接集合（source_id, target_id）
        def link_key(link: Dict) -> Tuple:
            return (link.get('source_id'), link.get('target_id'), link.get('link_type', 'reference'))

        source_set = {link_key(link) for link in source_links if link.get('source_id') and link.get('target_id')}
        target_set = {link_key(link) for link in target_links if link.get('source_id') and link.get('target_id')}

        missing = source_set - target_set
        extra = target_set - source_set

        if missing:
            result.warnings.append(f"目标缺少 {len(missing)} 个链接")

        if extra:
            result.warnings.append(f"目标多出 {len(extra)} 个链接")

        result.details['source_links'] = len(source_links)
        result.details['target_links'] = len(target_links)
        result.details['match_rate'] = len(source_set & target_set) / max(len(source_set), 1) * 100

        return result

    async def validate_search(self, kb_id: int, test_queries: List[str]) -> ValidationResult:
        """验证搜索功能

        Args:
            kb_id: 知识库 ID
            test_queries: 测试查询列表

        Returns:
            验证结果
        """
        result = ValidationResult(valid=True)
        search_results = []

        for query in test_queries:
            try:
                results = await self.db.search_atoms(query, kb_id=kb_id, limit=5)
                search_results.append({
                    'query': query,
                    'count': len(results),
                    'top_title': results[0]['title'] if results else None,
                })
            except Exception as e:
                result.errors.append(f"搜索失败 '{query}': {e}")
                result.valid = False

        result.details['queries'] = len(test_queries)
        result.details['results'] = search_results

        # 检查是否有查询无结果
        no_results = [r for r in search_results if r['count'] == 0]
        if no_results:
            result.warnings.append(f"{len(no_results)} 个查询无结果")

        return result

    async def validate_all(self, kb_id: int) -> ValidationResult:
        """执行完整验证

        Args:
            kb_id: 知识库 ID

        Returns:
            验证结果
        """
        results = []

        # 1. 统计验证
        source_stats = await self._get_source_stats()
        target_stats = await self._get_target_stats(kb_id)
        count_result = self.validate_counts(source_stats, target_stats)
        results.append(count_result)

        # 2. 内容验证
        source_atoms = await self._get_source_atoms()
        target_atoms = await self.db.list_atoms(kb_id, limit=10000)
        content_result = await self.validate_content(source_atoms, target_atoms)
        results.append(content_result)

        # 3. 搜索验证
        test_queries = ['安装', '配置', 'method', 'how to', 'setup']
        search_result = await self.validate_search(kb_id, test_queries)
        results.append(search_result)

        # 汇总结果
        final_result = ValidationResult(
            valid=all(r.valid for r in results),
            errors=[e for r in results for e in r.errors],
            warnings=[w for r in results for w in r.warnings],
            details={'individual_results': [r.details for r in results]},
        )

        print(final_result)
        return final_result

    async def _get_source_stats(self) -> Dict[str, int]:
        """获取源数据统计"""
        atoms_dir = self.kb_path / 'atoms'
        atoms_count = 0
        types_count = {}

        if atoms_dir.exists():
            for md_file in atoms_dir.rglob('*.md'):
                if md_file.name in RESERVED_FILES:
                    continue
                atoms_count += 1

                # 解析类型
                try:
                    content = md_file.read_text(encoding='utf-8')
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            fm = self.yaml_parser.parse(parts[1]) or {}
                            atom_type = fm.get('type', 'unknown')
                            types_count[atom_type] = types_count.get(atom_type, 0) + 1
                except Exception:
                    pass

        # 统计链接数（从所有原子中提取 wikilinks）
        import re
        wikilink_pattern = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')
        links_count = 0

        if atoms_dir.exists():
            for md_file in atoms_dir.rglob('*.md'):
                if md_file.name in RESERVED_FILES:
                    continue
                try:
                    content = md_file.read_text(encoding='utf-8')
                    links_count += len(wikilink_pattern.findall(content))
                except Exception:
                    pass

        return {
            'atoms': atoms_count,
            'links': links_count,
            'types': types_count,
        }

    async def _get_target_stats(self, kb_id: int) -> Dict[str, int]:
        """获取目标数据统计"""
        atoms_count = await self.db.get_atom_count(kb_id)
        stats = await self.db.get_kb_stats(kb_id)

        # 统计链接数
        async with self.db.pool.acquire() as conn:
            links_row = await conn.fetchrow(
                'SELECT COUNT(*) as count FROM atom_links WHERE source_atom_id IN (SELECT id FROM atoms WHERE kb_id = $1)',
                kb_id
            )
            links_count = links_row['count'] if links_row else 0

        return {
            'atoms': atoms_count,
            'links': links_count,
            'types': stats.get('types_count', {}),
        }

    async def _get_source_atoms(self) -> List[Dict]:
        """获取源原子列表"""
        atoms = []
        atoms_dir = self.kb_path / 'atoms'

        if not atoms_dir.exists():
            return atoms

        for md_file in atoms_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue

            relative_path = str(md_file.relative_to(self.kb_path))
            content = md_file.read_text(encoding='utf-8')

            frontmatter = {}
            body = content

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = self.yaml_parser.parse(parts[1]) or {}
                    body = parts[2].strip()

            atoms.append({
                'path': relative_path,
                'title': frontmatter.get('title', md_file.stem),
                'type': frontmatter.get('type', 'method'),
                'tags': frontmatter.get('tags', []),
                'body': body,
            })

        return atoms

    def compare_embeddings(self, source_embeddings: List[Dict], target_embeddings: List[Dict]) -> ValidationResult:
        """比较向量嵌入

        Args:
            source_embeddings: 源嵌入列表（ChromaDB）
            target_embeddings: 目标嵌入列表（pgvector）

        Returns:
            验证结果
        """
        result = ValidationResult(valid=True)

        # 检查数量
        if len(source_embeddings) != len(target_embeddings):
            result.warnings.append(f"嵌入数量不一致: 源 {len(source_embeddings)}, 目标 {len(target_embeddings)}")

        # 抽样比较向量相似度
        import random
        sample_size = min(10, len(source_embeddings))

        if source_embeddings and target_embeddings:
            # 构建映射（假设两者顺序一致或有唯一 ID）
            source_map = {e.get('id'): e for e in source_embeddings if e.get('id')}
            target_map = {e.get('id'): e for e in target_embeddings if e.get('id')}

            common_ids = set(source_map.keys()) & set(target_map.keys())

            if common_ids:
                sample_ids = random.sample(list(common_ids), min(sample_size, len(common_ids)))

                for vec_id in sample_ids:
                    source_vec = source_map.get(vec_id, {}).get('embedding', [])
                    target_vec = target_map.get(vec_id, {}).get('embedding', [])

                    if source_vec and target_vec:
                        # 计算余弦相似度
                        try:
                            similarity = self._cosine_similarity(source_vec, target_vec)
                            if similarity < 0.99:  # 允许小误差
                                result.warnings.append(f"{vec_id}: 向量相似度 {similarity:.4f} < 0.99")
                        except Exception as e:
                            result.warnings.append(f"{vec_id}: 向量比较失败: {e}")

        result.details['source_count'] = len(source_embeddings)
        result.details['target_count'] = len(target_embeddings)

        return result

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import math

        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
