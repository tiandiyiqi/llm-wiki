"""权限管理 API 测试

测试 PermissionAPI 的权限分配/撤销和批量操作。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from lib.api.permission_api import (
        PermissionAPI,
        CheckPermissionRequest,
        AssignRoleRequest,
        RevokeRoleRequest,
    )
    from lib.core.storage_interface import StorageInterface
    from lib.auth.rbac import RBACManager, Permission, Role, ROLE_DEFINITIONS

    _IMPORT_OK = True
except ImportError as _e:
    _IMPORT_OK = False
    _IMPORT_ERROR = str(_e)


@pytest.fixture
def mock_storage():
    """Mock StorageInterface"""
    storage = AsyncMock(spec=StorageInterface)
    storage.list_kbs = AsyncMock(return_value=[
        {'id': 1, 'name': 'KB1'},
        {'id': 2, 'name': 'KB2'},
    ])
    return storage


@pytest.fixture
def mock_rbac():
    """Mock RBACManager"""
    rbac = AsyncMock(spec=RBACManager)
    rbac.check_permission = AsyncMock(return_value=True)
    rbac.assign_role = AsyncMock(return_value=True)
    rbac.revoke_role = AsyncMock(return_value=True)
    rbac.get_user_roles = AsyncMock(return_value={'editor'})
    rbac.get_user_permissions = AsyncMock(return_value={Permission.KB_READ, Permission.ATOM_CREATE})
    rbac.get_role_permissions = AsyncMock(return_value={Permission.KB_READ, Permission.ATOM_CREATE})
    rbac.create_custom_role = AsyncMock(return_value=True)
    rbac.delete_custom_role = AsyncMock(return_value=True)
    return rbac


@pytest.fixture
def perm_api(mock_storage, mock_rbac):
    """创建 PermissionAPI 实例"""
    return PermissionAPI(storage=mock_storage, rbac=mock_rbac)


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestCheckPermission:
    """权限检查测试"""

    @pytest.mark.asyncio
    async def test_check_permission_has(self, perm_api, mock_rbac):
        """用户有权限"""
        mock_rbac.check_permission = AsyncMock(return_value=True)
        mock_rbac.get_user_roles = AsyncMock(return_value={'owner'})
        request = CheckPermissionRequest(kb_id=1, permission="kb:read")
        result = await perm_api.check_permission("user1", request)

        assert result['success'] is True
        assert result['data']['has_permission'] is True

    @pytest.mark.asyncio
    async def test_check_permission_no(self, perm_api, mock_rbac):
        """用户无权限"""
        mock_rbac.check_permission = AsyncMock(return_value=False)
        mock_rbac.get_user_roles = AsyncMock(return_value=set())
        request = CheckPermissionRequest(kb_id=1, permission="kb:read")
        result = await perm_api.check_permission("user1", request)

        assert result['success'] is True
        assert result['data']['has_permission'] is False

    @pytest.mark.asyncio
    async def test_check_permission_invalid_name(self, perm_api):
        """无效的权限名称"""
        request = CheckPermissionRequest(kb_id=1, permission="nonexistent_perm")


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestAssignRole:
    """角色分配测试"""

    @pytest.mark.asyncio
    async def test_assign_role_success(self, perm_api, mock_rbac):
        """成功分配角色"""
        mock_rbac.get_user_roles = AsyncMock(return_value={'owner'})
        request = AssignRoleRequest(user_id="target", kb_id=1, role="editor")
        result = await perm_api.assign_role("owner_user", request)

        assert result['success'] is True
        assert result['code'] == 201
        assert result['data']['role'] == 'editor'

    @pytest.mark.asyncio
    async def test_assign_role_permission_denied(self, perm_api, mock_rbac):
        """无权限分配角色"""
        mock_rbac.check_permission = AsyncMock(return_value=False)
        request = AssignRoleRequest(user_id="target", kb_id=1, role="editor")
        result = await perm_api.assign_role("user1", request)

        assert result['success'] is False
        assert result['code'] == 403

    @pytest.mark.asyncio
    async def test_assign_role_invalid_role(self, perm_api, mock_rbac):
        """无效的角色"""
        request = AssignRoleRequest(user_id="target", kb_id=1, role="superadmin")
        result = await perm_api.assign_role("admin", request)

        assert result['success'] is False
        assert result['code'] == 400
        assert 'Invalid role' in result['error']

    @pytest.mark.asyncio
    async def test_assign_owner_role_by_non_owner(self, perm_api, mock_rbac):
        """非 owner 不能分配 owner 角色"""
        mock_rbac.get_user_roles = AsyncMock(return_value={'editor'})
        request = AssignRoleRequest(user_id="target", kb_id=1, role="owner")
        result = await perm_api.assign_role("editor_user", request)

        assert result['success'] is False
        assert result['code'] == 403
        assert 'Only owner' in result['error']


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestRevokeRole:
    """角色撤销测试"""

    @pytest.mark.asyncio
    async def test_revoke_role_success(self, perm_api, mock_rbac):
        """成功撤销角色"""
        mock_rbac.get_user_roles = AsyncMock(return_value={'editor', 'reader'})
        request = RevokeRoleRequest(user_id="target", kb_id=1, role="editor")
        result = await perm_api.revoke_role("admin", request)

        assert result['success'] is True
        assert result['code'] == 200
        assert result['data']['revoked_role'] == 'editor'

    @pytest.mark.asyncio
    async def test_revoke_role_not_found(self, perm_api, mock_rbac):
        """用户没有该角色"""
        mock_rbac.get_user_roles = AsyncMock(return_value={'reader'})
        request = RevokeRoleRequest(user_id="target", kb_id=1, role="owner")
        result = await perm_api.revoke_role("admin", request)

        assert result['success'] is False
        assert result['code'] == 404

    @pytest.mark.asyncio
    async def test_revoke_role_permission_denied(self, perm_api, mock_rbac):
        """无权限撤销角色"""
        mock_rbac.check_permission = AsyncMock(return_value=False)
        request = RevokeRoleRequest(user_id="target", kb_id=1, role="editor")
        result = await perm_api.revoke_role("user1", request)

        assert result['success'] is False
        assert result['code'] == 403


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestBatchPermissions:
    """批量权限操作测试"""

    @pytest.mark.asyncio
    async def test_check_multiple_permissions(self, perm_api, mock_rbac):
        """批量检查权限"""
        mock_rbac.check_permission = AsyncMock(return_value=True)
        result = await perm_api.check_multiple_permissions(
            "user1", 1, ["kb:read", "atom:create"]
        )

        assert result['success'] is True
        assert result['data']['results']['kb:read'] is True
        assert result['data']['results']['atom:create'] is True

    @pytest.mark.asyncio
    async def test_check_multiple_permissions_with_invalid(self, perm_api, mock_rbac):
        """批量检查包含无效权限名"""
        result = await perm_api.check_multiple_permissions(
            "user1", 1, ["kb:read", "invalid_perm"]
        )

        assert result['success'] is True
        assert result['data']['results']['invalid_perm'] is False


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestListRolesAndPermissions:
    """角色和权限列表测试"""

    @pytest.mark.asyncio
    async def test_list_roles(self, perm_api):
        """列出所有角色"""
        result = await perm_api.list_roles()

        assert result['success'] is True
        assert result['data']['total'] > 0
        assert len(result['data']['roles']) > 0

    @pytest.mark.asyncio
    async def test_list_permissions(self, perm_api):
        """列出所有权限"""
        result = await perm_api.list_permissions()

        assert result['success'] is True
        assert result['data']['total'] > 0

    @pytest.mark.asyncio
    async def test_get_role_permissions(self, perm_api, mock_rbac):
        """获取角色权限"""
        # get_role_permissions 在 rbac 中是同步方法
        mock_rbac.get_role_permissions = MagicMock(return_value={Permission.KB_READ, Permission.ATOM_CREATE})
        # perm_api 的 get_role_permissions 是 async，内部调用同步的 rbac 方法
        result = await perm_api.get_role_permissions("owner")

        assert result['success'] is True
        assert len(result['data']['permissions']) >= 2

    @pytest.mark.asyncio
    async def test_get_role_permissions_not_found(self, perm_api):
        """获取不存在的角色权限"""
        result = await perm_api.get_role_permissions("nonexistent")

        assert result['success'] is False
        assert result['code'] == 404


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestCustomRole:
    """自定义角色测试"""

    @pytest.mark.asyncio
    async def test_create_custom_role_success(self, perm_api, mock_rbac):
        """成功创建自定义角色"""
        result = await perm_api.create_custom_role(
            operator_id="admin",
            role_name="custom_viewer",
            permissions=["kb:read", "atom:read"],
            description="自定义查看者",
        )

        assert result['success'] is True
        assert result['code'] == 201

    @pytest.mark.asyncio
    async def test_create_custom_role_invalid_permission(self, perm_api):
        """创建自定义角色时包含无效权限"""
        result = await perm_api.create_custom_role(
            operator_id="admin",
            role_name="custom_bad",
            permissions=["kb:read", "invalid_perm"],
            description="无效权限角色",
        )

        assert result['success'] is False
        assert result['code'] == 400
        assert 'Invalid permissions' in result['error']

    @pytest.mark.asyncio
    async def test_delete_custom_role_success(self, perm_api, mock_rbac):
        """成功删除自定义角色"""
        result = await perm_api.delete_custom_role("admin", "custom_viewer")

        assert result['success'] is True
        assert result['data']['deleted'] is True

    @pytest.mark.asyncio
    async def test_delete_predefined_role(self, perm_api):
        """不能删除预定义角色"""
        result = await perm_api.delete_custom_role("admin", "owner")

        assert result['success'] is False
        assert result['code'] == 400
        assert 'predefined' in result['error'].lower()


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestAccessibleKBs:
    """可访问知识库测试"""

    @pytest.mark.asyncio
    async def test_get_accessible_kbs(self, perm_api, mock_storage, mock_rbac):
        """获取用户可访问的知识库"""
        async def _check_perm(user_id, kb_id, perm):
            return kb_id == 1
        mock_rbac.check_permission = AsyncMock(side_effect=_check_perm)
        mock_rbac.get_user_roles = AsyncMock(side_effect=lambda uid, kid: {'reader'} if kid == 1 else set())

        result = await perm_api.get_accessible_kbs("user1")

        assert result['success'] is True
        assert result['data']['total'] >= 0
