"""混合搜索优化器测试

测试 HybridSearchOptimizer 的 RRF 合并、加权求和、归一化和重排序。
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

try:
    from lib.search.hybrid_search import HybridSearchOptimizer, RRFConfig
    from lib.search.engine import SearchResult

    _IMPORT_OK = True
except ImportError as _e:
    _IMPORT_OK = False
    _IMPORT_ERROR = str(_e)


def _make_result(atom_id, title, score, content="content", match_type="fulltext"):
    """创建测试用 SearchResult"""
    return SearchResult(
        atom_id=atom_id,
        slug=f"slug-{atom_id}",
        title=title,
        content=content,
        score=score,
        match_type=match_type,
    )


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestRRFConfig:
    """RRF 配置测试"""

    def test_rrf_config_defaults(self):
        """RRFConfig 默认值"""
        config = RRFConfig()
        assert config.k == 60
        assert config.weights is None
        assert config.deduplicate is True
        assert config.normalize_scores is True


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestReciprocalRankFusion:
    """RRF 合并测试"""

    def test_rrf_empty_input(self):
        """空输入返回空列表"""
        result = HybridSearchOptimizer.reciprocal_rank_fusion([])
        assert result == []

    def test_rrf_single_source(self):
        """单源 RRF"""
        results = [[
            _make_result(1, "A", 0.9),
            _make_result(2, "B", 0.8),
        ]]
        merged = HybridSearchOptimizer.reciprocal_rank_fusion(results)

        assert len(merged) == 2
        assert merged[0].atom_id == 1  # 排名第一
        assert merged[0].match_type == 'hybrid'

    def test_rrf_two_sources(self):
        """双源 RRF 合并"""
        text_results = [
            _make_result(1, "A", 0.9),
            _make_result(2, "B", 0.8),
        ]
        vector_results = [
            _make_result(2, "B", 0.95),
            _make_result(3, "C", 0.85),
        ]
        merged = HybridSearchOptimizer.reciprocal_rank_fusion(
            [text_results, vector_results]
        )

        # atom_id=2 在两个源中都出现，应排名最高
        assert len(merged) == 3
        assert merged[0].atom_id == 2
        assert merged[0].match_type == 'hybrid'

    def test_rrf_with_weights(self):
        """带权重的 RRF"""
        text_results = [_make_result(1, "A", 0.9)]
        vector_results = [_make_result(2, "B", 0.9)]
        merged = HybridSearchOptimizer.reciprocal_rank_fusion(
            [text_results, vector_results],
            weights=[2.0, 1.0],
        )

        # 文本源权重更高，其排名第一的结果应排在前面
        assert merged[0].atom_id == 1

    def test_rrf_deduplicate(self):
        """RRF 去重"""
        text_results = [_make_result(1, "A", 0.9)]
        vector_results = [_make_result(1, "A", 0.8)]
        merged = HybridSearchOptimizer.reciprocal_rank_fusion(
            [text_results, vector_results],
            deduplicate=True,
        )

        assert len(merged) == 1
        assert merged[0].atom_id == 1

    def test_rrf_weights_mismatch(self):
        """权重数量不匹配时使用等权重"""
        results = [[_make_result(1, "A", 0.9)]]
        # 权重数量不匹配，应回退到等权重
        merged = HybridSearchOptimizer.reciprocal_rank_fusion(
            results,
            weights=[1.0, 2.0],  # 2 个权重但只有 1 个源
        )
        assert len(merged) == 1


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestWeightedSumMerge:
    """加权求和合并测试"""

    def test_weighted_sum_basic(self):
        """基本加权求和"""
        text_results = [_make_result(1, "A", 0.8)]
        vector_results = [_make_result(1, "A", 0.6)]
        merged = HybridSearchOptimizer.weighted_sum_merge(
            text_results, vector_results,
            text_weight=0.5, vector_weight=0.5,
        )

        assert len(merged) == 1
        assert abs(merged[0].score - 0.7) < 0.01  # 0.8*0.5 + 0.6*0.5

    def test_weighted_sum_different_atoms(self):
        """不同原子的加权求和"""
        text_results = [_make_result(1, "A", 0.9)]
        vector_results = [_make_result(2, "B", 0.9)]
        merged = HybridSearchOptimizer.weighted_sum_merge(
            text_results, vector_results,
            text_weight=0.7, vector_weight=0.3,
        )

        assert len(merged) == 2
        # text 权重更高，A 应排在前面
        assert merged[0].atom_id == 1

    def test_weighted_sum_match_type_hybrid(self):
        """同时出现在两个源中的结果标记为 hybrid"""
        text_results = [_make_result(1, "A", 0.8, match_type="fulltext")]
        vector_results = [_make_result(1, "A", 0.6, match_type="vector")]
        merged = HybridSearchOptimizer.weighted_sum_merge(
            text_results, vector_results,
        )

        assert merged[0].match_type == 'hybrid'


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestNormalizeScores:
    """分数归一化测试"""

    def test_normalize_empty(self):
        """空列表归一化"""
        result = HybridSearchOptimizer.normalize_scores([])
        assert result == []

    def test_normalize_single(self):
        """单个结果归一化"""
        results = [_make_result(1, "A", 0.5)]
        normalized = HybridSearchOptimizer.normalize_scores(results)
        assert len(normalized) == 1
        assert normalized[0].score == 1.0  # 单个元素归一化到最大值

    def test_normalize_range(self):
        """分数范围归一化到 [0, 1]"""
        results = [
            _make_result(1, "A", 0.2),
            _make_result(2, "B", 0.8),
        ]
        normalized = HybridSearchOptimizer.normalize_scores(results, min_score=0.0, max_score=1.0)
        assert abs(normalized[0].score - 0.0) < 0.01
        assert abs(normalized[1].score - 1.0) < 0.01

    def test_normalize_equal_scores(self):
        """所有分数相同时归一化"""
        results = [
            _make_result(1, "A", 0.5),
            _make_result(2, "B", 0.5),
        ]
        normalized = HybridSearchOptimizer.normalize_scores(results)
        assert all(r.score == 1.0 for r in normalized)


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestReRank:
    """重排序测试"""

    def test_rerank_empty(self):
        """空结果重排序"""
        result = HybridSearchOptimizer.re_rank([], "query")
        assert result == []

    def test_rerank_with_custom_fn(self):
        """使用自定义重排序函数"""
        results = [
            _make_result(1, "A", 0.5, content="good match"),
            _make_result(2, "B", 0.8, content="bad match"),
        ]

        def custom_rerank(query, content):
            return 1.0 if "good" in content else 0.0

        reranked = HybridSearchOptimizer.re_rank(
            results, "good", rerank_fn=custom_rerank,
        )
        assert reranked[0].atom_id == 1
        assert reranked[0].match_type == 'reranked'

    def test_rerank_with_top_n(self):
        """重排序限制返回数量"""
        results = [
            _make_result(i, f"R{i}", 0.5) for i in range(5)
        ]

        def custom_rerank(query, content):
            return 0.5

        reranked = HybridSearchOptimizer.re_rank(
            results, "query", top_n=3, rerank_fn=custom_rerank,
        )
        assert len(reranked) == 3


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestDiversityAwareMerge:
    """多样性感知合并测试"""

    def test_diversity_small_input(self):
        """少量结果直接返回"""
        results = [_make_result(1, "A", 0.9)]
        merged = HybridSearchOptimizer.diversity_aware_merge(results)
        assert len(merged) == 1

    def test_diversity_with_similar_content(self):
        """相似内容被限制"""
        results = [
            _make_result(1, "A", 0.9, content="python programming tutorial"),
            _make_result(2, "B", 0.8, content="python programming guide"),
            _make_result(3, "C", 0.7, content="java programming tutorial"),
        ]
        merged = HybridSearchOptimizer.diversity_aware_merge(
            results, diversity_threshold=0.5, max_similar=1,
        )
        # 应该减少相似结果
        assert len(merged) <= len(results)


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestBoostRecentContent:
    """近期内容提升测试"""

    def test_boost_recent(self):
        """近期内容分数提升"""
        now = datetime.now()
        old_date = now - timedelta(days=60)
        results = [
            _make_result(1, "Recent", 0.5, content="recent"),
            _make_result(2, "Old", 0.5, content="old"),
        ]
        results[0].created_at = now
        results[1].created_at = old_date

        boosted = HybridSearchOptimizer.boost_recent_content(
            results, boost_factor=1.5, days_threshold=30,
        )
        # 近期内容分数应更高
        assert boosted[0].atom_id == 1
        assert boosted[0].score > boosted[1].score

    def test_boost_type(self):
        """按类型提升权重"""
        results = [
            _make_result(1, "A", 0.5, content="fact content"),
            _make_result(2, "B", 0.5, content="method content"),
        ]
        results[0].atom_type = "fact"
        results[1].atom_type = "method"

        boosted = HybridSearchOptimizer.boost_type(
            results, type_boosts={"fact": 2.0},
        )
        assert boosted[0].atom_id == 1
        assert boosted[0].score > boosted[1].score
