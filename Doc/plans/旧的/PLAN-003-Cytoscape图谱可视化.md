# 实施计划：Cytoscape.js 知识图谱可视化（方案 A）

## 需求重述

为 `llm-wiki` 项目实现**类 Obsidian 级别**的知识图谱交互体验：
- 力导向布局（fcose），自动散开避免重叠
- 右侧控制面板：筛选（按类型/标签/孤立节点）、外观调节（节点大小、连线粗细、文字透明度）、力度调节（向心力、排斥力）
- 节点按 `type` 染色，按入度/出度调整大小
- 点击节点：高亮 1 跳邻居、淡化其他、右侧显示 atom 详情
- 全文搜索匹配节点并聚焦
- 双击节点跳转到 atom 详情页
- 性能目标：≤2000 节点流畅，3000+ 仍可用

## 当前状态

**已有基础设施**：
- `lib/visualizer.py` 已输出 `graph-data.json`（nodes: id/label/type/description/path/color；edges: id/source/target）
- `lib/validator.py` 已提取 `tags`、`links` 字段
- `views/index.html` 已引入 Alpine.js + Tailwind CDN，图谱视图仅占位提示
- 颜色系统已定义（method: #3b82f6, fact: #22c55e, definition: #a855f7 等）

**缺失**：
- 入度/出度统计（需后端计算）
- 前端 Cytoscape.js 渲染（需引入 CDN + 约 500 行 JS）
- 控制面板、节点详情面板、搜索功能

---

## 实施阶段

### 第 1 阶段：后端数据增强（约 1 小时）

**目标**：为 `graph-data.json` 增加 `in_degree`、`out_degree` 字段，便于前端按连接数调整节点大小。

**文件修改**：
- `lib/visualizer.py`

**具体步骤**：
1. 在 `generate_json_data()` 中，遍历 edges 计算 `in_degree`（被引用次数）和 `out_degree`（引用次数）
2. 将这两个字段加入节点字典：
   ```python
   nodes.append({
       'id': node_id,
       'label': concept['title'][:30],
       'type': node_type,
       'description': concept.get('description', ''),
       'path': concept['path'],
       'color': color,
       'in_degree': in_degree[node_id],
       'out_degree': out_degree[node_id],
       'tags': concept.get('tags', [])
   })
   ```
3. 运行 `python3 llm-wiki.py visualize ./examples/nextcloud-kb` 验证输出

**验证**：`views/data/graph-data.json` 中节点包含 `in_degree`、`out_degree`、`tags`

---

### 第 2 阶段：前端 Cytoscape.js 集成（约 3 小时）

**目标**：引入 Cytoscape.js + fcose 布局，替换占位提示为真实图谱画布。

**文件修改**：
- `views/index.html`（图谱视图区域 + CDN 引入 + Alpine.js 数据）
- 新建 `views/graph.js`（约 500 行，图谱渲染逻辑）

**具体步骤**：

1. **引入 CDN**（`index.html` 头部）：
   ```html
   <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.28/dist/cytoscape.min.js"></script>
   <script src="https://cdn.jsdelivr.net/npm/cytoscape-fcose@2.2/dist/cytoscape-fcose.min.js"></script>
   ```

2. **替换图谱视图 HTML**（L460-492）：
   - 画布容器 `<div id="cy" class="w-full h-full"></div>`
   - 右侧控制面板（筛选、外观、力度）
   - 底部节点详情面板（点击节点时显示）

3. **创建 `views/graph.js`**：
   - `initGraph(data)`：初始化 Cytoscape 实例，配置 fcose 布局
   - 样式配置：节点大小按 `in_degree + out_degree` 缩放（最小 20px，最大 60px）
   - 颜色映射：复用 `typeColor()` 已有配色
   - 交互：
     - `click` → 高亮邻居、淡化其他、更新详情面板
     - `dblclick` → 跳转到 atom 详情（`browse.html?atom=<id>`）
     - `mouseover` → 显示 tooltip
   - 控制面板回调：
     - `filterByType(types)` → 只显示选中类型的节点
     - `filterByTag(tag)` → 只显示含该 tag 的节点
     - `toggleOrphans(show)` → 显示/隐藏孤立节点
     - `adjustNodeSize(scale)` → 调整节点大小比例
     - `adjustEdgeWidth(scale)` → 调整连线粗细
     - `adjustForce(gravity, repulsion)` → 重新布局

4. **Alpine.js 数据绑定**：
   - `graphData`：存储加载的 graph-data.json
   - `selectedNode`：当前选中节点
   - `graphFilters`：{ types: [], tags: [], showOrphans: true }
   - `graphSettings`：{ nodeSize: 1.0, edgeWidth: 1.0, gravity: 0.25, repulsion: 1 }

5. **与浏览视图联动**：
   - 全文搜索框输入 → `searchGraph(query)` → 匹配节点并居中聚焦

**验证**：
- 打开 `http://localhost:8080`，切换到图谱视图
- 节点按类型染色，按连接数大小变化
- 点击节点显示详情，双击跳转
- 控制面板筛选生效

---

### 第 3 阶段：优化与细节打磨（约 1 小时）

**目标**：提升用户体验，处理边缘情况。

**文件修改**：
- `views/index.html`
- `views/graph.js`

**具体步骤**：
1. **孤立节点处理**：
   - 默认隐藏孤立节点（无连接）
   - 控制面板提供"显示孤立节点"开关

2. **标签长度优化**：
   - 节点标签 ≤15 字符，超长截断 + "..."
   - tooltip 显示完整标题

3. **空知识库提示**：
   - 若 `graphData.nodes.length === 0`，显示"暂无知识原子"

4. **性能优化**：
   - 使用 Canvas renderer（`renderer: { name: 'canvas' }`）
   - 大图谱时启用 `textureOnWebGL: true`

5. **视觉细节**：
   - 节点选中时边框加粗 + 阴影
   - 邻居节点高亮，其他节点 opacity 降至 0.2
   - 连线平滑曲线（`curve-style: 'bezier'`）

**验证**：
- 100+ 节点知识库流畅拖拽、缩放
- 孤立节点开关生效
- 长标签截断显示

---

## 依赖关系

| 阶段 | 依赖 | 说明 |
|------|------|------|
| 第 1 阶段 | 无 | 纯后端修改 |
| 第 2 阶段 | 第 1 阶段 | 需增强后的 graph-data.json |
| 第 3 阶段 | 第 2 阶段 | 基础渲染完成后优化 |

---

## 风险评估

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| Cytoscape.js CDN 加载失败 | 低 | 国内网络可能慢 | 提供本地 fallback（下载到 views/lib/） |
| fcose 布局参数调优耗时 | 中 | 效果不如 Obsidian 需反复调试 | 参考官方示例参数，提供用户可调面板 |
| 大图谱性能问题 | 中 | 500+ 节点可能卡顿 | Canvas renderer + 孤立节点隐藏 |
| 与 Alpine.js 冲突 | 低 | Cytoscape 独立实例，不冲突 | 事件通过 Alpine 回调传递 |

---

## 预估复杂度

**中（MEDIUM）**
- 后端：1 小时
- 前端：4 小时
- 测试验证：1 小时
- **总计：约 6 小时（1 天）**

---

## 验证方案

1. **构建验证**：无 TypeScript/编译步骤，直接测试
2. **功能验证**：
   - `python3 llm-wiki.py web-ui ./examples/nextcloud-kb`
   - `cd views && python3 -m http.server 8080`
   - 浏览器打开 `http://localhost:8080`
   - 切换图谱视图，测试：
     - 节点渲染正确（颜色、大小）
     - 点击高亮邻居
     - 控制面板筛选生效
     - 搜索聚焦功能
     - 双击跳转详情
3. **性能验证**：创建 200+ 节点测试知识库，验证流畅度

---

## 关键文件清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `lib/visualizer.py` | 修改 | 增加 in_degree/out_degree/tags 字段 |
| `views/index.html` | 修改 | 引入 Cytoscape CDN + 替换图谱视图 HTML + Alpine.js 数据 |
| `views/graph.js` | 新建 | 图谱渲染逻辑（约 500 行） |

---

**等待确认**：是否继续执行此计划？(yes/no/modify)