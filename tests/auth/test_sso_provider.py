"""SSOAuthProvider 认证提供者测试."""

import secrets
from unittest.mock import AsyncMock, MagicMock

import pytest

from lib.auth.casdoor_client import CasdoorClient, CasdoorError, CasdoorUserInfo
from lib.auth.casdoor_config import CasdoorConfig
from lib.auth.sso_provider import SSOAuthProvider, SSOAuthResult


def _make_config(**overrides) -> CasdoorConfig:
    """创建测试用 CasdoorConfig."""
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


def _make_mock_client() -> MagicMock:
    """创建 Mock CasdoorClient."""
    client = MagicMock(spec=CasdoorClient)
    client.get_authorization_url = MagicMock(return_value="https://casdoor.example.com/login/oauth/authorize?client_id=test")
    client.exchange_code = AsyncMock()
    client.get_user_info = AsyncMock()
    client.validate_jwt = AsyncMock(return_value=None)
    return client


class TestInitiateLogin:
    """SSOAuthProvider.initiate_login() 测试."""

    @pytest.mark.asyncio
    async def test_returns_valid_url_and_state(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        result = await provider.initiate_login()

        assert result.success is True
        assert result.redirect_url is not None
        assert result.session_id is not None  # session_id 持有 state
        assert len(result.session_id) > 10  # state 有足够长度

    @pytest.mark.asyncio
    async def test_state_stored_in_memory(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        result = await provider.initiate_login(redirect_url="https://app.example.com/dashboard")

        state = result.session_id
        # state 应存入内存
        assert state in provider._memory_store
        assert provider._memory_store[state] == "https://app.example.com/dashboard"

    @pytest.mark.asyncio
    async def test_authorization_url_called_with_state(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        result = await provider.initiate_login()

        client.get_authorization_url.assert_called_once()
        called_state = client.get_authorization_url.call_args[0][0]
        assert called_state == result.session_id


class TestHandleCallback:
    """SSOAuthProvider.handle_callback() 测试."""

    @pytest.mark.asyncio
    async def test_success_flow(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        # 先发起登录以存储 state
        init_result = await provider.initiate_login()
        state = init_result.session_id

        # Mock exchange_code 和 get_user_info
        from lib.auth.casdoor_client import CasdoorTokenResponse
        client.exchange_code = AsyncMock(return_value=CasdoorTokenResponse(
            access_token="valid-at",
        ))
        client.get_user_info = AsyncMock(return_value=CasdoorUserInfo(
            id="casdoor-user-1",
            name="testuser",
            roles=["user"],
        ))

        result = await provider.handle_callback(code="valid-code", state=state)

        assert result.success is True
        assert result.user_id == "casdoor-user-1"
        assert result.roles == ["user"]

    @pytest.mark.asyncio
    async def test_invalid_state_csrf_protection(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        result = await provider.handle_callback(code="valid-code", state="invalid-state")

        assert result.success is False
        assert "Invalid or expired state" in (result.error or "")

    @pytest.mark.asyncio
    async def test_code_exchange_failure(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        # 先存储有效 state
        init_result = await provider.initiate_login()
        state = init_result.session_id

        client.exchange_code = AsyncMock(side_effect=CasdoorError("exchange failed", status_code=401))

        result = await provider.handle_callback(code="bad-code", state=state)

        assert result.success is False
        assert "Code exchange failed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_get_user_info_failure(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        init_result = await provider.initiate_login()
        state = init_result.session_id

        from lib.auth.casdoor_client import CasdoorTokenResponse
        client.exchange_code = AsyncMock(return_value=CasdoorTokenResponse(access_token="valid-at"))
        client.get_user_info = AsyncMock(side_effect=CasdoorError("user info failed"))

        result = await provider.handle_callback(code="valid-code", state=state)

        assert result.success is False
        assert "user info" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_empty_access_token(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        init_result = await provider.initiate_login()
        state = init_result.session_id

        from lib.auth.casdoor_client import CasdoorTokenResponse
        client.exchange_code = AsyncMock(return_value=CasdoorTokenResponse(access_token=""))

        result = await provider.handle_callback(code="valid-code", state=state)

        assert result.success is False
        assert "empty access token" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_state_consumed_after_use(self):
        """回调后 state 应被删除（单次使用）."""
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        init_result = await provider.initiate_login()
        state = init_result.session_id

        from lib.auth.casdoor_client import CasdoorTokenResponse
        client.exchange_code = AsyncMock(return_value=CasdoorTokenResponse(access_token="at"))
        client.get_user_info = AsyncMock(return_value=CasdoorUserInfo(id="user-1"))

        # 第一次回调成功
        await provider.handle_callback(code="code", state=state)

        # 第二次使用相同 state 应失败
        result = await provider.handle_callback(code="code", state=state)
        assert result.success is False


class TestHandleLogout:
    """SSOAuthProvider.handle_logout() 测试."""

    @pytest.mark.asyncio
    async def test_returns_casdoor_logout_url(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        result = await provider.handle_logout(session_id="session-1")

        assert result.success is True
        assert result.redirect_url is not None
        assert config.endpoint in result.redirect_url
        assert "logout" in result.redirect_url
        assert config.client_id in result.redirect_url


class TestValidateSsoToken:
    """SSOAuthProvider.validate_sso_token() 测试."""

    @pytest.mark.asyncio
    async def test_delegates_to_client(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        client.validate_jwt = AsyncMock(return_value={"sub": "user-1", "name": "test"})

        result = await provider.validate_sso_token("valid-jwt")

        assert result == {"sub": "user-1", "name": "test"}
        client.validate_jwt.assert_called_once_with("valid-jwt")

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_jwt(self):
        config = _make_config()
        client = _make_mock_client()
        provider = SSOAuthProvider(client, config)

        client.validate_jwt = AsyncMock(return_value=None)

        result = await provider.validate_sso_token("invalid-jwt")
        assert result is None


class TestRedisStateStore:
    """SSOAuthProvider 使用 Redis state_store 测试."""

    @pytest.mark.asyncio
    async def test_state_stored_in_redis(self):
        config = _make_config()
        client = _make_mock_client()

        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.set = MagicMock()

        provider = SSOAuthProvider(client, config, state_store=mock_redis)

        await provider.initiate_login(redirect_url="https://app.example.com/page")

        # Redis set 应被调用
        assert mock_redis.set.called

    @pytest.mark.asyncio
    async def test_state_retrieved_from_redis(self):
        config = _make_config()
        client = _make_mock_client()

        mock_redis = MagicMock()
        mock_redis.set = MagicMock()
        mock_redis.get = MagicMock(return_value=b"https://app.example.com/page")
        mock_redis.delete = MagicMock()

        provider = SSOAuthProvider(client, config, state_store=mock_redis)

        init_result = await provider.initiate_login()
        state = init_result.session_id

        # 模拟回调
        from lib.auth.casdoor_client import CasdoorTokenResponse
        client.exchange_code = AsyncMock(return_value=CasdoorTokenResponse(access_token="at"))
        client.get_user_info = AsyncMock(return_value=CasdoorUserInfo(id="user-1"))

        result = await provider.handle_callback(code="code", state=state)

        assert result.success is True
        mock_redis.get.assert_called()
