"""会话管理器，支持超时、刷新和自动清理."""

import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 默认会话超时时间（8 小时）
DEFAULT_SESSION_TIMEOUT = 8 * 60 * 60  # 秒
# 默认最大会话数
DEFAULT_MAX_SESSIONS = 1000
# 清理间隔（10 分钟）
CLEANUP_INTERVAL = 10 * 60  # 秒


@dataclass
class Session:
    """用户会话."""

    session_id: str
    user_id: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """检查会话是否过期."""
        timeout = int(os.getenv('SESSION_TIMEOUT', str(DEFAULT_SESSION_TIMEOUT)))
        return (time.time() - self.last_accessed) > timeout

    def touch(self) -> None:
        """刷新会话访问时间."""
        self.last_accessed = time.time()


class SessionManager:
    """会话管理器，支持超时、刷新和自动清理."""

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS):
        self._sessions: Dict[str, Session] = {}
        self._max_sessions = max_sessions
        self._last_cleanup: float = time.time()

    def create_session(
        self,
        user_id: str,
        metadata: Optional[Dict] = None,
    ) -> Session:
        """创建新会话.

        Args:
            user_id: 用户 ID
            metadata: 会话元数据

        Returns:
            新创建的 Session 实例
        """
        # 清理过期会话
        self._maybe_cleanup()

        # 检查最大会话数
        if len(self._sessions) >= self._max_sessions:
            # 移除最旧的会话
            oldest_id = min(
                self._sessions,
                key=lambda sid: self._sessions[sid].last_accessed,
            )
            del self._sessions[oldest_id]
            logger.info("Removed oldest session to make room: %s***", oldest_id[:8])

        session = Session(
            session_id=secrets.token_urlsafe(32),
            user_id=user_id,
            metadata=metadata or {},
        )
        self._sessions[session.session_id] = session
        logger.debug("Created session for user: %s***", user_id[:8])
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话（如果未过期）.

        Args:
            session_id: 会话 ID

        Returns:
            Session 实例，过期或不存在则返回 None
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if session.is_expired:
            del self._sessions[session_id]
            logger.debug("Session expired: %s***", session_id[:8])
            return None

        # 刷新访问时间
        session.touch()
        return session

    def destroy_session(self, session_id: str) -> bool:
        """销毁会话.

        Args:
            session_id: 会话 ID

        Returns:
            是否成功销毁
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.debug("Destroyed session: %s***", session_id[:8])
            return True
        return False

    def get_user_sessions(self, user_id: str) -> List[Session]:
        """获取用户的所有活跃会话.

        Args:
            user_id: 用户 ID

        Returns:
            该用户的活跃会话列表
        """
        return [
            s for s in self._sessions.values()
            if s.user_id == user_id and not s.is_expired
        ]

    def destroy_user_sessions(self, user_id: str) -> int:
        """销毁用户的所有会话.

        Args:
            user_id: 用户 ID

        Returns:
            销毁的会话数量
        """
        session_ids = [
            sid for sid, s in self._sessions.items()
            if s.user_id == user_id
        ]
        for sid in session_ids:
            del self._sessions[sid]
        logger.info(
            "Destroyed %d sessions for user: %s***",
            len(session_ids),
            user_id[:8],
        )
        return len(session_ids)

    def _maybe_cleanup(self) -> None:
        """定期清理过期会话."""
        now = time.time()
        if (now - self._last_cleanup) < CLEANUP_INTERVAL:
            return

        self._last_cleanup = now
        expired_count = self.cleanup_expired()
        if expired_count > 0:
            logger.info("Cleaned up %d expired sessions", expired_count)

    def cleanup_expired(self) -> int:
        """清理所有过期会话.

        Returns:
            清理的会话数量
        """
        expired_ids = [
            sid for sid, s in self._sessions.items()
            if s.is_expired
        ]
        for sid in expired_ids:
            del self._sessions[sid]
        return len(expired_ids)

    @property
    def active_session_count(self) -> int:
        """活跃会话数."""
        return len(self._sessions)
