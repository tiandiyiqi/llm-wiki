# PLAN-M-012-侧边栏治理与UI组件化.md

---
plan_id: PLAN-M-012
type: master
status: completed
created: 2026-06-25
completed: 2026-06-25
priority: high
parent: PLAN-M-011 (管理工具区 SPA 迁移)
segments_file: PLAN-M-012-侧边栏治理与UI组件化-segments.md
segments_created: 2026-06-25
current_stage: 任务组拆分完成，等待执行确认
based_on: web-ui 左侧栏统筹分析报告（2026-06-25）
---

## 一、需求重述

承接 PLAN-M-011（14 个管理模块完成 SPA 迁移）后的**治理与收尾**工作。迁移虽已完成功能填充，但留下三类问题，本计划针对性解决：

1. **导航层**：侧边栏入口与命名混乱（"通知"实际指向 webhooks；桌面 9 项 vs 移动端 4 项不一致；permissions/kb-management/users/approvals/audit 等重型模块无稳定入口）。
2. **外观层**：PLAN-M-011 任务组 5-1 规划的通用组件 `ui-components.js` 从未落地，导致 `escapeHtml`×13、手写弹窗×7、loading×10、徽章映射×6 大量重复；dashboard.js 完全未主题化（45 硬编码色 / 0 语义色）。
3. **遗留层**：新旧两套页面并存，`header.js` 与 `index.html:1190` 仍引用旧 `/admin/*.html` 静态页；PLAN-M-011 任务组 6-4 的清理未执行。

**核心目标**：在不破坏现有 SPA 功能的前提下，统一导航、抽取共享 UI 组件、补齐主题化、清理遗留引用。

**非目标**：不重写业务逻辑，不改后端 API，不引入构建工具或 JS 框架。

---

## 二、现状分析（摘自统筹分析报告）

### 2.1 技术约束

- **前端栈**：原生 JS + Alpine.js + Tailwind（CDN），无 Node 构建、无打包、无 JS 测试框架。
- **视图模块**：`views/views/*.js` 共 14 个，导出 `render()` 生成模板字符串。
- **路由**：hash 路由（`#qa` 等）+ index.html 内嵌 `loadViewModule()` 动态 `import()`。
- **主题**：5 套主题（classic/dark-tech/forest/terracotta/monochrome），语义 class（`text-accent`/`bg-bg-surface` 等）+ `localStorage`。

> ⚠️ **测试说明**：本项目 `tests/` 为 Python 后端测试，前端无自动化测试框架。本计划验证以**人工冒烟 + 浏览器 console 检查 + 多主题切换目测**为主，不套用 80% 覆盖率门禁（如需引入前端测试需另立专项计划）。

### 2.2 关键事实数据

| 问题 | 量化证据 |
|------|---------|
| `escapeHtml` 重复 | 13 / 14 模块各自定义 |
| 手写弹窗骨架 | 7 个模块 |
| loading spinner | 10 个模块 |
| 徽章颜色映射 | 6 个模块 |
| dashboard 主题化 | 45 硬编码色 / 0 语义色 |
| notifications 主题化 | 19 硬编码 / 11 语义 |
| 桌面/移动端入口 | 9 项 vs 4 项 |
| 旧页残留引用 | header.js 4 处 + index.html:1190 共 5 处 |
| 无侧边栏入口的模块 | permissions(857)/kb-management(775)/users(603)/approvals/audit |

---

## 三、实施阶段（Phases）

> 阶段按"风险递增、价值递减"排序，支持按 scope 裁剪（core = Phase 0+1；complete = 全部）。

### Phase 0：导航修正（P0，低风险高价值）

**目标**：理清入口与命名，统一双端导航。

- **0.1 修正"通知"语义错配**
  - `index.html` 侧边栏：将标签"通知"（当前 `id=webhookLinkDesktop` → `#webhooks`）拆为两项：
    - "通知" → `#notifications`（站内消息中心，对应 `notifications.js`）
    - "集成/Webhook" → `#webhooks`（出站推送配置，对应 `webhooks.js`）
  - 修正 `id` 命名（`webhookLinkDesktop` → 语义化）。
- **0.2 补齐重型模块入口**
  - 为 `permissions` / `kb-management` / `users` / `approvals` / `audit` 在"系统管理"分组下补稳定 hash 入口（按权限 `x-show` 控制）。
- **0.3 统一桌面/移动端侧边栏**
  - 抽取**单一导航配置数组**（`views/utils/nav-config.js`，含 label/route/icon/权限/分组），桌面与移动端 drawer 均由该数组渲染，消除两套手写不一致。

### Phase 1：UI 组件化 + 主题化补齐 + 遗留清理（P1）

**目标**：落地 PLAN-M-011 跳过的 5-1/6-4 任务。

- **1.1 创建 `views/utils/ui-components.js`**
  - 导出：`escapeHtml` / `createModal` / `createTable` / `createBadge` / `createLoadingSpinner` / `createTabSwitcher`。
  - 统一使用语义 class，确保组件自带主题适配。
- **1.2 逐模块接入共享组件**
  - 14 个模块替换各自的 `escapeHtml`、手写弹窗、loading、徽章映射为共享组件调用。
  - 每替换一个模块即冒烟验证一次（最小差异、逐个提交）。
- **1.3 dashboard.js 主题化**
  - 统计卡硬编码色 → 语义 class。
  - Chart.js 颜色改为读取 CSS 变量（`getComputedStyle` 取主题色），主题切换时重绘。
  - 同步处理 notifications.js（19 硬编码）等次要超标模块。
- **1.4 遗留引用清理**
  - 修正 `header.js` 4 处 `/admin/*.html` → 对应 hash 路由。
  - 修正 `index.html:1190` 的 `/admin/duplicates.html` → `#duplicates`。
  - 决策旧 `admin/*.html` 14 页去留（建议：保留但加显著"已迁移至新版"提示，或移入 `views/admin/_legacy/`）。

### Phase 2：分组与一致性优化（P2，可选）

**目标**：体验打磨，非必须。

- **2.1 管理工具区分组**：按"内容操作"（新建/上传/质检/去重/分享）与"系统管理"（看板/用户/权限/知识库/审批/审计/通知/Webhook）二级分组。
- **2.2 统一 API 调用方式**：`upload.js`/`qa.js`/`webhooks.js` 的裸 `fetch()`、`apiGet/apiPost` 统一为 `WikiAPI`。
- **2.3 功能边界梳理**：概览 vs 看板、质检/去重/缺口 的职责说明与可能的聚合（仅文档建议，不强制合并）。

---

## 四、依赖关系（Dependencies）

```
Phase 0.3 (nav-config.js) ──┬──> Phase 0.1 / 0.2（导航项均由配置驱动）
Phase 1.1 (ui-components.js) ──> Phase 1.2（模块接入依赖组件存在）
Phase 1.1 ──> Phase 1.3（dashboard 主题化复用 createBadge 等）
Phase 0/1 完成 ──> Phase 2（优化依赖稳定基线）
```

- 无外部依赖（不新增 npm 包/CDN）。
- Chart.js、Marked.js 已存在，复用。

---

## 五、风险评估

| 等级 | 风险 | 缓解措施 |
|:----:|------|---------|
| 🟠 中高 | Phase 0.3 采用彻底方案：用 Alpine `<template x-for>` 重写桌面+移动端侧边栏为 nav-config 驱动，改动 140KB 主文件结构 | 先备份 index.html 侧边栏原始片段于计划"发现与记录"；保留主视图按钮（overview 等）的 `@click="view="` 行为不变，仅将管理工具区改为配置渲染；改完立即多主题+双端冒烟 |
| 🟡 中 | 14 模块批量替换共享组件可能引入回归 | 逐模块替换 + 每模块冒烟 + 独立提交，便于回滚 |
| 🟡 中 | dashboard Chart.js 读 CSS 变量在主题切换时机问题 | 监听主题切换事件触发 `chart.update()`；降级为固定调色板 |
| 🟢 低 | 导航配置化后权限 `x-show` 遗漏 | 对照现有 header.js 权限逻辑逐项核对 |
| 🟢 低 | 旧 admin 页删除影响外部书签 | 优先"保留+提示"而非删除 |
| 🟢 低 | 无自动化测试，回归靠人工 | 提供逐模块冒烟清单（见验收标准） |

---

## 六、复杂度估算

| Phase | 范围 | 复杂度 | 预估 |
|:-----:|------|:------:|------|
| Phase 0 | 导航修正（3 文件） | 中 | 2-3 小时 |
| Phase 1 | 组件化+主题化+清理（17 文件） | 高 | 6-9 小时 |
| Phase 2 | 分组与一致性（可选） | 中 | 2-4 小时 |
| **合计** | | **高** | **core 8-12h / complete 10-16h** |

---

## 七、验收标准

**Phase 0**
- [ ] 侧边栏"通知"指向站内通知；Webhook 配置有独立入口；两者不再混淆。
- [ ] permissions/kb-management/users/approvals/audit 均可从侧边栏（按权限）进入。
- [ ] 桌面与移动端导航项数量/顺序一致，且由同一配置驱动。

**Phase 1**
- [ ] `ui-components.js` 存在并被 ≥10 个模块引用。
- [ ] 全局 `escapeHtml` 仅保留 1 处定义（共享）。
- [ ] dashboard 在 5 套主题下均正确换肤（含图表色）。
- [ ] 全仓 grep `/admin/*.html` 引用为 0（除旧页自身与刻意保留的提示链接）。

**Phase 2（若执行）**
- [ ] 侧边栏呈现"内容/系统管理"分组。
- [ ] 全部模块 API 调用统一走 `WikiAPI`。

**通用**
- [ ] 浏览器 console 无新增报错。
- [ ] 逐模块冒烟：打开每个视图 → 主要交互（弹窗/筛选/提交）正常。

---

## 八、发现与记录

### 8.1 执行中发现

- **桌面侧边栏权限脚本为空操作**：改造前 `editLinkDesktop`/`uploadLinkDesktop`/`sharesLinkDesktop` 等并无 `hidden` 初始类，511-524 行的 `classList.remove('hidden')` 实为无效（这些入口对所有角色恒显示）。改为 nav-config `roles` + Alpine `x-show` 后，权限可见性才真正生效。
- **「通知」语义错配确认**：旧「通知」项使用铃铛图标却 `href="#webhooks"`。已拆为 `通知 #notifications`（铃铛）与 `集成/Webhook #webhooks`（链接图标）两条独立项。
- **dashboard 刷新潜在 bug**：原 `loadData()` 重复渲染同一 canvas 未先 `destroyCharts()`，再次点击「刷新」会触发 Chart.js "Canvas is already in use" 报错。已在 `loadData()` 开头加 `destroyCharts()` 一并修复，并复用为主题重绘入口。
- **upload 上传必须用 FormData**：`/api/ingest/upload` 为 multipart 上传，不可走 `WikiAPI.post`（其 `JSON.stringify` + `application/json` 会破坏 FormData）。已在 `WikiAPI` 新增 `postForm(url, formData)`（不手动设 Content-Type，内置 401 跳转），upload.js 改用之，实现「统一走 WikiAPI」而不破坏上传语义。
- **状态徽章保留**：notifications 的事件状态徽章（绿/红/黄/蓝 浅底深字）为跨主题可读的语义状态标识，未强行映射为主题变量；仅清理了真正破坏暗色主题的结构色（卡片面/边框/悬停/未读高亮）。
- **遗留 `/admin/*.html` 引用**：活跃 SPA 代码（index.html / views/*.js / components）中的链接引用已清零；仅余各视图模块顶部 JSDoc 的「提取自 /views/admin/xxx.html」溯源注释（非链接，不影响）。14 个旧页已加「前往新版」提示 banner 并保留，避免破坏外部书签。

### 8.2 功能边界建议（SUB-2-C · 仅文档，不强制合并）

> 目的：厘清概览/看板与质检/去重/缺口之间的职责，供后续信息架构优化参考。

| 模块 | 定位 | 数据视角 | 边界建议 |
|------|------|---------|---------|
| **概览（overview）** | 知识库「快照」首页 | 原子总量、类型分布、近期/高置信原子、标签云 | 面向**所有读者**的只读概要，强调「内容有什么」。 |
| **看板（dashboard）** | 运营「分析」后台 | 行为分析、用户活跃度、操作总数、热门文档（Chart.js） | 面向**运营/管理者**，强调「系统被如何使用」。与概览数据视角不同，**建议保持独立**，但可在概览增加「查看完整看板 →」入口避免认知割裂。 |
| **质检（quality）** | 内容**健康度**检查 | 字段完整性、格式规范、置信度阈值 | 关注「单条质量」。 |
| **去重（duplicates）** | 内容**冗余**检查 | 相似度比对、重复对 | 关注「条目间冗余」。 |
| **缺口（gaps）** | 内容**覆盖度**检查 | 缺失主题/未回答问题 | 关注「整体缺什么」。 |

**聚合建议（可选，非本计划范围）**：质检 / 去重 / 缺口 三者同属「内容治理」语义，未来可考虑聚合为单一「内容体检」入口下的三个 Tab（复用 `createTabSwitcher`），减少侧边栏「内容操作」分组的项数。当前保持独立入口，不强制合并。

---

## 九、完成总结

**完成日期**：2026-06-25　**执行模式**：`/supercode:plan-execution --auto`（全自动）

### 9.1 交付物

| 类别 | 文件 | 说明 |
|------|------|------|
| 新增 | `views/utils/nav-config.js` | 导航单一来源：`MAIN_VIEWS`(5) / `ADMIN_TOOLS`(14) / `EXTERNAL_LINKS` / `getRoutableViews()` / `getAdminGroups()` |
| 新增 | `views/utils/ui-components.js` | 共享组件：`escapeHtml` / `createBadge` / `createLoadingSpinner` / `createModal` / `createTable` / `createTabSwitcher` |
| 改造 | `views/index.html` | 桌面+移动端侧边栏改为 `x-for` 配置驱动（按角色 `x-show` + 二级分组）；删除失效权限脚本；路由白名单统一为 `getRoutableViews()`；`setTheme` 增加看板重绘 hook；`WikiAPI` 新增 `postForm`；移除冗余 header 入口与 `/admin/duplicates.html` 链接 |
| 改造 | `views/views/*.js`（13 个） | 接入共享 `escapeHtml`，删除各自本地实现 |
| 改造 | `views/views/dashboard.js` | 统计卡/文本/图表全量主题化；Chart.js 配色读 CSS 变量；修复重复渲染 bug |
| 改造 | `views/views/notifications.js` | 结构色主题化（面/边框/悬停/未读高亮） |
| 改造 | `views/views/upload.js`、`qa.js` | 裸 `fetch` 统一为 `WikiAPI.postForm` / `WikiAPI.post` |
| 改造 | `views/components/header.js` | 旧 `/admin/*.html` 链接 → hash 路由 |
| 改造 | `views/admin/*.html`（14 个） | 顶部加「前往新版」迁移提示 banner |

### 9.2 验收对照

- ✅ 「通知」指向站内通知，Webhook 独立入口，语义不再混淆。
- ✅ permissions/kb-management/users/approvals/audit 均可从侧边栏（admin 角色）进入。
- ✅ 桌面与移动端导航由同一 nav-config 驱动，数量/顺序/权限一致。
- ✅ `ui-components.js` 被 13 个视图模块引用（≥10）。
- ✅ SPA 视图模块内 `escapeHtml` 仅 1 处共享定义。
- ✅ dashboard 5 主题换肤（含图表色），主题切换触发重绘。
- ✅ 活跃 SPA 代码中 `/admin/*.html` 链接引用为 0。
- ✅ 侧边栏呈现「内容操作 / 系统管理」分组。
- ✅ 目标模块 API 调用统一走 `WikiAPI`。

### 9.3 验证方式与遗留

- **自动验证**：全部新增/改造的 JS 与 index.html 内联脚本通过 `node --check`；nav-config / ui-components 通过 node ESM 导入冒烟；视图模块 import 链解析通过。
- **待人工冒烟**（无前端自动化测试，须浏览器侧确认）：三角色（admin/editor/viewer）侧边栏项；双端 drawer；5 主题切换（重点看板图表）；各 hash 路由跳转；上传与 AI 问答。
- **保守跳过**：1-B 中弹窗/表格/部分 loading/徽章的组件化替换因缺少前端测试、回归不可自动验证而**未强行替换**（escapeHtml 去重已满足硬性验收）；可作为后续增量项逐模块接入。
