"""Tests for lib/timeline.py — TimelineGenerator."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestTimelineImport:
    """测试 timeline 模块导入."""

    def test_import_timeline(self):
        try:
            from lib.timeline import TimelineGenerator
        except ImportError as e:
            pytest.skip(f"无法导入 TimelineGenerator: {e}")


try:
    from lib.timeline import TimelineGenerator
    _TIMELINE_AVAILABLE = True
except ImportError:
    _TIMELINE_AVAILABLE = False


@pytest.mark.skipif(not _TIMELINE_AVAILABLE, reason="TimelineGenerator 导入依赖不满足")
class TestTimelineGeneratorInit:
    """测试 TimelineGenerator 初始化."""

    def test_init(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        gen = TimelineGenerator(kb_dir)
        assert gen.kb_dir == kb_dir
        assert gen.events == []


# ============================================================================
# JSON Data Generation Tests
# ============================================================================

@pytest.mark.skipif(not _TIMELINE_AVAILABLE, reason="TimelineGenerator 导入依赖不满足")
class TestTimelineGeneratorJsonData:
    """测试 JSON 数据生成."""

    def _setup_kb(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "atom1.md").write_text(
            "---\ntitle: First\ntype: fact\ncreated_at: 2026-01-15\n---\nBody",
            encoding="utf-8"
        )
        (kb_dir / "atom2.md").write_text(
            "---\ntitle: Second\ntype: method\ncreated_at: 2026-03-20\n---\nBody",
            encoding="utf-8"
        )
        return kb_dir

    def test_generate_json_data_basic(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        gen = TimelineGenerator(kb_dir)
        data = gen.generate_json_data()

        assert "events" in data
        assert "stats" in data
        assert len(data["events"]) == 2

    def test_generate_json_data_sorted_by_date(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        gen = TimelineGenerator(kb_dir)
        data = gen.generate_json_data()

        # 最新的在前
        assert data["events"][0]["date"] >= data["events"][1]["date"]

    def test_generate_json_data_stats(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        gen = TimelineGenerator(kb_dir)
        data = gen.generate_json_data()

        stats = data["stats"]
        assert stats["total"] == 2
        assert "fact" in stats["by_type"]
        assert "method" in stats["by_type"]

    def test_generate_json_data_by_month(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        gen = TimelineGenerator(kb_dir)
        data = gen.generate_json_data()

        assert len(data["stats"]["by_month"]) >= 1

    def test_generate_json_data_empty_kb(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        gen = TimelineGenerator(kb_dir)
        data = gen.generate_json_data()

        assert data["events"] == []
        assert data["stats"]["total"] == 0


# ============================================================================
# Date Extraction Tests
# ============================================================================

@pytest.mark.skipif(not _TIMELINE_AVAILABLE, reason="TimelineGenerator 导入依赖不满足")
class TestTimelineGeneratorDateExtraction:
    """测试日期提取逻辑."""

    def _make_gen(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        return TimelineGenerator(kb_dir)

    def test_extract_date_from_created_at(self, tmp_path):
        gen = self._make_gen(tmp_path)
        fm = {"created_at": "2026-03-15"}
        result = gen._extract_date(fm, Path("/dummy.md"))
        assert result == "2026-03-15"

    def test_extract_date_from_date_field(self, tmp_path):
        gen = self._make_gen(tmp_path)
        fm = {"date": "2026-05-01"}
        result = gen._extract_date(fm, Path("/dummy.md"))
        assert result == "2026-05-01"

    def test_extract_date_from_updated_at(self, tmp_path):
        gen = self._make_gen(tmp_path)
        fm = {"updated_at": "2026-06-10"}
        result = gen._extract_date(fm, Path("/dummy.md"))
        assert result == "2026-06-10"

    def test_extract_date_fallback_to_mtime(self, tmp_path):
        gen = self._make_gen(tmp_path)
        fm = {}
        # 需要一个真实文件来获取 mtime
        test_file = tmp_path / "kb" / "test.md"
        test_file.write_text("content", encoding="utf-8")
        result = gen._extract_date(fm, test_file)
        assert result is not None
        assert len(result) == 10  # YYYY-MM-DD

    def test_extract_date_none_when_no_info(self, tmp_path):
        gen = self._make_gen(tmp_path)
        fm = {}
        # 使用不存在的文件路径
        result = gen._extract_date(fm, Path("/nonexistent/file.md"))
        assert result is None


# ============================================================================
# Date Normalization Tests
# ============================================================================

@pytest.mark.skipif(not _TIMELINE_AVAILABLE, reason="TimelineGenerator 导入依赖不满足")
class TestTimelineGeneratorNormalizeDate:
    """测试日期标准化."""

    def _make_gen(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        return TimelineGenerator(kb_dir)

    def test_normalize_yyyy_mm_dd(self, tmp_path):
        gen = self._make_gen(tmp_path)
        assert gen._normalize_date("2026-03-15") == "2026-03-15"

    def test_normalize_yyyy_mm_dd_hh_mm_ss(self, tmp_path):
        gen = self._make_gen(tmp_path)
        assert gen._normalize_date("2026-03-15 10:30:00") == "2026-03-15"

    def test_normalize_iso_with_timezone(self, tmp_path):
        gen = self._make_gen(tmp_path)
        result = gen._normalize_date("2026-03-15T10:30:00Z")
        assert result is not None
        assert result.startswith("2026-03-15")

    def test_normalize_empty_returns_none(self, tmp_path):
        gen = self._make_gen(tmp_path)
        assert gen._normalize_date("") is None
        assert gen._normalize_date(None) is None

    def test_normalize_short_date(self, tmp_path):
        gen = self._make_gen(tmp_path)
        result = gen._normalize_date("2026-03")
        # Should attempt to parse or return None
        assert result is None or result.startswith("2026")


# ============================================================================
# HTML Generation Tests
# ============================================================================

@pytest.mark.skipif(not _TIMELINE_AVAILABLE, reason="TimelineGenerator 导入依赖不满足")
class TestTimelineGeneratorHTML:
    """测试 HTML 生成."""

    def _setup_kb(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "atom1.md").write_text(
            "---\ntitle: Test Atom\ntype: fact\ncreated_at: 2026-01-15\n---\nBody",
            encoding="utf-8"
        )
        return kb_dir

    def test_generate_creates_html_file(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        output_path = tmp_path / "timeline.html"
        gen = TimelineGenerator(kb_dir)
        result = gen.generate(output_path)

        assert result is True
        assert output_path.exists()

    def test_generate_html_contains_title(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        output_path = tmp_path / "timeline.html"
        gen = TimelineGenerator(kb_dir)
        gen.generate(output_path)

        content = output_path.read_text(encoding="utf-8")
        assert "知识时间线" in content
        assert "Test Atom" in content

    def test_generate_html_has_css(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        output_path = tmp_path / "timeline.html"
        gen = TimelineGenerator(kb_dir)
        gen.generate(output_path)

        content = output_path.read_text(encoding="utf-8")
        assert "<style>" in content

    def test_generate_empty_kb_returns_false(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        output_path = tmp_path / "timeline.html"
        gen = TimelineGenerator(kb_dir)
        result = gen.generate(output_path)
        assert result is False

    def test_generate_creates_parent_dir(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        output_path = tmp_path / "subdir" / "deep" / "timeline.html"
        gen = TimelineGenerator(kb_dir)
        result = gen.generate(output_path)
        assert result is True
        assert output_path.exists()


# ============================================================================
# Month Formatting Tests
# ============================================================================

@pytest.mark.skipif(not _TIMELINE_AVAILABLE, reason="TimelineGenerator 导入依赖不满足")
class TestTimelineGeneratorFormatMonth:
    """测试月份格式化."""

    def _make_gen(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        return TimelineGenerator(kb_dir)

    def test_format_month_january(self, tmp_path):
        gen = self._make_gen(tmp_path)
        result = gen._format_month("2026-01")
        assert "2026" in result
        assert "一月" in result

    def test_format_month_december(self, tmp_path):
        gen = self._make_gen(tmp_path)
        result = gen._format_month("2026-12")
        assert "十二月" in result

    def test_format_month_invalid(self, tmp_path):
        gen = self._make_gen(tmp_path)
        result = gen._format_month("invalid")
        assert result == "invalid"


# ============================================================================
# Events Loading Tests
# ============================================================================

@pytest.mark.skipif(not _TIMELINE_AVAILABLE, reason="TimelineGenerator 导入依赖不满足")
class TestTimelineGeneratorLoadEvents:
    """测试事件加载."""

    def test_load_events_skips_reserved(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "index.md").write_text("# Index\nContent", encoding="utf-8")
        (kb_dir / "log.md").write_text("# Log\nContent", encoding="utf-8")

        gen = TimelineGenerator(kb_dir)
        gen._load_events()
        assert len(gen.events) == 0

    def test_load_events_extracts_frontmatter(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "test.md").write_text(
            "---\ntitle: My Atom\ntype: method\ncreated_at: 2026-02-10\n---\nBody",
            encoding="utf-8"
        )

        gen = TimelineGenerator(kb_dir)
        gen._load_events()
        assert len(gen.events) == 1
        assert gen.events[0]["title"] == "My Atom"
        assert gen.events[0]["type"] == "method"

    def test_load_events_no_date_skipped(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        # 没有 frontmatter 的文件不应出现在事件中
        # 但如果没有日期字段，会 fallback 到 mtime
        (kb_dir / "nodate.md").write_text(
            "---\ntitle: No Date\ntype: fact\n---\nBody",
            encoding="utf-8"
        )

        gen = TimelineGenerator(kb_dir)
        gen._load_events()
        # mtime 回退会产生日期
        assert len(gen.events) >= 1
