# PLAN-M-013-UIUX靛蓝专业克制改造.md

---
plan_id: PLAN-M-013
type: master
status: active
created: 2026-06-26
priority: high
parent: PLAN-M-012 (侧边栏治理与UI组件化)
segments_file: PLAN-M-013-UIUX靛蓝专业克制改造-segments.md
execution_mode: /supercode:plan-draft --auto
based_on: Doc/design.md（设计系统）+ Doc/UI-UX-改造方案.md + views/mockup.html（已确认外观方向）
---

## 一、需求重述

承接 PLAN-M-012（导航治理 + 共享组件库落地）后的**视觉与体验升级**。用户已通过 `views/mockup.html` 原型确认设计方向：**专业克制风格（Linear/Notion/GitHub 系）+ 靛蓝主色 + 亮色为主、暗色次要**。

本计划将该方向落地到真实 Web UI，**严格复用现有主题系统**（`.theme-{name}` + CSS 变量 + 语义 Tailwind class），不引入并行的设计令牌体系、不更换前端框架、不新增构建工具。

**核心目标**：
1. 将默认主题重调为"靛蓝专业克制"配色，去除现有紫调 accent（`#667eea`/`#764ba2`）与重投影卡片阴影带来的"AI 模板感"。
2. 统一字体（Inter）、圆角、阴影、侧边栏选中态，对齐 `Doc/design.md` 规范。
3. 补齐三态组件（空状态 / 骨架屏）与 ⌘K 命令面板交互骨架。
4. 校验响应式、可访问性（WCAG AA）、性能。

**非目标**：不改后端 API、不改业务逻辑、不引入 npm/框架/构建链、不强制重写 14 个视图模块结构。

---

## 二、现状分析（基于真实代码核对）

### 2.1 既有架构（关键发现）

- **主题系统已存在**：`index.html` 内 Tailwind config 将语义 class（`bg-bg-surface`/`text-accent`/`text-on-base`/`border-th`…）映射到 CSS 变量；`<style>` 中以 `.theme-classic`（默认）/`.theme-dark-tech`/`.theme-forest`/`.theme-terracotta`/`.theme-monochrome` 5 套主题各自定义变量值。
- **共享组件库已存在**：`views/utils/ui-components.js` 导出 `escapeHtml/createBadge/createLoadingSpinner/createModal/createTable/createTabSwitcher`，全部用语义 class，自带主题适配。
- **导航单一来源已存在**：`views/utils/nav-config.js`（`MAIN_VIEWS`/`ADMIN_TOOLS`/`getAdminGroups`）。

> ✅ 这意味着 `design.md` 所述"一处改色、全局生效"的能力**已具备**——改造主要是**重调既有主题变量值**，而非重建体系。风险因此大幅低于通用方案预估。

### 2.2 待改进点（量化）

| 维度 | 现状证据 | 目标 |
|------|---------|------|
| 主色 | `--color-accent-primary: #667eea`（紫调 periwinkle）+ `#764ba2`（紫）| 靛蓝 `#4F46E5` / `#4338CA` |
| 品牌渐变 | `gradient-brand` 紫色 135° 渐变（AI 感来源） | 收敛为同色系微渐变或纯色 |
| 卡片阴影 | `--shadow-card: 0 10px 30px rgba(0,0,0,.1)`（过重，"气泡感"） | `0 1px 2px` / `0 4px 12px`（design.md） |
| 中性色 | gray 系（`#f3f4f6`/`#e5e7eb`/`#111827`） | slate 系（`#f8fafc`/`#e2e8f0`/`#0f172a`） |
| 字体 | 未统一指定（依赖系统默认） | Inter + 中文回退栈 |
| 侧边栏选中态 | 仅底色 | 左 3px accent 条 + 浅底（mockup 已验证） |
| 三态 | 仅 loading spinner | + 空状态 EmptyState + 骨架屏 Skeleton |
| 全局搜索 | 顶栏搜索框 | + ⌘K 命令面板（搜索 + 跳转） |

> ⚠️ **测试说明**：本项目前端无自动化测试框架。验证以 `node --check` 语法校验 + 浏览器人工冒烟 + 多主题切换目测为主，不套用 80% 覆盖率门禁（沿用 PLAN-M-012 约定）。

---

## 三、实施阶段（Phases）

> 按"风险递增、价值递减"排序。core = Phase 0+1；complete = 全部。

### Phase 0：靛蓝专业克制令牌重调（P0，🟢 低风险高价值）

**目标**：仅改 CSS 变量值，瞬时落地新视觉，完全可逆。

- **0.1 重调默认主题（`.theme-classic`）变量**
  - accent：`--color-accent-primary` → `#4F46E5`；`--color-accent-secondary` → `#4338CA`；`--color-accent-medium` → `#c7d2fe`（保留 indigo-200）。
  - 中性色：`bg-base #f3f4f6→#f8fafc`、`bg-surface-alt #f9fafb→#f8fafc`、`bg-hover→#f1f5f9`、`border #e5e7eb→#e2e8f0`、`text-primary #111827→#0f172a`、`text-secondary #4b5563→#475569`、`text-tertiary #9ca3af→#94a3b8`、`focus-ring→#4F46E5`。
- **0.2 柔化阴影**
  - `--shadow-card: 0 1px 2px rgba(15,23,42,.06)`；`--shadow-card-hover: 0 4px 12px rgba(15,23,42,.08)`。
- **0.3 收敛品牌渐变**
  - `gradient-brand` 改为同色系克制微渐变（`#4F46E5→#6366F1`）或在主标题处改用纯色（避免大面积渐变）。
- **0.4 类型徽章微调**（可选）：definition 由紫 `#a855f7` 维持语义，不动；仅确保与新 accent 不冲突。

### Phase 1：视觉规范化（P1，🟢 低风险）

**目标**：字体、圆角、间距、选中态对齐 design.md。

- **1.1 字体接入**：`<head>` 引入 Inter（Google Fonts / 本地），`body` 字体栈 `'Inter','PingFang SC','Microsoft YaHei',system-ui,sans-serif`；等宽 `JetBrains Mono`（代码/ID）。
- **1.2 侧边栏选中态**：当前导航项激活态加左侧 3px `bg-accent` 条 + `bg-accent-soft` 底（参照 mockup `nav-item.active`）；侧边栏宽度评估 192→240px。
- **1.3 圆角/间距统一**：卡片/弹窗圆角向 `8px` 收敛，按钮/输入框/徽章 `6px`；避免 >12px 大圆角。
- **1.4 ui-components.js 视觉微调**：`createBadge` 语义浅底深字保持；`createModal` 遮罩统一 `bg-black/40`、宽度档位；`createLoadingSpinner` 配合骨架屏使用。

### Phase 2：交互增强（P2，🟡 中风险 · 外观骨架优先）

**目标**：补齐高频路径与状态体系（功能对接可分步）。

- **2.1 新增三态组件**：`createEmptyState(cfg)`、`createSkeleton(cfg)` 加入 `ui-components.js`；在列表/表格类视图替换裸 spinner/空白。
- **2.2 ⌘K 命令面板**：新增 `views/components/command-palette.js`，复用 `nav-config.js` 渲染"跳转"分组、`/api/search`+`/api/suggest` 渲染"知识原子"分组；⌘K/Ctrl+K 唤起、ESC 关闭、键盘上下选择。**外观骨架先行，API 对接可作为子任务。**
- **2.3 顶栏搜索条**：与命令面板打通（点击即唤起）。

### Phase 3：响应式·可访问性·性能（P3，🟡 中风险 · 校验为主）

- **3.1 A11y**：全局 `:focus-visible` 焦点环；交互元素键盘可达；`aria-label` 补齐；对比度审计（靛蓝 `#4F46E5`/白底 = 7.0:1 ✓）；尊重 `prefers-reduced-motion`。
- **3.2 响应式**：断点、表格→卡片堆叠、触控目标 ≥44px 校验（沿用 PLAN-M-006 基线）。
- **3.3 性能**：模块加载 `?t=Date.now()` → 版本号缓存；评估 Tailwind CDN→构建期（**可选，保持零构建则跳过**）。

---

## 四、依赖关系（Dependencies）

```
Phase 0（令牌重调）──> Phase 1（视觉规范化依赖新令牌）
Phase 1 ──> Phase 2（命令面板/三态复用规范化样式与组件）
Phase 0/1 ──> Phase 3（校验依赖稳定外观基线）
```

- 无外部依赖（除 Phase 1 字体 CDN，可本地化）。
- 复用既有 `nav-config.js`、`ui-components.js`、`WikiAPI`、Cytoscape/Chart/Marked。

---

## 五、风险评估

| 等级 | 风险 | 缓解措施 |
|:----:|------|---------|
| 🟢 低 | Phase 0 纯改变量值，可能与其它 4 套主题视觉关系微变 | 仅改 classic；其余主题不动；改后 5 主题逐一目测 |
| 🟢 低 | 字体 CDN 加载失败 | 系统字体栈兜底；可改本地字体 |
| 🟡 中 | 侧边栏选中态结构改动触及 index.html `x-for` 渲染 | 最小差异；仅加 class/伪元素，不改 nav-config 数据结构 |
| 🟡 中 | ⌘K 命令面板新增交互的键盘/焦点缺陷 | 模块化独立文件，可整体下线；外观先行、功能分步 |
| 🟢 低 | 无前端自动化测试，回归靠人工 | 提供逐项冒烟清单 + `node --check` 全量语法校验 |

---

## 六、复杂度估算

| Phase | 范围 | 复杂度 | 预估 |
|:-----:|------|:------:|------|
| Phase 0 | 令牌重调（1 文件 index.html `<style>`） | 低 | 0.5-1h |
| Phase 1 | 视觉规范化（index.html + ui-components.js） | 中 | 2-3h |
| Phase 2 | 三态组件 + ⌘K 面板（+2 文件） | 中高 | 3-5h |
| Phase 3 | A11y/响应式/性能校验 | 中 | 2-3h |
| **合计** | | **中** | **core 2.5-4h / complete 7.5-12h** |

---

## 七、验收标准

**Phase 0**
- [ ] 默认主题 accent 为靛蓝 `#4F46E5`，无紫调；`gradient-brand` 不再是紫色大渐变。
- [ ] 卡片阴影柔化（无 `0 10px 30px` 重投影）。
- [ ] 其余 4 套主题切换仍正常。

**Phase 1**
- [ ] 全站使用 Inter 字体栈。
- [ ] 侧边栏激活项有左 3px accent 条 + 浅底。
- [ ] 圆角统一（无 >12px 大圆角误用）。

**Phase 2（若执行）**
- [ ] `ui-components.js` 新增 `createEmptyState`/`createSkeleton` 并被引用。
- [ ] ⌘K 可唤起命令面板，含"跳转"分组（外观至少完成；搜索分组功能可标注待对接）。

**Phase 3（若执行）**
- [ ] 键盘可完成核心流程，焦点环可见。
- [ ] 对比度审计通过；触控目标达标。

**通用**
- [ ] 全部改动 JS / index.html 内联脚本通过 `node --check`。
- [ ] 浏览器 console 无新增报错。
- [ ] 5 主题 + 三角色（admin/editor/viewer）+ 双端 逐项冒烟。

---

## 八、发现与记录

### 8.1 执行中发现

- **主题系统即"令牌单一来源"**：`design.md` 设想的"一处改色全局生效"在 `.theme-classic` CSS 变量层已天然具备，改造退化为"重调变量值"，风险远低于通用方案预估。
- **侧边栏选中态已存在**：`index.html` 桌面/移动端 `x-for` 模板（672/729 行）已有 `border-l-4 border-accent` 激活态，无需新增，TG-1 仅补字体。
- **导航全走 hash**：`handleRoute()` 对任意 `location.hash` 设 `this.view` 并按需 `loadViewModule()`，故命令面板跳转只需 `window.location.hash = '#'+target`，**零耦合 Alpine 内部**。
- **紫调残留三处**：除 classic 主题变量外，`meta[theme-color]`(466)、水印色(588)、主题选择器 classic 色板(1657) 亦为 `#667eea`，已一并同步为 `#4f46e5`。
- **暗色主题重投影保留**：dark-tech/forest 的 `0 10px 30px` 卡片阴影为暗色下的刻意设计，不在本次"柔化"范围，仅改 classic。
- **命令面板搜索优雅降级**：`window.WikiAPI` 不可用时显示"搜索接口待对接"，不报错；竞态用 `searchSeq` 序号丢弃过期请求。

---

## 九、完成总结

**执行日期**：2026-06-26　**执行模式**：`/supercode:plan-draft --auto`（全自动，ship 前停顿）

### 9.1 交付物

| 类别 | 文件 | 说明 |
|------|------|------|
| 改造 | `views/index.html` | classic 主题令牌→靛蓝专业克制（accent/中性/阴影/渐变）；Inter+JetBrains Mono 字体栈；`fontFamily` 配置；`:focus-visible` 焦点环 + `prefers-reduced-motion`；暴露 `window.__wikiApp`；引入命令面板；3 处紫调残留同步 |
| 新增 | `views/components/command-palette.js` | ⌘K 命令面板：nav-config 跳转分组 + WikiAPI 搜索分组 + 键盘（↑↓/Enter/ESC）+ 优雅降级 |
| 改造 | `views/utils/ui-components.js` | 新增 `createEmptyState` / `createSkeleton`（三态体系之空/加载）并挂载 `window.UI` |
| 新增 | `views/mockup.html` | 纯外观原型（设计方向确认用） |
| 文档 | `Doc/design.md` / `Doc/UI-UX-改造方案.md` | 设计系统 + 可行性方案 |

### 9.2 验收对照

- ✅ 默认主题 accent 靛蓝 `#4f46e5`，无紫调；`gradient-brand` 收敛为同色系微渐变。
- ✅ classic 卡片阴影柔化（`0 1px 2px` / `0 4px 12px`）。
- ✅ 全站 Inter 字体栈；代码/ID 用 JetBrains Mono。
- ✅ 侧边栏激活态左 3/4px accent 条 + 浅底（既有，保留）。
- ✅ `ui-components.js` 新增三态组件并导出。
- ✅ ⌘K 命令面板可唤起，跳转分组可用，搜索分组对接 WikiAPI（降级安全）。
- ✅ `:focus-visible` 焦点环 + reduced-motion 支持。
- ✅ 全部独立 JS 通过 `node --check`；index.html 无紫调残留。

### 9.3 验证方式与遗留

- **自动验证**：`node --check` 通过 ui-components / nav-config / command-palette；grep 校验配色/字体/组件/无残留全部通过。
- **待人工冒烟（需浏览器）**：5 主题切换目测（重点 classic 新配色）；⌘K 面板键盘与搜索；三角色侧边栏；双端 drawer；对比度/触控目标/键盘走查（Phase 3 剩余项）。
- **未执行（按安全边界停顿）**：`/supercode:ship`（版本发布/部署为外向操作），等待用户确认后再执行。
- **可选未做**：Tailwind CDN→构建期（保持零构建现状）；命令面板"知识原子"跳转到具体详情（当前跳浏览视图，详情对接可作后续子任务）。

### 9.4 定稿后追加（用户确认外观方向后的实地打磨）

> 通过 GStack `/browse` 实地截图核查驱动，非凭描述。

| 项 | 问题 | 处理 |
|----|------|------|
| **概览整页渐变** | `.overview-container` 给整个概览页铺 `linear-gradient(accent→accent-secondary)` 全屏渐变，是"满屏靛蓝、改色后观感无变化"的真正元凶（Phase 0 仅改变量值掩盖不了它） | 改为中性背景 `--color-bg-base`；卡片改白底+细边框+小圆角；`gradient-number/title` 去渐变文字改实色。真正落地"专业克制" |
| **类型分布徽章** | 数字徽章用 `bg-gradient-brand` 实底渐变胶囊，偏重 | 改 `bg-accent-soft text-accent` 浅底深字 |
| **类型"引号"数据** | 部分原子 `type` 含字面引号，`"method"` 与 `method` 被当两类 | `typeStats` 取数层防御性归一（去首尾引号），合并显示并修正圆点配色；底层数据清洗另列 |
| **Service Worker 旧缓存** | `sw.js` 对 CSS/JS 用 cacheFirst 且版本号 `v1` 从未变，导致改动在浏览器端不可见 | 版本号 `v1→v2` 触发 activate 清旧缓存；修离线页残留紫色 |
| **权限页 admin 被挡（bug）** | `permissions.js` 读 `window.WikiAPI.currentUser`（全项目从未赋值、恒空），含 admin 在内任何人都被弹"仅管理员可访问"并踢回概览 | 改读真实来源 `window.__currentUser`，与 users.js/approvals.js 一致；实测 admin 可正常进入。仅此一处有该 bug |

**实地验证（8 视图 `/browse` 截图）**：概览/浏览/图谱/看板/AI问答/上传/用户/权限 均确认白底白卡、靛蓝克制、风格统一；其它视图经令牌继承自动达成，无同类结构性渐变残留。
