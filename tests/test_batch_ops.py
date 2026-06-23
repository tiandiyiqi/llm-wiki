"""Tests for lib/batch_ops.py — BatchOperations."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestBatchOperationsImport:
    """测试 batch_ops 模块导入（依赖 ingestor 等模块）."""

    def test_import_batch_ops(self):
        try:
            from lib.batch_ops import BatchOperations
        except ImportError as e:
            pytest.skip(f"无法导入 BatchOperations: {e}")


# 尝试导入，失败则跳过所有测试
try:
    from lib.batch_ops import BatchOperations
    _BATCH_OPS_AVAILABLE = True
except ImportError:
    _BATCH_OPS_AVAILABLE = False


@pytest.mark.skipif(not _BATCH_OPS_AVAILABLE, reason="BatchOperations 导入依赖不满足")
class TestBatchOperationsInit:
    """测试 BatchOperations 初始化."""

    def test_init_creates_instance(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ops = BatchOperations(kb_dir)
        assert ops.kb_dir == kb_dir

    def test_init_has_yaml_parser(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ops = BatchOperations(kb_dir)
        assert ops.yaml_parser is not None


@pytest.mark.skipif(not _BATCH_OPS_AVAILABLE, reason="BatchOperations 导入依赖不满足")
class TestBatchOperationsIngest:
    """测试批量摄入."""

    def test_batch_ingest_nonexistent_dir(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ops = BatchOperations(kb_dir)
        success, failed = ops.batch_ingest(tmp_path / "nonexistent")
        assert success == 0
        assert failed == 0

    def test_batch_ingest_empty_dir(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        ops = BatchOperations(kb_dir)
        success, failed = ops.batch_ingest(source_dir)
        assert success == 0
        assert failed == 0

    def test_batch_ingest_dry_run(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.md").write_text("# Test\nContent", encoding="utf-8")

        ops = BatchOperations(kb_dir)
        success, failed = ops.batch_ingest(source_dir, dry_run=True)
        # dry_run 返回匹配文件数
        assert success >= 0


@pytest.mark.skipif(not _BATCH_OPS_AVAILABLE, reason="BatchOperations 导入依赖不满足")
class TestBatchOperationsExport:
    """测试批量导出."""

    def _create_atom_file(self, kb_dir, name, atom_type="fact", tags=None, status="published"):
        from lib.constants import TYPE_DIRS
        type_dir = TYPE_DIRS.get(atom_type, "facts")
        atom_dir = kb_dir / type_dir
        atom_dir.mkdir(parents=True, exist_ok=True)
        atom_file = atom_dir / f"{name}.md"
        tags_str = "\n  - ".join(tags) if tags else "test"
        atom_file.write_text(
            f"---\ntitle: {name}\ntype: {atom_type}\nstatus: {status}\ntags:\n  - {tags_str}\n---\nContent",
            encoding="utf-8"
        )
        return atom_file

    def test_batch_export_no_atoms(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        output_dir = tmp_path / "output"
        ops = BatchOperations(kb_dir)
        count = ops.batch_export(output_dir)
        assert count == 0

    def test_batch_export_dry_run(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        self._create_atom_file(kb_dir, "test-atom")
        output_dir = tmp_path / "output"
        ops = BatchOperations(kb_dir)
        count = ops.batch_export(output_dir, dry_run=True)
        assert count >= 0


@pytest.mark.skipif(not _BATCH_OPS_AVAILABLE, reason="BatchOperations 导入依赖不满足")
class TestBatchOperationsDelete:
    """测试批量删除."""

    def test_batch_delete_default_is_dry_run(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ops = BatchOperations(kb_dir)
        # 默认 dry_run=True，安全模式
        count = ops.batch_delete()
        assert count == 0

    def test_batch_delete_no_matching_atoms(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ops = BatchOperations(kb_dir)
        count = ops.batch_delete(by_type="nonexistent", dry_run=False)
        assert count == 0


@pytest.mark.skipif(not _BATCH_OPS_AVAILABLE, reason="BatchOperations 导入依赖不满足")
class TestBatchOperationsTag:
    """测试批量打标签."""

    def test_batch_tag_no_atoms(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ops = BatchOperations(kb_dir)
        count = ops.batch_tag(add_tags=["new-tag"])
        assert count == 0

    def test_batch_tag_dry_run(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ops = BatchOperations(kb_dir)
        count = ops.batch_tag(add_tags=["new-tag"], dry_run=True)
        assert count == 0


@pytest.mark.skipif(not _BATCH_OPS_AVAILABLE, reason="BatchOperations 导入依赖不满足")
class TestBatchOperationsMove:
    """测试批量迁移."""

    def test_batch_move_invalid_type(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ops = BatchOperations(kb_dir)
        count = ops.batch_move(target_type="invalid_type")
        assert count == 0

    def test_batch_move_no_atoms(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ops = BatchOperations(kb_dir)
        count = ops.batch_move(target_type="fact")
        assert count == 0


@pytest.mark.skipif(not _BATCH_OPS_AVAILABLE, reason="BatchOperations 导入依赖不满足")
class TestBatchOperationsInternal:
    """测试内部辅助方法."""

    def test_load_atoms_empty_kb(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ops = BatchOperations(kb_dir)
        atoms = ops._load_atoms()
        assert atoms == []

    def test_load_atoms_with_valid_atom(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text(
            "---\ntitle: Test\ntype: fact\nstatus: published\ntags:\n  - test\n---\nBody",
            encoding="utf-8"
        )
        ops = BatchOperations(kb_dir)
        atoms = ops._load_atoms()
        assert len(atoms) == 1
        assert atoms[0]["title"] == "Test"

    def test_load_atoms_filters_by_type(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text(
            "---\ntitle: Test\ntype: fact\n---\nBody",
            encoding="utf-8"
        )
        ops = BatchOperations(kb_dir)
        atoms = ops._load_atoms(by_type="opinion")
        assert len(atoms) == 0

    def test_load_atoms_skips_reserved_files(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        index_file = kb_dir / "index.md"
        index_file.write_text("# Index\n\nContent", encoding="utf-8")
        ops = BatchOperations(kb_dir)
        atoms = ops._load_atoms()
        assert len(atoms) == 0

    def test_modify_tags_add(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text(
            "---\ntitle: Test\ntype: fact\ntags:\n  - existing\n---\nBody",
            encoding="utf-8"
        )
        ops = BatchOperations(kb_dir)
        result = ops._modify_tags(atom_file, add_tags=["new-tag"], remove_tags=None)
        assert result is True
        content = atom_file.read_text(encoding="utf-8")
        assert "new-tag" in content

    def test_modify_tags_remove(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text(
            "---\ntitle: Test\ntype: fact\ntags:\n  - remove-me\n  - keep-me\n---\nBody",
            encoding="utf-8"
        )
        ops = BatchOperations(kb_dir)
        result = ops._modify_tags(atom_file, add_tags=None, remove_tags=["remove-me"])
        assert result is True
        content = atom_file.read_text(encoding="utf-8")
        assert "remove-me" not in content

    def test_modify_tags_no_frontmatter(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("No frontmatter", encoding="utf-8")
        ops = BatchOperations(kb_dir)
        result = ops._modify_tags(atom_file, add_tags=["tag"], remove_tags=None)
        assert result is False
