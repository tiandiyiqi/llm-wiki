"""权限与访问控制模块，支持三级角色、Token 认证、IP 白名单、用户会话管理.

集成 RBAC 和 RLS 系统，提供细粒度的权限控制。
"""

import asyncio
import getpass
import hashlib
import json
import logging
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

import bcrypt
from cryptography.fernet import Fernet, InvalidToken

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

        # Token 加密密钥文件路径
        self.key_path = kb_dir / '.llm-wiki' / '.token-key'
        self._cipher: Optional[Fernet] = None

        # Token 哈希索引（用于快速查找）
        self._token_hash_index: Dict[str, str] = {}  # hash -> encrypted_token

        self.config = self._load_config()

        # 初始化哈希索引
        self._build_token_hash_index()

        # RBAC 和 RLS 管理器（延迟初始化）
        self._rbac: Optional['RBACManager'] = None
        self._rls: Optional['RLSManager'] = None
        self._permission_middleware: Optional['PermissionMiddleware'] = None

        # SSO 相关（延迟初始化）
        self._sso_provider: Optional[Any] = None
        self._session_manager: Optional[Any] = None  # RedisSessionManager 或 SessionManager

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
        # 设置文件权限为 600（仅所有者可读写）
        try:
            os.chmod(self.config_path, 0o600)
        except OSError as e:
            logger.warning(f"Failed to set file permissions: {e}")

    def _build_token_hash_index(self) -> None:
        """构建 Token 哈希索引（用于快速查找）.

        遍历所有存储的 Token，解密后计算哈希，建立索引。
        这样在验证 Token 时，可以直接通过哈希查找，无需遍历所有 Token。
        """
        self._token_hash_index.clear()
        tokens_dict = self.config.get('tokens', {})

        for encrypted_token, token_info in tokens_dict.items():
            try:
                if token_info.get('encrypted'):
                    # 解密 Token
                    decrypted = self._decrypt_token(encrypted_token)
                    if decrypted:
                        # 计算哈希
                        token_hash = hashlib.sha256(decrypted.encode()).hexdigest()
                        self._token_hash_index[token_hash] = encrypted_token
                else:
                    # 兼容旧版本：未加密的 Token
                    token_hash = hashlib.sha256(encrypted_token.encode()).hexdigest()
                    self._token_hash_index[token_hash] = encrypted_token
            except Exception as e:
                logger.warning(f"Failed to build hash index for token: {e}")
                continue

        logger.debug(f"Built token hash index: {len(self._token_hash_index)} tokens")

    def _get_or_create_cipher(self) -> Fernet:
        """获取或创建 Fernet 加密器.

        优先级：
        1. 环境变量 TOKEN_ENCRYPTION_KEY
        2. 本地密钥文件 .llm-wiki/.token-key
        3. 生成新密钥并保存到本地文件

        Returns:
            Fernet 加密器实例
        """
        if self._cipher is not None:
            return self._cipher

        # 尝试从环境变量获取密钥
        key = os.environ.get('TOKEN_ENCRYPTION_KEY')

        if key:
            try:
                self._cipher = Fernet(key.encode())
                return self._cipher
            except Exception as e:
                logger.warning(f"Invalid TOKEN_ENCRYPTION_KEY in environment: {e}")

        # 尝试从本地文件加载密钥
        if self.key_path.exists():
            try:
                key = self.key_path.read_text(encoding='utf-8').strip()
                self._cipher = Fernet(key.encode())
                return self._cipher
            except Exception as e:
                logger.warning(f"Failed to load encryption key from file: {e}")

        # 生成新密钥
        key = Fernet.generate_key().decode()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_text(key, encoding='utf-8')

        # 设置密钥文件权限为 600
        try:
            os.chmod(self.key_path, 0o600)
        except OSError as e:
            logger.warning(f"Failed to set key file permissions: {e}")

        logger.info("Generated new token encryption key")

        self._cipher = Fernet(key.encode())
        return self._cipher

    def _encrypt_token(self, token: str) -> str:
        """加密 Token.

        Args:
            token: 明文 Token

        Returns:
            加密后的 Token（Base64 编码）
        """
        cipher = self._get_or_create_cipher()
        encrypted = cipher.encrypt(token.encode('utf-8'))
        return encrypted.decode('utf-8')

    def _decrypt_token(self, encrypted_token: str) -> Optional[str]:
        """解密 Token.

        Args:
            encrypted_token: 加密的 Token

        Returns:
            解密后的明文 Token，失败返回 None
        """
        try:
            cipher = self._get_or_create_cipher()
            decrypted = cipher.decrypt(encrypted_token.encode('utf-8'))
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("Invalid encrypted token (may be corrupted or wrong key)")
            return None
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            return None

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
        """为用户生成 API Token（加密存储）.

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

        # 加密存储 Token
        encrypted_token = self._encrypt_token(token)

        self.config.setdefault('tokens', {})[encrypted_token] = {
            'username': username,
            'role': user_role,
            'created': datetime.now().isoformat(),
            'encrypted': True,  # 标记为加密存储
        }
        self._save_config()

        # 更新哈希索引
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self._token_hash_index[token_hash] = encrypted_token

        # 返回原始 Token（用户需要保存）
        return token

    def revoke_token(self, token: str) -> bool:
        """吊销 Token（使用哈希索引优化性能）.

        Args:
            token: Token 字符串（明文）

        Returns:
            是否成功
        """
        # 计算 Token 哈希
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # 使用哈希索引快速查找
        encrypted_token = self._token_hash_index.get(token_hash)

        if encrypted_token:
            # 找到匹配的 Token，删除
            if encrypted_token in self.config.get('tokens', {}):
                del self.config['tokens'][encrypted_token]
                self._save_config()
                # 从索引中移除
                del self._token_hash_index[token_hash]
                return True

        # 哈希索引未找到，降级到遍历查找
        logger.warning("Token hash index miss during revoke, falling back to linear search")
        tokens_dict = self.config.get('tokens', {})

        for enc_token, token_info in tokens_dict.items():
            if token_info.get('encrypted'):
                decrypted = self._decrypt_token(enc_token)
                if decrypted and decrypted == token:
                    del self.config['tokens'][enc_token]
                    self._save_config()
                    # 重建索引
                    self._build_token_hash_index()
                    return True
            else:
                # 兼容旧版本：直接比较未加密的 Token
                if enc_token == token:
                    del self.config['tokens'][enc_token]
                    self._save_config()
                    # 重建索引
                    self._build_token_hash_index()
                    return True

        return False

    def validate_token(self, token: str) -> Optional[str]:
        """验证 Token，返回角色（使用哈希索引优化性能）.

        支持两种 Token 类型：
        1. 本地 API Token（Fernet 加密存储）
        2. SSO JWT Token（以 'eyJ' 开头）

        Args:
            token: Token 字符串（明文）

        Returns:
            角色字符串，验证失败返回 None
        """
        # 检测 JWT 格式 token（SSO）
        if token.startswith('eyJ') and self._sso_provider is not None:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 在已有事件循环中无法直接 await，返回 None
                    # SSO JWT 应在异步上下文中通过 validate_sso_token 验证
                    return None
                claims = loop.run_until_complete(self._sso_provider.validate_sso_token(token))
            except Exception:
                claims = None
            if claims:
                # 从 JWT claims 中提取角色
                roles = claims.get('roles', [])
                if isinstance(roles, list) and 'admin' in roles:
                    return 'admin'
                return 'user'
            return None

        # 本地 API Token 验证
        # 计算 Token 哈希
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # 使用哈希索引快速查找
        encrypted_token = self._token_hash_index.get(token_hash)

        if encrypted_token:
            # 找到匹配的 Token，返回角色
            token_info = self.config.get('tokens', {}).get(encrypted_token)
            if token_info:
                return token_info.get('role', 'reader')

        # 哈希索引未找到，可能索引未同步，降级到遍历查找
        # 这种情况只在以下场景发生：
        # 1. 索引未正确初始化
        # 2. Token 是旧版本未加密的
        logger.warning("Token hash index miss, falling back to linear search")
        tokens_dict = self.config.get('tokens', {})

        for enc_token, token_info in tokens_dict.items():
            # 如果 Token 标记为加密
            if token_info.get('encrypted'):
                decrypted = self._decrypt_token(enc_token)
                if decrypted and decrypted == token:
                    # 重建索引以提高后续查找性能
                    self._build_token_hash_index()
                    return token_info.get('role', 'reader')
            else:
                # 兼容旧版本：直接比较未加密的 Token
                if enc_token == token:
                    # 重建索引以提高后续查找性能
                    self._build_token_hash_index()
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
        for encrypted_token, info in self.config.get('tokens', {}).items():
            # 尝试解密 Token（如果已加密）
            if info.get('encrypted'):
                decrypted = self._decrypt_token(encrypted_token)
                if decrypted:
                    display_token = decrypted[:8] + '...' + decrypted[-4:]
                else:
                    display_token = '<encrypted>'
            else:
                # 兼容旧版本未加密的 Token
                display_token = encrypted_token[:8] + '...' + encrypted_token[-4:]

            tokens.append({
                'token': display_token,
                'username': info.get('username', ''),
                'role': info.get('role', 'reader'),
                'created': info.get('created', ''),
                'encrypted': info.get('encrypted', False),
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

    # --- SSO 相关方法 ---

    def setup_sso(self, sso_provider: Any, session_manager: Any) -> None:
        """配置 SSO 认证提供者和会话管理器.

        Args:
            sso_provider: SSOAuthProvider 实例
            session_manager: SessionManager 或 RedisSessionManager 实例
        """
        self._sso_provider = sso_provider
        self._session_manager = session_manager
        logger.info("SSO provider configured for AuthManager")

    def is_sso_enabled(self) -> bool:
        """检查 SSO 是否已启用.

        Returns:
            SSO 提供者是否已配置
        """
        return self._sso_provider is not None

    async def sso_login(self, redirect_url: Optional[str] = None) -> Any:
        """发起 SSO 登录.

        Args:
            redirect_url: 登录成功后的重定向 URL

        Returns:
            SSOAuthResult 认证结果

        Raises:
            RuntimeError: SSO 未启用
        """
        if self._sso_provider is None:
            raise RuntimeError("SSO is not enabled. Call setup_sso() first.")
        return await self._sso_provider.initiate_login(redirect_url=redirect_url)

    async def sso_callback(self, code: str, state: str) -> Any:
        """处理 SSO 登录回调.

        Args:
            code: OAuth2 授权码
            state: CSRF 防护的 state 参数

        Returns:
            SSOAuthResult 认证结果

        Raises:
            RuntimeError: SSO 未启用
        """
        if self._sso_provider is None:
            raise RuntimeError("SSO is not enabled. Call setup_sso() first.")
        return await self._sso_provider.handle_callback(code=code, state=state)

    async def sso_logout(self, session_id: str) -> Any:
        """处理 SSO 登出.

        Args:
            session_id: 会话 ID

        Returns:
            SSOAuthResult 包含 Casdoor 登出 URL

        Raises:
            RuntimeError: SSO 未启用
        """
        if self._sso_provider is None:
            raise RuntimeError("SSO is not enabled. Call setup_sso() first.")

        # 销毁本地会话
        if self._session_manager is not None:
            if hasattr(self._session_manager, 'destroy_session'):
                if asyncio.iscoroutinefunction(self._session_manager.destroy_session):
                    await self._session_manager.destroy_session(session_id)
                else:
                    self._session_manager.destroy_session(session_id)

        return await self._sso_provider.handle_logout(session_id=session_id)

    async def validate_sso_token(self, token: str) -> Optional[Dict]:
        """验证 SSO JWT Token.

        Args:
            token: JWT 令牌字符串

        Returns:
            解码后的 JWT claims，验证失败返回 None
        """
        if self._sso_provider is None:
            return None
        return await self._sso_provider.validate_sso_token(token)

    async def validate_sso_session(self, session_id: str) -> Optional[Dict]:
        """从会话管理器获取 SSO 会话信息.

        Args:
            session_id: 会话 ID

        Returns:
            包含 user_id 和 roles 的字典，不存在返回 None
        """
        if self._session_manager is None:
            return None

        try:
            if hasattr(self._session_manager, 'get_session'):
                if asyncio.iscoroutinefunction(self._session_manager.get_session):
                    session = await self._session_manager.get_session(session_id)
                else:
                    session = self._session_manager.get_session(session_id)

                if session is None:
                    return None

                # 兼容 dict 和 Session 对象
                if isinstance(session, dict):
                    return {
                        'user_id': session.get('user_id', ''),
                        'roles': session.get('metadata', {}).get('roles', []),
                    }
                # Session dataclass
                return {
                    'user_id': getattr(session, 'user_id', ''),
                    'roles': getattr(session, 'metadata', {}).get('roles', []),
                }
        except Exception as exc:
            logger.error("Failed to validate SSO session: %s", exc)
            return None
