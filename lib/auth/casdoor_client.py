"""Casdoor OAuth2 客户端模块.

实现与 Casdoor SSO 服务的 OAuth2 协议交互，包括：
- 授权 URL 生成
- Code 换取 Token
- 用户信息获取
- JWT 验证
- Token 刷新
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

try:
    from jose import JWTError, jwt
except ImportError:
    jwt = None  # type: ignore[assignment]
    JWTError = Exception  # type: ignore[assignment,misc]

from lib.auth.casdoor_config import CasdoorConfig

logger = logging.getLogger(__name__)


class CasdoorError(Exception):
    """Casdoor 操作异常.

    Attributes:
        message: 错误描述
        status_code: HTTP 状态码（可选）
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class CasdoorTokenResponse:
    """Casdoor OAuth2 Token 响应.

    Attributes:
        access_token: 访问令牌
        token_type: 令牌类型（默认 Bearer）
        expires_in: 有效期（秒）
        refresh_token: 刷新令牌
        scope: 权限范围
    """

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 0
    refresh_token: str = ""
    scope: str = ""


@dataclass
class CasdoorUserInfo:
    """Casdoor 用户信息.

    Attributes:
        id: Casdoor 用户 ID
        name: 用户名
        display_name: 显示名称
        email: 电子邮箱
        phone: 手机号
        avatar: 头像 URL
        organization: 所属组织
        roles: 用户角色列表
    """

    id: str
    name: str = ""
    display_name: str = ""
    email: str = ""
    phone: str = ""
    avatar: str = ""
    organization: str = ""
    roles: list[str] = field(default_factory=list)


class CasdoorClient:
    """Casdoor OAuth2 客户端.

    负责与 Casdoor 服务进行 OAuth2 协议交互，包括授权、Token 交换、
    用户信息获取和 JWT 验证。

    支持作为 async context manager 使用:
        async with CasdoorClient(config) as client:
            ...
    """

    def __init__(self, config: CasdoorConfig) -> None:
        """初始化 CasdoorClient.

        Args:
            config: Casdoor 连接配置

        Raises:
            CasdoorError: httpx 未安装
        """
        if httpx is None:
            raise CasdoorError("httpx is required for CasdoorClient. Install with: pip install llm-wiki[sso]")
        self._config = config
        self._http_client = httpx.AsyncClient(timeout=30.0)

    def get_authorization_url(self, state: str) -> str:
        """生成 OAuth2 授权 URL.

        Args:
            state: CSRF 防护的 state 参数

        Returns:
            完整的授权 URL，包含所有必要参数
        """
        params = {
            "client_id": self._config.client_id,
            "response_type": "code",
            "redirect_uri": self._config.redirect_uri,
            "scope": "read",
            "state": state,
            "organization": self._config.organization,
            "application": self._config.application,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self._config.endpoint}/login/oauth/authorize?{query}"

    async def exchange_code(self, code: str) -> CasdoorTokenResponse:
        """用授权码换取访问令牌.

        Args:
            code: OAuth2 授权码

        Returns:
            CasdoorTokenResponse 包含访问令牌等信息

        Raises:
            CasdoorError: 交换失败或网络错误
        """
        url = f"{self._config.endpoint}/api/login/oauth/access_token"
        form_data = {
            "grant_type": "authorization_code",
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "code": code,
            "redirect_uri": self._config.redirect_uri,
        }

        try:
            response = await self._http_client.post(url, data=form_data)
        except httpx.TimeoutException as exc:
            raise CasdoorError(
                f"Timeout exchanging code with Casdoor: {exc}",
            ) from exc
        except httpx.HTTPError as exc:
            raise CasdoorError(
                f"Network error exchanging code with Casdoor: {exc}",
            ) from exc

        if response.status_code != 200:
            error_detail = response.text
            raise CasdoorError(
                f"Failed to exchange code (status={response.status_code}): {error_detail}",
                status_code=response.status_code,
            )

        data = response.json()
        return CasdoorTokenResponse(
            access_token=data.get("access_token", ""),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 0),
            refresh_token=data.get("refresh_token", ""),
            scope=data.get("scope", ""),
        )

    async def get_user_info(self, access_token: str) -> CasdoorUserInfo:
        """获取用户信息.

        Args:
            access_token: 访问令牌

        Returns:
            CasdoorUserInfo 用户信息

        Raises:
            CasdoorError: 获取失败或网络错误
        """
        url = f"{self._config.endpoint}/api/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = await self._http_client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            raise CasdoorError(
                f"Timeout fetching user info from Casdoor: {exc}",
            ) from exc
        except httpx.HTTPError as exc:
            raise CasdoorError(
                f"Network error fetching user info from Casdoor: {exc}",
            ) from exc

        if response.status_code != 200:
            error_detail = response.text
            raise CasdoorError(
                f"Failed to get user info (status={response.status_code}): {error_detail}",
                status_code=response.status_code,
            )

        data = response.json()
        return CasdoorUserInfo(
            id=data.get("id", data.get("sub", "")),
            name=data.get("name", ""),
            display_name=data.get("displayName", data.get("display_name", "")),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            avatar=data.get("avatar", ""),
            organization=data.get("organization", ""),
            roles=data.get("roles", []),
        )

    async def validate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 JWT 令牌.

        使用配置的证书验证 JWT 签名和过期时间。

        Args:
            token: JWT 令牌字符串

        Returns:
            解码后的 JWT claims 字典，验证失败返回 None
        """
        if not self._config.certificate:
            logger.warning("No certificate configured for JWT validation")
            return None

        try:
            claims = jwt.decode(
                token,
                self._config.certificate,
                algorithms=["RS256"],
                audience=self._config.client_id,
            )
            return claims
        except JWTError as exc:
            logger.debug("JWT validation failed: %s", exc)
            return None

    async def refresh_token(self, refresh_token: str) -> CasdoorTokenResponse:
        """刷新访问令牌.

        Args:
            refresh_token: 刷新令牌

        Returns:
            CasdoorTokenResponse 新的访问令牌信息

        Raises:
            CasdoorError: 刷新失败或网络错误
        """
        url = f"{self._config.endpoint}/api/login/oauth/refresh"
        form_data = {
            "grant_type": "refresh_token",
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "refresh_token": refresh_token,
        }

        try:
            response = await self._http_client.post(url, data=form_data)
        except httpx.TimeoutException as exc:
            raise CasdoorError(
                f"Timeout refreshing token with Casdoor: {exc}",
            ) from exc
        except httpx.HTTPError as exc:
            raise CasdoorError(
                f"Network error refreshing token with Casdoor: {exc}",
            ) from exc

        if response.status_code != 200:
            error_detail = response.text
            raise CasdoorError(
                f"Failed to refresh token (status={response.status_code}): {error_detail}",
                status_code=response.status_code,
            )

        data = response.json()
        return CasdoorTokenResponse(
            access_token=data.get("access_token", ""),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 0),
            refresh_token=data.get("refresh_token", ""),
            scope=data.get("scope", ""),
        )

    async def close(self) -> None:
        """关闭 HTTP 客户端."""
        await self._http_client.aclose()

    async def __aenter__(self) -> CasdoorClient:
        """进入 async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """退出 async context manager."""
        await self.close()
