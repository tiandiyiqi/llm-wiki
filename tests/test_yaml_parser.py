"""Tests for lib/yaml_parser.py — SimpleYAMLParser."""

import sys
from pathlib import Path

import pytest

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.yaml_parser import SimpleYAMLParser


class TestSimpleYAMLParserParse:
    """测试 SimpleYAMLParser.parse 方法."""

    def setup_method(self):
        self.parser = SimpleYAMLParser()

    def test_parse_empty_string(self):
        result = self.parser.parse("")
        assert result is None

    def test_parse_whitespace_only(self):
        result = self.parser.parse("   \n  \n  ")
        assert result is None

    def test_parse_simple_key_value(self):
        text = "title: Hello World"
        result = self.parser.parse(text)
        assert result is not None
        assert result["title"] == "Hello World"

    def test_parse_quoted_value_double(self):
        text = 'title: "Hello World"'
        result = self.parser.parse(text)
        assert result is not None
        assert result["title"] == "Hello World"

    def test_parse_quoted_value_single(self):
        text = "title: 'Hello World'"
        result = self.parser.parse(text)
        assert result is not None
        assert result["title"] == "Hello World"

    def test_parse_boolean_true(self):
        text = "enabled: true"
        result = self.parser.parse(text)
        assert result["enabled"] is True

    def test_parse_boolean_false(self):
        text = "enabled: false"
        result = self.parser.parse(text)
        assert result["enabled"] is False

    def test_parse_integer(self):
        text = "count: 42"
        result = self.parser.parse(text)
        assert result["count"] == 42
        assert isinstance(result["count"], int)

    def test_parse_negative_integer(self):
        text = "offset: -10"
        result = self.parser.parse(text)
        assert result["offset"] == -10

    def test_parse_float(self):
        text = "rate: 3.14"
        result = self.parser.parse(text)
        assert result["rate"] == 3.14
        assert isinstance(result["rate"], float)

    def test_parse_inline_list(self):
        text = 'tags: [python, test, yaml]'
        result = self.parser.parse(text)
        assert result["tags"] == ["python", "test", "yaml"]

    def test_parse_multiline_list(self):
        text = "tags:\n  - python\n  - test\n  - yaml"
        result = self.parser.parse(text)
        assert result["tags"] == ["python", "test", "yaml"]

    def test_parse_multiline_list_quoted(self):
        text = 'tags:\n  - "hello world"\n  - \'foo bar\''
        result = self.parser.parse(text)
        assert result["tags"] == ["hello world", "foo bar"]

    def test_parse_comment_lines_ignored(self):
        text = "# This is a comment\ntitle: Hello"
        result = self.parser.parse(text)
        assert result is not None
        assert result["title"] == "Hello"
        assert "# This is a comment" not in str(result)

    def test_parse_blank_lines_ignored(self):
        text = "title: Hello\n\ndescription: World"
        result = self.parser.parse(text)
        assert result["title"] == "Hello"
        assert result["description"] == "World"

    def test_parse_multiple_keys(self):
        text = "title: Test\ntype: fact\nstatus: active"
        result = self.parser.parse(text)
        assert result["title"] == "Test"
        assert result["type"] == "fact"
        assert result["status"] == "active"

    def test_parse_empty_value_triggers_list_mode(self):
        text = "tags:\n  - a\n  - b"
        result = self.parser.parse(text)
        assert result["tags"] == ["a", "b"]

    def test_parse_returns_none_when_no_valid_content(self):
        text = "# only comments\n\n# more comments"
        result = self.parser.parse(text)
        assert result is None


class TestSimpleYAMLParserDump:
    """测试 SimpleYAMLParser.dump 方法."""

    def setup_method(self):
        self.parser = SimpleYAMLParser()

    def test_dump_string_value(self):
        data = {"title": "Hello"}
        result = self.parser.dump(data)
        assert 'title: "Hello"' in result

    def test_dump_integer_value(self):
        data = {"count": 42}
        result = self.parser.dump(data)
        assert "count: 42" in result

    def test_dump_boolean_value(self):
        data = {"enabled": True}
        result = self.parser.dump(data)
        assert "enabled: true" in result

    def test_dump_false_boolean(self):
        data = {"enabled": False}
        result = self.parser.dump(data)
        assert "enabled: false" in result

    def test_dump_list_value(self):
        data = {"tags": ["python", "test"]}
        result = self.parser.dump(data)
        assert "tags:" in result
        assert "  - python" in result
        assert "  - test" in result

    def test_dump_float_value(self):
        data = {"rate": 3.14}
        result = self.parser.dump(data)
        assert "rate: 3.14" in result

    def test_dump_escapes_quotes_in_string(self):
        data = {"title": 'He said "hello"'}
        result = self.parser.dump(data)
        assert '\\"' in result


class TestSimpleYAMLParserRoundTrip:
    """测试 parse + dump 往返一致性."""

    def setup_method(self):
        self.parser = SimpleYAMLParser()

    def test_roundtrip_simple_dict(self):
        original = "title: Test\ntype: fact"
        parsed = self.parser.parse(original)
        assert parsed is not None
        dumped = self.parser.dump(parsed)
        reparsed = self.parser.parse(dumped)
        assert reparsed == parsed

    def test_roundtrip_with_list(self):
        original = "tags:\n  - a\n  - b\n  - c"
        parsed = self.parser.parse(original)
        assert parsed is not None
        dumped = self.parser.dump(parsed)
        reparsed = self.parser.parse(dumped)
        assert reparsed["tags"] == ["a", "b", "c"]
