---
name: PLAN-007-test-coverage
description: 测试覆盖率提升计划 — 覆盖所有 PLAN（001-006）的自动化测试补全
priority: P1
status: segments-generated
created: 2026-06-23
updated: 2026-06-23
---

# PLAN-007 - 测试覆盖率提升计划

> **所属项目**：PLAN-000 企业化改造
> **阶段**：跨阶段（质量保障）
> **当前完成度**：0%
> **预估周期**：2-3 周
> **前置依赖**：PLAN-001~006 代码已实现

---

## 一、需求重述

### 1.1 核心需求

为 llm-wiki 项目建立全面的自动化测试体系，补全现有所有 PLAN（001-006）的测试覆盖，确保核心代码的可靠性和可维护性。

### 1.2 覆盖率目标

| 模块 | 目标覆盖率 | 说明 |
|------|:----------:|------|
| 核心代码（auth/storage/web_server） | **100%** | 安全敏感 + 数据关键路径 |
| PWA/API 逻辑 | **100%** | Service Worker 策略 + API 路由 |
| 工具类（utils/） | **≥ 90%** | 输入验证/路径验证/SQL 验证 |
| 业务逻辑（search/media/ocr） | **≥ 80%** | 搜索引擎/图片处理/OCR |
| 辅助模块（backup/export/lifecycle） | **≥ 60%** | 非关键路径 |
| **整体** | **≥ 80%** | 项目级最低标准 |

### 1.3 约束条件

| 约束项 | 要求 |
|--------|------|
| 不修改源代码 | 仅添加测试，不修改 lib/ 下的业务代码（修复 bug 除外） |
| 测试隔离 | 每个测试独立运行，无共享状态依赖 |
| Mock 外部依赖 | 不依赖真实 PostgreSQL/Redis/Casdoor 服务 |
| 快速执行 | 全量测试 ≤ 5 分钟完成 |
| CI 就绪 | 测试可在 CI 环境中自动运行 |

---

## 二、现状分析

### 2.1 当前测试状态

| 指标 | 值 |
|------|-----|
| 总源文件 | 89 个 |
| 有测试覆盖 | 47 个 |
| 缺少测试 | 42 个 |
| 估算覆盖率 | 52.8% |
| 现有测试用例 | 835 个 |
| 损坏的测试 | 7 个（auth 模块 numpy import 错误） |

### 2.2 已有测试分布

| 目录 | 测试文件数 | 覆盖的 PLAN |
|------|:----------:|:-----------:|
| `tests/core/` | 5 | PLAN-001（PostgreSQL 迁移） |
| `tests/auth/` | 7（有错误） | PLAN-005（SSO 集成） |
| `tests/search/` | 7 | PLAN-003（搜索引擎） |
| `tests/media/` | 4 | PLAN-004（媒体处理） |
| `tests/ocr/` | 5 | PLAN-004（OCR） |
| `tests/preview/` | 2 | PLAN-004（预览） |
| `tests/e2e/` | 4 | PLAN-001/002/005 |
| `tests/`（根级） | 9 | 安全/验证相关 |
| `tests/benchmarks/` | 1 | 性能基准 |
| `tests/unit/` | 1 | 路径验证 |

### 2.3 缺少测试的文件（42 个）

按优先级分组：

**P0 — 安全/认证/核心（必须 100%）：**
- `lib/web_server.py` — 主服务器，API 路由 + PWA 路由 + 移动端检测
- `lib/auth.py` — 认证入口
- `lib/api_server.py` — API 服务器
- `lib/auth/auth_middleware.py` — 认证中间件
- `lib/auth/permission_middleware.py` — 权限中间件
- `lib/auth/session_manager.py` — 会话管理
- `lib/utils/log_sanitizer.py` — 日志脱敏
- `lib/auth/rbac_model.py` — RBAC 模型

**P1 — API 层 + 业务逻辑（目标 ≥ 80%）：**
- `lib/api/kb_management.py` — 知识库管理 API
- `lib/api/member_api.py` — 成员管理 API
- `lib/api/ocr_api.py` — OCR API
- `lib/api/permission_api.py` — 权限 API
- `lib/api/preview_api.py` — 预览 API
- `lib/search/engine.py` — 搜索引擎
- `lib/search/hybrid_search.py` — 混合搜索
- `lib/search/postgres_search.py` — PostgreSQL 搜索
- `lib/audit/audit_logger.py` — 审计日志
- `lib/audit.py` — 审计入口
- `lib/migration/migrate.py` — 数据迁移
- `lib/migration/validators.py` — 迁移验证

**P2 — 辅助/工具模块（目标 ≥ 60%）：**
- `lib/ai_helper.py` — AI 辅助
- `lib/analytics.py` — 分析统计
- `lib/backup.py` — 备份
- `lib/batch_ops.py` — 批量操作
- `lib/cache.py` — 缓存
- `lib/cli_commands.py` — CLI 命令
- `lib/discovery.py` — 发现
- `lib/exporter.py` — 导出
- `lib/feedback.py` — 反馈
- `lib/fts_index.py` — 全文索引
- `lib/importer.py` — 导入
- `lib/indexer.py` — 索引器
- `lib/ingestor.py` — 摄取
- `lib/initializer.py` — 初始化
- `lib/lifecycle.py` — 生命周期
- `lib/logging_config.py` — 日志配置
- `lib/multi_format_parser.py` — 多格式解析
- `lib/querier.py` — 查询器
- `lib/quick_capture.py` — 快速捕获
- `lib/registry.py` — 注册表
- `lib/semantic.py` — 语义
- `lib/timeline.py` — 时间线
- `lib/visualizer.py` — 可视化
- `lib/watcher.py` — 监视器
- `lib/web_data.py` — Web 数据
- `lib/web_ui.py` — Web UI
- `lib/workflow.py` — 工作流
- `lib/yaml_parser.py` — YAML 解析
- `lib/constants.py` — 常量

### 2.4 已有测试的问题

1. **auth 模块 7 个测试 import 错误**：numpy 兼容性问题导致无法运行
2. **缺少 conftest.py**：大部分测试目录缺少共享 fixture
3. **测试命名不一致**：`test_*_independent.py`、`test_*_standalone.py` 命名混乱
4. **缺少覆盖率配置**：没有 `.coveragerc` 或 `pyproject.toml` 中的 coverage 配置

---

## 三、实施阶段

### Phase 1：测试基础设施修复（2-3 天）

**目标**：修复已有测试问题，建立测试基础设施

#### 步骤 1.1：修复 auth 模块测试

- **修改文件**：`tests/auth/test_*.py`（7 个文件）
- **修改点**：
  1. 修复 numpy import 错误（可能是 numpy 2.x 兼容问题）
  2. 确保所有 835 个测试可正常运行

#### 步骤 1.2：配置覆盖率工具

- **修改文件**：`pyproject.toml`
- **新增**：
  ```toml
  [tool.coverage.run]
  source = ["lib"]
  omit = ["lib/__init__.py", "lib/db/*"]
  
  [tool.coverage.report]
  fail_under = 80
  show_missing = true
  exclude_lines = [
      "pragma: no cover",
      "if __name__ == .__main__.:",
      "pass",
  ]
  ```

#### 步骤 1.3：创建共享 conftest.py

- **创建文件**：`tests/conftest.py`
- **内容**：
  1. 通用 Mock fixtures（HTTP 请求、数据库连接、Redis）
  2. 临时目录 fixture
  3. 测试数据工厂 fixtures
- **创建文件**：`tests/api/conftest.py`、`tests/web/conftest.py`

#### 步骤 1.4：重命名不一致的测试文件

- `test_*_independent.py` → `test_*.py`（移除 `_independent` 后缀）
- `test_*_standalone.py` → `test_*.py`（移除 `_standalone` 后缀）
- 更新 `pytest.ini` 确保发现规则正确

---

### Phase 2：P0 核心模块测试补全（3-5 天）

**目标**：安全/认证/核心模块达到 100% 覆盖率

#### 步骤 2.1：web_server.py 测试

- **创建文件**：`tests/web/test_web_server.py`
- **测试内容**：
  1. API 路由分发（GET/POST/PUT/DELETE）
  2. 静态文件服务（_serve_static / _serve_file）
  3. CORS 头部处理
  4. 认证中间件（_authenticate）
  5. 权限检查（_check_permission）
  6. **PWA 路由**：manifest.json（Content-Type: application/manifest+json）、sw.js、icons
  7. **移动端检测**：_is_mobile_request（User-Agent / Sec-CH-UA-Mobile）
  8. **移动端 API 精简**：_api_atom_list 的 is_mobile 分支
  9. 错误处理（404、401、403、500）

#### 步骤 2.2：auth 模块补全

- **创建文件**：`tests/auth/test_auth_middleware.py`
- **测试内容**：
  1. Token 验证流程
  2. 会话过期处理
  3. 无效 Token 处理
  4. 权限装饰器（@require_admin, @require_editor）

- **创建文件**：`tests/auth/test_session_manager.py`
- **测试内容**：
  1. 会话创建/读取/删除
  2. 会话过期清理
  3. Redis 连接失败降级

- **创建文件**：`tests/auth/test_rbac_model.py`
- **测试内容**：
  1. 角色权限矩阵验证
  2. 权限继承关系

#### 步骤 2.3：工具类补全

- **创建文件**：`tests/utils/test_log_sanitizer.py`
- **测试内容**：
  1. 敏感信息脱敏（密码、Token、API Key）
  2. 正常日志不修改
  3. 边界情况（空字符串、None、特殊字符）

---

### Phase 3：P1 API 层 + 业务逻辑测试（3-5 天）

**目标**：API 层和业务逻辑达到 ≥ 80% 覆盖率

#### 步骤 3.1：API 模块测试

- **创建文件**：`tests/api/test_kb_management_api.py`
  - 知识库 CRUD 操作
  - 权限检查
  - 输入验证

- **创建文件**：`tests/api/test_member_api.py`
  - 成员邀请/移除/角色变更
  - 权限边界

- **创建文件**：`tests/api/test_ocr_api.py`
  - OCR 任务提交/状态查询/结果获取
  - 文件上传验证

- **创建文件**：`tests/api/test_permission_api.py`
  - 权限分配/撤销
  - 批量操作

- **创建文件**：`tests/api/test_preview_api.py`
  - 预览请求/缓存命中/格式转换

#### 步骤 3.2：搜索模块补全

- **创建文件**：`tests/search/test_engine.py`
  - 搜索引擎初始化和查询
  - 结果排序/过滤

- **创建文件**：`tests/search/test_hybrid_search.py`
  - 混合搜索策略选择
  - 向量 + 关键词融合

- **创建文件**：`tests/search/test_postgres_search.py`
  - PostgreSQL 全文搜索
  - tsquery 构建

#### 步骤 3.3：审计 + 迁移模块

- **创建文件**：`tests/audit/test_audit_logger.py`
  - 审计日志记录
  - 日志格式验证
  - 敏感操作追踪

- **创建文件**：`tests/migration/test_migrate.py`
  - 数据迁移执行
  - 回滚机制
  - 迁移验证

- **创建文件**：`tests/migration/test_validators.py`
  - 迁移数据验证
  - Schema 兼容性检查

---

### Phase 4：P2 辅助模块测试补全（2-3 天）

**目标**：辅助模块达到 ≥ 60% 覆盖率

#### 步骤 4.1：高价值辅助模块

- `tests/test_yaml_parser.py` — YAML 解析/序列化
- `tests/test_multi_format_parser.py` — 多格式解析
- `tests/test_lifecycle.py` — 原子生命周期管理
- `tests/test_batch_ops.py` — 批量操作
- `tests/test_backup.py` — 备份/恢复

#### 步骤 4.2：其余辅助模块

- `tests/test_fts_index.py` — 全文索引
- `tests/test_indexer.py` — 索引构建
- `tests/test_querier.py` — 查询处理
- `tests/test_cache.py` — 缓存管理
- `tests/test_exporter.py` — 数据导出
- `tests/test_feedback.py` — 反馈系统
- `tests/test_timeline.py` — 时间线生成

---

### Phase 5：PWA/前端测试 + CI 集成（2-3 天）

**目标**：PWA 逻辑测试 + CI 自动化

#### 步骤 5.1：PWA 逻辑测试

- **创建文件**：`tests/pwa/test_sw_strategy.py`
- **测试内容**：
  1. Network First 策略（在线/离线/超时）
  2. Cache First 策略（缓存命中/未命中）
  3. Network Only 策略
  4. 缓存版本升级（旧缓存清理）
  5. 离线回退页面

- **创建文件**：`tests/pwa/test_manifest.py`
- **测试内容**：
  1. manifest.json 格式验证
  2. 图标文件存在性
  3. 必填字段完整性

#### 步骤 5.2：移动端 API 测试

- **创建文件**：`tests/mobile/test_mobile_api.py`
- **测试内容**：
  1. _is_mobile_request 检测（各种 User-Agent）
  2. 移动端精简数据字段验证
  3. 描述截断逻辑（≤ 80 字符）

#### 步骤 5.3：CI 配置

- **创建文件**：`.github/workflows/test.yml`
- **内容**：
  ```yaml
  name: Test Suite
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: '3.12'
        - run: pip install -e ".[dev]"
        - run: pytest --cov=lib --cov-report=xml --cov-report=term-missing
        - uses: codecov/codecov-action@v4
  ```

---

### Phase 6：验证与文档（1-2 天）

**目标**：验证覆盖率达标 + 文档更新

#### 步骤 6.1：覆盖率验证

- 运行全量覆盖率报告
- 确认各模块覆盖率达标
- 对未达标模块补充测试

#### 步骤 6.2：测试质量审查

- 检查测试隔离性
- 验证无 Mock 泄漏
- 确认无 flaky tests

#### 步骤 6.3：文档更新

- 更新 `Doc/plans/PLAN-000-enterprise-overall-plan.md` 测试状态
- 创建 `tests/README.md` 测试指南
- 更新 `README.md` 添加测试运行说明

---

## 四、依赖关系

```
Phase 1（基础设施修复）
  ├─→ Phase 2（P0 核心模块）
  │     └─→ Phase 3（P1 API + 业务逻辑）
  │           └─→ Phase 4（P2 辅助模块）
  ├─→ Phase 5（PWA/前端 + CI）← 与 Phase 3 并行
  └─→ Phase 6（验证 + 文档）
```

---

## 五、风险评估

| 风险 | 严重程度 | 概率 | 缓解措施 |
|------|:--------:|:----:|----------|
| web_server.py 复杂度高，Mock 困难 | 高 | 高 | 拆分为小测试，使用 TestClient 模式 |
| 外部依赖 Mock 不完整 | 中 | 中 | 创建统一的 Mock 工厂 fixtures |
| 已有 7 个 auth 测试修复困难 | 中 | 中 | 重写而非修复，保持测试意图不变 |
| 覆盖率 80% 对辅助模块过高 | 低 | 中 | 辅助模块目标降至 60% |
| CI 环境与本地不一致 | 低 | 低 | 使用 Docker 统一环境 |

---

## 六、文件变更清单

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `tests/conftest.py` | 通用共享 fixtures |
| `tests/api/conftest.py` | API 测试 fixtures |
| `tests/web/conftest.py` | Web 服务器测试 fixtures |
| `tests/web/test_web_server.py` | web_server.py 完整测试 |
| `tests/auth/test_auth_middleware.py` | 认证中间件测试 |
| `tests/auth/test_session_manager.py` | 会话管理测试 |
| `tests/auth/test_rbac_model.py` | RBAC 模型测试 |
| `tests/utils/test_log_sanitizer.py` | 日志脱敏测试 |
| `tests/api/test_kb_management_api.py` | 知识库管理 API 测试 |
| `tests/api/test_member_api.py` | 成员 API 测试 |
| `tests/api/test_ocr_api.py` | OCR API 测试 |
| `tests/api/test_permission_api.py` | 权限 API 测试 |
| `tests/api/test_preview_api.py` | 预览 API 测试 |
| `tests/search/test_engine.py` | 搜索引擎测试 |
| `tests/search/test_hybrid_search.py` | 混合搜索测试 |
| `tests/search/test_postgres_search.py` | PostgreSQL 搜索测试 |
| `tests/audit/test_audit_logger.py` | 审计日志测试 |
| `tests/migration/test_migrate.py` | 数据迁移测试 |
| `tests/migration/test_validators.py` | 迁移验证测试 |
| `tests/pwa/test_sw_strategy.py` | Service Worker 策略测试 |
| `tests/pwa/test_manifest.py` | PWA manifest 测试 |
| `tests/mobile/test_mobile_api.py` | 移动端 API 测试 |
| `tests/test_yaml_parser.py` | YAML 解析测试 |
| `tests/test_multi_format_parser.py` | 多格式解析测试 |
| `tests/test_lifecycle.py` | 生命周期测试 |
| `tests/test_batch_ops.py` | 批量操作测试 |
| `tests/test_backup.py` | 备份测试 |
| `tests/test_fts_index.py` | 全文索引测试 |
| `tests/test_indexer.py` | 索引器测试 |
| `tests/test_querier.py` | 查询器测试 |
| `tests/test_cache.py` | 缓存测试 |
| `tests/test_exporter.py` | 导出测试 |
| `tests/test_feedback.py` | 反馈测试 |
| `tests/test_timeline.py` | 时间线测试 |
| `.github/workflows/test.yml` | CI 测试工作流 |
| `tests/README.md` | 测试指南 |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `pyproject.toml` | 添加 coverage 配置 |
| `tests/auth/test_*.py` | 修复 7 个 import 错误 |
| `tests/test_*_independent.py` | 重命名（移除 `_independent` 后缀） |
| `tests/test_*_standalone.py` | 重命名（移除 `_standalone` 后缀） |
| `Doc/plans/PLAN-000-enterprise-overall-plan.md` | 更新测试状态 |

---

## 七、验收标准

1. ✅ 所有 835+ 测试通过（无 skip、无 error）
2. ✅ 整体代码覆盖率 ≥ 80%
3. ✅ 核心模块（auth/storage/web_server）覆盖率 100%
4. ✅ PWA/API 逻辑覆盖率 100%
5. ✅ 新增测试文件 ≥ 30 个
6. ✅ CI 工作流可正常运行
7. ✅ 全量测试执行时间 ≤ 5 分钟
8. ✅ 无 flaky tests（连续运行 3 次结果一致）

---

**计划创建时间**：2026-06-23
**计划状态**：draft — 等待审批
