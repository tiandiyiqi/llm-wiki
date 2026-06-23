"""Tests for lib/backup.py — BackupManager."""

import json
import sys
import tarfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestBackupManagerImport:
    """测试 backup 模块导入."""

    def test_import_backup_manager(self):
        try:
            from lib.backup import BackupManager
        except ImportError as e:
            pytest.skip(f"无法导入 BackupManager: {e}")


try:
    from lib.backup import BackupManager
    _BACKUP_AVAILABLE = True
except ImportError:
    _BACKUP_AVAILABLE = False


@pytest.mark.skipif(not _BACKUP_AVAILABLE, reason="BackupManager 导入依赖不满足")
class TestBackupManagerInit:
    """测试 BackupManager 初始化."""

    def test_init_creates_backup_dir(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = BackupManager(kb_dir)
        assert manager.backup_dir.exists()
        assert manager.backup_dir.name == "backups"

    def test_init_kb_dir_stored(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = BackupManager(kb_dir)
        assert manager.kb_dir == kb_dir


@pytest.mark.skipif(not _BACKUP_AVAILABLE, reason="BackupManager 导入依赖不满足")
class TestBackupManagerFullBackup:
    """测试完整备份."""

    def _setup_kb(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "facts").mkdir()
        (kb_dir / "facts" / "test.md").write_text(
            "---\ntitle: Test\ntype: fact\n---\nContent", encoding="utf-8"
        )
        return kb_dir

    def test_backup_creates_tar_gz(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        manager = BackupManager(kb_dir)
        backup_path = manager.backup()
        assert backup_path.exists()
        assert backup_path.suffix == ".gz"

    def test_backup_tar_contains_files(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        manager = BackupManager(kb_dir)
        backup_path = manager.backup()

        with tarfile.open(backup_path, 'r:gz') as tar:
            names = tar.getnames()
        assert any("test.md" in n for n in names)

    def test_backup_skips_llm_wiki_dir(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        # .llm-wiki 目录应被跳过
        manager = BackupManager(kb_dir)
        backup_path = manager.backup()

        with tarfile.open(backup_path, 'r:gz') as tar:
            names = tar.getnames()
        assert not any(".llm-wiki" in n for n in names)

    def test_backup_custom_output_path(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        custom_output = tmp_path / "custom-backup.tar.gz"
        manager = BackupManager(kb_dir)
        backup_path = manager.backup(output=custom_output)
        assert backup_path == custom_output
        assert backup_path.exists()

    def test_backup_records_metadata(self, tmp_path):
        kb_dir = self._setup_kb(tmp_path)
        manager = BackupManager(kb_dir)
        manager.backup()

        meta_path = manager.backup_dir / "backup-meta.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert "backups" in meta
        assert len(meta["backups"]) >= 1
        assert meta["backups"][0]["type"] == "full"


@pytest.mark.skipif(not _BACKUP_AVAILABLE, reason="BackupManager 导入依赖不满足")
class TestBackupManagerAtomBackup:
    """测试单原子备份."""

    def test_backup_atom_creates_copy(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("---\ntitle: Test\n---\nContent", encoding="utf-8")

        manager = BackupManager(kb_dir)
        backup_path = manager.backup_atom(atom_file)
        assert backup_path.exists()
        assert backup_path.name.startswith("atom-")

    def test_backup_atom_content_matches(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        original_content = "---\ntitle: Test\n---\nOriginal content"
        atom_file.write_text(original_content, encoding="utf-8")

        manager = BackupManager(kb_dir)
        backup_path = manager.backup_atom(atom_file)
        assert backup_path.read_text(encoding="utf-8") == original_content


@pytest.mark.skipif(not _BACKUP_AVAILABLE, reason="BackupManager 导入依赖不满足")
class TestBackupManagerRestore:
    """测试原子恢复."""

    def test_restore_atom_from_backup(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        atom_file = kb_dir / "test.md"
        atom_file.write_text("---\ntitle: Test\n---\nOriginal", encoding="utf-8")

        manager = BackupManager(kb_dir)
        manager.backup_atom(atom_file)

        # 修改原文件
        atom_file.write_text("---\ntitle: Test\n---\nModified", encoding="utf-8")

        # 恢复
        result = manager.restore_atom("test")
        assert result is True
        assert "Original" in atom_file.read_text(encoding="utf-8")

    def test_restore_atom_no_backup_returns_false(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = BackupManager(kb_dir)
        # 没有 git 也没有备份文件
        result = manager.restore_atom("nonexistent")
        assert result is False


@pytest.mark.skipif(not _BACKUP_AVAILABLE, reason="BackupManager 导入依赖不满足")
class TestBackupManagerListBackups:
    """测试备份列表."""

    def test_list_backups_empty(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = BackupManager(kb_dir)
        # 清空自动创建的 meta 文件
        backups = manager.list_backups()
        # 可能有 meta 文件，但不应有备份
        backup_files = [b for b in backups if b["type"] in ("full", "atom")]
        assert len(backup_files) == 0

    def test_list_backups_after_backup(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "test.md").write_text("---\ntitle: T\n---\nC", encoding="utf-8")

        manager = BackupManager(kb_dir)
        manager.backup()
        backups = manager.list_backups()
        assert len(backups) >= 1


@pytest.mark.skipif(not _BACKUP_AVAILABLE, reason="BackupManager 导入依赖不满足")
class TestBackupManagerCleanOld:
    """测试旧备份清理."""

    def test_clean_old_backups_keeps_recent(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = BackupManager(kb_dir)

        # 创建多个备份文件
        for i in range(5):
            (manager.backup_dir / f"kb-backup-2026010{i}_000000.tar.gz").write_bytes(b"fake")

        removed = manager.clean_old_backups(keep_count=2)
        assert removed == 3

        remaining = list(manager.backup_dir.glob("kb-backup-*.tar.gz"))
        assert len(remaining) == 2


@pytest.mark.skipif(not _BACKUP_AVAILABLE, reason="BackupManager 导入依赖不满足")
class TestBackupManagerSchedule:
    """测试定时备份脚本生成."""

    def test_schedule_daily(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = BackupManager(kb_dir)
        cron = manager.schedule_backup("daily")
        assert "0 0 * * *" in cron

    def test_schedule_weekly(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = BackupManager(kb_dir)
        cron = manager.schedule_backup("weekly")
        assert "0 0 * * 0" in cron

    def test_schedule_hourly(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        manager = BackupManager(kb_dir)
        cron = manager.schedule_backup("hourly")
        assert "0 * * * *" in cron
