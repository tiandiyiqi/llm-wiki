"""rbac_model 模块单元测试

测试范围：
1. RBAC_SCHEMA 常量
2. DEFAULT_ROLES / DEFAULT_PERMISSIONS / DEFAULT_ROLE_PERMISSIONS 常量
3. RBACManager 类的所有方法
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


# ---------------------------------------------------------------------------
# 导入被测模块
# ---------------------------------------------------------------------------
try:
    from lib.auth.rbac_model import (
        RBAC_SCHEMA,
        DEFAULT_ROLES,
        DEFAULT_PERMISSIONS,
        DEFAULT_ROLE_PERMISSIONS,
        RBACManager,
    )
except ImportError:
    try:
        from auth.rbac_model import (
            RBAC_SCHEMA,
            DEFAULT_ROLES,
            DEFAULT_PERMISSIONS,
            DEFAULT_ROLE_PERMISSIONS,
            RBACManager,
        )
    except ImportError as exc:
        pytest.skip(f"Cannot import rbac_model: {exc}", allow_module_level=True)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock 数据库管理器"""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_all = AsyncMock(return_value=[])
    return db


@pytest.fixture
def manager(mock_db):
    """RBACManager 实例"""
    return RBACManager(mock_db)


# ============================================================================
# 常量测试
# ============================================================================


class TestConstants:
    """常量定义测试"""

    def test_rbac_schema_is_string(self):
        assert isinstance(RBAC_SCHEMA, str)
        assert len(RBAC_SCHEMA) > 0

    def test_rbac_schema_contains_tables(self):
        assert 'CREATE TABLE' in RBAC_SCHEMA
        assert 'roles' in RBAC_SCHEMA
        assert 'permissions' in RBAC_SCHEMA
        assert 'role_permissions' in RBAC_SCHEMA
        assert 'user_roles' in RBAC_SCHEMA

    def test_rbac_schema_has_indexes(self):
        assert 'CREATE INDEX' in RBAC_SCHEMA

    def test_default_roles_structure(self):
        assert len(DEFAULT_ROLES) == 4
        role_names = [r['name'] for r in DEFAULT_ROLES]
        assert 'admin' in role_names
        assert 'editor' in role_names
        assert 'viewer' in role_names
        assert 'guest' in role_names

    def test_default_roles_are_system(self):
        for role in DEFAULT_ROLES:
            assert role['is_system'] is True

    def test_default_roles_have_descriptions(self):
        for role in DEFAULT_ROLES:
            assert 'description' in role
            assert len(role['description']) > 0

    def test_default_permissions_structure(self):
        assert len(DEFAULT_PERMISSIONS) >= 10
        for perm in DEFAULT_PERMISSIONS:
            assert 'name' in perm
            assert 'description' in perm
            assert 'resource_type' in perm
            assert 'action' in perm

    def test_default_permissions_categories(self):
        resource_types = {p['resource_type'] for p in DEFAULT_PERMISSIONS}
        assert 'kb' in resource_types
        assert 'atom' in resource_types
        assert 'user' in resource_types
        assert 'system' in resource_types

    def test_default_role_permissions_keys(self):
        assert set(DEFAULT_ROLE_PERMISSIONS.keys()) == {'admin', 'editor', 'viewer', 'guest'}

    def test_admin_has_all_permissions(self):
        admin_perms = DEFAULT_ROLE_PERMISSIONS['admin']
        all_perm_names = {p['name'] for p in DEFAULT_PERMISSIONS}
        assert set(admin_perms) == all_perm_names

    def test_viewer_has_read_only(self):
        viewer_perms = DEFAULT_ROLE_PERMISSIONS['viewer']
        assert 'kb:read' in viewer_perms
        assert 'atom:read' in viewer_perms
        assert 'kb:delete' not in viewer_perms
        assert 'kb:update' not in viewer_perms

    def test_guest_minimal_permissions(self):
        guest_perms = DEFAULT_ROLE_PERMISSIONS['guest']
        assert 'atom:read' in guest_perms
        assert len(guest_perms) < len(DEFAULT_ROLE_PERMISSIONS['viewer'])

    def test_editor_has_create_update(self):
        editor_perms = DEFAULT_ROLE_PERMISSIONS['editor']
        assert 'kb:read' in editor_perms
        assert 'kb:update' in editor_perms
        assert 'atom:create' in editor_perms
        assert 'atom:update' in editor_perms
        assert 'kb:delete' not in editor_perms

    def test_all_mapped_roles_exist_in_default(self):
        role_names = {r['name'] for r in DEFAULT_ROLES}
        for role_name in DEFAULT_ROLE_PERMISSIONS:
            assert role_name in role_names

    def test_all_mapped_permissions_exist_in_default(self):
        perm_names = {p['name'] for p in DEFAULT_PERMISSIONS}
        for role_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
            for perm in perms:
                assert perm in perm_names


# ============================================================================
# RBACManager 初始化测试
# ============================================================================


class TestRBACManagerInit:
    """RBACManager 初始化测试"""

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, manager, mock_db):
        """初始化时创建表结构"""
        await manager.initialize()
        assert manager._initialized is True
        assert mock_db.execute.call_count > 0

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, manager, mock_db):
        """重复初始化不会重复执行"""
        await manager.initialize()
        call_count = mock_db.execute.call_count
        await manager.initialize()
        assert mock_db.execute.call_count == call_count

    @pytest.mark.asyncio
    async def test_initialize_inserts_default_roles(self, manager, mock_db):
        """初始化时插入默认角色"""
        await manager.initialize()
        role_insert_calls = [
            call for call in mock_db.execute.call_args_list
            if 'roles' in str(call)
        ]
        assert len(role_insert_calls) >= len(DEFAULT_ROLES)


# ============================================================================
# RBACManager 角色管理测试
# ============================================================================


class TestRBACManagerRoles:
    """RBACManager 角色管理测试"""

    @pytest.mark.asyncio
    async def test_create_role_success(self, manager, mock_db):
        """创建角色成功"""
        mock_db.fetch_one = AsyncMock(return_value={'id': 10})
        result = await manager.create_role('custom_role', 'Custom role description')
        assert result == 10

    @pytest.mark.asyncio
    async def test_create_role_none_result(self, manager, mock_db):
        """创建角色时 fetch_one 返回 None"""
        mock_db.fetch_one = AsyncMock(return_value=None)
        result = await manager.create_role('custom_role', 'Custom role description')
        assert result is None

    @pytest.mark.asyncio
    async def test_create_role_failure(self, manager, mock_db):
        """创建角色失败（如名称冲突）"""
        mock_db.fetch_one = AsyncMock(side_effect=Exception("duplicate key"))
        result = await manager.create_role('admin', 'Duplicate')
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_role_non_system(self, manager, mock_db):
        """删除非系统角色"""
        mock_db.fetch_one = AsyncMock(
            side_effect=[
                {'is_system': False},  # check is_system
                {'id': 5},  # DELETE RETURNING
            ]
        )
        result = await manager.delete_role(5)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_system_role_denied(self, manager, mock_db):
        """不能删除系统角色"""
        mock_db.fetch_one = AsyncMock(return_value={'is_system': True})
        result = await manager.delete_role(1)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_role(self, manager, mock_db):
        """删除不存在的角色"""
        mock_db.fetch_one = AsyncMock(
            side_effect=[
                {'is_system': False},  # check
                None,  # DELETE RETURNING (no rows)
            ]
        )
        result = await manager.delete_role(999)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_role_check_returns_none(self, manager, mock_db):
        """删除角色时检查查询返回 None（角色不存在）"""
        mock_db.fetch_one = AsyncMock(return_value=None)
        result = await manager.delete_role(999)
        # 角色不存在时 DELETE 也不会返回行
        assert result is False

    @pytest.mark.asyncio
    async def test_list_roles(self, manager, mock_db):
        """列出所有角色"""
        expected = [
            {'id': 1, 'name': 'admin', 'description': 'Admin', 'is_system': True, 'created_at': '2026-01-01'},
            {'id': 2, 'name': 'editor', 'description': 'Editor', 'is_system': True, 'created_at': '2026-01-01'},
        ]
        mock_db.fetch_all = AsyncMock(return_value=expected)
        result = await manager.list_roles()
        assert result == expected

    @pytest.mark.asyncio
    async def test_list_permissions(self, manager, mock_db):
        """列出所有权限"""
        expected = [
            {'id': 1, 'name': 'kb:create', 'description': 'Create KB', 'resource_type': 'kb', 'action': 'create'},
        ]
        mock_db.fetch_all = AsyncMock(return_value=expected)
        result = await manager.list_permissions()
        assert result == expected


# ============================================================================
# RBACManager 用户角色管理测试
# ============================================================================


class TestRBACManagerUserRoles:
    """RBACManager 用户角色管理测试"""

    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, manager, mock_db):
        """给用户分配角色"""
        result = await manager.assign_role_to_user('user1', 1)
        assert result is True
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_role_with_extras(self, manager, mock_db):
        """给用户分配角色（带分配者和过期时间）"""
        expires = datetime(2027, 1, 1)
        result = await manager.assign_role_to_user(
            'user1', 1, assigned_by=2, expires_at=expires
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_assign_role_failure(self, manager, mock_db):
        """分配角色失败"""
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
        result = await manager.assign_role_to_user('user1', 1)
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_role_from_user(self, manager, mock_db):
        """撤销用户角色"""
        mock_db.fetch_one = AsyncMock(return_value={'user_id': 'user1'})
        result = await manager.revoke_role_from_user('user1', 1)
        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_role(self, manager, mock_db):
        """撤销不存在的角色关联"""
        mock_db.fetch_one = AsyncMock(return_value=None)
        result = await manager.revoke_role_from_user('user1', 999)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_user_roles(self, manager, mock_db):
        """获取用户角色列表"""
        mock_db.fetch_all = AsyncMock(
            return_value=[{'name': 'admin'}, {'name': 'editor'}]
        )
        result = await manager.get_user_roles('user1')
        assert result == ['admin', 'editor']

    @pytest.mark.asyncio
    async def test_get_user_roles_empty(self, manager, mock_db):
        """用户无角色"""
        mock_db.fetch_all = AsyncMock(return_value=[])
        result = await manager.get_user_roles('unknown_user')
        assert result == []


# ============================================================================
# RBACManager 权限管理测试
# ============================================================================


class TestRBACManagerPermissions:
    """RBACManager 权限管理测试"""

    @pytest.mark.asyncio
    async def test_get_user_permissions(self, manager, mock_db):
        """获取用户权限集合"""
        mock_db.fetch_all = AsyncMock(
            return_value=[{'name': 'kb:read'}, {'name': 'kb:update'}]
        )
        result = await manager.get_user_permissions('user1')
        assert result == {'kb:read', 'kb:update'}

    @pytest.mark.asyncio
    async def test_get_user_permissions_empty(self, manager, mock_db):
        """用户无权限"""
        mock_db.fetch_all = AsyncMock(return_value=[])
        result = await manager.get_user_permissions('unknown')
        assert result == set()

    @pytest.mark.asyncio
    async def test_get_user_permissions_deduplication(self, manager, mock_db):
        """权限去重（DISTINCT）"""
        mock_db.fetch_all = AsyncMock(
            return_value=[{'name': 'kb:read'}, {'name': 'kb:read'}]
        )
        result = await manager.get_user_permissions('user1')
        assert result == {'kb:read'}

    @pytest.mark.asyncio
    async def test_check_permission_allowed(self, manager, mock_db):
        """检查权限：有权限"""
        mock_db.fetch_one = AsyncMock(return_value={'has_permission': True})
        result = await manager.check_permission('user1', 'kb:read')
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_denied(self, manager, mock_db):
        """检查权限：无权限"""
        mock_db.fetch_one = AsyncMock(return_value={'has_permission': False})
        result = await manager.check_permission('user1', 'kb:delete')
        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_no_result(self, manager, mock_db):
        """检查权限：查询无结果"""
        mock_db.fetch_one = AsyncMock(return_value=None)
        result = await manager.check_permission('user1', 'kb:read')
        assert result is False

    @pytest.mark.asyncio
    async def test_grant_permission_to_role(self, manager, mock_db):
        """给角色授权"""
        result = await manager.grant_permission_to_role(1, 2)
        assert result is True
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_grant_permission_failure(self, manager, mock_db):
        """授权失败"""
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
        result = await manager.grant_permission_to_role(1, 2)
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_permission_from_role(self, manager, mock_db):
        """撤销角色权限"""
        mock_db.fetch_one = AsyncMock(return_value={'role_id': 1})
        result = await manager.revoke_permission_from_role(1, 2)
        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_permission(self, manager, mock_db):
        """撤销不存在的权限关联"""
        mock_db.fetch_one = AsyncMock(return_value=None)
        result = await manager.revoke_permission_from_role(1, 999)
        assert result is False
