"""
知识图谱数据生成模块

本模块负责从知识库中提取原子数据，生成用于图谱可视化的 JSON 数据。
实际的图谱渲染由前端 JavaScript 库完成。

## 数据格式说明

### 节点 (Node) 格式

每个节点代表一个知识原子，包含以下字段：

```json
{
    "id": "atoms/methods/nextcloud-install",
    "label": "Nextcloud 安装方法",
    "type": "method",
    "description": "在 Ubuntu 上安装 Nextcloud 的完整步骤",
    "path": "atoms/methods/nextcloud-install.md",
    "color": "#3498db",
    "tags": ["ubuntu", "nextcloud"],
    "in_degree": 2,
    "out_degree": 3
}
```

字段说明：
- id: 唯一标识符，通常是原子的相对路径（不含 .md 后缀）
- label: 显示标签，用于图谱节点上的文字（建议 ≤30 字符）
- type: 知识类型（method/fact/definition/opinion/data/question/reference）
- description: 详细描述，用于节点详情面板
- path: 原子文件的相对路径
- color: 节点颜色，根据类型自动分配
- tags: 标签列表，用于筛选
- in_degree: 入度（被引用次数），用于节点大小计算
- out_degree: 出度（引用次数），用于节点大小计算

### 边 (Edge) 格式

边表示原子之间的链接关系，通过解析 Markdown 中的 [[链接]] 语法生成：

```json
{
    "id": "atoms/methods/nextcloud-install->atoms/facts/nextcloud-requirements",
    "source": "atoms/methods/nextcloud-install",
    "target": "atoms/facts/nextcloud-requirements"
}
```

字段说明：
- id: 边的唯一标识符，格式为 "{source}->{target}"
- source: 源节点 ID
- target: 目标节点 ID

### 类型颜色映射

| 类型       | 颜色代码 | 说明           |
|-----------|---------|----------------|
| method    | #3498db | 操作步骤、方法  |
| fact      | #2ecc71 | 可验证的事实    |
| definition| #9b59b6 | 概念定义        |
| opinion   | #e74c3c | 主观观点        |
| data      | #f39c12 | 数值、统计数据  |
| question  | #1abc9c | 待解答问题      |
| reference | #34495e | 外部参考链接    |

## 前端渲染建议

### 推荐的 JavaScript 图可视化库

1. **Cytoscape.js** (https://js.cytoscape.org/)
   - 适合中小规模图谱（<500 节点）
   - 内置多种布局算法（COSE、Grid、Circle 等）
   - 支持交互（拖拽、缩放、点击）

2. **D3.js + Canvas** (https://d3js.org/)
   - 适合大规模图谱（500-5000 节点）
   - 高度可定制
   - 使用 Canvas 渲染以提升性能

3. **vis-network** (https://visjs.github.io/vis-network/docs/network/)
   - 轻量级，易于集成
   - 自动物理模拟
   - 支持大量节点

4. **Sigma.js** (http://sigmajs.org/)
   - 专门为大规模图谱设计
   - WebGL 渲染
   - 支持 10,000+ 节点

### 布局算法选择

| 节点数量    | 推荐布局        | 说明                          |
|-----------|----------------|------------------------------|
| <50       | Grid/Circle    | 整齐排列，易于浏览              |
| 50-200    | COSE/Force     | 自动调整位置，显示关系           |
| 200-1000  | Concentric     | 按类型分组，减少重叠             |
| >1000     | 层次聚类 + 缩放  | 先聚类显示，点击展开              |

### 性能优化建议

对于 1000+ 节点的大型知识库：

1. **分页/虚拟滚动**
   - 只渲染可见区域的节点
   - 使用 Intersection Observer API

2. **节点聚类**
   - 按类型聚合显示
   - 点击聚类展开详细节点

3. **延迟加载**
   - 初始只加载节点 ID 和标签
   - 点击后才加载详细内容

4. **Canvas 替代 SVG**
   - SVG 渲染在大规模时性能差
   - Canvas 可以渲染数万个节点

5. **抽样显示**
   - 默认只显示高置信度/高连接度节点
   - 提供"显示更多"按钮

## 使用示例

### Python 后端生成数据

```python
from lib.visualizer import KnowledgeVisualizer
from pathlib import Path

# 初始化可视化器
kb_dir = Path('/path/to/knowledge-base')
output_path = kb_dir / 'views' / 'data' / 'graph-data.json'

# 生成图谱数据
visualizer = KnowledgeVisualizer(kb_dir, output_path)
graph_data = visualizer.generate_json_data()

# graph_data = {
#     'nodes': [...],
#     'edges': [...]
# }
```

### 前端加载数据

```javascript
// 从 JSON 文件加载
const response = await fetch('data/graph-data.json');
const graphData = await response.json();

// 使用 Cytoscape.js 渲染
const cy = cytoscape({
    container: document.getElementById('graph'),
    elements: [
        ...graphData.nodes.map(n => ({ data: n })),
        ...graphData.edges.map(e => ({ data: e }))
    ],
    style: [
        {
            selector: 'node',
            style: {
                'label': 'data(label)',
                'background-color': 'data(color)'
            }
        }
    ],
    layout: { name: 'grid' }
});
```

## 注意事项

1. **浏览器安全策略**
   - 直接打开本地 HTML 文件时，浏览器会阻止 fetch() 加载本地 JSON
   - 解决方案：使用 HTTP 服务器（python -m http.server 8080）

2. **节点 ID 唯一性**
   - 确保 ID 不重复
   - 建议使用相对路径作为 ID

3. **边的有效性**
   - 只添加目标节点存在的边
   - 避免悬空引用

4. **标签长度**
   - 限制标签长度（≤30 字符）
   - 过长标签会影响渲染效果
"""

import json
from pathlib import Path
from typing import Dict, List
from .validator import OKFValidator


class KnowledgeVisualizer:
    """知识图谱数据生成器

    负责从知识库中提取原子数据，生成用于前端图谱渲染的 JSON 数据。
    """

    # 类型颜色映射
    TYPE_COLORS = {
        'method': '#3498db',
        'fact': '#2ecc71',
        'definition': '#9b59b6',
        'opinion': '#e74c3c',
        'data': '#f39c12',
        'question': '#1abc9c',
        'reference': '#34495e'
    }

    def __init__(self, kb_dir: Path, output_path: Path):
        """初始化可视化器

        Args:
            kb_dir: 知识库目录路径
            output_path: 输出 JSON 文件路径
        """
        self.kb_dir = kb_dir
        self.output_path = output_path
        self.validator = OKFValidator()
        self._concepts_loaded = False

    def _ensure_concepts_loaded(self):
        """确保概念数据已加载"""
        if not self._concepts_loaded:
            self.validator.validate_bundle(self.kb_dir)
            self._concepts_loaded = True

    def generate_json_data(self) -> Dict:
        """生成图谱数据

        从知识库中提取原子数据，生成 nodes 和 edges 列表。

        Returns:
            Dict with 'nodes' and 'edges' lists for graph visualization.

        示例输出:
            {
                'nodes': [
                    {
                        'id': 'atoms/methods/nextcloud-install',
                        'label': 'Nextcloud 安装',
                        'type': 'method',
                        'description': '...',
                        'path': 'atoms/methods/nextcloud-install.md',
                        'color': '#3498db'
                    },
                    ...
                ],
                'edges': [
                    {
                        'id': 'atoms/methods/a->atoms/facts/b',
                        'source': 'atoms/methods/a',
                        'target': 'atoms/facts/b'
                    },
                    ...
                ]
            }
        """
        self._ensure_concepts_loaded()

        nodes: List[Dict] = []
        edges: List[Dict] = []

        # 预计算度数：in_degree（被引用次数），out_degree（引用次数）
        in_degree: Dict[str, int] = {}
        out_degree: Dict[str, int] = {}

        # 第一遍：生成所有节点
        for concept in self.validator.concepts:
            node_id = concept['id']
            node_type = concept['type']
            color = self.TYPE_COLORS.get(node_type, '#95a5a6')

            # 初始化度数
            in_degree[node_id] = 0
            out_degree[node_id] = 0

            nodes.append({
                'id': node_id,
                'label': concept['title'][:30],  # 限制标签长度
                'type': node_type,
                'description': concept.get('description', ''),
                'path': concept['path'],
                'color': color,
                'tags': concept.get('tags', [])
            })

        # 第二遍：生成边（解析 [[链接]]）
        # 注意：需要先生成所有节点，才能验证边的目标是否存在
        node_ids = {n['id'] for n in nodes}

        for concept in self.validator.concepts:
            node_id = concept['id']

            for link in concept.get('links', []):
                # 标准化链接为目标节点 ID
                # 链接格式可能是：
                # - "nextcloud-server-cache"
                # - "atoms/methods/nextcloud-server-cache"
                # - "./atoms/methods/nextcloud-server-cache"

                target_candidates = []

                # 尝试精确匹配
                target_candidates.append(link.replace('.md', ''))

                # 移除 ./ 前缀
                if link.startswith('./'):
                    target_candidates.append(link[2:].replace('.md', ''))

                # 查找匹配的节点
                target_id = None
                for candidate in target_candidates:
                    # 精确匹配
                    if candidate in node_ids:
                        target_id = candidate
                        break
                    # 部分匹配（链接是节点 ID 的最后部分）
                    for existing_id in node_ids:
                        if existing_id.endswith('/' + candidate):
                            target_id = existing_id
                            break
                    if target_id:
                        break

                # 只添加有效边（目标节点存在）
                if target_id and target_id != node_id:
                    edges.append({
                        'id': f"{node_id}->{target_id}",
                        'source': node_id,
                        'target': target_id
                    })
                    # 统计度数
                    out_degree[node_id] = out_degree.get(node_id, 0) + 1
                    in_degree[target_id] = in_degree.get(target_id, 0) + 1

        # 第三遍：将度数添加到节点
        for node in nodes:
            node_id = node['id']
            node['in_degree'] = in_degree.get(node_id, 0)
            node['out_degree'] = out_degree.get(node_id, 0)

        return {'nodes': nodes, 'edges': edges}

    def export_graph_data(self) -> bool:
        """导出图谱数据到 JSON 文件

        Returns:
            True if successful, False otherwise.
        """
        print(f"📊 Generating graph data: {self.kb_dir}")

        self._ensure_concepts_loaded()

        if not self.validator.concepts:
            print("   No concepts found in knowledge base")
            return False

        print(f"   Concepts: {len(self.validator.concepts)}")

        # 生成数据
        graph_data = self.generate_json_data()

        print(f"   Nodes: {len(graph_data['nodes'])}")
        print(f"   Edges: {len(graph_data['edges'])}")

        # 写入文件
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Graph data exported: {self.output_path}")

        return True

    # 保留旧方法以兼容现有代码
    def visualize(self, name: str = None) -> bool:
        """已弃用：请使用 export_graph_data() 并在前端渲染图谱"""
        print("⚠️  Warning: visualize() is deprecated.")
        print("   Use export_graph_data() and render in frontend instead.")
        return self.export_graph_data()
