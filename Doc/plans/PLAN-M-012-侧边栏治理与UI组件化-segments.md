# PLAN-M-012-侧边栏治理与UI组件化-segments.md

---
plan_id: PLAN-M-012
type: segments
source_plan: PLAN-M-012-侧边栏治理与UI组件化.md
status: executed
created: 2026-06-25
executed: 2026-06-25
execution_mode: auto
result: 38/38 子任务完成（无阻塞）；详见源计划「九、完成总结」
total_task_groups: 11
total_sub_tasks: 38
serial_groups: 8
parallel_groups: 3
nav_strategy: 彻底方案（nav-config 驱动 + Alpine template x-for）
---

## 一、拆分总览

| 阶段 | 任务组 | 类型 | 前置 | 子任务 |
|------|--------|------|------|:-----:|
| P0 | 0-A 导航数据层 | 串行·基础 | 无 | 4 |
| P0 | 0-B 桌面侧边栏改造 | 串行 | 0-A | 4 |
| P0 | 0-C 移动端 drawer 改造 | 串行 | 0-A（与 0-B 同文件，不并行） | 3 |
| P0 | 0-D 路由白名单单一来源 | 串行 | 0-A | 2 |
| P1 | 1-A 共享组件库 | 串行·基础 | 无（可与 P0 并行起步） | 2 |
| P1 | 1-B 模块接入共享组件 | **并行**（14 独立文件） | 1-A | 14 |
| P1 | 1-C 主题化补齐 | 串行 | 1-A | 4 |
| P1 | 1-D 遗留引用清理 | **并行** | 0-B（header 与侧边栏入口需协调） | 3 |
| P2 | 2-A 分组呈现 | 串行 | 0-B/0-C | 1 |
| P2 | 2-B API 调用统一 | **并行** | 1-B | 1 |
| P2 | 2-C 功能边界建议 | 串行·文档 | 无 | — |

---

## 二、任务组详情

### 任务组 0-A：导航数据层（串行 · 基础）
**前置条件：** 无
**文件：** 新建 `views/utils/nav-config.js`
**测试策略：** 仅手动验证（纯数据模块）

- [x] SUB-001: 创建 `nav-config.js`，导出 `MAIN_VIEWS[]`（overview/browse/graph/timeline/gaps，字段 label/view/icon/badge）
- [x] SUB-002: 导出 `ADMIN_TOOLS[]`（字段 label/route/icon/roles/group），**修正语义错配**：`notifications`→"通知"、`webhooks`→"集成/Webhook" 两条独立项
- [x] SUB-003: 在 `ADMIN_TOOLS` 补入 permissions/kb-management/users/approvals/audit（roles=['admin']，group='系统管理'）
- [x] SUB-004: 导出派生工具 `getRoutableViews()`（供路由白名单复用，消除两处硬编码）

### 任务组 0-B：桌面侧边栏改造（串行 · 依赖 0-A）
**文件：** `views/index.html`（侧边栏 707-819；权限脚本 511-524）
**测试策略：** 手动 + admin/editor/viewer 三角色冒烟

- [x] SUB-005: 备份当前静态侧边栏片段到本 segments 文件"附录"
- [x] SUB-006: 在 `app()` Alpine 数据中引入 `adminTools`（import nav-config）
- [x] SUB-007: 桌面"管理工具"区改为 `<template x-for="item in adminTools">`，`x-show` 按 `currentUser.role ∈ item.roles` 过滤
- [x] SUB-008: 删除 511-524 的 `getElementById(...).classList.remove('hidden')` 权限脚本（由 Alpine x-show 接管）

### 任务组 0-C：移动端 drawer 改造（串行 · 依赖 0-A）
**文件：** `views/index.html`（移动端 drawer 675-702）
**测试策略：** 移动端视口手动冒烟

- [x] SUB-009: 移动端主视图区改 `<template x-for="v in mainViews">`（保留 `@click="view=...; sidebarOpen=false"` 行为）
- [x] SUB-010: 移动端管理工具区改 `<template x-for="item in adminTools">`，与桌面同源
- [x] SUB-011: 验证双端项数量/顺序/权限完全一致

### 任务组 0-D：路由白名单单一来源（串行 · 依赖 0-A）
**文件：** `views/index.html`（handleRoute 1772-1774；isExternalView 1902-1906）
**测试策略：** 各 hash 路由手动跳转冒烟

- [x] SUB-012: `handleRoute()` 的硬编码数组改为 `getRoutableViews()`
- [x] SUB-013: `isExternalView()` 的硬编码数组改为同一来源

### 任务组 1-A：共享组件库（串行 · 基础）
**文件：** 新建 `views/utils/ui-components.js`
**测试策略：** node 导入冒烟（语法/导出检查）

- [x] SUB-014: 创建 `ui-components.js`，导出 `escapeHtml`
- [x] SUB-015: 导出 `createBadge` / `createLoadingSpinner` / `createModal` / `createTable` / `createTabSwitcher`（全部用语义 class，自带主题适配）

### 任务组 1-B：模块接入共享组件（**并行** · 依赖 1-A）
**文件：** `views/views/*.js`（14 个，互相独立 → 流水线/并行）
**测试策略：** 每模块打开视图 + 主交互手动冒烟

- [x] SUB-016~029: 逐模块替换各自的 `escapeHtml`/手写弹窗/loading/徽章映射为共享组件
  - notifications / quality / audit / duplicates / upload / shares / webhooks / edit / approvals / dashboard / qa / users / permissions / kb-management

### 任务组 1-C：主题化补齐（串行 · 依赖 1-A）
**文件：** `views/views/dashboard.js`、`views/views/notifications.js`、`views/index.html`（setTheme 1808-1817）
**测试策略：** 5 主题逐一切换目测

- [x] SUB-030: dashboard 统计卡硬编码色 → 语义 class
- [x] SUB-031: dashboard Chart.js 颜色改读 CSS 变量（`getComputedStyle`）
- [x] SUB-032: `setTheme()` 增加图表重绘 hook（主题切换时 `chart.update()`）
- [x] SUB-033: notifications.js 19 处硬编码色清理

### 任务组 1-D：遗留引用清理（**并行** · 依赖 0-B）
**文件：** `views/components/header.js`、`views/index.html:1190`、`views/admin/*.html`
**测试策略：** `grep /admin/*.html` 计数 + 手动

- [x] SUB-034: `header.js` 50-55 四个 `/admin/*.html` 链接 → 改 hash 路由 **或** 移除（因侧边栏已补入口，建议移除避免重复）
- [x] SUB-035: `index.html:1190` `/admin/duplicates.html` → `#duplicates`
- [x] SUB-036: 14 个 `admin/*.html` 顶部加"已迁移至新版，请使用主界面"提示 banner

### 任务组 2-A：分组呈现（串行 · 依赖 0-B/0-C）
**测试策略：** 目测

- [x] SUB-037: 侧边栏按 `item.group` 渲染分组标题（内容操作 / 系统管理）

### 任务组 2-B：API 调用统一（**并行** · 依赖 1-B）
**文件：** `views/views/upload.js`、`qa.js`、`webhooks.js`
**测试策略：** 手动冒烟

- [x] SUB-038: 裸 `fetch()` / `apiGet` / `apiPost` 统一为 `WikiAPI`

### 任务组 2-C：功能边界建议（文档 · 无依赖）
- 在源计划"发现与记录"补：概览 vs 看板、质检/去重/缺口 的职责边界与聚合建议（仅文档，不强制合并）

---

## 三、执行顺序

```
1️⃣ 0-A 导航数据层（nav-config.js）──────┐
   1-A 共享组件库（ui-components.js）── 可同时起步（不同文件）
        ↓                                    ↓
2️⃣ 0-B 桌面侧边栏 ─→ 0-C 移动端 ─→ 0-D 路由   1-B 模块接入（14 并行）
        ↓                                    ↓
3️⃣ 1-D 遗留清理（依赖 0-B）          1-C 主题化补齐
        ↓
4️⃣ 2-A 分组 → 2-B API统一 → 2-C 文档建议
        ↓
5️⃣ 全量多主题 + 双端 + 多角色冒烟验收
```

**关键协调点：**
- 0-B 与 0-C 同改 index.html → **不可并行**，顺序执行。
- 1-D（header 清理）必须在 0-B 之后：侧边栏补入口后 header 的 admin 链接才成冗余。
- 1-B 14 模块文件独立，是最大并行收益点。

---

## 附录：原始静态侧边栏片段备份
（SUB-005 已填入，便于回滚）

> 备份时间：2026-06-25。以下为改造前 `views/index.html` 的静态侧边栏结构关键事实，
> 完整原文可通过 `git show HEAD:views/index.html` 获取（行号以改造前为准）。

**桌面侧边栏「管理工具」区（改造前，约 740-817 行）**：静态 9 条 `<a>`，含语义错配项
`id="webhookLinkDesktop"` 标签为「通知」却 `href="#webhooks"`；`editLinkDesktop`/`uploadLinkDesktop`/
`sharesLinkDesktop` 由 511-524 行 `getElementById(...).classList.remove('hidden')` 权限脚本控制（实际无 `hidden` 初始类，恒显示）。

**移动端 drawer（改造前，约 675-702 行）**：主视图 5 项（概览/浏览/图谱/时间线/缺口）+
管理工具仅 4 项（AI 问答/看板/质检/去重），与桌面 9 项不一致。

**权限脚本（改造前 511-524 行）**：基于 `d.user.role` 的 `classList.remove('hidden')`，已由 Alpine `x-show` + nav-config `roles` 接管，整段删除。

**路由白名单（改造前）**：`handleRoute()`（约 1772-1774）与 `isExternalView()`（约 1902-1906）
各硬编码一份 14 元素数组，已统一为 `nav-config.getRoutableViews()`。
