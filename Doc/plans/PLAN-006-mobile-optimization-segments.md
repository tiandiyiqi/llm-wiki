# 任务组结构：PLAN-006 移动端优化

## 元信息
- 源计划：PLAN-006-mobile-optimization.md
- 创建时间：2026-06-23 21:31
- 任务组数量：8

---

## 任务组概览

| 任务组 | 名称 | 类型 | 子任务数 | 前置条件 |
|--------|------|------|----------|----------|
| A | 响应式基础设施 | 串行 | 3 | 无 |
| B | index.html 响应式布局 | 串行 | 4 | A |
| C | 页面级响应式改造（并行批次 1） | 并行 | 4 | B |
| D | 页面级响应式改造（并行批次 2） | 并行 | 4 | B |
| E | PWA 基础设施 | 并行 | 4 | C, D |
| F | index.html PWA 集成 | 串行 | 3 | E |
| G | 触摸优化与性能 | 并行 | 4 | F |
| H | 测试与验证 | 串行 | 3 | G |

---

## 依赖分析

### 文件冲突矩阵

| 文件 | 涉及任务组 | 冲突处理 |
|------|-----------|----------|
| `views/index.html` | B, F, G | 串行执行，按 B→F→G 顺序修改 |
| `views/login.html` | C | 仅 C 涉及，无冲突 |
| `views/js/auth.js` | F | 仅 F 涉及，无冲突 |
| `views/graph.js` | D | 仅 D 涉及，无冲突 |
| `views/components/*.html` | C | C 内部并行需注意，但各组件独立 |
| `views/admin/*.html` | D | D 内部并行需注意，但各页面独立 |
| `lib/web_server.py` | G | 仅 G 涉及，无冲突 |

### 并行机会

1. **任务组 C 与 D 可并行**：C 处理 login/components/search，D 处理 admin 页面，文件无交叉
2. **任务组 E 内部并行**：manifest.json、sw.js、icons 创建互不依赖
3. **任务组 G 内部部分并行**：4.1(触摸) 和 4.3(API) 可并行，4.2(index.html) 需等 F 完成

### 与 PLAN-005 的协调

- `views/login.html` 同时有 SSO（PLAN-005）和响应式（PLAN-006）修改
- **策略**：PLAN-005 的 login.html 修改应先完成，PLAN-006 的 C-1 在 PLAN-005 完成后再执行
- `views/sso-callback.html` 不在本计划修改范围内

---

## 执行顺序

### 任务组 A：响应式基础设施
**类型：** 串行
**前置条件：** 无

#### 任务 A-1：创建全局响应式工具样式
- [x] SUB-TASK-001: 创建 `views/css/responsive.css`，包含移动端优先断点定义、mobile-only/desktop-only 工具类、安全区域适配（刘海屏 env()）、触摸目标最小尺寸（44px）、移动端滚动优化（-webkit-overflow-scrolling: touch）
  - **依赖：** 无
  - **涉及文件：** `views/css/responsive.css`（新建）
  - **复杂度：** 低
  - **测试策略：** 测试后行（CSS 配置/工具类，无业务逻辑）
  - **预估时间：** 3 分钟

#### 任务 A-2：创建移动端侧边栏组件
- [x] SUB-TASK-002: 创建 `views/components/mobile-sidebar.html`，实现桌面端固定侧边栏不变 + 移动端汉堡菜单触发抽屉式侧边栏（左滑出）+ 遮罩层点击关闭 + 手势滑动关闭，使用 Alpine.js 控制状态
  - **依赖：** SUB-TASK-001（需要 responsive.css 中的 mobile-only/desktop-only 类）
  - **涉及文件：** `views/components/mobile-sidebar.html`（新建）
  - **复杂度：** 中
  - **测试策略：** 测试后行（UI 组件，需浏览器验证交互行为）
  - **预估时间：** 5 分钟

#### 任务 A-3：在 index.html 中引入 responsive.css
- [x] SUB-TASK-003: 在 `views/index.html` 的 `<head>` 中添加 `<link rel="stylesheet" href="/css/responsive.css">`，确保在 Tailwind CDN 之后加载
  - **依赖：** SUB-TASK-001
  - **涉及文件：** `views/index.html`
  - **复杂度：** 低
  - **测试策略：** 仅手动验证（单行配置引入）
  - **预估时间：** 1 分钟

---

### 任务组 B：index.html 响应式布局
**类型：** 串行
**前置条件：** 任务组 A 完成

> index.html 有 2258 行，修改需渐进式进行。本任务组仅处理 Phase 1 的响应式布局修改，PWA 相关修改在任务组 F 中进行。

#### 任务 B-1：侧边栏响应式改造
- [x] SUB-TASK-004: 修改 `views/index.html` 中侧边栏相关样式：将 `ml-48` 改为 `lg:ml-48 ml-0`，将侧边栏 `w-48` 改为 `lg:w-48`，添加 `hidden lg:block` 使移动端隐藏固定侧边栏
  - **依赖：** SUB-TASK-002（需要 mobile-sidebar.html 组件已创建）
  - **涉及文件：** `views/index.html`
  - **复杂度：** 中
  - **测试策略：** 测试后行（布局修改，需浏览器验证不同断点下的表现）
  - **预估时间：** 3 分钟

#### 任务 B-2：网格布局响应式改造
- [x] SUB-TASK-005: 修改 `views/index.html` 中所有硬编码网格列数：`grid-cols-4` 改为 `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`，`grid-cols-3` 改为 `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
  - **依赖：** 无（与 B-1 无文件内顺序依赖，但同文件需串行）
  - **涉及文件：** `views/index.html`
  - **复杂度：** 中
  - **测试策略：** 测试后行（布局修改，需多断点验证）
  - **预估时间：** 3 分钟

#### 任务 B-3：添加移动端顶部导航栏
- [x] SUB-TASK-006: 在 `views/index.html` 的 `<body>` 开头添加移动端顶部导航栏（汉堡菜单按钮 + LLM Wiki 标题 + 搜索图标 + 用户头像），使用 `mobile-only` 类控制仅移动端显示，汉堡菜单通过 Alpine.js 控制侧边栏抽屉开关
  - **依赖：** SUB-TASK-002（需要 mobile-sidebar 组件的 Alpine.js 状态）
  - **涉及文件：** `views/index.html`
  - **复杂度：** 中
  - **测试策略：** 测试后行（UI 组件，需浏览器验证交互）
  - **预估时间：** 4 分钟

#### 任务 B-4：引入 mobile-sidebar 组件
- [x] SUB-TASK-007: 在 `views/index.html` 中引入 `views/components/mobile-sidebar.html` 的内容（通过服务端 include 或内联方式），确保移动端抽屉侧边栏可用
  - **依赖：** SUB-TASK-002, SUB-TASK-006
  - **涉及文件：** `views/index.html`
  - **复杂度：** 低
  - **测试策略：** 仅手动验证（组件引入，需浏览器验证渲染）
  - **预估时间：** 2 分钟

---

### 任务组 C：页面级响应式改造（并行批次 1）
**类型：** 并行
**前置条件：** 任务组 B 完成

> 本批次处理 login、components、search 页面。各子任务修改不同文件，可并行执行。

#### 任务 C-1：login.html 响应式改造
- [x] SUB-TASK-008: 修改 `views/login.html`：登录卡片居中 + 最大宽度约束（max-w-md mx-auto）、SSO 按钮区域响应式排列（flex-col sm:flex-row）、输入框全宽适配（w-full）
  - **依赖：** 任务组 B（需要 responsive.css 已加载），PLAN-005 的 login.html 修改已完成
  - **涉及文件：** `views/login.html`
  - **复杂度：** 低
  - **测试策略：** 测试后行（布局修改，需浏览器验证）
  - **预估时间：** 3 分钟

#### 任务 C-2：image-picker + image-upload 组件响应式
- [x] SUB-TASK-009: 修改 `views/components/image-picker.html`（网格列数响应式 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4）和 `views/components/image-upload.html`（上传区域全宽、按钮响应式排列）
  - **依赖：** 任务组 A（需要 responsive.css）
  - **涉及文件：** `views/components/image-picker.html`, `views/components/image-upload.html`
  - **复杂度：** 低
  - **测试策略：** 测试后行（布局修改）
  - **预估时间：** 3 分钟

#### 任务 C-3：pdf-viewer + search-box 组件响应式
- [x] SUB-TASK-010: 修改 `views/components/pdf-viewer.html`（移动端全屏模态、工具栏折叠）和 `views/components/search-box.html`（搜索输入框全宽、下拉结果响应式、移动端底部弹出式菜单）
  - **依赖：** 任务组 A（需要 responsive.css）
  - **涉及文件：** `views/components/pdf-viewer.html`, `views/components/search-box.html`
  - **复杂度：** 中
  - **测试策略：** 测试后行（布局修改 + 模态框交互）
  - **预估时间：** 4 分钟

#### 任务 C-4：搜索结果页响应式
- [x] SUB-TASK-011: 修改 `views/search/results.html`：搜索结果卡片式布局（grid-cols-1 sm:grid-cols-2 lg:grid-cols-3）、筛选栏移动端折叠、分页组件响应式
  - **依赖：** 任务组 A（需要 responsive.css）
  - **涉及文件：** `views/search/results.html`
  - **复杂度：** 中
  - **测试策略：** 测试后行（布局修改）
  - **预估时间：** 3 分钟

---

### 任务组 D：页面级响应式改造（并行批次 2）
**类型：** 并行
**前置条件：** 任务组 B 完成

> 本批次处理 admin 页面和 graph.js。各子任务修改不同文件，可并行执行。admin 页面按复杂度分组。

#### 任务 D-1：admin 简单页面响应式（≤300 行）
- [x] SUB-TASK-012: 修改 `views/admin/` 下简单页面（audit.html 240行、duplicates.html 237行、notifications.html 219行、quality.html 220行、shares.html 268行、upload.html 257行、webhooks.html 292行）：表格→移动端卡片布局、表单全宽垂直排列、操作按钮响应式
  - **依赖：** 任务组 A（需要 responsive.css）
  - **涉及文件：** `views/admin/audit.html`, `views/admin/duplicates.html`, `views/admin/notifications.html`, `views/admin/quality.html`, `views/admin/shares.html`, `views/admin/upload.html`, `views/admin/webhooks.html`
  - **复杂度：** 中
  - **测试策略：** 测试后行（布局修改，批量处理相似模式）
  - **预估时间：** 5 分钟

#### 任务 D-2：admin 中等页面响应式（300-450 行）
- [x] SUB-TASK-013: 修改 `views/admin/` 下中等页面（approvals.html 343行、edit.html 306行、qa.html 385行、users.html 441行）：表格→卡片布局 + 侧边导航折叠 + FAB 按钮
  - **依赖：** 任务组 A（需要 responsive.css）
  - **涉及文件：** `views/admin/approvals.html`, `views/admin/edit.html`, `views/admin/qa.html`, `views/admin/users.html`
  - **复杂度：** 中
  - **测试策略：** 测试后行（布局修改）
  - **预估时间：** 4 分钟

#### 任务 D-3：admin 复杂页面响应式（>450 行）
- [x] SUB-TASK-014: 修改 `views/admin/` 下复杂页面（dashboard.html 359行但已有响应式基础需审查、kb-management.html 832行、permissions.html 823行）：kb-management 和 permissions 需要侧边导航→移动端标签式导航、复杂表格→卡片列表、FAB 按钮
  - **依赖：** 任务组 A（需要 responsive.css）
  - **涉及文件：** `views/admin/dashboard.html`, `views/admin/kb-management.html`, `views/admin/permissions.html`
  - **复杂度：** 高
  - **测试策略：** TDD（复杂度高 + 大文件修改出错代价大，先定义响应式断点测试用例）
  - **预估时间：** 5 分钟

#### 任务 D-4：知识图谱触摸手势 + media 响应式
- [x] SUB-TASK-015: 修改 `views/graph.js`（启用 Cytoscape.js 触摸交互：捏合缩放 pinchZoom、单指拖拽、双击聚焦节点）和 `views/media/gallery.html`（网格响应式 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4、图片懒加载）
  - **依赖：** 任务组 A（需要 responsive.css）
  - **涉及文件：** `views/graph.js`, `views/media/gallery.html`
  - **复杂度：** 高
  - **测试策略：** TDD（Cytoscape.js 触摸交互是核心功能逻辑，需验证手势行为）
  - **预估时间：** 5 分钟

---

### 任务组 E：PWA 基础设施
**类型：** 并行
**前置条件：** 任务组 C、D 完成

> PWA 基础文件的创建互不依赖，可并行执行。但 index.html 的修改集中在任务组 F 中串行处理。

#### 任务 E-1：创建 Web App Manifest
- [x] SUB-TASK-016: 创建 `views/manifest.json`，包含 name/short_name/description/start_url/display/background_color/theme_color/icons/shortcuts 字段，图标路径指向 `/icons/` 目录
  - **依赖：** 无
  - **涉及文件：** `views/manifest.json`（新建）
  - **复杂度：** 低
  - **测试策略：** 测试后行（JSON 配置文件，需 Lighthouse 验证）
  - **预估时间：** 2 分钟

#### 任务 E-2：创建 PWA 图标
- [x] SUB-TASK-017: 创建 `views/icons/` 目录，生成 PWA 图标文件：icon-192.png、icon-512.png、icon-maskable-192.png、icon-maskable-512.png（使用 SVG 源文件 + 命令行工具转换，或使用 placeholder 图标）
  - **依赖：** 无
  - **涉及文件：** `views/icons/icon-192.png`（新建）, `views/icons/icon-512.png`（新建）, `views/icons/icon-maskable-192.png`（新建）, `views/icons/icon-maskable-512.png`（新建）
  - **复杂度：** 低
  - **测试策略：** 仅手动验证（图片资源文件）
  - **预估时间：** 3 分钟

#### 任务 E-3：创建 Service Worker
- [x] SUB-TASK-018: 创建 `views/sw.js`，实现三种缓存策略：HTML 页面 Network First（优先网络，离线降级缓存）、CSS/JS/CDN/图片/字体 Cache First（缓存优先）、API 请求 Network Only（始终从服务器获取），包含 install 事件预缓存静态资源、activate 事件清理旧缓存、fetch 事件路由分发
  - **依赖：** 无
  - **涉及文件：** `views/sw.js`（新建）
  - **复杂度：** 高
  - **测试策略：** TDD（缓存策略是核心逻辑，需验证 Network First/Cache First/Network Only 行为）
  - **预估时间：** 5 分钟

#### 任务 E-4：添加 web_server.py 的 manifest/sw.js 路由
- [x] SUB-TASK-019: 修改 `lib/web_server.py`，添加 `/manifest.json` 和 `/sw.js` 的路由处理，确保 Content-Type 正确（application/manifest+json 和 application/javascript），添加 `/icons/` 静态文件路由
  - **依赖：** SUB-TASK-016, SUB-TASK-018（需要文件已创建才能测试路由）
  - **涉及文件：** `lib/web_server.py`
  - **复杂度：** 中
  - **测试策略：** TDD（API 路由层修改，需验证 Content-Type 和路由可达性）
  - **预估时间：** 3 分钟

---

### 任务组 F：index.html PWA 集成
**类型：** 串行
**前置条件：** 任务组 E 完成

> index.html 在任务组 B 中已做响应式修改，本任务组继续添加 PWA 相关内容。由于所有修改都在同一文件，必须串行执行。

#### 任务 F-1：添加 manifest link 和主题色
- [x] SUB-TASK-020: 在 `views/index.html` 的 `<head>` 中添加 `<link rel="manifest" href="/manifest.json">` 和 `<meta name="theme-color" content="#1e40af">`，添加 Apple PWA 兼容 meta 标签（apple-mobile-web-app-capable、apple-mobile-web-app-status-bar-style）
  - **依赖：** SUB-TASK-016（manifest.json 已创建）
  - **涉及文件：** `views/index.html`
  - **复杂度：** 低
  - **测试策略：** 仅手动验证（HTML meta 标签配置）
  - **预估时间：** 2 分钟

#### 任务 F-2：添加 Service Worker 注册脚本
- [x] SUB-TASK-021: 在 `views/index.html` 的 `</body>` 前添加 Service Worker 注册脚本：检测 `navigator.serviceWorker` 支持、注册 `/sw.js`、处理注册成功/失败日志
  - **依赖：** SUB-TASK-018（sw.js 已创建）
  - **涉及文件：** `views/index.html`
  - **复杂度：** 低
  - **测试策略：** 测试后行（脚本注册，需浏览器 DevTools 验证 SW 状态）
  - **预估时间：** 2 分钟

#### 任务 F-3：添加 PWA 安装提示
- [x] SUB-TASK-022: 修改 `views/js/auth.js`，添加 `beforeinstallprompt` 事件监听器，保存 deferredPrompt，实现 `showInstallBanner()` 函数（在页面顶部显示"安装到桌面"横幅），用户点击后调用 `deferredPrompt.prompt()`
  - **依赖：** SUB-TASK-020（manifest 已链接）
  - **涉及文件：** `views/js/auth.js`
  - **复杂度：** 中
  - **测试策略：** TDD（PWA 安装是 API 契约级别的功能，需验证事件处理逻辑）
  - **预估时间：** 4 分钟

---

### 任务组 G：触摸优化与性能
**类型：** 并行
**前置条件：** 任务组 F 完成

> 触摸优化（G-1）和 API 优化（G-3）修改不同文件可并行。性能优化（G-2）修改 index.html 需在 F 之后串行，但可与 G-1/G-3 并行。G-4 依赖 G-2。

#### 任务 G-1：触摸优化（index.html + components）
- [x] SUB-TASK-023: 修改 `views/index.html` 和 `views/components/` 下的组件：所有可点击元素添加最小尺寸 44x44px（.touch-target 类）、按钮间距 gap-2→gap-3、链接区域扩展 inline→inline-block p-1、添加 touch-action: manipulation 消除 300ms 延迟
  - **依赖：** 任务组 F（index.html PWA 修改已完成）
  - **涉及文件：** `views/index.html`, `views/components/image-picker.html`, `views/components/image-upload.html`, `views/components/search-box.html`
  - **复杂度：** 中
  - **测试策略：** 测试后行（UI 样式优化，需设备验证触摸体验）
  - **预估时间：** 4 分钟

#### 任务 G-2：移动端性能优化（index.html）
- [x] SUB-TASK-024: 修改 `views/index.html`：图片添加 `loading="lazy"`、CDN 资源添加 `defer`/`async`、Cytoscape.js 改为按需加载（仅在图谱页面加载）、减少首屏 DOM 节点（侧边栏懒渲染）
  - **依赖：** 任务组 F（index.html PWA 修改已完成）
  - **涉及文件：** `views/index.html`
  - **复杂度：** 中
  - **测试策略：** 测试后行（性能优化，需 Lighthouse 对比验证）
  - **预估时间：** 4 分钟

#### 任务 G-3：移动端专用 API 优化
- [x] SUB-TASK-025: 修改 `lib/web_server.py`：添加移动端检测（User-Agent 或 Sec-CH-UA-Mobile 请求头）、移动端请求返回精简数据（减少字段）、图片返回缩略图（利用已有 thumbnail.py）
  - **依赖：** 无（与 G-1/G-2 修改不同文件）
  - **涉及文件：** `lib/web_server.py`
  - **复杂度：** 高
  - **测试策略：** TDD（API 层修改 + 数据处理/转换逻辑，需验证移动端检测和精简数据输出）
  - **预估时间：** 5 分钟

#### 任务 G-4：responsive.css 补充触摸和性能样式
- [x] SUB-TASK-026: 在 `views/css/responsive.css` 中补充：touch-action 工具类（.touch-manipulation、.touch-pan-x 等）、懒加载占位样式、移动端性能相关 CSS（will-change、contain）
  - **依赖：** SUB-TASK-023, SUB-TASK-024（需要确认实际使用的工具类）
  - **涉及文件：** `views/css/responsive.css`
  - **复杂度：** 低
  - **测试策略：** 仅手动验证（CSS 工具类补充）
  - **预估时间：** 2 分钟

---

### 任务组 H：测试与验证
**类型：** 串行
**前置条件：** 任务组 G 完成

#### 任务 H-1：浏览器兼容性测试
- [x] SUB-TASK-027: 执行浏览器兼容性测试矩阵：iPhone 14+ Safari（必须）、Android 13+ Chrome（必须）、iPhone SE Safari（应该）、Android 11+ Chrome（应该）、iPad Safari（应该），验证所有页面在 375px-2560px 宽度范围内正常显示
  - **依赖：** 任务组 G（所有代码修改已完成）
  - **涉及文件：** 无（测试活动）
  - **复杂度：** 中
  - **测试策略：** 仅手动验证（跨设备手动测试）
  - **预估时间：** 5 分钟

#### 任务 H-2：PWA Lighthouse 审计
- [x] SUB-TASK-028: 使用 Chrome Lighthouse 执行 PWA 审计，目标得分：Performance >= 80、Accessibility >= 90、Best Practices >= 90、SEO >= 80、PWA >= 80，记录得分并修复未达标项
  - **依赖：** SUB-TASK-027（基础兼容性已验证）
  - **涉及文件：** 可能涉及修复文件
  - **复杂度：** 中
  - **测试策略：** 仅手动验证（Lighthouse 自动化审计 + 手动修复）
  - **预估时间：** 5 分钟

#### 任务 H-3：文档更新
- [x] SUB-TASK-029: 更新 `Doc/plans/PLAN-000-enterprise-overall-plan.md` 中阶段 3.5 的进度状态，标记 PLAN-006 为已完成
  - **依赖：** SUB-TASK-028（审计通过）
  - **涉及文件：** `Doc/plans/PLAN-000-enterprise-overall-plan.md`
  - **复杂度：** 低
  - **测试策略：** 仅手动验证（文档更新）
  - **预估时间：** 2 分钟

---

## 执行顺序可视化

```
1️⃣ 任务组 A（响应式基础设施）
   ├─ A-1：创建 responsive.css
   ├─ A-2：创建 mobile-sidebar.html
   └─ A-3：index.html 引入 responsive.css
       ↓
2️⃣ 任务组 B（index.html 响应式布局）
   ├─ B-1：侧边栏响应式
   ├─ B-2：网格布局响应式
   ├─ B-3：移动端顶部导航栏
   └─ B-4：引入 mobile-sidebar 组件
       ↓
3️⃣ 任务组 C（页面改造批次 1）  ← 与 D 并行
   ├─ C-1：login.html 响应式
   ├─ C-2：image-picker + image-upload 响应式
   ├─ C-3：pdf-viewer + search-box 响应式
   └─ C-4：搜索结果页响应式

3️⃣ 任务组 D（页面改造批次 2）  ← 与 C 并行
   ├─ D-1：admin 简单页面响应式（7个文件）
   ├─ D-2：admin 中等页面响应式（4个文件）
   ├─ D-3：admin 复杂页面响应式（3个文件）
   └─ D-4：知识图谱触摸 + gallery 响应式
       ↓
4️⃣ 任务组 E（PWA 基础设施）
   ├─ E-1：创建 manifest.json
   ├─ E-2：创建 PWA 图标
   ├─ E-3：创建 Service Worker
   └─ E-4：web_server.py 路由
       ↓
5️⃣ 任务组 F（index.html PWA 集成）
   ├─ F-1：添加 manifest link + 主题色
   ├─ F-2：添加 SW 注册脚本
   └─ F-3：添加 PWA 安装提示
       ↓
6️⃣ 任务组 G（触摸优化与性能）
   ├─ G-1：触摸优化（index.html + components）
   ├─ G-2：性能优化（index.html）
   ├─ G-3：API 优化（web_server.py）
   └─ G-4：responsive.css 补充
       ↓
7️⃣ 任务组 H（测试与验证）
   ├─ H-1：浏览器兼容性测试
   ├─ H-2：PWA Lighthouse 审计
   └─ H-3：文档更新
```

---

## 测试策略汇总

| 测试策略 | 子任务数 | 子任务 ID |
|----------|----------|-----------|
| TDD | 5 | SUB-TASK-014, SUB-TASK-015, SUB-TASK-018, SUB-TASK-022, SUB-TASK-025 |
| 测试后行 | 16 | SUB-TASK-001, SUB-TASK-002, SUB-TASK-004, SUB-TASK-005, SUB-TASK-006, SUB-TASK-008, SUB-TASK-009, SUB-TASK-010, SUB-TASK-011, SUB-TASK-012, SUB-TASK-013, SUB-TASK-021, SUB-TASK-023, SUB-TASK-024 |
| 仅手动验证 | 8 | SUB-TASK-003, SUB-TASK-007, SUB-TASK-017, SUB-TASK-020, SUB-TASK-026, SUB-TASK-027, SUB-TASK-028, SUB-TASK-029 |

### TDD 任务判断依据

| 子任务 | 命中信号 | 说明 |
|--------|---------|------|
| SUB-TASK-014 (admin 复杂页面) | 信号5：复杂度为高 | 832行+823行大文件修改，出错代价大 |
| SUB-TASK-015 (知识图谱触摸) | 信号1：核心业务逻辑 + 信号2：数据处理/转换 | Cytoscape.js 触摸交互是核心功能，涉及手势计算/转换 |
| SUB-TASK-018 (Service Worker) | 信号1：核心业务逻辑 + 信号5：复杂度为高 | 缓存策略是 PWA 核心逻辑，策略错误影响全局 |
| SUB-TASK-022 (PWA 安装提示) | 信号4：API 契约 | beforeinstallprompt 是浏览器 API 契约，需验证事件处理 |
| SUB-TASK-025 (移动端 API) | 信号1：核心业务逻辑 + 信号2：数据处理/转换 + 信号4：API 层 | web_server.py 修改涉及 API 层 + 数据精简转换逻辑 |

---

## 关键风险与缓解

| 风险 | 影响任务组 | 缓解措施 |
|------|-----------|----------|
| index.html 多次修改冲突 | B, F, G | 严格按 B→F→G 顺序串行修改，每次修改后验证 |
| PLAN-005 login.html 冲突 | C | C-1 需等待 PLAN-005 的 login.html 修改完成后再执行 |
| kb-management.html 832行修改困难 | D | D-3 标记为 TDD，先定义测试用例再修改 |
| Service Worker 缓存策略错误 | E | E-3 标记为 TDD，版本化缓存名 + 强制更新机制 |
| iOS PWA 兼容性不完整 | H | H-1 优先测试 iOS Safari，记录已知限制 |
