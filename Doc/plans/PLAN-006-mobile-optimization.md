---
name: PLAN-006-mobile-optimization
description: 阶段 3.5 — 移动端优化实施计划（响应式设计 + PWA）
priority: P2
status: draft
created: 2026-06-23
updated: 2026-06-23
---

# PLAN-006 - 移动端优化实施计划

> **所属项目**：PLAN-000 企业化改造
> **阶段**：3.5 移动端优化
> **当前完成度**：0%
> **预估周期**：3-4 周
> **前置依赖**：阶段 1 已完成；建议阶段 3.1-3.4 部分完成后再启动

---

## 一、需求重述

### 1.1 核心需求

对 llm-wiki 的 Web 前端进行移动端优化，包括响应式布局重构和 PWA 支持，使其在手机和平板上具备良好的使用体验。

### 1.2 功能要求

1. **响应式布局**：所有页面适配手机/平板/桌面三种尺寸
2. **移动端导航**：汉堡菜单 + 抽屉式侧边栏
3. **触摸优化**：触摸友好的按钮/链接/手势操作
4. **PWA 支持**：可安装到桌面、离线缓存、推送通知预留
5. **性能优化**：首屏加载速度、图片懒加载、代码按需加载

### 1.3 约束条件

| 约束项 | 要求 |
|--------|------|
| 无构建步骤 | 保持纯 HTML + CDN 的技术栈，不引入 npm/webpack |
| 渐进增强 | 桌面端体验不降级，移动端渐进增强 |
| 向后兼容 | 旧浏览器基础可用，现代浏览器完整体验 |
| 与 SSO 兼容 | 移动端登录需同时支持本地登录和 SSO（PLAN-005） |

---

## 二、现状分析

### 2.1 当前前端技术栈

| 技术 | 用途 | 移动端友好度 |
|------|------|:----------:|
| Tailwind CSS (CDN) | 样式框架 | ✅ 原生支持响应式 |
| Alpine.js (CDN) | 轻量交互框架 | ✅ 无 DOM 依赖 |
| Cytoscape.js | 知识图谱 | ⚠️ 需要触摸适配 |
| PDF.js | PDF 预览 | ⚠️ 移动端体验差 |
| 自定义 ThreadingHTTPServer | 后端 | ✅ 与前端无关 |

### 2.2 当前移动端问题清单

| 页面 | 问题 | 严重程度 |
|------|------|:--------:|
| `views/index.html` | `grid-cols-4` 硬编码，小屏幕溢出 | 🔴 高 |
| `views/index.html` | 侧边栏 `ml-48` 固定偏移，手机不可用 | 🔴 高 |
| `views/index.html` | 水平导航栏 `space-x-3`，手机溢出 | 🔴 高 |
| `views/index.html` | 操作按钮过小，触摸不友好 | 🟡 中 |
| `views/login.html` | 基本可用，但缺乏 SSO 按钮（PLAN-005） | 🟡 中 |
| `views/admin/*` | `dashboard.html` 有响应式，其他页面硬编码 | 🟡 中 |
| `views/components/*` | 大部分无响应式 | 🟡 中 |
| `views/graph.js` | 知识图谱无触摸手势 | 🟡 中 |
| 全局 | 无 manifest.json / Service Worker | 🟡 中 |
| 全局 | 无 PWA 安装支持 | 🟡 中 |

### 2.3 已有的响应式基础

- ✅ 所有页面都有 `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
- ✅ `views/admin/dashboard.html` 正确使用了 Tailwind 响应式前缀（`md:grid-cols-4`、`lg:grid-cols-2`）
- ✅ `views/components/image-picker.html` 有 `@media (max-width: 640px)` 查询
- ✅ Tailwind CSS 原生支持 `sm:` / `md:` / `lg:` / `xl:` 断点

---

## 三、实施阶段

### Phase 1：响应式布局基础（1 周）

**目标**：建立响应式设计基础设施，修复最严重的布局问题

#### 步骤 1.1：创建全局响应式工具

- **创建文件**：`views/css/responsive.css`
- **内容**：
  ```css
  /* 移动端优先断点 */
  /* sm: 640px, md: 768px, lg: 1024px, xl: 1280px */

  /* 隐藏/显示工具类 */
  .mobile-only { display: none; }
  .desktop-only { display: block; }
  @media (max-width: 767px) {
    .mobile-only { display: block; }
    .desktop-only { display: none; }
  }

  /* 移动端安全区域（刘海屏） */
  @supports (padding: env(safe-area-inset-top)) {
    .safe-area-top { padding-top: env(safe-area-inset-top); }
    .safe-area-bottom { padding-bottom: env(safe-area-inset-bottom); }
  }

  /* 触摸优化 */
  .touch-target { min-height: 44px; min-width: 44px; }

  /* 移动端滚动优化 */
  .smooth-scroll { -webkit-overflow-scrolling: touch; scroll-behavior: smooth; }
  ```

#### 步骤 1.2：响应式侧边栏组件

- **创建文件**：`views/components/mobile-sidebar.html`
- **功能**：
  1. 桌面端：固定侧边栏（现有行为不变）
  2. 移动端：汉堡菜单触发 → 抽屉式侧边栏（左滑出）
  3. 遮罩层点击关闭
  4. 支持手势滑动关闭

- **UI 设计**：
  ```
  桌面端 (≥1024px):
  ┌──────┬──────────────────────┐
  │      │                      │
  │ 侧边 │     主内容区         │
  │  栏  │                      │
  │      │                      │
  └──────┴──────────────────────┘

  移动端 (<768px):
  ┌─────────────────────────┐
  │ ☰  LLM Wiki    🔍 👤   │ ← 顶部导航栏
  ├─────────────────────────┤
  │                         │
  │    主内容区              │
  │    (全宽)               │
  │                         │
  └─────────────────────────┘

  汉堡菜单展开:
  ┌─────────┬──────────────┐
  │ ☰ 关闭  │              │
  │─────────│   遮罩层     │
  │ 📁 KB1  │              │
  │ 📁 KB2  │              │
  │ 📁 KB3  │              │
  │─────────│              │
  │ ⚙️ 设置 │              │
  └─────────┴──────────────┘
  ```

#### 步骤 1.3：修复 index.html 布局

- **修改文件**：`views/index.html`
- **修改点**：
  1. 侧边栏：`ml-48` → 响应式 `lg:ml-48 ml-0`
  2. 侧边栏本身：`w-48` → `lg:w-48 w-0 lg:block hidden`，移动端用抽屉替代
  3. 网格布局：`grid-cols-4` → `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`
  4. `grid-cols-3` → `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
  5. 添加移动端顶部导航栏（汉堡菜单 + 标题 + 搜索 + 用户头像）

---

### Phase 2：页面级响应式改造（1 周）

**目标**：逐页修复响应式布局

#### 步骤 2.1：login.html 响应式

- **修改文件**：`views/login.html`
- **修改点**：
  1. 登录卡片居中 + 最大宽度约束
  2. SSO 按钮区域响应式排列
  3. 输入框全宽适配

#### 步骤 2.2：admin/ 管理页面

- **修改文件**：`views/admin/` 下所有页面
- **修改点**：
  1. 表格 → 移动端卡片布局（`<table>` → 卡片列表）
  2. 表单 → 全宽输入 + 垂直排列
  3. 侧边导航 → 移动端折叠/标签式导航
  4. 操作按钮 → 移动端浮动操作按钮 (FAB)

#### 步骤 2.3：components/ 组件

- **修改文件**：`views/components/` 下所有组件
- **修改点**：
  1. `image-picker.html` — 网格列数响应式
  2. 模态框 → 移动端全屏模态
  3. 下拉菜单 → 移动端底部弹出式菜单

#### 步骤 2.4：搜索和知识图谱

- **修改文件**：`views/search/results.html`、`views/graph.js`
- **修改点**：
  1. 搜索结果 → 卡片式布局
  2. 知识图谱 → 触摸手势（捏合缩放、单指拖拽）
  3. Cytoscape.js 启用触摸交互

---

### Phase 3：PWA 支持（1 周）

**目标**：实现 PWA 安装和离线缓存

#### 步骤 3.1：Web App Manifest

- **创建文件**：`views/manifest.json`
- **内容**：
  ```json
  {
    "name": "LLM Wiki",
    "short_name": "LLM Wiki",
    "description": "企业级知识管理系统",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#1e40af",
    "icons": [
      { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
      { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
      { "src": "/icons/icon-maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
      { "src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
    ],
    "categories": ["productivity", "utilities"],
    "shortcuts": [
      { "name": "搜索", "url": "/?action=search" },
      { "name": "新建原子", "url": "/?action=create" }
    ]
  }
  ```

- **创建文件**：`views/icons/` — PWA 图标（使用 SVG 生成 192/512 尺寸）
- **修改文件**：`views/index.html` — `<link rel="manifest" href="/manifest.json">`

#### 步骤 3.2：Service Worker

- **创建文件**：`views/sw.js`
- **缓存策略**：
  | 资源类型 | 策略 | 说明 |
  |----------|------|------|
  | HTML 页面 | Network First | 优先网络，离线降级缓存 |
  | CSS/JS/CDN | Cache First | 缓存优先，减少请求 |
  | API 请求 | Network Only | 数据始终从服务器获取 |
  | 图片 | Cache First | 缓存优先，节省流量 |
  | 字体 | Cache First | 缓存优先 |

- **内容**：
  ```javascript
  const CACHE_NAME = 'llm-wiki-v1';
  const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/login.html',
    '/css/responsive.css',
    '/js/auth.js',
    '/manifest.json',
  ];
  const CDN_ASSETS = [
    'https://cdn.tailwindcss.com',  // 仅缓存编译后的 CSS
    'https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js',
  ];

  // Install: 预缓存静态资源
  self.addEventListener('install', (event) => { ... });

  // Activate: 清理旧缓存
  self.addEventListener('activate', (event) => { ... });

  // Fetch: 路由策略
  self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    if (url.pathname.startsWith('/api/')) {
      // Network Only
      return;
    }
    if (url.origin !== self.location.origin) {
      // CDN: Cache First
      event.respondWith(cacheFirst(event.request));
      return;
    }
    // 本地资源: Network First
    event.respondWith(networkFirst(event.request));
  });
  ```

#### 步骤 3.3：PWA 注册

- **修改文件**：`views/index.html`
- **新增**：
  ```html
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then(reg => console.log('SW registered:', reg.scope))
        .catch(err => console.log('SW registration failed:', err));
    }
  </script>
  ```

#### 步骤 3.4：安装提示

- **修改文件**：`views/js/auth.js` 或 `views/index.html`
- **新增**：
  ```javascript
  // 监听 beforeinstallprompt 事件
  let deferredPrompt;
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallBanner();  // 显示自定义安装横幅
  });

  function showInstallBanner() {
    // 在页面顶部显示"安装到桌面"横幅
    // 用户点击 → deferredPrompt.prompt()
  }
  ```

---

### Phase 4：触摸优化与性能（0.5-1 周）

**目标**：优化触摸体验和移动端性能

#### 步骤 4.1：触摸优化

- **修改文件**：`views/index.html`、`views/components/`
- **修改点**：
  1. 所有可点击元素最小尺寸 44×44px（Apple HIG 标准）
  2. 按钮间距增大（`gap-2` → `gap-3`）
  3. 链接区域扩展（`inline` → `inline-block p-1`）
  4. 添加 `touch-action` CSS 属性控制手势
  5. 消除 300ms 点击延迟：`touch-action: manipulation`

#### 步骤 4.2：移动端性能优化

- **修改文件**：`views/index.html`
- **修改点**：
  1. 图片懒加载：`<img loading="lazy">`
  2. CDN 资源 `defer` / `async` 加载
  3. 知识图谱 Cytoscape.js 按需加载（仅在图谱页面）
  4. 减少首屏 DOM 节点（侧边栏懒渲染）

#### 步骤 4.3：移动端专用 API 优化

- **修改文件**：`lib/web_server.py`
- **修改点**：
  1. 检测 `User-Agent` 或 `Sec-CH-UA-Mobile` 请求头
  2. 移动端请求返回精简数据（减少字段）
  3. 图片返回缩略图（已有 thumbnail.py）

---

### Phase 5：测试与验证（0.5 周）

**目标**：验证移动端兼容性

#### 步骤 5.1：浏览器兼容性测试

- **测试矩阵**：

  | 设备 | 浏览器 | 优先级 |
  |------|--------|:------:|
  | iPhone 14+ | Safari | 🔴 必须 |
  | iPhone SE | Safari | 🟡 应该 |
  | Android 13+ | Chrome | 🔴 必须 |
  | Android 11+ | Chrome | 🟡 应该 |
  | iPad | Safari | 🟡 应该 |
  | iPad | Chrome | 🟢 可选 |

#### 步骤 5.2：PWA 验证

- Lighthouse 审计得分目标：
  - Performance: ≥ 80
  - Accessibility: ≥ 90
  - Best Practices: ≥ 90
  - SEO: ≥ 80
  - PWA: ≥ 80

#### 步骤 5.3：文档

- **更新文件**：`Doc/plans/PLAN-000-enterprise-overall-plan.md` — 更新 3.5 进度

---

## 四、依赖关系

```
Phase 1（响应式基础）
  ├─→ Phase 2（页面改造）
  │     └─→ Phase 3（PWA 支持）
  │           └─→ Phase 4（触摸与性能）
  │                 └─→ Phase 5（测试验证）
  └─→ PLAN-005（SSO 集成）  ← login.html 修改需协调
```

- **与 PLAN-005 的协调**：login.html 同时有 SSO 和响应式修改，需要按顺序或合并修改

---

## 五、风险评估

| 风险 | 严重程度 | 概率 | 缓解措施 |
|------|:--------:|:----:|----------|
| index.html 2258 行修改困难 | 高 | 高 | 渐进式修改，小步提交 |
| Tailwind CDN 版本升级破坏样式 | 中 | 低 | 锁定 CDN 版本 |
| Service Worker 缓存策略不当 | 中 | 中 | 版本化缓存名 + 强制更新机制 |
| Cytoscape.js 移动端性能 | 中 | 中 | 移动端限制节点数量 |
| PWA iOS 兼容性 | 中 | 高 | iOS 不完全支持 PWA，提供基础体验 |
| 无构建步骤限制 | 中 | 高 | 使用原生 CSS/JS，避免引入 npm |
| 与 PLAN-005 修改冲突 | 中 | 中 | 先完成 PLAN-005 的 login.html 修改 |

---

## 六、文件变更清单

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `views/css/responsive.css` | 响应式工具样式 |
| `views/components/mobile-sidebar.html` | 移动端侧边栏组件 |
| `views/manifest.json` | PWA 清单 |
| `views/sw.js` | Service Worker |
| `views/icons/icon-192.png` | PWA 图标 192px |
| `views/icons/icon-512.png` | PWA 图标 512px |
| `views/icons/icon-maskable-192.png` | PWA 遮罩图标 |
| `views/icons/icon-maskable-512.png` | PWA 遮罩图标 |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `views/index.html` | 响应式布局 + 移动端导航 + PWA 注册 |
| `views/login.html` | 响应式样式 |
| `views/js/auth.js` | PWA 安装提示 |
| `views/graph.js` | 触摸手势支持 |
| `views/admin/*.html` | 响应式改造 |
| `views/components/*.html` | 响应式改造 |
| `views/search/results.html` | 响应式改造 |
| `views/media/gallery.html` | 响应式改造 |
| `lib/web_server.py` | manifest/sw.js 路由 + 移动端检测 |

---

## 七、验收标准

1. ✅ 所有页面在 375px（iPhone SE）到 2560px（4K）宽度范围内正常显示
2. ✅ 移动端侧边栏可通过汉堡菜单打开/关闭
3. ✅ 所有可点击元素最小 44×44px
4. ✅ PWA 可安装到桌面（Chrome Android）
5. ✅ Lighthouse PWA 得分 ≥ 80
6. ✅ 离线访问基础页面（首页、登录页）
7. ✅ 桌面端体验无降级
8. ✅ 知识图谱支持触摸操作

---

**计划创建时间**：2026-06-23
**计划状态**：draft — 等待审批
