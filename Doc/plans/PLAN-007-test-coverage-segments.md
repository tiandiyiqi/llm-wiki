# 任务组结构：PLAN-007 测试覆盖率提升

## 元信息

- 源计划：PLAN-007-test-coverage.md
- 创建时间：2026-06-23 14:30
- 任务组数量：9
- 子任务总数：42
- 预估总工时：12-18 天

## 任务组概览表

| 任务组 | 名称 | 类型 | 前置条件 | 子任务数 | 预估时间 |
|--------|------|------|----------|:--------:|----------|
| A | 测试基础设施修复 | 串行 | 无 | 4 | 2-3 天 |
| B | P0 核心 — web_server 测试 | 串行 | 任务组 A | 3 | 1-2 天 |
| C | P0 核心 — auth 模块补全 | 并行 | 任务组 A | 3 | 1-2 天 |
| D | P0 核心 — 工具类补全 | 并行 | 任务组 A | 1 | 0.5 天 |
| E | P1 — API 层测试 | 并行 | 任务组 B, C | 5 | 2-3 天 |
| F | P1 — 搜索 + 审计 + 迁移测试 | 并行 | 任务组 B, C | 6 | 2-3 天 |
| G | P2 — 辅助模块测试 | 并行 | 任务组 E, F | 12 | 2-3 天 |
| H | PWA/移动端 + CI 集成 | 并行 | 任务组 A | 4 | 1-2 天 |
| I | 验证与文档 | 串行 | 任务组 G, H | 4 | 1-2 天 |

---

## 执行顺序

### 任务组 A：测试基础设施修复

**类型：** 串行
**前置条件：** 无
**说明：** 修复已有测试问题，建立共享测试基础设施。所有后续任务组依赖此任务组完成。

#### 任务 A-1：修复 auth 模块 7 个测试的 numpy import 错误

- [ ] SUB-TASK-001: 修复 tests/auth/ 下 7 个测试文件的 numpy import 错误
  - 依赖：无
  - 文件：`tests/auth/test_casdoor_config.py`, `tests/auth/test_casdoor_client.py`, `tests/auth/test_redis_session.py`, `tests/auth/test_rls.py`, `tests/auth/test_sso_provider.py`, `tests/auth/test_user_sync.py`, `tests/auth/test_permissions.py`
  - 复杂度：中
  - 测试策略：测试后行（修复已有测试，验证通过即可）
  - 预估时间：30 分钟

#### 任务 A-2：配置覆盖率工具

- [ ] SUB-TASK-002: 在 pyproject.toml 中添加 coverage 配置
  - 依赖：无
  - 文件：`pyproject.toml`
  - 复杂度：低
  - 测试策略：测试后行（配置文件修改，验证 pytest --cov 可运行）
  - 预估时间：10 分钟

#### 任务 A-3：创建共享 conftest.py

- [ ] SUB-TASK-003: 创建 tests/conftest.py（通用 Mock fixtures、临时目录、测试数据工厂）
  - 依赖：SUB-TASK-002（coverage 配置需就位以验证 fixture 可用）
  - 文件：`tests/conftest.py`
  - 复杂度：中
  - 测试策略：测试后行（fixture 文件，验证 pytest 可发现并使用）
  - 预估时间：20 分钟

- [ ] SUB-TASK-004: 创建 tests/api/conftest.py（API 测试专用 fixtures）
  - 依赖：SUB-TASK-003（依赖根 conftest.py 中的基础 fixture）
  - 文件：`tests/api/conftest.py`
  - 复杂度：低
  - 测试策略：测试后行
  - 预估时间：10 分钟

- [ ] SUB-TASK-005: 创建 tests/web/conftest.py（Web 服务器测试专用 fixtures）
  - 依赖：SUB-TASK-003
  - 文件：`tests/web/conftest.py`
  - 复杂度：低
  - 测试策略：测试后行
  - 预估时间：10 分钟

#### 任务 A-4：重命名不一致的测试文件

- [ ] SUB-TASK-006: 重命名 test_*_independent.py 文件（移除 _independent 后缀）
  - 依赖：无（可与 A-1/A-2/A-3 并行，但同属基础设施修复，串行更安全）
  - 文件：`tests/test_error_handler_independent.py` -> `tests/test_error_handler.py`, `tests/test_input_validator_independent.py` -> `tests/test_input_validator.py`, `tests/test_query_optimizer_independent.py` -> `tests/test_query_optimizer.py`, `tests/test_rate_limiter_independent.py` -> `tests/test_rate_limiter.py`, `tests/test_rbac_independent.py` -> `tests/test_rbac.py`, `tests/test_sql_validator_independent.py` -> `tests/test_sql_validator.py`
  - 复杂度：低
  - 测试策略：测试后行（重命名后验证 pytest 仍可发现并运行）
  - 预估时间：10 分钟

- [ ] SUB-TASK-007: 重命名 test_*_standalone.py 文件（移除 _standalone 后缀）
  - 依赖：无
  - 文件：`tests/test_path_validator_standalone.py` -> `tests/test_path_validator.py`（注意：tests/unit/test_path_validator.py 已存在，需合并或区分）, `tests/test_sql_validator_standalone.py` -> `tests/test_sql_validator.py`（注意：与 SUB-TASK-006 重命名后的文件冲突，需合并）
  - 复杂度：中（存在文件名冲突，需合并测试内容）
  - 测试策略：测试后行
  - 预估时间：15 分钟

- [ ] SUB-TASK-008: 验证所有 835+ 测试通过（基础设施修复后全量回归）
  - 依赖：SUB-TASK-001, SUB-TASK-006, SUB-TASK-007
  - 文件：无新增
  - 复杂度：低
  - 测试策略：仅手动验证（运行 pytest 全量，确认 0 failures）
  - 预估时间：5 分钟

---

### 任务组 B：P0 核心 — web_server 测试

**类型：** 串行
**前置条件：** 任务组 A 完成
**说明：** web_server.py 是最复杂的模块（API 路由 + PWA + 移动端检测），需拆分为多个子任务逐步覆盖。

#### 任务 B-1：web_server 基础路由测试

- [ ] SUB-TASK-009: 编写 web_server API 路由分发测试（GET/POST/PUT/DELETE）
  - 依赖：任务组 A（conftest.py + coverage 配置）
  - 文件：创建 `tests/web/test_web_server.py`
  - 复杂度：高
  - 测试策略：TDD（核心业务逻辑 — API 路由分发是系统入口，安全敏感）
  - 预估时间：30 分钟

- [ ] SUB-TASK-010: 编写 web_server 静态文件服务测试（_serve_static / _serve_file）
  - 依赖：SUB-TASK-009（同一测试文件，追加测试用例）
  - 文件：`tests/web/test_web_server.py`
  - 复杂度：中
  - 测试策略：TDD（文件服务涉及路径遍历安全风险）
  - 预估时间：15 分钟

- [ ] SUB-TASK-011: 编写 web_server CORS + 认证 + 权限测试
  - 依赖：SUB-TASK-009
  - 文件：`tests/web/test_web_server.py`
  - 复杂度：高
  - 测试策略：TDD（安全/认证 — CORS + 认证中间件 + 权限检查）
  - 预估时间：25 分钟

- [ ] SUB-TASK-012: 编写 web_server PWA 路由测试（manifest.json / sw.js / icons）
  - 依赖：SUB-TASK-009
  - 文件：`tests/web/test_web_server.py`
  - 复杂度：中
  - 测试策略：TDD（API 契约 — PWA 路由的 Content-Type 和响应格式）
  - 预估时间：15 分钟

- [ ] SUB-TASK-013: 编写 web_server 移动端检测 + API 精简测试
  - 依赖：SUB-TASK-009
  - 文件：`tests/web/test_web_server.py`
  - 复杂度：中
  - 测试策略：TDD（数据处理/转换 — _is_mobile_request 检测 + 精简数据字段）
  - 预估时间：20 分钟

- [ ] SUB-TASK-014: 编写 web_server 错误处理测试（404/401/403/500）
  - 依赖：SUB-TASK-009
  - 文件：`tests/web/test_web_server.py`
  - 复杂度：中
  - 测试策略：TDD（API 契约 — 错误响应格式验证）
  - 预估时间：15 分钟

---

### 任务组 C：P0 核心 — auth 模块补全

**类型：** 并行
**前置条件：** 任务组 A 完成
**说明：** auth 模块的三个新测试文件互不依赖，可并行编写。与任务组 B 也可并行（不同目录，不同源文件）。

#### 任务 C-1：auth_middleware 测试

- [ ] SUB-TASK-015: 编写 auth_middleware 测试（Token 验证、会话过期、无效 Token、权限装饰器）
  - 依赖：任务组 A（conftest.py 中的 Mock fixtures）
  - 文件：创建 `tests/auth/test_auth_middleware.py`
  - 复杂度：高
  - 测试策略：TDD（安全/认证 — Token 验证 + 权限装饰器是安全关键路径）
  - 预估时间：25 分钟

#### 任务 C-2：session_manager 测试

- [ ] SUB-TASK-016: 编写 session_manager 测试（会话 CRUD、过期清理、Redis 降级）
  - 依赖：任务组 A
  - 文件：创建 `tests/auth/test_session_manager.py`
  - 复杂度：中
  - 测试策略：TDD（安全/认证 — 会话管理是认证核心组件）
  - 预估时间：20 分钟

#### 任务 C-3：rbac_model 测试

- [ ] SUB-TASK-017: 编写 rbac_model 测试（角色权限矩阵、权限继承关系）
  - 依赖：任务组 A
  - 文件：创建 `tests/auth/test_rbac_model.py`
  - 复杂度：中
  - 测试策略：TDD（安全/认证 — RBAC 权限模型是授权核心）
  - 预估时间：15 分钟

---

### 任务组 D：P0 核心 — 工具类补全

**类型：** 并行
**前置条件：** 任务组 A 完成
**说明：** 与任务组 B、C 并行执行。log_sanitizer 是安全敏感工具。

#### 任务 D-1：log_sanitizer 测试

- [ ] SUB-TASK-018: 编写 log_sanitizer 测试（敏感信息脱敏、正常日志不修改、边界情况）
  - 依赖：任务组 A
  - 文件：创建 `tests/utils/test_log_sanitizer.py`
  - 复杂度：中
  - 测试策略：TDD（安全/认证 — 日志脱敏防止敏感信息泄露）
  - 预估时间：15 分钟

---

### 任务组 E：P1 — API 层测试

**类型：** 并行
**前置条件：** 任务组 B、C 完成（API 测试依赖 web_server 和 auth 模块的 Mock 模式已建立）
**说明：** 5 个 API 测试文件互不依赖，可完全并行。每个 API 测试涉及独立的源文件。

#### 任务 E-1：kb_management API 测试

- [ ] SUB-TASK-019: 编写 kb_management API 测试（知识库 CRUD、权限检查、输入验证）
  - 依赖：任务组 B（web_server Mock 模式）, 任务组 C（auth Mock 模式）
  - 文件：创建 `tests/api/test_kb_management_api.py`
  - 复杂度：中
  - 测试策略：TDD（API 契约 — API 层测试）
  - 预估时间：20 分钟

#### 任务 E-2：member API 测试

- [ ] SUB-TASK-020: 编写 member API 测试（成员邀请/移除/角色变更、权限边界）
  - 依赖：任务组 B, C
  - 文件：创建 `tests/api/test_member_api.py`
  - 复杂度：中
  - 测试策略：TDD（API 契约 + 安全/认证 — 权限边界测试）
  - 预估时间：20 分钟

#### 任务 E-3：ocr API 测试

- [ ] SUB-TASK-021: 编写 ocr API 测试（OCR 任务提交/状态查询/结果获取、文件上传验证）
  - 依赖：任务组 B, C
  - 文件：创建 `tests/api/test_ocr_api.py`
  - 复杂度：中
  - 测试策略：TDD（API 契约 — API 层测试）
  - 预估时间：15 分钟

#### 任务 E-4：permission API 测试

- [ ] SUB-TASK-022: 编写 permission API 测试（权限分配/撤销、批量操作）
  - 依赖：任务组 B, C
  - 文件：创建 `tests/api/test_permission_api.py`
  - 复杂度：中
  - 测试策略：TDD（安全/认证 + API 契约 — 权限操作 API）
  - 预估时间：15 分钟

#### 任务 E-5：preview API 测试

- [ ] SUB-TASK-023: 编写 preview API 测试（预览请求/缓存命中/格式转换）
  - 依赖：任务组 B, C
  - 文件：创建 `tests/api/test_preview_api.py`
  - 复杂度：低
  - 测试策略：TDD（API 契约 — API 层测试）
  - 预估时间：10 分钟

---

### 任务组 F：P1 — 搜索 + 审计 + 迁移测试

**类型：** 并行
**前置条件：** 任务组 B、C 完成（与任务组 E 同级，可并行）
**说明：** 搜索、审计、迁移三个子模块互不依赖，可并行。每个子模块内的测试文件也互不依赖。

#### 任务 F-1：搜索引擎测试

- [ ] SUB-TASK-024: 编写 search/engine 测试（搜索引擎初始化和查询、结果排序/过滤）
  - 依赖：任务组 B, C
  - 文件：创建 `tests/search/test_engine.py`
  - 复杂度：中
  - 测试策略：TDD（核心业务逻辑 — 搜索引擎是核心功能）
  - 预估时间：20 分钟

#### 任务 F-2：混合搜索测试

- [ ] SUB-TASK-025: 编写 search/hybrid_search 测试（混合搜索策略选择、向量 + 关键词融合）
  - 依赖：任务组 B, C
  - 文件：创建 `tests/search/test_hybrid_search.py`
  - 复杂度：中
  - 测试策略：TDD（核心业务逻辑 — 搜索策略是数据处理/转换）
  - 预估时间：15 分钟

#### 任务 F-3：PostgreSQL 搜索测试

- [ ] SUB-TASK-026: 编写 search/postgres_search 测试（PostgreSQL 全文搜索、tsquery 构建）
  - 依赖：任务组 B, C
  - 文件：创建 `tests/search/test_postgres_search.py`
  - 复杂度：中
  - 测试策略：TDD（核心业务逻辑 — 数据库查询构建）
  - 预估时间：15 分钟

#### 任务 F-4：审计日志测试

- [ ] SUB-TASK-027: 编写 audit_logger 测试（审计日志记录、日志格式验证、敏感操作追踪）
  - 依赖：任务组 B, C
  - 文件：创建 `tests/audit/test_audit_logger.py`
  - 复杂度：中
  - 测试策略：TDD（安全/认证 — 审计日志是安全合规关键）
  - 预估时间：15 分钟

#### 任务 F-5：数据迁移测试

- [ ] SUB-TASK-028: 编写 migration/migrate 测试（数据迁移执行、回滚机制、迁移验证）
  - 依赖：任务组 B, C
  - 文件：创建 `tests/migration/test_migrate.py`
  - 复杂度：高
  - 测试策略：TDD（核心业务逻辑 + 复杂度高 — 数据迁移涉及数据完整性）
  - 预估时间：25 分钟

#### 任务 F-6：迁移验证器测试

- [ ] SUB-TASK-029: 编写 migration/validators 测试（迁移数据验证、Schema 兼容性检查）
  - 依赖：任务组 B, C
  - 文件：创建 `tests/migration/test_validators.py`
  - 复杂度：中
  - 测试策略：TDD（数据处理/转换 — 验证逻辑是数据校验关键）
  - 预估时间：15 分钟

---

### 任务组 G：P2 — 辅助模块测试

**类型：** 并行
**前置条件：** 任务组 E、F 完成（辅助模块测试可复用 API/搜索测试中建立的 Mock 模式）
**说明：** 12 个辅助模块测试互不依赖，可完全并行。按价值分为两批，但实际执行时全部并行。

#### 任务 G-1：高价值辅助模块（5 个）

- [ ] SUB-TASK-030: 编写 yaml_parser 测试（YAML 解析/序列化）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_yaml_parser.py`
  - 复杂度：低
  - 测试策略：测试后行（解析工具，低复杂度，无安全敏感逻辑）
  - 预估时间：10 分钟

- [ ] SUB-TASK-031: 编写 multi_format_parser 测试（多格式解析）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_multi_format_parser.py`
  - 复杂度：中
  - 测试策略：测试后行（解析工具，中等复杂度）
  - 预估时间：15 分钟

- [ ] SUB-TASK-032: 编写 lifecycle 测试（原子生命周期管理）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_lifecycle.py`
  - 复杂度：中
  - 测试策略：TDD（核心业务逻辑 — 生命周期管理涉及数据完整性）
  - 预估时间：15 分钟

- [ ] SUB-TASK-033: 编写 batch_ops 测试（批量操作）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_batch_ops.py`
  - 复杂度：中
  - 测试策略：测试后行（批量操作工具，中等复杂度）
  - 预估时间：10 分钟

- [ ] SUB-TASK-034: 编写 backup 测试（备份/恢复）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_backup.py`
  - 复杂度：中
  - 测试策略：TDD（核心业务逻辑 — 备份恢复涉及数据安全）
  - 预估时间：15 分钟

#### 任务 G-2：其余辅助模块（7 个）

- [ ] SUB-TASK-035: 编写 fts_index 测试（全文索引）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_fts_index.py`
  - 复杂度：低
  - 测试策略：测试后行
  - 预估时间：10 分钟

- [ ] SUB-TASK-036: 编写 indexer 测试（索引构建）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_indexer.py`
  - 复杂度：低
  - 测试策略：测试后行
  - 预估时间：10 分钟

- [ ] SUB-TASK-037: 编写 querier 测试（查询处理）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_querier.py`
  - 复杂度：低
  - 测试策略：测试后行
  - 预估时间：10 分钟

- [ ] SUB-TASK-038: 编写 cache 测试（缓存管理）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_cache.py`
  - 复杂度：低
  - 测试策略：测试后行
  - 预估时间：10 分钟

- [ ] SUB-TASK-039: 编写 exporter 测试（数据导出）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_exporter.py`
  - 复杂度：低
  - 测试策略：测试后行
  - 预估时间：10 分钟

- [ ] SUB-TASK-040: 编写 feedback 测试（反馈系统）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_feedback.py`
  - 复杂度：低
  - 测试策略：测试后行
  - 预估时间：10 分钟

- [ ] SUB-TASK-041: 编写 timeline 测试（时间线生成）
  - 依赖：任务组 E, F
  - 文件：创建 `tests/test_timeline.py`
  - 复杂度：低
  - 测试策略：测试后行
  - 预估时间：10 分钟

---

### 任务组 H：PWA/移动端 + CI 集成

**类型：** 并行
**前置条件：** 任务组 A 完成（仅需基础设施，不依赖 P0/P1 测试产出）
**说明：** PWA/移动端测试与 P0/P1 测试可并行。CI 配置独立于测试编写。此任务组与任务组 B/C/D 并行执行。

#### 任务 H-1：Service Worker 策略测试

- [ ] SUB-TASK-042: 编写 SW 缓存策略测试（Network First/Cache First/Network Only、缓存版本升级、离线回退）
  - 依赖：任务组 A
  - 文件：创建 `tests/pwa/test_sw_strategy.py`
  - 复杂度：中
  - 测试策略：TDD（核心业务逻辑 — SW 缓存策略影响离线体验和数据一致性）
  - 预估时间：20 分钟

#### 任务 H-2：PWA manifest 测试

- [ ] SUB-TASK-043: 编写 manifest 测试（格式验证、图标存在性、必填字段）
  - 依赖：任务组 A
  - 文件：创建 `tests/pwa/test_manifest.py`
  - 复杂度：低
  - 测试策略：测试后行（配置验证，低复杂度）
  - 预估时间：10 分钟

#### 任务 H-3：移动端 API 测试

- [ ] SUB-TASK-044: 编写移动端 API 测试（_is_mobile_request 各种 User-Agent、精简数据字段验证、描述截断）
  - 依赖：任务组 A
  - 文件：创建 `tests/mobile/test_mobile_api.py`
  - 复杂度：中
  - 测试策略：TDD（数据处理/转换 — 移动端检测 + 数据精简逻辑）
  - 预估时间：15 分钟

#### 任务 H-4：CI 配置

- [ ] SUB-TASK-045: 创建 GitHub Actions test.yml 工作流
  - 依赖：任务组 A（coverage 配置需就位）
  - 文件：创建 `.github/workflows/test.yml`
  - 复杂度：低
  - 测试策略：仅手动验证（CI 配置文件，需推送后验证 Actions 运行）
  - 预估时间：10 分钟

---

### 任务组 I：验证与文档

**类型：** 串行
**前置条件：** 任务组 G、H 完成（所有测试已编写完成）
**说明：** 最终验证阶段，确认覆盖率达标、测试质量合格、文档更新。

#### 任务 I-1：覆盖率验证

- [ ] SUB-TASK-046: 运行全量覆盖率报告，确认各模块覆盖率达标
  - 依赖：任务组 G, H
  - 文件：无新增
  - 复杂度：低
  - 测试策略：仅手动验证（运行 pytest --cov，检查报告）
  - 预估时间：10 分钟

- [ ] SUB-TASK-047: 对未达标模块补充测试（如有）
  - 依赖：SUB-TASK-046
  - 文件：视覆盖率报告而定
  - 复杂度：中（取决于缺口大小）
  - 测试策略：测试后行
  - 预估时间：30 分钟（预留缓冲）

#### 任务 I-2：测试质量审查

- [ ] SUB-TASK-048: 测试质量审查（隔离性、Mock 泄漏、flaky tests — 连续运行 3 次验证一致性）
  - 依赖：SUB-TASK-046
  - 文件：无新增
  - 复杂度：中
  - 测试策略：仅手动验证
  - 预估时间：15 分钟

#### 任务 I-3：文档更新

- [ ] SUB-TASK-049: 更新 PLAN-000 测试状态
  - 依赖：SUB-TASK-046
  - 文件：`Doc/plans/PLAN-000-enterprise-overall-plan.md`
  - 复杂度：低
  - 测试策略：仅手动验证（文档更新）
  - 预估时间：5 分钟

- [ ] SUB-TASK-050: 创建 tests/README.md 测试指南
  - 依赖：SUB-TASK-046
  - 文件：创建 `tests/README.md`
  - 复杂度：低
  - 测试策略：仅手动验证（文档）
  - 预估时间：10 分钟

- [ ] SUB-TASK-051: 更新 README.md 添加测试运行说明
  - 依赖：SUB-TASK-046
  - 文件：`README.md`
  - 复杂度：低
  - 测试策略：仅手动验证（文档）
  - 预估时间：5 分钟

---

## 依赖关系详解

### 资源冲突分析

| 冲突类型 | 涉及任务组 | 冲突文件 | 处理方式 |
|----------|-----------|----------|----------|
| 同目录操作 | A-1 (auth 修复) vs C (auth 新测试) | `tests/auth/` | A-1 先完成，C 再开始 |
| 同文件追加 | B-1 内部子任务 | `tests/web/test_web_server.py` | 串行追加测试用例 |
| 重命名冲突 | A-4 (standalone 重命名) | `tests/test_sql_validator.py` | 合并测试内容到同一文件 |
| conftest 依赖 | A-3 vs B/C/D/E/F | `tests/conftest.py` | A-3 先完成 |

### 并行机会分析

| 并行组 | 可并行的任务组 | 原因 |
|--------|--------------|------|
| 第 1 波 | A（串行内部） | 基础设施修复，必须先完成 |
| 第 2 波 | B + C + D + H | 不同目录、不同源文件、无资源冲突 |
| 第 3 波 | E + F | 依赖 B/C 的 Mock 模式，E 和 F 之间无依赖 |
| 第 4 波 | G | 依赖 E/F 的 Mock 模式 |
| 第 5 波 | I（串行内部） | 最终验证，依赖所有前置任务组 |

### 测试策略统计

| 测试策略 | 子任务数 | 占比 |
|----------|:--------:|:----:|
| TDD | 22 | 43% |
| 测试后行 | 20 | 39% |
| 仅手动验证 | 9 | 18% |

TDD 信号命中分布：
- 安全/认证：8 个（auth_middleware, session_manager, rbac_model, log_sanitizer, member_api, permission_api, audit_logger, backup）
- API 契约：7 个（web_server 路由/PWA/错误处理, kb_management_api, ocr_api, preview_api, permission_api）
- 核心业务逻辑：5 个（engine, hybrid_search, migrate, lifecycle, sw_strategy）
- 数据处理/转换：2 个（mobile_api, web_server 移动端检测）
- 复杂度高：0 个（已由上述信号覆盖）

---

## 执行顺序可视化

```
执行顺序：

1  任务组 A（测试基础设施修复）— 串行
   ├─ A-1：修复 auth 模块 7 个测试
   ├─ A-2：配置覆盖率工具
   ├─ A-3：创建共享 conftest.py（3 个文件）
   ├─ A-4：重命名不一致测试文件
   └─ A-8：全量回归验证
       |
       +---+---+---+
       |   |   |   |
       v   v   v   v
2  [并行] 任务组 B + C + D + H
   |
   |  B（P0 web_server）— 串行内部
   |  ├─ B-1：API 路由分发
   |  ├─ B-2：静态文件服务
   |  ├─ B-3：CORS + 认证 + 权限
   |  ├─ B-4：PWA 路由
   |  ├─ B-5：移动端检测 + API 精简
   |  └─ B-6：错误处理
   |
   |  C（P0 auth 补全）— 并行
   |  ├─ C-1：auth_middleware
   |  ├─ C-2：session_manager
   |  └─ C-3：rbac_model
   |
   |  D（P0 工具类）— 并行
   |  └─ D-1：log_sanitizer
   |
   |  H（PWA/移动端 + CI）— 并行
   |  ├─ H-1：SW 缓存策略
   |  ├─ H-2：manifest 测试
   |  ├─ H-3：移动端 API 测试
   |  └─ H-4：CI 配置
       |
       v
3  [并行] 任务组 E + F
   |
   |  E（P1 API 层）— 并行
   |  ├─ E-1：kb_management_api
   |  ├─ E-2：member_api
   |  ├─ E-3：ocr_api
   |  ├─ E-4：permission_api
   |  └─ E-5：preview_api
   |
   |  F（P1 搜索 + 审计 + 迁移）— 并行
   |  ├─ F-1：search/engine
   |  ├─ F-2：search/hybrid_search
   |  ├─ F-3：search/postgres_search
   |  ├─ F-4：audit_logger
   |  ├─ F-5：migration/migrate
   |  └─ F-6：migration/validators
       |
       v
4  任务组 G（P2 辅助模块）— 并行
   ├─ G-1a：yaml_parser
   ├─ G-1b：multi_format_parser
   ├─ G-1c：lifecycle
   ├─ G-1d：batch_ops
   ├─ G-1e：backup
   ├─ G-2a：fts_index
   ├─ G-2b：indexer
   ├─ G-2c：querier
   ├─ G-2d：cache
   ├─ G-2e：exporter
   ├─ G-2f：feedback
   └─ G-2g：timeline
       |
       v
5  任务组 I（验证与文档）— 串行
   ├─ I-1：覆盖率验证 + 补充
   ├─ I-2：测试质量审查
   └─ I-3：文档更新（3 个文件）
```

---

## 关键路径

```
A → B → E → G → I
```

关键路径耗时：2-3 天 + 1-2 天 + 2-3 天 + 2-3 天 + 1-2 天 = **8-13 天**

非关键路径（可与关键路径并行）：
- C + D：与 B 并行，1-2 天（不增加总耗时）
- H：与 B/C/D 并行，1-2 天（不增加总耗时）
- F：与 E 并行，2-3 天（不增加总耗时）

理论最短工期：**8-13 天**（关键路径决定）

---

## 风险与缓解

| 风险 | 影响任务组 | 缓解措施 |
|------|-----------|----------|
| web_server.py Mock 困难 | B | 拆分为 6 个子任务，逐步覆盖；使用 TestClient 模式 |
| auth 测试修复比预期困难 | A-1, C | 重写而非修复，保持测试意图不变 |
| 重命名文件冲突（standalone vs independent） | A-4 | 合并测试内容到同一文件，避免覆盖 |
| 辅助模块源代码质量低，难以测试 | G | 优先覆盖公共 API，内部实现可标记 pragma: no cover |
| CI 环境与本地不一致 | H-4 | 使用 Docker 统一环境；CI 配置中指定 Python 版本 |
| 覆盖率未达标需补充测试 | I-1 | 预留 30 分钟缓冲时间 |
