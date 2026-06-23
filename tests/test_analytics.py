"""Tests for lib/analytics.py — AnalyticsEngine."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from lib.analytics import AnalyticsEngine
except ImportError as exc:
    pytest.skip(f"Cannot import AnalyticsEngine: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kb_dir(tmp_path, atoms=None, search_history=None, views=None):
    """Create a minimal KB directory with atom files and optional metadata.

    atoms: list of dicts with keys: filename, frontmatter (dict), body (str)
    search_history: list of search history dicts
    views: dict of path -> view count
    """
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    meta_dir = kb_dir / ".llm-wiki"
    meta_dir.mkdir()

    if atoms:
        for atom in atoms:
            fpath = kb_dir / atom["filename"]
            fm = atom.get("frontmatter", {})
            body = atom.get("body", "")
            fm_lines = []
            for k, v in fm.items():
                if isinstance(v, list):
                    fm_lines.append(f"{k}:")
                    for item in v:
                        fm_lines.append(f"  - {item}")
                else:
                    fm_lines.append(f"{k}: {v}")
            fm_str = "\n".join(fm_lines)
            content = f"---\n{fm_str}\n---\n{body}"
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")

    if search_history is not None:
        sh_path = meta_dir / "search-history.json"
        sh_path.write_text(json.dumps(search_history), encoding="utf-8")

    if views is not None:
        analytics_path = meta_dir / "analytics.json"
        analytics_path.write_text(json.dumps(views), encoding="utf-8")

    return kb_dir


# ---------------------------------------------------------------------------
# Test AnalyticsEngine initialization
# ---------------------------------------------------------------------------

class TestAnalyticsEngineInit:

    def test_init_creates_analytics_dir(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = AnalyticsEngine(kb_dir)
        assert engine.analytics_path.parent.exists()

    def test_init_sets_kb_dir(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = AnalyticsEngine(kb_dir)
        assert engine.kb_dir == kb_dir


# ---------------------------------------------------------------------------
# Test get_stats
# ---------------------------------------------------------------------------

class TestGetStats:

    def test_empty_kb_stats(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        engine = AnalyticsEngine(kb_dir)
        stats = engine.get_stats()
        assert stats["total_atoms"] == 0
        assert stats["by_type"] == {}
        assert stats["by_status"] == {}
        assert stats["total_tags"] == 0

    def test_stats_with_atoms(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, atoms=[
            {
                "filename": "fact1.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "Fact One",
                    "tags": ["python", "test"],
                    "author": "alice",
                    "status": "published",
                    "timestamp": "2026-01-15T10:00:00",
                },
                "body": "Content of fact one.",
            },
            {
                "filename": "method1.md",
                "frontmatter": {
                    "type": "method",
                    "title": "Method One",
                    "tags": ["docker"],
                    "author": "bob",
                    "status": "draft",
                    "timestamp": "2026-03-20T10:00:00",
                },
                "body": "Content of method one.",
            },
        ])
        engine = AnalyticsEngine(kb_dir)
        stats = engine.get_stats()
        assert stats["total_atoms"] == 2
        assert stats["by_type"]["fact"] == 1
        assert stats["by_type"]["method"] == 1
        assert stats["by_status"]["published"] == 1
        assert stats["by_status"]["draft"] == 1
        assert "python" in stats["by_tag"]
        assert stats["by_author"]["alice"] == 1

    def test_stats_monthly_trend(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, atoms=[
            {
                "filename": "a1.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "A1",
                    "timestamp": "2026-01-10T00:00:00",
                },
                "body": "Content.",
            },
            {
                "filename": "a2.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "A2",
                    "timestamp": "2026-01-20T00:00:00",
                },
                "body": "Content.",
            },
            {
                "filename": "a3.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "A3",
                    "timestamp": "2026-03-05T00:00:00",
                },
                "body": "Content.",
            },
        ])
        engine = AnalyticsEngine(kb_dir)
        stats = engine.get_stats()
        assert stats["by_month"]["2026-01"] == 2
        assert stats["by_month"]["2026-03"] == 1

    def test_stats_with_search_history(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, search_history=[
            {"query": "python", "result_count": 5},
            {"query": "python", "result_count": 3},
            {"query": "docker", "result_count": 0},
        ])
        engine = AnalyticsEngine(kb_dir)
        stats = engine.get_stats()
        assert len(stats["hot_queries"]) > 0
        assert stats["hot_queries"][0]["query"] == "python"
        assert stats["hot_queries"][0]["count"] == 2
        assert "docker" in stats["no_result_queries"]

    def test_stats_with_views(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, views={
            "facts/fact1": 10,
            "methods/method1": 5,
        })
        engine = AnalyticsEngine(kb_dir)
        stats = engine.get_stats()
        assert len(stats["popular_docs"]) == 2
        assert stats["popular_docs"][0]["path"] == "facts/fact1"
        assert stats["popular_docs"][0]["views"] == 10

    def test_stats_generated_at_present(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        engine = AnalyticsEngine(kb_dir)
        stats = engine.get_stats()
        assert "generated_at" in stats
        assert stats["generated_at"] != ""

    def test_stats_recent_activity(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, atoms=[
            {
                "filename": "recent.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "Recent",
                    "timestamp": "2026-06-20T10:00:00",
                },
                "body": "Recent content.",
            },
        ])
        engine = AnalyticsEngine(kb_dir)
        stats = engine.get_stats()
        assert len(stats["recent_activity"]) > 0

    def test_tags_as_string_converted_to_list(self, tmp_path):
        """Tags that are strings (not lists) should be handled gracefully."""
        kb_dir = _make_kb_dir(tmp_path, atoms=[
            {
                "filename": "singletag.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "Single Tag",
                    "tags": "python",
                },
                "body": "Content.",
            },
        ])
        engine = AnalyticsEngine(kb_dir)
        stats = engine.get_stats()
        assert "python" in stats["by_tag"]


# ---------------------------------------------------------------------------
# Test record_view
# ---------------------------------------------------------------------------

class TestRecordView:

    def test_record_first_view(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        engine = AnalyticsEngine(kb_dir)
        engine.record_view("facts/test")
        views = engine._load_views()
        assert views["facts/test"] == 1

    def test_record_multiple_views(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        engine = AnalyticsEngine(kb_dir)
        engine.record_view("facts/test")
        engine.record_view("facts/test")
        engine.record_view("facts/test")
        views = engine._load_views()
        assert views["facts/test"] == 3

    def test_record_view_different_paths(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        engine = AnalyticsEngine(kb_dir)
        engine.record_view("facts/a")
        engine.record_view("facts/b")
        views = engine._load_views()
        assert views["facts/a"] == 1
        assert views["facts/b"] == 1


# ---------------------------------------------------------------------------
# Test export_report
# ---------------------------------------------------------------------------

class TestExportReport:

    def test_export_creates_csv(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, atoms=[
            {
                "filename": "fact1.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "Fact One",
                    "tags": ["test"],
                    "status": "published",
                    "timestamp": "2026-01-01T00:00:00",
                },
                "body": "Content.",
            },
        ])
        engine = AnalyticsEngine(kb_dir)
        output_path = tmp_path / "reports" / "report.csv"
        engine.export_report(output_path)
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "LLM Wiki" in content
        assert "fact" in content

    def test_export_creates_parent_dir(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        engine = AnalyticsEngine(kb_dir)
        output_path = tmp_path / "deep" / "nested" / "report.csv"
        engine.export_report(output_path)
        assert output_path.exists()

    def test_export_empty_kb(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        engine = AnalyticsEngine(kb_dir)
        output_path = tmp_path / "report.csv"
        engine.export_report(output_path)
        content = output_path.read_text(encoding="utf-8")
        assert "原子总数" in content


# ---------------------------------------------------------------------------
# Test private methods
# ---------------------------------------------------------------------------

class TestPrivateMethods:

    def test_load_all_atoms_skips_non_frontmatter(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / ".llm-wiki").mkdir()
        # File without frontmatter
        (kb_dir / "no_fm.md").write_text("Just plain text", encoding="utf-8")
        engine = AnalyticsEngine(kb_dir)
        atoms = engine._load_all_atoms()
        assert len(atoms) == 0

    def test_load_all_atoms_skips_reserved_files(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / ".llm-wiki").mkdir()
        (kb_dir / "index.md").write_text("---\ntype: index\n---\nContent", encoding="utf-8")
        (kb_dir / "log.md").write_text("---\ntype: log\n---\nContent", encoding="utf-8")
        engine = AnalyticsEngine(kb_dir)
        atoms = engine._load_all_atoms()
        assert len(atoms) == 0

    def test_load_search_history_missing_file(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / ".llm-wiki").mkdir()
        engine = AnalyticsEngine(kb_dir)
        history = engine._load_search_history()
        assert history == []

    def test_load_search_history_invalid_json(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        meta_dir = kb_dir / ".llm-wiki"
        meta_dir.mkdir()
        (meta_dir / "search-history.json").write_text("not json", encoding="utf-8")
        engine = AnalyticsEngine(kb_dir)
        history = engine._load_search_history()
        assert history == []

    def test_load_views_missing_file(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / ".llm-wiki").mkdir()
        engine = AnalyticsEngine(kb_dir)
        views = engine._load_views()
        assert views == {}

    def test_save_and_load_views(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / ".llm-wiki").mkdir()
        engine = AnalyticsEngine(kb_dir)
        engine._save_views({"test": 5})
        views = engine._load_views()
        assert views == {"test": 5}

    def test_get_recent_activity_sorted(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / ".llm-wiki").mkdir()
        engine = AnalyticsEngine(kb_dir)
        atoms = [
            {"timestamp": "2026-01-01T00:00:00", "type": "fact", "title": "Old"},
            {"timestamp": "2026-06-01T00:00:00", "type": "method", "title": "New"},
        ]
        activity = engine._get_recent_activity(atoms)
        assert len(activity) == 2
        # Most recent first
        assert "New" in activity[0]
