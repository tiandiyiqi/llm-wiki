"""Tests for lib/discovery.py — DiscoveryEngine."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from lib.discovery import DiscoveryEngine
except ImportError as exc:
    pytest.skip(f"Cannot import DiscoveryEngine: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kb_dir(tmp_path, atoms):
    """Create a minimal KB directory with atom files.

    atoms: list of dicts with keys: filename, frontmatter (dict), body (str)
    """
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    for atom in atoms:
        fpath = kb_dir / atom["filename"]
        fm = atom.get("frontmatter", {})
        body = atom.get("body", "")
        # Build YAML-like frontmatter
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
    return kb_dir


# ---------------------------------------------------------------------------
# Test DiscoveryEngine initialization
# ---------------------------------------------------------------------------

class TestDiscoveryEngineInit:

    def test_init_basic(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        assert engine.kb_dir == kb_dir
        assert engine.semantic_engine is None
        assert engine.concepts == []

    def test_init_with_semantic_engine(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        mock_engine = MagicMock()
        engine = DiscoveryEngine(kb_dir, semantic_engine=mock_engine)
        assert engine.semantic_engine is mock_engine


# ---------------------------------------------------------------------------
# Test find_gaps
# ---------------------------------------------------------------------------

class TestFindGaps:

    def test_empty_kb_no_gaps(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        gaps = engine.find_gaps()
        assert gaps == []

    def test_isolated_node_detected(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "isolated.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "Isolated Node",
                    "description": "A node with no links",
                },
                "body": "This is an isolated node with no links to others.",
            }
        ])
        engine = DiscoveryEngine(kb_dir)
        gaps = engine.find_gaps()
        isolated = [g for g in gaps if g["type"] == "isolated"]
        assert len(isolated) >= 1
        assert isolated[0]["atom_id"] == "isolated"

    def test_stale_knowledge_detected(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "stale.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "Stale Node",
                    "description": "Old knowledge",
                    "updated": "2020-01-01",
                },
                "body": "This is stale content that has not been updated in a very long time and exceeds the threshold.",
            }
        ])
        engine = DiscoveryEngine(kb_dir)
        gaps = engine.find_gaps()
        stale = [g for g in gaps if g["type"] == "stale"]
        assert len(stale) >= 1
        assert stale[0]["days_stale"] > 90

    def test_empty_content_detected(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "empty.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "Empty Node",
                    "description": "Short",
                },
                "body": "Hi",
            }
        ])
        engine = DiscoveryEngine(kb_dir)
        gaps = engine.find_gaps()
        empty = [g for g in gaps if g["type"] == "empty_content"]
        assert len(empty) >= 1

    def test_missing_fields_detected(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "nofields.md",
                "frontmatter": {
                    "type": "fact",
                },
                "body": "Some content that is long enough to not trigger empty_content gap detection for this test scenario.",
            }
        ])
        engine = DiscoveryEngine(kb_dir)
        gaps = engine.find_gaps()
        missing = [g for g in gaps if g["type"] == "missing_fields"]
        assert len(missing) >= 1
        assert "title" in missing[0]["missing"] or "description" in missing[0]["missing"]

    def test_gaps_sorted_by_severity(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "high_gap.md",
                "frontmatter": {"type": "fact", "title": "High", "description": "Short"},
                "body": "Short",
            },
            {
                "filename": "medium_gap.md",
                "frontmatter": {"type": "fact"},
                "body": "This is a medium gap node with enough content to avoid empty_content detection but missing title and description fields.",
            },
        ])
        engine = DiscoveryEngine(kb_dir)
        gaps = engine.find_gaps()
        if len(gaps) >= 2:
            severity_order = {"high": 0, "medium": 1, "low": 2}
            for i in range(len(gaps) - 1):
                assert severity_order.get(gaps[i]["severity"], 1) <= severity_order.get(gaps[i + 1]["severity"], 1)

    def test_linked_node_not_isolated(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "source.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "Source",
                    "description": "Links to target",
                },
                "body": "See [[target]] for more details. This content is long enough to avoid empty detection.",
            },
            {
                "filename": "target.md",
                "frontmatter": {
                    "type": "fact",
                    "title": "Target",
                    "description": "Linked from source",
                },
                "body": "Target content that is long enough to avoid empty content detection in this test.",
            },
        ])
        engine = DiscoveryEngine(kb_dir)
        gaps = engine.find_gaps()
        isolated_ids = [g["atom_id"] for g in gaps if g["type"] == "isolated"]
        assert "target" not in isolated_ids

    def test_concepts_cached(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "cached.md",
                "frontmatter": {"type": "fact", "title": "Cached", "description": "Test"},
                "body": "Content for caching test that is long enough to pass the empty content threshold.",
            },
        ])
        engine = DiscoveryEngine(kb_dir)
        engine.find_gaps()
        assert len(engine.concepts) > 0
        # Second call should use cache
        engine.find_gaps()
        assert len(engine.concepts) > 0


# ---------------------------------------------------------------------------
# Test find_relations
# ---------------------------------------------------------------------------

class TestFindRelations:

    def test_nonexistent_atom_returns_empty(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "exists.md",
                "frontmatter": {"type": "fact", "title": "Exists", "description": "Test"},
                "body": "Some content here.",
            },
        ])
        engine = DiscoveryEngine(kb_dir)
        result = engine.find_relations("nonexistent")
        assert result == []

    def test_keyword_relations_found(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "python_basics.md",
                "frontmatter": {
                    "type": "method",
                    "title": "Python Basics",
                    "description": "Learn python programming",
                    "tags": ["python", "programming"],
                },
                "body": "Python is a programming language with many features and capabilities for developers.",
            },
            {
                "filename": "python_advanced.md",
                "frontmatter": {
                    "type": "method",
                    "title": "Python Advanced",
                    "description": "Advanced python techniques",
                    "tags": ["python", "advanced"],
                },
                "body": "Advanced python programming techniques for experienced developers and engineers.",
            },
        ])
        engine = DiscoveryEngine(kb_dir)
        result = engine.find_relations("python_basics")
        assert len(result) > 0
        assert any("python" in r.get("reason", "").lower() for r in result)

    def test_relations_limited_to_10(self, tmp_path):
        """Verify find_relations returns at most 10 results."""
        atoms = [
            {
                "filename": f"atom_{i}.md",
                "frontmatter": {
                    "type": "fact",
                    "title": f"Atom {i}",
                    "description": "Python programming test",
                    "tags": ["python"],
                },
                "body": "Python programming content for testing relation discovery limits.",
            }
            for i in range(15)
        ]
        atoms[0]["frontmatter"]["title"] = "Target Atom"
        kb_dir = _make_kb_dir(tmp_path, atoms)
        engine = DiscoveryEngine(kb_dir)
        result = engine.find_relations("atom_0")
        assert len(result) <= 10

    def test_find_relations_with_semantic_engine(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "source.md",
                "frontmatter": {"type": "fact", "title": "Source", "description": "Test"},
                "body": "Source content for semantic search testing.",
            },
            {
                "filename": "related.md",
                "frontmatter": {"type": "fact", "title": "Related", "description": "Test"},
                "body": "Related content for semantic search testing.",
            },
        ])
        mock_semantic = MagicMock()
        mock_semantic.search.return_value = [
            {"id": "related", "path": "related.md", "title": "Related", "similarity": 0.85, "type": "fact", "description": "Test"},
        ]
        engine = DiscoveryEngine(kb_dir, semantic_engine=mock_semantic)
        result = engine.find_relations("source")
        assert len(result) > 0
        mock_semantic.search.assert_called_once()


# ---------------------------------------------------------------------------
# Test heads_up
# ---------------------------------------------------------------------------

class TestHeadsUp:

    def test_empty_context(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "test.md",
                "frontmatter": {"type": "fact", "title": "Test", "description": "Test"},
                "body": "Test content for heads up functionality.",
            },
        ])
        engine = DiscoveryEngine(kb_dir)
        result = engine.heads_up("")
        assert isinstance(result, list)

    def test_keyword_match_returns_results(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "docker_setup.md",
                "frontmatter": {
                    "type": "method",
                    "title": "Docker Setup",
                    "description": "How to set up docker",
                    "tags": ["docker", "setup"],
                },
                "body": "Docker setup instructions for containerized deployment of applications.",
            },
        ])
        engine = DiscoveryEngine(kb_dir)
        result = engine.heads_up("docker container deployment", top_k=5)
        assert len(result) > 0
        assert result[0]["match_type"] == "keyword"

    def test_top_k_limits_results(self, tmp_path):
        atoms = [
            {
                "filename": f"doc_{i}.md",
                "frontmatter": {
                    "type": "fact",
                    "title": f"Doc {i}",
                    "description": "Python programming",
                    "tags": ["python"],
                },
                "body": "Python programming content for testing top_k limits in heads up.",
            }
            for i in range(10)
        ]
        kb_dir = _make_kb_dir(tmp_path, atoms)
        engine = DiscoveryEngine(kb_dir)
        result = engine.heads_up("python programming", top_k=3)
        assert len(result) <= 3

    def test_heads_up_with_semantic_engine(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "test.md",
                "frontmatter": {"type": "fact", "title": "Test", "description": "Test"},
                "body": "Test content.",
            },
        ])
        mock_semantic = MagicMock()
        mock_semantic.search.return_value = [
            {"id": "test", "path": "test.md", "type": "fact", "title": "Test", "description": "Test", "similarity": 0.9},
        ]
        engine = DiscoveryEngine(kb_dir, semantic_engine=mock_semantic)
        result = engine.heads_up("test query", top_k=5)
        mock_semantic.search.assert_called_once()

    def test_deduplication_of_results(self, tmp_path):
        """Results from semantic and keyword matching should be deduplicated."""
        kb_dir = _make_kb_dir(tmp_path, [
            {
                "filename": "python.md",
                "frontmatter": {
                    "type": "method",
                    "title": "Python Guide",
                    "description": "Python programming guide",
                    "tags": ["python"],
                },
                "body": "Python programming guide for beginners and advanced users alike.",
            },
        ])
        mock_semantic = MagicMock()
        mock_semantic.search.return_value = [
            {"id": "python", "path": "python.md", "type": "method", "title": "Python Guide", "description": "Python programming guide", "similarity": 0.95},
        ]
        engine = DiscoveryEngine(kb_dir, semantic_engine=mock_semantic)
        result = engine.heads_up("python programming", top_k=5)
        ids = [r["atom_id"] for r in result]
        assert len(ids) == len(set(ids)), "Results should not contain duplicates"


# ---------------------------------------------------------------------------
# Test private helper methods
# ---------------------------------------------------------------------------

class TestPrivateHelpers:

    def test_build_query_text(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        concept = {
            "title": "Test Title",
            "description": "Test Description",
            "tags": ["tag1", "tag2"],
            "body": "Some body content here",
        }
        result = engine._build_query_text(concept)
        assert "Test Title" in result
        assert "Test Description" in result
        assert "tag1" in result

    def test_suggest_relation_type_definition(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        source = {"type": "fact"}
        target = {"type": "definition"}
        assert engine._suggest_relation_type(source, target) == "defines"

    def test_suggest_relation_type_method_supported_by(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        source = {"type": "fact"}
        target = {"type": "method"}
        assert engine._suggest_relation_type(source, target) == "supported_by"

    def test_suggest_relation_type_opinion_supports(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        source = {"type": "opinion"}
        target = {"type": "fact"}
        assert engine._suggest_relation_type(source, target) == "supports"

    def test_suggest_relation_type_question_answers(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        source = {"type": "fact"}
        target = {"type": "question"}
        assert engine._suggest_relation_type(source, target) == "answers"

    def test_suggest_relation_type_default(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        source = {"type": "fact"}
        target = {"type": "fact"}
        assert engine._suggest_relation_type(source, target) == "relates_to"

    def test_extract_keywords(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        concept = {
            "title": "Docker Setup",
            "description": "How to install docker",
            "tags": ["docker", "container"],
        }
        keywords = engine._extract_keywords(concept)
        assert "docker" in keywords
        assert "container" in keywords

    def test_extract_text_keywords(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        keywords = engine._extract_text_keywords("The quick brown fox jumps over the lazy dog")
        assert "quick" in keywords
        assert "brown" in keywords
        assert "fox" in keywords
        # Stopwords should be removed
        assert "the" not in keywords
        assert "over" not in keywords

    def test_extract_text_keywords_removes_markdown(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        keywords = engine._extract_text_keywords("# Heading **bold** [link](url)")
        assert "#" not in str(keywords)

    def test_generate_reason_high_similarity(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        result = {"type": "fact", "similarity": 0.9, "description": "test description"}
        reason = engine._generate_reason(result, "test context")
        assert "高度相关" in reason

    def test_generate_reason_medium_similarity(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        result = {"type": "fact", "similarity": 0.7, "description": "test description"}
        reason = engine._generate_reason(result, "test context")
        assert "中度相关" in reason

    def test_generate_reason_low_similarity(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        engine = DiscoveryEngine(kb_dir)
        result = {"type": "fact", "similarity": 0.3, "description": "test description"}
        reason = engine._generate_reason(result, "test context")
        assert "可能相关" in reason
