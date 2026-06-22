"""权限与访问控制模块，支持三级角色、Token 认证、IP 白名单、用户会话管理.

集成 RBAC 和 RLS 系统，提供细粒度的权限控制。
"""

import getpass
import json
import logging
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

import bcrypt

# 配置日志
logger = logging.getLogger(__name__)

# 条件导入，避免循环依赖
if TYPE_CHECKING:
    from lib.auth.rbac import RBACManager, Permission
    from lib.auth.rls_manager import RLSManager
    from lib.auth.permission_middleware import PermissionMiddleware


# 角色权限等级
ROLE_LEVELS = {
    'reader': 1,   # 只读
    'editor': 2,   # 编辑
    'admin': 3,    # 管理
}

# 操作所需权限等级
ACTION_LEVELS = {
    'view': 1,
    'query': 1,
    'export': 1,
    'comment': 1,
    'favorite': 1,
    'rate': 1,
    'ingest': 2,
    'edit': 2,
    'publish': 2,
    'archive': 2,
    'submit': 2,
    'delete': 3,
    'approve': 3,
    'reject': 3,
    'deprecate': 3,
    'manage': 3,
}


def hash_password(password: str) -> str:
    """使用 bcrypt 安全哈希密码.

    Args:
        password: 明文密码

    Returns:
        哈希后的密码字符串
    """
    # 生成盐（rounds=12 表示 2^12 次迭代）
    salt = bcrypt.gensalt(rounds=12)
    # 哈希密码
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, stored_hash: str) -> bool:
    """验证密码是否匹配.

    Args:
        password: 明文密码
        stored_hash: 存储的哈希值

    Returns:
        是否匹配
    """
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            stored_hash.encode('utf-8')
        )
    except Exception:
        return False


class AuthManager:
    """权限管理器，管理用户、Token、IP 白名单、用户会话.

    集成 RBAC 和 RLS 系统，提供细粒度的权限控制。
    """

    def __init__(self, kb_dir: Path):
        """初始化权限管理器.

        Args:
            kb_dir: 知识库目录
        """
        self.kb_dir = kb_dir
        self.config_path = kb_dir / '.kb-access.json'
        self.session_path = kb_dir / '.llm-wiki' / 'current-user.json'
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()

        # RBAC 和 RLS 管理器（延迟初始化）
        self._rbac: Optional['RBACManager'] = None
        self._rls: Optional['RLSManager'] = None
        self._permission_middleware: Optional['PermissionMiddleware'] = None

    @property
    def rbac(self) -> Optional['RBACManager']:
        """获取 RBAC 管理器"""
        return self._rbac

    @property
    def rls(self) -> Optional['RLSManager']:
        """获取 RLS 管理器"""
        return self._rls

    @property
    def permission_middleware(self) -> Optional['PermissionMiddleware']:
        """获取权限中间件"""
        return self._permission_middleware

    def _load_config(self) -> Dict:
        """加载权限配置."""
        default = {
            'users': {},
            'tokens': {},
            'ip_whitelist': [],
            'enabled': False,
        }
        try:
            if self.config_path.exists():
                return json.loads(self.config_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return default

    def _save_config(self) -> None:
        """保存权限配置."""
        self.config_path.write_text(
            json.dumps(self.config, indent=2, ensure_ascii=False), encoding='utf-8'
        )

    def enable(self) -> None:
        """启用权限控制."""
        self.config['enabled'] = True
        self._save_config()

    def disable(self) -> None:
        """禁用权限控制."""
        self.config['enabled'] = False
        self._save_config()

    def is_enabled(self) -> bool:
        """是否启用权限控制."""
        return self.config.get('enabled', False)

    def add_user(self, username: str, role: str = 'reader',
                 password: Optional[str] = None) -> bool:
        """添加用户.

        Args:
            username: 用户名
            role: 角色（reader/editor/admin）
            password: 密码（明文，内部会哈希存储）

        Returns:
            是否成功
        """
        if role not in ROLE_LEVELS:
            return False
        self.config.setdefault('users', {})[username] = {
            'role': role,
            'password': hash_password(password) if password else '',
            'created': datetime.now().isoformat(),
        }
        self._save_config()
        return True

    def remove_user(self, username: str) -> bool:
        """移除用户."""
        if username in self.config.get('users', {}):
            del self.config['users'][username]
            # 同时移除该用户的所有 Token
            tokens = self.config.get('tokens', {})
            to_remove = [t for t, info in tokens.items() if info.get('username') == username]
            for t in to_remove:
                del tokens[t]
            self._save_config()
            # 如果当前登录用户被删除，清除会话
            current = self.get_current_user()
            if current and current.get('username') == username:
                self.logout()
            return True
        return False

    def get_user_role(self, username: str) -> Optional[str]:
        """获取用户角色."""
        user = self.config.get('users', {}).get(username)
        return user.get('role') if user else None

    def update_user_role(self, username: str, role: str) -> bool:
        """更新用户角色.

        Args:
            username: 用户名
            role: 新角色

        Returns:
            是否成功
        """
        if role not in ROLE_LEVELS:
            return False
        if username not in self.config.get('users', {}):
            return False
        self.config['users'][username]['role'] = role
        self._save_config()
        return True

    def change_password(self, username: str, new_password: str) -> bool:
        """修改用户密码.

        Args:
            username: 用户名
            new_password: 新密码（明文）

        Returns:
            是否成功
        """
        if username not in self.config.get('users', {}):
            return False
        self.config['users'][username]['password'] = hash_password(new_password)
        self._save_config()
        return True

    def generate_token(self, username: str, role: Optional[str] = None) -> Optional[str]:
        """为用户生成 API Token.

        Args:
            username: 用户名
            role: 角色覆盖（可选）

        Returns:
            Token 字符串，失败返回 None
        """
        if username not in self.config.get('users', {}):
            return None
        token = secrets.token_urlsafe(32)
        user_role = role or self.config['users'][username].get('role', 'reader')
        self.config.setdefault('tokens', {})[token] = {
            'username': username,
            'role': user_role,
            'created': datetime.now().isoformat(),
        }
        self._save_config()
        return token

    def revoke_token(self, token: str) -> bool:
        """吊销 Token."""
        if token in self.config.get('tokens', {}):
            del self.config['tokens'][token]
            self._save_config()
            return True
        return False

    def validate_token(self, token: str) -> Optional[str]:
        """验证 Token，返回角色.

        Args:
            token: Token 字符串

        Returns:
            角色字符串，无效返回 None
        """
        token_info = self.config.get('tokens', {}).get(token)
        if token_info:
            return token_info.get('role', 'reader')
        return None

    def add_ip_whitelist(self, ip: str) -> None:
        """添加 IP 到白名单."""
        whitelist = self.config.setdefault('ip_whitelist', [])
        if ip not in whitelist:
            whitelist.append(ip)
            self._save_config()

    def remove_ip_whitelist(self, ip: str) -> bool:
        """从白名单移除 IP."""
        whitelist = self.config.get('ip_whitelist', [])
        if ip in whitelist:
            whitelist.remove(ip)
            self._save_config()
            return True
        return False

    def check_ip(self, ip: str) -> bool:
        """检查 IP 是否在白名单（空白名单表示允许所有）."""
        whitelist = self.config.get('ip_whitelist', [])
        if not whitelist:
            return True
        return ip in whitelist

    def check_permission(self, role: str, action: str) -> bool:
        """检查角色是否有权限执行操作.

        Args:
            role: 用户角色
            action: 操作名称

        Returns:
            是否有权限
        """
        role_level = ROLE_LEVELS.get(role, 0)
        action_level = ACTION_LEVELS.get(action, 3)
        return role_level >= action_level

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """用户名密码认证.

        Args:
            username: 用户名
            password: 明文密码

        Returns:
            角色字符串，失败返回 None
        """
        user = self.config.get('users', {}).get(username)
        if not user:
            return None
        stored_hash = user.get('password', '')
        if not stored_hash:
            return None
        if verify_password(password, stored_hash):
            return user.get('role', 'reader')
        return None

    # ========================================================================
    # 用户会话管理（当前登录用户上下文）
    # ========================================================================

    def login(self, username: str, password: str) -> bool:
        """用户登录，验证密码并持久化会话.

        Args:
            username: 用户名
            password: 明文密码

        Returns:
            是否登录成功
        """
        role = self.authenticate(username, password)
        if role is None:
            return False
        session = {
            'username': username,
            'role': role,
            'login_at': datetime.now().isoformat(),
        }
        self.session_path.write_text(
            json.dumps(session, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        return True

    def logout(self) -> bool:
        """退出登录，清除会话.

        Returns:
            是否成功
        """
        if self.session_path.exists():
            self.session_path.unlink()
            return True
        return False

    def get_current_user(self) -> Optional[Dict]:
        """获取当前登录用户信息.

        Returns:
            用户信息字典（username/role/login_at），未登录返回 None
        """
        try:
            if self.session_path.exists():
                return json.loads(self.session_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return None

    def get_current_username(self) -> str:
        """获取当前登录用户名，未登录返回 'anonymous'."""
        user = self.get_current_user()
        return user.get('username', 'anonymous') if user else 'anonymous'

    def get_current_role(self) -> str:
        """获取当前登录用户角色，未登录返回 'guest'."""
        user = self.get_current_user()
        return user.get('role', 'guest') if user else 'guest'

    def is_logged_in(self) -> bool:
        """是否已登录."""
        return self.get_current_user() is not None

    def require_user(self) -> str:
        """要求用户已登录，返回用户名；未登录时返回 'anonymous' 并打印警告.

        Returns:
            当前用户名
        """
        user = self.get_current_user()
        if user:
            return user.get('username', 'anonymous')
        print("   ⚠️  未登录，操作将以 anonymous 身份执行（建议先执行 'llm-wiki login'）")
        return 'anonymous'

    def require_permission(self, action: str) -> bool:
        """检查当前用户是否有权限执行操作.

        Args:
            action: 操作名称

        Returns:
            是否有权限
        """
        role = self.get_current_role()
        # guest 角色仅允许只读操作
        if role == 'guest':
            return ACTION_LEVELS.get(action, 3) <= 1
        return self.check_permission(role, action)

    def list_users(self) -> List[Dict]:
        """列出所有用户."""
        users = []
        for username, info in self.config.get('users', {}).items():
            users.append({
                'username': username,
                'role': info.get('role', 'reader'),
                'created': info.get('created', ''),
            })
        return users

    def list_tokens(self) -> List[Dict]:
        """列出所有 Token（脱敏显示）."""
        tokens = []
        for token, info in self.config.get('tokens', {}).items():
            tokens.append({
                'token': token[:8] + '...' + token[-4:],
                'username': info.get('username', ''),
                'role': info.get('role', 'reader'),
                'created': info.get('created', ''),
            })
        return tokens

    # ========================================================================
    # RBAC/RLS 集成方法
    # ========================================================================

    async def initialize_permission_system(
        self,
        db_manager: Optional[Any] = None
    ) -> None:
        """初始化 RBAC 和 RLS 权限系统.

        Args:
            db_manager: 数据库管理器（用于 RLS）
        """
        try:
            # 导入模块
            from lib.auth.rbac import RBACManager
            from lib.auth.rls_manager import RLSManager
            from lib.auth.permission_middleware import PermissionMiddleware

            # 初始化 RBAC
            self._rbac = RBACManager()
            await self._rbac.initialize()
            logger.info("RBAC system initialized")

            # 初始化 RLS（如果有数据库）
            if db_manager:
                self._rls = RLSManager(db_manager)
                await self._rls.initialize()
                logger.info("RLS system initialized")

            # 初始化权限中间件
            if self._rbac and self._rls:
                self._permission_middleware = PermissionMiddleware(
                    self._rbac,
                    self._rls
                )
                await self._permission_middleware.initialize()
                logger.info("Permission middleware initialized")

        except ImportError as e:
            logger.warning(f"Permission modules not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize permission system: {e}")

    async def has_permission(
        self,
        user_id: str,
        kb_id: int,
        permission_name: str
    ) -> bool:
        """检查用户是否有指定权限.

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            permission_name: 权限名称（如 'kb:read'）

        Returns:
            是否有权限
        """
        # 如果没有权限系统，使用旧的权限检查
        if not self._permission_middleware:
            user = self.config.get('users', {}).get(user_id)
            if not user:
                return False
            role = user.get('role', 'reader')
            return self.check_permission(role, permission_name)

        # 使用新的权限系统
        try:
            from lib.auth.rbac import Permission

            # 将权限名称转换为 Permission 枚举
            permission_map = {
                'kb:create': Permission.KB_CREATE,
                'kb:read': Permission.KB_READ,
                'kb:update': Permission.KB_UPDATE,
                'kb:delete': Permission.KB_DELETE,
                'kb:manage': Permission.KB_MANAGE,
                'atom:create': Permission.ATOM_CREATE,
                'atom:read': Permission.ATOM_READ,
                'atom:update': Permission.ATOM_UPDATE,
                'atom:delete': Permission.ATOM_DELETE,
                'member:manage': Permission.MEMBER_MANAGE,
                'admin': Permission.ADMIN,
            }

            permission = permission_map.get(permission_name)
            if not permission:
                logger.warning(f"Unknown permission: {permission_name}")
                return False

            return await self._permission_middleware.check_kb_permission(
                user_id,
                kb_id,
                permission
            )

        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return False

    async def grant_kb_access(
        self,
        user_id: str,
        kb_id: int,
        role: str = 'reader'
    ) -> bool:
        """授予用户对知识库的访问权限.

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            role: 角色（owner/editor/reader）

        Returns:
            是否成功
        """
        if not self._rbac or not self._rls:
            logger.warning("Permission system not initialized")
            return False

        try:
            # 分配角色
            await self._rbac.assign_role(user_id, kb_id, role)

            # 添加到知识库成员
            await self._rls.add_user_to_kb(user_id, kb_id, role)

            logger.info(f"Granted {role} access to user {user_id} for KB {kb_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to grant access: {e}")
            return False

    async def revoke_kb_access(
        self,
        user_id: str,
        kb_id: int
    ) -> bool:
        """撤销用户对知识库的访问权限.

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            是否成功
        """
        if not self._rbac or not self._rls:
            logger.warning("Permission system not initialized")
            return False

        try:
            # 获取用户角色
            roles = await self._rbac.get_user_roles(user_id, kb_id)

            # 撤销所有角色
            for role in roles:
                await self._rbac.revoke_role(user_id, kb_id, role)

            # 从成员表中移除
            await self._rls.remove_user_from_kb(user_id, kb_id)

            logger.info(f"Revoked access for user {user_id} from KB {kb_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke access: {e}")
            return False

    async def get_user_kb_permissions(
        self,
        user_id: str,
        kb_id: int
    ) -> List[str]:
        """获取用户在知识库中的所有权限.

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            权限名称列表
        """
        if not self._rbac:
            return []

        try:
            from lib.auth.rbac import Permission

            permissions = await self._rbac.get_user_permissions(user_id, kb_id)
            return [p.value for p in permissions]

        except Exception as e:
            logger.error(f"Failed to get permissions: {e}")
            return []

    async def close_permission_system(self) -> None:
        """关闭权限系统"""
        try:
            if self._permission_middleware:
                await self._permission_middleware.close()

            if self._rbac:
                await self._rbac.close()

            if self._rls:
                await self._rls.close()

            logger.info("Permission system closed")

        except Exception as e:
            logger.error(f"Failed to close permission system: {e}")
