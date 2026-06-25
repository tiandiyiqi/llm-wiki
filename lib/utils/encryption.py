"""加密工具类

提供统一的加密/解密接口：
- 应用层加密（cryptography.Fernet）
- HMAC 生成（用于索引查询）
- pgcrypto SQL 生成（用于数据库层加密）

PLAN-009: 数据加密存储实现
"""

import os
import hmac
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class EncryptionManager:
    """加密管理器

    提供三种加密功能：

    1. **应用层加密/解密**（Fernet）
       - 用于敏感凭据加密（如 token）
       - 每次加密产生不同密文（包含时间戳）
       - 自动处理空值

    2. **HMAC 生成**（SHA256）
       - 用于加密字段索引查询
       - 相同输入产生相同输出
       - 支持自定义 HMAC 密钥

    3. **pgcrypto SQL 生成**
       - 用于数据库层加密（PostgreSQL pgcrypto 扩展）
       - 提供 SQL 表达式生成函数

    环境变量配置：
        - DATABASE_ENCRYPTION_KEY: pgcrypto 加密密钥
        - TOKEN_ENCRYPTION_KEY: 应用层加密密钥（Fernet）
        - DATABASE_HMAC_KEY: HMAC 密钥（可选，默认使用 DATABASE_ENCRYPTION_KEY）

    示例：
        >>> manager = EncryptionManager()
        >>> # 应用层加密
        >>> encrypted = manager.encrypt("13800138000")
        >>> decrypted = manager.decrypt(encrypted)
        >>> # HMAC 生成
        >>> hmac_value = manager.generate_hmac("13800138000")
        >>> # pgcrypto SQL
        >>> sql = EncryptionManager.pgp_encrypt_sql("value", "key")
    """

    def __init__(self):
        """初始化加密管理器

        从环境变量加载密钥配置。

        Raises:
            ValueError: 密钥未配置时抛出异常
        """
        # 加载密钥
        self.db_key = os.getenv('DATABASE_ENCRYPTION_KEY')
        self.app_key = os.getenv('TOKEN_ENCRYPTION_KEY')
        self.hmac_key = os.getenv('DATABASE_HMAC_KEY', self.db_key)

        # 验证密钥配置
        if not self.db_key:
            raise ValueError("DATABASE_ENCRYPTION_KEY not configured")
        if not self.app_key:
            raise ValueError("TOKEN_ENCRYPTION_KEY not configured")

        # 初始化 Fernet 加密器
        # Fernet 密钥必须是 32 字节的 base64 编码字符串（44 字符）
        try:
            if len(self.app_key) == 44:
                # 使用提供的密钥
                self._fernet = Fernet(self.app_key.encode())
            else:
                # 如果密钥格式不正确，生成新密钥（警告）
                logger.warning(
                    "TOKEN_ENCRYPTION_KEY format invalid (expected 44 chars), "
                    "generating temporary key. Please update your configuration."
                )
                self._fernet = Fernet(Fernet.generate_key())
        except Exception as e:
            logger.error(f"Failed to initialize Fernet: {e}")
            raise ValueError(f"Invalid TOKEN_ENCRYPTION_KEY: {e}")

        logger.info("EncryptionManager initialized successfully")

    # ========================================
    # 应用层加密/解密（Fernet）
    # ========================================

    def encrypt(self, plaintext: Optional[str]) -> str:
        """应用层加密

        使用 Fernet 对称加密算法。每次加密都会产生不同的密文
        （因为包含时间戳），但都能正确解密。

        Args:
            plaintext: 明文字符串（可选）

        Returns:
            str: 加密后的密文（base64 编码），空值返回空字符串

        示例：
            >>> manager.encrypt("13800138000")
            'gAAAAABh...'
            >>> manager.encrypt("")  # 空字符串
            ''
            >>> manager.encrypt(None)  # None
            ''
        """
        if not plaintext:
            return ""

        try:
            encrypted = self._fernet.encrypt(plaintext.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: Optional[str]) -> str:
        """应用层解密

        Args:
            ciphertext: 密文字符串（可选）

        Returns:
            str: 解密后的明文，空值返回空字符串

        Raises:
            cryptography.fernet.InvalidToken: 密钥不匹配或密文损坏

        示例：
            >>> encrypted = manager.encrypt("13800138000")
            >>> manager.decrypt(encrypted)
            '13800138000'
            >>> manager.decrypt("")  # 空字符串
            ''
            >>> manager.decrypt(None)  # None
            ''
        """
        if not ciphertext:
            return ""

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    # ========================================
    # HMAC 生成（用于索引查询）
    # ========================================

    def generate_hmac(self, value: Optional[str]) -> str:
        """生成 HMAC 用于加密字段索引查询

        使用 SHA256 哈希算法。相同输入总是产生相同输出，
        适合用于数据库索引查询。

        为什么需要 HMAC：
            - 加密字段无法直接查询（每次加密产生不同密文）
            - HMAC 提供确定性哈希，支持等值查询
            - 不同密钥的 HMAC 不同，防止跨数据库泄露

        Args:
            value: 要生成 HMAC 的值（可选）

        Returns:
            str: HMAC 值（64 字符十六进制字符串），空值返回空字符串

        示例：
            >>> manager.generate_hmac("13800138000")
            'a1b2c3d4e5f6...'
            >>> manager.generate_hmac("13800138000")  # 相同输入
            'a1b2c3d4e5f6...'  # 相同输出
            >>> manager.generate_hmac("")
            ''
        """
        if not value:
            return ""

        try:
            hmac_value = hmac.new(
                self.hmac_key.encode('utf-8'),
                value.encode('utf-8'),
                hashlib.sha256
            )
            return hmac_value.hexdigest()
        except Exception as e:
            logger.error(f"HMAC generation failed: {e}")
            raise

    # ========================================
    # pgcrypto SQL 生成（用于数据库层加密）
    # ========================================

    @staticmethod
    def pgp_encrypt_sql(value: str, key: str) -> str:
        """生成 pgp_sym_encrypt SQL 表达式

        用于 PostgreSQL pgcrypto 扩展的对称加密。

        Args:
            value: 要加密的值
            key: 加密密钥

        Returns:
            str: SQL 表达式

        示例：
            >>> EncryptionManager.pgp_encrypt_sql("13800138000", "secret_key")
            "pgp_sym_encrypt('13800138000', 'secret_key')"

        SQL 使用示例：
            UPDATE users SET
                phone_encrypted = pgp_sym_encrypt('13800138000', 'secret_key')
        """
        return f"pgp_sym_encrypt('{value}', '{key}')"

    @staticmethod
    def pgp_decrypt_sql(column: str, key: str) -> str:
        """生成 pgp_sym_decrypt SQL 表达式

        用于 PostgreSQL pgcrypto 扩展的对称解密。

        Args:
            column: 加密字段名
            key: 解密密钥

        Returns:
            str: SQL 表达式

        示例：
            >>> EncryptionManager.pgp_decrypt_sql("phone_encrypted", "secret_key")
            "pgp_sym_decrypt(phone_encrypted, 'secret_key')"

        SQL 使用示例：
            SELECT pgp_sym_decrypt(phone_encrypted, 'secret_key') AS phone
            FROM users
        """
        return f"pgp_sym_decrypt({column}, '{key}')"


# ========================================
# 密钥生成工具函数
# ========================================

def generate_fernet_key() -> str:
    """生成 Fernet 密钥

    用于 TOKEN_ENCRYPTION_KEY 配置。

    Returns:
        str: 44 字符的 base64 编码密钥

    示例：
        >>> key = generate_fernet_key()
        >>> len(key)
        44

    使用方法：
        python -c "from lib.utils.encryption import generate_fernet_key; print(generate_fernet_key())"
    """
    return Fernet.generate_key().decode('utf-8')


def generate_hmac_key(length: int = 32) -> str:
    """生成 HMAC 密钥

    用于 DATABASE_HMAC_KEY 配置。

    Args:
        length: 密钥长度（字节），默认 32

    Returns:
        str: 随机密钥字符串

    使用方法：
        python -c "from lib.utils.encryption import generate_hmac_key; print(generate_hmac_key())"
    """
    import secrets
    return secrets.token_hex(length)


if __name__ == "__main__":
    # 测试密钥生成
    print("Fernet Key (44 chars):")
    print(generate_fernet_key())

    print("\nHMAC Key (64 chars):")
    print(generate_hmac_key(32))

    # 测试加密功能（需要环境变量）
    print("\n--- 测试加密功能 ---")
    print("请设置环境变量：")
    print("  DATABASE_ENCRYPTION_KEY=<generated_key>")
    print("  TOKEN_ENCRYPTION_KEY=<fernet_key>")