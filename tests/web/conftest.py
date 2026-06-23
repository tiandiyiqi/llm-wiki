"""
Web 服务器测试共享 fixtures

提供 web_server.py 测试专用的 Mock 对象和 HTTP 请求模拟。
"""

import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_handler():
    """创建一个完整的 WikiHTTPRequestHandler Mock。

    模拟 HTTP 请求处理器的所有核心方法，
    使得可以在不启动真实 HTTP 服务器的情况下测试路由逻辑。
    """
    handler = MagicMock()

    # HTTP 基础属性
    handler.command = "GET"
    handler.path = "/"
    handler.headers = MagicMock()
    handler.headers.get = MagicMock(return_value="")
    handler.client_address = ("127.0.0.1", 12345)

    # 响应方法
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = io.BytesIO()

    # 业务方法
    handler._json_response = MagicMock()
    handler._read_json_body = MagicMock(return_value={})
    handler._authenticate = MagicMock(return_value=True)
    handler._check_permission = MagicMock(return_value=True)
    handler._get_current_username = MagicMock(return_value="testuser")
    handler._get_current_role = MagicMock(return_value="editor")
    handler._is_mobile_request = MagicMock(return_value=False)

    # 存储相关
    handler.storage = None
    handler.kb_dir = Path("/tmp/test_kb")
    handler.kb_views_dir = Path("/tmp/test_kb/views")
    handler.static_dir = Path("/tmp/test_kb/views")

    # 用户状态
    handler._current_user = {"username": "testuser", "role": "editor"}

    # CORS
    handler._send_cors_headers = MagicMock()

    return handler


@pytest.fixture
def mock_handler_factory(mock_handler):
    """创建 Handler Mock 的工厂函数，可自定义属性。"""
    def _create(**overrides):
        h = MagicMock()
        # 复制默认属性
        h.command = mock_handler.command
        h.path = mock_handler.path
        h.headers = mock_handler.headers
        h.send_response = mock_handler.send_response
        h.send_header = mock_handler.send_header
        h.end_headers = mock_handler.end_headers
        h.wfile = io.BytesIO()
        h._json_response = mock_handler._json_response
        h._read_json_body = mock_handler._read_json_body
        h._authenticate = mock_handler._authenticate
        h._check_permission = mock_handler._check_permission
        h._get_current_username = mock_handler._get_current_username
        h._get_current_role = mock_handler._get_current_role
        h._is_mobile_request = mock_handler._is_mobile_request
        h.storage = mock_handler.storage
        h.kb_dir = mock_handler.kb_dir
        h.kb_views_dir = mock_handler.kb_views_dir
        h.static_dir = mock_handler.static_dir
        h._current_user = mock_handler._current_user
        h._send_cors_headers = mock_handler._send_cors_headers
        # 应用自定义覆盖
        for key, value in overrides.items():
            setattr(h, key, value)
        return h
    return _create


@pytest.fixture
def mobile_user_agent():
    """返回常见移动端 User-Agent 字符串列表。"""
    return {
        "iphone_safari": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "android_chrome": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "ipad_safari": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/604.1",
        "desktop_chrome": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
