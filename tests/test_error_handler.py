"""错误处理器测试."""

import pytest
from lib.api.error_handler import (
    ErrorCode,
    safe_error_response,
    create_error_response,
    handle_validation_error,
    handle_not_found_error,
    handle_permission_denied,
    handle_rate_limit_exceeded
)


class TestErrorCode:
    """测试错误代码枚举."""

    def test_error_codes_exist(self):
        """测试所有错误代码存在."""
        assert ErrorCode.INTERNAL_ERROR.value == "internal_error"
        assert ErrorCode.NOT_FOUND.value == "not_found"
        assert ErrorCode.PERMISSION_DENIED.value == "permission_denied"
        assert ErrorCode.INVALID_INPUT.value == "invalid_input"
        assert ErrorCode.UNAUTHORIZED.value == "unauthorized"
        assert ErrorCode.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"
        assert ErrorCode.SERVICE_UNAVAILABLE.value == "service_unavailable"


class TestSafeErrorResponse:
    """测试安全错误响应."""

    def test_basic_error_response(self):
        """测试基本错误响应."""
        error = Exception("Test error")
        response = safe_error_response(error)
        
        assert response['success'] is False
        assert response['error'] == "Internal error"
        assert response['code'] == 500
        assert 'error_id' in response
        assert len(response['error_id']) == 36  # UUID format

    def test_custom_message(self):
        """测试自定义错误消息."""
        error = ValueError("Invalid value")
        response = safe_error_response(error, "Custom error message")
        
        assert response['error'] == "Custom error message"

    def test_error_code_included(self):
        """测试错误代码包含在响应中."""
        error = Exception("Test error")
        response = safe_error_response(
            error,
            error_code=ErrorCode.NOT_FOUND,
            status_code=404
        )
        
        assert response['code'] == 404
        assert response['error_code'] == "not_found"


class TestCreateErrorResponse:
    """测试创建错误响应."""

    def test_simple_response(self):
        """测试简单响应."""
        response = create_error_response("Bad request", 400)
        
        assert response['success'] is False
        assert response['error'] == "Bad request"
        assert response['code'] == 400

    def test_response_with_details(self):
        """测试带详情的响应."""
        details = {'field': 'name', 'reason': 'too long'}
        response = create_error_response(
            "Validation failed",
            400,
            ErrorCode.INVALID_INPUT,
            details
        )
        
        assert response['error_code'] == "invalid_input"
        assert response['details'] == details


class TestHandleNotFoundError:
    """测试资源未找到处理."""

    def test_not_found_response(self):
        """测试未找到响应."""
        response = handle_not_found_error('knowledge_base', 'kb-123')
        
        assert response['success'] is False
        assert response['code'] == 404
        assert 'not found' in response['error'].lower()
        assert response['resource_type'] == 'knowledge_base'
        assert response['resource_id'] == 'kb-123'


class TestHandlePermissionDenied:
    """测试权限拒绝处理."""

    def test_permission_denied_response(self):
        """测试权限拒绝响应."""
        response = handle_permission_denied('delete', 'knowledge_base', 'kb-456')
        
        assert response['success'] is False
        assert response['code'] == 403
        assert 'Permission denied' in response['error']
        assert response['action'] == 'delete'
        assert response['resource_type'] == 'knowledge_base'

    def test_permission_denied_simple(self):
        """测试简单权限拒绝响应."""
        response = handle_permission_denied('admin_access')
        
        assert response['code'] == 403
        assert 'admin_access' in response['error']


class TestHandleRateLimitExceeded:
    """测试速率限制处理."""

    def test_rate_limit_response(self):
        """测试速率限制响应."""
        response = handle_rate_limit_exceeded(60, 100, "minute")
        
        assert response['success'] is False
        assert response['code'] == 429
        assert response['retry_after'] == 60
        assert response['limit'] == 100
        assert response['window'] == "minute"
        assert 'Rate limit exceeded' in response['error']
