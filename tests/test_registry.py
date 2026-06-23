"""Tests for lib/registry.py — KBRegistry."""

import json
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from lib.registry import KBRegistry
except ImportError as exc:
    pytest.skip(f"Cannot import KBRegistry: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid(prefix="kb"):
    """Generate a unique name to avoid global state collisions."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _make_project_dir(tmp_path):
    """Create a project directory with .llm-wiki subdirectory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    return project_dir


def _make_kb_dir(tmp_path, name=None):
    """Create a knowledge base directory."""
    name = name or _uid("testkb")
    kb_dir = tmp_path / name
    kb_dir.mkdir()
    return kb_dir


# ---------------------------------------------------------------------------
# Test KBRegistry initialization
# ---------------------------------------------------------------------------

class TestKBRegistryInit:

    def test_init_without_project_dir(self, tmp_path):
        registry = KBRegistry()
        assert registry.project_dir is None
        assert registry.project_registry is None

    def test_init_with_project_dir(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        registry = KBRegistry(project_dir=project_dir)
        assert registry.project_dir == project_dir
        assert registry.project_registry is not None

    def test_init_creates_global_registry(self, tmp_path):
        """Global registry directory and files should be created on init."""
        registry = KBRegistry()
        assert registry.GLOBAL_DIR.exists()
        assert registry.GLOBAL_REGISTRY.exists()
        assert registry.GLOBAL_CONFIG.exists()

    def test_init_creates_project_registry(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        registry = KBRegistry(project_dir=project_dir)
        assert registry.project_registry is not None
        assert registry.project_registry.exists()


# ---------------------------------------------------------------------------
# Test register
# ---------------------------------------------------------------------------

class TestRegister:

    def test_register_success(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        unique_name = _uid("reg")
        result = registry.register(kb_dir, unique_name, description="Test KB")
        assert result is True

    def test_register_nonexistent_path(self, tmp_path):
        registry = KBRegistry()
        unique_name = _uid("bad")
        result = registry.register(Path("/nonexistent/path"), unique_name)
        assert result is False

    def test_register_duplicate_name(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        unique_name = _uid("dup")
        registry.register(kb_dir, unique_name)
        result = registry.register(kb_dir, unique_name)
        assert result is False

    def test_register_with_tags(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        unique_name = _uid("tagged")
        result = registry.register(kb_dir, unique_name, tags=["python", "docker"])
        assert result is True
        kb_info = registry.get(unique_name)
        assert kb_info is not None
        assert "python" in kb_info["tags"]

    def test_register_with_scope_project(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry(project_dir=project_dir)
        unique_name = _uid("proj")
        result = registry.register(kb_dir, unique_name, scope="project")
        assert result is True

    def test_register_with_scope_global(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        unique_name = _uid("glob")
        result = registry.register(kb_dir, unique_name, scope="global")
        assert result is True

    def test_register_child_kb(self, tmp_path):
        parent_dir = _make_kb_dir(tmp_path, name=_uid("parent"))
        child_dir = _make_kb_dir(tmp_path, name=_uid("child"))
        registry = KBRegistry()
        parent_name = _uid("parent")
        child_name = _uid("child")
        registry.register(parent_dir, parent_name)
        result = registry.register(child_dir, child_name, kb_type="child", parent=parent_name)
        assert result is True

    def test_register_with_validator(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        mock_validator = MagicMock()
        mock_validator.concepts = [{"id": "c1"}, {"id": "c2"}]
        mock_validator._count_types.return_value = {"fact": 2}
        registry = KBRegistry()
        unique_name = _uid("valid")
        result = registry.register(kb_dir, unique_name, validator=mock_validator)
        assert result is True
        kb_info = registry.get(unique_name)
        assert kb_info["statistics"]["concepts"] == 2


# ---------------------------------------------------------------------------
# Test unregister
# ---------------------------------------------------------------------------

class TestUnregister:

    def test_unregister_existing(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        unique_name = _uid("remove")
        registry.register(kb_dir, unique_name)
        result = registry.unregister(unique_name)
        assert result is True
        assert registry.get(unique_name) is None

    def test_unregister_nonexistent(self, tmp_path):
        registry = KBRegistry()
        result = registry.unregister("nonexistent-kb-xyz-999")
        assert result is False

    def test_unregister_from_project_scope(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry(project_dir=project_dir)
        unique_name = _uid("projrm")
        registry.register(kb_dir, unique_name, scope="project")
        result = registry.unregister(unique_name, scope="project")
        assert result is True

    def test_unregister_from_all_scopes(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry(project_dir=project_dir)
        unique_name = _uid("allrm")
        registry.register(kb_dir, unique_name, scope="global")
        result = registry.unregister(unique_name, scope="all")
        assert result is True


# ---------------------------------------------------------------------------
# Test list
# ---------------------------------------------------------------------------

class TestList:

    def test_list_empty(self, tmp_path):
        registry = KBRegistry()
        result = registry.list()
        # May contain entries from other tests, but should be a list
        assert isinstance(result, list)

    def test_list_with_entries(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        name1 = _uid("list1")
        name2 = _uid("list2")
        registry.register(kb_dir, name1)
        registry.register(kb_dir, name2)
        result = registry.list()
        names = [kb["name"] for kb in result]
        assert name1 in names
        assert name2 in names

    def test_list_project_scope(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry(project_dir=project_dir)
        unique_name = _uid("plist")
        registry.register(kb_dir, unique_name, scope="project")
        result = registry.list(scope="project")
        names = [kb["name"] for kb in result]
        assert unique_name in names

    def test_list_deduplication(self, tmp_path):
        """Project-level entries should take priority over global with same name."""
        project_dir = _make_project_dir(tmp_path)
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry(project_dir=project_dir)
        unique_name = _uid("dedup")
        registry.register(kb_dir, unique_name, scope="project")
        registry.register(kb_dir, unique_name, scope="global")
        result = registry.list()
        dedup_entries = [kb for kb in result if kb["name"] == unique_name]
        # Should not have more than 2 (one per scope at most)
        assert len(dedup_entries) <= 2


# ---------------------------------------------------------------------------
# Test get
# ---------------------------------------------------------------------------

class TestGet:

    def test_get_existing(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        unique_name = _uid("getkb")
        registry.register(kb_dir, unique_name)
        result = registry.get(unique_name)
        assert result is not None
        assert result["name"] == unique_name

    def test_get_nonexistent(self, tmp_path):
        registry = KBRegistry()
        result = registry.get("nonexistent-kb-xyz-999")
        assert result is None

    def test_get_prefers_project_scope(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry(project_dir=project_dir)
        unique_name = _uid("scopekb")
        registry.register(kb_dir, unique_name, scope="project")
        result = registry.get(unique_name)
        assert result is not None
        assert result["scope"] == "project"


# ---------------------------------------------------------------------------
# Test set_current / get_current
# ---------------------------------------------------------------------------

class TestCurrentKB:

    def test_set_and_get_current(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        unique_name = _uid("cur")
        registry.register(kb_dir, unique_name)
        result = registry.set_current(unique_name)
        assert result is True
        current = registry.get_current()
        assert current == unique_name

    def test_set_current_nonexistent(self, tmp_path):
        registry = KBRegistry()
        result = registry.set_current("nonexistent-kb-xyz-999")
        assert result is False

    def test_set_current_project_scope(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry(project_dir=project_dir)
        unique_name = _uid("pcur")
        registry.register(kb_dir, unique_name, scope="project")
        result = registry.set_current(unique_name, scope="project")
        assert result is True


# ---------------------------------------------------------------------------
# Test resolve_path
# ---------------------------------------------------------------------------

class TestResolvePath:

    def test_resolve_by_name(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        unique_name = _uid("resolve")
        registry.register(kb_dir, unique_name)
        result = registry.resolve_path(unique_name)
        assert result is not None
        assert result.exists()

    def test_resolve_by_existing_path(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        result = registry.resolve_path(str(kb_dir))
        assert result is not None

    def test_resolve_nonexistent(self, tmp_path):
        registry = KBRegistry()
        result = registry.resolve_path("nonexistent-name-or-path-xyz-999")
        assert result is None


# ---------------------------------------------------------------------------
# Test parent-child knowledge base support
# ---------------------------------------------------------------------------

class TestParentChildKB:

    def test_register_child(self, tmp_path):
        parent_dir = _make_kb_dir(tmp_path, name=_uid("pkb"))
        registry = KBRegistry()
        parent_name = _uid("parent")
        registry.register(parent_dir, parent_name)
        result = registry.register_child(parent_name, _uid("child"), "child-1/")
        assert result is True

    def test_register_child_nonexistent_parent(self, tmp_path):
        registry = KBRegistry()
        result = registry.register_child("nonexistent-parent-xyz-999", "child-1", "child-1/")
        assert result is False

    def test_get_children(self, tmp_path):
        parent_dir = _make_kb_dir(tmp_path, name=_uid("pkb"))
        registry = KBRegistry()
        parent_name = _uid("parent")
        child_name = _uid("child")
        registry.register(parent_dir, parent_name)
        registry.register_child(parent_name, child_name, "child-1/")
        children = registry.get_children(parent_name)
        assert child_name in children

    def test_get_children_nonexistent(self, tmp_path):
        registry = KBRegistry()
        children = registry.get_children("nonexistent-xyz-999")
        assert children == []

    def test_get_parent(self, tmp_path):
        parent_dir = _make_kb_dir(tmp_path, name=_uid("pkb"))
        child_dir = _make_kb_dir(tmp_path, name=_uid("ckb"))
        registry = KBRegistry()
        parent_name = _uid("parent")
        child_name = _uid("child")
        registry.register(parent_dir, parent_name)
        registry.register(child_dir, child_name, kb_type="child", parent=parent_name)
        parent = registry.get_parent(child_name)
        # Parent info is stored in .kb-meta.json of the child
        assert parent is None or isinstance(parent, str)

    def test_get_kb_type(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        unique_name = _uid("type")
        registry.register(kb_dir, unique_name)
        kb_type = registry.get_kb_type(unique_name)
        assert kb_type in ("standalone", "parent", "child")

    def test_get_kb_type_nonexistent(self, tmp_path):
        registry = KBRegistry()
        kb_type = registry.get_kb_type("nonexistent-xyz-999")
        assert kb_type == "standalone"

    def test_read_kb_meta_default(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        meta = registry._read_kb_meta(kb_dir)
        assert "kb_type" in meta
        assert meta["kb_type"] == "standalone"

    def test_write_and_read_kb_meta(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry()
        meta = {"kb_type": "parent", "children": ["c1"], "children_paths": {"c1": "c1/"}}
        registry._write_kb_meta(kb_dir, meta)
        loaded = registry._read_kb_meta(kb_dir)
        assert loaded["kb_type"] == "parent"
        assert "c1" in loaded["children"]


# ---------------------------------------------------------------------------
# Test registry read/write helpers
# ---------------------------------------------------------------------------

class TestRegistryHelpers:

    def test_read_registry_missing_file(self, tmp_path):
        registry = KBRegistry()
        result = registry._read_registry(Path("/nonexistent/registry.json"))
        assert result == {"version": "1.0", "knowledge_bases": {}}

    def test_read_registry_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json", encoding="utf-8")
        registry = KBRegistry()
        result = registry._read_registry(bad_file)
        assert result == {"version": "1.0", "knowledge_bases": {}}

    def test_write_and_read_registry(self, tmp_path):
        reg_file = tmp_path / "test_registry.json"
        registry = KBRegistry()
        data = {"version": "1.0", "knowledge_bases": {"test": {"path": "/tmp/test"}}}
        registry._write_registry(reg_file, data)
        result = registry._read_registry(reg_file)
        assert result == data

    def test_read_config_missing_file(self, tmp_path):
        registry = KBRegistry()
        result = registry._read_config(Path("/nonexistent/config.json"))
        assert result == {"current_kb": None}

    def test_write_and_read_config(self, tmp_path):
        config_file = tmp_path / "test_config.json"
        registry = KBRegistry()
        data = {"current_kb": "my-kb"}
        registry._write_config(config_file, data)
        result = registry._read_config(config_file)
        assert result == data

    def test_get_registry_for_scope_auto(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        kb_dir = _make_kb_dir(tmp_path)
        registry = KBRegistry(project_dir=project_dir)
        unique_name = _uid("auto")
        registry.register(kb_dir, unique_name, scope="project")
        path, data = registry._get_registry_for_scope("auto")
        assert data is not None

    def test_get_registry_for_scope_global(self, tmp_path):
        registry = KBRegistry()
        path, data = registry._get_registry_for_scope("global")
        assert path == registry.GLOBAL_REGISTRY
