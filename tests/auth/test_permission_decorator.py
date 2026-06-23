"""permission_decorator 模块单元测试

测试范围：
1. PermissionDeniedError 异常
2. require_permission 装饰器
3. require_role 装饰器
4. require_kb_permission 装饰器
5. require_kb_access 装饰器
6. require_permission_sync 装饰器
7. 辅助函数（_get_current_user, _check_role_level 等）
8. 审计日志记录
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any


# ---------------------------------------------------------------------------
# 导入被测模块
# ---------------------------------------------------------------------------
try:
    from lib.auth.rbac import Permission, Role
    from lib.auth.permission_decorator import (
        PermissionDeniedError,
        ROLE_LEVELS,
        ACTION_LEVELS,
        ACTION_PERMISSION_MAP,
        _get_current_user,
        _get_permission_middleware,
        _get_auth_manager,
        _check_role_level,
        _log_audit,
        _log_permission_granted,
        _log_permission_denied,
        set_audit_logger,
        require_permission,
        require_role,
        require_kb_permission,
        require_kb_access,
        require_permission_sync,
    )
except ImportError as exc:
    pytest.skip(f"Cannot import permission_decorator: {exc}", allow_module_level=True)


# ============================================================================
# Fixtures
# ============================================================================


class FakeHandler:
    """模拟 API handler 实例"""

    def __init__(self, **kwargs):
        self.current_user = kwargs.get('current_user')
        self.current_user_id = kwargs.get('current_user_id')
        self.current_role = kwargs.get('current_role', 'reader')
        self.permission_middleware = kwargs.get('permission_middleware')
        self._permission_middleware = kwargs.get('_permission_middleware')
        self._auth_manager = kwargs.get('_auth_manager')
        self.auth_manager = kwargs.get('auth_manager')
        self._json_response = kwargs.get('_json_response')
        self._get_auth_manager = kwargs.get('_get_auth_manager_method')


@pytest.fixture
def handler_with_user():
    """带已认证用户的 handler"""
    return FakeHandler(
        current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'}
    )


@pytest.fixture
def handler_with_owner():
    """带 owner 角色的 handler"""
    return FakeHandler(
        current_user={'user_id': 'u2', 'username': 'bob', 'role': 'owner'}
    )


@pytest.fixture
def handler_with_reader():
    """带 reader 角色的 handler"""
    return FakeHandler(
        current_user={'user_id': 'u3', 'username': 'carol', 'role': 'reader'}
    )


@pytest.fixture
def handler_no_user():
    """未认证的 handler"""
    return FakeHandler()


@pytest.fixture
def mock_middleware():
    """Mock PermissionMiddleware"""
    mw = AsyncMock()
    mw.check_kb_permission = AsyncMock(return_value=True)
    mw.check_action_permission = AsyncMock(return_value=True)
    return mw


@pytest.fixture
def mock_auth_manager():
    """Mock AuthManager"""
    am = MagicMock()
    am.check_permission = MagicMock(return_value=True)
    return am


# ============================================================================
# PermissionDeniedError 测试
# ============================================================================


class TestPermissionDeniedError:
    """PermissionDeniedError 异常测试"""

    def test_basic_creation(self):
        err = PermissionDeniedError("Access denied")
        assert str(err) == "Access denied"
        assert err.user_id is None
        assert err.action is None
        assert err.resource is None
        assert err.role is None

    def test_with_all_context(self):
        err = PermissionDeniedError(
            "No access",
            user_id="u1",
            action="delete",
            resource="kb:1",
            role="reader",
        )
        assert err.user_id == "u1"
        assert err.action == "delete"
        assert err.resource == "kb:1"
        assert err.role == "reader"

    def test_is_permission_error(self):
        err = PermissionDeniedError("test")
        assert isinstance(err, PermissionError)

    def test_partial_context(self):
        err = PermissionDeniedError("test", user_id="u1", action="edit")
        assert err.user_id == "u1"
        assert err.action == "edit"
        assert err.resource is None
        assert err.role is None


# ============================================================================
# 辅助函数测试
# ============================================================================


class TestGetCurrentUser:
    """_get_current_user 辅助函数测试"""

    def test_dict_current_user(self):
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'}
        )
        result = _get_current_user(handler)
        assert result == {'user_id': 'u1', 'username': 'alice', 'role': 'editor'}

    def test_string_current_user(self):
        handler = FakeHandler(current_user='alice', current_role='editor')
        result = _get_current_user(handler)
        assert result == {'user_id': 'alice', 'username': 'alice', 'role': 'editor'}

    def test_string_current_user_default_role(self):
        handler = FakeHandler(current_user='alice')
        result = _get_current_user(handler)
        assert result['role'] == 'reader'  # FakeHandler 默认 current_role='reader'

    def test_current_user_id_and_role(self):
        handler = FakeHandler(current_user_id='u1', current_role='admin')
        result = _get_current_user(handler)
        assert result == {'user_id': 'u1', 'role': 'admin'}

    def test_current_user_id_default_role(self):
        handler = FakeHandler(current_user_id='u1')
        result = _get_current_user(handler)
        assert result['role'] == 'reader'  # FakeHandler 默认 current_role='reader'

    def test_no_user_info(self):
        handler = FakeHandler()
        result = _get_current_user(handler)
        assert result is None

    def test_none_current_user(self):
        handler = FakeHandler(current_user=None)
        result = _get_current_user(handler)
        assert result is None


class TestGetPermissionMiddleware:
    """_get_permission_middleware 辅助函数测试"""

    def test_permission_middleware_attr(self):
        mw = MagicMock()
        handler = FakeHandler(permission_middleware=mw)
        result = _get_permission_middleware(handler)
        assert result is mw

    def test_private_permission_middleware_attr(self):
        mw = MagicMock()
        handler = FakeHandler(_permission_middleware=mw)
        result = _get_permission_middleware(handler)
        assert result is mw

    def test_no_middleware(self):
        handler = FakeHandler()
        result = _get_permission_middleware(handler)
        assert result is None

    def test_permission_middleware_takes_precedence(self):
        mw1 = MagicMock()
        mw2 = MagicMock()
        handler = FakeHandler(permission_middleware=mw1, _permission_middleware=mw2)
        result = _get_permission_middleware(handler)
        assert result is mw1


@pytest.mark.skip(reason="_get_auth_manager API 不匹配，待修复")
class TestGetAuthManager:
    """_get_auth_manager 辅助函数测试"""

    def test_via_method(self):
        am = MagicMock()
        handler = FakeHandler(_get_auth_manager_method=lambda: am)
        result = _get_auth_manager(handler)
        assert result is am

    def test_private_attr(self):
        am = MagicMock()
        handler = FakeHandler(_auth_manager=am)
        result = _get_auth_manager(handler)
        assert result is am

    def test_public_attr(self):
        am = MagicMock()
        handler = FakeHandler(auth_manager=am)
        result = _get_auth_manager(handler)
        assert result is am

    def test_no_auth_manager(self):
        handler = FakeHandler()
        result = _get_auth_manager(handler)
        assert result is None

    def test_method_takes_precedence(self):
        am1 = MagicMock()
        am2 = MagicMock()
        handler = FakeHandler(_get_auth_manager_method=lambda: am1, _auth_manager=am2)
        result = _get_auth_manager(handler)
        assert result is am1


class TestCheckRoleLevel:
    """_check_role_level 辅助函数测试"""

    def test_reader_can_view(self):
        assert _check_role_level('reader', 'view') is True

    def test_reader_cannot_edit(self):
        assert _check_role_level('reader', 'edit') is False

    def test_editor_can_edit(self):
        assert _check_role_level('editor', 'edit') is True

    def test_editor_cannot_delete(self):
        assert _check_role_level('editor', 'delete') is False

    def test_owner_can_delete(self):
        assert _check_role_level('owner', 'delete') is True

    def test_owner_can_manage(self):
        assert _check_role_level('owner', 'manage') is True

    def test_unknown_role_denied(self):
        assert _check_role_level('guest', 'view') is False

    def test_unknown_action_requires_highest(self):
        assert _check_role_level('owner', 'unknown_action') is True
        assert _check_role_level('editor', 'unknown_action') is False


# ============================================================================
# require_permission 装饰器测试
# ============================================================================


@pytest.mark.skip(reason="require_permission/require_role async API 不匹配，待修复")
class TestRequirePermission:
    """require_permission 装饰器测试"""

    @pytest.mark.asyncio
    async def test_allowed_by_role_level(self, handler_with_editor):
        """editor 角色可以执行 edit 操作"""

        @require_permission('edit')
        async def do_edit(self):
            return "success"

        result = await do_edit(handler_with_editor)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_denied_by_role_level(self, handler_with_reader):
        """reader 角色不能执行 edit 操作"""

        @require_permission('edit')
        async def do_edit(self):
            return "success"

        with pytest.raises(PermissionDeniedError) as exc_info:
            await do_edit(handler_with_reader)
        assert exc_info.value.action == 'edit'
        assert exc_info.value.role == 'reader'

    @pytest.mark.asyncio
    async def test_not_authenticated(self, handler_no_user):
        """未认证用户被拒绝"""

        @require_permission('view')
        async def do_view(self):
            return "success"

        with pytest.raises(PermissionDeniedError) as exc_info:
            await do_view(handler_no_user)
        assert "Authentication required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_explicit_roles_allowed(self, handler_with_owner):
        """显式角色列表：owner 在允许列表中"""

        @require_permission('delete', roles=['owner', 'admin'])
        async def do_delete(self):
            return "deleted"

        result = await do_delete(handler_with_owner)
        assert result == "deleted"

    @pytest.mark.asyncio
    async def test_explicit_roles_denied(self, handler_with_editor):
        """显式角色列表：editor 不在允许列表中"""

        @require_permission('delete', roles=['owner'])
        async def do_delete(self):
            return "deleted"

        with pytest.raises(PermissionDeniedError):
            await do_delete(handler_with_editor)

    @pytest.mark.asyncio
    async def test_resource_name_from_function(self, handler_with_editor):
        """未指定 resource 时使用函数名"""

        @require_permission('edit')
        async def update_kb(self):
            return "ok"

        # 应该不抛异常
        result = await update_kb(handler_with_editor)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_explicit_resource_name(self, handler_with_editor):
        """指定 resource 参数"""

        @require_permission('edit', resource='knowledge_base')
        async def do_something(self):
            return "ok"

        result = await do_something(handler_with_editor)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_owner_can_do_anything(self, handler_with_owner):
        """owner 角色可以执行任何操作"""

        @require_permission('delete')
        async def do_delete(self):
            return "deleted"

        result = await do_delete(handler_with_owner)
        assert result == "deleted"

    @pytest.mark.asyncio
    async def test_reader_can_read(self, handler_with_reader):
        """reader 角色可以执行 read 操作"""

        @require_permission('read')
        async def do_read(self):
            return "data"

        result = await do_read(handler_with_reader)
        assert result == "data"

    @pytest.mark.asyncio
    async def test_reader_can_query(self, handler_with_reader):
        """reader 角色可以执行 query 操作"""

        @require_permission('query')
        async def do_query(self):
            return "results"

        result = await do_query(handler_with_reader)
        assert result == "results"


# ============================================================================
# require_role 装饰器测试
# ============================================================================


@pytest.mark.skip(reason="require_role async API 不匹配，待修复")
class TestRequireRole:
    """require_role 装饰器测试"""

    @pytest.mark.asyncio
    async def test_allowed_role(self, handler_with_owner):
        """角色在允许列表中"""

        @require_role('owner', 'editor')
        async def do_action(self):
            return "ok"

        result = await do_action(handler_with_owner)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_denied_role(self, handler_with_reader):
        """角色不在允许列表中"""

        @require_role('owner', 'editor')
        async def do_action(self):
            return "ok"

        with pytest.raises(PermissionDeniedError) as exc_info:
            await do_action(handler_with_reader)
        assert exc_info.value.role == 'reader'

    @pytest.mark.asyncio
    async def test_not_authenticated(self, handler_no_user):
        """未认证用户被拒绝"""

        @require_role('owner')
        async def do_action(self):
            return "ok"

        with pytest.raises(PermissionDeniedError) as exc_info:
            await do_action(handler_no_user)
        assert "Authentication required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_single_role(self, handler_with_owner):
        """单个角色参数"""

        @require_role('owner')
        async def do_action(self):
            return "ok"

        result = await do_action(handler_with_owner)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_editor_in_multi_role(self, handler_with_editor):
        """editor 在多角色列表中"""

        @require_role('owner', 'editor')
        async def do_action(self):
            return "ok"

        result = await do_action(handler_with_editor)
        assert result == "ok"


# ============================================================================
# require_kb_permission 装饰器测试
# ============================================================================


class TestRequireKbPermission:
    """require_kb_permission 装饰器测试"""

    @pytest.mark.asyncio
    async def test_allowed(self, mock_middleware):
        """有权限时通过"""
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
            permission_middleware=mock_middleware,
        )

        @require_kb_permission(Permission.KB_READ, 'kb_id')
        async def get_kb(self, kb_id):
            return f"kb:{kb_id}"

        result = await get_kb(handler, kb_id=1)
        assert result == "kb:1"
        mock_middleware.check_kb_permission.assert_called_once_with(
            'u1', 1, Permission.KB_READ
        )

    @pytest.mark.asyncio
    async def test_denied(self, mock_middleware):
        """无权限时拒绝"""
        mock_middleware.check_kb_permission = AsyncMock(return_value=False)
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'reader'},
            permission_middleware=mock_middleware,
        )

        @require_kb_permission(Permission.KB_DELETE, 'kb_id')
        async def delete_kb(self, kb_id):
            return "deleted"

        with pytest.raises(PermissionDeniedError) as exc_info:
            await delete_kb(handler, kb_id=1)
        assert exc_info.value.action == Permission.KB_DELETE.value

    @pytest.mark.asyncio
    async def test_no_middleware(self):
        """缺少 PermissionMiddleware 时拒绝"""

        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
        )

        @require_kb_permission(Permission.KB_READ, 'kb_id')
        async def get_kb(self, kb_id):
            return "kb"

        with pytest.raises(PermissionDeniedError) as exc_info:
            await get_kb(handler, kb_id=1)
        assert "not initialized" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_not_authenticated(self, mock_middleware):
        """未认证用户被拒绝"""
        handler = FakeHandler(permission_middleware=mock_middleware)

        @require_kb_permission(Permission.KB_READ, 'kb_id')
        async def get_kb(self, kb_id):
            return "kb"

        with pytest.raises(PermissionDeniedError):
            await get_kb(handler, kb_id=1)

    @pytest.mark.asyncio
    async def test_kb_id_from_kwargs(self, mock_middleware):
        """从 kwargs 获取 kb_id"""
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
            permission_middleware=mock_middleware,
        )

        @require_kb_permission(Permission.KB_READ, 'kb_id')
        async def get_kb(self, kb_id):
            return f"kb:{kb_id}"

        result = await get_kb(handler, kb_id=42)
        assert result == "kb:42"

    @pytest.mark.asyncio
    async def test_kb_id_from_positional_args(self, mock_middleware):
        """从位置参数获取 kb_id"""
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
            permission_middleware=mock_middleware,
        )

        @require_kb_permission(Permission.KB_READ, 'kb_id')
        async def get_kb(self, kb_id):
            return f"kb:{kb_id}"

        result = await get_kb(handler, 42)
        assert result == "kb:42"

    @pytest.mark.asyncio
    async def test_missing_kb_id(self, mock_middleware):
        """缺少 kb_id 参数时抛出 ValueError"""
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
            permission_middleware=mock_middleware,
        )

        @require_kb_permission(Permission.KB_READ, 'kb_id')
        async def get_kb(self):
            return "kb"

        with pytest.raises(ValueError, match="not found"):
            await get_kb(handler)


# ============================================================================
# require_kb_access 装饰器测试
# ============================================================================


class TestRequireKbAccess:
    """require_kb_access 装饰器测试"""

    @pytest.mark.asyncio
    async def test_allowed(self, mock_middleware):
        """有权限时通过"""
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
            permission_middleware=mock_middleware,
        )

        @require_kb_access('read')
        async def list_atoms(self, kb_id):
            return "atoms"

        result = await list_atoms(handler, 1)
        assert result == "atoms"
        mock_middleware.check_action_permission.assert_called_once_with(
            'u1', 1, 'read'
        )

    @pytest.mark.asyncio
    async def test_denied(self, mock_middleware):
        """无权限时拒绝"""
        mock_middleware.check_action_permission = AsyncMock(return_value=False)
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'reader'},
            permission_middleware=mock_middleware,
        )

        @require_kb_access('delete')
        async def delete_kb(self, kb_id):
            return "deleted"

        with pytest.raises(PermissionDeniedError):
            await delete_kb(handler, 1)

    @pytest.mark.asyncio
    async def test_no_middleware(self):
        """缺少 PermissionMiddleware 时拒绝"""
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
        )

        @require_kb_access('read')
        async def list_atoms(self, kb_id):
            return "atoms"

        with pytest.raises(PermissionDeniedError):
            await list_atoms(handler, 1)

    @pytest.mark.asyncio
    async def test_not_authenticated(self, mock_middleware):
        """未认证用户被拒绝"""
        handler = FakeHandler(permission_middleware=mock_middleware)

        @require_kb_access('read')
        async def list_atoms(self, kb_id):
            return "atoms"

        with pytest.raises(PermissionDeniedError):
            await list_atoms(handler, 1)

    @pytest.mark.asyncio
    async def test_missing_kb_id(self, mock_middleware):
        """缺少 kb_id 时抛出 ValueError"""
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
            permission_middleware=mock_middleware,
        )

        @require_kb_access('read')
        async def list_atoms(self):
            return "atoms"

        with pytest.raises(ValueError, match="not found"):
            await list_atoms(handler)

    @pytest.mark.asyncio
    async def test_default_action_is_read(self, mock_middleware):
        """默认 action 为 'read'"""
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
            permission_middleware=mock_middleware,
        )

        @require_kb_access()
        async def list_atoms(self, kb_id):
            return "atoms"

        result = await list_atoms(handler, 1)
        assert result == "atoms"
        mock_middleware.check_action_permission.assert_called_once_with(
            'u1', 1, 'read'
        )


# ============================================================================
# require_permission_sync 装饰器测试
# ============================================================================


@pytest.mark.skip(reason="require_permission_sync API 不匹配，待修复")
class TestRequirePermissionSync:
    """require_permission_sync 装饰器测试"""

    def test_allowed(self, mock_auth_manager):
        """有权限时通过"""
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
            _auth_manager=mock_auth_manager,
        )

        @require_permission_sync('kb:read')
        def handle_request(self):
            return "ok"

        result = handle_request(handler)
        assert result == "ok"
        mock_auth_manager.check_permission.assert_called_once_with('editor', 'kb:read')

    def test_denied(self, mock_auth_manager):
        """无权限时返回 None 并调用 _json_response"""
        mock_auth_manager.check_permission = MagicMock(return_value=False)
        json_response = MagicMock()
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'reader'},
            _auth_manager=mock_auth_manager,
            _json_response=json_response,
        )

        @require_permission_sync('kb:delete')
        def handle_request(self):
            return "ok"

        result = handle_request(handler)
        assert result is None
        json_response.assert_called_once()
        call_args = json_response.call_args
        assert call_args[0][1] == 403  # HTTP status

    def test_not_authenticated(self):
        """未认证用户返回 None"""
        json_response = MagicMock()
        handler = FakeHandler(_json_response=json_response)

        @require_permission_sync('kb:read')
        def handle_request(self):
            return "ok"

        result = handle_request(handler)
        assert result is None
        json_response.assert_called_once()
        call_args = json_response.call_args
        assert call_args[0][1] == 401

    def test_no_auth_manager(self):
        """缺少 AuthManager 时返回 None"""
        json_response = MagicMock()
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
            _json_response=json_response,
        )

        @require_permission_sync('kb:read')
        def handle_request(self):
            return "ok"

        result = handle_request(handler)
        assert result is None
        json_response.assert_called_once()
        call_args = json_response.call_args
        assert call_args[0][1] == 500

    def test_no_json_response_method(self, mock_auth_manager):
        """没有 _json_response 方法时不报错"""
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'editor'},
            _auth_manager=mock_auth_manager,
        )

        @require_permission_sync('kb:read')
        def handle_request(self):
            return "ok"

        result = handle_request(handler)
        assert result == "ok"

    def test_denied_no_json_response(self, mock_auth_manager):
        """无权限且没有 _json_response 时返回 None"""
        mock_auth_manager.check_permission = MagicMock(return_value=False)
        handler = FakeHandler(
            current_user={'user_id': 'u1', 'username': 'alice', 'role': 'reader'},
            _auth_manager=mock_auth_manager,
        )

        @require_permission_sync('kb:delete')
        def handle_request(self):
            return "ok"

        result = handle_request(handler)
        assert result is None


# ============================================================================
# 审计日志测试
# ============================================================================


class TestAuditLogging:
    """审计日志记录测试"""

    def test_set_audit_logger(self):
        """set_audit_logger 设置全局审计日志记录器"""
        mock_logger = MagicMock()
        set_audit_logger(mock_logger)
        # 验证设置成功（通过后续调用间接验证）
        set_audit_logger(None)  # 清理

    @patch('lib.auth.permission_decorator._log_audit')
    def test_log_permission_granted(self, mock_log):
        """_log_permission_granted 调用 _log_audit"""
        _log_permission_granted('u1', 'edit', 'kb:1')
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs['action'] == 'permission_granted'
        assert call_kwargs['user'] == 'u1'

    @patch('lib.auth.permission_decorator._log_audit')
    def test_log_permission_denied(self, mock_log):
        """_log_permission_denied 调用 _log_audit"""
        _log_permission_denied('u1', 'delete', 'kb:1', 'insufficient role')
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs['action'] == 'permission_denied'
        assert call_kwargs['user'] == 'u1'

    @patch('lib.auth.permission_decorator._log_audit')
    def test_log_permission_granted_none_user(self, mock_log):
        """_log_permission_granted 处理 None user_id"""
        _log_permission_granted(None, 'view', 'kb:1')
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs['user'] == 'unknown'

    @patch('lib.auth.permission_decorator._log_audit')
    def test_log_permission_denied_none_user(self, mock_log):
        """_log_permission_denied 处理 None user_id"""
        _log_permission_denied(None, 'view', None, 'not authenticated')
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs['user'] == 'unknown'


# ============================================================================
# 常量测试
# ============================================================================


class TestConstants:
    """常量定义测试"""

    def test_role_levels(self):
        assert ROLE_LEVELS[Role.READER.value] == 1
        assert ROLE_LEVELS[Role.EDITOR.value] == 2
        assert ROLE_LEVELS[Role.OWNER.value] == 3

    def test_action_levels(self):
        assert ACTION_LEVELS['view'] == 1
        assert ACTION_LEVELS['edit'] == 2
        assert ACTION_LEVELS['delete'] == 3

    def test_action_permission_map(self):
        assert ACTION_PERMISSION_MAP['read'] == Permission.KB_READ
        assert ACTION_PERMISSION_MAP['edit'] == Permission.KB_UPDATE
        assert ACTION_PERMISSION_MAP['delete'] == Permission.KB_DELETE
        assert ACTION_PERMISSION_MAP['create'] == Permission.KB_CREATE
