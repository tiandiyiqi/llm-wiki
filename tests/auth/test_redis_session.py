"""Redis 会话管理器测试."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lib.auth.user_sync import (
    RedisSessionManager,
    _dict_to_session,
    _session_to_dict,
    create_session_manager,
)


class TestSessionSerialization:
    """会话序列化辅助函数测试."""

    def test_session_to_dict(self):
        data = {
            "session_id": "abc123",
            "user_id": "user-1",
            "created_at": 1000.0,
            "last_accessed": 1000.0,
            "metadata": {"key": "value"},
        }
        result = _session_to_dict(data)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["session_id"] == "abc123"
        assert parsed["metadata"]["key"] == "value"

    def test_dict_to_session(self):
        json_str = json.dumps({
            "session_id": "abc123",
            "user_id": "user-1",
            "created_at": 1000.0,
            "last_accessed": 1000.0,
            "metadata": {},
        })
        result = _dict_to_session(json_str)
        assert result["session_id"] == "abc123"
        assert result["user_id"] == "user-1"

    def test_round_trip(self):
        data = {
            "session_id": "xyz",
            "user_id": "u2",
            "created_at": 2000.0,
            "last_accessed": 2000.0,
            "metadata": {"sso": True},
        }
        assert _dict_to_session(_session_to_dict(data)) == data


class TestRedisSessionManager:
    """RedisSessionManager 测试（使用 Mock Redis）."""

    def _make_mock_redis(self) -> MagicMock:
        """创建 Mock Redis 客户端."""
        redis = MagicMock()
        redis.ping = AsyncMock(return_value=True)
        redis.setex = AsyncMock(return_value=True)
        redis.get = AsyncMock(return_value=None)
        redis.delete = AsyncMock(return_value=1)
        redis.sadd = AsyncMock(return_value=1)
        redis.smembers = AsyncMock(return_value=set())
        redis.srem = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)
        redis.aclose = AsyncMock()
        # Pipeline mock
        pipe = MagicMock()
        pipe.delete = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[1, 1])
        redis.pipeline = MagicMock(return_value=pipe)
        return redis

    @pytest.mark.asyncio
    async def test_create_session(self):
        manager = RedisSessionManager("redis://localhost:6379/0")
        mock_redis = self._make_mock_redis()
        manager._redis = mock_redis

        session = await manager.create_session(user_id="user-1", metadata={"source": "sso"})

        assert session["user_id"] == "user-1"
        assert session["metadata"]["source"] == "sso"
        assert "session_id" in session
        mock_redis.setex.assert_called_once()
        mock_redis.sadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_exists(self):
        manager = RedisSessionManager("redis://localhost:6379/0")
        mock_redis = self._make_mock_redis()

        session_data = json.dumps({
            "session_id": "test-sid",
            "user_id": "user-1",
            "created_at": time.time(),
            "last_accessed": time.time(),
            "metadata": {},
        })
        mock_redis.get = AsyncMock(return_value=session_data)
        manager._redis = mock_redis

        session = await manager.get_session("test-sid")

        assert session is not None
        assert session["user_id"] == "user-1"

    @pytest.mark.asyncio
    async def test_get_session_not_exists(self):
        manager = RedisSessionManager("redis://localhost:6379/0")
        mock_redis = self._make_mock_redis()
        mock_redis.get = AsyncMock(return_value=None)
        manager._redis = mock_redis

        session = await manager.get_session("nonexistent")

        assert session is None

    @pytest.mark.asyncio
    async def test_destroy_session(self):
        manager = RedisSessionManager("redis://localhost:6379/0")
        mock_redis = self._make_mock_redis()

        session_data = json.dumps({
            "session_id": "test-sid",
            "user_id": "user-1",
            "created_at": time.time(),
            "last_accessed": time.time(),
            "metadata": {},
        })
        mock_redis.get = AsyncMock(return_value=session_data)
        manager._redis = mock_redis

        result = await manager.destroy_session("test-sid")

        assert result is True
        mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_destroy_session_not_exists(self):
        manager = RedisSessionManager("redis://localhost:6379/0")
        mock_redis = self._make_mock_redis()
        mock_redis.get = AsyncMock(return_value=None)
        manager._redis = mock_redis

        result = await manager.destroy_session("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_destroy_user_sessions(self):
        manager = RedisSessionManager("redis://localhost:6379/0")
        mock_redis = self._make_mock_redis()
        mock_redis.smembers = AsyncMock(return_value={"sid1", "sid2"})
        manager._redis = mock_redis

        count = await manager.destroy_user_sessions("user-1")

        assert count == 2

    @pytest.mark.asyncio
    async def test_destroy_user_sessions_no_sessions(self):
        manager = RedisSessionManager("redis://localhost:6379/0")
        mock_redis = self._make_mock_redis()
        mock_redis.smembers = AsyncMock(return_value=set())
        manager._redis = mock_redis

        count = await manager.destroy_user_sessions("user-1")

        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_returns_zero(self):
        manager = RedisSessionManager("redis://localhost:6379/0")
        mock_redis = self._make_mock_redis()
        manager._redis = mock_redis

        count = await manager.cleanup_expired()

        assert count == 0

    @pytest.mark.asyncio
    async def test_close(self):
        manager = RedisSessionManager("redis://localhost:6379/0")
        mock_redis = self._make_mock_redis()
        manager._redis = mock_redis

        await manager.close()

        mock_redis.aclose.assert_called_once()
        assert manager._redis is None


class TestCreateSessionManager:
    """create_session_manager 工厂方法测试."""

    def test_with_redis_url(self):
        manager = create_session_manager(redis_url="redis://localhost:6379/0")
        assert isinstance(manager, RedisSessionManager)

    def test_without_redis_url(self):
        from lib.auth.session_manager import SessionManager

        manager = create_session_manager(redis_url=None)
        assert isinstance(manager, SessionManager)

    def test_with_custom_max_sessions(self):
        manager = create_session_manager(
            redis_url="redis://localhost:6379/0",
            max_sessions=5000,
        )
        assert manager._max_sessions == 5000
