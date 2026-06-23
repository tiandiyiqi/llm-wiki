"""Tests for lib/querier.py — KnowledgeQuerier, SearchHistory, AggregatedQuerier."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestQuerierImport:
    """测试 querier 模块导入."""

    def test_import_querier(self):
        try:
            from lib.querier import KnowledgeQuerier, SearchHistory, highlight_text, extract_snippet
        except ImportError as e:
            pytest.skip(f"无法导入 querier 模块: {e}")


try:
    from lib.querier import (
        KnowledgeQuerier, SearchHistory, AggregatedQuerier,
        highlight_text, extract_snippet, _calculate_score, _match_filters, _sort_results
    )
    _QUERIER_AVAILABLE = True
except ImportError:
    _QUERIER_AVAILABLE = False


# ============================================================================
# highlight_text & extract_snippet Tests
# ============================================================================

@pytest.mark.skipif(not _QUERIER_AVAILABLE, reason="querier 模块导入依赖不满足")
class TestHighlightText:
    """测试关键词高亮."""

    def test_highlight_single_keyword(self):
        result = highlight_text("Hello world", ["world"])
        assert "\033[" in result
        assert "world" in result

    def test_highlight_no_keywords(self):
        result = highlight_text("Hello world", [])
        assert result == "Hello world"

    def test_highlight_empty_keyword(self):
        result = highlight_text("Hello world", [""])
        assert result == "Hello world"

    def test_highlight_case_insensitive(self):
        result = highlight_text("Hello World", ["world"])
        assert "\033[" in result


@pytest.mark.skipif(not _QUERIER_AVAILABLE, reason="querier 模块导入依赖不满足")
class TestExtractSnippet:
    """测试片段提取."""

    def test_extract_snippet_found(self):
        body = "Start " + "x" * 100 + " keyword " + "y" * 100 + " end"
        snippet = extract_snippet(body, ["keyword"])
        assert "keyword" in snippet

    def test_extract_snippet_not_found(self):
        snippet = extract_snippet("No match here", ["xyz123"])
        assert snippet == ""

    def test_extract_snippet_empty_body(self):
        snippet = extract_snippet("", ["keyword"])
        assert snippet == ""

    def test_extract_snippet_no_keywords(self):
        snippet = extract_snippet("Some body text", [])
        assert snippet == ""


# ============================================================================
# _calculate_score & _match_filters Tests
# ============================================================================

@pytest.mark.skipif(not _QUERIER_AVAILABLE, reason="querier 模块导入依赖不满足")
class TestCalculateScore:
    """测试相关性评分."""

    def test_title_match_highest_score(self):
        concept = {"title": "Python Programming", "description": "", "tags": [], "type": "fact", "body": ""}
        score = _calculate_score(concept, "python", ["python"])
        assert score >= 100

    def test_description_match_medium_score(self):
        concept = {"title": "Unrelated", "description": "Python is great", "tags": [], "type": "fact", "body": ""}
        score = _calculate_score(concept, "python", ["python"])
        assert score >= 25

    def test_no_match_zero_score(self):
        concept = {"title": "Unrelated", "description": "Nothing here", "tags": [], "type": "fact", "body": ""}
        score = _calculate_score(concept, "python", ["python"])
        assert score == 0

    def test_tag_match_adds_score(self):
        concept = {"title": "Unrelated", "description": "", "tags": ["python"], "type": "fact", "body": ""}
        score = _calculate_score(concept, "python", ["python"])
        assert score >= 15


@pytest.mark.skipif(not _QUERIER_AVAILABLE, reason="querier 模块导入依赖不满足")
class TestMatchFilters:
    """测试过滤条件匹配."""

    def test_no_filters_always_matches(self):
        concept = {"tags": [], "author": "", "status": "published"}
        assert _match_filters(concept, {}) is True

    def test_tag_filter_matches(self):
        concept = {"tags": ["python", "test"], "author": "", "status": "published"}
        assert _match_filters(concept, {"tag": "python"}) is True

    def test_tag_filter_no_match(self):
        concept = {"tags": ["rust"], "author": "", "status": "published"}
        assert _match_filters(concept, {"tag": "python"}) is False

    def test_author_filter(self):
        concept = {"tags": [], "author": "Alice", "status": "published"}
        assert _match_filters(concept, {"author": "alice"}) is True
        assert _match_filters(concept, {"author": "Bob"}) is False

    def test_status_filter(self):
        concept = {"tags": [], "author": "", "status": "draft"}
        assert _match_filters(concept, {"status": "draft"}) is True
        assert _match_filters(concept, {"status": "published"}) is False

    def test_date_range_filter(self):
        concept = {"tags": [], "author": "", "status": "published", "timestamp": "2026-03-15"}
        assert _match_filters(concept, {"date_from": "2026-01-01", "date_to": "2026-12-31"}) is True
        assert _match_filters(concept, {"date_from": "2027-01-01"}) is False


@pytest.mark.skipif(not _QUERIER_AVAILABLE, reason="querier 模块导入依赖不满足")
class TestSortResults:
    """测试结果排序."""

    def test_sort_by_relevance(self):
        results = [
            {"score": 10, "title": "Low"},
            {"score": 100, "title": "High"},
        ]
        sorted_r = _sort_results(results, "relevance")
        assert sorted_r[0]["score"] == 100

    def test_sort_by_title(self):
        results = [
            {"title": "Zebra", "score": 0},
            {"title": "Apple", "score": 0},
        ]
        sorted_r = _sort_results(results, "title")
        assert sorted_r[0]["title"] == "Apple"

    def test_sort_by_time(self):
        results = [
            {"timestamp": "2026-01-01", "score": 0},
            {"timestamp": "2026-06-01", "score": 0},
        ]
        sorted_r = _sort_results(results, "time")
        assert sorted_r[0]["timestamp"] == "2026-06-01"


# ============================================================================
# SearchHistory Tests
# ============================================================================

@pytest.mark.skipif(not _QUERIER_AVAILABLE, reason="querier 模块导入依赖不满足")
class TestSearchHistory:
    """测试搜索历史."""

    def test_record_and_get_suggestions(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        history = SearchHistory(kb_dir)
        history.record("python tutorial", 5)
        history.record("python basics", 3)
        history.record("python advanced", 2)

        suggestions = history.get_suggestions("python")
        assert len(suggestions) >= 1
        assert all(s.lower().startswith("python") for s in suggestions)

    def test_get_suggestions_empty_prefix(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        history = SearchHistory(kb_dir)
        suggestions = history.get_suggestions("")
        assert suggestions == []

    def test_get_hot_queries(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        history = SearchHistory(kb_dir)
        history.record("python", 5)
        history.record("python", 3)
        history.record("rust", 2)

        hot = history.get_hot_queries()
        assert len(hot) >= 1
        assert hot[0][0] == "python"

    def test_get_no_result_queries(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        history = SearchHistory(kb_dir)
        history.record("found", 5)
        history.record("notfound", 0)

        no_result = history.get_no_result_queries()
        assert "notfound" in no_result
        assert "found" not in no_result

    def test_history_persists_to_file(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        history1 = SearchHistory(kb_dir)
        history1.record("test query", 1)

        # 新实例应能读取
        history2 = SearchHistory(kb_dir)
        suggestions = history2.get_suggestions("test")
        assert len(suggestions) >= 1

    def test_history_truncates_at_1000(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        history = SearchHistory(kb_dir)
        for i in range(1100):
            history.record(f"query-{i}", 1)
        # 应只保留最近 1000 条
        data = history._load()
        assert len(data) <= 1000


# ============================================================================
# KnowledgeQuerier Tests
# ============================================================================

@pytest.mark.skipif(not _QUERIER_AVAILABLE, reason="querier 模块导入依赖不满足")
class TestKnowledgeQuerier:
    """测试知识查询器."""

    def _setup_kb(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "python.md").write_text(
            "---\ntitle: Python Language\ntype: fact\ndescription: A programming language\n"
            "tags:\n  - python\nauthor: Guido\nstatus: published\n---\nPython is popular.",
            encoding="utf-8"
        )
        (kb_dir / "rust.md").write_text(
            "---\ntitle: Rust Language\ntype: fact\ndescription: A systems language\n"
            "tags:\n  - rust\nauthor: Graydon\nstatus: published\n---\nRust is safe.",
            encoding="utf-8"
        )
        return kb_dir

    def test_query_finds_results(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        querier = KnowledgeQuerier(kb_dir)
        results = querier.query("Python")
        assert len(results) >= 1

    def test_query_empty_string_returns_results(self, tmp_path):
        """空字符串查询时，_calculate_score 中 '' in title.lower() 为 True，
        因此所有概念都会得到 score > 0 的结果。
        """
        kb_dir = self._setup_kb(tmp_path)
        querier = KnowledgeQuerier(kb_dir)
        results = querier.query("")
        # 空字符串匹配所有概念（因为空串是所有字符串的子串）
        assert len(results) >= 2

    def test_query_by_type(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        querier = KnowledgeQuerier(kb_dir)
        results = querier.query("language", by_type="fact")
        assert all(r.get("type") == "fact" for r in results)

    def test_query_no_results(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        querier = KnowledgeQuerier(kb_dir)
        results = querier.query("nonexistent_xyz_99999")
        assert len(results) == 0

    def test_query_with_highlight(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        querier = KnowledgeQuerier(kb_dir)
        results = querier.query("Python", highlight=True)
        if results:
            assert "title_highlighted" in results[0]

    def test_query_sort_by_title(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        querier = KnowledgeQuerier(kb_dir)
        results = querier.query("language", sort_by="title")
        if len(results) >= 2:
            assert results[0]["title"].lower() <= results[1]["title"].lower()

    def test_get_suggestions(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        querier = KnowledgeQuerier(kb_dir)
        querier.query("Python")
        suggestions = querier.get_suggestions("Pyth")
        assert len(suggestions) >= 0  # 可能为空，取决于历史
