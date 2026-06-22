"""RBAC（基于角色的访问控制）数据库模型.

提供角色、权限和用户角色关系的数据库持久化存储。
"""

import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


# 数据库表结构定义（用于创建表）
RBAC_SCHEMA = """
-- 角色表
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 权限表
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource_type VARCHAR(50),
    action VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 角色权限关联表
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER,
    PRIMARY KEY (role_id, permission_id)
);

-- 用户角色关联表
CREATE TABLE IF NOT EXISTS user_roles (
    user_id VARCHAR(255) NOT NULL,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER,
    expires_at TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_permissions_name ON permissions(name);
"""

# 默认系统角色
DEFAULT_ROLES = [
    {
        'name': 'admin',
        'description': '系统管理员，拥有所有权限',
        'is_system': True,
    },
    {
        'name': 'editor',
        'description': '编辑者，可以创建和编辑内容',
        'is_system': True,
    },
    {
        'name': 'viewer',
        'description': '查看者，只能查看内容',
        'is_system': True,
    },
    {
        'name': 'guest',
        'description': '访客，只有基本访问权限',
        'is_system': True,
    },
]

# 默认权限
DEFAULT_PERMISSIONS = [
    # 知识库权限
    {'name': 'kb:create', 'description': '创建知识库', 'resource_type': 'kb', 'action': 'create'},
    {'name': 'kb:read', 'description': '查看知识库', 'resource_type': 'kb', 'action': 'read'},
    {'name': 'kb:update', 'description': '更新知识库', 'resource_type': 'kb', 'action': 'update'},
    {'name': 'kb:delete', 'description': '删除知识库', 'resource_type': 'kb', 'action': 'delete'},

    # 知识原子权限
    {'name': 'atom:create', 'description': '创建知识原子', 'resource_type': 'atom', 'action': 'create'},
    {'name': 'atom:read', 'description': '查看知识原子', 'resource_type': 'atom', 'action': 'read'},
    {'name': 'atom:update', 'description': '更新知识原子', 'resource_type': 'atom', 'action': 'update'},
    {'name': 'atom:delete', 'description': '删除知识原子', 'resource_type': 'atom', 'action': 'delete'},

    # 用户管理权限
    {'name': 'user:create', 'description': '创建用户', 'resource_type': 'user', 'action': 'create'},
    {'name': 'user:read', 'description': '查看用户', 'resource_type': 'user', 'action': 'read'},
    {'name': 'user:update', 'description': '更新用户', 'resource_type': 'user', 'action': 'update'},
    {'name': 'user:delete', 'description': '删除用户', 'resource_type': 'user', 'action': 'delete'},

    # 系统管理权限
    {'name': 'system:admin', 'description': '系统管理', 'resource_type': 'system', 'action': 'admin'},
    {'name': 'system:config', 'description': '系统配置', 'resource_type': 'system', 'action': 'config'},
]

# 默认角色权限映射
DEFAULT_ROLE_PERMISSIONS = {
    'admin': [
        'kb:create', 'kb:read', 'kb:update', 'kb:delete',
        'atom:create', 'atom:read', 'atom:update', 'atom:delete',
        'user:create', 'user:read', 'user:update', 'user:delete',
        'system:admin', 'system:config',
    ],
    'editor': [
        'kb:read', 'kb:update',
        'atom:create', 'atom:read', 'atom:update', 'atom:delete',
    ],
    'viewer': [
        'kb:read',
        'atom:read',
    ],
    'guest': [
        'atom:read',
    ],
}


class RBACManager:
    """RBAC 管理器.

    管理角色、权限和用户角色关系。
    """

    def __init__(self, db_manager):
        """初始化 RBAC 管理器.

        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self._initialized = False

    async def initialize(self) -> None:
        """初始化 RBAC 系统.

        创建表结构并插入默认数据。
        """
        if self._initialized:
            return

        # 创建表结构
        await self.db_manager.execute(RBAC_SCHEMA)
        logger.info("RBAC tables created")

        # 插入默认角色
        await self._insert_default_roles()

        # 插入默认权限
        await self._insert_default_permissions()

        # 建立默认角色权限关系
        await self._insert_default_role_permissions()

        self._initialized = True
        logger.info("RBACManager initialized")

    async def _insert_default_roles(self) -> None:
        """插入默认角色."""
        for role in DEFAULT_ROLES:
            query = """
                INSERT INTO roles (name, description, is_system)
                VALUES ($1, $2, $3)
                ON CONFLICT (name) DO NOTHING
            """
            await self.db_manager.execute(
                query,
                role['name'],
                role['description'],
                role['is_system']
            )

        logger.info("Default roles inserted")

    async def _insert_default_permissions(self) -> None:
        """插入默认权限."""
        for perm in DEFAULT_PERMISSIONS:
            query = """
                INSERT INTO permissions (name, description, resource_type, action)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (name) DO NOTHING
            """
            await self.db_manager.execute(
                query,
                perm['name'],
                perm['description'],
                perm.get('resource_type'),
                perm.get('action')
            )

        logger.info("Default permissions inserted")

    async def _insert_default_role_permissions(self) -> None:
        """插入默认角色权限关系."""
        for role_name, permissions in DEFAULT_ROLE_PERMISSIONS.items():
            # 获取角色 ID
            role_query = "SELECT id FROM roles WHERE name = $1"
            role_result = await self.db_manager.fetch_one(role_query, role_name)

            if not role_result:
                continue

            role_id = role_result['id']

            for perm_name in permissions:
                # 获取权限 ID
                perm_query = "SELECT id FROM permissions WHERE name = $1"
                perm_result = await self.db_manager.fetch_one(perm_query, perm_name)

                if not perm_result:
                    continue

                perm_id = perm_result['id']

                # 插入角色权限关系
                insert_query = """
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                """
                await self.db_manager.execute(insert_query, role_id, perm_id)

        logger.info("Default role permissions inserted")

    async def create_role(
        self,
        name: str,
        description: str,
        is_system: bool = False
    ) -> Optional[int]:
        """创建新角色.

        Args:
            name: 角色名称
            description: 角色描述
            is_system: 是否系统角色

        Returns:
            角色 ID，失败返回 None
        """
        query = """
            INSERT INTO roles (name, description, is_system)
            VALUES ($1, $2, $3)
            RETURNING id
        """

        try:
            result = await self.db_manager.fetch_one(query, name, description, is_system)
            logger.info(f"Created role: {name}")
            return result['id'] if result else None
        except Exception as e:
            logger.error(f"Failed to create role {name}: {e}")
            return None

    async def delete_role(self, role_id: int) -> bool:
        """删除角色.

        Args:
            role_id: 角色 ID

        Returns:
            是否成功
        """
        # 检查是否是系统角色
        check_query = "SELECT is_system FROM roles WHERE id = $1"
        result = await self.db_manager.fetch_one(check_query, role_id)

        if result and result['is_system']:
            logger.warning(f"Cannot delete system role: {role_id}")
            return False

        query = "DELETE FROM roles WHERE id = $1 RETURNING id"
        result = await self.db_manager.fetch_one(query, role_id)

        if result:
            logger.info(f"Deleted role: {role_id}")
            return True
        return False

    async def assign_role_to_user(
        self,
        user_id: str,
        role_id: int,
        assigned_by: Optional[int] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """给用户分配角色.

        Args:
            user_id: 用户 ID
            role_id: 角色 ID
            assigned_by: 分配者 ID
            expires_at: 过期时间

        Returns:
            是否成功
        """
        query = """
            INSERT INTO user_roles (user_id, role_id, assigned_by, expires_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, role_id)
            DO UPDATE SET
                assigned_by = $3,
                expires_at = $4,
                assigned_at = CURRENT_TIMESTAMP
        """

        try:
            await self.db_manager.execute(query, user_id, role_id, assigned_by, expires_at)
            logger.info(f"Assigned role {role_id} to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to assign role: {e}")
            return False

    async def revoke_role_from_user(self, user_id: str, role_id: int) -> bool:
        """撤销用户的角色.

        Args:
            user_id: 用户 ID
            role_id: 角色 ID

        Returns:
            是否成功
        """
        query = """
            DELETE FROM user_roles
            WHERE user_id = $1 AND role_id = $2
            RETURNING user_id
        """

        result = await self.db_manager.fetch_one(query, user_id, role_id)
        if result:
            logger.info(f"Revoked role {role_id} from user {user_id}")
            return True
        return False

    async def get_user_roles(self, user_id: str) -> List[str]:
        """获取用户的所有角色.

        Args:
            user_id: 用户 ID

        Returns:
            角色名称列表
        """
        query = """
            SELECT r.name
            FROM roles r
            INNER JOIN user_roles ur ON r.id = ur.role_id
            WHERE ur.user_id = $1
            AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
        """

        results = await self.db_manager.fetch_all(query, user_id)
        return [r['name'] for r in results]

    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户的所有权限.

        Args:
            user_id: 用户 ID

        Returns:
            权限名称集合
        """
        query = """
            SELECT DISTINCT p.name
            FROM permissions p
            INNER JOIN role_permissions rp ON p.id = rp.permission_id
            INNER JOIN user_roles ur ON rp.role_id = ur.role_id
            WHERE ur.user_id = $1
            AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
        """

        results = await self.db_manager.fetch_all(query, user_id)
        return {r['name'] for r in results}

    async def check_permission(self, user_id: str, permission: str) -> bool:
        """检查用户是否有指定权限.

        Args:
            user_id: 用户 ID
            permission: 权限名称

        Returns:
            是否有权限
        """
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM role_permissions rp
                INNER JOIN user_roles ur ON rp.role_id = ur.role_id
                INNER JOIN permissions p ON rp.permission_id = p.id
                WHERE ur.user_id = $1
                AND p.name = $2
                AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
            ) AS has_permission
        """

        result = await self.db_manager.fetch_one(query, user_id, permission)
        return result['has_permission'] if result else False

    async def grant_permission_to_role(self, role_id: int, permission_id: int) -> bool:
        """给角色授权.

        Args:
            role_id: 角色 ID
            permission_id: 权限 ID

        Returns:
            是否成功
        """
        query = """
            INSERT INTO role_permissions (role_id, permission_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """

        try:
            await self.db_manager.execute(query, role_id, permission_id)
            logger.info(f"Granted permission {permission_id} to role {role_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to grant permission: {e}")
            return False

    async def revoke_permission_from_role(self, role_id: int, permission_id: int) -> bool:
        """撤销角色的权限.

        Args:
            role_id: 角色 ID
            permission_id: 权限 ID

        Returns:
            是否成功
        """
        query = """
            DELETE FROM role_permissions
            WHERE role_id = $1 AND permission_id = $2
            RETURNING role_id
        """

        result = await self.db_manager.fetch_one(query, role_id, permission_id)
        if result:
            logger.info(f"Revoked permission {permission_id} from role {role_id}")
            return True
        return False

    async def list_roles(self) -> List[Dict]:
        """列出所有角色.

        Returns:
            角色列表
        """
        query = """
            SELECT id, name, description, is_system, created_at
            FROM roles
            ORDER BY id
        """

        return await self.db_manager.fetch_all(query)

    async def list_permissions(self) -> List[Dict]:
        """列出所有权限.

        Returns:
            权限列表
        """
        query = """
            SELECT id, name, description, resource_type, action
            FROM permissions
            ORDER BY resource_type, action
        """

        return await self.db_manager.fetch_all(query)
