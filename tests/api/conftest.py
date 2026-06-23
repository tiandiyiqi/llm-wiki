"""
API 测试共享 fixtures

提供 API 测试专用的 Mock 对象和辅助函数。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_web_server():
    """Mock WikiHTTPRequestHandler 实例。"""
    handler = MagicMock()
    handler.command = "GET"
    handler.path = "/api/atoms"
    handler.headers = MagicMock()
    handler.headers.get = MagicMock(return_value="")
    handler._current_user = {"username": "testuser", "role": "editor"}
    handler._json_response = MagicMock()
    handler._read_json_body = MagicMock(return_value={})
    handler._authenticate = MagicMock(return_value=True)
    handler._check_permission = MagicMock(return_value=True)
    handler._get_current_username = MagicMock(return_value="testuser")
    handler._is_mobile_request = MagicMock(return_value=False)
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = MagicMock()
    handler.wfile.write = MagicMock()
    handler.storage = None
    handler.kb_dir = MagicMock()
    handler.kb_views_dir = MagicMock()
    handler.static_dir = MagicMock()
    return handler


@pytest.fixture
def mock_api_handler(mock_web_server):
    """创建 API 处理器的 Mock 基础设施。"""
    return mock_web_server


@pytest.fixture
def api_request_factory():
    """创建 API 请求模拟对象的工厂。"""
    def _make_request(method="GET", path="/api/atoms", headers=None, body=None):
        handler = MagicMock()
        handler.command = method
        handler.path = path
        handler.headers = MagicMock()
        if headers:
            for key, value in headers.items():
                handler.headers.__getitem__ = MagicMock(
                    side_effect=lambda k, v=headers: v.get(k, "")
                )
        handler._read_json_body = MagicMock(return_value=body or {})
        handler._json_response = MagicMock()
        handler._authenticate = MagicMock(return_value=True)
        handler._current_user = {"username": "testuser", "role": "editor"}
        return handler
    return _make_request
