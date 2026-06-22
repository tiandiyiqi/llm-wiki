# 任务组拆分：Cytoscape.js 知识图谱可视化

## 任务组结构

### 任务组 1：后端数据增强
**类型：** 串行
**前置条件：** 无

#### 任务 1-1：读取现有代码结构
- [x] SUB-TASK-001: 读取 `lib/visualizer.py`，理解 `generate_json_data()` 当前实现
  - 文件：`lib/visualizer.py`
  - 复杂度：低

#### 任务 1-2：计算节点度数
- [x] SUB-TASK-002: 在 `generate_json_data()` 中添加 in_degree 和 out_degree 计算
  - 文件：`lib/visualizer.py`
  - 位置：`generate_json_data()` 函数
  - 逻辑：遍历 edges 统计每个节点的入度和出度
  - 复杂度：中

#### 任务 1-3：添加 tags 字段
- [x] SUB-TASK-003: 在节点输出中添加 tags 字段
  - 文件：`lib/visualizer.py`
  - 位置：节点数据构建处
  - 复杂度：低

#### 任务 1-4：验证数据输出
- [x] SUB-TASK-004: 运行生成命令，验证 `views/data/graph-data.json` 输出正确
  - 命令：`python3 llm-wiki.py visualize ./examples/nextcloud-kb`
  - 验证：检查 JSON 中节点是否包含 degree 和 tags 字段
  - 复杂度：低

---

### 任务组 2：前端 HTML 结构重构
**类型：** 串行
**前置条件：** 任务组 1 完成

#### 任务 2-1：读取现有 HTML
- [ ] SUB-TASK-005: 读取 `views/index.html`，理解当前图谱视图结构
  - 文件：`views/index.html`
  - 复杂度：低

#### 任务 2-2：引入 Cytoscape.js CDN
- [ ] SUB-TASK-006: 在 `<head>` 中添加 Cytoscape.js 和 fcose 布局 CDN
  - 文件：`views/index.html`
  - 代码：
    ```html
    <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.28/dist/cytoscape.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/cytoscape-fcose@2.2/dist/cytoscape-fcose.min.js"></script>
    ```
  - 复杂度：低

#### 任务 2-3：替换图谱视图 HTML
- [ ] SUB-TASK-007: 用 Cytoscape 画布替换现有图谱容器
  - 文件：`views/index.html`
  - 位置：图谱视图 x-show 区域（L460-492）
  - 内容：画布容器 `<div id="cy"></div>` + 控制面板 + 详情面板
  - 复杂度：中

#### 任务 2-4：添加控制面板 HTML
- [ ] SUB-TASK-008: 创建控制面板（布局切换、筛选器、设置开关）
  - 文件：`views/index.html`
  - 元素：布局选择下拉、度数筛选滑块、孤立节点开关
  - 复杂度：中

#### 任务 2-5：添加详情面板 HTML
- [ ] SUB-TASK-009: 创建节点详情面板（显示选中节点信息）
  - 文件：`views/index.html`
  - 元素：节点标题、内容摘要、标签列表、度数显示
  - 复杂度：中

---

### 任务组 3：前端 JavaScript 实现
**类型：** 串行
**前置条件：** 任务组 2 完成

#### 任务 3-1：创建 graph.js 文件
- [ ] SUB-TASK-010: 创建 `views/graph.js` 文件骨架
  - 文件：`views/graph.js`（新建）
  - 内容：模块结构、全局变量声明
  - 复杂度：低

#### 任务 3-2：实现 Cytoscape 初始化
- [ ] SUB-TASK-011: 编写 `initGraph()` 函数，初始化 Cytoscape 实例
  - 文件：`views/graph.js`
  - 配置：容器、样式、初始布局、交互事件
  - 复杂度：高

#### 任务 3-3：实现节点样式定义
- [ ] SUB-TASK-012: 编写 `getStylesheet()` 函数，定义节点和边样式
  - 文件：`views/graph.js`
  - 样式：节点大小（基于度数）、颜色、标签、边样式
  - 复杂度：中

#### 任务 3-4：实现数据加载函数
- [ ] SUB-TASK-013: 编写 `loadGraphData(data)` 函数，转换并加载数据到 Cytoscape
  - 文件：`views/graph.js`
  - 逻辑：将 JSON 数据转换为 Cytoscape 元素格式
  - 复杂度：中

#### 任务 3-5：实现节点选择交互
- [ ] SUB-TASK-014: 编写节点点击事件处理，显示详情面板
  - 文件：`views/graph.js`
  - 逻辑：选中节点、高亮邻居、更新 Alpine.js 数据
  - 复杂度：中

#### 任务 3-6：实现控制面板回调
- [ ] SUB-TASK-015: 编写布局切换、筛选、设置变更的处理函数
  - 文件：`views/graph.js`
  - 函数：`changeLayout()`, `applyFilters()`, `toggleOrphanNodes()`
  - 复杂度：中

#### 任务 3-7：实现搜索聚焦联动
- [ ] SUB-TASK-016: 编写 `focusNode(nodeId)` 函数，与浏览视图搜索联动
  - 文件：`views/graph.js`
  - 逻辑：定位并高亮搜索节点
  - 复杂度：中

---

### 任务组 4：Alpine.js 数据绑定
**类型：** 串行
**前置条件：** 任务组 3 完成

#### 任务 4-1：添加图谱相关数据属性
- [ ] SUB-TASK-017: 在 Alpine.js 主组件中添加图谱数据属性
  - 文件：`views/index.html`
  - 属性：`graphData`, `selectedNode`, `graphFilters`, `graphSettings`
  - 复杂度：低

#### 任务 4-2：添加图谱初始化方法
- [ ] SUB-TASK-018: 在 Alpine.js 中添加 `initGraphView()` 方法
  - 文件：`views/index.html`
  - 逻辑：调用 `graph.js` 的初始化函数
  - 复杂度：低

#### 任务 4-3：绑定控制面板事件
- [ ] SUB-TASK-019: 将控制面板元素绑定到 Alpine.js 方法
  - 文件：`views/index.html`
  - 绑定：`x-on:change`, `x-model` 等
  - 复杂度：低

#### 任务 4-4：绑定详情面板显示
- [ ] SUB-TASK-020: 将详情面板绑定到 `selectedNode` 数据
  - 文件：`views/index.html`
  - 绑定：`x-show`, `x-text` 等
  - 复杂度：低

---

### 任务组 5：优化与细节打磨
**类型：** 串行
**前置条件：** 任务组 4 完成

#### 任务 5-1：孤立节点处理
- [ ] SUB-TASK-021: 实现孤立节点默认隐藏与开关切换
  - 文件：`views/graph.js`
  - 逻辑：筛选 degree=0 的节点，通过开关控制显示
  - 复杂度：中

#### 任务 5-2：标签长度优化
- [ ] SUB-TASK-022: 实现标签截断（超过 15 字符显示省略号）
  - 文件：`views/graph.js`
  - 位置：样式定义中的 label 函数
  - 复杂度：低

#### 任务 5-3：添加标签 tooltip
- [ ] SUB-TASK-023: 实现鼠标悬停显示完整标签
  - 文件：`views/graph.js`
  - 逻辑：监听 mouseover 事件，显示 tooltip
  - 复杂度：中

#### 任务 5-4：空知识库提示
- [ ] SUB-TASK-024: 添加空知识库检测与友好提示
  - 文件：`views/index.html`, `views/graph.js`
  - 逻辑：检测 graphData 为空，显示提示信息
  - 复杂度：低

#### 任务 5-5：性能优化
- [ ] SUB-TASK-025: 启用 Canvas 渲染器替代 SVG
  - 文件：`views/graph.js`
  - 配置：`renderer: { name: 'canvas' }`
  - 复杂度：低

#### 任务 5-6：视觉细节优化
- [ ] SUB-TASK-026: 添加选中节点边框、邻居高亮、曲线连线
  - 文件：`views/graph.js`
  - 位置：样式定义和事件处理
  - 复杂度：中

#### 任务 5-7：最终验证
- [ ] SUB-TASK-027: 完整功能测试，验证所有交互正常
  - 验证：节点选择、筛选、布局切换、搜索联动
  - 复杂度：中

---

## 执行顺序可视化

```
执行顺序：

1️⃣ 任务组 1：后端数据增强（串行）
   ├─ 任务 1-1：读取现有代码
   ├─ 任务 1-2：计算度数
   ├─ 任务 1-3：添加 tags
   └─ 任务 1-4：验证输出
       ↓
2️⃣ 任务组 2：前端 HTML 结构重构（串行）
   ├─ 任务 2-1：读取现有 HTML
   ├─ 任务 2-2：引入 CDN
   ├─ 任务 2-3：替换图谱容器
   ├─ 任务 2-4：添加控制面板
   └─ 任务 2-5：添加详情面板
       ↓
3️⃣ 任务组 3：前端 JavaScript 实现（串行）
   ├─ 任务 3-1：创建文件骨架
   ├─ 任务 3-2：初始化 Cytoscape
   ├─ 任务 3-3：定义样式
   ├─ 任务 3-4：数据加载
   ├─ 任务 3-5：节点选择
   ├─ 任务 3-6：控制回调
   └─ 任务 3-7：搜索联动
       ↓
4️⃣ 任务组 4：Alpine.js 数据绑定（串行）
   ├─ 任务 4-1：添加数据属性
   ├─ 任务 4-2：添加初始化方法
   ├─ 任务 4-3：绑定控制面板
   └─ 任务 4-4：绑定详情面板
       ↓
5️⃣ 任务组 5：优化与细节打磨（串行）
   ├─ 任务 5-1：孤立节点处理
   ├─ 任务 5-2：标签截断
   ├─ 任务 5-3：标签 tooltip
   ├─ 任务 5-4：空知识库提示
   ├─ 任务 5-5：Canvas 渲染
   ├─ 任务 5-6：视觉细节
   └─ 任务 5-7：最终验证
```

---

## 任务统计

| 任务组 | 子任务数 | 预估时间 | 类型 |
|--------|----------|----------|------|
| 任务组 1 | 4 | 15-20 分钟 | 串行 |
| 任务组 2 | 5 | 20-30 分钟 | 串行 |
| 任务组 3 | 7 | 40-60 分钟 | 串行 |
| 任务组 4 | 4 | 15-20 分钟 | 串行 |
| 任务组 5 | 7 | 30-40 分钟 | 串行 |
| **总计** | **27** | **约 2-2.5 小时** | - |

---

## 依赖关系说明

1. **任务组 1 → 任务组 2**：前端需要后端输出的 degree 和 tags 字段
2. **任务组 2 → 任务组 3**：JavaScript 需要操作 HTML 中的 DOM 元素
3. **任务组 3 → 任务组 4**：Alpine.js 绑定需要调用 JavaScript 函数
4. **任务组 4 → 任务组 5**：优化功能依赖基础功能完成

---

## 关键风险点

1. **任务 3-2（Cytoscape 初始化）**：复杂度最高，是核心功能
2. **任务 3-5（节点选择交互）**：涉及事件处理和 Alpine.js 状态同步
3. **任务 5-6（视觉细节）**：需要调整多个样式参数