---
name: PLAN-005-casdoor-sso-integration
description: 阶段 2.1 — Casdoor SSO 单点登录集成实施计划
priority: P1
status: segments-generated
created: 2026-06-23
updated: 2026-06-23
---

# PLAN-005 - Casdoor SSO 集成实施计划

> **所属项目**：PLAN-000 企业化改造
> **阶段**：2.1 Casdoor SSO 集成
> **当前完成度**：0%（仅 schema 预留）
> **预估周期**：4-6 周
> **前置依赖**：阶段 1 已完成（PostgreSQL + 双模式架构）

---

## 一、需求重述

### 1.1 核心需求

集成 Casdoor 实现 SSO 单点登录，支持企业微信/钉钉/飞书第三方登录，与现有本地认证（AuthManager）并存，复用已有 `users` 表和 RLS 权限系统。

### 1.2 功能要求

1. **OAuth2 授权码流程**：用户点击"SSO 登录" → 重定向 Casdoor → 回调获取用户信息 → 自动同步到 `users` 表 → 创建本地会话
2. **多 IdP 支持**：Casdoor 作为统一认证网关，内置对接企业微信/钉钉/飞书
3. **用户自动同步**：首次 SSO 登录自动创建本地用户，后续登录自动更新（name/email/department）
4. **角色映射**：Casdoor 角色 → llm-wiki `global_role`（admin/user）
5. **双认证并存**：本地用户名密码登录保留，SSO 登录为可选增强
6. **会话统一**：SSO 登录后的会话与本地登录共享同一会话管理机制
7. **单点登出**：支持 SSO 单点登出（可选，Casdoor 支持 front-channel logout）

### 1.3 约束条件

| 约束项 | 要求 |
|--------|------|
| 信创友好 | Casdoor 为国产开源，满足信创要求 |
| 向后兼容 | file_mode 不受影响，SSO 仅在 db_mode 下启用 |
| 渐进式 | SSO 可独立开关，不启用时系统行为不变 |
| 无破坏性 | 现有本地用户数据不受影响 |

---

## 二、现状分析

### 2.1 已有基础

| 组件 | 现状 | SSO 集成点 |
|------|------|-----------|
| `users` 表 | ✅ `id VARCHAR(64)` 已预留 Casdoor 用户 ID | 直接写入 |
| RLS 策略 | ✅ 完整的行级安全策略，基于 `current_user_id()` | SSO 用户 ID 可直接用于 RLS |
| `RBACManager` | ✅ 数据库持久化 RBAC | SSO 用户自动获得默认角色 |
| `PermissionMiddleware` | ✅ 统一权限验证 | 透明支持 SSO 用户 |
| `SessionManager` | ✅ 内存会话管理（但未使用） | SSO 会话存入 SessionManager |
| `DatabaseStorage` | ✅ `set_current_user()` 方法 | SSO 登录后调用 |
| Docker Compose | ✅ PostgreSQL + Redis | 新增 Casdoor 服务 |

### 2.2 需要新增的组件

| 组件 | 说明 |
|------|------|
| `CasdoorConfig` | Casdoor 连接配置（endpoint、client_id 等） |
| `CasdoorClient` | Casdoor OAuth2 客户端封装 |
| `SSOAuthProvider` | SSO 认证提供者（实现 OAuth2 授权码流程） |
| `UserSyncService` | Casdoor 用户 → `users` 表同步服务 |
| SSO API 路由 | `/api/auth/sso/login`、`/api/auth/sso/callback`、`/api/auth/sso/logout` |
| Redis 会话存储 | 替换内存 SessionManager，支持多实例共享 |
| 前端 SSO 登录 | login.html 新增 SSO 登录按钮 |
| Casdoor Docker 服务 | docker-compose.yml 新增 Casdoor 容器 |

### 2.3 角色映射问题

当前存在 3 套角色体系，需要统一：

| 来源 | 角色定义 |
|------|----------|
| `AuthManager`（file_mode） | reader=1, editor=2, admin=3 |
| `users.global_role`（db_mode） | user, admin |
| `kb_members.member_role`（db_mode） | owner, editor, reader |

**统一方案**：
- Casdoor 角色 `admin` → `global_role=admin`
- Casdoor 其他角色 → `global_role=user`
- 知识库级权限仍由 `kb_members.member_role` 控制（SSO 登录后由管理员分配）

---

## 三、实施阶段

### Phase 1：基础设施（1 周）

**目标**：配置和连接 Casdoor，新增 SSO 配置项

#### 步骤 1.1：CasdoorConfig 配置模块

- **创建文件**：`lib/auth/casdoor_config.py`
- **内容**：
  ```python
  @dataclass
  class CasdoorConfig:
      enabled: bool = False
      endpoint: str = ""           # http://casdoor:8000
      client_id: str = ""
      client_secret: str = ""
      organization: str = "llm-wiki"
      application: str = "llm-wiki-app"
      certificate: str = ""        # JWT 验证公钥
      redirect_uri: str = ""       # http://localhost:8000/api/auth/sso/callback

      @classmethod
      def from_env(cls) -> 'CasdoorConfig'

      def validate(self) -> List[str]
  ```
- **环境变量**：`SSO_ENABLED`, `CASDOOR_ENDPOINT`, `CASDOOR_CLIENT_ID`, `CASDOOR_CLIENT_SECRET`, `CASDOOR_ORGANIZATION`, `CASDOOR_APPLICATION`, `CASDOOR_CERTIFICATE`, `CASDOOR_REDIRECT_URI`

#### 步骤 1.2：CasdoorClient OAuth2 客户端

- **创建文件**：`lib/auth/casdoor_client.py`
- **内容**：
  ```python
  class CasdoorClient:
      def __init__(self, config: CasdoorConfig)

      def get_authorization_url(self, state: str) -> str
      async def exchange_code(self, code: str) -> CasdoorTokenResponse
      async def get_user_info(self, access_token: str) -> CasdoorUserInfo
      async def validate_jwt(self, token: str) -> Optional[Dict]
      async def refresh_token(self, refresh_token: str) -> CasdoorTokenResponse
      async def get_user_profile(self, user_id: str) -> Optional[Dict]
  ```
- **依赖**：`python-jose[cryptography]`（JWT 验证）、`httpx`（异步 HTTP 客户端）

#### 步骤 1.3：Docker Compose 新增 Casdoor 服务

- **修改文件**：`docker-compose.yml`
- **新增服务**：
  ```yaml
  casdoor:
    image: casbin/casdoor-all-in-one:latest
    ports:
      - "8001:8000"
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      RUNNING_IN_DOCKER: "true"
      DRIVER_NAME: "postgres"
      DATA_SOURCE_NAME: "user=llm_wiki password=llm_wiki_dev host=postgres port=5432 sslmode=disable dbname=casdoor"
    volumes:
      - casdoor_data:/var/casdoor
  ```
- **修改文件**：`.env.example` — 新增 SSO 相关环境变量

#### 步骤 1.4：更新 requirements

- **修改文件**：`pyproject.toml`
- **新增依赖**：`python-jose[cryptography]`（可选依赖组 `sso`）

---

### Phase 2：认证核心（1.5 周）

**目标**：实现 SSO 认证流程和用户同步

#### 步骤 2.1：SSOAuthProvider 认证提供者

- **创建文件**：`lib/auth/sso_provider.py`
- **内容**：
  ```python
  class SSOAuthProvider:
      def __init__(self, casdoor_client: CasdoorClient, config: CasdoorConfig)

      async def initiate_login(self, redirect_url: Optional[str] = None) -> SSOAuthResult:
          """生成授权 URL 和 state 参数"""
          # 1. 生成随机 state（CSRF 防护）
          # 2. 缓存 state → redirect_url 映射（Redis，TTL 10 分钟）
          # 3. 返回 {authorization_url, state}

      async def handle_callback(self, code: str, state: str) -> SSOAuthResult:
          """处理 OAuth2 回调"""
          # 1. 验证 state（防 CSRF）
          # 2. 用 code 换取 access_token
          # 3. 获取用户信息
          # 4. 同步用户到数据库
          # 5. 创建本地会话
          # 6. 返回 {user_id, roles, session_id}

      async def handle_logout(self, session_id: str) -> SSOAuthResult:
          """SSO 单点登出"""
          # 1. 销毁本地会话
          # 2. 返回 Casdoor 登出 URL（前端重定向）

      async def validate_sso_token(self, token: str) -> Optional[Dict]:
          """验证 Casdoor JWT"""
          # 1. 解码 JWT
          # 2. 验证签名（Casdoor 公钥）
          # 3. 检查过期时间
          # 4. 返回 {user_id, name, roles, ...}

  @dataclass
  class SSOAuthResult:
      success: bool
      user_id: Optional[str] = None
      roles: Optional[List[str]] = None
      session_id: Optional[str] = None
      redirect_url: Optional[str] = None
      error: Optional[str] = None
  ```

#### 步骤 2.2：UserSyncService 用户同步服务

- **创建文件**：`lib/auth/user_sync.py`
- **内容**：
  ```python
  class UserSyncService:
      def __init__(self, db_manager)

      async def sync_user_from_casdoor(self, casdoor_user: CasdoorUserInfo) -> SyncResult:
          """从 Casdoor 同步用户到 users 表"""
          # 1. 检查用户是否已存在（by id）
          # 2. 不存在 → INSERT（自动创建）
          # 3. 已存在 → UPDATE（name, email, organization_id, department_id, last_login_at）
          # 4. 同步角色映射：Casdoor role → global_role
          # 5. 返回 {user_id, is_new, roles}

      async def get_or_create_organization(self, org_name: str) -> int:
          """获取或创建组织（与 Casdoor 组织对应）"""

      async def get_or_create_department(self, org_id: int, dept_name: str) -> int:
          """获取或创建部门"""

      async def update_last_login(self, user_id: str) -> None:
          """更新 last_login_at"""
  ```

#### 步骤 2.3：Redis 会话存储

- **修改文件**：`lib/auth/session_manager.py`
- **新增类**：
  ```python
  class RedisSessionManager(SessionManager):
      """基于 Redis 的会话存储，支持多实例共享"""

      def __init__(self, redis_url: str, max_sessions: int = 10000):
          # 连接 Redis
          # 会话以 JSON 序列化存储，key: session:{session_id}
          # 用户索引: user_sessions:{user_id} -> Set[session_id]
          # TTL 与会话超时一致

      async def create_session(self, user_id: str, metadata: Optional[Dict] = None) -> Session
      async def get_session(self, session_id: str) -> Optional[Session]
      async def destroy_session(self, session_id: str) -> bool
      async def destroy_user_sessions(self, user_id: str) -> int
      async def cleanup_expired(self) -> int
  ```
- **环境变量**：`REDIS_URL`（docker-compose.yml 中已定义）
- **选择逻辑**：`REDIS_URL` 存在 → RedisSessionManager，否则 → 内存 SessionManager

#### 步骤 2.4：扩展 AuthManager 支持 SSO

- **修改文件**：`lib/auth.py`
- **修改点**：
  1. `__init__` 新增 `sso_provider: Optional[SSOAuthProvider]` 参数
  2. 新增 `sso_login() -> SSOAuthResult` 方法 — 委托给 SSOAuthProvider
  3. 修改 `validate_token()` — 支持 Casdoor JWT 验证（Bearer token 以 `sso_` 前缀区分，或通过 JWT 结构判断）
  4. 新增 `validate_sso_session(session_id) -> Optional[Dict]` 方法
  5. 修改 `_authenticate()` 调用方 — 统一认证入口

---

### Phase 3：API 集成（1 周）

**目标**：在 web_server.py 中集成 SSO 路由，统一认证流程

#### 步骤 3.1：SSO API 路由

- **修改文件**：`lib/web_server.py`
- **新增路由**：

  | 路由 | 方法 | 说明 |
  |------|------|------|
  | `/api/auth/sso/providers` | GET | 返回可用的 SSO 提供商列表（Casdoor + 子 IdP） |
  | `/api/auth/sso/login` | GET | 发起 SSO 登录（重定向到 Casdoor） |
  | `/api/auth/sso/callback` | GET | OAuth2 回调处理（Casdoor → 本地会话） |
  | `/api/auth/sso/logout` | POST | SSO 单点登出 |

- **修改 `PUBLIC_ENDPOINTS`**：
  ```python
  PUBLIC_ENDPOINTS = {
      '/api/health',
      '/api/auth/login',
      '/api/auth/sso/providers',   # 新增
      '/api/auth/sso/callback',    # 新增
  }
  ```

#### 步骤 3.2：统一认证流程

- **修改文件**：`lib/web_server.py`
- **修改 `_authenticate()` 方法**：
  ```python
  async def _authenticate(self, path: str) -> bool:
      # 1. PUBLIC_ENDPOINTS → 放行
      # 2. Bearer Token:
      #    a. SSO JWT token → sso_provider.validate_sso_token()
      #    b. 本地 API token → auth.validate_token()
      # 3. Cookie Session:
      #    a. 检查 SessionManager（Redis/内存）
      #    b. 兼容旧版文件会话
      # 4. SSO 未启用 → 匿名/guest
      # 5. 认证失败 → 401
  ```

#### 步骤 3.3：DatabaseStorage 用户上下文设置

- **修改文件**：`lib/web_server.py`
- **修改点**：在认证成功后，对 db_mode 请求自动调用 `storage.set_current_user(user_id, roles)`
- **位置**：`_authenticate()` 方法末尾

#### 步骤 3.4：SSO 配置 API

- **修改文件**：`lib/web_server.py`
- **新增路由**：
  - `GET /api/config/sso` — 获取 SSO 配置状态（enabled、providers、login_url）
  - 仅 admin 可访问

---

### Phase 4：前端集成（1 周）

**目标**：登录页面新增 SSO 入口，支持 OAuth2 重定向流程

#### 步骤 4.1：login.html 新增 SSO 登录

- **修改文件**：`views/login.html`
- **新增内容**：
  1. 页面加载时调用 `GET /api/auth/sso/providers` 获取可用 SSO 提供商
  2. 如果 SSO 启用，显示分隔线 + "企业账号登录" 区域
  3. 显示 SSO 提供商按钮（企业微信/钉钉/飞书/Casdoor）
  4. 点击按钮 → `window.location.href = '/api/auth/sso/login?provider=xxx'`
  5. 保留原有用户名密码登录表单

- **UI 设计**：
  ```
  ┌─────────────────────────────┐
  │     📚 LLM Wiki 登录       │
  │                             │
  │  ┌─────────────────────┐   │
  │  │ 用户名              │   │
  │  └─────────────────────┘   │
  │  ┌─────────────────────┐   │
  │  │ 密码                │   │
  │  └─────────────────────┘   │
  │  [ 登 录 ]                 │
  │                             │
  │  ─── 或使用企业账号 ───    │
  │                             │
  │  [🔵 企业微信] [🟡 钉钉]  │
  │  [🔵 飞书]     [🟢 SSO]   │
  │                             │
  └─────────────────────────────┘
  ```

#### 步骤 4.2：auth.js 支持 SSO

- **修改文件**：`views/js/auth.js`
- **新增方法**：
  ```javascript
  const API = {
      // ... 现有方法 ...

      async getSSOProviders()          // GET /api/auth/sso/providers
      ssoLogin(provider)               // window.location.href 重定向
      async handleSSOCallback()         // 解析 URL 参数，POST /api/auth/sso/callback
  };
  ```

#### 步骤 4.3：SSO 回调页面

- **创建文件**：`views/sso-callback.html`（或复用 login.html + query 参数）
- **功能**：
  1. 从 URL 解析 `code` 和 `state`
  2. 调用 `API.handleSSOCallback()`
  3. 成功 → 重定向到首页 `/`
  4. 失败 → 显示错误信息 + 返回登录页

#### 步骤 4.4：管理页面 SSO 配置

- **修改文件**：`views/admin/` 相关管理页面
- **新增**：SSO 配置管理页面（查看状态、配置 Casdoor 连接、管理 IdP）

---

### Phase 5：测试与文档（1 周）

**目标**：全面测试 SSO 流程，编写文档

#### 步骤 5.1：单元测试

- **创建文件**：`tests/auth/test_casdoor_config.py`
  - CasdoorConfig.from_env() 配置解析
  - CasdoorConfig.validate() 校验逻辑
  - 默认值和环境变量覆盖

- **创建文件**：`tests/auth/test_casdoor_client.py`
  - get_authorization_url() URL 生成
  - exchange_code() token 交换（Mock httpx）
  - get_user_info() 用户信息获取
  - validate_jwt() JWT 验证
  - refresh_token() token 刷新
  - 错误处理（网络错误、无效 code、过期 token）

- **创建文件**：`tests/auth/test_sso_provider.py`
  - initiate_login() state 生成和缓存
  - handle_callback() 完整回调流程
  - handle_logout() 登出流程
  - validate_sso_token() JWT 验证
  - CSRF 防护验证（无效 state）
  - 并发回调处理

- **创建文件**：`tests/auth/test_user_sync.py`
  - sync_user_from_casdoor() 新用户创建
  - sync_user_from_casdoor() 已有用户更新
  - 角色映射逻辑
  - 组织/部门自动创建
  - 部分字段缺失处理

- **创建文件**：`tests/auth/test_redis_session.py`
  - Redis 会话 CRUD
  - TTL 过期清理
  - 用户会话批量销毁
  - Redis 连接失败降级

#### 步骤 5.2：集成测试

- **创建文件**：`tests/e2e/test_sso_flow.py`
  - 完整 SSO 登录流程（Mock Casdoor）
  - SSO + 本地登录并存
  - SSO 登录后 RLS 上下文正确
  - SSO 用户创建原子/知识库
  - Token 过期刷新
  - 单点登出

#### 步骤 5.3：Casdoor 初始化脚本

- **创建文件**：`scripts/init-casdoor.py`
- **功能**：
  1. 调用 Casdoor API 创建组织
  2. 创建应用（配置 redirect_uri）
  3. 配置 IdP（企业微信/钉钉/飞书）
  4. 输出 client_id、client_secret、certificate

#### 步骤 5.4：文档

- **更新文件**：`Doc/plans/PLAN-000-enterprise-overall-plan.md` — 更新 2.1 进度
- **创建文件**：`docs/sso-integration-guide.md` — SSO 集成运维指南

---

## 四、依赖关系

```
Phase 1（基础设施）
  ├─→ Phase 2（认证核心）
  │     ├─→ Phase 3（API 集成）
  │     │     └─→ Phase 4（前端集成）
  │     └─────────────→ Phase 5（测试与文档）
  └───────────────────→ Phase 5（测试与文档）
```

- Phase 1 → Phase 2：配置和客户端就绪后才能实现认证逻辑
- Phase 2 → Phase 3：认证核心就绪后才能集成 API 路由
- Phase 3 → Phase 4：API 路由就绪后才能实现前端调用
- Phase 2 → Phase 5：认证核心就绪后可并行编写测试
- Phase 3 → Phase 5：API 集成后可编写集成测试

---

## 五、风险评估

| 风险 | 严重程度 | 概率 | 缓解措施 |
|------|:--------:|:----:|----------|
| Casdoor 版本兼容性 | 高 | 中 | 锁定 Casdoor 版本，编写适配层 |
| JWT 验证公钥轮换 | 中 | 低 | 定期拉取 Casdoor JWKS，本地缓存 |
| 角色映射不一致 | 高 | 中 | 统一角色体系，编写映射测试 |
| Redis 单点故障 | 中 | 低 | Redis 降级为内存 SessionManager |
| CSRF 攻击 | 高 | 低 | state 参数 + Redis 缓存验证 |
| Casdoor 服务不可用 | 高 | 中 | 降级到本地登录，前端显示提示 |
| 用户数据同步冲突 | 中 | 中 | 以 Casdoor 为权威源，本地只读同步 |
| 企业微信/钉钉 IdP 配置复杂 | 中 | 高 | 提供 init-casdoor.py 自动化脚本 |

---

## 六、文件变更清单

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `lib/auth/casdoor_config.py` | Casdoor 配置模块 |
| `lib/auth/casdoor_client.py` | Casdoor OAuth2 客户端 |
| `lib/auth/sso_provider.py` | SSO 认证提供者 |
| `lib/auth/user_sync.py` | 用户同步服务 |
| `views/sso-callback.html` | SSO 回调页面 |
| `scripts/init-casdoor.py` | Casdoor 初始化脚本 |
| `tests/auth/test_casdoor_config.py` | 配置测试 |
| `tests/auth/test_casdoor_client.py` | 客户端测试 |
| `tests/auth/test_sso_provider.py` | SSO 提供者测试 |
| `tests/auth/test_user_sync.py` | 用户同步测试 |
| `tests/auth/test_redis_session.py` | Redis 会话测试 |
| `tests/e2e/test_sso_flow.py` | SSO 集成测试 |
| `docs/sso-integration-guide.md` | SSO 运维指南 |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `lib/auth/__init__.py` | 导出新增模块 |
| `lib/auth/session_manager.py` | 新增 RedisSessionManager |
| `lib/auth.py` | AuthManager 支持 SSO |
| `lib/web_server.py` | SSO 路由 + 统一认证 |
| `lib/core/config.py` | 新增 CasdoorConfig 到 from_env() |
| `views/login.html` | SSO 登录入口 |
| `views/js/auth.js` | SSO 认证方法 |
| `docker-compose.yml` | 新增 Casdoor 服务 |
| `.env.example` | 新增 SSO 环境变量 |
| `pyproject.toml` | 新增 sso 可选依赖组 |

---

## 七、验收标准

1. ✅ SSO 登录流程完整：点击 SSO 按钮 → Casdoor 授权 → 回调 → 自动创建用户 → 进入首页
2. ✅ 本地登录不受影响：用户名密码登录仍可正常使用
3. ✅ RLS 策略正确：SSO 用户的数据隔离与本地用户一致
4. ✅ 角色映射正确：Casdoor admin → global_role=admin
5. ✅ 会话管理统一：SSO 登录和本地登录共享会话机制
6. ✅ Docker Compose 一键启动：`docker compose up` 即可使用 SSO
7. ✅ SSO 可开关：`SSO_ENABLED=false` 时系统行为不变
8. ✅ 测试覆盖率 ≥ 80%：新增模块全部覆盖
9. ✅ Casdoor 不可用时降级：自动降级到本地登录

---

**计划创建时间**：2026-06-23
**计划状态**：segments-generated — 任务已拆分，等待执行
