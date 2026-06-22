# 🔧 PLAN-002 问题修复计划

**制定日期**: 2026-06-22
**修复范围**: 30 个审查问题
**修复周期**: 约 2-3 周
**修复策略**: 分阶段、分优先级、并行执行

---

## 📊 问题总览

| 优先级 | 数量 | 修复周期 | 阻塞发布 |
|--------|------|---------|----------|
| **P0 (CRITICAL)** | 7 | 1-2 天 | ✅ 是 |
| **P1 (HIGH)** | 10 | 3-5 天 | ✅ 是 |
| **P2 (MEDIUM)** | 10 | 1-2 周 | ❌ 否 |
| **P3 (LOW)** | 3 | 持续改进 | ❌ 否 |
| **总计** | **30** | **2-3 周** | - |

---

## 🚨 第一阶段：P0 问题修复（1-2 天）

**目标**: 修复 7 个 CRITICAL 问题，确保核心安全

### 任务组 1：密码安全重构

**问题**: CRITICAL-1 - 不安全的密码哈希算法

**修复内容**:
- 替换 SHA-256 + 固定盐 → bcrypt
- 重写 `hash_password()` 和 `verify_password()`
- 更新现有用户密码（迁移策略）

**文件修改**:
```
lib/auth.py
  - hash_password(): 改用 bcrypt.hashpw()
  - verify_password(): 改用 bcrypt.checkpw()
  - authenticate(): 更新验证逻辑

requirements.txt
  - 添加: bcrypt>=4.0.0
```

**代码示例**:
```python
import bcrypt

def hash_password(password: str) -> str:
    """使用 bcrypt 安全哈希密码"""
    salt = bcrypt.gensalt(rounds=12)  # 2^12 次迭代
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, stored_hash: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        password.encode('utf-8'),
        stored_hash.encode('utf-8')
    )
```

**测试验证**:
```bash
# 测试密码哈希
python -c "
import bcrypt
hashed = bcrypt.hashpw('test123'.encode(), bcrypt.gensalt())
print(f'Hashed: {hashed}')
print(f'Verify: {bcrypt.checkpw(\"test123\".encode(), hashed)}')
"
```

**预计时间**: 0.5 天

---

### 任务组 2：认证中间件实现

**问题**: CRITICAL-4 - 缺少认证的 API 端点

**修复内容**:
- 实现 `require_auth` 装饰器
- 所有 API 端点添加认证检查
- 健康检查端点保持公开

**文件修改**:
```
lib/auth/auth_middleware.py（新建）
  - require_auth 装饰器
  - Token 验证逻辑
  - 用户上下文设置

lib/api_server.py
  - 导入 auth_middleware
  - 所有端点添加 @require_auth

lib/api/*.py
  - 所有 API 方法添加认证检查
```

**代码示例**:
```python
from functools import wraps

def require_auth(func):
    """认证装饰器"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 检查 Authorization header
        auth_header = self.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            self._json_response({'error': 'Missing authentication'}, 401)
            return None
        
        token = auth_header[7:]
        
        # 验证 token
        auth = self._get_auth_manager()
        user_info = auth.validate_token(token)
        
        if not user_info:
            self._json_response({'error': 'Invalid token'}, 401)
            return None
        
        # 设置用户上下文
        self.current_user = user_info['username']
        self.current_role = user_info['role']
        
        return func(self, *args, **kwargs)
    return wrapper

# 使用
class APIRequestHandler(BaseHTTPRequestHandler):
    @require_auth
    def _handle_list_atoms(self, params: Dict) -> None:
        # 原有逻辑
        pass
```

**测试验证**:
```bash
# 测试无认证请求
curl http://localhost:5000/api/kbs
# 预期: 401 Unauthorized

# 测试有效认证
curl -H "Authorization: Bearer <valid_token>" http://localhost:5000/api/kbs
# 预期: 200 OK
```

**预计时间**: 1 天

---

### 任务组 3：SQL 注入修复

**问题**: CRITICAL-2, CRITICAL-3 - SQL 拼接导致注入风险

**修复内容**:
- 重写所有动态 SQL 构建逻辑
- 使用参数化查询 + 白名单验证
- 添加标识符验证函数

**文件修改**:
```
lib/core/db_storage.py
  - list_kbs(): 白名单验证 + 参数化
  - update_kb(): 白名单验证
  - update_atom(): 白名单验证

lib/auth/rls_manager.py
  - create_kb_policy(): 类型验证 + quote_ident
  - drop_kb_policy(): 类型验证
  - create_atom_policy(): 类型验证
  - drop_atom_policy(): 类型验证

lib/utils/sql_validator.py（新建）
  - validate_identifier()
  - validate_table_name()
  - sanitize_sql_string()
```

**代码示例**:
```python
import re

def validate_identifier(value: str) -> bool:
    """验证 SQL 标识符"""
    # 只允许字母、数字、下划线、连字符
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', value))

# db_storage.py
async def list_kbs(self, user_id: Optional[str] = None, scope: Optional[str] = None) -> List[Dict]:
    """列出知识库"""
    conditions = []
    params = []

    if user_id:
        # ✅ 验证标识符
        if not validate_identifier(user_id):
            raise ValueError(f"Invalid user_id: {user_id}")
        conditions.append("owner_id = $1")
        params.append(user_id)

    if scope:
        # ✅ 白名单验证
        valid_scopes = ['personal', 'department', 'project', 'company']
        if scope not in valid_scopes:
            raise ValueError(f"Invalid scope: {scope}")
        conditions.append(f"scope = ${len(params) + 1}")
        params.append(scope)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"SELECT * FROM knowledge_bases {where_clause} ORDER BY updated_at DESC"

    return await self.db_manager.fetch_all(query, *params)

# rls_manager.py
async def create_kb_policy(self, kb_id: int) -> None:
    """为知识库创建 RLS 策略"""
    # ✅ 严格类型检查
    if not isinstance(kb_id, int) or kb_id <= 0:
        raise ValueError(f"Invalid kb_id: {kb_id}")
    
    policy_name = f"kb_{kb_id}_policy"
    
    # ✅ 使用 PostgreSQL quote_ident 函数
    query = """
        DO $$
        BEGIN
            EXECUTE format(
                'CREATE POLICY %I ON knowledge_bases
                FOR ALL
                USING (
                    id IN (
                        SELECT kb_id FROM kb_members
                        WHERE user_id = current_setting(''llmwiki.current_user_id'')::TEXT
                    )
                    OR owner_id = current_setting(''llmwiki.current_user_id'')::TEXT
                )',
                %L
            );
        END $$;
    """
    
    await self.db_manager.execute(query, policy_name)
```

**测试验证**:
```bash
# 测试 SQL 注入
curl "http://localhost:5000/api/kbs?scope=personal'; DROP TABLE knowledge_bases; --"
# 预期: 400 Bad Request

# 测试路径遍历
curl "http://localhost:5000/api/atoms/../../../etc/passwd"
# 预期: 400 Bad Request
```

**预计时间**: 0.5 天

---

## ⚠️ 第二阶段：P1 问题修复（3-5 天）

**目标**: 修复 10 个 HIGH 问题，确保生产可用

### 任务组 4：输入验证层

**问题**: HIGH-1, MEDIUM-1 - 缺少输入验证

**修复内容**:
- 实现 Pydantic 验证模型
- 所有 API 端点添加验证
- 添加范围检查和格式验证

**文件修改**:
```
lib/api/validators.py（新建）
  - ListAtomsRequest (Pydantic)
  - QueryRequest (Pydantic)
  - CreateKBRequest (Pydantic)
  - UpdateKBRequest (Pydantic)

lib/api/*.py
  - 所有 API 方法使用验证模型

requirements.txt
  - 添加: pydantic>=2.0.0
```

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

**预计时间**: 1 天

---

### 任务组 5：速率限制实现

**问题**: HIGH-2 - 缺少速率限制

**修复内容**:
- 实现 RateLimiter 中间件
- 不同端点设置不同限制
- 添加 IP 和用户级限制

**文件修改**:
```
lib/api/rate_limiter.py（新建）
  - RateLimiter 类
  - 不同端点的限制策略
  - 内存缓存（带过期）

lib/api_server.py
  - 集成速率限制
  - 返回 429 状态码
```

**代码示例**:
```python
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock

class RateLimiter:
    """速率限制器"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.requests = defaultdict(list)
        self.lock = Lock()
    
    def is_allowed(self, client_id: str) -> bool:
        """检查是否允许请求"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        with self.lock:
            # 清理过期记录
            self.requests[client_id] = [
                t for t in self.requests[client_id]
                if t > cutoff
            ]
            
            # 检查限制
            if len(self.requests[client_id]) >= self.rpm:
                return False
            
            # 记录请求
            self.requests[client_id].append(now)
            return True

# 不同端点的限制策略
RATE_LIMITS = {
    '/api/query': 30,      # 查询：30/分钟
    '/api/ingest': 10,     # 摄入：10/分钟
    '/api/embed': 5,       # 嵌入：5/分钟
    'default': 60,         # 默认：60/分钟
}
```

**预计时间**: 1 天

---

### 任务组 6：错误处理改进

**问题**: HIGH-3 - 错误信息泄露内部细节

**修复内容**:
- 实现安全的错误响应
- 区分用户错误和系统错误
- 记录详细错误到日志

**文件修改**:
```
lib/api/error_handler.py（新建）
  - safe_error_response()
  - ErrorCode 枚举
  - 错误 ID 生成

lib/api/*.py
  - 所有错误处理使用安全响应
```

**代码示例**:
```python
import uuid
import logging

class ErrorCode(Enum):
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_INPUT = "invalid_input"

def safe_error_response(error: Exception, default_message: str = "Internal error") -> Dict:
    """安全的错误响应"""
    # 记录详细错误
    error_id = str(uuid.uuid4())
    logger.error(f"[{error_id}] Error: {error}", exc_info=True)
    
    # 返回通用错误
    return {
        'success': False,
        'error': default_message,
        'code': 500,
        'error_id': error_id
    }

# 使用
except FileNotFoundError as e:
    return {
        'success': False,
        'error': 'Resource not found',
        'code': 404
    }

except Exception as e:
    return safe_error_response(e, "Internal server error")
```

**预计时间**: 0.5 天

---

### 任务组 7：RBAC 持久化

**问题**: HIGH-4 - RBAC 权限仅内存存储

**修复内容**:
- 修改 RBACManager 使用数据库存储
- 实现缓存机制（内存 + 数据库）
- 支持多实例部署

**文件修改**:
```
lib/auth/rbac.py
  - assign_role(): 写入 kb_members 表
  - revoke_role(): 删除 kb_members 记录
  - get_user_roles(): 从数据库加载
  - 添加缓存机制

lib/db/schema.sql
  - 确保 kb_members 表存在
```

**代码示例**:
```python
async def assign_role(self, user_id: str, kb_id: int, role_name: str) -> bool:
    """为用户分配角色（持久化到数据库）"""
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
    
    logger.info(f"Assigned role {role_name} to user {user_id} for KB {kb_id}")
    return True
```

**预计时间**: 1 天

---

### 任务组 8：N+1 查询优化

**问题**: HIGH-5 - N+1 查询问题

**修复内容**:
- 重写成员列表查询为批量查询
- 使用 JOIN 减少查询次数
- 添加查询性能测试

**文件修改**:
```
lib/api/member_api.py
  - list_members(): 单次批量查询
  - 添加性能基准测试

tests/performance/test_member_list.py（新建）
  - 1000 成员查询性能测试
```

**代码示例**:
```python
async def list_members(self, user_id: str, kb_id: int, page: int = 1, limit: int = 20) -> Dict:
    """查询知识库成员列表（优化版）"""
    # ✅ 单次查询获取所有成员及其角色
    query = """
        SELECT 
            km.user_id,
            km.role,
            km.joined_at,
            u.username
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
    
    # 处理结果（无需额外查询）
    members = []
    for row in results:
        members.append({
            'user_id': row['user_id'],
            'username': row.get('username'),
            'role': row['role'],
            'joined_at': row['joined_at']
        })
    
    return {
        'success': True,
        'data': {'members': members},
        'code': 200
    }
```

**预计时间**: 0.5 天

---

### 任务组 9：RLS 上下文修复

**问题**: HIGH-6 - RLS 策略未正确绑定用户上下文

**修复内容**:
- 确保 RLS 上下文在事务中设置
- 使用 SET 而非 SET LOCAL
- 添加事务管理

**文件修改**:
```
lib/auth/rls_manager.py
  - set_user_context(): 确保在事务中
  - 添加事务检查
```

**预计时间**: 0.5 天

---

### 任务组 10：Token 存储加密

**问题**: HIGH-7 - Token 明文存储

**修复内容**:
- 使用加密存储 Token
- 或迁移到数据库存储
- 设置正确的文件权限

**文件修改**:
```
lib/auth.py
  - 使用 Fernet 加密
  - 或迁移到数据库

requirements.txt
  - 添加: cryptography>=41.0.0
```

**预计时间**: 1 天

---

### 任务组 11：路径遍历防护

**问题**: HIGH-8 - 路径遍历风险

**修复内容**:
- 验证所有路径参数
- 确保路径在知识库目录内
- 防止 .. 和绝对路径

**文件修改**:
```
lib/api_server.py
  - _handle_get_atom(): 添加路径验证

lib/utils/path_validator.py（新建）
  - validate_path()
  - sanitize_path()
```

**预计时间**: 0.5 天

---

### 任务组 12：CORS 配置修复

**问题**: HIGH-9 - CORS 配置不当

**修复内容**:
- 配置严格的 CORS 策略
- 白名单验证来源
- 添加预检请求处理

**文件修改**:
```
lib/api_server.py
  - 严格的 CORS 配置
  - 添加 OPTIONS 处理
```

**预计时间**: 0.5 天

---

## 📝 第三阶段：P2 问题修复（1-2 周）

**目标**: 修复 10 个 MEDIUM 问题，提升用户体验

### 任务组 13：安全标头和 HTTPS

**修复内容**:
- 添加所有安全标头
- 强制 HTTPS（生产环境）
- HSTS 配置

**预计时间**: 1 天

---

### 任务组 14：会话管理改进

**修复内容**:
- 实现会话超时（8 小时）
- 会话刷新机制
- 自动清理过期会话

**预计时间**: 1 天

---

### 任务组组 15：日志和审计

**修复内容**:
- 日志脱敏处理
- 实现审计日志系统
- 监控安全事件

**预计时间**: 2 天

---

### 任务组 16：权限检查改进

**修复内容**:
- 简化权限装饰器
- 添加审计日志
- 统一错误处理

**预计时间**: 1 天

---

### 任务组 17：事务管理完善

**修复内容**:
- 所有多步操作添加事务
- 实现回滚处理
- 状态一致性保障

**预计时间**: 1 天

---

### 任务组 18：缓存失效机制

**修复内容**:
- 权限变更时清除缓存
- 实现缓存失效 API
- TTL 优化

**预计时间**: 0.5 天

---

## 🔄 第四阶段：P3 问题修复（持续改进）

**目标**: 修复 LOW 问题，持续优化

### 任务组 19：依赖安全审计

**修复内容**:
- 锁定依赖版本
- 定期运行 pip audit
- 使用 Dependabot

**预计时间**: 持续

---

## 📊 修复进度跟踪

### 总体进度表

```
阶段 1（P0）：1-2 天
  ├─ 任务组 1：密码安全（0.5 天）
  ├─ 任务组 2：认证中间件（1 天）
  └─ 任务组 3：SQL 注入（0.5 天）

阶段 2（P1）：3-5 天
  ├─ 任务组 4：输入验证（1 天）
  ├─ 任务组 5：速率限制（1 天）
  ├─ 任务组 6：错误处理（0.5 天）
  ├─ 任务组 7：RBAC 持久化（1 天）
  ├─ 任务组 8：N+1 查询（0.5 天）
  ├─ 任务组 9：RLS 上下文（0.5 天）
  ├─ 任务组 10：Token 加密（1 天）
  ├─ 任务组 11：路径遍历（0.5 天）
  └─ 任务组 12：CORS 配置（0.5 天）

阶段 3（P2）：1-2 周
  ├─ 任务组 13：安全标头（1 天）
  ├─ 任务组 14：会话管理（1 天）
  ├─ 任务组 15：日志审计（2 天）
  ├─ 任务组 16：权限检查（1 天）
  ├─ 任务组 17：事务管理（1 天）
  └─ 任务组 18：缓存失效（0.5 天）

阶段 4（P3）：持续改进
  └─ 任务组 19：依赖审计（持续）
```

---

## 🎯 执行策略

### 并行执行建议

**阶段 1（P0）**：串行执行
- 严格依赖关系
- 每完成一个验证通过

**阶段 2（P1）**：部分并行
- 任务组 4-5 可并行（不同开发者）
- 任务组 8-12 可并行

**阶段 3（P2）**：并行执行
- 所有任务组可并行

---

## ✅ 验证检查清单

### 阶段 1 完成标准

- [ ] 密码哈希使用 bcrypt
- [ ] 所有 API 端点需要认证
- [ ] 所有 SQL 查询参数化
- [ ] RLS 策略无 SQL 注入
- [ ] 所有 CRITICAL 测试通过

### 阶段 2 完成标准

- [ ] 所有输入参数验证
- [ ] 速率限制生效
- [ ] 错误信息无泄露
- [ ] RBAC 持久化正常
- [ ] N+1 查询优化
- [ ] Token 加密存储
- [ ] 路径遍历防护
- [ ] CORS 严格配置
- [ ] 所有 HIGH 测试通过

### 阶段 3 完成标准

- [ ] HTTPS 强制
- [ ] 安全标头完整
- [ ] 会话超时生效
- [ ] 审计日志记录
- [ ] 事务管理完整
- [ ] 所有 MEDIUM 测试通过

---

## 📄 相关文档

- **审查报告**: `.claude/plans/PLAN-002-review-summary.md`
- **修复计划**: `.claude/plans/PLAN-002-fix-plan.md`
- **任务组拆分**: `.claude/plans/PLAN-002-fix-plan-segments.md` ✅ 已生成

---

**计划制定**: 2026-06-22
**任务组拆分**: 2026-06-22
**预计完成**: 2-3 周
**执行方式**: 分阶段、分优先级、并行执行
**当前状态**: 任务组已拆分，准备执行