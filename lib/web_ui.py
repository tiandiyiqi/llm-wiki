"""Web UI generation module for LLM Wiki."""

import shutil
from pathlib import Path
from typing import Dict

from .web_data import WebDataExporter
from .visualizer import KnowledgeVisualizer
from .timeline import TimelineGenerator


def create_web_ui(kb_dir: Path) -> Dict[str, int]:
    """Create Web UI - one command to generate all view files.

    Generated files:
    - views/index.html          - Web UI entry page
    - views/knowledge-graph.html - Knowledge graph (force-directed)
    - views/timeline.html        - Timeline view
    - views/data/atoms.json      - Atom data
    - views/data/gaps.json       - Gap data
    - views/data/browse.html     - Browse view
    - views/data/gaps.html       - Gap view

    Args:
        kb_dir: Knowledge base directory path

    Returns:
        Dict with counts: {'atoms': N, 'gaps': M}
    """
    print(f"\n{'='*50}")
    print(f"🚀 创建 Web UI: {kb_dir.name}")
    print(f"{'='*50}\n")

    # 1. Export static data
    print("📦 步骤 1/4: 导出静态数据...")
    exporter = WebDataExporter(kb_dir)
    result = exporter.export_all()
    print(f"   ✅ atoms.json: {result['atoms']} 个原子")
    print(f"   ✅ gaps.json: {result['gaps']} 个缺口")

    # 2. Generate knowledge graph
    print("\n📊 步骤 2/4: 生成知识图谱...")
    views_dir = kb_dir / 'views'
    views_dir.mkdir(parents=True, exist_ok=True)
    visualizer = KnowledgeVisualizer(kb_dir, views_dir / 'knowledge-graph.html')
    visualizer.visualize(name=kb_dir.name)
    print(f"   ✅ knowledge-graph.html")

    # 3. Generate timeline
    print("\n📅 步骤 3/4: 生成时间线...")
    generator = TimelineGenerator(kb_dir)
    generator.generate(views_dir / 'timeline.html')
    print(f"   ✅ timeline.html")

    # 4. Copy entry page and browse views
    print("\n🌐 步骤 4/4: 复制页面模板...")
    script_dir = Path(__file__).parent.parent
    views_data_dir = views_dir / 'data'
    views_data_dir.mkdir(parents=True, exist_ok=True)

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
    print(f"   ├── knowledge-graph.html # 知识图谱")
    print(f"   ├── timeline.html        # 时间线")
    print(f"   └── data/")
    print(f"       ├── atoms.json       # 原子数据")
    print(f"       ├── gaps.json        # 缺口数据")
    print(f"       ├── browse.html      # 浏览视图")
    print(f"       └── gaps.html        # 缺口视图")
    print(f"\n🌐 启动方式:")
    print(f"   cd {views_dir}")
    print(f"   python3 -m http.server 8899")
    print(f"   open http://localhost:8899/index.html")
    print()

    return result
