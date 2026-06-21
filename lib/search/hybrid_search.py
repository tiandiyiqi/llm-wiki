"""混合检索优化器

实现 RRF (Reciprocal Rank Fusion) 等多源结果合并算法。
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .engine import SearchResult


logger = logging.getLogger(__name__)


@dataclass
class RRFConfig:
    """RRF 配置

    Attributes:
        k: RRF 常数（通常为 60）
        weights: 各结果源的权重
        deduplicate: 是否去重
        normalize_scores: 是否归一化分数
    """

    k: int = 60
    weights: Optional[List[float]] = None
    deduplicate: bool = True
    normalize_scores: bool = True


class HybridSearchOptimizer:
    """混合检索优化器

    提供多种算法合并不同搜索源的结果：
    - RRF (Reciprocal Rank Fusion): 按排名位置加权
    - Weighted Sum: 按分数加权求和
    - Cross-Encoder Rerank: 使用 Cross-Encoder 模型重排序

    使用示例:
        optimizer = HybridSearchOptimizer()

        # RRF 合并
        merged = optimizer.reciprocal_rank_fusion(
            [text_results, vector_results],
            k=60
        )

        # 加权求和合并
        merged = optimizer.weighted_sum_merge(
            text_results, vector_results,
            text_weight=0.5, vector_weight=0.5
        )
    """

    @staticmethod
    def reciprocal_rank_fusion(
        results_list: List[List[SearchResult]],
        weights: Optional[List[float]] = None,
        k: int = 60,
        deduplicate: bool = True,
    ) -> List[SearchResult]:
        """RRF 算法合并多个搜索结果

        RRF 公式: score(d) = sum(1 / (k + rank(d, source_i)))

        对于每个结果 d，其在各搜索源中的排名位置越靠前，
        对最终得分贡献越大。

        Args:
            results_list: 多个搜索结果列表
            weights: 各源的权重（可选）
            k: RRF 常数，默认 60
            deduplicate: 是否去重

        Returns:
            合并后的搜索结果列表
        """
        if not results_list:
            return []

        # 默认权重相等
        if weights is None:
            weights = [1.0] * len(results_list)

        if len(weights) != len(results_list):
            logger.warning("Weights length mismatch, using equal weights")
            weights = [1.0] * len(results_list)

        # 按原子 ID 聚合分数
        scores_by_atom: Dict[int, float] = {}
        result_by_atom: Dict[int, SearchResult] = {}

        for source_idx, results in enumerate(results_list):
            weight = weights[source_idx]

            for rank_idx, result in enumerate(results):
                # 排名从 1 开始
                rank = rank_idx + 1

                # RRF 分数贡献
                rrf_score = weight / (k + rank)

                atom_id = result.atom_id

                if atom_id not in scores_by_atom:
                    scores_by_atom[atom_id] = 0.0
                    result_by_atom[atom_id] = result
                elif not deduplicate:
                    # 不去重时，创建副本
                    result_by_atom[atom_id + rank * 1000000] = result

                scores_by_atom[atom_id] += rrf_score

        # 按合并分数排序
        sorted_atoms = sorted(
            scores_by_atom.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # 构建最终结果
        merged_results = []
        for atom_id, score in sorted_atoms:
            result = result_by_atom[atom_id]
            # 创建新结果对象，更新分数和匹配类型
            merged_result = SearchResult(
                atom_id=result.atom_id,
                slug=result.slug,
                title=result.title,
                content=result.content,
                score=score,
                highlights=result.highlights,
                metadata=result.metadata,
                kb_id=result.kb_id,
                kb_name=result.kb_name,
                atom_type=result.atom_type,
                created_at=result.created_at,
                updated_at=result.updated_at,
                match_type='hybrid',
            )
            merged_results.append(merged_result)

        return merged_results

    @staticmethod
    def weighted_sum_merge(
        text_results: List[SearchResult],
        vector_results: List[SearchResult],
        text_weight: float = 0.5,
        vector_weight: float = 0.5,
        deduplicate: bool = True,
    ) -> List[SearchResult]:
        """加权求和合并

        直接对分数进行加权求和，适用于分数在相同范围的情况。

        Args:
            text_results: 全文搜索结果
            vector_results: 向量搜索结果
            text_weight: 全文权重
            vector_weight: 向量权重
            deduplicate: 是否去重

        Returns:
            合并后的结果
        """
        # 按原子 ID 聚合
        scores_by_atom: Dict[int, float] = {}
        result_by_atom: Dict[int, SearchResult] = {}

        # 处理全文结果
        for result in text_results:
            atom_id = result.atom_id
            weighted_score = result.score * text_weight

            if atom_id in scores_by_atom:
                scores_by_atom[atom_id] += weighted_score
            else:
                scores_by_atom[atom_id] = weighted_score
                result_by_atom[atom_id] = result

        # 处理向量结果
        for result in vector_results:
            atom_id = result.atom_id
            weighted_score = result.score * vector_weight

            if atom_id in scores_by_atom:
                scores_by_atom[atom_id] += weighted_score
                # 更新匹配类型为混合
                result_by_atom[atom_id].match_type = 'hybrid'
            else:
                scores_by_atom[atom_id] = weighted_score
                result_by_atom[atom_id] = result

        # 排序
        sorted_atoms = sorted(
            scores_by_atom.items(),
            key=lambda x: x[1],
            reverse=True
        )

        merged_results = []
        for atom_id, score in sorted_atoms:
            result = result_by_atom[atom_id]
            merged_result = SearchResult(
                atom_id=result.atom_id,
                slug=result.slug,
                title=result.title,
                content=result.content,
                score=score,
                highlights=result.highlights,
                metadata=result.metadata,
                kb_id=result.kb_id,
                kb_name=result.kb_name,
                atom_type=result.atom_type,
                created_at=result.created_at,
                updated_at=result.updated_at,
                match_type='hybrid',
            )
            merged_results.append(merged_result)

        return merged_results

    @staticmethod
    def normalize_scores(
        results: List[SearchResult],
        min_score: float = 0.0,
        max_score: float = 1.0,
    ) -> List[SearchResult]:
        """归一化分数到指定范围

        Args:
            results: 搜索结果列表
            min_score: 目标最小值
            max_score: 目标最大值

        Returns:
            分数归一化后的结果
        """
        if not results:
            return []

        # 找到原始分数范围
        scores = [r.score for r in results]
        original_min = min(scores)
        original_max = max(scores)

        # 避免除零
        if original_max == original_min:
            return [
                SearchResult(
                    atom_id=r.atom_id,
                    slug=r.slug,
                    title=r.title,
                    content=r.content,
                    score=max_score,
                    highlights=r.highlights,
                    metadata=r.metadata,
                    kb_id=r.kb_id,
                    kb_name=r.kb_name,
                    atom_type=r.atom_type,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                    match_type=r.match_type,
                )
                for r in results
            ]

        # 归一化
        scale = (max_score - min_score) / (original_max - original_min)

        normalized_results = []
        for result in results:
            normalized_score = min_score + (result.score - original_min) * scale
            normalized_result = SearchResult(
                atom_id=result.atom_id,
                slug=result.slug,
                title=result.title,
                content=result.content,
                score=normalized_score,
                highlights=result.highlights,
                metadata=result.metadata,
                kb_id=result.kb_id,
                kb_name=result.kb_name,
                atom_type=result.atom_type,
                created_at=result.created_at,
                updated_at=result.updated_at,
                match_type=result.match_type,
            )
            normalized_results.append(normalized_result)

        return normalized_results

    @staticmethod
    def re_rank(
        results: List[SearchResult],
        query: str,
        model: str = 'cross-encoder',
        top_n: Optional[int] = None,
        rerank_fn: Optional[Callable[[str, str], float]] = None,
    ) -> List[SearchResult]:
        """重排序（使用 Cross-Encoder 或自定义函数）

        Cross-Encoder 模型比双塔模型更准确，
        但计算成本更高，适合对少量候选结果进行重排序。

        Args:
            results: 原始搜索结果（通常是候选集）
            query: 查询字符串
            model: 重排序模型类型
            top_n: 仅返回前 N 个结果
            rerank_fn: 自定义重排序函数 (query, content) -> score

        Returns:
            重排序后的结果
        """
        if not results:
            return []

        # 如果提供了自定义重排序函数
        if rerank_fn:
            reranked = []
            for result in results:
                score = rerank_fn(query, result.content)
                reranked_result = SearchResult(
                    atom_id=result.atom_id,
                    slug=result.slug,
                    title=result.title,
                    content=result.content,
                    score=score,
                    highlights=result.highlights,
                    metadata=result.metadata,
                    kb_id=result.kb_id,
                    kb_name=result.kb_name,
                    atom_type=result.atom_type,
                    created_at=result.created_at,
                    updated_at=result.updated_at,
                    match_type='reranked',
                )
                reranked.append(reranked_result)

            reranked.sort(key=lambda x: x.score, reverse=True)
            if top_n:
                reranked = reranked[:top_n]
            return reranked

        # 尝试使用 Cross-Encoder 模型
        try:
            from sentence_transformers import CrossEncoder

            # 加载模型
            if model == 'cross-encoder':
                # 默认使用轻量级模型
                model_name = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
            else:
                model_name = model

            encoder = CrossEncoder(model_name)

            # 构建查询-文档对
            pairs = [(query, r.content) for r in results]

            # 计算分数
            scores = encoder.predict(pairs)

            # 更新分数并排序
            reranked = []
            for result, score in zip(results, scores):
                reranked_result = SearchResult(
                    atom_id=result.atom_id,
                    slug=result.slug,
                    title=result.title,
                    content=result.content,
                    score=float(score),
                    highlights=result.highlights,
                    metadata=result.metadata,
                    kb_id=result.kb_id,
                    kb_name=result.kb_name,
                    atom_type=result.atom_type,
                    created_at=result.created_at,
                    updated_at=result.updated_at,
                    match_type='reranked',
                )
                reranked.append(reranked_result)

            reranked.sort(key=lambda x: x.score, reverse=True)

            if top_n:
                reranked = reranked[:top_n]

            return reranked

        except ImportError:
            logger.warning(
                "CrossEncoder not available, "
                "install sentence-transformers for reranking"
            )
            # 返回原始结果
            return results[:top_n] if top_n else results

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return results[:top_n] if top_n else results

    @staticmethod
    def diversity_aware_merge(
        results: List[SearchResult],
        diversity_threshold: float = 0.8,
        max_similar: int = 3,
        similarity_fn: Optional[Callable[[str, str], float]] = None,
    ) -> List[SearchResult]:
        """多样性感知合并

        确保结果具有一定的多样性，避免过于相似的文档占据前列。

        Args:
            results: 搜索结果列表
            diversity_threshold: 相似度阈值（超过则视为相似）
            max_similar: 相似文档最大数量
            similarity_fn: 相似度计算函数 (content1, content2) -> similarity

        Returns:
            多样性优化后的结果
        """
        if len(results) <= max_similar:
            return results

        # 默认使用简单的词汇重叠相似度
        if similarity_fn is None:
            def simple_similarity(text1: str, text2: str) -> float:
                """简单的词汇重叠相似度"""
                words1 = set(text1.lower().split())
                words2 = set(text2.lower().split())
                if not words1 or not words2:
                    return 0.0
                intersection = len(words1 & words2)
                union = len(words1 | words2)
                return intersection / union if union > 0 else 0.0

            similarity_fn = simple_similarity

        diverse_results: List[SearchResult] = []
        similar_groups: List[List[SearchResult]] = []

        for result in results:
            # 检查与现有结果的相似度
            is_similar = False
            for group in similar_groups:
                if len(group) >= max_similar:
                    continue

                # 检查与组内第一个元素的相似度
                sim = similarity_fn(result.content, group[0].content)
                if sim >= diversity_threshold:
                    group.append(result)
                    is_similar = True
                    break

            if not is_similar:
                # 创建新组
                similar_groups.append([result])
                diverse_results.append(result)

        return diverse_results

    @staticmethod
    def boost_recent_content(
        results: List[SearchResult],
        boost_factor: float = 1.2,
        days_threshold: int = 30,
    ) -> List[SearchResult]:
        """提升近期内容的权重

        Args:
            results: 搜索结果列表
            boost_factor: 提升因子
            days_threshold: 天数阈值

        Returns:
            权重调整后的结果
        """
        from datetime import datetime, timedelta

        threshold_date = datetime.now() - timedelta(days=days_threshold)

        boosted = []
        for result in results:
            score = result.score

            # 检查创建时间
            if result.created_at and result.created_at >= threshold_date:
                score *= boost_factor

            boosted_result = SearchResult(
                atom_id=result.atom_id,
                slug=result.slug,
                title=result.title,
                content=result.content,
                score=score,
                highlights=result.highlights,
                metadata=result.metadata,
                kb_id=result.kb_id,
                kb_name=result.kb_name,
                atom_type=result.atom_type,
                created_at=result.created_at,
                updated_at=result.updated_at,
                match_type=result.match_type,
            )
            boosted.append(boosted_result)

        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted

    @staticmethod
    def boost_type(
        results: List[SearchResult],
        type_boosts: Dict[str, float],
    ) -> List[SearchResult]:
        """按原子类型提升权重

        Args:
            results: 搜索结果列表
            type_boosts: 类型到提升因子的映射

        Returns:
            权重调整后的结果
        """
        boosted = []
        for result in results:
            score = result.score

            # 应用类型提升
            if result.atom_type in type_boosts:
                score *= type_boosts[result.atom_type]

            boosted_result = SearchResult(
                atom_id=result.atom_id,
                slug=result.slug,
                title=result.title,
                content=result.content,
                score=score,
                highlights=result.highlights,
                metadata=result.metadata,
                kb_id=result.kb_id,
                kb_name=result.kb_name,
                atom_type=result.atom_type,
                created_at=result.created_at,
                updated_at=result.updated_at,
                match_type=result.match_type,
            )
            boosted.append(boosted_result)

        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted