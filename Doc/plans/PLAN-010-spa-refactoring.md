# PLAN-010：SPA 单页应用重构（方案 B）

---
plan_id: PLAN-010
type: master
status: active
created: 2026-06-24
priority: high
estimated_hours: 32-40
segments_file: PLAN-010-spa-refactoring-segments.md
segments_created: 2026-06-24
current_stage: 阶段 1 基础架构
---

## 一、需求重述

**核心目标**：将管理工具页面改造为 SPA 单页应用，实现左侧边栏固定、右侧动态加载视图内容的架构。

**具体需求**：
1. ✅ 保持左侧边栏不变（与首页一致）
2. ✅ 点击管理工具时，右侧内容区动态加载对应功能
3. ✅ 无需"返回首页"按钮，侧边栏始终可见
4. ✅ 使用 Alpine.js + 模块化组件架构
5. ✅ 支持浏览器前进/后退（hash 路由）
6. ✅ 保持主题切换功能
7. ✅ 保持用户认证和水印功能

**涉及页面**（共 14 个管理工具）：
- `/admin/qa.html` - AI 问答
- `/admin/dashboard.html` - 看板
- `/admin/quality.html` - 质检
- `/admin/duplicates.html` - 去重
- `/admin/shares.html` - 分享
- `/admin/webhooks.html` - 通知
- `/admin/edit.html` - 新建
- `/admin/upload.html` - 上传
- `/admin/users.html` - 用户管理
- `/admin/approvals.html` - 审批
- `/admin/audit.html` - 审计
- `/admin/permissions.html` - 权限
- `/admin/kb-management.html` - 知识库管理
- `/admin/notifications.html` - 通知管理

---

## 二、架构设计

### 2.1 目录结构

```
views/
├── index.html                 # 主框架（SPA 入口）
├── components/                # 组件目录（新建）
│   ├── header.js             # 头部组件
│   ├── sidebar.js            # 侧边栏组件
│   ├── theme-switcher.js     # 主题切换器
│   └── watermark.js          # 水印组件
├── views/                     # 视图模块（新建）
│   ├── overview.js           # 概览视图（内联）
│   ├── browse.js             # 浏览视图（内联）
│   ├── graph.js              # 图谱视图（内联）
│   ├── timeline.js           # 时间线视图（内联）
│   ├── gaps.js               # 缺口视图（内联）
│   ├── qa.js                 # AI 问答
│   ├── dashboard.js          # 看板
│   ├── quality.js            # 质检
│   ├── duplicates.js         # 去重
│   ├── shares.js             # 分享
│   ├── webhooks.js           # 通知
│   ├── edit.js               # 新建
│   ├── upload.js             # 上传
│   ├── users.js              # 用户管理
│   ├── approvals.js          # 审批
│   ├── audit.js              # 审计
│   ├── permissions.js        # 权限
│   ├── kb-management.js      # 知识库管理
│   └── notifications.js      # 通知管理
├── utils/                     # 工具模块（新建）
│   ├── router.js             # 路由管理
│   ├── state.js              # 状态管理
│   ├── api.js                # API 封装
│   └── loader.js             # 模块加载器
├── css/                       # 样式（不变）
│   ├── themes.css            # 主题样式（从 index.html 提取）
│   └── responsive.css        # 响应式样式（不变）
├── lib/                       # 第三方库（不变）
└── admin/                     # 原管理页面（逐步迁移）
    ├── qa.html               # 保留作为备份
    └── ...
```

### 2.2 技术栈

| 技术 | 版本 | 加载方式 | 用途 |
|------|------|---------|------|
| Alpine.js | 3.x | CDN | 状态管理、组件化 |
| Tailwind CSS | 3.x | CDN | 样式 |
| marked.js | latest | CDN | Markdown 渲染 |
| Cytoscape.js | 3.28 | CDN | 知识图谱 |
| ES6 Modules | - | 浏览器原生 | 模块化 |

### 2.3 路由策略

**Hash 路由**（无需后端支持）：

```javascript
// 路由映射
const routes = {
    'overview': { inline: true },
    'browse': { inline: true },
    'graph': { inline: true },
    'timeline': { inline: true },
    'gaps': { inline: true },
    'qa': { module: 'views/qa.js' },
    'dashboard': { module: 'views/dashboard.js' },
    'quality': { module: 'views/quality.js' },
    // ... 其他管理工具
};
```

**URL 示例**：
- `http://localhost:8080/#browse` - 浏览视图
- `http://localhost:8080/#qa` - AI 问答
- `http://localhost:8080/#dashboard` - 看板

### 2.4 模块加载策略

**内联视图**：直接在 `index.html` 中，使用 Alpine.js 组件
**管理视图**：动态加载 ES6 模块，按需加载

```javascript
// 懒加载示例
async loadView(viewName) {
    if (routes[viewName].inline) {
        this.currentView = viewName;
        return;
    }
    
    const module = await import(`./views/${viewName}.js`);
    this.views[viewName] = module.default;
    this.currentView = viewName;
}
```

---

## 三、实施阶段

### 第 1 阶段：基础架构搭建（5 小时）

#### 任务 1.1：创建目录结构（0.5h）
- [ ] 创建 `views/components/` 目录
- [ ] 创建 `views/views/` 目录
- [ ] 创建 `views/utils/` 目录
- [ ] 创建 `.gitkeep` 文件保持目录结构

#### 任务 1.2：实现路由模块（1h）
- [ ] 创建 `views/utils/router.js`
- [ ] 实现 hash 路由监听
- [ ] 实现路由映射表
- [ ] 实现路由跳转方法
- [ ] 实现浏览器前进/后退支持

#### 任务 1.3：实现状态管理（1h）
- [ ] 创建 `views/utils/state.js`
- [ ] 实现全局状态对象
- [ ] 实现状态订阅机制
- [ ] 实现状态持久化（localStorage）

#### 任务 1.4：实现 API 封装（1h）
- [ ] 创建 `views/utils/api.js`
- [ ] 封装 GET/POST/PUT/DELETE 方法
- [ ] 封装认证检查逻辑
- [ ] 封装错误处理逻辑

#### 任务 1.5：实现模块加载器（1.5h）
- [ ] 创建 `views/utils/loader.js`
- [ ] 实现动态 import 逻辑
- [ ] 实现模块缓存机制
- [ ] 实现加载失败重试
- [ ] 实现加载进度提示

---

### 第 2 阶段：组件拆分（2 小时）

#### 任务 2.1：提取 Header 组件（0.5h）
- [ ] 创建 `views/components/header.js`
- [ ] 提取 header HTML 结构
- [ ] 提取 header Alpine.js 状态
- [ ] 提取主题切换逻辑

#### 任务 2.2：提取 Sidebar 组件（1h）
- [ ] 创建 `views/components/sidebar.js`
- [ ] 提取 sidebar HTML 结构
- [ ] 提取导航链接逻辑
- [ ] 修改链接为 hash 路由（`href="#qa"` 而非 `/admin/qa.html`）
- [ ] 提取移动端侧边栏逻辑

#### 任务 2.3：提取 Theme Switcher（0.5h）
- [ ] 创建 `views/components/theme-switcher.js`
- [ ] 提取主题切换 HTML
- [ ] 提取主题定义数组
- [ ] 提取主题应用逻辑

---

### 第 3 阶段：内联视图模块化（7 小时）

**说明**：这些视图已经在 `index.html` 中，需要提取为独立模块。

#### 任务 3.1：概览视图（1h）
- [ ] 创建 `views/views/overview.js`
- [ ] 提取概览 HTML 结构
- [ ] 提取概览 Alpine.js 状态
- [ ] 提取统计数据计算逻辑
- [ ] 测试概览视图加载

#### 任务 3.2：浏览视图（2h）
- [ ] 创建 `views/views/browse.js`
- [ ] 提取原子列表 HTML
- [ ] 提取原子详情面板 HTML
- [ ] 提取搜索/过滤逻辑
- [ ] 提取批量操作逻辑
- [ ] 提取协同功能（评论、收藏、评分）
- [ ] 测试浏览视图加载

#### 任务 3.3：图谱视图（2h）⚠️ 高复杂度
- [ ] 创建 `views/views/graph.js`
- [ ] 提取 Cytoscape.js 配置
- [ ] 提取图谱 HTML 结构
- [ ] 提取图谱 Alpine.js 状态
- [ ] 提取 fcose 布局参数逻辑
- [ ] 提取节点筛选逻辑
- [ ] 测试图谱视图加载

#### 任务 3.4：时间线视图（1h）
- [ ] 创建 `views/views/timeline.js`
- [ ] 提取时间线 HTML 结构
- [ ] 提取时间线 Alpine.js 状态
- [ ] 测试时间线视图加载

#### 任务 3.5：缺口视图（1h）
- [ ] 创建 `views/views/gaps.js`
- [ ] 提取缺口 HTML 结构
- [ ] 提取缺口 Alpine.js 状态
- [ ] 测试缺口视图加载

---

### 第 4 阶段：管理工具迁移（23 小时）

**迁移顺序**：按复杂度从低到高

#### 任务 4.1：质检页面（1h）⭐ 低复杂度
- [ ] 创建 `views/views/quality.js`
- [ ] 从 `admin/quality.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 调整 API 调用路径
- [ ] 测试质检视图加载

#### 任务 4.2：去重页面（1h）⭐ 低复杂度
- [ ] 创建 `views/views/duplicates.js`
- [ ] 从 `admin/duplicates.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 调整 API 调用路径
- [ ] 测试去重视图加载

#### 任务 4.3：分享页面（1h）⭐ 低复杂度
- [ ] 创建 `views/views/shares.js`
- [ ] 从 `admin/shares.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 调整 API 调用路径
- [ ] 测试分享视图加载

#### 任务 4.4：通知页面（1h）⭐ 低复杂度
- [ ] 创建 `views/views/webhooks.js`
- [ ] 从 `admin/webhooks.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 调整 API 调用路径
- [ ] 测试通知视图加载

#### 任务 4.5：上传页面（1h）⭐ 低复杂度
- [ ] 创建 `views/views/upload.js`
- [ ] 从 `admin/upload.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 调整 API 调用路径
- [ ] 测试上传视图加载

#### 任务 4.6：审计页面（1h）⭐ 低复杂度
- [ ] 创建 `views/views/audit.js`
- [ ] 从 `admin/audit.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 调整 API 调用路径
- [ ] 测试审计视图加载

#### 任务 4.7：审批页面（1h）⭐ 低复杂度
- [ ] 创建 `views/views/approvals.js`
- [ ] 从 `admin/approvals.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 调整 API 调用路径
- [ ] 测试审批视图加载

#### 任务 4.8：通知管理页面（1h）⭐ 低复杂度
- [ ] 创建 `views/views/notifications.js`
- [ ] 从 `admin/notifications.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 调整 API 调用路径
- [ ] 测试通知管理视图加载

#### 任务 4.9：AI 问答页面（1.5h）⭐⭐ 中复杂度
- [ ] 创建 `views/views/qa.js`
- [ ] 从 `admin/qa.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 提取聊天历史状态管理
- [ ] 提取 LLM 配置弹窗逻辑
- [ ] 调整 API 调用路径
- [ ] 测试 AI 问答视图加载

#### 任务 4.10：看板页面（1.5h）⭐⭐ 中复杂度
- [ ] 创建 `views/views/dashboard.js`
- [ ] 从 `admin/dashboard.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 提取统计数据计算逻辑
- [ ] 调整 API 谳用路径
- [ ] 测试看板视图加载

#### 任务 4.11：新建页面（1.5h）⭐⭐ 中复杂度
- [ ] 创建 `views/views/edit.js`
- [ ] 从 `admin/edit.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 提取编辑器状态管理
- [ ] 提取表单验证逻辑
- [ ] 调整 API 调用路径
- [ ] 测试新建视图加载

#### 任务 4.12：用户管理页面（1.5h）⭐⭐ 中复杂度
- [ ] 创建 `views/views/users.js`
- [ ] 从 `admin/users.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 提取用户列表状态管理
- [ ] 提取权限编辑逻辑
- [ ] 调整 API 调用路径
- [ ] 测试用户管理视图加载

#### 任务 4.13：权限页面（2h）⭐⭐⭐ 高复杂度
- [ ] 创建 `views/views/permissions.js`
- [ ] 从 `admin/permissions.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 提取权限矩阵逻辑
- [ ] 提取知识库权限逻辑
- [ ] 调整 API 调用路径
- [ ] 测试权限视图加载

#### 任务 4.14：知识库管理页面（2h）⭐⭐⭐ 高复杂度
- [ ] 创建 `views/views/kb-management.js`
- [ ] 从 `admin/kb-management.html` 提取核心内容
- [ ] 剔除 header 和 sidebar
- [ ] 提取知识库切换逻辑
- [ ] 提取元数据编辑逻辑
- [ ] 提取图谱配置逻辑
- [ ] 调整 API 调用路径
- [ ] 测试知识库管理视图加载

---

### 第 5 阶段：主框架整合（2 小时）

#### 任务 5.1：重构 index.html（2h）
- [ ] 修改 `index.html` 为 SPA 主框架
- [ ] 引入模块加载器
- [ ] 引入路由模块
- [ ] 引入状态管理
- [ ] 整合 Header 组件
- [ ] 整合 Sidebar 组件
- [ ] 整合内联视图（概览、浏览、图谱、时间线、缺口）
- [ ] 整合动态视图加载逻辑
- [ ] 提取主题样式到 `css/themes.css`
- [ ] 测试主框架加载

---

### 第 6 阶段：整合测试（7.5 小时）

#### 任务 6.1：路由测试（1h）
- [ ] 测试所有视图切换
- [ ] 测试浏览器前进/后退
- [ ] 测试 hash 路由跳转
- [ ] 测试移动端路由
- [ ] 测试首次加载默认路由

#### 任务 6.2：状态同步测试（1.5h）
- [ ] 测试主题切换跨视图持久化
- [ ] 测试用户信息跨视图共享
- [ ] 测试水印跨视图保持
- [ ] 测试原子数据跨视图同步
- [ ] 测试选中状态保持

#### 任务 6.3：性能优化（2h）
- [ ] 实现视图懒加载
- [ ] 实现模块缓存策略
- [ ] 优化初始加载时间
- [ ] 优化视图切换速度
- [ ] 添加加载进度提示

#### 任务 6.4：跨浏览器测试（1h）
- [ ] Chrome 测试
- [ ] Firefox 测试
- [ ] Safari 测试
- [ ] Edge 测试
- [ ] 移动端浏览器测试

#### 任务 6.5：边界情况处理（1h）
- [ ] 测试模块加载失败处理
- [ ] 测试网络错误重试
- [ ] 测试未授权视图跳转
- [ ] 测试 404 视图处理

#### 任务 6.6：文档更新（1h）
- [ ] 更新 `Doc/SPA-ARCHITECTURE.md`（架构文档）
- [ ] 更新 `Doc/SPA-DEVELOPMENT-GUIDE.md`（开发指南）
- [ ] 更新 `README.md`（用户说明）
- [ ] 更新 `.claude/project.md`（项目索引）

---

### 第 7 阶段：清理与备份（可选）

#### 任务 7.1：备份原管理页面（0.5h）
- [ ] 创建 `views/admin_backup/` 目录
- [ ] 移动原管理页面到备份目录
- [ ] 保留备份文件（安全措施）

#### 任务 7.2：清理冗余代码（0.5h）
- [ ] 清理原 `index.html` 中的内联视图代码
- [ ] 清理冗余的 CSS
- [ ] 清理冗余的 JavaScript
- [ ] 优化文件大小

---

## 四、依赖关系

### 4.1 技术依赖

| 依赖 | 来源 | 用途 | 风险 |
|------|------|------|------|
| ES6 Modules | 浏览器原生 | 模块化 | ⚠️ 需服务器支持正确 MIME type |
| Alpine.js CDN | cdn.jsdelivr.net | 状态管理 | ⚠️ CDN 不可用时需本地备份 |
| Hash 路由 | 浏览器原生 | 路由 | ✅ 无依赖 |
| Python 服务器 | lib/web_server.py | 静态文件 | ⚠️ 需支持 ES6 模块 MIME type |

### 4.2 任务依赖

```
阶段 1（基础架构）
  ↓ 必须完成
阶段 2（组件拆分）
  ↓ 必须完成
阶段 3（内联视图模块化）
  ↓ 必须完成
阶段 4（管理工具迁移）
  ↓ 可并行执行（低复杂度优先）
阶段 5（主框架整合）
  ↓ 必须完成
阶段 6（整合测试）
  ↓ 必须完成
阶段 7（清理与备份）
```

**并行执行机会**：
- 任务 4.1-4.8（低复杂度页面）可并行迁移
- 任务 4.9-4.12（中复杂度页面）可并行迁移
- 任务 6.1-6.5（测试）可并行执行

---

## 五、风险评估

### 5.1 高风险（HIGH）

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **ES6 模块 MIME type 错误** | 模块加载失败，SPA 无法运行 | 修改 `web_server.py`，确保 `.js` 文件返回 `application/javascript` |
| **状态同步复杂** | 数据不一致，用户体验差 | 使用单一数据源，清晰的数据流，充分的测试 |
| **图谱视图迁移复杂** | Cytoscape.js 配置复杂，迁移失败风险高 | 优先测试图谱视图，发现问题及时调整 |

### 5.2 中风险（MEDIUM）

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **模块加载性能问题** | 初始加载慢，视图切换慢 | 实现懒加载、缓存策略、加载进度提示 |
| **浏览器兼容性** | 部分浏览器不支持 ES6 模块 | 使用特性检测，提供降级方案（方案 A） |
| **Alpine.js CDN 不可用** | SPA 无法运行 | 本地备份 Alpine.js 文件 |

### 5.3 低风险（LOW）

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **原管理页面备份不足** | 迁移失败无法回退 | 阶段 7 强制备份 |
| **测试覆盖不足** | 边界情况未发现 | 充分的整合测试（阶段 6） |

---

## 六、预估复杂度

**总体复杂度：高（HIGH）**

| 类别 | 预估时间 | 占比 |
|------|---------|------|
| 基础架构 | 5h | 12.5% |
| 组件拆分 | 2h | 5% |
| 内联视图模块化 | 7h | 17.5% |
| 管理工具迁移 | 23h | 57.5% |
| 主框架整合 | 2h | 5% |
| 整合测试 | 7.5h | 18.75% |
| **总计** | **39.5h** | **100%** |

**分阶段复杂度**：
- 阶段 1：中（技术基础，但无业务逻辑）
- 阶段 2：低（纯提取，无新逻辑）
- 阶段 3：中-高（图谱视图复杂）
- 阶段 4：低-高（页面复杂度差异大）
- 阶段 5：中（整合逻辑复杂）
- 阶段 6：中（测试全面）

---

## 七、成功标准

### 7.1 功能标准

- ✅ 所有 14 个管理工具正常加载
- ✅ 左侧边栏始终可见
- ✅ 视图切换无刷新（SPA 体验）
- ✅ 浏览器前进/后退正常工作
- ✅ 主题切换跨视图持久化
- ✅ 用户认证和水印正常工作

### 7.2 性能标准

- ✅ 初始加载时间 < 2s（gzip）
- ✅ 视图切换时间 < 500ms
- ✅ 首次访问新视图加载 < 1s
- ✅ 后续访问视图加载 < 100ms（缓存）

### 7.3 质量标准

- ✅ 无 console.log 语句
- ✅ 无硬编码路径
- ✅ 所有 API 调用统一封装
- ✅ 所有模块有清晰的注释
- ✅ 所有边界情况有错误处理

---

## 八、后续优化建议（可选）

### 8.1 短期优化（1-2 周后）

1. **引入 Vite 构建工具**：
   - 自动代码分割
   - 自动压缩优化
   - 开发服务器热更新
   - 生产构建优化

2. **添加 TypeScript**：
   - 类型安全
   - 更好的 IDE 支持
   - 更容易维护

### 8.2 长期优化（3-6 月后）

1. **单元测试**：
   - Jest 测试框架
   - 测试覆盖率 > 80%

2. **性能监控**：
   - 添加性能指标收集
   - 添加错误日志收集

3. **PWA 支持**：
   - Service Worker 缓存
   - 离线访问支持

---

## 九、执行策略

**本计划为 Master 计划，需要拆分为 Phase 计划**：

建议拆分：
- **Phase 1**：基础架构 + 组件拆分（阶段 1-2，7 小时）
- **Phase 2**：内联视图模块化（阶段 3，7 小时）
- **Phase 3**：管理工具迁移（阶段 4，23 小时）← 最大工作量
- **Phase 4**：主框架整合 + 测试（阶段 5-6，9.5 小时）

---

**下一步**：调用 `/supercode:plan-segment` 进行任务拆分