"""Tests for lib/cache.py — ConceptCache, EmbedIncremental, PaginatedQuerier."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestCacheImport:
    """测试 cache 模块导入."""

    def test_import_cache(self):
        try:
            from lib.cache import ConceptCache, EmbedIncremental, PaginatedQuerier
        except ImportError as e:
            pytest.skip(f"无法导入 cache 模块: {e}")


try:
    from lib.cache import ConceptCache, EmbedIncremental, PaginatedQuerier
    _CACHE_AVAILABLE = True
except ImportError:
    _CACHE_AVAILABLE = False


# ============================================================================
# ConceptCache Tests
# ============================================================================

@pytest.mark.skipif(not _CACHE_AVAILABLE, reason="cache 模块导入依赖不满足")
class TestConceptCacheInit:
    """测试 ConceptCache 初始化."""

    def test_init_creates_cache_dir(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        cache = ConceptCache(kb_dir)
        assert (kb_dir / ".llm-wiki").exists()

    def test_init_cache_path(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        cache = ConceptCache(kb_dir)
        assert cache.cache_path.name == "concept-cache.json"


@pytest.mark.skipif(not _CACHE_AVAILABLE, reason="cache 模块导入依赖不满足")
class TestConceptCacheGetConcepts:
    """测试概念获取（带缓存）."""

    def _create_atom(self, kb_dir, name, title="Test"):
        atom_file = kb_dir / f"{name}.md"
        atom_file.write_text(
            f"---\ntitle: {title}\ntype: fact\ndescription: A test\n---\nBody",
            encoding="utf-8"
        )
        return atom_file

    def test_get_concepts_empty_kb(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        cache = ConceptCache(kb_dir)
        concepts = cache.get_concepts()
        assert concepts == []

    def test_get_concepts_with_atoms(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        self._create_atom(kb_dir, "atom1", "First")
        self._create_atom(kb_dir, "atom2", "Second")

        cache = ConceptCache(kb_dir)
        concepts = cache.get_concepts()
        assert len(concepts) == 2

    def test_get_concepts_caches_result(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        self._create_atom(kb_dir, "atom1", "Test")

        cache = ConceptCache(kb_dir)
        concepts1 = cache.get_concepts()
        concepts2 = cache.get_concepts()
        assert len(concepts1) == len(concepts2)

    def test_get_concepts_force_reload(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        self._create_atom(kb_dir, "atom1", "Test")

        cache = ConceptCache(kb_dir)
        cache.get_concepts()

        # 添加新文件
        self._create_atom(kb_dir, "atom2", "New")

        concepts = cache.get_concepts(force_reload=True)
        assert len(concepts) == 2

    def test_get_concepts_detects_new_file(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        self._create_atom(kb_dir, "atom1", "First")

        cache = ConceptCache(kb_dir)
        cache.get_concepts()

        # 添加新文件
        self._create_atom(kb_dir, "atom2", "Second")

        # 增量更新应检测到新文件
        concepts = cache.get_concepts()
        assert len(concepts) == 2

    def test_get_concepts_skips_no_frontmatter(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "plain.md").write_text("No frontmatter here", encoding="utf-8")

        cache = ConceptCache(kb_dir)
        concepts = cache.get_concepts()
        assert len(concepts) == 0


@pytest.mark.skipif(not _CACHE_AVAILABLE, reason="cache 模块导入依赖不满足")
class TestConceptCacheClear:
    """测试缓存清理."""

    def test_clear_removes_cache_file(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "test.md").write_text(
            "---\ntitle: Test\ntype: fact\n---\nBody", encoding="utf-8"
        )
        cache = ConceptCache(kb_dir)
        cache.get_concepts()
        assert cache.cache_path.exists()

        cache.clear()
        assert not cache.cache_path.exists()


# ============================================================================
# EmbedIncremental Tests
# ============================================================================

@pytest.mark.skipif(not _CACHE_AVAILABLE, reason="cache 模块导入依赖不满足")
class TestEmbedIncremental:
    """测试 embed 增量更新管理."""

    def _create_atom(self, kb_dir, name):
        atom_file = kb_dir / f"{name}.md"
        atom_file.write_text(
            f"---\ntitle: {name}\ntype: fact\n---\nBody", encoding="utf-8"
        )
        return atom_file

    def test_get_pending_atoms_all_new(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        self._create_atom(kb_dir, "atom1")
        self._create_atom(kb_dir, "atom2")

        embed = EmbedIncremental(kb_dir)
        added, updated = embed.get_pending_atoms()
        assert len(added) == 2
        assert len(updated) == 0

    def test_mark_embedded(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        self._create_atom(kb_dir, "atom1")

        embed = EmbedIncremental(kb_dir)
        added, _ = embed.get_pending_atoms()
        embed.mark_embedded(added)

        # 再次检查应无新增
        added2, _ = embed.get_pending_atoms()
        assert len(added2) == 0

    def test_remove_embedded(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        self._create_atom(kb_dir, "atom1")

        embed = EmbedIncremental(kb_dir)
        added, _ = embed.get_pending_atoms()
        embed.mark_embedded(added)
        embed.remove_embedded(added)

        # 移除后应重新检测为新增
        added2, _ = embed.get_pending_atoms()
        assert len(added2) == 1

    def test_detects_updated_file(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        self._create_atom(kb_dir, "atom1")

        embed = EmbedIncremental(kb_dir)
        added, _ = embed.get_pending_atoms()
        embed.mark_embedded(added)

        # 修改文件
        import time
        time.sleep(0.1)
        (kb_dir / "atom1.md").write_text(
            "---\ntitle: Updated\ntype: fact\n---\nNew body", encoding="utf-8"
        )

        _, updated = embed.get_pending_atoms()
        assert len(updated) == 1


# ============================================================================
# PaginatedQuerier Tests
# ============================================================================

@pytest.mark.skipif(not _CACHE_AVAILABLE, reason="cache 模块导入依赖不满足")
class TestPaginatedQuerier:
    """测试分页查询."""

    def _setup_kb(self, tmp_path, count=5):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        for i in range(count):
            (kb_dir / f"atom{i}.md").write_text(
                f"---\ntitle: Atom {i}\ntype: fact\ndescription: Test atom {i}\n---\nBody {i}",
                encoding="utf-8"
            )
        return kb_dir

    def test_query_paginated_basic(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path, 5)
        querier = PaginatedQuerier(kb_dir, page_size=2)
        result = querier.query_paginated()
        assert result["page"] == 1
        assert result["page_size"] == 2
        assert result["total_count"] == 5
        assert len(result["results"]) == 2

    def test_query_paginated_second_page(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path, 5)
        querier = PaginatedQuerier(kb_dir, page_size=2)
        result = querier.query_paginated(page=2)
        assert result["page"] == 2
        assert len(result["results"]) == 2

    def test_query_paginated_last_page(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path, 5)
        querier = PaginatedQuerier(kb_dir, page_size=2)
        result = querier.query_paginated(page=3)
        assert result["page"] == 3
        assert len(result["results"]) == 1

    def test_query_paginated_total_pages(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path, 5)
        querier = PaginatedQuerier(kb_dir, page_size=2)
        result = querier.query_paginated()
        assert result["total_pages"] == 3

    def test_query_paginated_with_search(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path, 5)
        querier = PaginatedQuerier(kb_dir, page_size=10)
        result = querier.query_paginated(query_str="Atom 0")
        assert result["total_count"] >= 1

    def test_query_paginated_by_type(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path, 3)
        querier = PaginatedQuerier(kb_dir, page_size=10)
        result = querier.query_paginated(by_type="fact")
        assert result["total_count"] == 3

    def test_query_paginated_empty_kb(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        querier = PaginatedQuerier(kb_dir)
        result = querier.query_paginated()
        assert result["total_count"] == 0
        assert result["results"] == []
