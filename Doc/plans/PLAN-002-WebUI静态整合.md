# 实施计划：Web UI 入口 - 静态整合方案

## 元信息

| 属性 | 值 |
|------|-----|
| 状态 | draft |
| 创建时间 | 2026-06-19 |
| 所属阶段 | 阶段 3 - 开发 |
| 预估复杂度 | 低 |
| 前置计划 | PLAN-001-知识库互动增强.md (已完成) |

---

## Context

PLAN-001 已完成，实现了：
- 一句话捕获 (capture)
- 文件监控 (watch)
- Heads Up 主动推送 (gaps, relations, heads-up)
- 可视化增强 (timeline, visualize --interactive)

现在需要创建 Web UI 入口，整合现有功能。

---

## 目标

创建一个静态 Web UI 入口页面，整合现有的图谱和时间线可视化，提供基础的知识浏览功能。

**两步实施**：
- **Step 1**：静态整合（无后端，快速验证 UX）
- **Step 2**：FastAPI 后端（根据反馈决定是否实现）

---

## 实施阶段

### Step 1：静态资源整合（约 2 小时）

**目标**：创建静态 HTML 入口，嵌入现有可视化

#### 1.1 创建入口页面

**文件**：`views/index.html`

**功能**：
- 左侧导航栏：浏览、图谱、时间线、缺口
- 主内容区：知识列表（从静态 JSON 加载）
- 详情面板：选中的原子详情
- Heads Up 区：显示推荐内容

**技术栈**：
- Alpine.js（~15KB，轻量响应式）
- Tailwind CSS CDN（样式）
- marked.js（Markdown 渲染）

#### 1.2 创建静态数据生成器

**文件**：`lib/web_data.py`

**功能**：
- `generate_atoms_json()` - 导出所有原子为 JSON
- `generate_gaps_json()` - 导出缺口为 JSON
- 供静态 HTML 读取

**CLI 命令**：
```bash
llm-wiki web-data ./my-kb
# 输出到 views/data/
```

#### 1.3 修改现有可视化

**文件**：`views/knowledge-graph.html`, `views/timeline.html`

**修改**：
- 添加返回入口链接
- 统一导航样式
- 支持 iframe 嵌入

---

### Step 2：FastAPI 后端（约 4 小时，待定）

**目标**：提供 API，支持搜索和创建

**触发条件**：Step 1 使用后认为需要以下功能时实施：
- 实时搜索
- 一句话创建原子
- 知识编辑

#### 2.1 创建 API 服务

**文件**：`lib/web_server.py`

**API 端点**：
```
GET  /api/kb/{name}/atoms       # 原子列表
GET  /api/kb/{name}/atoms/{id}  # 原子详情
POST /api/kb/{name}/capture     # 一句话创建
GET  /api/kb/{name}/search      # 搜索
GET  /api/kb/{name}/graph       # 图谱数据
GET  /api/kb/{name}/timeline    # 时间线数据
```

#### 2.2 CLI 命令

```bash
llm-wiki web ./my-kb --port 8080
# 启动 FastAPI 服务器
```

---

## 依赖关系

```
Step 1（静态整合）
    ├─ views/index.html（独立）
    ├─ lib/web_data.py（独立）
    └─ 修改现有可视化（独立）
         ↓
Step 2（FastAPI 后端）
    └─ lib/web_server.py（依赖 Step 1 验证结果）
```

---

## 风险

| 级别 | 风险 | 缓解措施 |
|------|------|----------|
| LOW | 静态页面加载慢 | 使用分页 JSON、懒加载 |
| LOW | 图谱嵌入 iframe 问题 | 添加 sandbox 属性 |
| LOW | Alpine.js 学习曲线 | 保持简单，仅用基础指令 |
| MEDIUM | Step 2 可能不需要 | 先完成 Step 1，根据反馈决定 |

---

## 预估复杂度：低

| 步骤 | 状态 | 预估工时 |
|------|------|----------|
| Step 1 | 可执行 | 2 小时 |
| Step 2 | 待定 | 4 小时 |

---

## 验证计划

### Step 1 验证

```bash
# 生成静态数据
llm-wiki web-data ./test-kb

# 打开入口页面
open ./test-kb/views/index.html

# 验证：
# - 知识列表显示
# - 图谱链接跳转
# - 时间线链接跳转
# - 详情面板显示
```

### Step 2 验证（待定）

```bash
# 启动服务器
llm-wiki web ./test-kb --port 8080

# 验证：
# - API 端点响应
# - 搜索功能
# - 创建原子
```

---

## 完成标准

**Step 1 完成标准**：
- [ ] `views/index.html` 可正常打开
- [ ] 知识列表可加载显示
- [ ] 图谱和时间线可嵌入访问
- [ ] 详情面板可显示选中原子

**Step 2 完成标准（待定）**：
- [ ] FastAPI 服务可启动
- [ ] 所有 API 端点响应正常
- [ ] 搜索和创建功能正常

---

## 页面布局参考

```
┌─────────────────────────────────────────────────┐
│ Header: 知识库名称 + 搜索框（静态提示）          │
├────────────┬────────────────────────────────────┤
│ Sidebar    │ Main Content                       │
│            │                                    │
│ 📚 浏览    │ ┌────────────────────────────────┐ │
│ 🕸️ 图谱    │ │ 知识列表                       │ │
│ 📅 时间线  │ │                                │ │
│ 🔍 缺口    │ │ ┌───┐ ┌───┐ ┌───┐              │ │
│            │ │ │ A │ │ B │ │ C │ ...          │ │
│            │ │ └───┘ └───┘ └───┘              │ │
│ Heads Up   │ │                                │ │
│ ─────────  │ │ (从 views/data/atoms.json)     │ │
│ 💡 推荐知识│ └────────────────────────────────┘ │
│ - Atom 1   │                                    │
│ - Atom 2   │ ┌────────────────────────────────┐ │
│            │ │ 详情面板                       │ │
│            │ │ (点击原子显示)                 │ │
│            │ │                                │ │
│            │ └────────────────────────────────┘ │
└────────────┴────────────────────────────────────┘
```

---

## 技术栈详情

### Step 1 静态页面

```html
<!-- views/index.html -->
<!DOCTYPE html>
<html>
<head>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.x.x/dist/tailwind.min.css" rel="stylesheet">
</head>
<body x-data="app()">
  <!-- Alpine.js 响应式组件 -->
</body>
</html>
```

### Step 2 FastAPI（待定）

```python
# lib/web_server.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LLM Wiki Web UI")

@app.get("/api/kb/{name}/atoms")
async def list_atoms(name: str):
    # 复用现有 query 功能
    pass
```