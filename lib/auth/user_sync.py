"""Redis 会话管理器 + 用户同步服务.

扩展 SessionManager 支持 Redis 持久化存储，以及 Casdoor 用户同步到 users 表。
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# --- Session 序列化辅助 ---

def _session_to_dict(session_dict: dict) -> str:
    """将会话字典序列化为 JSON 字符串.

    Args:
        session_dict: 包含 session 信息的字典

    Returns:
        JSON 字符串
    """
    return json.dumps(session_dict, ensure_ascii=False)


def _dict_to_session(data: str) -> dict:
    """从 JSON 字符串反序列化为会话字典.

    Args:
        data: JSON 字符串

    Returns:
        会话字典
    """
    return json.loads(data)


# --- Redis 会话管理器 ---

class RedisSessionManager:
    """基于 Redis 的异步会话管理器.

    支持多实例共享会话，使用 Redis TTL 自动过期。

    存储格式:
        session:{session_id} -> JSON（TTL = session_timeout）
        user_sessions:{user_id} -> Set[session_id]
    """

    def __init__(self, redis_url: str, max_sessions: int = 10000) -> None:
        """初始化 Redis 会话管理器.

        Args:
            redis_url: Redis 连接 URL（如 redis://localhost:6379/0）
            max_sessions: 最大会话数（用于兼容接口，Redis 中不强制）
        """
        self._redis_url = redis_url
        self._max_sessions = max_sessions
        self._redis: Any = None
        self._session_timeout = int(os.getenv("SESSION_TIMEOUT", str(8 * 60 * 60)))

    async def _ensure_connection(self) -> Any:
        """确保 Redis 连接已建立.

        Returns:
            Redis 客户端实例
        """
        if self._redis is None:
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(
                    self._redis_url,
                    decode_responses=True,
                )
                # 测试连接
                await self._redis.ping()
            except Exception as exc:
                logger.error("Failed to connect to Redis: %s", exc)
                raise
        return self._redis

    async def create_session(
        self,
        user_id: str,
        metadata: Optional[Dict] = None,
    ) -> dict:
        """创建新会话.

        Args:
            user_id: 用户 ID
            metadata: 会话元数据

        Returns:
            会话字典
        """
        r = await self._ensure_connection()

        session_id = secrets.token_urlsafe(32)
        now = time.time()
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": now,
            "last_accessed": now,
            "metadata": metadata or {},
        }

        # 写入会话数据（带 TTL）
        session_key = f"session:{session_id}"
        await r.setex(session_key, self._session_timeout, _session_to_dict(session_data))

        # 更新用户索引
        user_key = f"user_sessions:{user_id}"
        await r.sadd(user_key, session_id)

        logger.debug("Created Redis session for user: %s***", user_id[:8])
        return session_data

    async def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话.

        Args:
            session_id: 会话 ID

        Returns:
            会话字典，不存在或过期返回 None
        """
        r = await self._ensure_connection()

        session_key = f"session:{session_id}"
        data = await r.get(session_key)

        if data is None:
            return None

        session = _dict_to_session(data)

        # 刷新 TTL
        await r.expire(session_key, self._session_timeout)

        # 更新 last_accessed
        session["last_accessed"] = time.time()
        await r.setex(session_key, self._session_timeout, _session_to_dict(session))

        return session

    async def destroy_session(self, session_id: str) -> bool:
        """销毁会话.

        Args:
            session_id: 会话 ID

        Returns:
            是否成功销毁
        """
        r = await self._ensure_connection()

        session_key = f"session:{session_id}"
        data = await r.get(session_key)

        if data is None:
            return False

        session = _dict_to_session(data)
        user_id = session.get("user_id", "")

        # 删除会话
        await r.delete(session_key)

        # 从用户索引中移除
        if user_id:
            user_key = f"user_sessions:{user_id}"
            await r.srem(user_key, session_id)

        logger.debug("Destroyed Redis session: %s***", session_id[:8])
        return True

    async def get_user_sessions(self, user_id: str) -> List[dict]:
        """获取用户的所有活跃会话.

        Args:
            user_id: 用户 ID

        Returns:
            活跃会话列表
        """
        r = await self._ensure_connection()

        user_key = f"user_sessions:{user_id}"
        session_ids = await r.smembers(user_key)

        sessions = []
        for sid in session_ids:
            session = await self.get_session(sid)
            if session is not None:
                sessions.append(session)

        return sessions

    async def destroy_user_sessions(self, user_id: str) -> int:
        """销毁用户的所有会话.

        Args:
            user_id: 用户 ID

        Returns:
            销毁的会话数量
        """
        r = await self._ensure_connection()

        user_key = f"user_sessions:{user_id}"
        session_ids = await r.smembers(user_key)

        if not session_ids:
            return 0

        # 批量删除会话
        pipe = r.pipeline()
        for sid in session_ids:
            pipe.delete(f"session:{sid}")
        pipe.delete(user_key)
        await pipe.execute()

        logger.info(
            "Destroyed %d Redis sessions for user: %s***",
            len(session_ids),
            user_id[:8],
        )
        return len(session_ids)

    async def cleanup_expired(self) -> int:
        """清理过期会话.

        Redis TTL 自动过期，此方法返回 0。

        Returns:
            0（Redis 自动过期）
        """
        return 0

    @property
    def active_session_count(self) -> int:
        """活跃会话数（需异步获取，此处返回 -1 表示不可用）."""
        return -1

    async def close(self) -> None:
        """关闭 Redis 连接."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


def create_session_manager(
    redis_url: Optional[str] = None,
    max_sessions: int = 1000,
) -> Union["SessionManager", RedisSessionManager]:
    """创建会话管理器工厂方法.

    如果提供了 redis_url，返回 RedisSessionManager；
    否则返回内存 SessionManager。

    Args:
        redis_url: Redis 连接 URL（可选）
        max_sessions: 最大会话数

    Returns:
        SessionManager 或 RedisSessionManager 实例
    """
    if redis_url:
        return RedisSessionManager(redis_url=redis_url, max_sessions=max_sessions)

    from lib.auth.session_manager import SessionManager

    return SessionManager(max_sessions=max_sessions)


# --- 用户同步服务 ---

@dataclass
class SyncResult:
    """用户同步结果.

    Attributes:
        user_id: 用户 ID
        is_new: 是否为新创建的用户
        roles: 用户角色列表
    """

    user_id: str
    is_new: bool
    roles: list[str] = field(default_factory=list)


def _generate_slug(name: str) -> str:
    """从名称生成 URL slug.

    Args:
        name: 原始名称

    Returns:
        小写 + 连字符格式的 slug
    """
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:128] or "default"


class UserSyncService:
    """Casdoor 用户同步服务.

    将 Casdoor 用户信息同步到 PostgreSQL users 表。
    """

    def __init__(self, db_manager: Any) -> None:
        """初始化 UserSyncService.

        Args:
            db_manager: PostgreSQLManager 实例（需提供 asyncpg 连接池）
        """
        self._db = db_manager

    async def sync_user_from_casdoor(
        self,
        casdoor_user_id: str,
        casdoor_user_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        organization: Optional[str] = None,
        department: Optional[str] = None,
        roles: Optional[list[str]] = None,
    ) -> SyncResult:
        """从 Casdoor 同步用户到 users 表.

        使用 INSERT ... ON CONFLICT 实现幂等同步：
        - 用户不存在 → INSERT（自动创建）
        - 用户已存在 → UPDATE（更新名称、邮箱等字段）

        Args:
            casdoor_user_id: Casdoor 用户 ID
            casdoor_user_name: 用户显示名称
            email: 电子邮箱（可选）
            phone: 手机号（可选）
            organization: 组织名称（可选）
            department: 部门名称（可选）
            roles: Casdoor 角色列表（可选）

        Returns:
            SyncResult 同步结果
        """
        # 角色映射
        global_role = "admin" if (roles and "admin" in roles) else "user"

        # 解析组织和部门 ID
        org_id = None
        dept_id = None
        if organization:
            org_id = await self.get_or_create_organization(organization)
        if department and org_id:
            dept_id = await self.get_or_create_department(org_id, department)

        # 幂等同步：INSERT ON CONFLICT DO UPDATE
        query = """
            INSERT INTO users (id, name, email, phone, organization_id, department_id, global_role, status, last_login_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'active', NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                email = COALESCE(EXCLUDED.email, users.email),
                phone = COALESCE(EXCLUDED.phone, users.phone),
                organization_id = COALESCE(EXCLUDED.organization_id, users.organization_id),
                department_id = COALESCE(EXCLUDED.department_id, users.department_id),
                global_role = EXCLUDED.global_role,
                last_login_at = NOW(),
                updated_at = NOW()
            RETURNING (xmax = 0) AS is_new
        """

        try:
            result = await self._db.execute_query(
                query,
                casdoor_user_id,
                casdoor_user_name,
                email,
                phone,
                org_id,
                dept_id,
                global_role,
            )

            is_new = result[0]["is_new"] if result else True

            return SyncResult(
                user_id=casdoor_user_id,
                is_new=is_new,
                roles=[global_role],
            )
        except Exception as exc:
            logger.error("Failed to sync user from Casdoor: %s", exc)
            raise

    async def get_or_create_organization(self, org_name: str) -> int:
        """获取或创建组织.

        Args:
            org_name: 组织名称

        Returns:
            组织 ID
        """
        slug = _generate_slug(org_name)

        query = """
            INSERT INTO organizations (name, slug)
            VALUES ($1, $2)
            ON CONFLICT (slug) DO UPDATE SET name = $1
            RETURNING id
        """

        result = await self._db.execute_query(query, org_name, slug)
        return result[0]["id"]

    async def get_or_create_department(self, org_id: int, dept_name: str) -> int:
        """获取或创建部门.

        Args:
            org_id: 组织 ID
            dept_name: 部门名称

        Returns:
            部门 ID
        """
        slug = _generate_slug(dept_name)

        query = """
            INSERT INTO departments (org_id, name, slug)
            VALUES ($1, $2, $3)
            ON CONFLICT (org_id, slug) DO UPDATE SET name = $2
            RETURNING id
        """

        result = await self._db.execute_query(query, org_id, dept_name, slug)
        return result[0]["id"]

    async def update_last_login(self, user_id: str) -> None:
        """更新用户最后登录时间.

        Args:
            user_id: 用户 ID
        """
        query = "UPDATE users SET last_login_at = NOW() WHERE id = $1"
        await self._db.execute_query(query, user_id)
