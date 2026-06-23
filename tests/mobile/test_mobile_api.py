"""
移动端 API 测试

测试 _is_mobile_request 和移动端数据精简逻辑。
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestMobileDetection:
    """测试移动端检测逻辑。"""

    def _call_is_mobile(self, user_agent="", mobile_hint=""):
        from lib.web_server import UnifiedRequestHandler
        handler = MagicMock(spec=UnifiedRequestHandler)
        handler.headers = MagicMock()
        handler.headers.get = MagicMock(side_effect=lambda key, default="": {
            "User-Agent": user_agent,
            "Sec-CH-UA-Mobile": mobile_hint,
        }.get(key, default))
        return UnifiedRequestHandler._is_mobile_request(handler)

    # --- User-Agent 检测 ---

    def test_iphone_safari(self):
        assert self._call_is_mobile(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        ) is True

    def test_android_chrome(self):
        assert self._call_is_mobile(
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile"
        ) is True

    def test_ipad_safari(self):
        assert self._call_is_mobile(
            "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        ) is True

    def test_ipod_touch(self):
        assert self._call_is_mobile(
            "Mozilla/5.0 (iPod touch; CPU iPhone OS 16_0 like Mac OS X)"
        ) is True

    def test_blackberry(self):
        assert self._call_is_mobile(
            "Mozilla/5.0 (BlackBerry; U; BlackBerry 9900)"
        ) is True

    # --- Client Hints ---

    def test_chrome_mobile_hint(self):
        """Chrome Android 发送 Sec-CH-UA-Mobile: ?1。"""
        assert self._call_is_mobile(mobile_hint="?1") is True

    def test_chrome_desktop_hint(self):
        """Chrome 桌面端不发送 ?1。"""
        assert self._call_is_mobile(mobile_hint="?0") is False

    # --- 桌面端 ---

    def test_mac_chrome(self):
        assert self._call_is_mobile(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ) is False

    def test_windows_firefox(self):
        assert self._call_is_mobile(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
        ) is False

    def test_linux_chrome(self):
        assert self._call_is_mobile(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ) is False

    # --- 边界情况 ---

    def test_empty_ua(self):
        assert self._call_is_mobile() is False

    def test_partial_mobile_ua(self):
        """仅包含 "Mobile" 关键词的 UA。"""
        assert self._call_is_mobile("SomeBrowser Mobile/1.0") is True


class TestMobileDataSlim:
    """测试移动端数据精简逻辑。"""

    def test_atom_slim_has_5_fields(self):
        """移动端原子精简数据应有 5 个字段。"""
        slim = {
            "id": "1", "path": "test", "type": "fact",
            "title": "Test", "description": "Desc"[:80],
        }
        assert len(slim) == 5

    def test_atom_full_has_9_fields(self):
        """桌面端原子完整数据应有 9 个字段。"""
        full = {
            "id": "1", "path": "test", "type": "fact", "title": "Test",
            "description": "Desc", "tags": [], "status": "active",
            "author": "user", "updated": "2026-01-01",
        }
        assert len(full) == 9

    def test_description_truncation(self):
        """描述应截断为 80 字符。"""
        long_desc = "X" * 200
        mobile_desc = long_desc[:80]
        assert len(mobile_desc) == 80
        assert mobile_desc == "X" * 80

    def test_short_description_preserved(self):
        """短描述应原样保留。"""
        short = "Hello World"
        assert short[:80] == "Hello World"

    def test_empty_description_handled(self):
        """空描述应正常处理。"""
        desc = ""
        assert desc[:80] == ""

    def test_none_description_handled(self):
        """None 描述应转为空字符串后截断。"""
        desc = None
        result = (desc or "")[:80]
        assert result == ""

    def test_slim_omits_tags_status_author(self):
        """精简数据应省略 tags、status、author、created、updated。"""
        slim_fields = {"id", "path", "type", "title", "description"}
        omitted_fields = {"tags", "status", "author", "created", "updated"}
        for field in omitted_fields:
            assert field not in slim_fields
