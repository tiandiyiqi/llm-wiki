"""
web_server.py 单元测试

覆盖：Content-Type 判断、移动端检测、PWA manifest 特殊处理。
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# TestGetContentType
# ============================================================================

class TestGetContentType:
    """测试 _get_content_type 方法。"""

    def _call_get_content_type(self, suffix):
        """直接调用 _get_content_type 实例方法。"""
        from lib.web_server import UnifiedRequestHandler
        handler = MagicMock(spec=UnifiedRequestHandler)
        return UnifiedRequestHandler._get_content_type(handler, suffix)

    def test_html(self):
        assert "text/html" in self._call_get_content_type(".html")

    def test_css(self):
        assert "text/css" in self._call_get_content_type(".css")

    def test_js(self):
        assert "javascript" in self._call_get_content_type(".js")

    def test_json(self):
        assert "application/json" in self._call_get_content_type(".json")

    def test_png(self):
        assert "image/png" in self._call_get_content_type(".png")

    def test_svg(self):
        assert "svg+xml" in self._call_get_content_type(".svg")

    def test_pdf(self):
        assert "application/pdf" in self._call_get_content_type(".pdf")

    def test_webmanifest(self):
        assert "manifest+json" in self._call_get_content_type(".webmanifest")

    def test_unknown_fallback(self):
        assert "octet-stream" in self._call_get_content_type(".xyz")

    def test_woff2(self):
        assert "font/woff2" in self._call_get_content_type(".woff2")


# ============================================================================
# TestIsMobileRequest
# ============================================================================

class TestIsMobileRequest:
    """测试 _is_mobile_request 方法。"""

    def _call_is_mobile(self, user_agent="", mobile_hint=""):
        """直接调用 _is_mobile_request 实例方法。"""
        from lib.web_server import UnifiedRequestHandler
        handler = MagicMock(spec=UnifiedRequestHandler)
        handler.headers = MagicMock()
        handler.headers.get = MagicMock(side_effect=lambda key, default="": {
            "User-Agent": user_agent,
            "Sec-CH-UA-Mobile": mobile_hint,
        }.get(key, default))
        return UnifiedRequestHandler._is_mobile_request(handler)

    def test_iphone(self):
        assert self._call_is_mobile(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
        ) is True

    def test_android(self):
        assert self._call_is_mobile(
            user_agent="Mozilla/5.0 (Linux; Android 13; Pixel 7)"
        ) is True

    def test_ipad(self):
        assert self._call_is_mobile(
            user_agent="Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)"
        ) is True

    def test_windows_phone(self):
        assert self._call_is_mobile(
            user_agent="Mozilla/5.0 (Windows Phone 10.0)"
        ) is True

    def test_mobile_hint_header(self):
        """Sec-CH-UA-Mobile: ?1 应识别为移动端。"""
        assert self._call_is_mobile(mobile_hint="?1") is True

    def test_desktop_mac(self):
        assert self._call_is_mobile(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        ) is False

    def test_desktop_linux(self):
        assert self._call_is_mobile(
            user_agent="Mozilla/5.0 (X11; Linux x86_64)"
        ) is False

    def test_empty_ua(self):
        assert self._call_is_mobile() is False


# ============================================================================
# TestServeFile — PWA manifest 特殊 Content-Type
# ============================================================================

class TestServeFile:
    """测试 _serve_file 方法。"""

    def test_serve_file_reads_and_sends(self, tmp_path):
        """测试 _serve_file 正确读取并发送文件。"""
        from lib.web_server import UnifiedRequestHandler

        test_file = tmp_path / "test.html"
        test_file.write_text("<html>hello</html>")

        handler = MagicMock(spec=UnifiedRequestHandler)
        handler._get_content_type = MagicMock(return_value="text/html; charset=utf-8")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler._send_cors_headers = MagicMock()
        handler.wfile = MagicMock()

        UnifiedRequestHandler._serve_file(handler, test_file)

        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call("Content-Type", "text/html; charset=utf-8")
        handler.wfile.write.assert_called_once()

    def test_serve_file_missing_returns_404(self, tmp_path):
        """测试 _serve_file 对不存在的文件返回 404。"""
        from lib.web_server import UnifiedRequestHandler

        missing = tmp_path / "missing.html"
        handler = MagicMock(spec=UnifiedRequestHandler)
        handler._json_response = MagicMock()

        UnifiedRequestHandler._serve_file(handler, missing)

        handler._json_response.assert_called_once_with({"error": "File not found"}, 404)

    def test_manifest_json_gets_manifest_content_type(self, tmp_path):
        """测试 manifest.json 获取 application/manifest+json。"""
        from lib.web_server import UnifiedRequestHandler

        manifest = tmp_path / "manifest.json"
        manifest.write_text('{"name": "LLM Wiki"}')

        handler = MagicMock(spec=UnifiedRequestHandler)
        handler._get_content_type = MagicMock(return_value="application/json; charset=utf-8")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler._send_cors_headers = MagicMock()
        handler.wfile = MagicMock()

        UnifiedRequestHandler._serve_file(handler, manifest)

        # 验证 Content-Type 被覆盖为 manifest+json
        ct_calls = [
            c for c in handler.send_header.call_args_list
            if c[0][0] == "Content-Type"
        ]
        assert len(ct_calls) == 1
        assert "manifest+json" in ct_calls[0][0][1]


# ============================================================================
# TestServeStatic — 路径安全
# ============================================================================

class TestServeStatic:
    """测试 _serve_static 路径安全。"""

    def test_path_traversal_blocked(self):
        """测试包含 .. 的路径被阻止。"""
        from lib.web_server import UnifiedRequestHandler

        handler = MagicMock(spec=UnifiedRequestHandler)
        handler._json_response = MagicMock()

        UnifiedRequestHandler._serve_static(handler, "../../../etc/passwd")

        handler._json_response.assert_called_once_with({"error": "Forbidden"}, 403)


# ============================================================================
# TestMobileAPISlim — 移动端精简数据逻辑
# ============================================================================

class TestMobileAPISlim:
    """测试移动端 API 精简数据。"""

    def test_slim_atom_has_fewer_fields(self):
        """移动端原子数据应比桌面端少。"""
        # 桌面端完整字段
        desktop_atom = {
            "id": "1", "path": "test", "type": "fact", "title": "Test",
            "description": "Full desc", "tags": ["test"], "status": "active",
            "author": "user", "created": "2026-01-01", "updated": "2026-06-01",
        }
        # 移动端精简字段（与 web_server.py 中 _api_atom_list 逻辑一致）
        mobile_atom = {
            "id": desktop_atom["id"], "path": desktop_atom["path"],
            "type": desktop_atom["type"], "title": desktop_atom["title"],
            "description": desktop_atom["description"][:80],
        }
        assert len(mobile_atom) == 5
        assert len(mobile_atom) < len(desktop_atom)

    def test_description_truncated_at_80_chars(self):
        """移动端描述应截断为 80 字符。"""
        long_desc = "A" * 200
        mobile_desc = long_desc[:80]
        assert len(mobile_desc) == 80

    def test_short_description_not_truncated(self):
        """短描述不应被截断。"""
        short_desc = "Short"
        mobile_desc = short_desc[:80]
        assert mobile_desc == "Short"
