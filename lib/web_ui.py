"""Web UI generation module for LLM Wiki.

生成 Web UI 所需的所有静态数据文件，用于浏览器访问知识库。

## 生成的文件结构

```
views/
├── index.html           # 入口页面（需要 HTTP 服务器）
├── data/
│   ├── atoms.json       # 原子数据（用于浏览视图）
│   ├── graph-data.json  # 图谱数据（用于知识图谱渲染）
│   ├── gaps.json        # 缺口数据（用于缺口视图）
│   ├── browse.html      # 浏览视图模板
│   └── gaps.html        # 缺口视图模板
└── timeline.html        # 时间线视图
```

## 使用方式

由于浏览器安全策略（CORS），本地 HTML 文件无法直接 fetch() 加载 JSON。
必须通过 HTTP 服务器访问：

```bash
# 启动 HTTP 服务器
cd views
python3 -m http.server 8080

# 打开浏览器
open http://localhost:8080/index.html
```

## 知识图谱渲染

知识图谱的数据已导出为 `graph-data.json`，需要前端 JavaScript 库渲染。
推荐使用：

- Cytoscape.js (https://js.cytoscape.org/)
- D3.js (https://d3js.org/)
- vis-network (https://visjs.github.io/vis-network/)
- Sigma.js (http://sigmajs.org/)

前端示例代码见 `lib/visualizer.py` 文件注释。
"""

import shutil
from pathlib import Path
from typing import Dict

from .web_data import WebDataExporter
from .visualizer import KnowledgeVisualizer
from .timeline import TimelineGenerator


def create_web_ui(kb_dir: Path) -> Dict[str, int]:
    """创建 Web UI - 一键生成所有视图文件

    生成的文件:
    - views/index.html          - Web UI 入口页面
    - views/timeline.html       - 时间线视图
    - views/data/atoms.json     - 原子数据（浏览视图）
    - views/data/graph-data.json - 图谱数据（前端渲染）
    - views/data/gaps.json      - 缺口数据
    - views/data/browse.html    - 浏览视图模板
    - views/data/gaps.html      - 缺口视图模板

    注意: 知识图谱 HTML 已移除，改为导出 JSON 数据供前端渲染。

    Args:
        kb_dir: Knowledge base directory path

    Returns:
        Dict with counts: {'atoms': N, 'gaps': M, 'graph_nodes': K, 'graph_edges': L}
    """
    print(f"\n{'='*50}")
    print(f"🚀 创建 Web UI: {kb_dir.name}")
    print(f"{'='*50}\n")

    views_dir = kb_dir / 'views'
    views_dir.mkdir(parents=True, exist_ok=True)
    views_data_dir = views_dir / 'data'
    views_data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Export static atom data (for browse view)
    print("📦 步骤 1/4: 导出原子数据...")
    exporter = WebDataExporter(kb_dir)
    result = exporter.export_all()
    print(f"   ✅ atoms.json: {result['atoms']} 个原子")
    print(f"   ✅ gaps.json: {result['gaps']} 个缺口")

    # 2. Export graph data (for frontend rendering)
    print("\n📊 步骤 2/4: 导出图谱数据...")
    graph_output = views_data_dir / 'graph-data.json'
    visualizer = KnowledgeVisualizer(kb_dir, graph_output)
    graph_result = visualizer.export_graph_data()
    if graph_result:
        # 读取生成的数据统计
        import json
        with open(graph_output, 'r') as f:
            graph_data = json.load(f)
        result['graph_nodes'] = len(graph_data.get('nodes', []))
        result['graph_edges'] = len(graph_data.get('edges', []))
        print(f"   ✅ graph-data.json: {result['graph_nodes']} 节点, {result['graph_edges']} 边")

    # 3. Generate timeline
    print("\n📅 步骤 3/4: 生成时间线...")
    generator = TimelineGenerator(kb_dir)
    generator.generate(views_dir / 'timeline.html')
    print(f"   ✅ timeline.html")

    # 4. Copy entry page and browse views
    print("\n🌐 步骤 4/4: 复制页面模板...")
    script_dir = Path(__file__).parent.parent

    copied_files = []

    # Entry page
    template_index = script_dir / 'views' / 'index.html'
    if template_index.exists():
        shutil.copy(template_index, views_dir / 'index.html')
        copied_files.append('index.html')

    # Browse view
    template_browse = script_dir / 'views' / 'data' / 'browse.html'
    if template_browse.exists():
        shutil.copy(template_browse, views_data_dir / 'browse.html')
        copied_files.append('browse.html')

    # Gap view
    template_gaps = script_dir / 'views' / 'data' / 'gaps.html'
    if template_gaps.exists():
        shutil.copy(template_gaps, views_data_dir / 'gaps.html')
        copied_files.append('gaps.html')

    # Graph JS
    template_graph_js = script_dir / 'views' / 'graph.js'
    if template_graph_js.exists():
        shutil.copy(template_graph_js, views_dir / 'graph.js')
        copied_files.append('graph.js')

    # Lib directory (fcose layout dependencies)
    template_lib_dir = script_dir / 'views' / 'lib'
    if template_lib_dir.exists():
        target_lib_dir = views_dir / 'lib'
        if target_lib_dir.exists():
            shutil.rmtree(target_lib_dir)
        shutil.copytree(template_lib_dir, target_lib_dir)
        copied_files.append('lib/')

    for f in copied_files:
        print(f"   ✅ {f}")

    # Summary
    print(f"\n{'='*50}")
    print(f"✅ Web UI 创建完成！")
    print(f"{'='*50}")
    print(f"\n📁 输出目录: {views_dir}")
    print(f"\n📄 生成的文件:")
    print(f"   views/")
    print(f"   ├── index.html           # 入口页面")
    print(f"   ├── timeline.html        # 时间线")
    print(f"   └── data/")
    print(f"       ├── atoms.json       # 原子数据（浏览视图）")
    print(f"       ├── graph-data.json  # 图谱数据（前端渲染）")
    print(f"       ├── gaps.json        # 缺口数据")
    print(f"       ├── browse.html      # 浏览视图")
    print(f"       └── gaps.html        # 缺口视图")
    print(f"\n💡 知识图谱:")
    print(f"   图谱数据已导出为 graph-data.json")
    print(f"   需使用前端 JavaScript 库渲染（如 Cytoscape.js、D3.js）")
    print(f"   详细说明见: lib/visualizer.py 文件注释")
    print(f"\n🌐 启动方式（必须使用 HTTP 服务器）:")
    print(f"   cd {views_dir}")
    print(f"   python3 -m http.server 8080")
    print(f"   open http://localhost:8080/index.html")
    print()

    return result