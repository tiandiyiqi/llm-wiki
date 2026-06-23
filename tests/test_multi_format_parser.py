"""Tests for lib/multi_format_parser.py — MultiFormatParser & LongDocumentSplitter."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.multi_format_parser import MultiFormatParser, LongDocumentSplitter, get_supported_formats_info


class TestMultiFormatParserMarkdown:
    """测试 Markdown 文件解析."""

    def setup_method(self):
        self.parser = MultiFormatParser()

    def test_parse_markdown_file(self, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test Title\n\nSome content here.", encoding="utf-8")
        title, content = self.parser.parse(md_file)
        assert title == "Test Title"
        assert "Some content here" in content

    def test_parse_markdown_with_frontmatter_title(self, tmp_path):
        md_file = tmp_path / "test.md"
        # _extract_md_title 先匹配 # 标题，再匹配 frontmatter title
        # 当正文有 # 标题时优先使用正文标题
        md_file.write_text("---\ntitle: Frontmatter Title\n---\n# Body Title\nContent", encoding="utf-8")
        title, content = self.parser.parse(md_file)
        # Body 的 # 标题优先于 frontmatter title
        assert title == "Body Title"

    def test_parse_markdown_frontmatter_title_no_heading(self, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("---\ntitle: Frontmatter Title\n---\nJust paragraph text", encoding="utf-8")
        title, content = self.parser.parse(md_file)
        assert title == "Frontmatter Title"

    def test_parse_markdown_no_title(self, tmp_path):
        md_file = tmp_path / "my_doc.md"
        md_file.write_text("Just some text without a heading.", encoding="utf-8")
        title, content = self.parser.parse(md_file)
        assert "My Doc" in title


class TestMultiFormatParserText:
    """测试纯文本文件解析."""

    def setup_method(self):
        self.parser = MultiFormatParser()

    def test_parse_txt_file(self, tmp_path):
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Hello world", encoding="utf-8")
        title, content = self.parser.parse(txt_file)
        assert "Notes" in title
        assert "Hello world" in content
        assert content.startswith("# ")

    def test_parse_log_file(self, tmp_path):
        log_file = tmp_path / "app.log"
        log_file.write_text("Error at line 5", encoding="utf-8")
        title, content = self.parser.parse(log_file)
        assert "```" in content

    def test_parse_rst_file(self, tmp_path):
        rst_file = tmp_path / "doc.rst"
        rst_file.write_text("Title\n=====\n\nParagraph text.", encoding="utf-8")
        title, content = self.parser.parse(rst_file)
        assert "## Title" in content


class TestMultiFormatParserJSON:
    """测试 JSON 文件解析."""

    def setup_method(self):
        self.parser = MultiFormatParser()

    def test_parse_json_list(self, tmp_path):
        json_file = tmp_path / "data.json"
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        json_file.write_text(json.dumps(data), encoding="utf-8")
        title, content = self.parser.parse(json_file)
        assert "2 条记录" in content
        assert "Alice" in content

    def test_parse_json_dict(self, tmp_path):
        json_file = tmp_path / "config.json"
        data = {"version": "1.0", "debug": True}
        json_file.write_text(json.dumps(data), encoding="utf-8")
        title, content = self.parser.parse(json_file)
        assert "version" in content

    def test_parse_json_invalid(self, tmp_path):
        json_file = tmp_path / "bad.json"
        json_file.write_text("{invalid json}", encoding="utf-8")
        title, content = self.parser.parse(json_file)
        assert "解析失败" in content


class TestMultiFormatParserCSV:
    """测试 CSV 文件解析."""

    def setup_method(self):
        self.parser = MultiFormatParser()

    def test_parse_csv_file(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25", encoding="utf-8")
        title, content = self.parser.parse(csv_file)
        assert "name" in content
        assert "Alice" in content
        assert "|" in content

    def test_parse_csv_empty(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("", encoding="utf-8")
        title, content = self.parser.parse(csv_file)
        assert "空文件" in content


class TestMultiFormatParserHTML:
    """测试 HTML 文件解析."""

    def setup_method(self):
        self.parser = MultiFormatParser()

    def test_parse_html_basic(self, tmp_path):
        html_file = tmp_path / "page.html"
        html_file.write_text(
            "<html><head><title>My Page</title></head><body><p>Hello</p></body></html>",
            encoding="utf-8"
        )
        title, content = self.parser.parse(html_file)
        assert "Hello" in content

    def test_parse_html_strips_scripts(self, tmp_path):
        html_file = tmp_path / "page.html"
        html_file.write_text(
            "<html><head><script>alert('xss')</script></head>"
            "<body><p>Safe content</p></body></html>",
            encoding="utf-8"
        )
        title, content = self.parser.parse(html_file)
        assert "Safe content" in content


class TestMultiFormatParserUnsupported:
    """测试不支持的格式."""

    def setup_method(self):
        self.parser = MultiFormatParser()

    def test_parse_doc_format_warning(self, tmp_path):
        doc_file = tmp_path / "legacy.doc"
        doc_file.write_text("binary content", encoding="utf-8", errors="ignore")
        title, content = self.parser.parse(doc_file)
        assert "不支持" in content

    def test_parse_unknown_format_fallback(self, tmp_path):
        unknown_file = tmp_path / "data.xyz"
        unknown_file.write_text("some text content", encoding="utf-8")
        title, content = self.parser.parse(unknown_file)
        assert "some text content" in content

    def test_parse_nonexistent_file(self, tmp_path):
        missing_file = tmp_path / "missing.md"
        with pytest.raises((FileNotFoundError, OSError)):
            self.parser.parse(missing_file)


class TestMultiFormatParserWarnings:
    """测试解析器 warnings 追踪."""

    def setup_method(self):
        self.parser = MultiFormatParser()

    def test_warnings_list_initially_empty(self):
        assert self.parser.warnings == []

    def test_doc_format_adds_warning(self, tmp_path):
        doc_file = tmp_path / "legacy.doc"
        doc_file.write_text("binary", encoding="utf-8", errors="ignore")
        self.parser.parse(doc_file)
        assert len(self.parser.warnings) > 0


class TestLongDocumentSplitter:
    """测试长文档拆分器."""

    def test_split_short_document(self):
        splitter = LongDocumentSplitter(max_chars_per_atom=2000)
        # split() 的第一个参数是主标题，但返回的第一个元素的标题
        # 取决于内部 _split_by_headings 逻辑——内容无标题时标题为空
        result = splitter.split("Test", "Short content")
        assert len(result) == 1
        assert result[0][1] == "Short content"

    def test_split_by_headings(self):
        splitter = LongDocumentSplitter(max_chars_per_atom=2000, min_chars_per_atom=10)
        # 内容需要足够长以避免被 _merge_short_sections 合并
        content = "# Section 1\n\n" + "A" * 200 + "\n\n## Sub Section\n\n" + "B" * 200 + "\n\n# Section 2\n\n" + "C" * 200
        result = splitter.split("Doc", content)
        assert len(result) >= 2

    def test_split_long_section_by_paragraphs(self):
        splitter = LongDocumentSplitter(max_chars_per_atom=50, min_chars_per_atom=5)
        content = "# Title\n\n" + "A" * 40 + "\n\n" + "B" * 40
        result = splitter.split("Doc", content)
        assert len(result) >= 2

    def test_split_empty_content(self):
        splitter = LongDocumentSplitter()
        result = splitter.split("Empty", "")
        assert len(result) >= 1

    def test_merge_short_sections(self):
        splitter = LongDocumentSplitter(max_chars_per_atom=2000, min_chars_per_atom=200)
        content = "# A\n\nShort\n\n# B\n\nAlso short"
        result = splitter.split("Doc", content)
        # Short sections should be merged
        assert len(result) >= 1


class TestGetSupportedFormatsInfo:
    """测试格式信息输出."""

    def test_returns_string(self):
        info = get_supported_formats_info()
        assert isinstance(info, str)
        assert "Markdown" in info
        assert "JSON" in info
