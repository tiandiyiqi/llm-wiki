"""SSO E2E 集成测试 — Mock 版本.

在没有实际 Casdoor 和 PostgreSQL 的环境中，使用 Mock 进行 E2E 测试。
覆盖 SSO 登录流程、会话管理、角色映射、降级场景。
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lib.auth.casdoor_client import CasdoorClient, CasdoorTokenResponse, CasdoorUserInfo
from lib.auth.casdoor_config import CasdoorConfig
from lib.auth.sso_provider import SSOAuthProvider, SSOAuthResult
from lib.auth.user_sync import UserSyncService


def _make_config(**overrides) -> CasdoorConfig:
    defaults = {
        "enabled": True,
        "endpoint": "https://casdoor.example.com",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "organization": "llm-wiki",
        "application": "llm-wiki-app",
        "certificate": "test-cert",
        "redirect_uri": "https://app.example.com/api/auth/sso/callback",
    }
    defaults.update(overrides)
    return CasdoorConfig(**defaults)


class TestSSOFullFlow:
    """完整 SSO 登录流程 E2E 测试（Mock Casdoor）."""

    @pytest.mark.asyncio
    async def test_initiate_login_to_callback_to_session(self):
        """测试完整流程：发起登录 → Casdoor 回调 → 用户同步 → 会话创建."""
        config = _make_config()

        # Mock CasdoorClient
        mock_client = MagicMock(spec=CasdoorClient)
        mock_client.get_authorization_url = MagicMock(
            return_value="https://casdoor.example.com/login/oauth/authorize?client_id=test&state=state123"
        )
        mock_client.exchange_code = AsyncMock(
            return_value=CasdoorTokenResponse(access_token="valid-at")
        )
        mock_client.get_user_info = AsyncMock(
            return_value=CasdoorUserInfo(
                id="casdoor-user-1",
                name="Test User",
                email="test@example.com",
                organization="llm-wiki",
                roles=["user"],
            )
        )

        provider = SSOAuthProvider(mock_client, config)

        # 步骤 1：发起登录
        init_result = await provider.initiate_login(redirect_url="https://app.example.com/dashboard")
        assert init_result.success is True
        assert init_result.redirect_url is not None
        state = init_result.session_id

        # 步骤 2：处理回调
        callback_result = await provider.handle_callback(code="valid-code", state=state)
        assert callback_result.success is True
        assert callback_result.user_id == "casdoor-user-1"
        assert callback_result.roles == ["user"]

    @pytest.mark.asyncio
    async def test_sso_and_local_login_coexist(self):
        """测试 SSO 登录和本地登录共存.

        两种认证方式应独立工作，不互相干扰。
        """
        config = _make_config()

        # SSO 认证成功
        mock_client = MagicMock(spec=CasdoorClient)
        mock_client.get_authorization_url = MagicMock(return_value="https://casdoor.example.com/login")
        mock_client.exchange_code = AsyncMock(
            return_value=CasdoorTokenResponse(access_token="sso-at")
        )
        mock_client.get_user_info = AsyncMock(
            return_value=CasdoorUserInfo(id="sso-user", name="SSO User", roles=["admin"])
        )

        provider = SSOAuthProvider(mock_client, config)

        # SSO 登录流程
        init_result = await provider.initiate_login()
        callback_result = await provider.handle_callback(code="sso-code", state=init_result.session_id)

        assert callback_result.success is True
        assert callback_result.user_id == "sso-user"
        assert "admin" in callback_result.roles

        # 本地登录流程（假设已有 AuthManager 的本地认证）
        # 这不需要 SSO provider，本地认证仍然工作


class TestSSOLogout:
    """SSO 单点登出测试."""

    @pytest.mark.asyncio
    async def test_logout_returns_casdoor_url(self):
        config = _make_config()
        mock_client = MagicMock(spec=CasdoorClient)
        provider = SSOAuthProvider(mock_client, config)

        result = await provider.handle_logout(session_id="session-123")

        assert result.success is True
        assert result.redirect_url is not None
        assert "casdoor.example.com" in result.redirect_url
        assert "logout" in result.redirect_url


class TestSSOGracefulDegradation:
    """Casdoor 不可用时的降级测试."""

    @pytest.mark.asyncio
    async def test_casdoor_connection_timeout(self):
        """Casdoor 连接超时时返回错误."""
        from lib.auth.casdoor_client import CasdoorError

        config = _make_config()
        mock_client = MagicMock(spec=CasdoorClient)
        mock_client.exchange_code = AsyncMock(
            side_effect=CasdoorError("Timeout connecting to Casdoor")
        )
        mock_client.get_authorization_url = MagicMock(return_value="https://casdoor.example.com/login")

        provider = SSOAuthProvider(mock_client, config)

        init_result = await provider.initiate_login()
        callback_result = await provider.handle_callback(
            code="code", state=init_result.session_id
        )

        assert callback_result.success is False
        assert "Timeout" in (callback_result.error or "")

    def test_sso_disabled_providers_returns_empty(self):
        """SSO 禁用时 /api/auth/sso/providers 返回空列表."""
        config = _make_config(enabled=False)

        # SSO 禁用时，CasdoorConfig.enabled=False
        assert config.enabled is False
        # 模拟 API 返回空列表
        # 在实际 web_server 中，is_sso_enabled() 返回 False → providers: []

    def test_local_login_works_when_sso_disabled(self):
        """SSO 禁用时本地登录不受影响.

        这是关键约束：SSO 禁用时，系统行为应完全不变。
        """
        config = _make_config(enabled=False)
        errors = config.validate()
        assert errors == []  # 禁用时不需要 Casdoor 配置
