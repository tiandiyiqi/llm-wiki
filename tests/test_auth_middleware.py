"""认证中间件测试."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from lib.auth.auth_middleware import require_auth, require_permission, public_endpoint


class TestRequireAuth:
    """测试 require_auth 装饰器."""

    def test_missing_auth_header(self):
        """测试缺少认证头返回 401."""
        # 创建模拟对象
        mock_func = Mock(return_value={'success': True})
        mock_self = Mock()
        mock_self.headers = {}
        mock_self._json_response = Mock()
        mock_self._get_auth_manager = Mock(return_value=Mock(
            is_enabled=Mock(return_value=True),
            validate_token=Mock(return_value=None)
        ))

        # 应用装饰器
        decorated = require_auth(mock_func)
        result = decorated(mock_self)

        # 验证返回 401
        mock_self._json_response.assert_called_once()
        call_args = mock_self._json_response.call_args
        assert call_args[0][0]['code'] == 401
        # _json_response 的第二个参数是状态码
        if len(call_args) > 1 and len(call_args[1]) > 0:
            assert call_args[1][0] == 401 or call_args[1] == ()
        assert result is None

    def test_invalid_token(self):
        """测试无效 Token 返回 401."""
        mock_func = Mock(return_value={'success': True})
        mock_self = Mock()
        mock_self.headers = {'Authorization': 'Bearer invalid_token'}
        mock_self._json_response = Mock()

        # 模拟无效 Token
        auth_manager = Mock()
        auth_manager.is_enabled = Mock(return_value=True)
        auth_manager.validate_token = Mock(return_value=None)
        mock_self._get_auth_manager = Mock(return_value=auth_manager)

        decorated = require_auth(mock_func)
        result = decorated(mock_self)

        # 验证返回 401
        mock_self._json_response.assert_called_once()
        call_args = mock_self._json_response.call_args
        assert call_args[0][0]['code'] == 401
        assert result is None

    def test_valid_auth(self):
        """测试有效认证返回 200."""
        mock_func = Mock(return_value={'success': True, 'data': 'test'})
        mock_self = Mock()
        mock_self.headers = {'Authorization': 'Bearer valid_token'}
        mock_self.current_user = None
        mock_self.current_role = None

        # 模拟有效 Token
        auth_manager = Mock()
        auth_manager.is_enabled = Mock(return_value=True)
        auth_manager.validate_token = Mock(return_value='admin')
        auth_manager.config = {
            'tokens': {
                'valid_token': {'username': 'test_user'}
            }
        }
        mock_self._get_auth_manager = Mock(return_value=auth_manager)

        decorated = require_auth(mock_func)
        result = decorated(mock_self)

        # 验证成功执行
        assert result == {'success': True, 'data': 'test'}
        assert mock_self.current_user == 'test_user'
        assert mock_self.current_role == 'admin'

    def test_public_endpoint_attribute(self):
        """测试公开端点标记."""
        @public_endpoint
        def public_func(self):
            return {'success': True}

        assert hasattr(public_func, '_public_endpoint')
        assert public_func._public_endpoint is True


class TestRequirePermission:
    """测试 require_permission 装饰器."""

    def test_permission_denied(self):
        """测试权限不足返回 403."""
        mock_func = Mock(return_value={'success': True})
        mock_self = Mock()
        mock_self.current_user = 'test_user'
        mock_self.current_role = 'reader'
        mock_self._json_response = Mock()

        # 模拟权限检查失败
        auth_manager = Mock()
        auth_manager.check_permission = Mock(return_value=False)
        mock_self._get_auth_manager = Mock(return_value=auth_manager)

        decorated = require_permission('kb:delete')(mock_func)
        result = decorated(mock_self)

        # 验证返回 403
        mock_self._json_response.assert_called_once()
        call_args = mock_self._json_response.call_args
        assert call_args[0][0]['code'] == 403
        assert result is None

    def test_permission_granted(self):
        """测试权限充足返回 200."""
        mock_func = Mock(return_value={'success': True, 'data': 'deleted'})
        mock_self = Mock()
        mock_self.current_user = 'admin_user'
        mock_self.current_role = 'admin'
        mock_self._json_response = Mock()

        # 模拟权限检查成功
        auth_manager = Mock()
        auth_manager.check_permission = Mock(return_value=True)
        mock_self._get_auth_manager = Mock(return_value=auth_manager)

        decorated = require_permission('kb:delete')(mock_func)
        result = decorated(mock_self)

        # 验证成功执行
        assert result == {'success': True, 'data': 'deleted'}

    def test_not_authenticated(self):
        """测试未认证返回 401."""
        mock_func = Mock(return_value={'success': True})
        mock_self = Mock()
        mock_self.current_user = None  # 未认证
        mock_self._json_response = Mock()

        decorated = require_permission('kb:read')(mock_func)
        result = decorated(mock_self)

        # 验证返回 401
        mock_self._json_response.assert_called_once()
        call_args = mock_self._json_response.call_args
        assert call_args[0][0]['code'] == 401
        assert result is None


class TestAuthMiddleware:
    """测试 AuthMiddleware 类."""

    def test_check_auth_success(self):
        """测试认证检查成功."""
        from lib.auth.auth_middleware import AuthMiddleware

        auth_manager = Mock()
        auth_manager.validate_token = Mock(return_value='admin')
        auth_manager.config = {
            'tokens': {
                'test_token': {'username': 'test_user'}
            }
        }

        middleware = AuthMiddleware(auth_manager)
        request = Mock()
        request.headers = {'Authorization': 'Bearer test_token'}

        result = middleware.check_auth(request)

        assert result is not None
        assert result['username'] == 'test_user'
        assert result['role'] == 'admin'

    def test_check_auth_failure(self):
        """测试认证检查失败."""
        from lib.auth.auth_middleware import AuthMiddleware

        auth_manager = Mock()
        auth_manager.validate_token = Mock(return_value=None)

        middleware = AuthMiddleware(auth_manager)
        request = Mock()
        request.headers = {'Authorization': 'Bearer invalid'}

        result = middleware.check_auth(request)

        assert result is None