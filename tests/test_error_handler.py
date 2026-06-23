#!/usr/bin/env python3
"""独立测试错误处理功能."""

from typing import Any, Dict, Optional
from enum import Enum


class ErrorCode(Enum):
    UNKNOWN_ERROR = 1000
    INVALID_PARAMETER = 1003
    UNAUTHORIZED = 2000
    PERMISSION_DENIED = 2003
    NOT_FOUND = 3000
    RATE_LIMIT_EXCEEDED = 4000


class APIError(Exception):
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        error_dict = {
            'success': False,
            'error': {
                'code': self.error_code.value,
                'message': self.message,
                'type': self.error_code.name,
            }
        }
        if self.details:
            error_dict['error']['details'] = self.details
        return error_dict


class ValidationError(APIError):
    def __init__(self, message: str, field: Optional[str] = None):
        details = {'field': field} if field else {}
        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_PARAMETER,
            status_code=400,
            details=details
        )


class AuthenticationError(APIError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=401
        )


class NotFoundError(APIError):
    def __init__(self, resource_type: str, resource_id: Optional[str] = None):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            status_code=404,
            details={'resource_type': resource_type, 'resource_id': resource_id}
        )


def test_api_error():
    print("\n=== 测试 API 错误基类 ===")
    error = APIError(
        message="Something went wrong",
        error_code=ErrorCode.UNKNOWN_ERROR,
        status_code=500
    )

    error_dict = error.to_dict()
    assert error_dict['success'] is False
    assert error_dict['error']['code'] == 1000
    assert error_dict['error']['message'] == "Something went wrong"
    print("✅ API 错误基类测试通过")


def test_validation_error():
    print("\n=== 测试验证错误 ===")
    error = ValidationError(
        message="Invalid email format",
        field="email"
    )

    error_dict = error.to_dict()
    assert error.status_code == 400
    assert error_dict['error']['code'] == 1003
    assert error_dict['error']['details']['field'] == "email"
    print("✅ 验证错误测试通过")


def test_authentication_error():
    print("\n=== 测试认证错误 ===")
    error = AuthenticationError()

    error_dict = error.to_dict()
    assert error.status_code == 401
    assert error_dict['error']['code'] == 2000
    print("✅ 认证错误测试通过")


def test_not_found_error():
    print("\n=== 测试资源未找到错误 ===")
    error = NotFoundError("KnowledgeBase", "kb_123")

    error_dict = error.to_dict()
    assert error.status_code == 404
    assert error_dict['error']['code'] == 3000
    assert "KnowledgeBase" in error.message
    assert "kb_123" in error.message
    print(f"✅ 资源未找到错误测试通过: {error.message}")


def test_error_inheritance():
    print("\n=== 测试错误继承 ===")
    error = ValidationError("Test error")

    # 应该是 APIError 的实例
    assert isinstance(error, APIError)
    assert isinstance(error, Exception)
    print("✅ 错误继承测试通过")


def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("错误处理功能测试（独立版本）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        test_api_error()
        test_validation_error()
        test_authentication_error()
        test_not_found_error()
        test_error_inheritance()

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("✅ 所有测试通过！")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())