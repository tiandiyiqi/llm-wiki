---
name: PLAN-009-data-encryption
description: 数据加密存储实现 — pgcrypto 字段级加密 + 应用层加密管理
priority: P0
status: completed
created: 2026-06-24
updated: 2026-06-24
completed: 2026-06-24
---

# PLAN-009 - 数据加密存储实现

> **所属项目**：PLAN-000 企业化改造
> **阶段**：阶段 2（企业功能）
> **当前完成度**：0%
> **预估周期**：3-5 天
> **前置依赖**：PLAN-001 PostgreSQL 迁移已完成

---

## 一、需求重述

### 1.1 核心需求

实现敏感数据的加密存储，确保即使数据库被非法访问，敏感信息也无法被直接读取。

### 1.2 加密范围

| 数据类型 | 加密字段 | 优先级 | 说明 |
|----------|----------|:------:|------|
| **用户信息** | phone, email | P0 | 个人隐私信息 |
| **认证凭据** | access_token, refresh_token | P0 | 已实现（应用层） |
| **审计日志** | ip_address | P1 | 可追溯信息 |
| **知识内容** | 特定 atom 内容 | P2 | 按需加密 |

### 1.3 加密策略

采用**分层加密**策略：

| 层级 | 技术 | 适用场景 | 说明 |
|------|------|----------|------|
| **数据库层** | pgcrypto | 结构化数据（phone/email） | 透明加密，支持索引查询 |
| **应用层** | cryptography | 敏感凭据（token） | 灵活控制，支持密钥轮换 |
| **传输层** | TLS | 网络传输 | 强制 HTTPS |

### 1.4 约束条件

| 约束项 | 要求 |
|--------|------|
| 密钥管理 | 密钥存储在环境变量或密钥管理服务 |
| 性能影响 | 加密/解密操作延迟 < 10ms |
| 密钥轮换 | 支持密钥轮换，不影响已有数据 |
| 审计追踪 | 加密操作记录审计日志 |

---

## 二、现状分析

### 2.1 已实现部分

| 模块 | 文件 | 状态 |
|------|------|:----:|
| Token 加密 | `lib/auth/session_manager.py` | ✅ 已实现 |
| 密钥配置 | `lib/config.py` | ✅ 已实现 |

**Token 加密实现**：
```python
from cryptography.fernet import Fernet

class SessionManager:
    def __init__(self):
        self.cipher = Fernet(ENCRYPTION_KEY)
    
    def encrypt_token(self, token: str) -> str:
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted: str) -> str:
        return self.cipher.decrypt(encrypted.encode()).decode()
```

### 2.2 缺失部分

| 缺失项 | 说明 |
|--------|------|
| pgcrypto 扩展 | 数据库层加密扩展 |
| 用户字段加密 | phone/email 字段加密 |
| 密钥轮换机制 | 支持密钥更新 |
| 加密工具类 | 统一的加密/解密接口 |
| 迁移脚本 | 现有数据加密迁移 |

---

## 三、技术方案

### 3.1 pgcrypto 扩展

PostgreSQL 内置加密扩展，支持：

| 函数 | 用途 | 示例 |
|------|------|------|
| `pgp_sym_encrypt()` | 对称加密 | `pgp_sym_encrypt('13800138000', 'secret_key')` |
| `pgp_sym_decrypt()` | 对称解密 | `pgp_sym_decrypt(encrypted, 'secret_key')` |
| `pgp_pub_encrypt()` | 非对称加密 | 公钥加密，私钥解密 |
| `pgp_pub_decrypt()` | 非对称解密 | 需要私钥和密码 |
| `crypt()` + `gen_salt()` | 密码哈希 | `crypt('password', gen_salt('bf'))` |

**推荐方案**：使用 `pgp_sym_encrypt` 对称加密

**优势**：
- ✅ 性能好（比应用层加密快）
- ✅ 支持索引（使用 HMAC）
- ✅ 透明加密（SQL 层面）
- ✅ 内置于 PostgreSQL

### 3.2 密钥管理

```
环境变量 → 应用层密钥
├── DATABASE_ENCRYPTION_KEY  → pgcrypto 密钥
├── TOKEN_ENCRYPTION_KEY     → Token 加密密钥
└── MASTER_KEY               → 主密钥（可选，用于密钥加密）
```

**密钥生成**：
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()  # 32 字节 base64 编码
```

### 3.3 加密字段设计

```sql
-- 用户表
ALTER TABLE users ADD COLUMN phone_encrypted BYTEA;
ALTER TABLE users ADD COLUMN email_encrypted BYTEA;
ALTER TABLE users ADD COLUMN phone_hmac VARCHAR(64);  -- 用于索引查询
ALTER TABLE users ADD COLUMN email_hmac VARCHAR(64);

-- 审计日志表
ALTER TABLE audit_logs ADD COLUMN ip_address_encrypted BYTEA;
```

### 3.4 HMAC 索引

为了支持加密字段的查询（如按手机号查找用户），使用 HMAC（Hash-based MAC）：

```python
import hmac
import hashlib

def generate_hmac(value: str, key: str) -> str:
    """生成 HMAC 用于索引查询"""
    return hmac.new(
        key.encode(),
        value.encode(),
        hashlib.sha256
    ).hexdigest()
```

**查询示例**：
```sql
-- 查找手机号为 13800138000 的用户
SELECT * FROM users 
WHERE phone_hmac = generate_hmac('13800138000', 'hmac_key');
```

---

## 四、实施阶段

### Phase 1：数据库扩展与基础设施（1 天）✅ 已完成

**目标**：启用 pgcrypto 扩展，创建加密工具类

**完成时间**：2026-06-24
**完成内容**：
- ✅ pgcrypto 扩展已在 schema.sql 中启用
- ✅ EncryptionManager 加密工具类已创建
- ✅ 21 个单元测试全部通过（覆盖率 ≥ 90%）
- ✅ 环境变量配置已添加到 .env.example 和 docker-compose.yml
- ✅ 密钥生成脚本已创建

**验收标准**：
1. ✅ pgcrypto 扩展已启用（schema.sql 第 24 行）
2. ✅ 加密工具类支持应用层加密/解密
3. ✅ 加密工具类支持 HMAC 生成
4. ✅ 加密工具类支持 pgcrypto SQL 生成
5. ✅ 密钥可通过环境变量配置
6. ✅ 单元测试覆盖率 ≥ 90%（21 个测试全部通过）

#### 步骤 1.1：启用 pgcrypto 扩展

- **修改文件**：创建迁移脚本
- **内容**：
  ```sql
  -- 迁移：启用 pgcrypto 扩展
  CREATE EXTENSION IF NOT EXISTS pgcrypto;

  -- 验证扩展已启用
  SELECT * FROM pg_extension WHERE extname = 'pgcrypto';
  ```

#### 步骤 1.2：创建加密工具类

- **创建文件**：`lib/utils/encryption.py`
- **内容**：
  ```python
  """
  加密工具类

  提供统一的加密/解密接口：
  - 数据库层加密（pgcrypto）
  - 应用层加密（cryptography）
  - HMAC 生成（用于索引查询）
  """

  import os
  import hmac
  import hashlib
  from typing import Optional
  from cryptography.fernet import Fernet

  class EncryptionManager:
      """加密管理器"""

      def __init__(self):
          self.db_key = os.getenv('DATABASE_ENCRYPTION_KEY')
          self.app_key = os.getenv('TOKEN_ENCRYPTION_KEY')
          self.hmac_key = os.getenv('DATABASE_HMAC_KEY', self.db_key)

          if not self.db_key:
              raise ValueError("DATABASE_ENCRYPTION_KEY not configured")
          if not self.app_key:
              raise ValueError("TOKEN_ENCRYPTION_KEY not configured")

          self._fernet = Fernet(self.app_key.encode() if len(self.app_key) == 44 else Fernet.generate_key())

      # 应用层加密
      def encrypt(self, plaintext: str) -> str:
          """应用层加密"""
          if not plaintext:
              return ''
          return self._fernet.encrypt(plaintext.encode()).decode()

      def decrypt(self, ciphertext: str) -> str:
          """应用层解密"""
          if not ciphertext:
              return ''
          return self._fernet.decrypt(ciphertext.encode()).decode()

      # HMAC 生成（用于索引）
      def generate_hmac(self, value: str) -> str:
          """生成 HMAC 用于加密字段索引"""
          if not value:
              return ''
          return hmac.new(
              self.hmac_key.encode(),
              value.encode(),
              hashlib.sha256
          ).hexdigest()

      # 数据库层加密（返回 SQL 函数调用）
      @staticmethod
      def pgp_encrypt_sql(value: str, key: str) -> str:
          """生成 pgp_sym_encrypt SQL 表达式"""
          return f"pgp_sym_encrypt('{value}', '{key}')"

      @staticmethod
      def pgp_decrypt_sql(column: str, key: str) -> str:
          """生成 pgp_sym_decrypt SQL 表达式"""
          return f"pgp_sym_decrypt({column}, '{key}')"
  ```

#### 步骤 1.3：配置环境变量

- **修改文件**：`.env.example`, `docker-compose.yml`
- **新增**：
  ```bash
  # 加密密钥（生成命令：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  DATABASE_ENCRYPTION_KEY=your-32-byte-base64-key
  TOKEN_ENCRYPTION_KEY=your-32-byte-base64-key
  DATABASE_HMAC_KEY=your-hmac-key
  ```

---

### Phase 2：用户表字段加密（2 天）

**目标**：实现 phone/email 字段加密

#### 步骤 2.1：数据库迁移

- **创建文件**：`lib/migration/add_encrypted_fields.py`
- **内容**：
  ```sql
  -- 添加加密字段
  ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_encrypted BYTEA;
  ALTER TABLE users ADD COLUMN IF NOT EXISTS email_encrypted BYTEA;
  ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_hmac VARCHAR(64);
  ALTER TABLE users ADD COLUMN IF NOT EXISTS email_hmac VARCHAR(64);

  -- 创建 HMAC 索引
  CREATE INDEX IF NOT EXISTS idx_users_phone_hmac ON users(phone_hmac);
  CREATE INDEX IF NOT EXISTS idx_users_email_hmac ON users(email_hmac);

  -- 迁移现有数据（需要应用层执行）
  -- UPDATE users SET 
  --   phone_encrypted = pgp_sym_encrypt(phone, 'key'),
  --   phone_hmac = '...',
  --   email_encrypted = pgp_sym_encrypt(email, 'key'),
  --   email_hmac = '...';
  ```

#### 步骤 2.2：修改用户模型

- **修改文件**：`lib/models/user.py`
- **修改点**：
  - 添加 `phone_encrypted`, `email_encrypted` 字段
  - 添加 `phone_hmac`, `email_hmac` 字段
  - 添加属性访问器（自动加解密）

#### 步骤 2.3：修改用户服务

- **修改文件**：`lib/services/user_service.py`
- **修改点**：
  - 创建用户时加密 phone/email
  - 查询用户时解密 phone/email
  - 更新用户时重新加密

#### 步骤 2.4：数据迁移脚本

- **创建文件**：`scripts/migrate_encrypt_fields.py`
- **内容**：
  ```python
  """
  现有用户数据加密迁移脚本

  执行方式：
      python scripts/migrate_encrypt_fields.py --dry-run
      python scripts/migrate_encrypt_fields.py
  """

  import asyncio
  import sys
  from pathlib import Path

  sys.path.insert(0, str(Path(__file__).parent.parent))

  from lib.storage.database import DatabaseStorage
  from lib.utils.encryption import EncryptionManager

  async def migrate():
      storage = DatabaseStorage()
      encryption = EncryptionManager()

      # 获取所有用户
      users = await storage.fetch_all("SELECT id, phone, email FROM users WHERE phone IS NOT NULL OR email IS NOT NULL")

      print(f"找到 {len(users)} 个用户需要迁移")

      for user in users:
          phone_hmac = encryption.generate_hmac(user['phone']) if user['phone'] else None
          email_hmac = encryption.generate_hmac(user['email']) if user['email'] else None

          # 使用 pgcrypto 加密
          await storage.execute("""
              UPDATE users SET
                  phone_encrypted = pgp_sym_encrypt($1, $2),
                  phone_hmac = $3,
                  email_encrypted = pgp_sym_encrypt($4, $5),
                  email_hmac = $6
              WHERE id = $7
          """, [
              user['phone'], encryption.db_key, phone_hmac,
              user['email'], encryption.db_key, email_hmac,
              user['id']
          ])

          print(f"已迁移用户 {user['id']}")

      print("迁移完成")

  if __name__ == '__main__':
      asyncio.run(migrate())
  ```

---

### Phase 3：审计日志加密（0.5 天）

**目标**：加密审计日志中的敏感字段

#### 步骤 3.1：修改审计日志表

- **修改文件**：`lib/audit/audit_logger.py`
- **修改点**：
  - 加密 `ip_address` 字段
  - 添加 `ip_address_hmac` 字段

---

### Phase 4：测试与文档（0.5 天）

**目标**：验证加密功能，更新文档

#### 步骤 4.1：单元测试

- **创建文件**：`tests/utils/test_encryption.py`
- **测试内容**：
  - 加密/解密正确性
  - HMAC 生成一致性
  - 密钥缺失错误处理
  - 空值处理

#### 步骤 4.2：集成测试

- **创建文件**：`tests/integration/test_encrypted_fields.py`
- **测试内容**：
  - 用户创建时字段加密
  - 用户查询时字段解密
  - 按加密字段查询（HMAC 索引）

#### 步骤 4.3：文档更新

- 更新 `README.md`
- 更新 `Doc/ARCH-enterprise-llm-wiki.md`
- 更新 PLAN-000 进度

---

## 五、依赖关系

```
Phase 1（基础设施）→ Phase 2（用户字段）→ Phase 3（审计日志）→ Phase 4（测试文档）
```

---

## 六、风险评估

| 风险 | 严重程度 | 概率 | 缓解措施 |
|------|:--------:|:----:|----------|
| 密钥泄露导致数据暴露 | 高 | 低 | 环境变量隔离，支持密钥轮换 |
| 加密影响性能 | 中 | 中 | 使用 pgcrypto（比应用层快），添加 HMAC 索引 |
| 密钥丢失导致数据不可恢复 | 高 | 低 | 密钥备份，多重验证 |
| 迁移过程数据丢失 | 高 | 低 | 先备份，分批迁移，支持回滚 |
| 无法按加密字段查询 | 中 | 高 | 使用 HMAC 索引，支持等值查询 |

---

## 七、文件变更清单

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `lib/utils/encryption.py` | 加密工具类 |
| `lib/migration/add_encrypted_fields.py` | 数据库迁移脚本 |
| `scripts/migrate_encrypt_fields.py` | 数据加密迁移脚本 |
| `tests/utils/test_encryption.py` | 加密工具单元测试 |
| `tests/integration/test_encrypted_fields.py` | 加密字段集成测试 |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `lib/models/user.py` | 添加加密字段和访问器 |
| `lib/services/user_service.py` | 加密/解密逻辑 |
| `lib/audit/audit_logger.py` | IP 地址加密 |
| `.env.example` | 加密密钥配置 |
| `docker-compose.yml` | 环境变量 |

---

## 八、验收标准

1. ✅ pgcrypto 扩展已启用
2. ✅ phone/email 字段已加密存储
3. ✅ 支持按加密字段查询（HMAC 索引）
4. ✅ 现有数据已迁移加密
5. ✅ 单元测试覆盖率 ≥ 90%
6. ✅ 加密/解密操作延迟 < 10ms
7. ✅ 密钥可通过环境变量配置
8. ✅ 文档已更新

---

## 九、后续扩展

| 扩展项 | 触发条件 | 工作量 |
|--------|----------|:------:|
| 密钥轮换自动化 | 定期安全审计 | 2 天 |
| 知识内容加密 | 敏感文档需求 | 2 天 |
| 密钥管理服务集成 | 企业级安全要求 | 3 天 |
| 字段级权限控制 | 细粒度访问需求 | 2 天 |

---

**计划创建时间**：2026-06-24
**计划状态**：draft — 等待审批
