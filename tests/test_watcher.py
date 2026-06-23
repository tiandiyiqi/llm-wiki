"""Tests for lib/watcher.py — KnowledgeWatcher."""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from watchdog.events import FileCreatedEvent, FileModifiedEvent
except ImportError:
    pytest.skip("watchdog not installed", allow_module_level=True)

try:
    from lib.watcher import KnowledgeWatcher
except ImportError as exc:
    pytest.skip(f"Cannot import KnowledgeWatcher: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kb_dir(tmp_path):
    """Create a minimal KB directory structure."""
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    for subdir in ["facts", "opinions", "definitions", "methods", "data", "questions", "references"]:
        (kb_dir / "atoms" / subdir).mkdir(parents=True)
    meta_dir = kb_dir / ".llm-wiki"
    meta_dir.mkdir()
    return kb_dir


def _make_registry(kb_dir):
    """Create a mock KBRegistry."""
    registry = MagicMock()
    registry.get.return_value = {"path": str(kb_dir)}
    return registry


# ---------------------------------------------------------------------------
# Test KnowledgeWatcher initialization
# ---------------------------------------------------------------------------

class TestKnowledgeWatcherInit:

    def test_init_basic(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        assert watcher.kb_dir == kb_dir
        assert watcher.registry is registry
        assert watcher.observer is None

    def test_init_creates_processors(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        assert watcher.quick_capture is not None
        assert watcher.ingestor is not None


# ---------------------------------------------------------------------------
# Test set_progress_callback
# ---------------------------------------------------------------------------

class TestProgressCallback:

    def test_set_callback(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        callback = MagicMock()
        watcher.set_progress_callback(callback)
        assert watcher._progress_callback is callback

    def test_report_calls_callback(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        callback = MagicMock()
        watcher.set_progress_callback(callback)
        watcher._report("test message")
        callback.assert_called_once_with("test message")

    def test_report_without_callback(self, tmp_path):
        """Should not error when no callback is set."""
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        watcher._report("test message")  # Should not raise


# ---------------------------------------------------------------------------
# Test _should_process
# ---------------------------------------------------------------------------

class TestShouldProcess:

    def test_process_md_file(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        event = FileCreatedEvent(str(kb_dir / "test.md"))
        assert watcher._should_process(event) is True

    def test_ignore_non_md_file(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        event = FileCreatedEvent(str(kb_dir / "test.txt"))
        assert watcher._should_process(event) is False

    def test_ignore_atoms_directory(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        event = FileCreatedEvent(str(kb_dir / "atoms" / "facts" / "test.md"))
        assert watcher._should_process(event) is False

    def test_ignore_hidden_file(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        event = FileCreatedEvent(str(kb_dir / ".hidden.md"))
        assert watcher._should_process(event) is False

    def test_ignore_index_md(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        event = FileCreatedEvent(str(kb_dir / "index.md"))
        assert watcher._should_process(event) is False

    def test_ignore_log_md(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        event = FileCreatedEvent(str(kb_dir / "log.md"))
        assert watcher._should_process(event) is False


# ---------------------------------------------------------------------------
# Test _get_file_content
# ---------------------------------------------------------------------------

class TestGetFileContent:

    def test_read_existing_file(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        test_file = kb_dir / "test.md"
        test_file.write_text("Hello World", encoding="utf-8")
        content = watcher._get_file_content(test_file)
        assert content == "Hello World"

    def test_read_nonexistent_file(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        content = watcher._get_file_content(kb_dir / "nonexistent.md")
        assert content is None


# ---------------------------------------------------------------------------
# Test _extract_content_body
# ---------------------------------------------------------------------------

class TestExtractContentBody:

    def test_content_without_frontmatter(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        content = "Just plain text without frontmatter."
        body = watcher._extract_content_body(content)
        assert body == "Just plain text without frontmatter."

    def test_content_with_frontmatter(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        content = "---\ntype: fact\ntitle: Test\n---\nActual body content here."
        body = watcher._extract_content_body(content)
        assert body == "Actual body content here."

    def test_content_with_unclosed_frontmatter(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        content = "---\ntype: fact\nNo closing frontmatter"
        body = watcher._extract_content_body(content)
        # Should return the full content since no closing ---
        assert "type: fact" in body

    def test_empty_body_after_frontmatter(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        content = "---\ntype: fact\n---\n"
        body = watcher._extract_content_body(content)
        assert body == ""


# ---------------------------------------------------------------------------
# Test _process_file
# ---------------------------------------------------------------------------

class TestProcessFile:

    def test_short_content_uses_quick_capture(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        # Create a short content file
        short_file = kb_dir / "short.md"
        short_file.write_text("---\ntype: fact\n---\nShort note", encoding="utf-8")

        watcher.quick_capture = MagicMock()
        watcher.quick_capture.capture.return_value = (True, "Captured successfully")

        watcher._process_file(short_file)
        watcher.quick_capture.capture.assert_called_once()

    def test_long_content_uses_ingestor(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        # Create a long content file
        long_content = "---\ntype: method\n---\n" + "A" * 300
        long_file = kb_dir / "long.md"
        long_file.write_text(long_content, encoding="utf-8")

        watcher.ingestor = MagicMock()
        watcher.ingestor.ingest.return_value = True

        watcher._process_file(long_file)
        watcher.ingestor.ingest.assert_called_once()

    def test_process_nonexistent_file(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        # Should not raise, just return
        watcher._process_file(kb_dir / "nonexistent.md")

    def test_process_file_ingest_error(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        long_content = "---\ntype: method\n---\n" + "A" * 300
        long_file = kb_dir / "error.md"
        long_file.write_text(long_content, encoding="utf-8")

        watcher.ingestor = MagicMock()
        watcher.ingestor.ingest.side_effect = Exception("Ingestion error")

        # Should not raise, just report error
        watcher._process_file(long_file)


# ---------------------------------------------------------------------------
# Test on_created / on_modified
# ---------------------------------------------------------------------------

class TestEventHandlers:

    def test_on_created_directory_event_ignored(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        event = MagicMock()
        event.is_directory = True
        event.src_path = str(kb_dir / "subdir")
        # Should not raise
        watcher.on_created(event)

    def test_on_created_non_md_ignored(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        event = FileCreatedEvent(str(kb_dir / "test.txt"))
        # Should not process
        with patch.object(watcher, "_process_file") as mock_process:
            watcher.on_created(event)
            mock_process.assert_not_called()

    def test_on_created_md_file_processed(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        test_file = kb_dir / "new.md"
        test_file.write_text("---\ntype: fact\n---\nNew content", encoding="utf-8")
        event = FileCreatedEvent(str(test_file))

        with patch.object(watcher, "_process_file") as mock_process:
            watcher.on_created(event)
            mock_process.assert_called_once()

    def test_on_modified_directory_event_ignored(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        event = MagicMock()
        event.is_directory = True
        event.src_path = str(kb_dir / "subdir")
        watcher.on_modified(event)

    def test_on_modified_md_file_processed(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        test_file = kb_dir / "modified.md"
        test_file.write_text("---\ntype: fact\n---\nModified content", encoding="utf-8")
        event = FileModifiedEvent(str(test_file))

        with patch.object(watcher, "_process_file") as mock_process:
            watcher.on_modified(event)
            mock_process.assert_called_once()


# ---------------------------------------------------------------------------
# Test start / stop
# ---------------------------------------------------------------------------

class TestStartStop:

    def test_start_watching(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)

        mock_observer = MagicMock()
        with patch("lib.watcher.Observer", return_value=mock_observer):
            watcher.start([kb_dir])
            assert watcher.observer is not None
            mock_observer.schedule.assert_called_once()
            mock_observer.start.assert_called_once()

    def test_start_already_running(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        watcher.observer = MagicMock()  # Simulate already running
        watcher.start([kb_dir])  # Should warn and return

    def test_start_nonexistent_path(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)

        mock_observer = MagicMock()
        with patch("lib.watcher.Observer", return_value=mock_observer):
            watcher.start([Path("/nonexistent/path")])
            # Should not schedule nonexistent path
            mock_observer.schedule.assert_not_called()

    def test_stop_watching(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        mock_observer = MagicMock()
        watcher.observer = mock_observer
        watcher.stop()
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
        assert watcher.observer is None

    def test_stop_not_running(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        watcher.stop()  # Should not raise

    def test_run_forever_not_started(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        # Should not raise, just report not started
        watcher.run_forever()


# ---------------------------------------------------------------------------
# Test SHORT_CONTENT_THRESHOLD
# ---------------------------------------------------------------------------

class TestConstants:

    def test_threshold_value(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        registry = _make_registry(kb_dir)
        watcher = KnowledgeWatcher(kb_dir, registry)
        assert watcher.SHORT_CONTENT_THRESHOLD == 200
