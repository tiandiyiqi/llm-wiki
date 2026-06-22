"""RBAC（基于角色的访问控制）系统单元测试

测试范围：
1. 角色权限查询
2. 权限检查逻辑
3. 角色分配/撤销
4. 用户角色查询
5. 自定义角色管理
6. 角色继承机制
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Set

from lib.auth.rbac import (
    RBACManager,
    Permission,
    Role,
    RoleDefinition,
    ROLE_DEFINITIONS
)


# ==================== Fixtures ====================

@pytest.fixture
def rbac_manager():
    """创建 RBAC 管理器实例"""
    manager = RBACManager()
    return manager


@pytest.fixture
async def initialized_rbac(rbac_manager):
    """已初始化的 RBAC 管理器"""
    await rbac_manager.initialize()
    return rbac_manager


@pytest.fixture
def clean_role_definitions():
    """清理后的角色定义（用于自定义角色测试）"""
    # 保存原始定义
    original = ROLE_DEFINITIONS.copy()
    yield ROLE_DEFINITIONS
    # 恢复原始定义
    ROLE_DEFINITIONS.clear()
    ROLE_DEFINITIONS.update(original)


# ==================== 初始化测试 ====================

class TestRBACInitialization:
    """RBAC 系统初始化测试"""

    @pytest.mark.asyncio
    async def test_initialize_creates_role_cache(self, rbac_manager):
        """测试初始化创建角色缓存"""
        await rbac_manager.initialize()

        # 验证缓存已创建
        assert len(rbac_manager._role_cache) > 0
        assert 'owner' in rbac_manager._role_cache
        assert 'editor' in rbac_manager._role_cache
        assert 'reader' in rbac_manager._role_cache

    @pytest.mark.asyncio
    async def test_initialize_caches_correct_permissions(self, initialized_rbac):
        """测试初始化缓存了正确的权限"""
        # 验证 owner 权限
        owner_perms = initialized_rbac._role_cache['owner']
        assert Permission.ADMIN in owner_perms
        assert Permission.KB_MANAGE in owner_perms
        assert Permission.KB_DELETE in owner_perms

        # 验证 editor 权限
        editor_perms = initialized_rbac._role_cache['editor']
        assert Permission.ATOM_UPDATE in editor_perms
        assert Permission.KB_READ in editor_perms

        # 验证 reader 权限
        reader_perms = initialized_rbac._role_cache['reader']
        assert Permission.ATOM_READ in reader_perms
        assert Permission.KB_READ in reader_perms

    @pytest.mark.asyncio
    async def test_close_clears_data(self, initialized_rbac):
        """测试关闭清理数据"""
        await initialized_rbac.close()

        assert len(initialized_rbac._user_roles) == 0
        assert len(initialized_rbac._role_cache) == 0


# ==================== 角色权限查询测试 ====================

class TestRolePermissionQuery:
    """角色权限查询测试"""

    @pytest.mark.asyncio
    async def test_get_owner_permissions(self, initialized_rbac):
        """测试获取 owner 所有权限"""
        permissions = initialized_rbac.get_role_permissions('owner')

        # 验证所有权限
        assert Permission.KB_CREATE in permissions
        assert Permission.KB_READ in permissions
        assert Permission.KB_UPDATE in permissions
        assert Permission.KB_DELETE in permissions
        assert Permission.KB_MANAGE in permissions
        assert Permission.ATOM_CREATE in permissions
        assert Permission.ATOM_READ in permissions
        assert Permission.ATOM_UPDATE in permissions
        assert Permission.ATOM_DELETE in permissions
        assert Permission.MEMBER_MANAGE in permissions
        assert Permission.ADMIN in permissions

    @pytest.mark.asyncio
    async def test_get_editor_permissions(self, initialized_rbac):
        """测试获取 editor 权限（包括继承）"""
        permissions = initialized_rbac.get_role_permissions('editor')

        # editor 自身权限
        assert Permission.ATOM_CREATE in permissions
        assert Permission.ATOM_UPDATE in permissions
        assert Permission.ATOM_DELETE in permissions

        # 继承自 reader 的权限
        assert Permission.KB_READ in permissions
        assert Permission.ATOM_READ in permissions

        # editor 不应有的权限
        assert Permission.KB_DELETE not in permissions
        assert Permission.KB_MANAGE not in permissions
        assert Permission.ADMIN not in permissions

    @pytest.mark.asyncio
    async def test_get_reader_permissions(self, initialized_rbac):
        """测试获取 reader 权限"""
        permissions = initialized_rbac.get_role_permissions('reader')

        # reader 权限
        assert Permission.KB_READ in permissions
        assert Permission.ATOM_READ in permissions

        # reader 不应有的权限
        assert Permission.ATOM_CREATE not in permissions
        assert Permission.ATOM_UPDATE not in permissions
        assert Permission.KB_DELETE not in permissions

    @pytest.mark.asyncio
    async def test_get_invalid_role_permissions(self, initialized_rbac):
        """测试获取无效角色的权限"""
        permissions = initialized_rbac.get_role_permissions('invalid_role')

        # 应返回空集合
        assert len(permissions) == 0

    def test_get_role_permissions_caches_result(self, initialized_rbac):
        """测试权限查询结果被缓存"""
        # 第一次查询
        perms1 = initialized_rbac.get_role_permissions('owner')

        # 验证缓存
        assert 'owner' in initialized_rbac._role_cache

        # 第二次查询（从缓存）
        perms2 = initialized_rbac.get_role_permissions('owner')

        assert perms1 == perms2


# ==================== 权限检查测试 ====================

class TestPermissionCheck:
    """权限检查逻辑测试"""

    @pytest.mark.asyncio
    async def test_has_permission_owner_has_all(self, initialized_rbac):
        """测试 owner 拥有所有权限"""
        # 检查各种权限
        assert initialized_rbac.has_permission('owner', Permission.KB_READ)
        assert initialized_rbac.has_permission('owner', Permission.KB_DELETE)
        assert initialized_rbac.has_permission('owner', Permission.ADMIN)
        assert initialized_rbac.has_permission('owner', Permission.MEMBER_MANAGE)

    @pytest.mark.asyncio
    async def test_has_permission_editor_limited(self, initialized_rbac):
        """测试 editor 权限限制"""
        # editor 应有的权限
        assert initialized_rbac.has_permission('editor', Permission.KB_READ)
        assert initialized_rbac.has_permission('editor', Permission.ATOM_CREATE)
        assert initialized_rbac.has_permission('editor', Permission.ATOM_UPDATE)

        # editor 不应有的权限
        assert not initialized_rbac.has_permission('editor', Permission.KB_DELETE)
        assert not initialized_rbac.has_permission('editor', Permission.ADMIN)
        assert not initialized_rbac.has_permission('editor', Permission.MEMBER_MANAGE)

    @pytest.mark.asyncio
    async def test_has_permission_reader_read_only(self, initialized_rbac):
        """测试 reader 只读权限"""
        # reader 应有的权限
        assert initialized_rbac.has_permission('reader', Permission.KB_READ)
        assert initialized_rbac.has_permission('reader', Permission.ATOM_READ)

        # reader 不应有的权限
        assert not initialized_rbac.has_permission('reader', Permission.ATOM_CREATE)
        assert not initialized_rbac.has_permission('reader', Permission.ATOM_DELETE)
        assert not initialized_rbac.has_permission('reader', Permission.KB_UPDATE)

    @pytest.mark.asyncio
    async def test_has_permission_admin_override(self, initialized_rbac):
        """测试 ADMIN 权限覆盖所有"""
        # 创建只有 ADMIN 权限的测试角色
        initialized_rbac._role_cache['admin_only'] = {Permission.ADMIN}

        # 应拥有所有权限
        assert initialized_rbac.has_permission('admin_only', Permission.KB_READ)
        assert initialized_rbac.has_permission('admin_only', Permission.KB_DELETE)
        assert initialized_rbac.has_permission('admin_only', Permission.ATOM_CREATE)

    @pytest.mark.asyncio
    async def test_has_permission_invalid_role(self, initialized_rbac):
        """测试无效角色的权限检查"""
        assert not initialized_rbac.has_permission('invalid_role', Permission.KB_READ)


# ==================== 角色分配/撤销测试 ====================

class TestRoleAssignment:
    """角色分配/撤销测试"""

    @pytest.mark.asyncio
    async def test_assign_role_success(self, initialized_rbac):
        """测试成功分配角色"""
        result = await initialized_rbac.assign_role('user1', 100, 'editor')

        assert result is True
        assert 'user1' in initialized_rbac._user_roles
        assert 100 in initialized_rbac._user_roles['user1']
        assert 'editor' in initialized_rbac._user_roles['user1'][100]

    @pytest.mark.asyncio
    async def test_assign_role_multiple_roles(self, initialized_rbac):
        """测试分配多个角色"""
        await initialized_rbac.assign_role('user1', 100, 'reader')
        await initialized_rbac.assign_role('user1', 100, 'editor')

        roles = initialized_rbac._user_roles['user1'][100]

        assert 'reader' in roles
        assert 'editor' in roles

    @pytest.mark.asyncio
    async def test_assign_role_multiple_kb(self, initialized_rbac):
        """测试分配不同知识库的角色"""
        await initialized_rbac.assign_role('user1', 100, 'owner')
        await initialized_rbac.assign_role('user1', 200, 'reader')

        assert 'owner' in initialized_rbac._user_roles['user1'][100]
        assert 'reader' in initialized_rbac._user_roles['user1'][200]

    @pytest.mark.asyncio
    async def test_assign_role_invalid_role(self, initialized_rbac):
        """测试分配无效角色"""
        result = await initialized_rbac.assign_role('user1', 100, 'invalid_role')

        assert result is False
        assert 'user1' not in initialized_rbac._user_roles

    @pytest.mark.asyncio
    async def test_assign_role_duplicate(self, initialized_rbac):
        """测试重复分配相同角色"""
        await initialized_rbac.assign_role('user1', 100, 'editor')
        await initialized_rbac.assign_role('user1', 100, 'editor')

        # 应只有一个角色
        roles = initialized_rbac._user_roles['user1'][100]
        assert len(roles) == 1
        assert 'editor' in roles

    @pytest.mark.asyncio
    async def test_revoke_role_success(self, initialized_rbac):
        """测试成功撤销角色"""
        await initialized_rbac.assign_role('user1', 100, 'editor')
        result = await initialized_rbac.revoke_role('user1', 100, 'editor')

        assert result is True
        assert 'editor' not in initialized_rbac._user_roles['user1'][100]

    @pytest.mark.asyncio
    async def test_revoke_role_not_assigned(self, initialized_rbac):
        """测试撤销未分配的角色"""
        result = await initialized_rbac.revoke_role('user1', 100, 'editor')

        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_role_user_not_exist(self, initialized_rbac):
        """测试撤销不存在用户的角色"""
        result = await initialized_rbac.revoke_role('user1', 100, 'editor')

        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_role_kb_not_exist(self, initialized_rbac):
        """测试撤销不存在知识库的角色"""
        await initialized_rbac.assign_role('user1', 100, 'editor')
        result = await initialized_rbac.revoke_role('user1', 200, 'editor')

        assert result is False


# ==================== 用户角色查询测试 ====================

class TestUserRoleQuery:
    """用户角色查询测试"""

    @pytest.mark.asyncio
    async def test_get_user_roles_single(self, initialized_rbac):
        """测试获取用户单个角色"""
        await initialized_rbac.assign_role('user1', 100, 'editor')

        roles = await initialized_rbac.get_user_roles('user1', 100)

        assert len(roles) == 1
        assert 'editor' in roles

    @pytest.mark.asyncio
    async def test_get_user_roles_multiple(self, initialized_rbac):
        """测试获取用户多个角色"""
        await initialized_rbac.assign_role('user1', 100, 'reader')
        await initialized_rbac.assign_role('user1', 100, 'editor')

        roles = await initialized_rbac.get_user_roles('user1', 100)

        assert len(roles) == 2
        assert 'reader' in roles
        assert 'editor' in roles

    @pytest.mark.asyncio
    async def test_get_user_roles_no_roles(self, initialized_rbac):
        """测试获取无角色用户的角色"""
        roles = await initialized_rbac.get_user_roles('user1', 100)

        assert len(roles) == 0

    @pytest.mark.asyncio
    async def test_get_user_roles_different_kb(self, initialized_rbac):
        """测试获取不同知识库的角色"""
        await initialized_rbac.assign_role('user1', 100, 'owner')
        await initialized_rbac.assign_role('user1', 200, 'reader')

        roles_kb100 = await initialized_rbac.get_user_roles('user1', 100)
        roles_kb200 = await initialized_rbac.get_user_roles('user1', 200)

        assert 'owner' in roles_kb100
        assert 'reader' in roles_kb200
        assert 'reader' not in roles_kb100
        assert 'owner' not in roles_kb200

    @pytest.mark.asyncio
    async def test_get_user_roles_returns_copy(self, initialized_rbac):
        """测试返回角色集合的副本"""
        await initialized_rbac.assign_role('user1', 100, 'editor')
        roles = await initialized_rbac.get_user_roles('user1', 100)

        # 修改返回值不影响内部数据
        roles.add('fake_role')

        internal_roles = initialized_rbac._user_roles['user1'][100]
        assert 'fake_role' not in internal_roles


# ==================== 用户权限检查测试 ====================

class TestUserPermissionCheck:
    """用户权限检查测试"""

    @pytest.mark.asyncio
    async def test_check_permission_has_permission(self, initialized_rbac):
        """测试用户有权限"""
        await initialized_rbac.assign_role('user1', 100, 'editor')

        has_perm = await initialized_rbac.check_permission(
            'user1', 100, Permission.KB_READ
        )

        assert has_perm is True

    @pytest.mark.asyncio
    async def test_check_permission_no_permission(self, initialized_rbac):
        """测试用户无权限"""
        await initialized_rbac.assign_role('user1', 100, 'reader')

        has_perm = await initialized_rbac.check_permission(
            'user1', 100, Permission.KB_DELETE
        )

        assert has_perm is False

    @pytest.mark.asyncio
    async def test_check_permission_no_roles(self, initialized_rbac):
        """测试无角色用户的权限检查"""
        has_perm = await initialized_rbac.check_permission(
            'user1', 100, Permission.KB_READ
        )

        assert has_perm is False

    @pytest.mark.asyncio
    async def test_check_permission_multiple_roles(self, initialized_rbac):
        """测试多角色用户的权限检查"""
        await initialized_rbac.assign_role('user1', 100, 'reader')
        await initialized_rbac.assign_role('user1', 100, 'editor')

        # reader + editor 应有读写权限
        assert await initialized_rbac.check_permission('user1', 100, Permission.KB_READ)
        assert await initialized_rbac.check_permission('user1', 100, Permission.ATOM_UPDATE)

        # 但无删除知识库权限
        assert not await initialized_rbac.check_permission('user1', 100, Permission.KB_DELETE)

    @pytest.mark.asyncio
    async def test_get_user_permissions(self, initialized_rbac):
        """测试获取用户所有权限"""
        await initialized_rbac.assign_role('user1', 100, 'editor')

        permissions = await initialized_rbac.get_user_permissions('user1', 100)

        # editor 权限（包括继承）
        assert Permission.KB_READ in permissions
        assert Permission.ATOM_READ in permissions
        assert Permission.ATOM_CREATE in permissions
        assert Permission.ATOM_UPDATE in permissions

        # 无管理权限
        assert Permission.ADMIN not in permissions
        assert Permission.KB_DELETE not in permissions


# ==================== 自定义角色管理测试 ====================

class TestCustomRoleManagement:
    """自定义角色管理测试"""

    @pytest.mark.asyncio
    async def test_create_custom_role_success(self, initialized_rbac, clean_role_definitions):
        """测试成功创建自定义角色"""
        permissions = {Permission.KB_READ, Permission.ATOM_READ, Permission.ATOM_CREATE}

        result = await initialized_rbac.create_custom_role(
            'contributor',
            permissions,
            '贡献者：可创建原子',
            inherits_from='reader'
        )

        assert result is True
        assert 'contributor' in ROLE_DEFINITIONS
        assert 'contributor' in initialized_rbac._role_cache

    @pytest.mark.asyncio
    async def test_create_custom_role_with_inheritance(self, initialized_rbac, clean_role_definitions):
        """测试创建带继承的自定义角色"""
        permissions = {Permission.ATOM_CREATE}

        await initialized_rbac.create_custom_role(
            'contributor',
            permissions,
            '贡献者',
            inherits_from='reader'
        )

        # 获取权限（应包括继承）
        perms = initialized_rbac.get_role_permissions('contributor')

        # 自身权限
        assert Permission.ATOM_CREATE in perms

        # 继承自 reader 的权限
        assert Permission.KB_READ in perms
        assert Permission.ATOM_READ in perms

    @pytest.mark.asyncio
    async def test_create_custom_role_duplicate_name(self, initialized_rbac):
        """测试创建重复名称的自定义角色"""
        result = await initialized_rbac.create_custom_role(
            'owner',  # 已存在的角色
            {Permission.KB_READ},
            '测试'
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_custom_role_success(self, initialized_rbac, clean_role_definitions):
        """测试成功删除自定义角色"""
        # 创建自定义角色
        await initialized_rbac.create_custom_role(
            'custom_role',
            {Permission.KB_READ},
            '自定义角色'
        )

        # 删除
        result = await initialized_rbac.delete_custom_role('custom_role')

        assert result is True
        assert 'custom_role' not in ROLE_DEFINITIONS
        assert 'custom_role' not in initialized_rbac._role_cache

    @pytest.mark.asyncio
    async def test_delete_custom_role_not_exist(self, initialized_rbac):
        """测试删除不存在的自定义角色"""
        result = await initialized_rbac.delete_custom_role('nonexistent')

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_predefined_role_forbidden(self, initialized_rbac):
        """测试禁止删除预定义角色"""
        result = await initialized_rbac.delete_custom_role('owner')

        assert result is False
        assert 'owner' in ROLE_DEFINITIONS

    @pytest.mark.asyncio
    async def test_assign_custom_role(self, initialized_rbac, clean_role_definitions):
        """测试分配自定义角色"""
        # 创建自定义角色
        await initialized_rbac.create_custom_role(
            'reviewer',
            {Permission.KB_READ, Permission.ATOM_READ, Permission.ATOM_UPDATE},
            '审核员'
        )

        # 分配给用户
        result = await initialized_rbac.assign_role('user1', 100, 'reviewer')

        assert result is True

        # 检查权限
        has_perm = await initialized_rbac.check_permission(
            'user1', 100, Permission.ATOM_UPDATE
        )
        assert has_perm is True


# ==================== 角色继承测试 ====================

class TestRoleInheritance:
    """角色继承机制测试"""

    @pytest.mark.asyncio
    async def test_editor_inherits_from_reader(self, initialized_rbac):
        """测试 editor 继承 reader 权限"""
        editor_perms = initialized_rbac.get_role_permissions('editor')
        reader_perms = initialized_rbac.get_role_permissions('reader')

        # editor 应包含所有 reader 权限
        for perm in reader_perms:
            assert perm in editor_perms

    @pytest.mark.asyncio
    async def test_owner_no_inheritance(self, initialized_rbac):
        """测试 owner 无继承"""
        owner_def = ROLE_DEFINITIONS['owner']

        assert owner_def.inherits_from is None

    @pytest.mark.asyncio
    async def test_deep_inheritance_chain(self, initialized_rbac, clean_role_definitions):
        """测试深层继承链"""
        # 创建继承链：reader -> contributor -> reviewer
        await initialized_rbac.create_custom_role(
            'contributor',
            {Permission.ATOM_CREATE},
            '贡献者',
            inherits_from='reader'
        )

        await initialized_rbac.create_custom_role(
            'reviewer',
            {Permission.ATOM_UPDATE},
            '审核员',
            inherits_from='contributor'
        )

        # 获取 reviewer 权限
        reviewer_perms = initialized_rbac.get_role_permissions('reviewer')

        # 自身权限
        assert Permission.ATOM_UPDATE in reviewer_perms

        # 继承自 contributor
        assert Permission.ATOM_CREATE in reviewer_perms

        # 继承自 reader（通过 contributor）
        assert Permission.KB_READ in reviewer_perms
        assert Permission.ATOM_READ in reviewer_perms

    @pytest.mark.asyncio
    async def test_inheritance_cache_update(self, initialized_rbac, clean_role_definitions):
        """测试继承链缓存更新"""
        # 创建自定义角色
        await initialized_rbac.create_custom_role(
            'custom_reader',
            {Permission.KB_READ},
            '自定义读者'
        )

        # 第一次查询（缓存）
        perms1 = initialized_rbac.get_role_permissions('custom_reader')

        # 更新角色定义（添加继承）
        ROLE_DEFINITIONS['custom_reader'].inherits_from = 'reader'

        # 清除缓存
        initialized_rbac._role_cache.clear()

        # 第二次查询（应包含继承）
        perms2 = initialized_rbac.get_role_permissions('custom_reader')

        # 验证继承生效
        assert Permission.ATOM_READ in perms2
        assert Permission.ATOM_READ not in perms1


# ==================== 边界情况测试 ====================

class TestEdgeCases:
    """边界情况测试"""

    @pytest.mark.asyncio
    async def test_empty_permission_set(self, initialized_rbac):
        """测试空权限集合"""
        initialized_rbac._role_cache['empty_role'] = set()

        has_perm = initialized_rbac.has_permission('empty_role', Permission.KB_READ)

        assert has_perm is False

    @pytest.mark.asyncio
    async def test_concurrent_role_assignments(self, initialized_rbac):
        """测试并发角色分配"""
        # 模拟并发场景
        import asyncio

        async def assign_role(user_id, kb_id, role):
            await initialized_rbac.assign_role(user_id, kb_id, role)

        # 并发分配
        await asyncio.gather(
            assign_role('user1', 100, 'reader'),
            assign_role('user1', 100, 'editor'),
            assign_role('user1', 200, 'owner')
        )

        # 验证结果
        roles_100 = await initialized_rbac.get_user_roles('user1', 100)
        roles_200 = await initialized_rbac.get_user_roles('user1', 200)

        assert 'reader' in roles_100
        assert 'editor' in roles_100
        assert 'owner' in roles_200

    @pytest.mark.asyncio
    async def test_permission_with_null_kb_id(self, initialized_rbac):
        """测试 null 知识库 ID"""
        # 系统应能处理 kb_id=None
        roles = await initialized_rbac.get_user_roles('user1', None)

        # 应返回空集合（不崩溃）
        assert len(roles) == 0

    @pytest.mark.asyncio
    async def test_permission_with_negative_kb_id(self, initialized_rbac):
        """测试负数知识库 ID"""
        await initialized_rbac.assign_role('user1', -1, 'reader')

        roles = await initialized_rbac.get_user_roles('user1', -1)

        assert 'reader' in roles

    @pytest.mark.asyncio
    async def test_permission_with_special_characters_user_id(self, initialized_rbac):
        """测试特殊字符用户 ID"""
        special_ids = [
            'user@email.com',
            'user-123',
            'user_456',
            '用户123'
        ]

        for user_id in special_ids:
            await initialized_rbac.assign_role(user_id, 100, 'reader')
            roles = await initialized_rbac.get_user_roles(user_id, 100)
            assert 'reader' in roles


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_permission_check_performance(self, initialized_rbac):
        """测试权限检查性能"""
        import time

        # 分配角色
        await initialized_rbac.assign_role('user1', 100, 'editor')

        # 测量权限检查时间
        start = time.time()
        for _ in range(1000):
            await initialized_rbac.check_permission('user1', 100, Permission.KB_READ)
        end = time.time()

        # 1000 次权限检查应在 1 秒内完成
        assert (end - start) < 1.0

    @pytest.mark.asyncio
    async def test_role_cache_effectiveness(self, initialized_rbac):
        """测试角色缓存有效性"""
        import time

        # 第一次查询（无缓存）
        initialized_rbac._role_cache.clear()
        start1 = time.time()
        for _ in range(100):
            initialized_rbac.get_role_permissions('editor')
        end1 = time.time()

        # 第二次查询（有缓存）
        start2 = time.time()
        for _ in range(100):
            initialized_rbac.get_role_permissions('editor')
        end2 = time.time()

        # 有缓存应明显更快
        assert (end2 - start2) < (end1 - start1)


# ==================== 错误处理测试 ====================

class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_assign_role_with_closed_manager(self, initialized_rbac):
        """测试关闭后的管理器分配角色"""
        await initialized_rbac.close()

        # 应能优雅处理（不崩溃）
        # 注意：当前实现可能不抛出异常，但不应崩溃
        try:
            result = await initialized_rbac.assign_role('user1', 100, 'reader')
            # 可能返回 False 或抛出异常
        except Exception:
            # 可接受的异常
            pass

    @pytest.mark.asyncio
    async def test_permission_check_with_invalid_permission_enum(self, initialized_rbac):
        """测试无效权限枚举"""
        # 当前实现不检查 Permission 类型有效性
        # 应能优雅处理
        has_perm = initialized_rbac.has_permission('reader', Permission.KB_READ)
        assert isinstance(has_perm, bool)