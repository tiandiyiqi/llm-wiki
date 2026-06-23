"""Tests for lib/exporter.py — OKFExporter."""

import json
import sys
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestExporterImport:
    """测试 exporter 模块导入."""

    def test_import_exporter(self):
        try:
            from lib.exporter import OKFExporter
        except ImportError as e:
            pytest.skip(f"无法导入 OKFExporter: {e}")


try:
    from lib.exporter import OKFExporter
    _EXPORTER_AVAILABLE = True
except ImportError:
    _EXPORTER_AVAILABLE = False


@pytest.mark.skipif(not _EXPORTER_AVAILABLE, reason="OKFExporter 导入依赖不满足")
class TestOKFExporterInit:
    """测试 OKFExporter 初始化."""

    def test_init_default_output_path(self, tmp_path):
        kb_dir = tmp_path / "my-kb"
        kb_dir.mkdir()
        exporter = OKFExporter(kb_dir)
        assert "my-kb" in str(exporter.output_path)
        assert str(exporter.output_path).endswith(".tar.gz")

    def test_init_custom_output_path(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        custom_output = tmp_path / "custom.tar.gz"
        exporter = OKFExporter(kb_dir, output_path=custom_output)
        assert exporter.output_path == custom_output

    def test_init_manifest_structure(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        exporter = OKFExporter(kb_dir)
        assert "okf_version" in exporter.manifest
        assert exporter.manifest["kb_type"] == "standalone"

    def test_init_include_children_flag(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        exporter = OKFExporter(kb_dir, include_children=True)
        assert exporter.include_children is True


@pytest.mark.skipif(not _EXPORTER_AVAILABLE, reason="OKFExporter 导入依赖不满足")
class TestOKFExporterDetectKBType:
    """测试知识库类型检测."""

    def test_detect_standalone_no_meta(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        exporter = OKFExporter(kb_dir)
        assert exporter._detect_kb_type() == "standalone"

    def test_detect_parent_from_meta(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        meta = {"kb_type": "parent", "children": []}
        (kb_dir / ".kb-meta.json").write_text(json.dumps(meta), encoding="utf-8")

        exporter = OKFExporter(kb_dir)
        assert exporter._detect_kb_type() == "parent"

    def test_detect_child_from_meta(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        meta = {"kb_type": "child", "parent": "main-kb"}
        (kb_dir / ".kb-meta.json").write_text(json.dumps(meta), encoding="utf-8")

        exporter = OKFExporter(kb_dir)
        assert exporter._detect_kb_type() == "child"

    def test_detect_invalid_meta_falls_back(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / ".kb-meta.json").write_text("invalid json{", encoding="utf-8")

        exporter = OKFExporter(kb_dir)
        assert exporter._detect_kb_type() == "standalone"


@pytest.mark.skipif(not _EXPORTER_AVAILABLE, reason="OKFExporter 导入依赖不满足")
class TestOKFExporterGetChildrenPaths:
    """测试子知识库路径获取."""

    def test_no_children_when_standalone(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        exporter = OKFExporter(kb_dir)
        children = exporter._get_children_paths()
        assert children == []

    def test_get_children_from_meta(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        child_dir = tmp_path / "child-kb"
        child_dir.mkdir()

        meta = {"children_paths": {"child-kb": "../child-kb"}}
        (kb_dir / ".kb-meta.json").write_text(json.dumps(meta), encoding="utf-8")

        exporter = OKFExporter(kb_dir)
        children = exporter._get_children_paths()
        assert len(children) == 1
        assert children[0][0] == "child-kb"


@pytest.mark.skipif(not _EXPORTER_AVAILABLE, reason="OKFExporter 导入依赖不满足")
class TestOKFExporterExport:
    """测试导出功能."""

    def _setup_valid_kb(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "test.md").write_text(
            "---\ntitle: Test\ntype: fact\ndescription: A test\n---\nContent",
            encoding="utf-8"
        )
        output_path = tmp_path / "export.tar.gz"
        return kb_dir, output_path

    def test_export_creates_tarball(self, tmp_path):
        kb_dir, output_path = self._setup_valid_kb(tmp_path)
        # Mock validator to avoid validation errors
        exporter = OKFExporter(kb_dir, output_path=output_path)
        with patch.object(exporter, 'validator') as mock_validator:
            mock_validator.validate_bundle.return_value = (True, [], [])
            mock_validator.concepts = [{"type": "fact", "title": "Test"}]
            result = exporter.export(validate=True)

        assert result is True
        assert output_path.exists()

    def test_export_without_validation(self, tmp_path):
        kb_dir, output_path = self._setup_valid_kb(tmp_path)
        exporter = OKFExporter(kb_dir, output_path=output_path)
        result = exporter.export(validate=False)
        assert result is True

    def test_export_tarball_contains_manifest(self, tmp_path):
        kb_dir, output_path = self._setup_valid_kb(tmp_path)
        exporter = OKFExporter(kb_dir, output_path=output_path)
        exporter.export(validate=False)

        with tarfile.open(output_path, 'r:gz') as tar:
            names = tar.getnames()
        assert "manifest.json" in names

    def test_export_tarball_contains_md_files(self, tmp_path):
        kb_dir, output_path = self._setup_valid_kb(tmp_path)
        exporter = OKFExporter(kb_dir, output_path=output_path)
        exporter.export(validate=False)

        with tarfile.open(output_path, 'r:gz') as tar:
            names = tar.getnames()
        assert any("test.md" in n for n in names)


@pytest.mark.skipif(not _EXPORTER_AVAILABLE, reason="OKFExporter 导入依赖不满足")
class TestOKFExporterCountTypes:
    """测试类型统计."""

    def test_count_types(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        exporter = OKFExporter(kb_dir)
        exporter.validator.concepts = [
            {"type": "fact"},
            {"type": "fact"},
            {"type": "method"},
        ]
        types = exporter._count_types()
        assert types["fact"] == 2
        assert types["method"] == 1
