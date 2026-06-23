"""CasdoorClient OAuth2 客户端测试."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lib.auth.casdoor_client import (
    CasdoorClient,
    CasdoorError,
    CasdoorTokenResponse,
    CasdoorUserInfo,
)
from lib.auth.casdoor_config import CasdoorConfig


def _make_config(**overrides) -> CasdoorConfig:
    """创建测试用 CasdoorConfig."""
    defaults = {
        "enabled": True,
        "endpoint": "https://casdoor.example.com",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "organization": "llm-wiki",
        "application": "llm-wiki-app",
        "certificate": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2Z3qO2gX5K9L8d7x\n-----END PUBLIC KEY-----",
        "redirect_uri": "https://app.example.com/api/auth/sso/callback",
    }
    defaults.update(overrides)
    return CasdoorConfig(**defaults)


class TestCasdoorTokenResponse:
    """CasdoorTokenResponse 测试."""

    def test_defaults(self):
        resp = CasdoorTokenResponse(access_token="at")
        assert resp.access_token == "at"
        assert resp.token_type == "Bearer"
        assert resp.expires_in == 0
        assert resp.refresh_token == ""
        assert resp.scope == ""

    def test_full(self):
        resp = CasdoorTokenResponse(
            access_token="at", token_type="Bearer",
            expires_in=3600, refresh_token="rt", scope="read"
        )
        assert resp.expires_in == 3600


class TestCasdoorUserInfo:
    """CasdoorUserInfo 测试."""

    def test_defaults(self):
        info = CasdoorUserInfo(id="user-1")
        assert info.id == "user-1"
        assert info.name == ""
        assert info.roles == []

    def test_full(self):
        info = CasdoorUserInfo(
            id="user-1", name="test", display_name="Test User",
            email="test@example.com", roles=["admin"]
        )
        assert info.roles == ["admin"]


class TestCasdoorClientGetAuthorizationUrl:
    """CasdoorClient.get_authorization_url() 测试."""

    def test_url_contains_required_params(self):
        config = _make_config()
        client = CasdoorClient(config)
        url = client.get_authorization_url(state="random-state")

        assert config.endpoint in url
        assert "client_id=test-client-id" in url
        assert "response_type=code" in url
        assert "redirect_uri=" in url
        assert "state=random-state" in url

    def test_url_contains_org_and_app(self):
        config = _make_config()
        client = CasdoorClient(config)
        url = client.get_authorization_url(state="s1")

        assert "organization=llm-wiki" in url
        assert "application=llm-wiki-app" in url

    def test_url_path_is_login_oauth_authorize(self):
        config = _make_config()
        client = CasdoorClient(config)
        url = client.get_authorization_url(state="s1")

        assert "/login/oauth/authorize" in url


class TestCasdoorClientExchangeCode:
    """CasdoorClient.exchange_code() 测试."""

    @pytest.mark.asyncio
    async def test_success(self):
        config = _make_config()
        client = CasdoorClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-at",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "test-rt",
            "scope": "read",
        }

        with patch.object(client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=mock_response)
            result = await client.exchange_code("valid-code")

        assert result.access_token == "test-at"
        assert result.expires_in == 3600

    @pytest.mark.asyncio
    async def test_invalid_code(self):
        config = _make_config()
        client = CasdoorClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "unauthorized"

        with patch.object(client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=mock_response)
            with pytest.raises(CasdoorError) as exc_info:
                await client.exchange_code("invalid-code")
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_network_error(self):
        import httpx

        config = _make_config()
        client = CasdoorClient(config)

        with patch.object(client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            with pytest.raises(CasdoorError):
                await client.exchange_code("code")


class TestCasdoorClientGetUserInfo:
    """CasdoorClient.get_user_info() 测试."""

    @pytest.mark.asyncio
    async def test_success(self):
        config = _make_config()
        client = CasdoorClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "casdoor-user-1",
            "name": "testuser",
            "display_name": "Test User",
            "email": "test@example.com",
            "phone": "",
            "avatar": "",
            "organization": "llm-wiki",
        }

        with patch.object(client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)
            result = await client.get_user_info("valid-token")

        assert result.id == "casdoor-user-1"
        assert result.name == "testuser"

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        config = _make_config()
        client = CasdoorClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "invalid token"

        with patch.object(client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)
            with pytest.raises(CasdoorError):
                await client.get_user_info("bad-token")


class TestCasdoorClientValidateJwt:
    """CasdoorClient.validate_jwt() 测试."""

    @pytest.mark.asyncio
    async def test_invalid_format_returns_none(self):
        config = _make_config()
        client = CasdoorClient(config)

        # 不是有效的 JWT 格式
        result = await client.validate_jwt("not-a-jwt")
        assert result is None

    @pytest.mark.asyncio
    async def test_expired_jwt_returns_none(self):
        # 使用空证书配置，validate_jwt 应返回 None
        config = _make_config(certificate="")
        client = CasdoorClient(config)

        result = await client.validate_jwt("eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxMDAwMDAwMDAwfQ.invalid")
        assert result is None


class TestCasdoorClientRefreshToken:
    """CasdoorClient.refresh_token() 测试."""

    @pytest.mark.asyncio
    async def test_success(self):
        config = _make_config()
        client = CasdoorClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-at",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "new-rt",
        }

        with patch.object(client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=mock_response)
            result = await client.refresh_token("old-rt")

        assert result.access_token == "new-at"

    @pytest.mark.asyncio
    async def test_failure(self):
        config = _make_config()
        client = CasdoorClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "invalid refresh token"

        with patch.object(client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=mock_response)
            with pytest.raises(CasdoorError):
                await client.refresh_token("bad-rt")


class TestCasdoorClientContextManager:
    """CasdoorClient async context manager 测试."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        config = _make_config()
        client = CasdoorClient(config)

        mock_close = AsyncMock()
        with patch.object(client, "_http_client") as mock_http:
            mock_http.aclose = mock_close
            async with client as c:
                assert c is client
            mock_close.assert_called_once()


class TestCasdoorError:
    """CasdoorError 异常测试."""

    def test_with_status_code(self):
        err = CasdoorError("test error", status_code=401)
        assert err.message == "test error"
        assert err.status_code == 401
        assert "test error" in str(err)

    def test_without_status_code(self):
        err = CasdoorError("test error")
        assert err.status_code is None
