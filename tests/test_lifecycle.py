"""Tests for lib/lifecycle.py — LifecycleManager."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.lifecycle import LifecycleManager, VALID_STATUSES, STATUS_TRANSITIONS


class TestLifecycleConstants:
    """测试生命周期常量定义."""

    def test_valid_statuses_contains_expected(self):
        expected = ['draft', 'review', 'published', 'archived', 'deprecated']
        assert VALID_STATUSES == expected

    def test_all_statuses_have_transitions(self):
        for status in VALID_STATUSES:
            assert status in STATUS_TRANSITIONS

    def test_draft_can_transition_to_review(self):
        assert 'review' in STATUS_TRANSITIONS['draft']

    def test_published_can_transition_to_archived(self):
        assert 'archived' in STATUS_TRANSITIONS['published']

    def test_published_can_transition_to_deprecated(self):
        assert 'deprecated' in STATUS_TRANSITIONS['published']

    def test_deprecated_can_return_to_published(self):
        assert 'published' in STATUS_TRANSITIONS['deprecated']


class TestLifecycleManagerGetStatus:
    """测试获取原子状态."""

    def test_get_status_published_default(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("---\ntitle: Test\ntype: fact\n---\nContent", encoding="utf-8")

        manager = LifecycleManager(kb_dir)
        status = manager.get_status(atom_file)
        assert status == "published"

    def test_get_status_explicit_draft(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("---\ntitle: Test\ntype: fact\nstatus: draft\n---\nContent", encoding="utf-8")

        manager = LifecycleManager(kb_dir)
        status = manager.get_status(atom_file)
        assert status == "draft"

    def test_get_status_no_frontmatter(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("Just content without frontmatter", encoding="utf-8")

        manager = LifecycleManager(kb_dir)
        status = manager.get_status(atom_file)
        assert status == "published"


class TestLifecycleManagerChangeStatus:
    """测试状态变更."""

    def _create_atom(self, kb_dir, status="draft"):
        atom_file = kb_dir / "test.md"
        atom_file.write_text(
            f"---\ntitle: Test\ntype: fact\nstatus: {status}\n---\nContent",
            encoding="utf-8"
        )
        return atom_file

    def test_change_status_valid_transition(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = self._create_atom(kb_dir, "draft")

        manager = LifecycleManager(kb_dir)
        result = manager.change_status(atom_file, "review")
        assert result is True
        assert manager.get_status(atom_file) == "review"

    def test_change_status_invalid_transition(self, tmp_path):
        # published -> draft 不在 STATUS_TRANSITIONS 中
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text(
            "---\ntitle: Test\ntype: fact\nstatus: published\n---\nContent",
            encoding="utf-8"
        )
        manager = LifecycleManager(kb_dir)
        result = manager.change_status(atom_file, "draft")
        assert result is False

    def test_change_status_force_bypasses_rules(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = self._create_atom(kb_dir, "published")

        manager = LifecycleManager(kb_dir)
        result = manager.change_status(atom_file, "draft", force=True)
        assert result is True

    def test_change_status_invalid_status_returns_false(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = self._create_atom(kb_dir, "draft")

        manager = LifecycleManager(kb_dir)
        result = manager.change_status(atom_file, "nonexistent")
        assert result is False

    def test_change_status_nonexistent_file_returns_false(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = LifecycleManager(kb_dir)
        result = manager.change_status(kb_dir / "missing.md", "review")
        assert result is False

    def test_change_status_same_status_succeeds(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = self._create_atom(kb_dir, "draft")

        manager = LifecycleManager(kb_dir)
        result = manager.change_status(atom_file, "draft")
        assert result is True


class TestLifecycleManagerConvenienceMethods:
    """测试便捷方法."""

    def _create_atom(self, kb_dir, status="draft"):
        atom_file = kb_dir / "test.md"
        atom_file.write_text(
            f"---\ntitle: Test\ntype: fact\nstatus: {status}\n---\nContent",
            encoding="utf-8"
        )
        return atom_file

    def test_publish(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = self._create_atom(kb_dir, "review")
        manager = LifecycleManager(kb_dir)
        assert manager.publish(atom_file) is True

    def test_archive(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = self._create_atom(kb_dir, "published")
        manager = LifecycleManager(kb_dir)
        assert manager.archive(atom_file) is True

    def test_deprecate(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = self._create_atom(kb_dir, "published")
        manager = LifecycleManager(kb_dir)
        assert manager.deprecate(atom_file) is True

    def test_submit_for_review(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = self._create_atom(kb_dir, "draft")
        manager = LifecycleManager(kb_dir)
        assert manager.submit_for_review(atom_file) is True

    def test_revert_to_draft(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = self._create_atom(kb_dir, "review")
        manager = LifecycleManager(kb_dir)
        assert manager.revert_to_draft(atom_file) is True


class TestLifecycleManagerWriteFrontmatter:
    """测试 frontmatter 写回逻辑."""

    def test_write_preserves_body(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text(
            "---\ntitle: Test\ntype: fact\nstatus: draft\n---\nOriginal body content",
            encoding="utf-8"
        )
        manager = LifecycleManager(kb_dir)
        manager.change_status(atom_file, "review")

        content = atom_file.read_text(encoding="utf-8")
        assert "Original body content" in content
        assert "review" in content

    def test_write_adds_status_updated(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text(
            "---\ntitle: Test\ntype: fact\nstatus: draft\n---\nBody",
            encoding="utf-8"
        )
        manager = LifecycleManager(kb_dir)
        manager.change_status(atom_file, "review")

        content = atom_file.read_text(encoding="utf-8")
        assert "status_updated" in content

    def test_write_no_frontmatter_returns_false(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("No frontmatter here", encoding="utf-8")

        manager = LifecycleManager(kb_dir)
        result = manager._write_frontmatter(atom_file, {"status": "draft"})
        assert result is False
