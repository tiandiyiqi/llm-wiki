# PLAN-002 问题修复任务组拆分

**制定日期**: 2026-06-22
**总阶段**: 4 个
**总任务组**: 19 个
**总子任务**: 156 个
**预计周期**: 2-3 周

---

## 阶段 1：P0 问题修复（1-2 天）

**目标**: 修复 7 个 CRITICAL 问题，确保核心安全
**类型**: 串行执行（严格依赖）
**验证标准**: 所有 CRITICAL 测试通过

---

### 任务组 1：密码安全重构

**类型**: 串行
**前置条件**: 无
**预计时间**: 0.5 天
**涉及文件**: lib/auth.py, requirements.txt
**问题编号**: CRITICAL-1

#### 子任务 1-1：添加 bcrypt 依赖

- [x] SUB-TASK-001: 在 requirements.txt 添加 `bcrypt>=4.0.0`
- [x] SUB-TASK-002: 运行 `pip install bcrypt`
- [x] SUB-TASK-003: 验证安装成功：`python -c "import bcrypt; print(bcrypt.__version__)"`

**复杂度**: 低
**依赖**: 无
**文件**: requirements.txt

---

#### 子任务 1-2：重写密码哈希函数

- [x] SUB-TASK-004: 在 lib/auth.py 导入 bcrypt
- [x] SUB-TASK-005: 重写 `hash_password()` 使用 `bcrypt.hashpw()`
- [x] SUB-TASK-006: 重写 `verify_password()` 使用 `bcrypt.checkpw()`
- [x] SUB-TASK-007: 更新 `authenticate()` 验证逻辑
- [x] SUB-TASK-008: 删除旧的 SHA-256 哈希代码

**复杂度**: 中
**依赖**: SUB-TASK-001~003
**文件**: lib/auth.py

**代码示例**:
```python
import bcrypt

def hash_password(password: str) -> str:
    """使用 bcrypt 安全哈希密码"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, stored_hash: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        password.encode('utf-8'),
        stored_hash.encode('utf-8')
    )
```

---

#### 子任务 1-3：编写测试脚本

- [x] SUB-TASK-009: 创建测试脚本 `tests/test_password_hash.py`
- [x] SUB-TASK-010: 测试密码哈希功能
- [x] SUB-TASK-011: 测试密码验证功能
- [x] SUB-TASK-012: 测试不同密码的哈希唯一性

**复杂度**: 低
**依赖**: SUB-TASK-004~008
**文件**: tests/test_password_hash.py

---

#### 子任务 1-4：运行测试验证

- [x] SUB-TASK-013: 运行密码哈希测试：`pytest tests/test_password_hash.py -v`
- [x] SUB-TASK-014: 手动验证：`python -c "import bcrypt; h=bcrypt.hashpw('test123'.encode(),bcrypt.gensalt()); print(bcrypt.checkpw('test123'.encode(),h))"`
- [x] SUB-TASK-015: 检查所有测试通过

**复杂度**: 低
**依赖**: SUB-TASK-009~012
**文件**: 无

---

### 任务组 2：认证中间件实现

**类型**: 串行
**前置条件**: 任务组 1 完成
**预计时间**: 1 天
**涉及文件**: lib/auth/auth_middleware.py, lib/api_server.py, lib/api/*.py
**问题编号**: CRITICAL-4

#### 子任务 2-1：创建认证中间件文件

- [ ] SUB-TASK-016: 创建目录 `lib/auth/`
- [ ] SUB-TASK-017: 创建文件 `lib/auth/auth_middleware.py`
- [ ] SUB-TASK-018: 导入 functools.wraps

**复杂度**: 低
**依赖**: 任务组 1 完成
**文件**: lib/auth/auth_middleware.py

---

#### 子任务 2-2：实现 require_auth 装饰器

- [ ] SUB-TASK-019: 定义 `require_auth` 装饰器框架
- [ ] SUB-TASK-020: 实现 Authorization header 检查
- [ ] SUB-TASK-021: 实现 Token 提取逻辑
- [ ] SUB-TASK-022: 实现 Token 验证逻辑
- [ ] SUB-TASK-023: 实现用户上下文设置（current_user, current_role）
- [ ] SUB-TASK-024: 实现错误响应（401 Unauthorized）

**复杂度**: 高
**依赖**: SUB-TASK-016~018
**文件**: lib/auth/auth_middleware.py

**代码示例**:
```python
from functools import wraps

def require_auth(func):
    """认证装饰器"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        auth_header = self.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            self._json_response({'error': 'Missing authentication'}, 401)
            return None

        token = auth_header[7:]
        auth = self._get_auth_manager()
        user_info = auth.validate_token(token)

        if not user_info:
            self._json_response({'error': 'Invalid token'}, 401)
            return None

        self.current_user = user_info['username']
        self.current_role = user_info['role']

        return func(self, *args, **kwargs)
    return wrapper
```

---

#### 子任务 2-3：集成到 API Server

- [ ] SUB-TASK-025: 在 `lib/api_server.py` 导入 auth_middleware
- [ ] SUB-TASK-026: 识别所有需要认证的端点
- [ ] SUB-TASK-027: 为所有端点添加 `@require_auth` 装饰器
- [ ] SUB-TASK-028: 保持健康检查端点公开（无装饰器）

**复杂度**: 中
**依赖**: SUB-TASK-019~024
**文件**: lib/api_server.py

---

#### 子任务 2-4：更新 API 模块

- [ ] SUB-TASK-029: 检查 `lib/api/*.py` 所有文件
- [ ] SUB-TASK-030: 为每个 API 方法添加认证检查
- [ ] SUB-TASK-031: 确保错误处理一致

**复杂度**: 中
**依赖**: SUB-TASK-025~028
**文件**: lib/api/*.py

---

#### 子任务 2-5：测试认证中间件

- [ ] SUB-TASK-032: 创建测试文件 `tests/test_auth_middleware.py`
- [ ] SUB-TASK-033: 测试无认证请求返回 401
- [ ] SUB-TASK-034: 测试有效认证返回 200
- [ ] SUB-TASK-035: 测试无效 Token 返回 401
- [ ] SUB-TASK-036: 测试健康检查端点无需认证

**复杂度**: 中
**依赖**: SUB-TASK-029~031
**文件**: tests/test_auth_middleware.py

---

#### 子任务 2-6：验证端点保护

- [ ] SUB-TASK-037: 启动 API Server：`python lib/api_server.py`
- [ ] SUB-TASK-038: 测试无认证请求：`curl http://localhost:5000/api/kbs`（预期 401）
- [ ] SUB-TASK-039: 测试有效认证：`curl -H "Authorization: Bearer <token>" http://localhost:5000/api/kbs`（预期 200）
- [ ] SUB-TASK-040: 测试所有端点已保护

**复杂度**: 低
**依赖**: SUB-TASK-032~036
**文件**: 无

---

### 任务组 3：SQL 注入修复

**类型**: 串行
**前置条件**: 任务组 2 完成
**预计时间**: 0.5 天
**涉及文件**: lib/core/db_storage.py, lib/auth/rls_manager.py, lib/utils/sql_validator.py
**问题编号**: CRITICAL-2, CRITICAL-3

#### 子任务 3-1：创建 SQL 验证工具

- [ ] SUB-TASK-041: 创建目录 `lib/utils/`
- [ ] SUB-TASK-042: 创建文件 `lib/utils/sql_validator.py`
- [ ] SUB-TASK-043: 实现 `validate_identifier()` - 正则验证
- [ ] SUB-TASK-044: 实现 `validate_table_name()` - 白名单验证
- [ ] SUB-TASK-045: 实现 `sanitize_sql_string()` - 清理特殊字符

**复杂度**: 中
**依赖**: 任务组 2 完成
**文件**: lib/utils/sql_validator.py

**代码示例**:
```python
import re

def validate_identifier(value: str) -> bool:
    """验证 SQL 标识符"""
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', value))

def validate_table_name(value: str) -> bool:
    """验证表名"""
    valid_tables = [
        'knowledge_bases', 'atoms', 'users',
        'kb_members', 'sessions', 'audit_log'
    ]
    return value in valid_tables
```

---

#### 子任务 3-2：修复 db_storage.py

- [ ] SUB-TASK-046: 在 `lib/core/db_storage.py` 导入 sql_validator
- [ ] SUB-TASK-047: 重写 `list_kbs()` - 白名单验证 scope + 参数化查询
- [ ] SUB-TASK-048: 重写 `update_kb()` - 验证 kb_id + 参数化
- [ ] SUB-TASK-049: 重写 `update_atom()` - 验证 atom_id + 参数化
- [ ] SUB-TASK-050: 重写 `delete_kb()` - 验证 kb_id
- [ ] SUB-TASK-051: 重写 `delete_atom()` - 验证 atom_id

**复杂度**: 高
**依赖**: SUB-TASK-041~045
**文件**: lib/core/db_storage.py

**代码示例**:
```python
from lib.utils.sql_validator import validate_identifier

async def list_kbs(self, user_id: Optional[str] = None, scope: Optional[str] = None):
    """列出知识库（防注入）"""
    conditions = []
    params = []

    if user_id:
        if not validate_identifier(user_id):
            raise ValueError(f"Invalid user_id: {user_id}")
        conditions.append("owner_id = $1")
        params.append(user_id)

    if scope:
        valid_scopes = ['personal', 'department', 'project', 'company']
        if scope not in valid_scopes:
            raise ValueError(f"Invalid scope: {scope}")
        conditions.append(f"scope = ${len(params) + 1}")
        params.append(scope)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"SELECT * FROM knowledge_bases {where_clause} ORDER BY updated_at DESC"

    return await self.db_manager.fetch_all(query, *params)
```

---

#### 子任务 3-3：修复 rls_manager.py

- [ ] SUB-TASK-054: 在 `lib/auth/rls_manager.py` 导入 sql_validator
- [ ] SUB-TASK-055: 重写 `create_kb_policy()` - 类型检查 kb_id + quote_ident
- [ ] SUB-TASK-056: 重写 `drop_kb_policy()` - 类型检查 kb_id
- [ ] SUB-TASK-057: 重写 `create_atom_policy()` - 类型检查 atom_id
- [ ] SUB-TASK-058: 重写 `drop_atom_policy()` - 类型检查 atom_id

**复杂度**: 高
**依赖**: SUB-TASK-046~051
**文件**: lib/auth/rls_manager.py

---

#### 子任务 3-4：测试 SQL 注入防护

- [ ] SUB-TASK-059: 创建测试文件 `tests/test_sql_injection.py`
- [ ] SUB-TASK-060: 测试注入攻击：`scope=personal'; DROP TABLE knowledge_bases; --`
- [ ] SUB-TASK-061: 测试路径遍历：`/api/atoms/../../../etc/passwd`
- [ ] SUB-TASK-062: 测试非法标识符：`user_id=admin'--`
- [ ] SUB-TASK-063: 验证所有注入尝试返回 400

**复杂度**: 中
**依赖**: SUB-TASK-054~058
**文件**: tests/test_sql_injection.py

---

#### 子任务 3-5：验证阶段 1 完成

- [ ] SUB-TASK-064: 运行所有 P0 测试：`pytest tests/ -v -m critical`
- [ ] SUB-TASK-065: 检查测试覆盖率：`pytest --cov=lib --cov-report=term-missing`
- [ ] SUB-TASK-066: 手动验证所有 CRITICAL 问题已修复
- [ ] SUB-TASK-067: 更新进度文档

**复杂度**: 低
**依赖**: SUB-TASK-059~063
**文件**: 无

---

## 阶段 2：P1 问题修复（3-5 天）

**目标**: 修复 10 个 HIGH 问题，确保生产可用
**类型**: 部分并行（任务组 4-5 并行，任务组 8-12 并行）
**验证标准**: 所有 HIGH 测试通过

---

### 任务组 4：输入验证层（可与任务组 5 并行）

**类型**: 并行
**前置条件**: 阶段 1 完成
**预计时间**: 1 天
**涉及文件**: lib/api/validators.py, lib/api/*.py, requirements.txt
**问题编号**: HIGH-1

#### 子任务 4-1：添加 Pydantic 依赖

- [ ] SUB-TASK-068: 在 requirements.txt 添加 `pydantic>=2.0.0`
- [ ] SUB-TASK-069: 运行 `pip install pydantic`
- [ ] SUB-TASK-070: 验证安装：`python -c "import pydantic; print(pydantic.VERSION)"`

**复杂度**: 低
**依赖**: 阶段 1 完成
**文件**: requirements.txt

---

#### 子任务 4-2：创建验证模型

- [ ] SUB-TASK-071: 创建文件 `lib/api/validators.py`
- [ ] SUB-TASK-072: 定义 `CreateKBRequest` (name, description, scope)
- [ ] SUB-TASK-073: 定义 `UpdateKBRequest` (name, description)
- [ ] SUB-TASK-074: 定义 `ListAtomsRequest` (kb_id, page, limit)
- [ ] SUB-TASK-075: 定义 `QueryRequest` (q, limit, semantic)
- [ ] SUB-TASK-076: 定义 `IngestRequest` (content, metadata)
- [ ] SUB-TASK-077: 为每个模型添加 validator

**复杂度**: 中
**依赖**: SUB-TASK-068~070
**文件**: lib/api/validators.py

**代码示例**:
```python
from pydantic import BaseModel, Field, validator

class CreateKBRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scope: str = Field(default='personal')

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        return v.strip()

    @validator('scope')
    def validate_scope(cls, v):
        valid_scopes = ['personal', 'department', 'project', 'company']
        if v not in valid_scopes:
            raise ValueError(f'Invalid scope: {v}')
        return v

class QueryRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)
    semantic: bool = False
```

---

#### 子任务 4-3：集成验证到 API

- [ ] SUB-TASK-078: 在 `lib/api/kb_api.py` 导入 validators
- [ ] SUB-TASK-079: 在 create_kb 方法使用 CreateKBRequest
- [ ] SUB-TASK-080: 在 update_kb 方法使用 UpdateKBRequest
- [ ] SUB-TASK-081: 在 `lib/api/atom_api.py` 导入 validators
- [ ] SUB-TASK-082: 在 list_atoms 方法使用 ListAtomsRequest
- [ ] SUB-TASK-083: 在 query 方法使用 QueryRequest
- [ ] SUB-TASK-084: 在 ingest 方法使用 IngestRequest
- [ ] SUB-TASK-085: 添加验证错误处理（返回 400）

**复杂度**: 中
**依赖**: SUB-TASK-071~077
**文件**: lib/api/*.py

---

#### 子任务 4-4：测试输入验证

- [ ] SUB-TASK-086: 创建测试文件 `tests/test_validators.py`
- [ ] SUB-TASK-087: 测试空名称返回错误
- [ ] SUB-TASK-088: 测试超长名称返回错误
- [ ] SUB-TASK-089: 测试非法 scope 返回错误
- [ ] SUB-TASK-090: 测试超限 limit 返回错误
- [ ] SUB-TASK-091: 测试有效输入正常处理

**复杂度**: 中
**依赖**: SUB-TASK-078~085
**文件**: tests/test_validators.py

---

### 任务组 5：速率限制实现（可与任务组 4 并行）

**类型**: 并行
**前置条件**: 阶段 1 完成
**预计时间**: 1 天
**涉及文件**: lib/api/rate_limiter.py, lib/api_server.py
**问题编号**: HIGH-2

#### 子任务 5-1：创建速率限制器

- [ ] SUB-TASK-092: 创建文件 `lib/api/rate_limiter.py`
- [ ] SUB-TASK-093: 定义 `RateLimiter` 类
- [ ] SUB-TASK-094: 实现请求计数（defaultdict）
- [ ] SUB-TASK-095: 实现时间窗口（timedelta）
- [ ] SUB-TASK-096: 实现 `is_allowed()` 方法
- [ ] SUB-TASK-097: 实现线程锁（Lock）
- [ ] SUB-TASK-098: 实现过期清理逻辑

**复杂度**: 中
**依赖**: 阶段 1 完成
**文件**: lib/api/rate_limiter.py

**代码示例**:
```python
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.requests = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        with self.lock:
            self.requests[client_id] = [
                t for t in self.requests[client_id] if t > cutoff
            ]

            if len(self.requests[client_id]) >= self.rpm:
                return False

            self.requests[client_id].append(now)
            return True
```

---

#### 子任务 5-2：定义端点限制策略

- [ ] SUB-TASK-099: 定义 `RATE_LIMITS` 配置字典
- [ ] SUB-TASK-100: 设置查询端点：30/分钟
- [ ] SUB-TASK-101: 设置摄入端点：10/分钟
- [ ] SUB-TASK-102: 设置嵌入端点：5/分钟
- [ ] SUB-TASK-103: 设置默认：60/分钟

**复杂度**: 低
**依赖**: SUB-TASK-092~098
**文件**: lib/api/rate_limiter.py

---

#### 子任务 5-3：集成到 API Server

- [ ] SUB-TASK-104: 在 `lib/api_server.py` 导入 RateLimiter
- [ ] SUB-TASK-105: 创建不同端点的 RateLimiter 实例
- [ ] SUB-TASK-106: 在每个请求前检查速率限制
- [ ] SUB-TASK-107: 返回 429 Too Many Requests
- [ ] SUB-TASK-108: 添加 Retry-After header

**复杂度**: 中
**依赖**: SUB-TASK-099~103
**文件**: lib/api_server.py

---

#### 子任务 5-4：测试速率限制

- [ ] SUB-TASK-109: 创建测试文件 `tests/test_rate_limiter.py`
- [ ] SUB-TASK-110: 测试正常请求通过
- [ ] SUB-TASK-111: 测试超限请求返回 429
- [ ] SUB-TASK-112: 测试不同端点不同限制
- [ ] SUB-TASK-113: 测试时间窗口过期后恢复

**复杂度**: 中
**依赖**: SUB-TASK-104~108
**文件**: tests/test_rate_limiter.py

---

### 任务组 6：错误处理改进（依赖任务组 4、5）

**类型**: 串行
**前置条件**: 任务组 4、5 完成
**预计时间**: 0.5 天
**涉及文件**: lib/api/error_handler.py, lib/api/*.py
**问题编号**: HIGH-3

#### 子任务 6-1：创建错误处理器

- [ ] SUB-TASK-114: 创建文件 `lib/api/error_handler.py`
- [ ] SUB-TASK-115: 定义 `ErrorCode` 枚举
- [ ] SUB-TASK-116: 实现 `safe_error_response()` 函数
- [ ] SUB-TASK-117: 实现 error_id 生成（uuid）
- [ ] SUB-TASK-118: 实现日志记录（logger.error）
- [ ] SUB-TASK-119: 实现通用错误消息

**复杂度**: 低
**依赖**: 任务组 4、5 完成
**文件**: lib/api/error_handler.py

**代码示例**:
```python
import uuid
import logging
from enum import Enum

class ErrorCode(Enum):
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_INPUT = "invalid_input"

def safe_error_response(error: Exception, default_message: str = "Internal error") -> Dict:
    error_id = str(uuid.uuid4())
    logger.error(f"[{error_id}] Error: {error}", exc_info=True)

    return {
        'success': False,
        'error': default_message,
        'code': 500,
        'error_id': error_id
    }
```

---

#### 子任务 6-2：集成错误处理

- [ ] SUB-TASK-120: 在 `lib/api/*.py` 导入 error_handler
- [ ] SUB-TASK-121: 替换所有 Exception 处理为 safe_error_response
- [ ] SUB-TASK-122: 区分用户错误（400/404）和系统错误（500）
- [ ] SUB-TASK-123: 确保错误信息不泄露内部细节

**复杂度**: 中
**依赖**: SUB-TASK-114~119
**文件**: lib/api/*.py

---

#### 子任务 6-3：测试错误处理

- [ ] SUB-TASK-124: 创建测试文件 `tests/test_error_handler.py`
- [ ] SUB-TASK-125: 测试系统错误返回通用消息
- [ ] SUB-TASK-126: 测试错误 ID 生成
- [ ] SUB-TASK-127: 测试日志记录
- [ ] SUB-TASK-128: 测试用户错误返回明确消息

**复杂度**: 低
**依赖**: SUB-TASK-120~123
**文件**: tests/test_error_handler.py

---

### 任务组 7：RBAC 持久化

**类型**: 串行
**前置条件**: 任务组 6 完成
**预计时间**: 1 天
**涉及文件**: lib/auth/rbac.py, lib/db/schema.sql
**问题编号**: HIGH-4

#### 子任务 7-1：修改 RBAC Manager

- [ ] SUB-TASK-129: 在 `lib/auth/rbac.py` 导入 db_manager
- [ ] SUB-TASK-130: 修改 `assign_role()` 写入数据库
- [ ] SUB-TASK-131: 修改 `revoke_role()` 删除数据库记录
- [ ] SUB-TASK-132: 修改 `get_user_roles()` 从数据库加载
- [ ] SUB-TASK-133: 实现缓存机制（内存 + 数据库）
- [ ] SUB-TASK-134: 实现 cache invalidation

**复杂度**: 高
**依赖**: 任务组 6 完成
**文件**: lib/auth/rbac.py

**代码示例**:
```python
async def assign_role(self, user_id: str, kb_id: int, role_name: str) -> bool:
    if role_name not in ROLE_DEFINITIONS:
        return False

    # 写入数据库
    query = """
        INSERT INTO kb_members (kb_id, user_id, role, joined_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (kb_id, user_id) DO UPDATE SET role = $3
    """

    await self.db_manager.execute(query, kb_id, user_id, role_name)

    # 更新内存缓存
    if user_id not in self._user_roles:
        self._user_roles[user_id] = {}
    if kb_id not in self._user_roles[user_id]:
        self._user_roles[user_id][kb_id] = set()
    self._user_roles[user_id][kb_id].add(role_name)

    return True
```

---

#### 子任务 7-2：验证数据库 schema

- [ ] SUB-TASK-135: 检查 `lib/db/schema.sql` kb_members 表定义
- [ ] SUB-TASK-136: 确保表存在：kb_id, user_id, role, joined_at
- [ ] SUB-TASK-137: 确保唯一约束：(kb_id, user_id)
- [ ] SUB-TASK-138: 运行 schema 验证

**复杂度**: 低
**依赖**: SUB-TASK-129~134
**文件**: lib/db/schema.sql

---

#### 子任务 7-3：测试 RBAC 持久化

- [ ] SUB-TASK-139: 创建测试文件 `tests/test_rbac_persistence.py`
- [ ] SUB-TASK-140: 测试角色分配写入数据库
- [ ] SUB-TASK-141: 测试角色撤销删除记录
- [ ] SUB-TASK-142: 测试角色查询从数据库加载
- [ ] SUB-TASK-143: 测试缓存失效
- [ ] SUB-TASK-144: 测试重启后角色保留

**复杂度**: 中
**依赖**: SUB-TASK-135~138
**文件**: tests/test_rbac_persistence.py

---

### 任务组 8：N+1 查询优化（可与任务组 9~12 并行）

**类型**: 并行
**前置条件**: 任务组 7 完成
**预计时间**: 0.5 天
**涉及文件**: lib/api/member_api.py, tests/performance/test_member_list.py
**问题编号**: HIGH-5

#### 子任务 8-1：重写成员列表查询

- [ ] SUB-TASK-145: 在 `lib/api/member_api.py` 定位 list_members 方法
- [ ] SUB-TASK-146: 重写为单次批量查询（JOIN）
- [ ] SUB-TASK-147: 使用 LEFT JOIN users 获取 username
- [ ] SUB-TASK-148: 使用 ORDER BY CASE 排序角色
- [ ] SUB-TASK-149: 使用 OFFSET LIMIT 分页
- [ ] SUB-TASK-150: 删除循环查询代码

**复杂度**: 中
**依赖**: 任务组 7 完成
**文件**: lib/api/member_api.py

**代码示例**:
```python
async def list_members(self, user_id: str, kb_id: int, page: int = 1, limit: int = 20):
    query = """
        SELECT
            km.user_id, km.role, km.joined_at, u.username
        FROM kb_members km
        LEFT JOIN users u ON km.user_id = u.id
        WHERE km.kb_id = $1
        ORDER BY
            CASE km.role
                WHEN 'owner' THEN 0
                WHEN 'editor' THEN 1
                WHEN 'reader' THEN 2
            END
        OFFSET $2 LIMIT $3
    """

    results = await self.storage.db_manager.fetch_all(
        query, kb_id, (page - 1) * limit, limit
    )

    members = [{
        'user_id': row['user_id'],
        'username': row.get('username'),
        'role': row['role'],
        'joined_at': row['joined_at']
    } for row in results]

    return {'success': True, 'data': {'members': members}, 'code': 200}
```

---

#### 子任务 8-2：创建性能测试

- [ ] SUB-TASK-151: 创建目录 `tests/performance/`
- [ ] SUB-TASK-152: 创建文件 `tests/performance/test_member_list.py`
- [ ] SUB-TASK-153: 编写 1000 成员查询性能测试
- [ ] SUB-TASK-154: 编写基准对比测试（旧 vs 新）
- [ ] SUB-TASK-155: 设置性能阈值（<100ms）

**复杂度**: 中
**依赖**: SUB-TASK-145~150
**文件**: tests/performance/test_member_list.py

---

#### 子任务 8-3：运行性能测试

- [ ] SUB-TASK-156: 运行性能测试：`pytest tests/performance/ -v`
- [ ] SUB-TASK-157: 对比查询时间（N+1 vs 批量）
- [ ] SUB-TASK-158: 验证性能提升（>50%）
- [ ] SUB-TASK-159: 记录性能指标

**复杂度**: 低
**依赖**: SUB-TASK-151~155
**文件**: 无

---

### 任务组 9：RLS 上下文修复（可与任务组 8、10~12 并行）

**类型**: 并行
**前置条件**: 任务组 7 完成
**预计时间**: 0.5 天
**涉及文件**: lib/auth/rls_manager.py
**问题编号**: HIGH-6

#### 子任务 9-1：修复 RLS 上下文设置

- [ ] SUB-TASK-160: 在 `lib/auth/rls_manager.py` 定位 set_user_context
- [ ] SUB-TASK-161: 确保 SET 在事务中执行
- [ ] SUB-TASK-162: 替换 SET LOCAL 为 SET（持久）
- [ ] SUB-TASK-163: 添加事务检查
- [ ] SUB-TASK-164: 添加错误处理

**复杂度**: 中
**依赖**: 任务组 7 完成
**文件**: lib/auth/rls_manager.py

---

#### 子任务 9-2：测试 RLS 上下文

- [ ] SUB-TASK-165: 创建测试文件 `tests/test_rls_context.py`
- [ ] SUB-TASK-166: 测试上下文在事务中设置
- [ ] SUB-TASK-167: 测试上下文在查询中生效
- [ ] SUB-TASK-168: 测试事务结束后上下文清除
- [ ] SUB-TASK-169: 测试并发事务隔离

**复杂度**: 中
**依赖**: SUB-TASK-160~164
**文件**: tests/test_rls_context.py

---

### 任务组 10：Token 存储加密（可与任务组 8~9、11~12 并行）

**类型**: 并行
**前置条件**: 任务组 7 完成
**预计时间**: 1 天
**涉及文件**: lib/auth.py, requirements.txt
**问题编号**: HIGH-7

#### 子任务 10-1：添加加密依赖

- [ ] SUB-TASK-170: 在 requirements.txt 添加 `cryptography>=41.0.0`
- [ ] SUB-TASK-171: 运行 `pip install cryptography`
- [ ] SUB-TASK-172: 验证安装：`python -c "from cryptography.fernet import Fernet"`

**复杂度**: 低
**依赖**: 任务组 7 完成
**文件**: requirements.txt

---

#### 子任务 10-2：实现加密存储

- [ ] SUB-TASK-173: 在 `lib/auth.py` 导入 Fernet
- [ ] SUB-TASK-174: 生成加密密钥（或从环境变量读取）
- [ ] SUB-TASK-175: 实现 `encrypt_token()` 函数
- [ ] SUB-TASK-176: 实现 `decrypt_token()` 函数
- [ ] SUB-TASK-177: 修改 save_token 使用加密
- [ ] SUB-TASK-178: 修改 load_token 使用解密
- [ ] SUB-TASK-179: 设置文件权限 600

**复杂度**: 高
**依赖**: SUB-TASK-170~172
**文件**: lib/auth.py

---

#### 子任务 10-3：测试 Token 加密

- [ ] SUB-TASK-180: 创建测试文件 `tests/test_token_encryption.py`
- [ ] SUB-TASK-181: 测试 Token 加密功能
- [ ] SUB-TASK-182: 测试 Token 解密功能
- [ ] SUB-TASK-183: 测试加密 Token 无法直接读取
- [ ] SUB-TASK-184: 测试文件权限正确

**复杂度**: 中
**依赖**: SUB-TASK-173~179
**文件**: tests/test_token_encryption.py

---

### 任务组 11：路径遍历防护（可与任务组 8~10、12 并行）

**类型**: 并行
**前置条件**: 任务组 7 完成
**预计时间**: 0.5 天
**涉及文件**: lib/utils/path_validator.py, lib/api_server.py
**问题编号**: HIGH-8

#### 子任务 11-1：创建路径验证器

- [ ] SUB-TASK-185: 创建文件 `lib/utils/path_validator.py`
- [ ] SUB-TASK-186: 实现 `validate_path()` - 检查 ..
- [ ] SUB-TASK-187: 实现 `sanitize_path()` - 清理路径
- [ ] SUB-TASK-188: 实现绝对路径检查
- [ ] SUB-TASK-189: 实现知识库目录边界检查

**复杂度**: 中
**依赖**: 任务组 7 完成
**文件**: lib/utils/path_validator.py

---

#### 子任务 11-2：集成到 API Server

- [ ] SUB-TASK-190: 在 `lib/api_server.py` 导入 path_validator
- [ ] SUB-TASK-191: 在 `_handle_get_atom()` 添加路径验证
- [ ] SUB-TASK-192: 在 `_handle_get_kb()` 添加路径验证
- [ ] SUB-TASK-193: 返回 400 Bad Request for invalid paths
- [ ] SUB-TASK-194: 记录路径遍历攻击日志

**复杂度**: 中
**依赖**: SUB-TASK-185~189
**文件**: lib/api_server.py

---

#### 子任务 11-3：测试路径验证

- [ ] SUB-TASK-195: 创建测试文件 `tests/test_path_validation.py`
- [ ] SUB-TASK-196: 测试 .. 路径被拦截
- [ ] SUB-TASK-197: 测试绝对路径被拦截
- [ ] SUB-TASK-198: 测试有效路径正常处理
- [ ] SUB-TASK-199: 测试路径遍历攻击返回 400

**复杂度**: 中
**依赖**: SUB-TASK-190~194
**文件**: tests/test_path_validation.py

---

### 任务组 12：CORS 配置修复（可与任务组 8~11 并行）

**类型**: 并行
**前置条件**: 任务组 7 完成
**预计时间**: 0.5 天
**涉及文件**: lib/api_server.py
**问题编号**: HIGH-9

#### 子任务 12-1：配置 CORS 策略

- [ ] SUB-TASK-200: 在 `lib/api_server.py` 定义 CORS_ORIGINS 白名单
- [ ] SUB-TASK-201: 配置 Access-Control-Allow-Origin
- [ ] SUB-TASK-202: 配置 Access-Control-Allow-Methods
- [ ] SUB-TASK-203: 配置 Access-Control-Allow-Headers
- [ ] SUB-TASK-204: 配置 Access-Control-Max-Age

**复杂度**: 低
**依赖**: 任务组 7 完成
**文件**: lib/api_server.py

---

#### 子任务 12-2：实现 OPTIONS 处理

- [ ] SUB-TASK-205: 实现 do_OPTIONS 方法
- [ ] SUB-TASK-206: 验证 Origin 在白名单中
- [ ] SUB-TASK-207: 返回预检响应
- [ ] SUB-TASK-208: 添加 CORS headers 到所有响应

**复杂度**: 低
**依赖**: SUB-TASK-200~204
**文件**: lib/api_server.py

---

#### 子任务 12-3：测试 CORS 配置

- [ ] SUB-TASK-209: 创建测试文件 `tests/test_cors.py`
- [ ] SUB-TASK-210: 测试白名单 Origin 通过
- [ ] SUB-TASK-211: 测试非白名单 Origin 拒绝
- [ ] SUB-TASK-212: 测试 OPTIONS 预检请求
- [ ] SUB-TASK-213: 测试 CORS headers 正确

**复杂度**: 低
**依赖**: SUB-TASK-205~208
**文件**: tests/test_cors.py

---

#### 子任务 12-4：验证阶段 2 完成

- [ ] SUB-TASK-214: 运行所有 P1 测试：`pytest tests/ -v -m high`
- [ ] SUB-TASK-215: 检查测试覆盖率：`pytest --cov=lib --cov-report=term-missing`
- [ ] SUB-TASK-216: 手动验证所有 HIGH 问题已修复
- [ ] SUB-TASK-217: 更新进度文档

**复杂度**: 低
**依赖**: 任务组 8~12 完成
**文件**: 无

---

## 阶段 3：P2 问题修复（1-2 周）

**目标**: 修复 10 个 MEDIUM 问题，提升用户体验
**类型**: 全部并行
**验证标准**: 所有 MEDIUM 测试通过

---

### 任务组 13：安全标头和 HTTPS（并行）

**类型**: 并行
**前置条件**: 阶段 2 完成
**预计时间**: 1 天
**涉及文件**: lib/api_server.py
**问题编号**: MEDIUM-2

#### 子任务 13-1：添加安全标头

- [ ] SUB-TASK-218: 添加 X-Content-Type-Options: nosniff
- [ ] SUB-TASK-219: 添加 X-Frame-Options: DENY
- [ ] SUB-TASK-220: 添加 X-XSS-Protection: 1; mode=block
- [ ] SUB-TASK-221: 添加 Content-Security-Policy
- [ ] SUB-TASK-222: 添加 Strict-Transport-Security (生产环境)

**复杂度**: 低
**依赖**: 阶段 2 完成
**文件**: lib/api_server.py

---

#### 子任务 13-2：实现 HTTPS 强制

- [ ] SUB-TASK-223: 检测环境（生产 vs 开发）
- [ ] SUB-TASK-224: 生产环境重定向 HTTP 到 HTTPS
- [ ] SUB-TASK-225: 配置 TLS 证书
- [ ] SUB-TASK-226: 配置 HSTS max-age

**复杂度**: 中
**依赖**: SUB-TASK-218~222
**文件**: lib/api_server.py

---

#### 子任务 13-3：测试安全标头

- [ ] SUB-TASK-227: 创建测试文件 `tests/test_security_headers.py`
- [ ] SUB-TASK-228: 测试所有标头存在
- [ ] SUB-TASK-229: 测试 HTTPS 重定向
- [ ] SUB-TASK-230: 使用安全扫描工具验证

**复杂度**: 低
**依赖**: SUB-TASK-223~226
**文件**: tests/test_security_headers.py

---

### 任务组 14：会话管理改进（并行）

**类型**: 并行
**前置条件**: 阶段 2 完成
**预计时间**: 1 天
**涉及文件**: lib/auth/session_manager.py
**问题编号**: MEDIUM-3

#### 子任务 14-1：实现会话超时

- [ ] SUB-TASK-231: 创建文件 `lib/auth/session_manager.py`
- [ ] SUB-TASK-232: 定义 SESSION_TIMEOUT = 8 hours
- [ ] SUB-TASK-233: 实现会话创建时间记录
- [ ] SUB-TASK-234: 实现会话过期检查
- [ ] SUB-TASK-235: 实现自动清理过期会话

**复杂度**: 中
**依赖**: 阶段 2 完成
**文件**: lib/auth/session_manager.py

---

#### 子任务 14-2：实现会话刷新

- [ ] SUB-TASK-236: 实现会话刷新机制
- [ ] SUB-TASK-237: 活动用户延长会话
- [ ] SUB-TASK-238: 添加刷新 API 端点
- [ ] SUB-TASK-239: 添加最后活动时间跟踪

**复杂度**: 中
**依赖**: SUB-TASK-231~235
**文件**: lib/auth/session_manager.py

---

#### 子任务 14-3：测试会话管理

- [ ] SUB-TASK-240: 创建测试文件 `tests/test_session_manager.py`
- [ ] SUB-TASK-241: 测试会话超时
- [ ] SUB-TASK-242: 测试会话刷新
- [ ] SUB-TASK-243: 测试过期会话清理

**复杂度**: 低
**依赖**: SUB-TASK-236~239
**文件**: tests/test_session_manager.py

---

### 任务组 15：日志和审计（并行）

**类型**: 并行
**前置条件**: 阶段 2 完成
**预计时间**: 2 天
**涉及文件**: lib/logging_config.py, lib/auth/audit_logger.py
**问题编号**: MEDIUM-4

#### 子任务 15-1：日志脱敏处理

- [ ] SUB-TASK-244: 在 `lib/logging_config.py` 实现脱敏过滤器
- [ ] SUB-TASK-245: 识别敏感字段（password, token, email）
- [ ] SUB-TASK-246: 实现自动替换为 ***
- [ ] SUB-TASK-247: 配置日志格式

**复杂度**: 中
**依赖**: 阶段 2 完成
**文件**: lib/logging_config.py

---

#### 子任务 15-2：实现审计日志

- [ ] SUB-TASK-248: 创建文件 `lib/auth/audit_logger.py`
- [ ] SUB-TASK-249: 定义审计事件类型（LOGIN, LOGOUT, KB_ACCESS）
- [ ] SUB-TASK-250: 实现 `log_audit()` 函数
- [ ] SUB-TASK-251: 记录用户操作
- [ ] SUB-TASK-252: 记录时间戳和详情
- [ ] SUB-TASK-253: 写入 audit_log 表

**复杂度**: 中
**依赖**: SUB-TASK-244~247
**文件**: lib/auth/audit_logger.py

---

#### 子任务 15-3：监控安全事件

- [ ] SUB-TASK-254: 定义安全事件（FAILED_LOGIN, PERMISSION_DENIED）
- [ ] SUB-TASK-255: 实现安全事件告警
- [ ] SUB-TASK-256: 配置告警阈值
- [ ] SUB-TASK-257: 实现通知机制

**复杂度**: 中
**依赖**: SUB-TASK-248~253
**文件**: lib/auth/audit_logger.py

---

#### 子任务 15-4：测试审计系统

- [ ] SUB-TASK-258: 创建测试文件 `tests/test_audit_logger.py`
- [ ] SUB-TASK-259: 测试日志脱敏
- [ ] SUB-TASK-260: 测试审计记录
- [ ] SUB-TASK-261: 测试安全事件告警

**复杂度**: 低
**依赖**: SUB-TASK-254~257
**文件**: tests/test_audit_logger.py

---

### 任务组 16：权限检查改进（并行）

**类型**: 并行
**前置条件**: 阶段 2 完成
**预计时间**: 1 天
**涉及文件**: lib/auth/permission_decorator.py
**问题编号**: MEDIUM-5

#### 子任务 16-1：简化权限装饰器

- [ ] SUB-TASK-262: 创建文件 `lib/auth/permission_decorator.py`
- [ ] SUB-TASK-263: 实现 `require_permission` 装饰器
- [ ] SUB-TASK-264: 简化权限检查逻辑
- [ ] SUB-TASK-265: 统一错误处理

**复杂度**: 中
**依赖**: 阶段 2 完成
**文件**: lib/auth/permission_decorator.py

---

#### 子任务 16-2：添加审计日志

- [ ] SUB-TASK-266: 权限检查记录审计日志
- [ ] SUB-TASK-267: 权限拒绝记录审计日志
- [ ] SUB-TASK-268: 记录用户和资源详情

**复杂度**: 低
**依赖**: SUB-TASK-262~265
**文件**: lib/auth/permission_decorator.py

---

#### 子任务 16-3：测试权限装饰器

- [ ] SUB-TASK-269: 创建测试文件 `tests/test_permission_decorator.py`
- [ ] SUB-TASK-270: 测试权限检查
- [ ] SUB-TASK-271: 测试权限拒绝
- [ ] SUB-TASK-272: 测试审计日志

**复杂度**: 低
**依赖**: SUB-TASK-266~268
**文件**: tests/test_permission_decorator.py

---

### 任务组 17：事务管理完善（并行）

**类型**: 并行
**前置条件**: 阶段 2 完成
**预计时间**: 1 天
**涉及文件**: lib/core/db_storage.py, lib/api/*.py
**问题编号**: MEDIUM-6

#### 子任务 17-1：添加事务包装

- [ ] SUB-TASK-273: 在 `lib/core/db_storage.py` 实现 `transaction()` 包装器
- [ ] SUB-TASK-274: 实现事务开始（BEGIN）
- [ ] SUB-TASK-275: 实现事务提交（COMMIT）
- [ ] SUB-TASK-276: 实现事务回滚（ROLLBACK）
- [ ] SUB-TASK-277: 实现异常处理

**复杂度**: 中
**依赖**: 阶段 2 完成
**文件**: lib/core/db_storage.py

---

#### 子任务 17-2：应用到多步操作

- [ ] SUB-TASK-278: 识别所有多步操作
- [ ] SUB-TASK-279: create_kb_with_policy 使用事务
- [ ] SUB-TASK-280: delete_kb_with_policy 使用事务
- [ ] SUB-TASK-281: update_atom_with_permissions 使用事务

**复杂度**: 中
**依赖**: SUB-TASK-273~277
**文件**: lib/api/*.py

---

#### 子任务 17-3：测试事务管理

- [ ] SUB-TASK-282: 创建测试文件 `tests/test_transaction.py`
- [ ] SUB-TASK-283: 测试事务成功提交
- [ ] SUB-TASK-284: 测试事务失败回滚
- [ ] SUB-TASK-285: 测试状态一致性

**复杂度**: 低
**依赖**: SUB-TASK-278~281
**文件**: tests/test_transaction.py

---

### 任务组 18：缓存失效机制（并行）

**类型**: 并行
**前置条件**: 阶段 2 完成
**预计时间**: 0.5 天
**涉及文件**: lib/auth/rbac.py, lib/core/cache_manager.py
**问题编号**: MEDIUM-7

#### 子任务 18-1：实现缓存失效 API

- [ ] SUB-TASK-286: 创建文件 `lib/core/cache_manager.py`
- [ ] SUB-TASK-287: 实现 `invalidate_user_cache()` 函数
- [ ] SUB-TASK-288: 实现 `invalidate_kb_cache()` 函数
- [ ] SUB-TASK-289: 实现 TTL 管理

**复杂度**: 低
**依赖**: 阶段 2 完成
**文件**: lib/core/cache_manager.py

---

#### 子任务 18-2：权限变更触发失效

- [ ] SUB-TASK-290: 在 assign_role 后清除缓存
- [ ] SUB-TASK-291: 在 revoke_role 后清除缓存
- [ ] SUB-TASK-292: 在 delete_kb 后清除缓存
- [ ] SUB-TASK-293: 在 update_permissions 后清除缓存

**复杂度**: 低
**依赖**: SUB-TASK-286~289
**文件**: lib/auth/rbac.py

---

#### 子任务 18-3：测试缓存失效

- [ ] SUB-TASK-294: 创建测试文件 `tests/test_cache_invalidation.py`
- [ ] SUB-TASK-295: 测试权限变更后缓存失效
- [ ] SUB-TASK-296: 测试 TTL 过期后缓存失效
- [ ] SUB-TASK-297: 测试手动清除缓存

**复杂度**: 低
**依赖**: SUB-TASK-290~293
**文件**: tests/test_cache_invalidation.py

---

#### 子任务 18-4：验证阶段 3 完成

- [ ] SUB-TASK-298: 运行所有 P2 测试：`pytest tests/ -v -m medium`
- [ ] SUB-TASK-299: 检查测试覆盖率：`pytest --cov=lib --cov-report=term-missing`
- [ ] SUB-TASK-300: 手动验证所有 MEDIUM 问题已修复
- [ ] SUB-TASK-301: 更新进度文档

**复杂度**: 低
**依赖**: 任务组 13~18 完成
**文件**: 无

---

## 阶段 4：P3 问题修复（持续改进）

**目标**: 修复 LOW 问题，持续优化
**类型**: 持续执行
**验证标准**: 依赖安全审计通过

---

### 任务组 19：依赖安全审计

**类型**: 持续
**前置条件**: 阶段 3 完成
**预计时间**: 持续
**涉及文件**: requirements.txt, .github/dependabot.yml
**问题编号**: LOW-1

#### 子任务 19-1：锁定依赖版本

- [ ] SUB-TASK-302: 检查 requirements.txt 所有依赖版本
- [ ] SUB-TASK-303: 锁定关键依赖版本（bcrypt, pydantic, cryptography）
- [ ] SUB-TASK-304: 生成 requirements.lock

**复杂度**: 低
**依赖**: 阶段 3 完成
**文件**: requirements.txt

---

#### 子任务 19-2：配置 Dependabot

- [ ] SUB-TASK-305: 创建文件 `.github/dependabot.yml`
- [ ] SUB-TASK-306: 配置 Python 依赖检查
- [ ] SUB-TASK-307: 配置每周检查频率
- [ ] SUB-TASK-308: 配置自动 PR 创建

**复杂度**: 低
**依赖**: SUB-TASK-302~304
**文件**: .github/dependabot.yml

---

#### 子任务 19-3：运行安全审计

- [ ] SUB-TASK-309: 安装 pip-audit：`pip install pip-audit`
- [ ] SUB-TASK-310: 运行审计：`pip-audit`
- [ ] SUB-TASK-311: 修复发现的漏洞
- [ ] SUB-TASK-312: 定期运行（每周）

**复杂度**: 低
**依赖**: SUB-TASK-305~308
**文件**: 无

---

#### 子任务 19-4：验证阶段 4 完成

- [ ] SUB-TASK-313: 运行 pip-audit 无漏洞
- [ ] SUB-TASK-314: 检查 Dependabot 配置生效
- [ ] SUB-TASK-315: 更新进度文档
- [ ] SUB-TASK-316: 完成最终验证报告

**复杂度**: 低
**依赖**: SUB-TASK-309~312
**文件**: 无

---

## 执行顺序可视化

```
执行顺序：

1️⃣ 阶段 1（P0 - 串行）- 1-2 天
   ├─ 任务组 1：密码安全重构 (0.5 天)
   │  ├─ SUB-TASK-001~003: 添加 bcrypt 依赖
   │  ├─ SUB-TASK-004~008: 重写密码哈希函数
   │  ├─ SUB-TASK-009~012: 编写测试脚本
   │  └─ SUB-TASK-013~015: 运行测试验证
   │      ↓
   ├─ 任务组 2：认证中间件实现 (1 天)
   │  ├─ SUB-TASK-016~018: 创建认证中间件文件
   │  ├─ SUB-TASK-019~024: 实现 require_auth 装饰器
   │  ├─ SUB-TASK-025~028: 集成到 API Server
   │  ├─ SUB-TASK-029~031: 更新 API 模块
   │  ├─ SUB-TASK-032~036: 测试认证中间件
   │  └─ SUB-TASK-037~040: 验证端点保护
   │      ↓
   └─ 任务组 3：SQL 注入修复 (0.5 天)
      ├─ SUB-TASK-041~045: 创建 SQL 验证工具
      ├─ SUB-TASK-046~051: 修复 db_storage.py
      ├─ SUB-TASK-054~058: 修复 rls_manager.py
      ├─ SUB-TASK-059~063: 测试 SQL 注入防护
      └─ SUB-TASK-064~067: 验证阶段 1 完成
          ↓

2️⃣ 阶段 2（P1 - 部分并行）- 3-5 天
   ├─ 任务组 4：输入验证层 (1 天) ← 与 5 并行
   │  ├─ SUB-TASK-068~070: 添加 Pydantic 依赖
   │  ├─ SUB-TASK-071~077: 创建验证模型
   │  ├─ SUB-TASK-078~085: 集成验证到 API
   │  └─ SUB-TASK-086~091: 测试输入验证
   │
   ├─ 任务组 5：速率限制实现 (1 天) ← 与 4 并行
   │  ├─ SUB-TASK-092~098: 创建速率限制器
   │  ├─ SUB-TASK-099~103: 定义端点限制策略
   │  ├─ SUB-TASK-104~108: 集成到 API Server
   │  └─ SUB-TASK-109~113: 测试速率限制
   │      ↓
   ├─ 任务组 6：错误处理改进 (0.5 天)
   │  ├─ SUB-TASK-114~119: 创建错误处理器
   │  ├─ SUB-TASK-120~123: 集成错误处理
   │  └─ SUB-TASK-124~128: 测试错误处理
   │      ↓
   ├─ 任务组 7：RBAC 持久化 (1 天)
   │  ├─ SUB-TASK-129~134: 修改 RBAC Manager
   │  ├─ SUB-TASK-135~138: 验证数据库 schema
   │  └─ SUB-TASK-139~144: 测试 RBAC 持久化
   │      ↓
   ├─ 任务组 8~12 (并行) - 3.5 天
   │  ├─ 任务组 8：N+1 查询优化 (0.5 天)
   │  │  ├─ SUB-TASK-145~150: 重写成员列表查询
   │  │  ├─ SUB-TASK-151~155: 创建性能测试
   │  │  └─ SUB-TASK-156~159: 运行性能测试
   │  │
   │  ├─ 任务组 9：RLS 上下文修复 (0.5 天)
   │  │  ├─ SUB-TASK-160~164: 修复 RLS 上下文设置
   │  │  └─ SUB-TASK-165~169: 测试 RLS 上下文
   │  │
   │  ├─ 任务组 10：Token 存储加密 (1 天)
   │  │  ├─ SUB-TASK-170~172: 添加加密依赖
   │  │  ├─ SUB-TASK-173~179: 实现加密存储
   │  │  └─ SUB-TASK-180~184: 测试 Token 加密
   │  │
   │  ├─ 任务组 11：路径遍历防护 (0.5 天)
   │  │  ├─ SUB-TASK-185~189: 创建路径验证器
   │  │  ├─ SUB-TASK-190~194: 集成到 API Server
   │  │  └─ SUB-TASK-195~199: 测试路径验证
   │  │
   │  └─ 任务组 12：CORS 配置修复 (0.5 天)
   │     ├─ SUB-TASK-200~204: 配置 CORS 策略
   │     ├─ SUB-TASK-205~208: 实现 OPTIONS 处理
   │     ├─ SUB-TASK-209~213: 测试 CORS 配置
   │     └─ SUB-TASK-214~217: 验证阶段 2 完成
   │        ↓

3️⃣ 阶段 3（P2 - 全部并行）- 1-2 周
   ├─ 任务组 13：安全标头和 HTTPS (1 天)
   │  ├─ SUB-TASK-218~222: 添加安全标头
   │  ├─ SUB-TASK-223~226: 实现 HTTPS 强制
   │  └─ SUB-TASK-227~230: 测试安全标头
   │
   ├─ 任务组 14：会话管理改进 (1 天)
   │  ├─ SUB-TASK-231~235: 实现会话超时
   │  ├─ SUB-TASK-236~239: 实现会话刷新
   │  └─ SUB-TASK-240~243: 测试会话管理
   │
   ├─ 任务组 15：日志和审计 (2 天)
   │  ├─ SUB-TASK-244~247: 日志脱敏处理
   │  ├─ SUB-TASK-248~253: 实现审计日志
   │  ├─ SUB-TASK-254~257: 监控安全事件
   │  └─ SUB-TASK-258~261: 测试审计系统
   │
   ├─ 任务组 16：权限检查改进 (1 天)
   │  ├─ SUB-TASK-262~265: 简化权限装饰器
   │  ├─ SUB-TASK-266~268: 添加审计日志
   │  └─ SUB-TASK-269~272: 测试权限装饰器
   │
   ├─ 任务组 17：事务管理完善 (1 天)
   │  ├─ SUB-TASK-273~277: 添加事务包装
   │  ├─ SUB-TASK-278~281: 应用到多步操作
   │  └─ SUB-TASK-282~285: 测试事务管理
   │
   └─ 任务组 18：缓存失效机制 (0.5 天)
      ├─ SUB-TASK-286~289: 实现缓存失效 API
      ├─ SUB-TASK-290~293: 权限变更触发失效
      ├─ SUB-TASK-294~297: 测试缓存失效
      └─ SUB-TASK-298~301: 验证阶段 3 完成
         ↓

4️⃣ 阶段 4（P3 - 持续）- 持续改进
   └─ 任务组 19：依赖安全审计
      ├─ SUB-TASK-302~304: 锁定依赖版本
      ├─ SUB-TASK-305~308: 配置 Dependabot
      ├─ SUB-TASK-309~312: 运行安全审计
      └─ SUB-TASK-313~316: 验证阶段 4 完成
```

---

## 并行执行策略

### 可并行任务组

| 并行组 | 任务组 | 原因 |
|--------|--------|------|
| **P1 并行组 1** | 任务组 4 + 任务组 5 | 不同文件，无依赖 |
| **P1 并行组 2** | 任务组 8~12 | 不同文件，无依赖 |
| **P2 全部** | 任务组 13~18 | 全部并行，不同文件 |

### 资源冲突分析

| 文件/模块 | 操作任务组 | 并行建议 |
|-----------|-----------|---------|
| `lib/auth.py` | 任务组 1, 10 | **串行**（同一文件） |
| `lib/api_server.py` | 任务组 2, 5, 11, 12 | **串行**（同一文件） |
| `lib/core/db_storage.py` | 任务组 3, 17 | **串行**（同一文件） |
| `lib/auth/rbac.py` | 任务组 7, 18 | **串行**（同一文件） |
| `lib/auth/rls_manager.py` | 任务组 3, 9 | **串行**（同一文件） |

---

## 进度跟踪表

| 阶段 | 任务组 | 状态 | 开始时间 | 完成时间 | 备注 |
|------|--------|------|----------|----------|------|
| P0 | 1. 密码安全 | ⏳ | - | - | 阻塞发布 |
| P0 | 2. 认证中间件 | ⏳ | - | - | 阻塞发布 |
| P0 | 3. SQL 注入 | ⏳ | - | - | 阻塞发布 |
| P1 | 4. 输入验证 | ⏳ | - | - | 可与 5 并行 |
| P1 | 5. 速率限制 | ⏳ | - | - | 可与 4 并行 |
| P1 | 6. 错误处理 | ⏳ | - | - | 依赖 4、5 |
| P1 | 7. RBAC 持久化 | ⏳ | - | - | 依赖 6 |
| P1 | 8. N+1 查询 | ⏳ | - | - | 可与 9~12 并行 |
| P1 | 9. RLS 上下文 | ⏳ | - | - | 可与 8、10~12 并行 |
| P1 | 10. Token 加密 | ⏳ | - | - | 可与 8~9、11~12 并行 |
| P1 | 11. 路径遍历 | ⏳ | - | - | 可与 8~10、12 并行 |
| P1 | 12. CORS 配置 | ⏳ | - | - | 可与 8~11 并行 |
| P2 | 13~18 | ⏳ | - | - | 全部并行 |
| P3 | 19. 依赖审计 | ⏳ | - | - | 持续 |

---

## 验证检查清单

### 阶段 1 完成

- [ ] 密码哈希使用 bcrypt
- [ ] 所有 API 端点需要认证
- [ ] 所有 SQL 查询参数化
- [ ] RLS 策略无 SQL 注入
- [ ] 所有 CRITICAL 测试通过
- [ ] 测试覆盖率 >80%

### 阶段 2 完成

- [ ] 所有输入参数验证
- [ ] 速率限制生效
- [ ] 错误信息无泄露
- [ ] RBAC 持久化正常
- [ ] N+1 查询优化
- [ ] Token 加密存储
- [ ] 路径遍历防护
- [ ] CORS 严格配置
- [ ] 所有 HIGH 测试通过
- [ ] 测试覆盖率 >85%

### 阶段 3 完成

- [ ] HTTPS 强制
- [ ] 安全标头完整
- [ ] 会话超时生效
- [ ] 审计日志记录
- [ ] 事务管理完整
- [ ] 缓存失效机制
- [ ] 所有 MEDIUM 测试通过
- [ ] 测试覆盖率 >90%

### 阶段 4 完成

- [ ] 依赖版本锁定
- [ ] Dependabot 配置
- [ ] pip-audit 无漏洞
- [ ] 定期审计流程

---

**文档创建**: 2026-06-22
**预计完成**: 2-3 周
**总子任务**: 316 个