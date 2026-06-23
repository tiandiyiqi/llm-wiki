"""SSO 认证提供者模块.

实现基于 Casdoor 的 SSO 认证流程，包括：
- 发起登录（生成 state + 授权 URL）
- 处理回调（code 换 token + 获取用户信息）
- 登出
- SSO Token 验证

注意：SSOAuthProvider 只负责 OAuth2 协议流程，
不直接管理 SessionManager 和 UserSyncService。
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from lib.auth.casdoor_client import CasdoorClient, CasdoorError
from lib.auth.casdoor_config import CasdoorConfig

logger = logging.getLogger(__name__)


@dataclass
class SSOAuthResult:
    """SSO 认证结果.

    Attributes:
        success: 认证是否成功
        user_id: Casdoor 用户 ID
        roles: 用户角色列表
        session_id: 会话 ID（通常是 state 参数）
        redirect_url: 重定向 URL（登录时为授权 URL，登出时为登出 URL）
        error: 错误信息
    """

    success: bool
    user_id: Optional[str] = None
    roles: Optional[list[str]] = None
    session_id: Optional[str] = None
    redirect_url: Optional[str] = None
    error: Optional[str] = None


class SSOAuthProvider:
    """SSO 认证提供者.

    封装 Casdoor OAuth2 认证流程，管理 state 参数防止 CSRF 攻击。

    state_store 用于持久化 state -> redirect_url 映射：
    - 生产环境：传入 Redis 客户端（需实现 set/get/delete 方法）
    - 开发环境：不传 state_store，使用内存 dict
    """

    def __init__(
        self,
        casdoor_client: CasdoorClient,
        config: CasdoorConfig,
        state_store: Any = None,
    ) -> None:
        """初始化 SSOAuthProvider.

        Args:
            casdoor_client: Casdoor OAuth2 客户端
            config: Casdoor 连接配置
            state_store: 可选的 state 存储后端（Redis 客户端等），
                         需实现 set(key, value, ex)/get(key)/delete(key) 方法。
                         如果为 None，使用内存 dict（仅用于开发模式）。
        """
        self._client = casdoor_client
        self._config = config
        self._state_store = state_store
        self._memory_store: dict[str, str] = {}

    async def initiate_login(
        self,
        redirect_url: Optional[str] = None,
    ) -> SSOAuthResult:
        """发起 SSO 登录.

        生成随机 state 参数，存储 state -> redirect_url 映射，
        并返回 Casdoor 授权 URL。

        Args:
            redirect_url: 登录成功后的重定向 URL（可选）

        Returns:
            SSOAuthResult 包含授权 URL 和 state
        """
        state = secrets.token_urlsafe(32)
        await self._store_state(state, redirect_url or "")

        authorization_url = self._client.get_authorization_url(state)

        return SSOAuthResult(
            success=True,
            redirect_url=authorization_url,
            session_id=state,
        )

    async def handle_callback(self, code: str, state: str) -> SSOAuthResult:
        """处理 SSO 登录回调.

        验证 state 参数，用 code 换取 access_token，获取用户信息。

        Args:
            code: OAuth2 授权码
            state: CSRF 防护的 state 参数

        Returns:
            SSOAuthResult 认证结果
        """
        # 验证 state 存在
        stored_redirect = await self._retrieve_state(state)
        if stored_redirect is None:
            return SSOAuthResult(
                success=False,
                error="Invalid or expired state parameter",
            )

        # 清理已使用的 state
        await self._delete_state(state)

        # 用 code 换取 access_token
        try:
            token_response = await self._client.exchange_code(code)
        except CasdoorError as exc:
            logger.warning("Code exchange failed: %s", exc.message)
            return SSOAuthResult(
                success=False,
                error=f"Code exchange failed: {exc.message}",
            )

        if not token_response.access_token:
            return SSOAuthResult(
                success=False,
                error="Code exchange returned empty access token",
            )

        # 获取用户信息
        try:
            user_info = await self._client.get_user_info(token_response.access_token)
        except CasdoorError as exc:
            logger.warning("Failed to get user info: %s", exc.message)
            return SSOAuthResult(
                success=False,
                error=f"Failed to get user info: {exc.message}",
            )

        return SSOAuthResult(
            success=True,
            user_id=user_info.id,
            roles=user_info.roles,
        )

    async def handle_logout(self, session_id: str) -> SSOAuthResult:
        """处理 SSO 登出.

        返回 Casdoor 登出 URL，前端应重定向到该 URL。

        Args:
            session_id: 会话 ID（未使用，保留扩展）

        Returns:
            SSOAuthResult 包含 Casdoor 登出 URL
        """
        logout_url = (
            f"{self._config.endpoint}/api/logout"
            f"?client_id={self._config.client_id}"
            f"&redirect_uri={self._config.redirect_uri}"
        )
        return SSOAuthResult(
            success=True,
            redirect_url=logout_url,
        )

    async def validate_sso_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 SSO Token.

        委托 CasdoorClient.validate_jwt 进行 JWT 验证。

        Args:
            token: JWT 令牌字符串

        Returns:
            解码后的 JWT claims，验证失败返回 None
        """
        return await self._client.validate_jwt(token)

    # --- State 存储辅助方法 ---

    async def _store_state(self, state: str, redirect_url: str) -> None:
        """存储 state -> redirect_url 映射.

        Args:
            state: CSRF state 参数
            redirect_url: 登录后的重定向 URL
        """
        if self._state_store is not None:
            # 生产模式：使用 Redis 等持久化存储
            self._state_store.set(state, redirect_url, ex=600)
        else:
            # 开发模式：使用内存 dict
            self._memory_store[state] = redirect_url

    async def _retrieve_state(self, state: str) -> Optional[str]:
        """从存储中获取 state 对应的 redirect_url.

        Args:
            state: CSRF state 参数

        Returns:
            redirect_url 或 None（state 不存在或已过期）
        """
        if self._state_store is not None:
            result = self._state_store.get(state)
            if result is None:
                return None
            # Redis 返回 bytes 或 str，统一转为 str
            return result.decode("utf-8") if isinstance(result, bytes) else result
        else:
            return self._memory_store.get(state)

    async def _delete_state(self, state: str) -> None:
        """从存储中删除已使用的 state.

        Args:
            state: CSRF state 参数
        """
        if self._state_store is not None:
            self._state_store.delete(state)
        else:
            self._memory_store.pop(state, None)
