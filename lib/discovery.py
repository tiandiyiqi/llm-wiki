"""Discovery Engine - Heads Up 主动推送与知识发现

实现智能发现层的核心功能：
- 知识缺口检测（孤立节点、过期知识）
- 潜在关联发现
- 主动推送相关内容
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser
from .semantic import SemanticSearchEngine


class DiscoveryEngine:
    """知识发现引擎 - 主动发现知识缺口和潜在关联"""

    def __init__(self, kb_dir: Path, semantic_engine: Optional[SemanticSearchEngine] = None):
        """初始化发现引擎

        Args:
            kb_dir: 知识库目录路径
            semantic_engine: 可选的语义搜索引擎（用于关联发现）
        """
        self.kb_dir = kb_dir
        self.semantic_engine = semantic_engine
        self.yaml_parser = SimpleYAMLParser()
        self.concepts: List[Dict] = []
        self.link_pattern = re.compile(r'\[\[([^\]]+)\]\]')

    def find_gaps(self) -> List[Dict]:
        """发现知识缺口

        检测以下类型的缺口：
        1. 孤立节点：没有任何 [[链接]] 指向或指出的原子
        2. 过期知识：90天以上未更新的原子
        3. 空内容原子：内容少于 100 字符的原子
        4. 缺失字段：缺少 title 或 description 的原子

        Returns:
            缺口列表，每个缺口包含类型、位置、描述
        """
        self._load_concepts()

        gaps = []
        linked_ids: Set[str] = set()  # 被链接的原子 ID
        all_ids: Set[str] = set()     # 所有原子 ID

        # 第一遍：收集所有 ID 和链接
        for concept in self.concepts:
            all_ids.add(concept['id'])

            # 收集指向其他原子的链接
            body = concept.get('body', '')
            links = self.link_pattern.findall(body)
            for link in links:
                # 简化链接 ID（去除路径前缀）
                link_id = link.split('/')[-1].replace('.md', '')
                linked_ids.add(link_id)

            # 也检查 relations 字段中的链接
            relations = concept.get('relations', [])
            if relations:
                for rel in relations:
                    for rel_type, target in rel.items():
                        if target and target.startswith('[['):
                            target_id = target[2:-2]  # 去除 [[ ]]
                            linked_ids.add(target_id)

        now = datetime.now()
        stale_threshold = now - timedelta(days=90)

        # 第二遍：检测缺口
        for concept in self.concepts:
            atom_id = concept['id']
            atom_path = concept['path']

            # 1. 检查孤立节点
            outgoing_links = self.link_pattern.findall(concept.get('body', ''))
            has_outgoing = len(outgoing_links) > 0 or len(concept.get('relations', [])) > 0
            is_linked = atom_id in linked_ids or atom_id.split('/')[-1] in linked_ids

            if not has_outgoing and not is_linked:
                gaps.append({
                    'type': 'isolated',
                    'severity': 'medium',
                    'atom_id': atom_id,
                    'path': atom_path,
                    'title': concept.get('title', atom_id),
                    'description': f"孤立节点：'{concept.get('title', atom_id)}' 没有与其他原子建立关联"
                })

            # 2. 检查过期知识
            updated = concept.get('updated') or concept.get('timestamp')
            if updated:
                try:
                    # 尝试解析 ISO 格式时间
                    if 'T' in updated:
                        update_time = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    else:
                        update_time = datetime.strptime(updated[:10], '%Y-%m-%d')

                    if update_time.replace(tzinfo=None) < stale_threshold:
                        days_stale = (now - update_time.replace(tzinfo=None)).days
                        gaps.append({
                            'type': 'stale',
                            'severity': 'low',
                            'atom_id': atom_id,
                            'path': atom_path,
                            'title': concept.get('title', atom_id),
                            'description': f"过期知识：'{concept.get('title', atom_id)}' 已 {days_stale} 天未更新",
                            'days_stale': days_stale,
                            'last_updated': updated
                        })
                except (ValueError, TypeError):
                    pass

            # 3. 检查空内容
            body = concept.get('body', '')
            if len(body.strip()) < 100:
                gaps.append({
                    'type': 'empty_content',
                    'severity': 'high',
                    'atom_id': atom_id,
                    'path': atom_path,
                    'title': concept.get('title', atom_id),
                    'description': f"空内容：'{concept.get('title', atom_id)}' 内容过少（{len(body.strip())} 字符）"
                })

            # 4. 检查缺失字段
            missing_fields = []
            if not concept.get('title'):
                missing_fields.append('title')
            if not concept.get('description'):
                missing_fields.append('description')

            if missing_fields:
                gaps.append({
                    'type': 'missing_fields',
                    'severity': 'medium',
                    'atom_id': atom_id,
                    'path': atom_path,
                    'title': concept.get('title', atom_id),
                    'description': f"缺失字段：'{atom_id}' 缺少 {', '.join(missing_fields)}",
                    'missing': missing_fields
                })

        # 按严重程度排序
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        gaps.sort(key=lambda x: severity_order.get(x['severity'], 1))

        return gaps

    def find_relations(self, atom_id: str) -> List[Dict]:
        """发现指定原子的潜在关联

        使用语义搜索找到与指定原子相似的其他原子

        Args:
            atom_id: 原子 ID（可以是路径或简化 ID）

        Returns:
            潜在关联列表，包含相似度、推荐关联类型、理由
        """
        self._load_concepts()

        # 找到目标原子
        target_concept = None
        for concept in self.concepts:
            if concept['id'] == atom_id or concept['id'].endswith(atom_id):
                target_concept = concept
                break

        if not target_concept:
            return []

        relations = []

        # 方法 1：使用语义搜索（如果可用）
        if self.semantic_engine:
            # 构建查询文本
            query_text = self._build_query_text(target_concept)

            # 语义搜索相似内容
            semantic_results = self.semantic_engine.search(
                query_str=query_text,
                limit=10
            )

            # 过滤掉自身
            for result in semantic_results:
                if result['id'] != target_concept['id'] and not result['id'].endswith(target_concept['id'].split('/')[-1]):
                    relations.append({
                        'atom_id': result['id'],
                        'path': result['path'],
                        'title': result['title'],
                        'similarity': result.get('similarity', 0),
                        'relation_type': self._suggest_relation_type(target_concept, result),
                        'reason': f"语义相似度: {result.get('similarity', 0):.2%}"
                    })

        # 方法 2：基于关键词匹配（备选）
        if not relations or not self.semantic_engine:
            relations = self._find_keyword_relations(target_concept)

        # 按相似度排序
        relations.sort(key=lambda x: x.get('similarity', 0), reverse=True)

        return relations[:10]  # 返回前 10 个

    def heads_up(self, context: str, top_k: int = 5) -> List[Dict]:
        """主动推送相关内容

        根据当前上下文，主动推荐相关知识原子

        Args:
            context: 当前上下文文本（用户正在处理的内容）
            top_k: 返回的结果数量

        Returns:
            推荐的知识原子列表，包含相关性分数和推荐理由
        """
        self._load_concepts()

        recommendations = []

        # 方法 1：使用语义搜索（如果可用）
        if self.semantic_engine:
            semantic_results = self.semantic_engine.search(
                query_str=context,
                limit=top_k * 2  # 获取更多，后面去重
            )

            for result in semantic_results:
                recommendations.append({
                    'atom_id': result['id'],
                    'path': result['path'],
                    'type': result['type'],
                    'title': result['title'],
                    'description': result['description'][:150] if result.get('description') else '',
                    'relevance': result.get('similarity', 0),
                    'reason': self._generate_reason(result, context),
                    'match_type': 'semantic'
                })

        # 方法 2：基于关键词匹配（补充）
        keyword_results = self._keyword_match(context)

        # 合并结果，去重
        existing_ids = {r['atom_id'] for r in recommendations}
        for result in keyword_results:
            if result['atom_id'] not in existing_ids:
                recommendations.append(result)
                existing_ids.add(result['atom_id'])

        # 按相关性排序
        recommendations.sort(key=lambda x: x.get('relevance', 0), reverse=True)

        return recommendations[:top_k]

    def _load_concepts(self) -> None:
        """加载知识库中的所有概念"""
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
                            'tags': fm.get('tags', []),
                            'updated': fm.get('updated') or fm.get('timestamp'),
                            'timestamp': fm.get('timestamp'),
                            'relations': fm.get('relations', []),
                            'body': body
                        })

    def _build_query_text(self, concept: Dict) -> str:
        """构建用于语义搜索的查询文本"""
        parts = []

        if concept.get('title'):
            parts.append(concept['title'])

        if concept.get('description'):
            parts.append(concept['description'])

        if concept.get('tags'):
            parts.append(' '.join(concept['tags']))

        # 添加部分正文（前 200 字符）
        body = concept.get('body', '')
        if body:
            clean_body = re.sub(r'[#*\[\]]', '', body[:200])
            parts.append(clean_body)

        return ' '.join(parts)

    def _suggest_relation_type(self, source: Dict, target: Dict) -> str:
        """建议关联类型"""
        source_type = source.get('type', '')
        target_type = target.get('type', '')

        # 基于类型推断关联
        if target_type == 'definition':
            return 'defines'
        elif target_type == 'method' and source_type == 'fact':
            return 'supported_by'
        elif target_type == 'fact' and source_type == 'opinion':
            return 'supports'
        elif target_type == 'question':
            return 'answers'
        else:
            return 'relates_to'

    def _find_keyword_relations(self, target_concept: Dict) -> List[Dict]:
        """基于关键词匹配找关联"""
        relations = []

        # 提取目标概念的关键词
        target_keywords = self._extract_keywords(target_concept)

        for concept in self.concepts:
            if concept['id'] == target_concept['id']:
                continue

            # 计算关键词重叠
            concept_keywords = self._extract_keywords(concept)
            overlap = target_keywords & concept_keywords

            if overlap:
                similarity = len(overlap) / max(len(target_keywords), len(concept_keywords), 1)
                relations.append({
                    'atom_id': concept['id'],
                    'path': concept['path'],
                    'title': concept['title'],
                    'similarity': similarity,
                    'relation_type': self._suggest_relation_type(target_concept, concept),
                    'reason': f"关键词重叠: {', '.join(list(overlap)[:5])}"
                })

        relations.sort(key=lambda x: x['similarity'], reverse=True)
        return relations[:10]

    def _keyword_match(self, context: str) -> List[Dict]:
        """基于关键词匹配"""
        results = []

        # 提取上下文关键词
        context_keywords = self._extract_text_keywords(context)

        for concept in self.concepts:
            # 计算关键词匹配
            concept_keywords = self._extract_keywords(concept)
            overlap = context_keywords & concept_keywords

            if overlap:
                relevance = len(overlap) / max(len(context_keywords), 1)
                results.append({
                    'atom_id': concept['id'],
                    'path': concept['path'],
                    'type': concept['type'],
                    'title': concept['title'],
                    'description': concept.get('description', '')[:150],
                    'relevance': min(relevance * 2, 1.0),  # 放大匹配度
                    'reason': f"关键词匹配: {', '.join(list(overlap)[:3])}",
                    'match_type': 'keyword'
                })

        results.sort(key=lambda x: x['relevance'], reverse=True)
        return results[:10]

    def _extract_keywords(self, concept: Dict) -> Set[str]:
        """从概念中提取关键词"""
        keywords = set()

        # 标题
        if concept.get('title'):
            keywords.update(self._extract_text_keywords(concept['title']))

        # 描述
        if concept.get('description'):
            keywords.update(self._extract_text_keywords(concept['description']))

        # 标签
        if concept.get('tags'):
            keywords.update(tag.lower() for tag in concept['tags'])

        return keywords

    def _extract_text_keywords(self, text: str) -> Set[str]:
        """从文本中提取关键词"""
        # 简单的关键词提取：分词、去停用词、转小写
        # 移除 Markdown 标记
        text = re.sub(r'[#*\[\]`]', ' ', text)

        # 分词
        words = re.findall(r'\b\w{2,}\b', text.lower())

        # 简单的停用词
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
            'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once', 'here',
            'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if',
            'or', 'because', 'until', 'while', 'this', 'that', 'these', 'those',
            'am', 'it', 'its', 'itself', 'they', 'them', 'their', 'what', 'which',
            'who', 'whom', 'this', 'that', 'these', 'those', 'are', 'was', 'were',
            'have', 'has', 'had', 'having', 'being', 'been', 'about', 'against',
            'along', 'among', 'around', 'behind', 'beside', 'besides', 'beyond',
            'down', 'during', 'except', 'inside', 'outside', 'over', 'since',
            'toward', 'towards', 'up', 'upon', 'within', 'without'
        }

        return set(word for word in words if word not in stopwords and len(word) > 2)

    def _generate_reason(self, result: Dict, context: str) -> str:
        """生成推荐理由"""
        reasons = []

        # 类型匹配
        if result.get('type'):
            reasons.append(f"类型: {result['type']}")

        # 相似度
        similarity = result.get('similarity', 0)
        if similarity > 0.8:
            reasons.append("高度相关")
        elif similarity > 0.6:
            reasons.append("中度相关")
        else:
            reasons.append("可能相关")

        # 标签匹配
        if result.get('description'):
            # 简单检查描述中的关键词
            desc_words = set(result['description'].lower().split())
            context_words = set(context.lower().split())
            overlap = desc_words & context_words
            if overlap and len(overlap) > 2:
                reasons.append(f"包含关键词: {', '.join(list(overlap)[:3])}")

        return ' | '.join(reasons)