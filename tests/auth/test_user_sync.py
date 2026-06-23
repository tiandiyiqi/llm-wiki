"""UserSyncService 用户同步服务测试."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lib.auth.user_sync import SyncResult, UserSyncService, _generate_slug


def _make_mock_db() -> MagicMock:
    """创建 Mock 数据库管理器."""
    db = MagicMock()
    db.execute_query = AsyncMock(return_value=[{"id": 1}])
    return db


class TestGenerateSlug:
    """_generate_slug 辅助函数测试."""

    def test_simple_name(self):
        assert _generate_slug("My Organization") == "my-organization"

    def test_special_chars(self):
        assert _generate_slug("Org #1! (Test)") == "org-1-test"

    def test_chinese_name(self):
        result = _generate_slug("测试组织")
        assert len(result) > 0

    def test_underscores(self):
        assert _generate_slug("my_org_name") == "my-org-name"

    def test_multiple_spaces(self):
        assert _generate_slug("my   org") == "my-org"

    def test_leading_trailing_hyphens(self):
        assert _generate_slug("-my-org-") == "my-org"

    def test_empty_string(self):
        assert _generate_slug("") == "default"

    def test_long_name_truncated(self):
        long_name = "a" * 200
        assert len(_generate_slug(long_name)) <= 128


class TestUserSyncServiceSyncUser:
    """UserSyncService.sync_user_from_casdoor() 测试."""

    @pytest.mark.asyncio
    async def test_new_user_creation(self):
        db = _make_mock_db()
        db.execute_query = AsyncMock(return_value=[{"is_new": True}])

        service = UserSyncService(db)
        result = await service.sync_user_from_casdoor(
            casdoor_user_id="casdoor-user-1",
            casdoor_user_name="Test User",
            email="test@example.com",
        )

        assert result.user_id == "casdoor-user-1"
        assert result.is_new is True
        assert "user" in result.roles

    @pytest.mark.asyncio
    async def test_existing_user_update(self):
        db = _make_mock_db()
        db.execute_query = AsyncMock(return_value=[{"is_new": False}])

        service = UserSyncService(db)
        result = await service.sync_user_from_casdoor(
            casdoor_user_id="casdoor-user-1",
            casdoor_user_name="Updated Name",
        )

        assert result.is_new is False

    @pytest.mark.asyncio
    async def test_role_mapping_admin(self):
        db = _make_mock_db()
        db.execute_query = AsyncMock(return_value=[{"is_new": True}])

        service = UserSyncService(db)
        result = await service.sync_user_from_casdoor(
            casdoor_user_id="admin-user",
            casdoor_user_name="Admin",
            roles=["admin", "user"],
        )

        assert result.roles == ["admin"]

    @pytest.mark.asyncio
    async def test_role_mapping_member_to_user(self):
        db = _make_mock_db()
        db.execute_query = AsyncMock(return_value=[{"is_new": True}])

        service = UserSyncService(db)
        result = await service.sync_user_from_casdoor(
            casdoor_user_id="member-user",
            casdoor_user_name="Member",
            roles=["member"],
        )

        assert result.roles == ["user"]

    @pytest.mark.asyncio
    async def test_role_mapping_no_roles(self):
        db = _make_mock_db()
        db.execute_query = AsyncMock(return_value=[{"is_new": True}])

        service = UserSyncService(db)
        result = await service.sync_user_from_casdoor(
            casdoor_user_id="no-role-user",
            casdoor_user_name="NoRole",
            roles=None,
        )

        assert result.roles == ["user"]

    @pytest.mark.asyncio
    async def test_with_organization(self):
        db = _make_mock_db()
        # 第一次调用：get_or_create_organization，第二次调用：sync user
        call_count = 0

        async def mock_execute(query, *args):
            nonlocal call_count
            call_count += 1
            if "organizations" in query:
                return [{"id": 42}]
            return [{"is_new": True}]

        db.execute_query = mock_execute

        service = UserSyncService(db)
        result = await service.sync_user_from_casdoor(
            casdoor_user_id="org-user",
            casdoor_user_name="Org User",
            organization="My Org",
        )

        assert result.user_id == "org-user"

    @pytest.mark.asyncio
    async def test_with_department(self):
        db = _make_mock_db()

        async def mock_execute(query, *args):
            if "organizations" in query:
                return [{"id": 42}]
            if "departments" in query:
                return [{"id": 7}]
            return [{"is_new": True}]

        db.execute_query = mock_execute

        service = UserSyncService(db)
        result = await service.sync_user_from_casdoor(
            casdoor_user_id="dept-user",
            casdoor_user_name="Dept User",
            organization="My Org",
            department="Engineering",
        )

        assert result.user_id == "dept-user"

    @pytest.mark.asyncio
    async def test_partial_fields_missing(self):
        db = _make_mock_db()
        db.execute_query = AsyncMock(return_value=[{"is_new": True}])

        service = UserSyncService(db)
        result = await service.sync_user_from_casdoor(
            casdoor_user_id="minimal-user",
            casdoor_user_name="Minimal",
            email=None,
            phone=None,
            organization=None,
        )

        assert result.user_id == "minimal-user"
        assert result.is_new is True


class TestUserSyncServiceOrgDept:
    """UserSyncService 组织和部门管理测试."""

    @pytest.mark.asyncio
    async def test_get_or_create_organization_new(self):
        db = _make_mock_db()
        db.execute_query = AsyncMock(return_value=[{"id": 1}])

        service = UserSyncService(db)
        org_id = await service.get_or_create_organization("New Org")

        assert org_id == 1

    @pytest.mark.asyncio
    async def test_get_or_create_department_new(self):
        db = _make_mock_db()
        db.execute_query = AsyncMock(return_value=[{"id": 5}])

        service = UserSyncService(db)
        dept_id = await service.get_or_create_department(org_id=1, dept_name="Engineering")

        assert dept_id == 5


class TestUserSyncServiceUpdateLastLogin:
    """UserSyncService.update_last_login() 测试."""

    @pytest.mark.asyncio
    async def test_update_last_login(self):
        db = _make_mock_db()
        db.execute_query = AsyncMock(return_value=[])

        service = UserSyncService(db)
        await service.update_last_login("user-1")

        db.execute_query.assert_called_once()
        query = db.execute_query.call_args[0][0]
        assert "last_login_at" in query
        assert "NOW()" in query
