---
name: PLAN-005-casdoor-sso-integration-segments
description: PLAN-005 任务拆分 — Casdoor SSO 集成可执行任务组
priority: P1
status: active
created: 2026-06-23
parent: PLAN-005-casdoor-sso-integration
---

# PLAN-005 任务拆分 — Casdoor SSO 集成

> **父计划**：PLAN-005-casdoor-sso-integration.md
> **总任务组**：7 个
> **串行任务组**：5 个
> **并行任务组**：2 个
> **总子任务**：35 个

---

## 执行顺序

```
1️⃣ 任务组 A（基础设施 — 配置 + Docker）
   ↓
2️⃣ 任务组 B（认证核心 — CasdoorClient + SSOAuthProvider）  ← 与 C 并行
3️⃣ 任务组 C（会话存储 — RedisSessionManager + UserSyncService）  ← 与 B 并行
   ↓
4️⃣ 任务组 D（AuthManager 集成 — 扩展认证管理器）
   ↓
5️⃣ 任务组 E（API 路由 — web_server SSO 集成）
   ↓
6️⃣ 任务组 F（前端 — login.html + auth.js + 回调页）
   ↓
7️⃣ 任务组 G（测试 + 文档 + 初始化脚本）
```

---

## 任务组 A：基础设施 — 配置与 Docker

**类型：** 串行
**前置条件：** 无
**预估耗时：** 1-2 小时

#### A-1：CasdoorConfig 配置模块

- [ ] SUB-TASK-001: 创建 `lib/auth/casdoor_config.py`，实现 `CasdoorConfig` dataclass
  - 字段：enabled, endpoint, client_id, client_secret, organization, application, certificate, redirect_uri
  - 方法：`from_env()` 解析 8 个环境变量（SSO_ENABLED, CASDOOR_*）
  - 方法：`validate()` 返回校验错误列表
  - 默认值：enabled=False, organization="llm-wiki", application="llm-wiki-app"
- [ ] SUB-TASK-002: 编写 `tests/auth/test_casdoor_config.py`
  - 测试 from_env() 默认值
  - 测试 from_env() 环境变量覆盖
  - 测试 validate() 启用时必填字段
  - 测试 validate() 禁用时跳过校验
  - 测试端点 URL 格式校验

#### A-2：依赖与 Docker 配置

- [ ] SUB-TASK-003: 修改 `pyproject.toml`，新增 `[sso]` 可选依赖组
  - `python-jose[cryptography]>=3.3.0` — JWT 验证
  - `httpx>=0.25.0` — 异步 HTTP 客户端
  - `redis>=5.0.0` — Redis 会话存储
- [ ] SUB-TASK-004: 修改 `docker-compose.yml`，新增 Casdoor 服务
  - 镜像：`casbin/casdoor-all-in-one:latest`
  - 端口：8001:8000
  - 依赖：postgres (service_healthy)
  - 环境变量：DRIVER_NAME=postgres, DATA_SOURCE_NAME 指向 postgres
  - 数据卷：casdoor_data
- [ ] SUB-TASK-005: 修改 `.env.example`，新增 SSO 环境变量
  - SSO_ENABLED=false
  - CASDOOR_ENDPOINT, CASDOOR_CLIENT_ID, CASDOOR_CLIENT_SECRET
  - CASDOOR_ORGANIZATION, CASDOOR_APPLICATION, CASDOOR_CERTIFICATE
  - CASDOOR_REDIRECT_URI
- [ ] SUB-TASK-006: 修改 `lib/auth/__init__.py`，导出新增模块
  - 导出 CasdoorConfig, CasdoorClient, SSOAuthProvider, UserSyncService

---

## 任务组 B：认证核心 — CasdoorClient + SSOAuthProvider

**类型：** 并行（与任务组 C 同时执行）
**前置条件：** 任务组 A 完成
**预估耗时：** 3-4 小时

#### B-1：CasdoorClient OAuth2 客户端

- [ ] SUB-TASK-007: 创建 `lib/auth/casdoor_client.py`，实现 `CasdoorClient` 类
  - `__init__(config: CasdoorConfig)` — 初始化 httpx.AsyncClient
  - `get_authorization_url(state: str) -> str` — 拼接 Casdoor 授权 URL
  - `async exchange_code(code: str) -> CasdoorTokenResponse` — code 换 token
  - `async get_user_info(access_token: str) -> CasdoorUserInfo` — 获取用户信息
  - `async validate_jwt(token: str) -> Optional[Dict]` — JWT 解码验证
  - `async refresh_token(refresh_token: str) -> CasdoorTokenResponse` — 刷新 token
  - 定义 `CasdoorTokenResponse` 和 `CasdoorUserInfo` dataclass
- [ ] SUB-TASK-008: 编写 `tests/auth/test_casdoor_client.py`
  - 测试 get_authorization_url() URL 格式（含 state, client_id, redirect_uri）
  - 测试 exchange_code() 成功流程（Mock httpx 响应）
  - 测试 exchange_code() 无效 code 错误
  - 测试 get_user_info() 成功流程
  - 测试 validate_jwt() 有效/过期/签名错误
  - 测试 refresh_token() 成功/失败
  - 测试网络超时错误处理

#### B-2：SSOAuthProvider 认证提供者

- [ ] SUB-TASK-009: 创建 `lib/auth/sso_provider.py`，实现 `SSOAuthProvider` 类
  - `__init__(casdoor_client: CasdoorClient, config: CasdoorConfig, session_manager: SessionManager, user_sync: UserSyncService)`
  - `async initiate_login(redirect_url: Optional[str] = None) -> SSOAuthResult`
    - 生成 secrets.token_urlsafe(32) 作为 state
    - state → redirect_url 映射存入 Redis（TTL 600s）
    - 返回 authorization_url + state
  - `async handle_callback(code: str, state: str) -> SSOAuthResult`
    - 验证 state 存在且未过期（CSRF 防护）
    - 用 code 换 access_token
    - 获取 Casdoor 用户信息
    - 调用 user_sync.sync_user_from_casdoor() 同步用户
    - 调用 session_manager.create_session() 创建会话
    - 返回 user_id, roles, session_id
  - `async handle_logout(session_id: str) -> SSOAuthResult`
    - 销毁本地会话
    - 返回 Casdoor 登出 URL
  - `async validate_sso_token(token: str) -> Optional[Dict]`
    - 委托 CasdoorClient.validate_jwt()
  - 定义 `SSOAuthResult` dataclass（success, user_id, roles, session_id, redirect_url, error）
- [ ] SUB-TASK-010: 编写 `tests/auth/test_sso_provider.py`
  - 测试 initiate_login() 返回有效 URL 和 state
  - 测试 handle_callback() 完整成功流程（Mock CasdoorClient + UserSyncService）
  - 测试 handle_callback() 无效 state 拒绝（CSRF 防护）
  - 测试 handle_callback() 过期 state 拒绝
  - 测试 handle_callback() Casdoor code 交换失败
  - 测试 handle_logout() 会话销毁
  - 测试 validate_sso_token() 有效 JWT
  - 测试 validate_sso_token() 过期 JWT 返回 None

---

## 任务组 C：会话存储与用户同步

**类型：** 并行（与任务组 B 同时执行）
**前置条件：** 任务组 A 完成
**预估耗时：** 2-3 小时

#### C-1：Redis 会话存储

- [ ] SUB-TASK-011: 修改 `lib/auth/session_manager.py`，新增 `RedisSessionManager` 类
  - 继承 SessionManager 接口
  - `__init__(redis_url: str, max_sessions: int = 10000)`
  - 使用 `redis.asyncio` 连接
  - 会话存储：`session:{session_id}` → JSON（TTL = session_timeout）
  - 用户索引：`user_sessions:{user_id}` → Set[session_id]
  - `async create_session(user_id, metadata) -> Session` — 写入 Redis + 更新索引
  - `async get_session(session_id) -> Optional[Session]` — 读取并 touch
  - `async destroy_session(session_id) -> bool` — 删除 + 清理索引
  - `async destroy_user_sessions(user_id) -> int` — 批量删除
  - `async cleanup_expired() -> int` — Redis TTL 自动过期，此方法返回 0
  - 新增工厂方法 `create_session_manager(redis_url: Optional[str] = None) -> SessionManager`
    - redis_url 存在 → RedisSessionManager
    - 否则 → 内存 SessionManager
- [ ] SUB-TASK-012: 编写 `tests/auth/test_redis_session.py`
  - 测试 create_session() 写入 Redis
  - 测试 get_session() 读取
  - 测试 destroy_session() 删除
  - 测试 destroy_user_sessions() 批量删除
  - 测试 TTL 过期后 get_session() 返回 None
  - 测试 Redis 连接失败时降级到内存（需 mock）
  - 测试 create_session_manager() 工厂方法

#### C-2：用户同步服务

- [ ] SUB-TASK-013: 创建 `lib/auth/user_sync.py`，实现 `UserSyncService` 类
  - `__init__(db_manager)` — 接受 PostgreSQLManager
  - `async sync_user_from_casdoor(casdoor_user: CasdoorUserInfo) -> SyncResult`
    - SELECT by id → 存在则 UPDATE，不存在则 INSERT
    - 角色映射：admin → admin，其他 → user
    - 更新 name, email, organization_id, department_id, last_login_at
    - 返回 SyncResult(user_id, is_new, roles)
  - `async get_or_create_organization(org_name: str) -> int`
    - INSERT ON CONFLICT DO UPDATE RETURNING id
  - `async get_or_create_department(org_id: int, dept_name: str) -> int`
    - INSERT ON CONFLICT DO UPDATE RETURNING id
  - `async update_last_login(user_id: str) -> None`
  - 定义 `SyncResult` dataclass（user_id, is_new, roles）
- [ ] SUB-TASK-014: 编写 `tests/auth/test_user_sync.py`
  - 测试新用户创建（INSERT）
  - 测试已有用户更新（UPDATE）
  - 测试角色映射 admin → admin
  - 测试角色映射 member → user
  - 测试 get_or_create_organization() 新建
  - 测试 get_or_create_organization() 已存在
  - 测试 get_or_create_department() 新建
  - 测试 update_last_login() 时间更新
  - 测试部分字段缺失（email=None, phone=None）

---

## 任务组 D：AuthManager SSO 集成

**类型：** 串行
**前置条件：** 任务组 B + C 完成
**预估耗时：** 2-3 小时

#### D-1：扩展 AuthManager

- [ ] SUB-TASK-015: 修改 `lib/auth.py`，AuthManager 新增 SSO 支持
  - `__init__` 新增参数：`sso_provider: Optional[SSOAuthProvider] = None`，`session_manager: Optional[SessionManager] = None`
  - 新增 `sso_login() -> SSOAuthResult` — 委托 SSOAuthProvider.initiate_login()
  - 新增 `sso_callback(code, state) -> SSOAuthResult` — 委托 SSOAuthProvider.handle_callback()
  - 新增 `sso_logout(session_id) -> SSOAuthResult` — 委托 SSOAuthProvider.handle_logout()
  - 修改 `validate_token(token)` — 新增 JWT 检测逻辑：
    - 如果 token 以 `eyJ` 开头（JWT 格式）→ 尝试 sso_provider.validate_sso_token()
    - 否则 → 走原有本地 token 验证
  - 新增 `validate_sso_session(session_id) -> Optional[Dict]`
    - 从 session_manager 获取会话
    - 返回 {user_id, roles, ...}
  - 新增 `is_sso_enabled() -> bool` — 返回 sso_provider is not None
- [ ] SUB-TASK-016: 修改 `lib/auth.py`，确保 file_mode 不受影响
  - sso_provider 和 session_manager 为 None 时，所有 SSO 方法返回失败或抛出不支持错误
  - validate_token() 仅在 sso_provider 存在时才尝试 JWT 验证
  - 原有文件会话（current-user.json）逻辑不变

---

## 任务组 E：API 路由集成

**类型：** 串行
**前置条件：** 任务组 D 完成
**预估耗时：** 2-3 小时

#### E-1：SSO API 路由

- [ ] SUB-TASK-017: 修改 `lib/web_server.py`，新增 SSO API 路由
  - `GET /api/auth/sso/providers` — 返回可用 SSO 提供商列表
    - 如果 SSO 未启用 → 返回空列表
    - 如果 SSO 已启用 → 返回 [{name: "casdoor", display_name: "企业 SSO", login_url: "/api/auth/sso/login"}]
  - `GET /api/auth/sso/login` — 发起 SSO 登录
    - 调用 auth.sso_login()
    - 302 重定向到 Casdoor 授权 URL
    - 如果 SSO 未启用 → 返回 501
  - `GET /api/auth/sso/callback` — OAuth2 回调
    - 从 query 参数获取 code 和 state
    - 调用 auth.sso_callback(code, state)
    - 成功 → 设置会话 cookie → 302 重定向到首页
    - 失败 → 302 重定向到 /login.html?error=xxx
  - `POST /api/auth/sso/logout` — SSO 登出
    - 调用 auth.sso_logout(session_id)
    - 清除会话 cookie
    - 返回 {logout_url: "https://casdoor/..."} 供前端重定向
- [ ] SUB-TASK-018: 修改 `lib/web_server.py`，更新 PUBLIC_ENDPOINTS
  - 新增 `/api/auth/sso/providers`
  - 新增 `/api/auth/sso/callback`（回调不需要认证）

#### E-2：统一认证流程

- [ ] SUB-TASK-019: 修改 `lib/web_server.py`，重构 `_authenticate()` 方法
  - 步骤 1：PUBLIC_ENDPOINTS 检查（不变）
  - 步骤 2：Bearer Token 认证
    - 新增：JWT 格式 token → auth.validate_token() 自动走 SSO 验证
    - 保留：本地 API token → auth.validate_token() 原有逻辑
  - 步骤 3：Cookie Session 认证
    - 新增：检查 session_manager（Redis/内存）获取会话
    - 保留：兼容旧版文件会话 auth.is_logged_in()
  - 步骤 4：认证失败 → 401（不变）
  - 步骤 5：认证成功 → 设置 self.current_user_id, self.current_roles
- [ ] SUB-TASK-020: 修改 `lib/web_server.py`，认证后设置 DatabaseStorage 用户上下文
  - 在 `_authenticate()` 末尾新增：
    - 如果 storage mode == db 且认证成功 → storage.set_current_user(user_id, roles)
  - 确保 RLS 上下文在所有数据库操作前已设置
- [ ] SUB-TASK-021: 修改 `lib/web_server.py`，新增 SSO 配置 API
  - `GET /api/config/sso` — 返回 SSO 配置状态
    - {enabled, providers, login_url, casdoor_endpoint}
    - 仅 admin 可访问
  - 复用现有的 admin 权限检查逻辑

---

## 任务组 F：前端集成

**类型：** 串行
**前置条件：** 任务组 E 完成
**预估耗时：** 2-3 小时

#### F-1：auth.js SSO 支持

- [ ] SUB-TASK-022: 修改 `views/js/auth.js`，新增 SSO 方法
  - `async getSSOProviders()` — GET /api/auth/sso/providers，返回提供商列表
  - `ssoLogin(provider)` — window.location.href = '/api/auth/sso/login?provider=' + provider
  - `async handleSSOCallback()` — 解析 URL 中的 code 和 state
  - `isSSOEnabled()` — 检查 SSO 提供商是否可用

#### F-2：login.html SSO 登录

- [ ] SUB-TASK-023: 修改 `views/login.html`，新增 SSO 登录区域
  - 页面加载时调用 API.getSSOProviders()
  - 如果 SSO 启用：显示分隔线 "── 或使用企业账号 ──"
  - 显示 SSO 提供商按钮（蓝色背景，白色文字）
  - 点击按钮调用 API.ssoLogin(provider)
  - 保留原有用户名密码登录表单不变
  - 错误处理：URL 中有 error 参数时显示错误提示

#### F-3：SSO 回调页面

- [ ] SUB-TASK-024: 创建 `views/sso-callback.html`
  - 页面加载时解析 URL 中的 code 和 state
  - 显示 "正在登录..." 加载状态
  - 等待服务端回调处理（由 /api/auth/sso/callback 直接 302 重定向）
  - 实际上回调由服务端处理，此页面作为 fallback/错误页面
  - 如果从 /login.html?error=xxx 跳转 → 显示具体错误信息
  - "返回登录" 按钮 → /login.html

#### F-4：管理页面 SSO 配置

- [ ] SUB-TASK-025: 修改 `views/admin/` 相关页面，新增 SSO 状态展示
  - 在系统设置页新增 SSO 配置区域
  - 显示当前 SSO 状态（启用/禁用）
  - 显示已配置的 IdP 列表
  - 显示 Casdoor 管理入口链接

---

## 任务组 G：测试、文档与脚本

**类型：** 串行
**前置条件：** 任务组 E 完成（集成测试依赖 E）
**预估耗时：** 3-4 小时

#### G-1：集成测试

- [ ] SUB-TASK-026: 创建 `tests/e2e/test_sso_flow.py` — 完整 SSO 登录流程
  - Mock Casdoor 服务端响应
  - 测试 initiate_login → callback → 会话创建 完整流程
  - 测试 SSO 用户 RLS 上下文正确
  - 测试 SSO 用户创建原子和知识库
- [ ] SUB-TASK-027: 创建 `tests/e2e/test_sso_flow.py` — SSO + 本地登录并存
  - SSO 登录成功后本地登录仍可用
  - 本地 token 和 SSO JWT 共存
  - 切换用户时会话正确隔离
- [ ] SUB-TASK-028: 创建 `tests/e2e/test_sso_flow.py` — 单点登出
  - SSO 登出销毁本地会话
  - 返回 Casdoor 登出 URL
  - 登出后访问受保护端点返回 401
- [ ] SUB-TASK-029: 创建 `tests/e2e/test_sso_flow.py` — Casdoor 不可用降级
  - Mock Casdoor 返回连接超时
  - 前端显示降级提示
  - 本地登录仍可用
  - /api/auth/sso/providers 返回空列表

#### G-2：Casdoor 初始化脚本

- [ ] SUB-TASK-030: 创建 `scripts/init-casdoor.py`
  - 调用 Casdoor API 创建组织（llm-wiki）
  - 调用 Casdoor API 创建应用（llm-wiki-app，配置 redirect_uri）
  - 输出 client_id、client_secret
  - 输出 JWT 证书（certificate）
  - 输出需要配置到 .env 的环境变量模板
  - 支持命令行参数覆盖（--endpoint, --admin-username, --admin-password）

#### G-3：文档

- [ ] SUB-TASK-031: 更新 `Doc/plans/PLAN-000-enterprise-overall-plan.md`
  - 更新 2.1 状态为"代码已实现"
  - 更新完成度
  - 更新下一步行动
- [ ] SUB-TASK-032: 更新 `Doc/plans/PLAN-005-casdoor-sso-integration.md`
  - 状态改为 "completed"
- [ ] SUB-TASK-033: 创建 `docs/sso-integration-guide.md`
  - 快速开始（docker compose up + init-casdoor.py）
  - 环境变量配置说明
  - IdP 配置指南（企业微信/钉钉/飞书）
  - 故障排除（Casdoor 不可用、JWT 验证失败、角色映射错误）
  - 安全注意事项（CSRF state、JWT 证书轮换、密钥管理）
- [ ] SUB-TASK-034: 更新 `docs/README.md` 或项目根 README
  - 新增 SSO 功能说明
  - 新增 docker-compose SSO 部署方式

#### G-4：最终验证

- [ ] SUB-TASK-035: 运行完整验证流程
  - 运行 `pytest tests/auth/ -v` — 所有单元测试通过
  - 运行 `pytest tests/e2e/test_sso_flow.py -v` — 集成测试通过
  - 运行 `docker compose up` — Casdoor + llm-wiki 启动成功
  - 运行 `python scripts/init-casdoor.py` — Casdoor 初始化成功
  - 手动测试：SSO 登录 → 创建知识库 → 登出
  - 手动测试：SSO 关闭时本地登录正常
  - 检查测试覆盖率 ≥ 80%

---

## 依赖关系图

```
任务组 A（基础设施）
    │
    ├─────────────────────┐
    ↓                     ↓
任务组 B（认证核心）   任务组 C（会话+同步）  ← 并行
    │                     │
    └─────────┬───────────┘
              ↓
         任务组 D（AuthManager 集成）
              ↓
         任务组 E（API 路由）
              ↓
         任务组 F（前端集成）
              ↓
         任务组 G（测试+文档）
```

---

## 并行机会

| 并行组 | 任务组 | 条件 |
|--------|--------|------|
| 并行 1 | B + C | 任务组 A 完成后可同时开始 |

- B（CasdoorClient + SSOAuthProvider）和 C（RedisSessionManager + UserSyncService）互不依赖
- B 的 SSOAuthProvider 依赖 C 的 SessionManager 和 UserSyncService，但这些接口在 B 中通过依赖注入传入，B 可先编写完自身逻辑

---

## 风险缓解

| 风险 | 影响任务组 | 缓解策略 |
|------|-----------|----------|
| Casdoor API 变更 | B | Mock Casdoor 响应，锁定 API 版本 |
| Redis 不可用 | C, D | 降级到内存 SessionManager |
| web_server.py 大文件修改 | E | 小步提交，每次仅修改一个方法 |
| login.html 修改破坏现有 UI | F | 渐进式添加，SSO 区域独立于本地登录 |
| 测试环境无 Casdoor | G | 全部 Mock，init-casdoor.py 仅用于生产部署 |

---

**创建时间**：2026-06-23
**状态**：active — 等待执行
