"""Tests for lib/workflow.py — WorkflowManager and Notifier."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from lib.workflow import WorkflowManager, Notifier
except ImportError as exc:
    pytest.skip(f"Cannot import WorkflowManager/Notifier: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kb_dir(tmp_path):
    """Create a minimal KB directory with .llm-wiki metadata."""
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    meta_dir = kb_dir / ".llm-wiki"
    meta_dir.mkdir()
    return kb_dir


def _make_atom_file(kb_dir, filename="test-atom.md", status="draft"):
    """Create a minimal atom file with frontmatter."""
    atom_path = kb_dir / filename
    atom_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""---
type: fact
title: Test Atom
status: {status}
---

Test content for the atom.
"""
    atom_path.write_text(content, encoding="utf-8")
    return atom_path


# ---------------------------------------------------------------------------
# Test WorkflowManager initialization
# ---------------------------------------------------------------------------

class TestWorkflowManagerInit:

    def test_init_creates_workflow_dir(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        manager = WorkflowManager(kb_dir)
        assert manager.workflow_path.parent.exists()

    def test_init_sets_kb_dir(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        manager = WorkflowManager(kb_dir)
        assert manager.kb_dir == kb_dir


# ---------------------------------------------------------------------------
# Test submit
# ---------------------------------------------------------------------------

class TestWorkflowSubmit:

    @patch("lib.workflow.LifecycleManager")
    def test_submit_success(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir, status="draft")

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        manager.notifier = MagicMock()
        result = manager.submit(atom_path, submitter="alice")
        assert result is True
        mock_lifecycle.submit_for_review.assert_called_once_with(atom_path)

    @patch("lib.workflow.LifecycleManager")
    def test_submit_lifecycle_fails(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir, status="published")

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = False
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        result = manager.submit(atom_path)
        assert result is False

    @patch("lib.workflow.LifecycleManager")
    def test_submit_adds_to_review_queue(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir)

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        manager.notifier = MagicMock()
        manager.submit(atom_path, submitter="bob")

        data = manager._load()
        queue = data.get("review_queue", [])
        assert len(queue) == 1
        assert queue[0]["submitter"] == "bob"
        assert queue[0]["status"] == "pending"

    @patch("lib.workflow.LifecycleManager")
    def test_submit_sends_notification(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir)

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        mock_notifier = MagicMock()
        manager.notifier = mock_notifier
        manager.submit(atom_path, submitter="alice")
        mock_notifier.notify.assert_called_once()
        call_args = mock_notifier.notify.call_args
        assert "review_submitted" == call_args[1].get("event") or "review_submitted" in str(call_args)


# ---------------------------------------------------------------------------
# Test approve
# ---------------------------------------------------------------------------

class TestWorkflowApprove:

    @patch("lib.workflow.LifecycleManager")
    def test_approve_success(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir)

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        mock_lifecycle.publish.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        manager.notifier = MagicMock()

        # First submit
        manager.submit(atom_path, submitter="alice")
        # Then approve
        result = manager.approve(atom_path, reviewer="admin", comment="Looks good")
        assert result is True
        mock_lifecycle.publish.assert_called_once_with(atom_path)

    @patch("lib.workflow.LifecycleManager")
    def test_approve_publish_fails(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir)

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        mock_lifecycle.publish.return_value = False
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        manager.notifier = MagicMock()
        manager.submit(atom_path)

        result = manager.approve(atom_path, reviewer="admin")
        assert result is False

    @patch("lib.workflow.LifecycleManager")
    def test_approve_updates_queue_status(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir)

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        mock_lifecycle.publish.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        manager.notifier = MagicMock()
        manager.submit(atom_path)
        manager.approve(atom_path, reviewer="admin", comment="Approved")

        data = manager._load()
        approved_items = [item for item in data["review_queue"] if item["status"] == "approved"]
        assert len(approved_items) == 1
        assert approved_items[0]["reviewer"] == "admin"


# ---------------------------------------------------------------------------
# Test reject
# ---------------------------------------------------------------------------

class TestWorkflowReject:

    @patch("lib.workflow.LifecycleManager")
    def test_reject_success(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir)

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        mock_lifecycle.revert_to_draft.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        manager.notifier = MagicMock()
        manager.submit(atom_path)

        result = manager.reject(atom_path, reason="Needs revision", reviewer="admin")
        assert result is True
        mock_lifecycle.revert_to_draft.assert_called_once_with(atom_path)

    @patch("lib.workflow.LifecycleManager")
    def test_reject_updates_queue_status(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir)

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        manager.notifier = MagicMock()
        manager.submit(atom_path)
        manager.reject(atom_path, reason="Bad quality", reviewer="admin")

        data = manager._load()
        rejected_items = [item for item in data["review_queue"] if item["status"] == "rejected"]
        assert len(rejected_items) == 1
        assert rejected_items[0]["reject_reason"] == "Bad quality"

    @patch("lib.workflow.LifecycleManager")
    def test_reject_sends_notification(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir)

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        mock_notifier = MagicMock()
        manager.notifier = mock_notifier
        manager.submit(atom_path)
        manager.reject(atom_path, reason="Fix needed", reviewer="admin")
        # Should have been called for both submit and reject
        assert mock_notifier.notify.call_count >= 2


# ---------------------------------------------------------------------------
# Test get_pending_reviews
# ---------------------------------------------------------------------------

class TestGetPendingReviews:

    @patch("lib.workflow.LifecycleManager")
    def test_get_pending_empty(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        MockLifecycle.return_value = MagicMock()
        manager = WorkflowManager(kb_dir)
        pending = manager.get_pending_reviews()
        assert pending == []

    @patch("lib.workflow.LifecycleManager")
    def test_get_pending_with_submitted(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir)

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        manager.notifier = MagicMock()
        manager.submit(atom_path)

        pending = manager.get_pending_reviews()
        assert len(pending) == 1
        assert pending[0]["status"] == "pending"


# ---------------------------------------------------------------------------
# Test get_review_history
# ---------------------------------------------------------------------------

class TestGetReviewHistory:

    @patch("lib.workflow.LifecycleManager")
    def test_get_history_empty(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        MockLifecycle.return_value = MagicMock()
        manager = WorkflowManager(kb_dir)
        history = manager.get_review_history()
        assert history == []

    @patch("lib.workflow.LifecycleManager")
    def test_get_history_by_atom_id(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom_path = _make_atom_file(kb_dir)

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        mock_lifecycle.publish.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        manager.notifier = MagicMock()
        manager.submit(atom_path)
        manager.approve(atom_path, reviewer="admin")

        atom_id = manager._get_atom_id(atom_path)
        history = manager.get_review_history(atom_id=atom_id)
        assert len(history) == 1

    @patch("lib.workflow.LifecycleManager")
    def test_get_history_excludes_pending(self, MockLifecycle, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        atom1 = _make_atom_file(kb_dir, filename="atom1.md")
        atom2 = _make_atom_file(kb_dir, filename="atom2.md")

        mock_lifecycle = MagicMock()
        mock_lifecycle.submit_for_review.return_value = True
        mock_lifecycle.publish.return_value = True
        MockLifecycle.return_value = mock_lifecycle

        manager = WorkflowManager(kb_dir)
        manager.lifecycle = mock_lifecycle
        manager.notifier = MagicMock()
        manager.submit(atom1)
        manager.submit(atom2)
        manager.approve(atom1, reviewer="admin")

        # History without atom_id should exclude pending
        history = manager.get_review_history()
        for item in history:
            assert item["status"] != "pending"


# ---------------------------------------------------------------------------
# Test _get_atom_id
# ---------------------------------------------------------------------------

class TestGetAtomId:

    def test_relative_path(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        MockLifecycle = MagicMock()
        with patch("lib.workflow.LifecycleManager", MockLifecycle):
            manager = WorkflowManager(kb_dir)
        atom_path = kb_dir / "facts" / "test.md"
        atom_id = manager._get_atom_id(atom_path)
        assert "facts" in atom_id or "test" in atom_id

    def test_absolute_path_fallback(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        MockLifecycle = MagicMock()
        with patch("lib.workflow.LifecycleManager", MockLifecycle):
            manager = WorkflowManager(kb_dir)
        # Path not relative to kb_dir
        atom_path = Path("/some/other/path/test.md")
        atom_id = manager._get_atom_id(atom_path)
        assert str(atom_path) == atom_id


# ---------------------------------------------------------------------------
# Test _load / _save
# ---------------------------------------------------------------------------

class TestWorkflowLoadSave:

    def test_load_missing_file(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        MockLifecycle = MagicMock()
        with patch("lib.workflow.LifecycleManager", MockLifecycle):
            manager = WorkflowManager(kb_dir)
        # Remove workflow file
        if manager.workflow_path.exists():
            manager.workflow_path.unlink()
        data = manager._load()
        assert data == {}

    def test_load_invalid_json(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        MockLifecycle = MagicMock()
        with patch("lib.workflow.LifecycleManager", MockLifecycle):
            manager = WorkflowManager(kb_dir)
        manager.workflow_path.write_text("not json", encoding="utf-8")
        data = manager._load()
        assert data == {}

    def test_save_and_load(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        MockLifecycle = MagicMock()
        with patch("lib.workflow.LifecycleManager", MockLifecycle):
            manager = WorkflowManager(kb_dir)
        data = {"review_queue": [{"atom_id": "test", "status": "pending"}]}
        manager._save(data)
        loaded = manager._load()
        assert loaded == data


# ---------------------------------------------------------------------------
# Test Notifier
# ---------------------------------------------------------------------------

class TestNotifier:

    def test_init_creates_config_dir(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        assert notifier.config_path.parent.exists()

    def test_notify_without_webhooks(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        result = notifier.notify("Test Title", "Test Message", event="test")
        assert result is True

    def test_notify_records_inapp(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        notifier.notify("Title", "Message", event="test")
        inbox = notifier.get_inbox()
        assert len(inbox) > 0
        assert inbox[-1]["title"] == "Title"

    def test_add_webhook(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        result = notifier.add_webhook("test-hook", "https://example.com/hook", wtype="generic")
        assert result is True
        config = notifier._load_config()
        assert len(config["webhooks"]) == 1
        assert config["webhooks"][0]["name"] == "test-hook"

    def test_remove_webhook(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        notifier.add_webhook("hook1", "https://example.com/1")
        notifier.add_webhook("hook2", "https://example.com/2")
        result = notifier.remove_webhook("hook1")
        assert result is True
        config = notifier._load_config()
        assert len(config["webhooks"]) == 1
        assert config["webhooks"][0]["name"] == "hook2"

    def test_remove_nonexistent_webhook(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        result = notifier.remove_webhook("nonexistent")
        assert result is True  # Always returns True

    def test_get_inbox_empty(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        inbox = notifier.get_inbox()
        assert inbox == []

    def test_get_inbox_with_limit(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        for i in range(25):
            notifier.notify(f"Title {i}", f"Message {i}")
        inbox = notifier.get_inbox(limit=10)
        assert len(inbox) <= 10

    def test_inbox_truncated_at_100(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        for i in range(110):
            notifier.notify(f"Title {i}", f"Message {i}")
        config = notifier._load_config()
        assert len(config["inbox"]) <= 100

    @patch("lib.workflow.urlopen")
    def test_send_webhook_generic(self, mock_urlopen, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        webhook = {"url": "https://example.com/hook", "type": "generic"}
        result = notifier._send_webhook(webhook, "Title", "Message", "test")
        assert result is True

    @patch("lib.workflow.urlopen")
    def test_send_webhook_wechat(self, mock_urlopen, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        webhook = {"url": "https://example.com/wechat", "type": "wechat"}
        result = notifier._send_webhook(webhook, "Title", "Message", "test")
        assert result is True

    @patch("lib.workflow.urlopen")
    def test_send_webhook_dingtalk(self, mock_urlopen, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        webhook = {"url": "https://example.com/dingtalk", "type": "dingtalk"}
        result = notifier._send_webhook(webhook, "Title", "Message", "test")
        assert result is True

    @patch("lib.workflow.urlopen")
    def test_send_webhook_feishu(self, mock_urlopen, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        webhook = {"url": "https://example.com/feishu", "type": "feishu"}
        result = notifier._send_webhook(webhook, "Title", "Message", "test")
        assert result is True

    @patch("lib.workflow.urlopen")
    def test_send_webhook_failure(self, mock_urlopen, tmp_path):
        from urllib.error import URLError
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        mock_urlopen.side_effect = URLError("Connection error")
        webhook = {"url": "https://example.com/hook", "type": "generic"}
        result = notifier._send_webhook(webhook, "Title", "Message", "test")
        assert result is False

    def test_send_webhook_no_url(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        webhook = {"type": "generic"}
        result = notifier._send_webhook(webhook, "Title", "Message", "test")
        assert result is False

    def test_notify_with_webhooks(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        notifier.add_webhook("test-hook", "https://example.com/hook")
        with patch.object(notifier, "_send_webhook", return_value=True) as mock_send:
            result = notifier.notify("Title", "Message", event="test")
            assert result is True
            mock_send.assert_called_once()

    def test_load_config_missing_file(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        notifier.config_path.unlink(missing_ok=True)
        config = notifier._load_config()
        assert config == {"webhooks": [], "inbox": []}

    def test_load_config_invalid_json(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        notifier.config_path.write_text("not json", encoding="utf-8")
        config = notifier._load_config()
        assert config == {"webhooks": [], "inbox": []}

    def test_save_and_load_config(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        notifier = Notifier(kb_dir)
        config = {"webhooks": [{"name": "test", "url": "https://example.com"}], "inbox": []}
        notifier._save_config(config)
        loaded = notifier._load_config()
        assert loaded == config
