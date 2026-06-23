"""Tests for lib/ingestor.py — KnowledgeIngestor."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from lib.ingestor import KnowledgeIngestor
except ImportError as exc:
    pytest.skip(f"Cannot import KnowledgeIngestor: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kb_dir(tmp_path):
    """Create a minimal KB directory structure."""
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    for subdir in ["facts", "opinions", "definitions", "methods", "data", "questions", "references"]:
        (kb_dir / "atoms" / subdir).mkdir(parents=True)
    return kb_dir


def _make_source_file(tmp_path, filename="source.md", content=None):
    """Create a source file for ingestion."""
    source_dir = tmp_path / "sources"
    source_dir.mkdir(exist_ok=True)
    source_path = source_dir / filename
    if content is None:
        content = """# Test Document

This is a test document about Python programming.
It contains information about installation and configuration steps.

## Installation

Step 1: Download the installer.
Step 2: Run the installer.
Step 3: Configure the environment.

## Configuration

Set the environment variables and configure the system properly.
"""
    source_path.write_text(content, encoding="utf-8")
    return source_path


# ---------------------------------------------------------------------------
# Test KnowledgeIngestor initialization
# ---------------------------------------------------------------------------

class TestKnowledgeIngestorInit:

    def test_init_basic(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        assert ingestor.kb_dir == kb_dir
        assert ingestor.source_path == Path(".")

    def test_init_with_source_path(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "source.md"
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        assert ingestor.source_path == source_path


# ---------------------------------------------------------------------------
# Test ingest
# ---------------------------------------------------------------------------

class TestIngest:

    def test_ingest_nonexistent_source(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        result = ingestor.ingest(source_path=Path("/nonexistent/file.md"))
        assert result is False

    def test_ingest_short_document(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = _make_source_file(tmp_path, content="# Short Doc\n\nBrief content about testing.")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        # Mock the format parser to return known content
        ingestor.format_parser = MagicMock()
        ingestor.format_parser.parse.return_value = ("Short Doc", "Brief content about testing.")
        ingestor.format_parser.warnings = []
        result = ingestor.ingest()
        assert result is True

    def test_ingest_long_document_splits(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        long_content = "A" * 3000  # Exceeds SPLIT_THRESHOLD
        source_path = _make_source_file(tmp_path, content=long_content)
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        ingestor.format_parser = MagicMock()
        ingestor.format_parser.parse.return_value = ("Long Doc", long_content)
        ingestor.format_parser.warnings = []
        # Mock splitter to return sections
        ingestor.splitter = MagicMock()
        ingestor.splitter.split.return_value = [
            ("Part 1", "Content for part 1 " * 50),
            ("Part 2", "Content for part 2 " * 50),
        ]
        result = ingestor.ingest(split_long=True)
        assert result is True

    def test_ingest_with_source_path_override(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source1 = _make_source_file(tmp_path, filename="source1.md", content="# Doc 1\n\nContent one.")
        source2 = _make_source_file(tmp_path, filename="source2.md", content="# Doc 2\n\nContent two.")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source1)
        ingestor.format_parser = MagicMock()
        ingestor.format_parser.parse.return_value = ("Doc 2", "Content two.")
        ingestor.format_parser.warnings = []
        result = ingestor.ingest(source_path=source2)
        assert result is True
        assert ingestor.source_path == source2

    def test_ingest_no_auto_detect(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = _make_source_file(tmp_path, content="# Custom Type\n\nSome content here.")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        ingestor.format_parser = MagicMock()
        ingestor.format_parser.parse.return_value = ("Custom Type", "Some content here.")
        ingestor.format_parser.warnings = []
        result = ingestor.ingest(auto_detect_type=False, default_type="fact")
        assert result is True

    def test_ingest_creates_atom_file(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = _make_source_file(tmp_path, content="# Test\n\nContent for atom creation test.")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        ingestor.format_parser = MagicMock()
        ingestor.format_parser.parse.return_value = ("Test", "Content for atom creation test.")
        ingestor.format_parser.warnings = []
        result = ingestor.ingest()
        assert result is True
        # Check that an atom file was created
        atom_files = list((kb_dir / "atoms").rglob("*.md"))
        assert len(atom_files) > 0

    def test_ingest_updates_log(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = _make_source_file(tmp_path, content="# Log Test\n\nContent for log update test.")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        ingestor.format_parser = MagicMock()
        ingestor.format_parser.parse.return_value = ("Log Test", "Content for log update test.")
        ingestor.format_parser.warnings = []
        ingestor.ingest()
        log_path = kb_dir / "log.md"
        assert log_path.exists()


# ---------------------------------------------------------------------------
# Test _detect_source_type
# ---------------------------------------------------------------------------

class TestDetectSourceType:

    def test_official_docs(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "official_docs" / "guide.md"
        source_path.parent.mkdir(parents=True)
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        assert ingestor._detect_source_type() == "official"

    def test_blog_source(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "blog" / "post.md"
        source_path.parent.mkdir(parents=True)
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        assert ingestor._detect_source_type() == "blog"

    def test_pdf_source(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "document.pdf"
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        assert ingestor._detect_source_type() == "document"

    def test_readme_source(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "README.md"
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        assert ingestor._detect_source_type() == "official"

    def test_user_source(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "notes.md"
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        assert ingestor._detect_source_type() == "user"


# ---------------------------------------------------------------------------
# Test _extract_description
# ---------------------------------------------------------------------------

class TestExtractDescription:

    def test_extract_from_plain_text(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        desc = ingestor._extract_description("This is the first paragraph.\n\nSecond paragraph follows.")
        assert "first paragraph" in desc

    def test_extract_skips_frontmatter(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        content = "---\ntype: fact\n---\nThis is the real content after frontmatter."
        desc = ingestor._extract_description(content)
        assert "real content" in desc
        assert "type" not in desc

    def test_extract_skips_headings(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        content = "# Heading\n\n## Subheading\n\nActual content here."
        desc = ingestor._extract_description(content)
        assert "Heading" not in desc
        assert "Actual content" in desc

    def test_extract_skips_code_blocks(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        content = "```\ncode here\n```\n\nReal description text."
        desc = ingestor._extract_description(content)
        assert "code here" not in desc
        assert "Real description" in desc

    def test_extract_truncates_long_text(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        long_text = "A" * 200
        desc = ingestor._extract_description(long_text)
        assert len(desc) <= 103  # 100 chars + "..."

    def test_extract_no_description(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        desc = ingestor._extract_description("")
        assert desc == "No description available"


# ---------------------------------------------------------------------------
# Test _extract_tags
# ---------------------------------------------------------------------------

class TestExtractTags:

    def test_extract_python_tag(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        tags = ingestor._extract_tags("How to install python on ubuntu")
        assert "python" in tags
        assert "ubuntu" in tags

    def test_extract_docker_tag(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        tags = ingestor._extract_tags("Deploy with docker and kubernetes")
        assert "docker" in tags
        assert "kubernetes" in tags

    def test_extract_default_general_tag(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        tags = ingestor._extract_tags("Random text with no tech keywords")
        assert tags == ["general"]

    def test_extract_limits_to_5_tags(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        content = "python javascript golang rust java docker kubernetes"
        tags = ingestor._extract_tags(content)
        assert len(tags) <= 5


# ---------------------------------------------------------------------------
# Test _determine_type
# ---------------------------------------------------------------------------

class TestDetermineType:

    def test_detect_method(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        assert ingestor._determine_type("How to install and configure step by step", True, "method") == "method"

    def test_detect_fact(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        assert ingestor._determine_type("The requirement and version support limit", True, "method") == "fact"

    def test_detect_definition(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        assert ingestor._determine_type("What is the definition of this concept", True, "method") == "definition"

    def test_detect_data(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        assert ingestor._determine_type("Statistics and performance data metrics", True, "method") == "data"

    def test_no_auto_detect_uses_default(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        assert ingestor._determine_type("install step", False, "fact") == "fact"

    def test_default_type_when_no_match(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        assert ingestor._determine_type("Generic text with no keywords", True, "method") == "method"


# ---------------------------------------------------------------------------
# Test _generate_atom_id
# ---------------------------------------------------------------------------

class TestGenerateAtomId:

    def test_generates_slug(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        atom_id = ingestor._generate_atom_id("Hello World Test")
        assert "hello-world-test" in atom_id

    def test_removes_special_chars(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        atom_id = ingestor._generate_atom_id("Test! @#$ Title")
        assert "!" not in atom_id
        assert "@" not in atom_id

    def test_includes_timestamp(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        atom_id = ingestor._generate_atom_id("Test")
        # Should end with a timestamp like -202606241200
        parts = atom_id.split("-")
        assert len(parts) >= 2

    def test_collapses_multiple_hyphens(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        ingestor = KnowledgeIngestor(kb_dir)
        atom_id = ingestor._generate_atom_id("A   B   C")
        assert "---" not in atom_id


# ---------------------------------------------------------------------------
# Test _create_atom_content
# ---------------------------------------------------------------------------

class TestCreateAtomContent:

    def test_creates_frontmatter(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "test.md"
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        content = ingestor._create_atom_content(
            title="Test Title",
            description="Test description",
            atom_type="fact",
            tags=["test"],
            source_path=source_path,
            source_type="user",
            original_content="Original content here.",
        )
        assert content.startswith("---")
        assert "type:" in content and "fact" in content
        assert "Test Title" in content

    def test_includes_citations(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "cite.md"
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        content = ingestor._create_atom_content(
            title="Cited",
            description="Desc",
            atom_type="method",
            tags=["test"],
            source_path=source_path,
            source_type="user",
            original_content="Content.",
        )
        assert "Citations" in content


# ---------------------------------------------------------------------------
# Test _update_log
# ---------------------------------------------------------------------------

class TestUpdateLog:

    def test_creates_log_if_missing(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "test.md"
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        ingestor._update_log("Test Title", "test-atom-001", "fact")
        log_path = kb_dir / "log.md"
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "Test Title" in content

    def test_appends_to_existing_log(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "test.md"
        source_path.write_text("content", encoding="utf-8")
        log_path = kb_dir / "log.md"
        log_path.write_text("# Knowledge Base Log\n\n## 2026-01-01\n\n* Old entry\n", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        ingestor._update_log("New Title", "new-atom-001", "method")
        content = log_path.read_text(encoding="utf-8")
        assert "New Title" in content

    def test_batch_log_entry(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "test.md"
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        ingestor._update_log("Batch Title", "", "", count=5)
        log_path = kb_dir / "log.md"
        content = log_path.read_text(encoding="utf-8")
        assert "5 atoms" in content


# ---------------------------------------------------------------------------
# Test _create_atom_file
# ---------------------------------------------------------------------------

class TestCreateAtomFile:

    def test_creates_file_in_correct_directory(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "test.md"
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        result = ingestor._create_atom_file(
            title="Test",
            description="Desc",
            atom_type="fact",
            tags=["test"],
            source_path=source_path,
            source_type="user",
            original_content="Content.",
            atom_id="test-atom-001",
        )
        assert result is True
        atom_path = kb_dir / "atoms" / "facts" / "test-atom-001.md"
        assert atom_path.exists()

    def test_unknown_type_uses_methods(self, tmp_path):
        kb_dir = _make_kb_dir(tmp_path)
        source_path = tmp_path / "test.md"
        source_path.write_text("content", encoding="utf-8")
        ingestor = KnowledgeIngestor(kb_dir, source_path=source_path)
        result = ingestor._create_atom_file(
            title="Test",
            description="Desc",
            atom_type="unknown_type",
            tags=["test"],
            source_path=source_path,
            source_type="user",
            original_content="Content.",
            atom_id="test-unknown-001",
        )
        assert result is True
        atom_path = kb_dir / "atoms" / "methods" / "test-unknown-001.md"
        assert atom_path.exists()
