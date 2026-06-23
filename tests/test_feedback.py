"""Tests for lib/feedback.py — FeedbackManager."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestFeedbackImport:
    """测试 feedback 模块导入."""

    def test_import_feedback(self):
        try:
            from lib.feedback import FeedbackManager
        except ImportError as e:
            pytest.skip(f"无法导入 FeedbackManager: {e}")


try:
    from lib.feedback import FeedbackManager
    _FEEDBACK_AVAILABLE = True
except ImportError:
    _FEEDBACK_AVAILABLE = False


@pytest.mark.skipif(not _FEEDBACK_AVAILABLE, reason="FeedbackManager 导入依赖不满足")
class TestFeedbackManagerInit:
    """测试 FeedbackManager 初始化."""

    def test_init_creates_dir(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = FeedbackManager(kb_dir)
        assert manager.feedback_path.parent.exists()

    def test_init_feedback_path(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = FeedbackManager(kb_dir)
        assert manager.feedback_path.name == "feedback.json"


# ============================================================================
# Comment Tests
# ============================================================================

@pytest.mark.skipif(not _FEEDBACK_AVAILABLE, reason="FeedbackManager 导入依赖不满足")
class TestFeedbackManagerComment:
    """测试评论功能."""

    def _setup(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("---\ntitle: Test\n---\nBody", encoding="utf-8")
        manager = FeedbackManager(kb_dir)
        return manager, atom_file

    def test_add_comment_success(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        result = manager.add_comment(atom_file, "Great article!")
        assert result is True

    def test_add_comment_empty_text_fails(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        result = manager.add_comment(atom_file, "")
        assert result is False

    def test_add_comment_nonexistent_file_fails(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = FeedbackManager(kb_dir)
        result = manager.add_comment(kb_dir / "missing.md", "Comment")
        assert result is False

    def test_get_comments_empty(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        comments = manager.get_comments(atom_file)
        assert comments == []

    def test_add_and_get_comment(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.add_comment(atom_file, "First comment", author="Alice")
        manager.add_comment(atom_file, "Second comment", author="Bob")

        comments = manager.get_comments(atom_file)
        assert len(comments) == 2
        assert comments[0]["text"] == "First comment"
        assert comments[0]["author"] == "Alice"

    def test_comment_has_timestamp(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.add_comment(atom_file, "Hello")
        comments = manager.get_comments(atom_file)
        assert "timestamp" in comments[0]

    def test_comment_default_author(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.add_comment(atom_file, "Hello", author="")
        comments = manager.get_comments(atom_file)
        assert comments[0]["author"] == "anonymous"


# ============================================================================
# Favorite Tests
# ============================================================================

@pytest.mark.skipif(not _FEEDBACK_AVAILABLE, reason="FeedbackManager 导入依赖不满足")
class TestFeedbackManagerFavorite:
    """测试收藏功能."""

    def _setup(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("---\ntitle: Test\n---\nBody", encoding="utf-8")
        manager = FeedbackManager(kb_dir)
        return manager, atom_file

    def test_add_favorite(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        result = manager.add_favorite(atom_file, user="alice")
        assert result is True

    def test_add_favorite_idempotent(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.add_favorite(atom_file, user="alice")
        manager.add_favorite(atom_file, user="alice")
        favorites = manager.get_favorites(user="alice")
        assert len(favorites) == 1

    def test_remove_favorite(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.add_favorite(atom_file, user="alice")
        result = manager.remove_favorite(atom_file, user="alice")
        assert result is True
        assert len(manager.get_favorites(user="alice")) == 0

    def test_remove_favorite_not_favorited(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        result = manager.remove_favorite(atom_file, user="alice")
        assert result is False

    def test_get_favorites_default_user(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.add_favorite(atom_file)
        favorites = manager.get_favorites()
        assert len(favorites) == 1

    def test_favorites_per_user(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom1 = kb_dir / "atom1.md"
        atom1.write_text("---\ntitle: A1\n---\nB", encoding="utf-8")
        atom2 = kb_dir / "atom2.md"
        atom2.write_text("---\ntitle: A2\n---\nB", encoding="utf-8")

        manager = FeedbackManager(kb_dir)
        manager.add_favorite(atom1, user="alice")
        manager.add_favorite(atom2, user="bob")

        assert len(manager.get_favorites(user="alice")) == 1
        assert len(manager.get_favorites(user="bob")) == 1


# ============================================================================
# Rating Tests
# ============================================================================

@pytest.mark.skipif(not _FEEDBACK_AVAILABLE, reason="FeedbackManager 导入依赖不满足")
class TestFeedbackManagerRating:
    """测试评分功能."""

    def _setup(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("---\ntitle: Test\n---\nBody", encoding="utf-8")
        manager = FeedbackManager(kb_dir)
        return manager, atom_file

    def test_rate_success(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        result = manager.rate(atom_file, 4, user="alice")
        assert result is True

    def test_rate_out_of_range_low(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        result = manager.rate(atom_file, 0, user="alice")
        assert result is False

    def test_rate_out_of_range_high(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        result = manager.rate(atom_file, 6, user="alice")
        assert result is False

    def test_rate_boundary_values(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        assert manager.rate(atom_file, 1) is True
        assert manager.rate(atom_file, 5) is True

    def test_get_rating_empty(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        rating = manager.get_rating(atom_file)
        assert rating["average"] == 0
        assert rating["count"] == 0

    def test_get_rating_average(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.rate(atom_file, 4, user="alice")
        manager.rate(atom_file, 2, user="bob")

        rating = manager.get_rating(atom_file)
        assert rating["count"] == 2
        assert rating["average"] == 3.0

    def test_rating_overwrite_by_same_user(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.rate(atom_file, 3, user="alice")
        manager.rate(atom_file, 5, user="alice")

        rating = manager.get_rating(atom_file)
        assert rating["count"] == 1
        assert rating["average"] == 5.0


# ============================================================================
# Correction Tests
# ============================================================================

@pytest.mark.skipif(not _FEEDBACK_AVAILABLE, reason="FeedbackManager 导入依赖不满足")
class TestFeedbackManagerCorrection:
    """测试纠错功能."""

    def _setup(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("---\ntitle: Test\n---\nBody", encoding="utf-8")
        manager = FeedbackManager(kb_dir)
        return manager, atom_file

    def test_submit_correction(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        result = manager.submit_correction(atom_file, "Typo in paragraph 2", "Bob")
        assert result is True

    def test_get_corrections(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.submit_correction(atom_file, "Error 1", "Alice")
        manager.submit_correction(atom_file, "Error 2", "Bob")

        corrections = manager.get_corrections()
        assert len(corrections) == 2

    def test_get_corrections_by_status(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.submit_correction(atom_file, "Error 1", "Alice")

        corrections = manager.get_corrections(status="pending")
        assert len(corrections) == 1

        corrections = manager.get_corrections(status="resolved")
        assert len(corrections) == 0

    def test_correction_has_timestamp(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.submit_correction(atom_file, "Fix this")
        corrections = manager.get_corrections()
        assert "timestamp" in corrections[0]

    def test_correction_default_submitter(self, tmp_path):
        manager, atom_file = self._setup(tmp_path)
        manager.submit_correction(atom_file, "Fix this", submitter="")
        corrections = manager.get_corrections()
        assert corrections[0]["submitter"] == "anonymous"
