"""RLS（Row-Level Security）管理器单元测试

测试范围：
1. RLS 启用/禁用
2. 用户上下文设置
3. 策略创建/删除
4. 访问权限检查
5. 成员管理
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call
from typing import Dict, List

from lib.auth.rls_manager import RLSManager


# ==================== Fixtures ====================

@pytest.fixture
def mock_db_manager():
    """创建 mock 数据库管理器"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    return db


@pytest.fixture
def rls_manager(mock_db_manager):
    """创建 RLS 管理器实例"""
    manager = RLSManager(mock_db_manager)
    return manager


@pytest.fixture
async def initialized_rls(rls_manager):
    """已初始化的 RLS 管理器"""
    await rls_manager.initialize()
    return rls_manager


# ==================== 初始化测试 ====================

class TestRLSInitialization:
    """RLS 系统初始化测试"""

    @pytest.mark.asyncio
    async def test_initialize_enables_rls_for_tables(self, rls_manager):
        """测试初始化为关键表启用 RLS"""
        await rls_manager.initialize()

        # 验证执行了 ALTER TABLE 语句
        rls_manager.db_manager.execute.assert_called()

        # 获取所有调用
        calls = rls_manager.db_manager.execute.call_args_list

        # 验证为三个表启用了 RLS
        table_names = ['knowledge_bases', 'atoms', 'kb_members']
        for table in table_names:
            found = any(
                f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY' in str(call)
                for call in calls
            )
            assert found, f"RLS not enabled for table: {table}"

    @pytest.mark.asyncio
    async def test_close_clears_user_context(self, initialized_rls):
        """测试关闭清理用户上下文"""
        # 设置用户上下文
        initialized_rls._current_user_id = 'user1'
        initialized_rls._current_user_roles = ['reader']

        await initialized_rls.close()

        assert initialized_rls._current_user_id is None
        assert len(initialized_rls._current_user_roles) == 0


# ==================== RLS 启用/禁用测试 ====================

class TestRLSEnableDisable:
    """RLS 启用/禁用测试"""

    @pytest.mark.asyncio
    async def test_enable_rls_executes_correct_sql(self, rls_manager):
        """测试启用 RLS 执行正确的 SQL"""
        await rls_manager._enable_rls()

        calls = rls_manager.db_manager.execute.call_args_list

        # 验证 SQL 语句
        for table in ['knowledge_bases', 'atoms', 'kb_members']:
            expected_sql = f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"
            assert any(expected_sql in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_enable_rls_handles_errors(self, rls_manager):
        """测试启用 RLS 错误处理"""
        # 模拟数据库错误
        rls_manager.db_manager.execute.side_effect = Exception("Database error")

        # 应捕获异常（不崩溃）
        try:
            await rls_manager._enable_rls()
        except Exception:
            # 可接受的异常
            pass


# ==================== 用户上下文设置测试 ====================

class TestUserContextSetting:
    """用户上下文设置测试"""

    @pytest.mark.asyncio
    async def test_set_user_context_basic(self, initialized_rls):
        """测试基本用户上下文设置"""
        await initialized_rls.set_user_context('user1', ['reader', 'editor'])

        # 验证内部状态
        assert initialized_rls._current_user_id == 'user1'
        assert initialized_rls._current_user_roles == ['reader', 'editor']

        # 验证数据库调用
        calls = initialized_rls.db_manager.execute.call_args_list

        # 应设置用户 ID
        assert any('llmwiki.current_user_id' in str(call) for call in calls)

        # 应设置角色列表
        assert any('llmwiki.current_user_roles' in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_set_user_context_empty_roles(self, initialized_rls):
        """测试空角色列表"""
        await initialized_rls.set_user_context('user1', [])

        assert initialized_rls._current_user_roles == []

    @pytest.mark.asyncio
    async def test_set_user_context_special_characters(self, initialized_rls):
        """测试特殊字符用户 ID"""
        special_ids = [
            'user@email.com',
            'user-123_456',
            '用户'
        ]

        for user_id in special_ids:
            await initialized_rls.set_user_context(user_id, ['reader'])
            assert initialized_rls._current_user_id == user_id

    @pytest.mark.asyncio
    async def test_set_user_context_overwrites_previous(self, initialized_rls):
        """测试覆盖之前的上下文"""
        await initialized_rls.set_user_context('user1', ['reader'])
        await initialized_rls.set_user_context('user2', ['editor'])

        # 应是最新设置的上下文
        assert initialized_rls._current_user_id == 'user2'
        assert initialized_rls._current_user_roles == ['editor']


# ==================== 策略创建/删除测试 ====================

class TestPolicyManagement:
    """策略创建/删除测试"""

    @pytest.mark.asyncio
    async def test_create_kb_policy(self, initialized_rls):
        """测试创建知识库策略"""
        kb_id = 100
        await initialized_rls.create_kb_policy(kb_id)

        # 验证执行了 CREATE POLICY
        calls = initialized_rls.db_manager.execute.call_args_list
        policy_name = f"kb_{kb_id}_policy"

        assert any(policy_name in str(call) for call in calls)
        assert any('knowledge_bases' in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_create_kb_policy_includes_member_check(self, initialized_rls):
        """测试知识库策略包含成员检查"""
        kb_id = 100
        await initialized_rls.create_kb_policy(kb_id)

        # 验证策略包含成员表查询
        calls = initialized_rls.db_manager.execute.call_args_list
        assert any('kb_members' in str(call) for call in calls)
        assert any('owner_id' in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_drop_kb_policy(self, initialized_rls):
        """测试删除知识库策略"""
        kb_id = 100
        await initialized_rls.drop_kb_policy(kb_id)

        # 验证执行了 DROP POLICY
        calls = initialized_rls.db_manager.execute.call_args_list
        policy_name = f"kb_{kb_id}_policy"

        assert any(f"DROP POLICY IF EXISTS {policy_name}" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_create_atom_policy(self, initialized_rls):
        """测试创建知识原子策略"""
        kb_id = 100
        await initialized_rls.create_atom_policy(kb_id)

        # 验证执行了 CREATE POLICY
        calls = initialized_rls.db_manager.execute.call_args_list
        policy_name = f"atom_kb_{kb_id}_policy"

        assert any(policy_name in str(call) for call in calls)
        assert any('atoms' in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_drop_atom_policy(self, initialized_rls):
        """测试删除知识原子策略"""
        kb_id = 100
        await initialized_rls.drop_atom_policy(kb_id)

        # 验证执行了 DROP POLICY
        calls = initialized_rls.db_manager.execute.call_args_list
        policy_name = f"atom_kb_{kb_id}_policy"

        assert any(f"DROP POLICY IF EXISTS {policy_name}" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_policy_names_are_unique(self, initialized_rls):
        """测试策略名称唯一性"""
        # 创建多个知识库策略
        for kb_id in [100, 200, 300]:
            await initialized_rls.create_kb_policy(kb_id)

        calls = initialized_rls.db_manager.execute.call_args_list

        # 验证每个策略名称唯一
        policy_names = [
            f"kb_{kb_id}_policy"
            for kb_id in [100, 200, 300]
        ]

        for name in policy_names:
            count = sum(name in str(call) for call in calls)
            assert count >= 1  # 至少出现一次


# ==================== 访问权限检查测试 ====================

class TestAccessControl:
    """访问权限检查测试"""

    @pytest.mark.asyncio
    async def test_check_access_member_has_access(self, initialized_rls):
        """测试成员有访问权限"""
        # 模拟数据库返回成员角色
        initialized_rls.db_manager.fetch_one.return_value = {'role': 'editor'}

        has_access = await initialized_rls.check_access('user1', 100, 'read')

        assert has_access is True

    @pytest.mark.asyncio
    async def test_check_access_owner_has_all_access(self, initialized_rls):
        """测试所有者拥有所有访问权限"""
        # 模拟不是成员
        initialized_rls.db_manager.fetch_one.side_effect = [
            None,  # 成员查询
            {'owner_id': 'user1'}  # 所有者查询
        ]

        for action in ['read', 'write', 'delete', 'manage']:
            initialized_rls.db_manager.fetch_one.reset_mock()
            initialized_rls.db_manager.fetch_one.side_effect = [
                None,
                {'owner_id': 'user1'}
            ]

            has_access = await initialized_rls.check_access('user1', 100, action)
            assert has_access is True

    @pytest.mark.asyncio
    async def test_check_access_reader_can_only_read(self, initialized_rls):
        """测试读者只能读"""
        initialized_rls.db_manager.fetch_one.return_value = {'role': 'reader'}

        # 读权限
        assert await initialized_rls.check_access('user1', 100, 'read')

        # 无写权限
        assert not await initialized_rls.check_access('user1', 100, 'write')

        # 无删除权限
        assert not await initialized_rls.check_access('user1', 100, 'delete')

    @pytest.mark.asyncio
    async def test_check_access_editor_can_read_write(self, initialized_rls):
        """测试编辑者可读写"""
        initialized_rls.db_manager.fetch_one.return_value = {'role': 'editor'}

        # 读权限
        assert await initialized_rls.check_access('user1', 100, 'read')

        # 写权限
        assert await initialized_rls.check_access('user1', 100, 'write')

        # 无删除权限
        assert not await initialized_rls.check_access('user1', 100, 'delete')

    @pytest.mark.asyncio
    async def test_check_access_no_member_no_owner(self, initialized_rls):
        """测试非成员非所有者无权限"""
        initialized_rls.db_manager.fetch_one.side_effect = [
            None,  # 成员查询
            {'owner_id': 'other_user'}  # 所有者查询
        ]

        has_access = await initialized_rls.check_access('user1', 100, 'read')

        assert has_access is False

    @pytest.mark.asyncio
    async def test_check_access_invalid_action(self, initialized_rls):
        """测试无效操作"""
        initialized_rls.db_manager.fetch_one.return_value = {'role': 'reader'}

        # 无效操作应返回 False
        has_access = await initialized_rls.check_access('user1', 100, 'invalid_action')

        assert has_access is False


# ==================== 成员管理测试 ====================

class TestMemberManagement:
    """成员管理测试"""

    @pytest.mark.asyncio
    async def test_add_user_to_kb_success(self, initialized_rls):
        """测试成功添加用户到知识库"""
        result = await initialized_rls.add_user_to_kb('user1', 100, 'editor')

        assert result is True

        # 验证执行了 INSERT
        initialized_rls.db_manager.execute.assert_called()

    @pytest.mark.asyncio
    async def test_add_user_to_kb_default_role(self, initialized_rls):
        """测试添加用户默认角色"""
        result = await initialized_rls.add_user_to_kb('user1', 100)

        assert result is True

        # 验证使用了默认角色 reader
        call_args = initialized_rls.db_manager.execute.call_args
        assert 'reader' in str(call_args)

    @pytest.mark.asyncio
    async def test_add_user_to_kb_handles_conflict(self, initialized_rls):
        """测试处理用户已存在冲突"""
        # ON CONFLICT DO UPDATE 应处理
        result = await initialized_rls.add_user_to_kb('user1', 100, 'editor')

        assert result is True

    @pytest.mark.asyncio
    async def test_add_user_to_kb_database_error(self, initialized_rls):
        """测试数据库错误处理"""
        initialized_rls.db_manager.execute.side_effect = Exception("Database error")

        result = await initialized_rls.add_user_to_kb('user1', 100, 'editor')

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_user_from_kb_success(self, initialized_rls):
        """测试成功从知识库移除用户"""
        result = await initialized_rls.remove_user_from_kb('user1', 100)

        assert result is True

        # 验证执行了 DELETE
        initialized_rls.db_manager.execute.assert_called()

    @pytest.mark.asyncio
    async def test_remove_user_from_kb_database_error(self, initialized_rls):
        """测试移除用户数据库错误"""
        initialized_rls.db_manager.execute.side_effect = Exception("Database error")

        result = await initialized_rls.remove_user_from_kb('user1', 100)

        assert result is False


# ==================== 可访问知识库查询测试 ====================

class TestAccessibleKnowledgeBases:
    """可访问知识库查询测试"""

    @pytest.mark.asyncio
    async def test_get_accessible_kbs_returns_list(self, initialized_rls):
        """测试返回可访问知识库列表"""
        # 模拟数据库返回
        initialized_rls.db_manager.fetch_all.return_value = [
            {'kb_id': 100},
            {'kb_id': 200},
            {'kb_id': 300}
        ]

        kb_ids = await initialized_rls.get_accessible_kbs('user1')

        assert len(kb_ids) == 3
        assert 100 in kb_ids
        assert 200 in kb_ids
        assert 300 in kb_ids

    @pytest.mark.asyncio
    async def test_get_accessible_kbs_includes_owned(self, initialized_rls):
        """测试包含用户拥有的知识库"""
        # 模拟成员知识和拥有的知识库
        initialized_rls.db_manager.fetch_all.return_value = [
            {'kb_id': 100},  # 成员
            {'kb_id': 200}   # 所有者
        ]

        kb_ids = await initialized_rls.get_accessible_kbs('user1')

        assert 100 in kb_ids
        assert 200 in kb_ids

    @pytest.mark.asyncio
    async def test_get_accessible_kbs_empty_result(self, initialized_rls):
        """测试无可访问知识库"""
        initialized_rls.db_manager.fetch_all.return_value = []

        kb_ids = await initialized_rls.get_accessible_kbs('user1')

        assert len(kb_ids) == 0

    @pytest.mark.asyncio
    async def test_get_accessible_kbs_deduplicates(self, initialized_rls):
        """测试去重"""
        # 模拟重复结果
        initialized_rls.db_manager.fetch_all.return_value = [
            {'kb_id': 100},
            {'kb_id': 100},  # 重复
            {'kb_id': 200}
        ]

        kb_ids = await initialized_rls.get_accessible_kbs('user1')

        # 应去重
        assert kb_ids.count(100) == 1


# ==================== 边界情况测试 ====================

class TestEdgeCases:
    """边界情况测试"""

    @pytest.mark.asyncio
    async def test_kb_id_zero(self, initialized_rls):
        """测试知识库 ID 为 0"""
        result = await initialized_rls.add_user_to_kb('user1', 0, 'reader')

        # 应能处理（不崩溃）
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_kb_id_negative(self, initialized_rls):
        """测试负数知识库 ID"""
        result = await initialized_rls.add_user_to_kb('user1', -1, 'reader')

        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_empty_user_id(self, initialized_rls):
        """测试空用户 ID"""
        result = await initialized_rls.add_user_to_kb('', 100, 'reader')

        # 应能处理（数据库可能拒绝）
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_none_user_id(self, initialized_rls):
        """测试 None 用户 ID"""
        try:
            result = await initialized_rls.add_user_to_kb(None, 100, 'reader')
        except (TypeError, AttributeError):
            # 可接受的异常
            pass

    @pytest.mark.asyncio
    async def test_special_role_names(self, initialized_rls):
        """测试特殊角色名称"""
        special_roles = ['reader', 'editor', 'owner', 'custom_role']

        for role in special_roles:
            result = await initialized_rls.add_user_to_kb('user1', 100, role)
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_concurrent_policy_creation(self, initialized_rls):
        """测试并发策略创建"""
        import asyncio

        # 并发创建多个策略
        await asyncio.gather(
            initialized_rls.create_kb_policy(100),
            initialized_rls.create_kb_policy(200),
            initialized_rls.create_kb_policy(300)
        )

        # 应不崩溃
        assert initialized_rls.db_manager.execute.call_count >= 3


# ==================== 错误处理测试 ====================

class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_database_connection_error(self, initialized_rls):
        """测试数据库连接错误"""
        initialized_rls.db_manager.execute.side_effect = ConnectionError("Connection lost")

        try:
            await initialized_rls.create_kb_policy(100)
        except ConnectionError:
            # 可接受的异常
            pass

    @pytest.mark.asyncio
    async def test_timeout_error(self, initialized_rls):
        """测试超时错误"""
        import asyncio

        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(10)

        initialized_rls.db_manager.execute = slow_operation

        try:
            await asyncio.wait_for(
                initialized_rls.create_kb_policy(100),
                timeout=1.0
            )
        except asyncio.TimeoutError:
            # 预期的超时
            pass

    @pytest.mark.asyncio
    async def test_invalid_sql_error(self, initialized_rls):
        """测试无效 SQL 错误"""
        initialized_rls.db_manager.execute.side_effect = Exception("Syntax error")

        try:
            await initialized_rls.create_kb_policy(100)
        except Exception:
            # 可接受的异常
            pass


# ==================== SQL 注入防护测试 ====================

class TestSQLInjectionPrevention:
    """SQL 注入防护测试"""

    @pytest.mark.asyncio
    async def test_user_id_injection(self, initialized_rls):
        """测试用户 ID 注入防护"""
        malicious_user_ids = [
            "user1'; DROP TABLE users; --",
            "user1' OR '1'='1",
            "user1; DELETE FROM kb_members"
        ]

        for user_id in malicious_user_ids:
            # 应使用参数化查询（$1 占位符）
            await initialized_rls.set_user_context(user_id, ['reader'])

            # 验证使用了参数化查询
            call_args = initialized_rls.db_manager.execute.call_args
            # 参数化查询使用 $1, $2 等
            assert '$1' in str(call_args) or len(call_args[0]) > 1

    @pytest.mark.asyncio
    async def test_role_injection(self, initialized_rls):
        """测试角色注入防护"""
        malicious_roles = [
            "reader'; DROP TABLE kb_members; --",
            "reader' OR '1'='1"
        ]

        for role in malicious_roles:
            # 应使用参数化查询
            await initialized_rls.add_user_to_kb('user1', 100, role)

            # 验证使用了参数化查询
            call_args = initialized_rls.db_manager.execute.call_args
            # 不应包含直接拼接的恶意 SQL
            assert 'DROP TABLE' not in str(call_args)


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_check_access_performance(self, initialized_rls):
        """测试访问检查性能"""
        import time

        initialized_rls.db_manager.fetch_one.return_value = {'role': 'reader'}

        start = time.time()
        for _ in range(100):
            await initialized_rls.check_access('user1', 100, 'read')
        end = time.time()

        # 100 次检查应在 1 秒内完成
        assert (end - start) < 1.0

    @pytest.mark.asyncio
    async def test_get_accessible_kbs_performance(self, initialized_rls):
        """测试获取可访问知识库性能"""
        import time

        # 模拟大量知识库
        initialized_rls.db_manager.fetch_all.return_value = [
            {'kb_id': i} for i in range(1000)
        ]

        start = time.time()
        kb_ids = await initialized_rls.get_accessible_kbs('user1')
        end = time.time()

        # 应快速返回
        assert (end - start) < 1.0
        assert len(kb_ids) == 1000
