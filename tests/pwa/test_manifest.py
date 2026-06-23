"""
PWA manifest.json 测试

验证 PWA 清单格式、图标文件、必填字段。
"""

import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VIEWS_DIR = PROJECT_ROOT / "views"


class TestManifestFormat:
    """验证 manifest.json 格式。"""

    @pytest.fixture
    def manifest(self):
        manifest_path = VIEWS_DIR / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("manifest.json not found")
        return json.loads(manifest_path.read_text())

    def test_manifest_is_valid_json(self):
        """manifest.json 应为有效 JSON。"""
        manifest_path = VIEWS_DIR / "manifest.json"
        data = json.loads(manifest_path.read_text())
        assert isinstance(data, dict)

    def test_required_fields(self, manifest):
        """PWA manifest 必须包含 name、short_name、start_url、display。"""
        assert "name" in manifest
        assert "short_name" in manifest
        assert "start_url" in manifest
        assert "display" in manifest

    def test_display_is_standalone(self, manifest):
        """display 应为 standalone。"""
        assert manifest["display"] == "standalone"

    def test_has_icons(self, manifest):
        """manifest 必须包含 icons 数组。"""
        assert "icons" in manifest
        assert isinstance(manifest["icons"], list)
        assert len(manifest["icons"]) > 0

    def test_icons_have_required_fields(self, manifest):
        """每个 icon 必须有 src、sizes、type。"""
        for icon in manifest["icons"]:
            assert "src" in icon
            assert "sizes" in icon
            assert "type" in icon

    def test_has_192_and_512_icons(self, manifest):
        """必须有 192x192 和 512x512 图标。"""
        sizes = {icon["sizes"] for icon in manifest["icons"]}
        assert "192x192" in sizes
        assert "512x512" in sizes

    def test_has_maskable_icons(self, manifest):
        """应有 maskable 图标。"""
        maskable = [i for i in manifest["icons"] if i.get("purpose") == "maskable"]
        assert len(maskable) >= 1

    def test_has_theme_color(self, manifest):
        """应有 theme_color。"""
        assert "theme_color" in manifest
        assert manifest["theme_color"].startswith("#")


class TestManifestIcons:
    """验证 PWA 图标文件。"""

    def test_icon_192_exists(self):
        """192px 图标文件应存在。"""
        assert (VIEWS_DIR / "icons" / "icon-192.png").exists()

    def test_icon_512_exists(self):
        """512px 图标文件应存在。"""
        assert (VIEWS_DIR / "icons" / "icon-512.png").exists()

    def test_maskable_192_exists(self):
        """192px maskable 图标应存在。"""
        assert (VIEWS_DIR / "icons" / "icon-maskable-192.png").exists()

    def test_maskable_512_exists(self):
        """512px maskable 图标应存在。"""
        assert (VIEWS_DIR / "icons" / "icon-maskable-512.png").exists()

    def test_icon_files_are_not_empty(self):
        """图标文件不应为空。"""
        icons_dir = VIEWS_DIR / "icons"
        for icon_file in icons_dir.glob("*.png"):
            assert icon_file.stat().st_size > 0, f"{icon_file.name} is empty"
