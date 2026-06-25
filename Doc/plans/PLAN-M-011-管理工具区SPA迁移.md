# PLAN-M-011-管理工具区SPA迁移.md

---
plan_id: PLAN-M-011
type: master
status: completed
created: 2026-06-25
priority: high
parent: PLAN-010 (SPA 重构)
segments_file: PLAN-M-011-管理工具区SPA迁移-segments.md
segments_created: 2026-06-25
current_stage: 任务组拆分完成，等待执行确认
total_task_groups: 6
total_sub_tasks: 89
---

## 一、需求重述

**核心目标**：将管理工具区（除 AI 问答外）的 13 个占位视图模块从"迁移中提示"状态迁移为完整的功能模块，实现与旧版 `admin/*.html` 页面的功能对等。

**当前状态**：
- ✅ AI 问答（`qa.js`）：已迁移，208 行，有实际功能（但缺少历史加载和清空功能）
- ⏳ 13 个模块：均为 92 行占位符，只显示"此功能正在从独立页面迁移到 SPA 架构中。"

**目标状态**：
- 所有 14 个管理工具在 SPA 中提供与旧版独立页面功能对等的体验
- 左侧边栏始终可见，无需"返回首页"
- 剔除旧版页面的 header/sidebar/login（SPA 框架已提供）
- 统一使用 `WikiAPI` 对象（已内联在 index.html）调用后端 API

---

## 二、现状分析

### 2.1 已完成的 SPA 基础设施（PLAN-010）

| 组件 | 位置 | 状态 |
|------|------|------|
| 路由机制 | index.html 内嵌 `initRouter() + handleRoute() + loadViewModule()` | ✅ 已工作 |
| 双容器切换 | `inlineViews` vs `externalViewContainer` | ✅ 已工作 |
| 动态 ES6 import | `await import(/views/views/${viewName}.js)` | ✅ 已工作 |
| WikiAPI | index.html 内嵌 `WikiAPI` 对象（get/post/put/delete） | ✅ 已工作 |
| 认证检查 | `GET /api/auth/whoami` + 水印 | ✅ 已工作 |
| 主题系统 | 5 主题 + Alpine.js store | ✅ 已工作 |
| PWA 支持 | sw.js + manifest.json | ✅ 已工作 |

**关键发现**：`views/utils/` 下的 router.js、state.js、loader.js、api.js 模块已编写但未被 index.html 引用。index.html 使用的是内嵌版本。本次迁移**不需要改变**现有路由和加载机制，只需填充各视图模块的内容。

### 2.2 旧版页面功能概览（按复杂度排序）

| 序号 | 模块 | 旧版行数 | API数 | 弹窗数 | 复杂度 | 核心交互 | 外部依赖 |
|------|------|---------|-------|--------|--------|---------|---------|
| 1 | notifications | 220 | 3 | 0 | ⭐ | 只读列表+已读标记 | 无 |
| 2 | quality | 221 | 3 | 0 | ⭐ | 统计卡片+筛选列表 | 无 |
| 3 | audit | 243 | 3 | 0 | ⭐ | 表格+筛选+导出 | 无 |
| 4 | duplicates | 238 | 3 | 1 | ⭐+ | 滑块+合并弹窗 | 无 |
| 5 | upload | 258 | 3 | 0 | ⭐+ | Tab切换+拖拽上传 | 无 |
| 6 | shares | 269 | 4 | 0 | ⭐+ | 创建表单+链接列表+删除 | 无 |
| 7 | webhooks | 293 | 5 | 1 | ⭐⭐ | CRUD+测试+弹窗 | 无 |
| 8 | edit | 307 | 5 | 1 | ⭐⭐ | Markdown编辑器+实时预览 | Marked.js |
| 9 | approvals | 344 | 5 | 1 | ⭐⭐ | Tab+表格+驳回弹窗 | 无 |
| 10 | dashboard | 360 | 3 | 0 | ⭐⭐ | 4图表+统计卡片 | Chart.js |
| 11 | qa(补全) | 387 | 4 | 1 | ⭐⭐ | 聊天界面+LLM配置 | Marked.js |
| 12 | users | 442 | 9 | 3 | ⭐⭐⭐ | 双表+3弹窗+Token管理 | 无 |
| 13 | permissions | 824 | 12 | 3 | ⭐⭐⭐ | RBAC矩阵+角色CRUD | 无 |
| 14 | kb-management | 835 | 12 | 4 | ⭐⭐⭐ | 递归树+成员管理+统计 | 无 |

### 2.3 迁移模式分析

每个模块的迁移遵循统一模式：

```
旧版页面结构：
  ┌─ HTML 文档 ──────────────────────┐
  │ <head> (CDN引入)                 │ ← 剔除（SPA 已有）
  │ <body>                           │
  │   ┌─ header ──────────────┐      │ ← 剔除（SPA 侧边栏替代）
  │   │  logo + auth + logout │      │
  │   └──────────────────────┘      │
  │   ┌─ content ────────────┐      │ ← 保留（这是核心迁移内容）
  │   │  功能区域             │      │
  │   │  API 对象             │      │ ← 替换为 WikiAPI
  │   │  交互逻辑             │      │ ← 保留但调整
  │   └──────────────────────┘      │
  └──────────────────────────────────┘

迁移后模块结构：
  export function render(container) {
      // 1. 生成 HTML（只保留 content 部分）
      // 2. 写入 container
      // 3. 初始化交互逻辑
      // 4. 使用 WikiAPI 替代内联 API 对象
  }
```

---

## 三、技术方案

### 3.1 统一模块接口规范

每个视图模块必须遵循以下接口：

```javascript
/**
 * @param {HTMLElement} container - 外部视图容器
 * @returns {string} HTML 内容
 */
export function render(container) {
    // 1. 生成功能 HTML
    const html = `...`;

    // 2. 写入容器
    if (container) {
        container.innerHTML = html;
    }

    // 3. 初始化交互逻辑和事件绑定
    initModule();

    return html;
}

// 默认导出
export default {
    render,
    name: '模块名称',
    icon: '图标'
};
```

### 3.2 API 调用方式

旧版页面使用内联 `API` 对象，迁移后使用全局 `WikiAPI`：

```javascript
// 旧版（内联在每个 admin/*.html 中）
const API = {
    async get(url) { ... },
    async post(url, data) { ... },
    ...
};

// 迁移后（使用 SPA 框架提供的 WikiAPI）
// WikiAPI 已在 index.html 中定义为全局对象
const result = await WikiAPI.get('/api/stats');
const result = await WikiAPI.post('/api/webhooks', data);
const result = await WikiAPI.put('/api/atoms/123', data);
const result = await WikiAPI.delete('/api/share/token123');
```

### 3.3 样式规范

- 继续使用 `overview-container` + `overview-card` 类名（与现有 SPA 视图一致）
- 使用 Tailwind CSS 类名（与旧版页面兼容）
- 使用 SPA 主题变量（`text-on-base`、`text-on-surface`、`bg-bg-surface` 等）
- 弹窗使用统一的 `fixed inset-0 z-50` 模式

### 3.4 外部库处理

- **Chart.js**（dashboard）：需要动态加载 CDN，在 `render()` 中检查是否已加载
- **Marked.js**（edit、qa）：已通过 CDN 在 index.html 中引入，直接使用 `marked.parse()`

---

## 四、实施阶段

### 第 1 阶段：简单模块迁移（4-5 小时）

迁移 3 个最简单的模块（无弹窗、无写操作或极简写操作）。

#### 任务 1.1：notifications.js — 通知中心（1h）

**功能**：通知列表 + 标记已读/全部已读
**API**：`GET /api/notifications`、`POST /api/notifications/read`、`POST /api/notifications/read-all`
**迁移要点**：
- 通知列表渲染（未读/已读状态区分）
- 事件类型徽章（不同颜色）
- 标记已读按钮（单条/全部）
- 自动加载通知列表

#### 任务 1.2：quality.js — 质检中心（1h）

**功能**：质量检测 + 问题清单 + 筛选
**API**：`GET /api/quality/check`
**迁移要点**：
- 5 个统计卡片（空白内容、过期内容、低质量、长期草稿、总问题数）
- 问题类型筛选器
- 严重程度筛选器
- 问题列表渲染
- 加载动画（质检需要时间）

#### 任务 1.3：audit.js — 审计日志（1h）

**功能**：审计日志表格 + 筛选 + 导出
**API**：`GET /api/audit?action=&limit=`
**迁移要点**：
- 操作类型下拉筛选
- 条数下拉筛选（50/100/200）
- 数据表格（5列：时间、用户、操作、目标、详情）
- 操作类型彩色徽章
- JSON 导出按钮（客户端 Blob/URL）

---

### 第 2 阶段：基础 CRUD 模块迁移（5-6 小时）

迁移 5 个基础 CRUD 模块（有弹窗或表单）。

#### 任务 2.1：duplicates.js — 去重管理（1h）

**功能**：重复检测 + 相似度调节 + 合并操作
**API**：`GET /api/duplicates?threshold=`、`POST /api/duplicates/merge`
**迁移要点**：
- 相似度滑块（0.3-1.0，默认 0.7）
- 重复对卡片（含相似度进度条）
- 合并弹窗（主文档选择 + 合并策略 append/replace）
- 重新检测按钮

#### 任务 2.2：upload.js — 内容上传（1h）

**功能**：文件上传 + 路径摄入
**API**：`POST /api/ingest/upload`、`POST /api/ingest`
**迁移要点**：
- Tab 切换（文件上传 / 路径摄入）
- 拖拽上传区（drop-zone）+ 文件选择
- 批量文件上传（FormData 循环）
- 路径摄入表单
- 权限检查（仅 editor/admin）

#### 任务 2.3：shares.js — 分享管理（1h）

**功能**：创建分享外链 + 列表 + 回收
**API**：`POST /api/share`、`GET /api/share`、`DELETE /api/share/:token`
**迁移要点**：
- 创建表单（原子ID、有效期、密码、最大访问次数）
- 分享链接列表（状态徽章：active/revoked/expired）
- 复制链接按钮
- 回收/删除按钮

#### 任务 2.4：webhooks.js — Webhook 管理（1.5h）

**功能**：Webhook CRUD + 测试发送
**API**：`GET /api/webhooks`、`POST /api/webhooks`、`DELETE /api/webhooks/:id`、`POST /api/webhooks/test`
**迁移要点**：
- Webhook 列表卡片（平台徽章）
- 添加弹窗（5字段：名称、平台、URL、事件、密钥）
- 平台选择（企业微信/钉钉/飞书/自定义）
- 测试发送按钮
- 删除确认

#### 任务 2.5：approvals.js — 审批管理（1.5h）

**功能**：待审批列表 + 审批历史 + 通过/驳回
**API**：`GET /api/approvals/pending`、`GET /api/approvals/history`、`POST /api/atoms/:id/approve`、`POST /api/atoms/:id/reject`
**迁移要点**：
- Tab 切换（待审批 / 审批历史）
- 待审批表格 + 操作按钮（通过/驳回）
- 驳回弹窗（含 textarea 填原因）
- 审批历史表格（状态徽章）
- 管理员权限检查

---

### 第 3 阶段：中等复杂度模块迁移（5-6 小时）

迁移 4 个中等复杂度模块（编辑器、图表、聊天等）。

#### 任务 3.1：qa.js 补全 — AI 问答功能增强（1h）

**功能**：补全 qa.js 缺失的 API 调用
**API**：`GET /api/qa/history`、`POST /api/qa/clear`（目前 qa.js 只用了 POST /api/qa/ask）
**迁移要点**：
- 加载对话历史（`GET /api/qa/history`）
- 清空对话历史（`POST /api/qa/clear`）
- 对话持久化（服务端而非仅 localStorage）
- 来源引用卡片渲染
- LLM 配置弹窗实现（替代当前 alert）

#### 任务 3.2：dashboard.js — 数据看板（1.5h）

**功能**：统计概览 + 图表
**API**：`GET /api/stats`、`GET /api/analytics/behavior`
**迁移要点**：
- 动态加载 Chart.js CDN（检查是否已加载）
- 4 个统计卡片
- 环形图（类型分布、状态分布）
- 柱状图（热门标签、用户活跃度）
- Chart 实例生命周期管理（切换视图时销毁）
- Promise.all 并发加载

#### 任务 3.3：edit.js — 在线编辑器（1.5h）

**功能**：Markdown 编辑器 + 实时预览
**API**：`POST /api/atoms`、`PUT /api/atoms/:id`、`GET /api/atoms/:id`、`POST /api/atoms/:id/publish`
**迁移要点**：
- 元信息表单（标题、类型、标签）
- Markdown 编辑器 + 实时预览（分栏）
- 编辑器工具栏（B/I/H/列表/链接/代码块）
- 加载已有原子弹窗
- URL 参数读取（`?atom_id=xxx` → `#edit?atom_id=xxx`）
- 创建/更新双模式
- Marked.js 已在 SPA 中引入

#### 任务 3.4：users.js — 用户管理（1.5h）

**功能**：用户 CRUD + Token 管理
**API**：`GET /api/users`、`POST /api/users`、`DELETE /api/users/:username`、`PUT /api/users/:username/role`、`PUT /api/users/:username/password`、`GET /api/tokens`、`POST /api/tokens`、`DELETE /api/tokens/:token`
**迁移要点**：
- Tab 切换（用户列表 / Token 管理）
- 用户表格（角色修改下拉）
- 3 个弹窗（添加用户、生成 Token、修改密码）
- 删除确认
- 管理员权限检查

---

### 第 4 阶段：高复杂度模块迁移（6-8 小时）

迁移 2 个最复杂模块（RBAC 权限矩阵、知识库层级树）。

#### 任务 4.1：permissions.js — 权限管理（3-4h）

**功能**：角色 CRUD + 权限矩阵 + 用户权限分配
**API**：12 个端点（角色 CRUD、权限矩阵、用户权限 CRUD）
**迁移要点**：
- 3 个 Tab（角色管理 / 权限矩阵 / 用户权限查询）
- 角色表格（CRUD）
- 权限矩阵表格（复选框网格：行=用户+知识库，列=6种权限）
- 3 个弹窗（创建角色、编辑角色、分配权限）
- 权限复选框即时切换 + 回滚逻辑
- 管理员权限检查

#### 任务 4.2：kb-management.js — 知识库管理（3-4h）

**功能**：知识库 CRUD + 层级树 + 成员管理
**API**：12 个端点（知识库 CRUD、层级树、成员 CRUD、统计）
**迁移要点**：
- 3 个 Tab（知识库列表 / 层级树 / 成员管理）
- 知识库表格（7列）
- 层级树视图（递归渲染 + 展开/折叠）
- 成员管理表格
- 4 个弹窗（创建、编辑，添加成员，统计）
- 层级筛选器
- 加载指示器

---

### 第 5 阶段：QA 补全 + 通用优化（2-3 小时）

#### 任务 5.1：qa.js 功能补全（1h）

（同任务 3.1，如已在第 3 阶段完成则跳过）

#### 任务 5.2：通用 UI 组件提取（1h）

从迁移过程中识别可复用的 UI 模式，提取为通用组件：
- `createModal(title, content, onConfirm)` — 弹窗组件
- `createTable(columns, data, actions)` — 表格组件
- `createTabSwitcher(tabs)` — Tab 切换组件
- `createBadge(text, color)` — 徽章组件
- `createLoadingSpinner()` — 加载指示器

**目的**：减少后续模块的重复代码，保持 UI 一致性。

#### 任务 5.3：侧边栏链接统一测试（0.5h）

- 验证所有 14 个管理工具的侧边栏链接
- 验证移动端侧边栏链接
- 验证 hash 路由跳转正确性
- 验证浏览器前进/后退

---

### 第 6 阶段：整合验证（3-4 小时）

#### 任务 6.1：功能对等验证（1.5h）

逐一对比旧版 `admin/*.html` 和新版 `views/*.js`：
- 每个 API 端点调用是否正确
- 每个交互功能是否完整
- 每个弹窗是否正常弹出和关闭
- 每个筛选/排序是否正常工作

#### 任务 6.2：跨视图状态验证（0.5h）

- 主题切换跨视图持久化
- 用户认证跨视图保持
- 水印跨视图保持
- Chart 实例在视图切换时正确销毁

#### 任务 6.3：边界情况验证（0.5h）

- 模块加载失败时的错误提示
- API 请求失败时的错误提示
- 未授权操作的提示
- 空数据时的空状态显示

#### 任务 6.4：旧版页面保留策略（0.5h）

- 保留 `admin/*.html` 作为备份（不删除）
- 在 admin 页面添加"新版入口"链接
- 侧边栏仅指向 SPA 路由（#xxx），不再链接 /admin/xxx.html

---

## 五、依赖关系

### 5.1 任务依赖图

```
阶段 1（notifications, quality, audit）← 无依赖，可并行
  ↓
阶段 2（duplicates, upload, shares, webhooks, approvals）← 依赖阶段 1 的经验
  ↓  可并行（5 个模块独立）
阶段 3（qa补全, dashboard, edit, users）← 依赖阶段 2 的弹窗/Tab组件经验
  ↓  dashboard 依赖 Chart.js CDN 加载方案
阶段 4（permissions, kb-management）← 依赖阶段 3 的完整 CRUD 经验
  ↓  可并行（2 个模块独立）
阶段 5（通用优化 + 侧边栏测试）← 依赖所有模块完成
  ↓
阶段 6（整合验证）← 依赖所有模块完成
```

### 5.2 并行执行机会

| 阶段 | 可并行数 | 说明 |
|------|---------|------|
| 阶段 1 | 3 个模块 | notifications, quality, audit 完全独立 |
| 阶段 2 | 5 个模块 | 所有模块独立，但建议串行积累弹窗经验 |
| 阶段 3 | 4 个模块 | qa补全、dashboard、edit、users 独立 |
| 阶段 4 | 2 个模块 | permissions、kb-management 独立 |

---

## 六、风险评估

### 6.1 高风险（HIGH）

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **Chart.js CDN 加载** | dashboard 图表无法渲染 | 在 render() 中动态检测+加载，失败时降级为纯数字统计 |
| **权限矩阵复选框即时切换** | 用户误操作导致权限混乱 | 添加确认提示 + 回滚逻辑 |
| **kb-management 递归树渲染** | 层级深时渲染性能差 | 限制展开深度 + 虚拟化渲染 |

### 6.2 中风险（MEDIUM）

| 鹿险 | 影响 | 缓解措施 |
|------|------|---------|
| **拖拽上传在 SPA 容器中的兼容性** | 拖拽事件可能与 SPA 交互冲突 | 使用 stopPropagation 防止事件冒泡 |
| **弹窗在 SPA 容器中的层级** | 弹窗可能被侧边栏遮挡 | 统一使用 z-50 + fixed inset-0 |
| **Markdown 编辑器光标操作** | 编辑器工具栏插入可能与 SPA 冲突 | 使用 textarea 直接操作，不依赖 DOM 事件委托 |

### 6.3 低风险（LOW）

| 鹿险 | 影响 | 缓解措施 |
|------|------|---------|
| **旧版页面保留** | 用户可能仍访问旧版 | 在旧版页面添加迁移提示 |
| **样式冲突** | 旧版 Tailwind 类可能与 SPA 主题变量冲突 | 使用优先级测试，必要时添加作用域 |

---

## 七、预估复杂度

**总体复杂度：中-高（MEDIUM-HIGH）**

| 阶段 | 预估时间 | 复杂度 | 说明 |
|------|---------|--------|------|
| 阶段 1：简单模块 | 3h | ⭐ | 只读列表+简单操作 |
| 阶段 2：基础 CRUD | 5.5h | ⭐+ | 弹窗+表单+CRUD |
| 阶段 3：中等模块 | 5.5h | ⭐⭐ | 编辑器+图表+多API |
| 阶段 4：高复杂度 | 7h | ⭐⭐⭐ | RBAC矩阵+递归树 |
| 阶段 5：优化 | 2h | ⭐ | 组件提取+测试 |
| 阶段 6：验证 | 3h | ⭐ | 功能对比+边界验证 |
| **总计** | **25h** | | |

---

## 八、成功标准

### 8.1 功能标准

- ✅ 13 个占位模块替换为完整功能模块
- ✅ qa.js 补全缺失的 API 调用（历史加载、清空）
- ✅ 所有模块功能与旧版 `admin/*.html` 对等
- ✅ 所有弹窗正常弹出、关闭、提交
- ✅ 所有筛选/排序/导出功能正常

### 8.2 体验标准

- ✅ 视图切换无刷新（SPA 体验）
- ✅ 侧边栏始终可见
- ✅ 浏览器前进/后退正常
- ✅ 主题切换跨视图持久化
- ✅ 加载状态有明确提示

### 8.3 质量标准

- ✅ 无 console.log 语句
- ✅ 所有 API 调用使用 WikiAPI
- ✅ 所有模块有清晰的注释
- ✅ 错误处理完善（API 失败、网络错误、权限不足）

---

## 九、下一步

1. 确认此计划后，调用 `/supercode:plan-segment` 进行任务拆分
2. 按阶段 1 → 6 顺序执行
3. 每个阶段完成后进行阶段性验证
4. 全部完成后调用 `/supercode:plan-verify` 进行质量验证

**等待确认**：是否继续执行此计划？
