# 数据加密配置指南

> PLAN-009: 数据加密存储实现
> 更新时间：2026-06-24

## 概述

LLM Wiki 企业版支持敏感数据加密存储，确保即使数据库被非法访问，敏感信息也无法被直接读取。

## 加密策略

采用**分层加密**策略：

| 层级 | 技术 | 适用场景 | 说明 |
|------|------|----------|------|
| **数据库层** | pgcrypto | 结构化数据（phone/email） | 透明加密，支持索引查询 |
| **应用层** | cryptography (Fernet) | 敏感凭据（token） | 灵活控制，支持密钥轮换 |
| **传输层** | TLS | 网络传输 | 强制 HTTPS |

## 加密范围

| 数据类型 | 加密字段 | 优先级 | 说明 |
|----------|----------|:------:|------|
| **用户信息** | phone, email | P0 | 个人隐私信息 |
| **认证凭据** | access_token, refresh_token | P0 | 已实现（应用层） |
| **审计日志** | ip_address | P1 | 可追溯信息 |

## 快速开始

### 1. 生成加密密钥

```bash
# 进入项目目录
cd llm-wiki

# 运行密钥生成脚本
source .venv/bin/activate
python scripts/generate_encryption_keys.py
```

输出示例：
```
1. TOKEN_ENCRYPTION_KEY（应用层加密密钥）
   密钥：-kohHSE7KG5NOzLhWPg1-pis5Siv70RaACULL67vadA=

2. DATABASE_HMAC_KEY（HMAC 密钥）
   密钥：f4be77e20d01845f9e8742aacd1be652f3374327881cb26dcc3428be51164daa
```

### 2. 配置环境变量

将生成的密钥添加到 `.env` 文件：

```bash
# .env 文件
DATABASE_ENCRYPTION_KEY=<your-pgcrypto-key>
TOKEN_ENCRYPTION_KEY=<your-fernet-key>
DATABASE_HMAC_KEY=<hmac-key>
```

### 3. 重启服务

```bash
# 使用 Docker Compose
docker-compose down
docker-compose up -d
```

### 4. 验证加密功能

```bash
# 验证 pgcrypto 扩展
python scripts/verify_pgcrypto.py
```

## 密钥管理

### 密钥要求

- **TOKEN_ENCRYPTION_KEY**: 44 字符（32 字节的 base64 编码）
- **DATABASE_HMAC_KEY**: 64 字符（32 字节的十六进制）
- **DATABASE_ENCRYPTION_KEY**: 任意字符串（建议 32+ 字符）

### 密钥生成

```bash
# Fernet 密钥（TOKEN_ENCRYPTION_KEY）
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# HMAC 密钥（DATABASE_HMAC_KEY）
python -c "from lib.utils.encryption import generate_hmac_key; print(generate_hmac_key())"
```

### 密钥轮换

支持密钥轮换，不影响已有数据：

1. 生成新密钥
2. 更新环境变量
3. 重启服务
4. 运行数据迁移脚本（可选）

## 数据迁移

### 迁移现有用户数据

```bash
# 预览模式（dry-run）
python scripts/migrate_encrypt_user_fields.py --dry-run

# 正式执行
python scripts/migrate_encrypt_user_fields.py
```

## HMAC 索引查询

加密字段支持等值查询（使用 HMAC 索引）：

```python
from lib.auth.user_sync import UserSyncService
from lib.utils.encryption import EncryptionManager

# 初始化
encryption = EncryptionManager()
phone_hmac = encryption.generate_hmac("13800138000")

# 查询用户
user = await user_sync.find_user_by_phone_hmac("13800138000")
```

## 安全最佳实践

### ✅ 必须执行

- [ ] 生产环境使用不同的强密钥
- [ ] 密钥存储在环境变量中
- [ ] 定期更换密钥（建议每 90 天）
- [ ] 备份密钥到安全存储

### ❌ 禁止操作

- ❌ 将密钥提交到 git
- ❌ 在日志中输出密钥
- ❌ 使用示例密钥用于生产
- ❌ 在多个环境共享密钥

## 性能影响

加密/解密操作延迟 < 10ms，对用户体验影响微乎其微。

## 故障排除

### 问题 1：密钥未配置

**症状**：启动时报错 `DATABASE_ENCRYPTION_KEY not configured`

**解决方案**：检查 `.env` 文件，确保三个密钥都已配置

### 问题 2：密钥格式错误

**症状**：启动时报错 `Invalid TOKEN_ENCRYPTION_KEY`

**解决方案**：使用密钥生成脚本重新生成符合要求的密钥

### 问题 3：无法查询加密字段

**症状**：按 phone/email 查询用户返回 None

**解决方案**：确保数据已迁移，HMAC 字段有值

## 相关文件

- **加密工具类**: `lib/utils/encryption.py`
- **密钥生成脚本**: `scripts/generate_encryption_keys.py`
- **用户数据迁移**: `scripts/migrate_encrypt_user_fields.py`
- **验证脚本**: `scripts/verify_pgcrypto.py`

## 更新日志

- **2026-06-24**: PLAN-009 完成
  - 实现 EncryptionManager 加密工具类
  - 用户字段加密支持（phone/email）
  - HMAC 索引查询
  - 数据迁移脚本
  - 密钥生成工具