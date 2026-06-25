"""RBAC 持久化功能测试."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from lib.auth.rbac import RBACManager, Role, Permission


class TestRBACPersistence:
    """测试 RBAC 持久化功能."""

    @pytest.fixture
    def mock_db_manager(self):
        """创建模拟数据库管理器."""
        db_manager = AsyncMock()
        db_manager.execute = AsyncMock()
        db_manager.fetch_all = AsyncMock()
        return db_manager

    @pytest.mark.asyncio
    async def test_assign_role_with_database(self, mock_db_manager):
        """测试分配角色写入数据库."""
        rbac = RBACManager(db_manager=mock_db_manager)
        await rbac.initialize()

        # 分配角色
        result = await rbac.assign_role('user1', 1, 'editor')

        # 验证成功
        assert result is True

        # 验证数据库写入
        mock_db_manager.execute.assert_called_once()
        call_args = mock_db_manager.execute.call_args
        assert 'INSERT INTO kb_members' in call_args[0][0]
        assert call_args[0][1] == 1  # kb_id
        assert call_args[0][2] == 'user1'
        assert call_args[0][3] == 'editor'

    @pytest.mark.asyncio
    async def test_assign_role_without_database(self):
        """测试分配角色不使用数据库."""
        rbac = RBACManager(db_manager=None)
        await rbac.initialize()

        # 分配角色
        result = await rbac.assign_role('user1', 1, 'editor')

        # 验证成功
        assert result is True

        # 验证内存缓存
        roles = await rbac.get_user_roles('user1', 1)
        assert 'editor' in roles

    @pytest.mark.asyncio
    async def test_revoke_role_from_database(self, mock_db_manager):
        """测试撤销角色从数据库删除."""
        rbac = RBACManager(db_manager=mock_db_manager)
        await rbac.initialize()

        # 先分配角色
        await rbac.assign_role('user1', 1, 'editor')

        # 撤销角色
        result = await rbac.revoke_role('user1', 1, 'editor')

        # 验证成功
        assert result is True

        # 验证数据库删除
        assert mock_db_manager.execute.call_count == 2  # 1 insert + 1 delete

    @pytest.mark.asyncio
    async def test_get_user_roles_from_database(self, mock_db_manager):
        """测试从数据库加载用户角色."""
        # 模拟数据库返回
        mock_db_manager.fetch_all.return_value = [
            {'role': 'owner'},
            {'role': 'editor'}
        ]

        rbac = RBACManager(db_manager=mock_db_manager)
        await rbac.initialize()

        # 获取角色（应从数据库加载）
        roles = await rbac.get_user_roles('user1', 1, force_reload=True)

        # 验证角色
        assert 'owner' in roles
        assert 'editor' in roles

        # 验证数据库查询
        mock_db_manager.fetch_all.assert_called()
        call_args = mock_db_manager.fetch_all.call_args
        assert 'SELECT role FROM kb_members' in call_args[0][0]

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, mock_db_manager):
        """测试缓存失效."""
        rbac = RBACManager(db_manager=mock_db_manager)
        await rbac.initialize()

        # 分配角色
        await rbac.assign_role('user1', 1, 'editor')

        # 验证缓存
        roles = await rbac.get_user_roles('user1', 1)
        assert 'editor' in roles

        # 使缓存失效
        await rbac.invalidate_user_cache('user1')

        # 模拟数据库返回空
        mock_db_manager.fetch_all.return_value = []

        # 强制重新加载
        roles = await rbac.get_user_roles('user1', 1, force_reload=True)

        # 验证缓存已清除（从数据库重新加载）
        assert len(roles) == 0

    @pytest.mark.asyncio
    async def test_restart_persistence(self, mock_db_manager):
        """测试重启后角色保留."""
        # 模拟数据库中已有角色
        mock_db_manager.fetch_all.return_value = [
            {'user_id': 'user1', 'kb_id': 1, 'role': 'owner'},
            {'user_id': 'user2', 'kb_id': 1, 'role': 'editor'},
        ]

        # 创建新的 RBAC 实例（模拟重启）
        rbac = RBACManager(db_manager=mock_db_manager)
        await rbac.initialize()

        # 验证从数据库加载的角色
        roles_user1 = await rbac.get_user_roles('user1', 1)
        roles_user2 = await rbac.get_user_roles('user2', 1)

        assert 'owner' in roles_user1
        assert 'editor' in roles_user2

    @pytest.mark.asyncio
    async def test_kb_cache_invalidation(self, mock_db_manager):
        """测试知识库缓存失效."""
        rbac = RBACManager(db_manager=mock_db_manager)
        await rbac.initialize()

        # 分配多个用户的角色
        await rbac.assign_role('user1', 1, 'owner')
        await rbac.assign_role('user2', 1, 'editor')

        # 使 KB 缓存失效
        await rbac.invalidate_kb_cache(1)

        # 验证所有用户的缓存都已清除
        assert 'user1' not in rbac._user_roles or 1 not in rbac._user_roles.get('user1', {})
        assert 'user2' not in rbac._user_roles or 1 not in rbac._user_roles.get('user2', {})

    @pytest.mark.asyncio
    async def test_database_error_handling(self, mock_db_manager):
        """测试数据库错误处理."""
        # 模拟数据库错误
        mock_db_manager.execute.side_effect = Exception("Database error")

        rbac = RBACManager(db_manager=mock_db_manager)
        await rbac.initialize()

        # 尝试分配角色（应失败但不崩溃）
        result = await rbac.assign_role('user1', 1, 'editor')

        # 验证失败
        assert result is False

    @pytest.mark.asyncio
    async def test_concurrent_role_operations(self, mock_db_manager):
        """测试并发角色操作."""
        rbac = RBACManager(db_manager=mock_db_manager)
        await rbac.initialize()

        # 并发分配多个角色
        await rbac.assign_role('user1', 1, 'owner')
        await rbac.assign_role('user1', 1, 'editor')

        # 验证两个角色都存在
        roles = await rbac.get_user_roles('user1', 1)
        assert 'owner' in roles
        assert 'editor' in roles


class TestRBACManagerInit:
    """测试 RBAC 管理器初始化."""

    def test_init_without_database(self):
        """测试不使用数据库初始化."""
        rbac = RBACManager(db_manager=None)
        assert rbac._db_manager is None
        assert rbac._user_roles == {}

    def test_init_with_database(self):
        """测试使用数据库初始化."""
        mock_db = Mock()
        rbac = RBACManager(db_manager=mock_db)
        assert rbac._db_manager == mock_db

    @pytest.mark.asyncio
    async def test_initialize_loads_roles(self):
        """测试初始化加载角色."""
        rbac = RBACManager(db_manager=None)
        await rbac.initialize()

        # 验证预定义角色已加载
        assert 'owner' in rbac._role_cache
        assert 'editor' in rbac._role_cache
        assert 'reader' in rbac._role_cache
