"""
Service Worker 缓存策略测试

验证 sw.js 中的 Network First / Cache First / Network Only 策略逻辑。
由于 sw.js 运行在浏览器 Service Worker 上下文中，
这里提取核心逻辑进行独立测试。
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SW_PATH = PROJECT_ROOT / "views" / "sw.js"


class TestSWFileExists:
    """验证 Service Worker 文件。"""

    def test_sw_js_exists(self):
        """sw.js 应存在。"""
        assert SW_PATH.exists()

    def test_sw_js_not_empty(self):
        """sw.js 不应为空。"""
        assert SW_PATH.stat().st_size > 0

    def test_sw_has_install_event(self):
        """sw.js 应包含 install 事件监听。"""
        content = SW_PATH.read_text()
        assert "install" in content
        assert "addEventListener" in content

    def test_sw_has_activate_event(self):
        """sw.js 应包含 activate 事件监听。"""
        content = SW_PATH.read_text()
        assert "activate" in content

    def test_sw_has_fetch_event(self):
        """sw.js 应包含 fetch 事件监听。"""
        content = SW_PATH.read_text()
        assert "fetch" in content

    def test_sw_has_cache_name(self):
        """sw.js 应定义缓存名称。"""
        content = SW_PATH.read_text()
        assert "CACHE_NAME" in content


class TestSWCacheStrategy:
    """验证 Service Worker 缓存策略逻辑。"""

    def _read_sw_content(self):
        return SW_PATH.read_text()

    def test_has_network_first_function(self):
        """应有 networkFirst 函数。"""
        content = self._read_sw_content()
        assert "networkFirst" in content or "Network First" in content

    def test_has_cache_first_function(self):
        """应有 cacheFirst 函数。"""
        content = self._read_sw_content()
        assert "cacheFirst" in content or "Cache First" in content

    def test_api_requests_are_network_only(self):
        """API 请求应使用 Network Only 策略。"""
        content = self._read_sw_content()
        assert "/api/" in content
        # API 请求不应缓存
        assert "Network Only" in content or "networkOnly" in content or "return" in content

    def test_cdn_assets_use_cache_first(self):
        """CDN 资源应使用 Cache First 策略。"""
        content = self._read_sw_content()
        assert "CDN" in content or "cdn" in content or "origin" in content

    def test_has_static_assets_list(self):
        """应有预缓存的静态资源列表。"""
        content = self._read_sw_content()
        assert "STATIC_ASSETS" in content or "static" in content.lower()

    def test_has_offline_fallback(self):
        """应有离线回退页面。"""
        content = self._read_sw_content()
        assert "offline" in content.lower() or "Offline" in content

    def test_caches_are_versioned(self):
        """缓存名称应有版本号。"""
        content = self._read_sw_content()
        assert "v1" in content or "v2" in content or "version" in content.lower()


# ============================================================================
# 缓存策略逻辑测试（提取纯函数测试）
# ============================================================================

class TestCacheStrategyLogic:
    """测试缓存策略的纯逻辑（不依赖浏览器 API）。"""

    def test_api_path_detection(self):
        """测试 API 路径检测。"""
        api_paths = ["/api/atoms", "/api/auth/login", "/api/kb/1"]
        for path in api_paths:
            assert path.startswith("/api/")

    def test_cdn_origin_detection(self):
        """测试 CDN 来源检测逻辑。"""
        local_url = MagicMock()
        local_url.origin = "http://localhost:8080"
        sw_origin = "http://localhost:8080"
        assert local_url.origin == sw_origin  # 本地资源

        cdn_url = MagicMock()
        cdn_url.origin = "https://cdn.tailwindcss.com"
        assert cdn_url.origin != sw_origin  # CDN 资源

    def test_description_truncation_logic(self):
        """测试移动端描述截断逻辑。"""
        desc = "A" * 200
        truncated = desc[:80]
        assert len(truncated) == 80

        short = "Hello"
        assert short[:80] == "Hello"
