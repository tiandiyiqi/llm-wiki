# LLM Wiki 设计系统（Design System）

> 本文件是 LLM Wiki 项目的**设计单一事实来源（Single Source of Truth）**。
> 所有 UI 改造、新功能界面、组件开发都应遵循本文档定义的设计令牌（Design Tokens）与规范。
>
> 版本：v1.0　|　最后更新：2026-06-26　|　适用范围：`/views/` Web UI

---

## 一、设计定位（Design Positioning）

### 产品性质
LLM Wiki 是一个**企业级 OKF 知识库系统**，承载知识录入、语义检索、图谱可视化、权限协作等专业作业。界面的本质目标是：**让专业用户长时间高效作业而不疲劳**。

### 目标用户
| 用户角色 | 主要诉求 | 设计含义 |
|---------|---------|---------|
| 知识工程师 / 编辑者 | 高频录入、检索、编辑知识原子 | 高信息密度、键盘友好、低视觉噪音 |
| 知识消费者 / 普通成员 | 快速找到并阅读知识 | 清晰的搜索与导航、舒适的阅读排版 |
| 管理员 | 权限、审批、审计、知识库治理 | 数据表格清晰、操作可追溯、状态明确 |

### 设计哲学
1. **专业克制（Restraint）** —— 参考 Linear / Notion / GitHub。中性色调主导，强调色克制使用，去除一切装饰性元素。
2. **信息优先（Content-first）** —— 界面退到内容之后，绝不与知识内容争夺注意力。
3. **一致性（Consistency）** —— 同一交互在任何位置表现一致；依托 `nav-config.js` 与 `ui-components.js` 的单一来源。
4. **效率（Efficiency）** —— 为高频用户优化：键盘快捷键、合理默认值、最少点击路径。
5. **去 AI 模板感（Anti-slop）** —— 拒绝过大圆角、艳丽渐变、随机阴影、紫色霓虹等"AI 生成感"视觉。

---

## 二、设计令牌（Design Tokens）

> 实现方式：以 CSS 自定义属性（CSS Variables）定义于 `:root`，Tailwind 通过 `tailwind.config` 的 `extend` 映射引用，保证亮/暗色一处切换。

### 2.1 色彩系统（Color）

**品牌主色 —— 靛蓝（Indigo）**

| 令牌 | 亮色值 | 用途 |
|------|--------|------|
| `--color-primary-50` | `#EEF2FF` | 主色浅背景（选中态、hover 底色） |
| `--color-primary-100` | `#E0E7FF` | 标签、徽章浅底 |
| `--color-primary-500` | `#6366F1` | 次级主色 |
| `--color-primary-600` | `#4F46E5` | **主操作色**（按钮、链接、激活态） |
| `--color-primary-700` | `#4338CA` | 主色 hover / pressed |

**中性灰阶（Neutral / Slate）—— 界面骨架**

| 令牌 | 亮色值 | 用途 |
|------|--------|------|
| `--color-bg` | `#FFFFFF` | 页面主背景 |
| `--color-bg-subtle` | `#F8FAFC` | 次级背景（侧边栏、卡片区） |
| `--color-bg-muted` | `#F1F5F9` | 表格斑马纹、输入框底 |
| `--color-border` | `#E2E8F0` | 默认边框/分隔线 |
| `--color-border-strong` | `#CBD5E1` | 强调边框、输入框聚焦前 |
| `--color-text` | `#0F172A` | 主文本（slate-900） |
| `--color-text-secondary` | `#475569` | 次要文本（slate-600） |
| `--color-text-muted` | `#94A3B8` | 占位/禁用文本（slate-400） |

**语义色（Semantic）—— 状态反馈**

| 令牌 | 值 | 用途 |
|------|-----|------|
| `--color-success` | `#16A34A` | 成功、通过、在线 |
| `--color-warning` | `#D97706` | 警告、待处理、缺口 |
| `--color-danger` | `#DC2626` | 错误、删除、驳回 |
| `--color-info` | `#0891B2` | 提示、信息 |

> **铁律**：语义色仅用于状态表达，绝不用作装饰；整页强调色面积建议 ≤ 10%。

### 2.2 字体排版（Typography）

| 令牌 | 值 | 用途 |
|------|-----|------|
| 正文字体 | `"Inter", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif` | 全局 UI 与中文正文 |
| 等宽字体 | `"JetBrains Mono", "SF Mono", Consolas, monospace` | 代码、ID、原子标识 |

**字阶（Type Scale，1.25 比例）**

| 级别 | 字号 / 行高 | 字重 | 用途 |
|------|-----------|------|------|
| Display | 28px / 36px | 600 | 页面主标题 |
| H1 | 22px / 30px | 600 | 视图标题 |
| H2 | 18px / 26px | 600 | 区块标题 |
| Body-L | 15px / 24px | 400 | 知识内容正文 |
| Body | 14px / 22px | 400 | **界面默认字号** |
| Caption | 12px / 18px | 400 | 辅助说明、时间戳 |

### 2.3 间距与栅格（Spacing & Layout）

- **基准单位**：4px（间距均为 4 的倍数：4 / 8 / 12 / 16 / 24 / 32 / 48）
- **内容最大宽度**：阅读区 `720px`，列表/表格区自适应
- **侧边栏宽度**：桌面 `240px`（当前 192px 偏窄，建议加宽）
- **栅格断点**：`sm 640 / md 768 / lg 1024 / xl 1280`

### 2.4 圆角、阴影、动效（Radius / Shadow / Motion）

| 类别 | 令牌 | 值 | 说明 |
|------|------|-----|------|
| 圆角 | `--radius-sm` | 6px | 按钮、输入框、徽章 |
| 圆角 | `--radius-md` | 8px | 卡片、弹窗 |
| 圆角 | `--radius-lg` | 12px | 大容器（克制使用，避免"气泡感"） |
| 阴影 | `--shadow-sm` | `0 1px 2px rgba(15,23,42,.06)` | 卡片、表格行 hover |
| 阴影 | `--shadow-md` | `0 4px 12px rgba(15,23,42,.08)` | 弹窗、下拉菜单 |
| 动效 | `--ease` | `cubic-bezier(.2,.8,.2,1)` | 标准缓动 |
| 动效 | 时长 | `150ms`（微交互）/ `220ms`（面板） | 一律 ≤ 250ms，遵守 `prefers-reduced-motion` |

> 阴影统一为冷灰半透明、单方向，**禁止彩色阴影与多层炫光**。

### 2.5 暗色模式（Dark Mode）

策略：**亮色为主、暗色次要**。通过 `[data-theme="dark"]` 在 `:root` 覆盖令牌实现，组件代码零改动。

| 令牌 | 暗色值 |
|------|--------|
| `--color-bg` | `#0F172A` |
| `--color-bg-subtle` | `#1E293B` |
| `--color-border` | `#334155` |
| `--color-text` | `#E2E8F0` |
| `--color-primary-600` | `#6366F1`（暗色下提亮一档保证对比度） |

---

## 三、组件规范（Component Conventions）

> 落地于 `/views/utils/ui-components.js` 共享组件库，确保 14 个管理工具与 5 个主视图表现一致。

| 组件 | 规范要点 |
|------|---------|
| **按钮 Button** | 三级：Primary（主色实底）/ Secondary（描边）/ Ghost（无底）。高度 36px，圆角 6px，loading 态内置 spinner |
| **徽章 Badge** | 语义变体（success/warning/danger/info/neutral），浅底深字，非实底高饱和 |
| **表格 Table** | 行高 44px，表头 sticky，斑马纹用 `bg-muted`，hover 行高亮，操作列右对齐 |
| **弹窗 Modal** | 居中 + 遮罩 `rgba(15,23,42,.4)`，宽度按内容（sm 420 / md 560 / lg 720），ESC 关闭 |
| **输入框 Input** | 默认边框 `border-strong`，聚焦 `ring-2 ring-primary-600/20 + border-primary-600` |
| **侧边栏项 NavItem** | 选中态：左侧 3px 主色条 + `bg-primary-50` 底；图标 18px |
| **加载 Spinner** | 主色描边旋转，伴随骨架屏（Skeleton）用于列表/表格首屏 |
| **空状态 Empty** | 统一插画/图标 + 一句说明 + 一个主操作，避免空白页 |

---

## 四、可访问性（Accessibility, WCAG 2.1 AA）

- 文本对比度 ≥ 4.5:1，大字号 ≥ 3:1（靛蓝 `#4F46E5` 在白底对比度 7.0:1，达标）
- 所有交互元素可键盘聚焦，焦点环（focus ring）可见，不可仅靠颜色传达状态
- 触控目标 ≥ 44×44px（移动端）
- 图片/图标提供 `aria-label`，表单控件关联 `<label>`
- 尊重 `prefers-reduced-motion` 与 `prefers-color-scheme`

---

## 五、不做清单（Anti-patterns）

- ❌ 大面积渐变背景、玻璃拟态（Glassmorphism）滥用
- ❌ 超过 12px 的卡片圆角、随机彩色阴影
- ❌ 强调色作为大面积背景
- ❌ 多种字体混用、字号随意
- ❌ 每个组件各写一套样式（必须走 `ui-components.js`）
- ❌ 纯前端硬编码导航/角色（必须走 `nav-config.js`）

---

## 六、参考基准（Benchmarks）

- **Linear** —— 信息密度与键盘效率
- **Notion** —— 内容优先的阅读排版
- **GitHub Primer** —— 企业级中性色与组件体系
- **Vercel / Geist** —— 克制的动效与间距
