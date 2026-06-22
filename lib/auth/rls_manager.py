"""RLS（Row-Level Security）策略管理

管理 PostgreSQL 的行级安全策略，确保用户只能访问自己有权限的数据。
"""

import logging
from typing import Dict, List, Optional, Set

from ..utils.sql_validator import SQLValidator

logger = logging.getLogger(__name__)


class RLSManager:
    """RLS 策略管理器

    管理 PostgreSQL 的 RLS 策略，包括：
    - 启用/禁用 RLS
    - 创建/删除策略
    - 设置用户上下文
    - 权限检查
    """

    def __init__(self, db_manager):
        """初始化 RLS 管理器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self._current_user_id: Optional[str] = None
        self._current_user_roles: List[str] = []

    async def initialize(self) -> None:
        """初始化 RLS 系统"""
        await self._enable_rls()
        logger.info("RLSManager initialized")

    async def _enable_rls(self) -> None:
        """为关键表启用 RLS"""
        tables = [
            'knowledge_bases',
            'atoms',
            'kb_members'
        ]

        for table in tables:
            # 验证表名（白名单检查）
            if not SQLValidator.validate_table_name(table):
                logger.error(f"Invalid table name: {table}")
                continue

            # 使用 safe_identifier 引用表名
            safe_table = SQLValidator.quote_identifier(table)
            query = f"ALTER TABLE {safe_table} ENABLE ROW LEVEL SECURITY"
            await self.db_manager.execute(query)
            logger.debug(f"Enabled RLS for table: {table}")

    async def set_user_context(self, user_id: str, roles: List[str]) -> None:
        """设置当前用户的 RLS 上下文

        在事务中设置 PostgreSQL 会话变量，确保 RLS 策略能正确应用。

        Args:
            user_id: 用户 ID
            roles: 用户角色列表

        Raises:
            ValueError: 如果输入参数无效
            RuntimeError: 如果未在事务中执行
            Exception: 如果设置上下文失败
        """
        # 输入验证
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        if len(user_id) > 255:
            raise ValueError("user_id must be at most 255 characters")
        if not roles or not isinstance(roles, list):
            raise ValueError("roles must be a non-empty list")
        if len(roles) > 100:
            raise ValueError("roles must contain at most 100 items")
        for role in roles:
            if not isinstance(role, str) or len(role) > 64:
                raise ValueError(
                    f"Invalid role: {role[:20]}..."
                    if isinstance(role, str)
                    else "Role must be a string"
                )

        # 更新实例变量（不可变：创建新列表）
        self._current_user_id = user_id
        self._current_user_roles = list(roles)

        # 通过 PostgreSQL 原生函数验证是否在事务中
        try:
            result = await self.db_manager.fetch_one(
                "SELECT pg_is_in_transaction() AS in_txn"
            )
            if not result or not result.get('in_txn'):
                raise RuntimeError(
                    "RLS context must be set within a transaction. "
                    "Call db_manager.begin_transaction() first."
                )
        except RuntimeError:
            raise
        except Exception as e:
            # 如果 fetch_one 不可用，回退到属性检查
            logger.warning(
                f"Cannot query pg_is_in_transaction(), "
                f"falling back to attribute check: {e}"
            )
            if not hasattr(self.db_manager, '_transaction_conn'):
                raise RuntimeError(
                    "RLS context must be set within a transaction. "
                    "Call db_manager.begin_transaction() first."
                )
            if self.db_manager._transaction_conn is None:
                raise RuntimeError(
                    "No active transaction found. "
                    "Call db_manager.begin_transaction() before "
                    "setting RLS context."
                )

        # 获取事务连接（优先使用 _transaction_conn）
        conn = getattr(self.db_manager, '_transaction_conn', None)
        if conn is None:
            raise RuntimeError(
                "Cannot obtain a database connection for RLS context. "
                "Ensure you are within an active transaction."
            )

        try:
            # 在事务中设置 PostgreSQL 会话变量
            # 注意：SET LOCAL 只在当前事务中有效
            await conn.execute(
                "SET LOCAL llmwiki.current_user_id = $1",
                user_id
            )

            # 设置角色列表
            roles_str = ','.join(roles)
            await conn.execute(
                "SET LOCAL llmwiki.current_user_roles = $1",
                roles_str
            )

            # 日志脱敏：生产环境不输出完整 user_id
            logger.debug(
                f"RLS context set: user={user_id[:8]}***, roles={roles}"
            )

        except Exception as e:
            # 重置实例变量，防止状态不一致
            self._current_user_id = None
            self._current_user_roles = []
            logger.error(f"Failed to set RLS context: {e}")
            raise

    async def create_kb_policy(self, kb_id: int) -> None:
        """为知识库创建 RLS 策略

        Args: 知识库 ID
        """
        # 验证 kb_id 是整数
        if not isinstance(kb_id, int) or kb_id < 0:
            logger.error(f"Invalid kb_id: {kb_id}")
            raise ValueError(f"Invalid kb_id: {kb_id}")

        policy_name = f"kb_{kb_id}_policy"

        # 验证策略名（防止注入）
        if not SQLValidator.validate_identifier(policy_name):
            logger.error(f"Invalid policy name: {policy_name}")
            raise ValueError(f"Invalid policy name: {policy_name}")

        # 使用 quote_ident 函数安全引用标识符
        # 注意：policy_name 已验证为安全标识符
        safe_policy = SQLValidator.quote_identifier(policy_name)

        # 创建策略：允许成员访问
        query = f"""
            CREATE POLICY {safe_policy} ON knowledge_bases
            FOR ALL
            USING (
                id IN (
                    SELECT kb_id FROM kb_members
                    WHERE user_id = current_setting('llmwiki.current_user_id')::TEXT
                )
                OR owner_id = current_setting('llmwiki.current_user_id')::TEXT
            )
        """

        await self.db_manager.execute(query)
        logger.info(f"Created RLS policy for KB {kb_id}")

    async def drop_kb_policy(self, kb_id: int) -> None:
        """删除知识库的 RLS 策略

        Args:
            kb_id: 知识库 ID
        """
        # 验证 kb_id 是整数
        if not isinstance(kb_id, int) or kb_id < 0:
            logger.error(f"Invalid kb_id: {kb_id}")
            return

        policy_name = f"kb_{kb_id}_policy"

        # 验证策略名（防止注入）
        if not SQLValidator.validate_identifier(policy_name):
            logger.error(f"Invalid policy name: {policy_name}")
            return

        safe_policy = SQLValidator.quote_identifier(policy_name)
        query = f"DROP POLICY IF EXISTS {safe_policy} ON knowledge_bases"
        await self.db_manager.execute(query)

        logger.info(f"Dropped RLS policy for KB {kb_id}")

    async def create_atom_policy(self, kb_id: int) -> None:
        """为知识原子创建 RLS 策略

        Args:
            kb_id: 知识库 ID
        """
        # 验证 kb_id 是整数
        if not isinstance(kb_id, int) or kb_id < 0:
            logger.error(f"Invalid kb_id: {kb_id}")
            raise ValueError(f"Invalid kb_id: {kb_id}")

        policy_name = f"atom_kb_{kb_id}_policy"

        # 验证策略名（防止注入）
        if not SQLValidator.validate_identifier(policy_name):
            logger.error(f"Invalid policy name: {policy_name}")
            raise ValueError(f"Invalid policy name: {policy_name}")

        safe_policy = SQLValidator.quote_identifier(policy_name)

        # 创建策略：允许成员访问原子
        # kb_id 已验证为整数，直接使用是安全的
        query = f"""
            CREATE POLICY {safe_policy} ON atoms
            FOR ALL
            USING (
                kb_id IN (
                    SELECT kb_id FROM kb_members
                    WHERE user_id = current_setting('llmwiki.current_user_id')::TEXT
                    AND kb_id = {kb_id}
                )
            )
        """

        await self.db_manager.execute(query)
        logger.info(f"Created RLS policy for atoms in KB {kb_id}")

    async def drop_atom_policy(self, kb_id: int) -> None:
        """删除知识原子的 RLS 策略

        Args:
            kb_id: 知识库 ID
        """
        # 验证 kb_id 是整数
        if not isinstance(kb_id, int) or kb_id < 0:
            logger.error(f"Invalid kb_id: {kb_id}")
            return

        policy_name = f"atom_kb_{kb_id}_policy"

        # 验证策略名（防止注入）
        if not SQLValidator.validate_identifier(policy_name):
            logger.error(f"Invalid policy name: {policy_name}")
            return

        safe_policy = SQLValidator.quote_identifier(policy_name)
        query = f"DROP POLICY IF EXISTS {safe_policy} ON atoms"
        await self.db_manager.execute(query)

        logger.info(f"Dropped RLS policy for atoms in KB {kb_id}")

    async def check_access(self, user_id: str, kb_id: int, action: str) -> bool:
        """检查用户是否有访问权限

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            action: 操作类型 (read/write/delete)

        Returns:
            是否有权限
        """
        # 验证参数
        if not isinstance(kb_id, int) or kb_id < 0:
            logger.error(f"Invalid kb_id: {kb_id}")
            return False

        # 验证 action（白名单检查）
        allowed_actions = ['read', 'write', 'delete', 'manage']
        if action not in allowed_actions:
            logger.error(f"Invalid action: {action}")
            return False

        # 查询用户成员关系
        query = """
            SELECT role FROM kb_members
            WHERE user_id = $1 AND kb_id = $2
        """

        result = await self.db_manager.fetch_one(query, user_id, kb_id)

        if not result:
            # 检查是否是所有者
            owner_query = """
                SELECT owner_id FROM knowledge_bases
                WHERE id = $1
            """
            owner_result = await self.db_manager.fetch_one(owner_query, kb_id)

            if owner_result and owner_result['owner_id'] == user_id:
                return True

            return False

        # 根据角色判断权限
        role = result['role']
        role_permissions = {
            'owner': ['read', 'write', 'delete', 'manage'],
            'editor': ['read', 'write'],
            'reader': ['read']
        }

        return action in role_permissions.get(role, [])

    async def get_accessible_kbs(self, user_id: str) -> List[int]:
        """获取用户可访问的所有知识库

        Args:
            user_id: 用户 ID

        Returns:
            知识库 ID 列表
        """
        query = """
            SELECT DISTINCT kb_id FROM kb_members
            WHERE user_id = $1
            UNION
            SELECT id as kb_id FROM knowledge_bases
            WHERE owner_id = $1
        """

        results = await self.db_manager.fetch_all(query, user_id)
        return [r['kb_id'] for r in results]

    async def add_user_to_kb(
        self,
        user_id: str,
        kb_id: int,
        role: str = 'reader'
    ) -> bool:
        """将用户添加到知识库

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            role: 角色

        Returns:
            是否成功
        """
        # 验证参数
        if not isinstance(kb_id, int) or kb_id < 0:
            logger.error(f"Invalid kb_id: {kb_id}")
            return False

        # 验证角色（白名单检查）
        allowed_roles = ['owner', 'editor', 'reader']
        if role not in allowed_roles:
            logger.error(f"Invalid role: {role}")
            return False

        query = """
            INSERT INTO kb_members (kb_id, user_id, role, joined_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (kb_id, user_id)
            DO UPDATE SET role = $3, updated_at = NOW()
        """

        try:
            await self.db_manager.execute(query, kb_id, user_id, role)
            logger.info(f"Added user {user_id} to KB {kb_id} as {role}")
            return True
        except Exception as e:
            logger.error(f"Failed to add user to KB: {e}")
            return False

    async def remove_user_from_kb(self, user_id: str, kb_id: int) -> bool:
        """从知识库移除用户

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            是否成功
        """
        query = """
            DELETE FROM kb_members
            WHERE kb_id = $1 AND user_id = $2
        """

        try:
            await self.db_manager.execute(query, kb_id, user_id)
            logger.info(f"Removed user {user_id} from KB {kb_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove user from KB: {e}")
            return False

    async def close(self) -> None:
        """关闭 RLS 管理器"""
        self._current_user_id = None
        self._current_user_roles.clear()
        logger.info("RLSManager closed")