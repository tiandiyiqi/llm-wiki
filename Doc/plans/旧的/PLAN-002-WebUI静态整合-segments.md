# 任务拆分：Web UI 入口 - 静态整合方案

## 元信息

| 属性 | 值 |
|------|-----|
| 状态 | completed |
| 创建时间 | 2026-06-19 |
| 完成时间 | 2026-06-19 |
| 来源计划 | PLAN-002-WebUI静态整合.md |
| 并行组数 | 1 |
| 串行组数 | 1 |

---

## 依赖关系图

```
任务组 A（可并行执行）
├─ 任务 A-1: 创建静态数据生成器 (lib/web_data.py)
├─ 任务 A-2: 创建入口页面 (views/index.html)
└─ 任务 A-3: 修改现有可视化（链接整合）
         ↓
任务组 B（依赖 A 完成）
└─ 任务 B-1: CLI 命令集成 (llm-wiki.py)
         ↓
任务组 C（待定，根据反馈决定）
└─ 任务 C-1: FastAPI 后端 (lib/web_server.py)
```

---

## 任务组详情

---

## 任务组 A：静态资源整合

**类型：** 并行
**预估时间：** 60-90 分钟
**文件：**
- 创建: `lib/web_data.py`
- 创建: `views/index.html`
- 修改: `views/knowledge-graph.html`
- 修改: `views/timeline.html`

### 任务 A-1：创建静态数据生成器

**文件：** `lib/web_data.py`
**预估：** 20 分钟

**子任务：**

- [ ] A-1.1: 创建 WebDataExporter 类骨架
  ```python
  """静态 Web UI 数据导出"""

  from pathlib import Path
  from typing import Dict, List
  import json
  from .yaml_parser import SimpleYAMLParser
  from .constants import RESERVED_FILES


  class WebDataExporter:
      """导出知识库数据为静态 JSON"""

      def __init__(self, kb_dir: Path):
          self.kb_dir = Path(kb_dir)
          self.output_dir = self.kb_dir / "views" / "data"

      def export_all(self) -> Dict[str, int]:
          """导出所有数据，返回文件统计"""
          raise NotImplementedError

      def export_atoms(self) -> int:
          """导出原子列表为 atoms.json"""
          raise NotImplementedError

      def export_gaps(self) -> int:
          """导出缺口为 gaps.json"""
          raise NotImplementedError
  ```

- [ ] A-1.2: 实现 export_atoms 方法
  ```python
  def export_atoms(self) -> int:
      """导出原子列表为 atoms.json"""
      self.output_dir.mkdir(parents=True, exist_ok=True)

      atoms = []
      for md_file in self.kb_dir.rglob('*.md'):
          if md_file.name in RESERVED_FILES:
              continue

          content = md_file.read_text(encoding='utf-8')
          if content.startswith('---'):
              parts = content.split('---', 2)
              if len(parts) >= 3:
                  # 解析 frontmatter
                  parser = SimpleYAMLParser()
                  fm = parser.parse(parts[1])
                  if fm:
                      atoms.append({
                          'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
                          'path': str(md_file.relative_to(self.kb_dir)),
                          'type': fm.get('type', 'Unknown'),
                          'title': fm.get('title', md_file.stem),
                          'description': fm.get('description', ''),
                          'tags': fm.get('tags', []),
                          'timestamp': fm.get('timestamp', fm.get('created', '')),
                          'content': parts[2].strip()[:500]  # 预览
                      })

      output_file = self.output_dir / 'atoms.json'
      output_file.write_text(json.dumps(atoms, ensure_ascii=False, indent=2), encoding='utf-8')
      return len(atoms)
  ```

- [ ] A-1.3: 实现 export_gaps 方法
  ```python
  def export_gaps(self) -> int:
      """导出缺口为 gaps.json"""
      from .discovery import KnowledgeGapFinder

      finder = KnowledgeGapFinder(self.kb_dir)
      gaps = finder.find_gaps()

      gap_list = []
      for gap in gaps:
          gap_list.append({
              'type': gap.get('type', 'unknown'),
              'description': gap.get('description', ''),
              'suggestion': gap.get('suggestion', '')
          })

      output_file = self.output_dir / 'gaps.json'
      output_file.write_text(json.dumps(gap_list, ensure_ascii=False, indent=2), encoding='utf-8')
      return len(gap_list)
  ```

- [ ] A-1.4: 实现 export_all 方法
  ```python
  def export_all(self) -> Dict[str, int]:
      """导出所有数据"""
      self.output_dir.mkdir(parents=True, exist_ok=True)

      atoms_count = self.export_atoms()
      gaps_count = self.export_gaps()

      print(f"✅ 已导出静态数据到 {self.output_dir}")
      print(f"   atoms.json: {atoms_count} 个原子")
      print(f"   gaps.json: {gaps_count} 个缺口")

      return {'atoms': atoms_count, 'gaps': gaps_count}
  ```

---

### 任务 A-2：创建入口页面

**文件：** `views/index.html`
**预估：** 30 分钟

**子任务：**

- [ ] A-2.1: 创建 HTML 基础结构和 CDN 引入
  ```html
  <!DOCTYPE html>
  <html lang="zh-CN">
  <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>LLM Wiki - 知识库浏览</title>
      <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
      <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.x.x/dist/tailwind.min.css" rel="stylesheet">
      <style>
          [x-cloak] { display: none !important; }
      </style>
  </head>
  <body class="bg-gray-100 min-h-screen" x-data="app()" x-cloak>
  ```

- [ ] A-2.2: 创建页面布局（Header + Sidebar + Main）
  ```html
  <!-- Header -->
  <header class="bg-white shadow-sm border-b border-gray-200 fixed top-0 left-0 right-0 z-50">
      <div class="flex items-center justify-between px-4 py-3">
          <h1 class="text-xl font-semibold text-gray-800" x-text="kbName">知识库</h1>
          <div class="text-sm text-gray-500">
              静态浏览模式
          </div>
      </div>
  </header>

  <div class="flex pt-14">
      <!-- Sidebar -->
      <aside class="w-48 bg-white border-r border-gray-200 fixed left-0 top-14 bottom-0 overflow-y-auto">
          <nav class="p-4">
              <div class="space-y-1">
                  <button @click="view='browse'"
                          :class="view === 'browse' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'"
                          class="w-full text-left px-3 py-2 rounded-md text-sm font-medium">
                      📚 浏览
                  </button>
                  <button @click="view='graph'"
                          :class="view === 'graph' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'"
                          class="w-full text-left px-3 py-2 rounded-md text-sm font-medium">
                      🕸️ 图谱
                  </button>
                  <button @click="view='timeline'"
                          :class="view === 'timeline' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'"
                          class="w-full text-left px-3 py-2 rounded-md text-sm font-medium">
                      📅 时间线
                  </button>
                  <button @click="view='gaps'"
                          :class="view === 'gaps' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'"
                          class="w-full text-left px-3 py-2 rounded-md text-sm font-medium">
                      🔍 缺口
                  </button>
              </div>

              <!-- Heads Up 区 -->
              <div class="mt-6 pt-4 border-t border-gray-200">
                  <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Heads Up</h3>
                  <div class="space-y-1">
                      <template x-for="gap in gaps.slice(0, 5)" :key="gap.description">
                          <div class="text-xs text-gray-600 px-3 py-1 hover:bg-gray-50 rounded cursor-pointer"
                               @click="view='gaps'">
                              💡 <span x-text="gap.description?.slice(0, 30) + '...'"></span>
                          </div>
                      </template>
                  </div>
              </div>
          </nav>
      </aside>

      <!-- Main Content -->
      <main class="ml-48 flex-1 p-6">
          <!-- 浏览视图 -->
          <div x-show="view === 'browse'" x-cloak>
              <!-- 原子列表 -->
          </div>

          <!-- 图谱视图 -->
          <div x-show="view === 'graph'" x-cloak>
              <iframe src="knowledge-graph.html" class="w-full h-[calc(100vh-120px)] border-0"></iframe>
          </div>

          <!-- 时间线视图 -->
          <div x-show="view === 'timeline'" x-cloak>
              <iframe src="timeline.html" class="w-full h-[calc(100vh-120px)] border-0"></iframe>
          </div>

          <!-- 缺口视图 -->
          <div x-show="view === 'gaps'" x-cloak>
              <!-- 缺口列表 -->
          </div>
      </main>
  </div>
  ```

- [ ] A-2.3: 创建 Alpine.js 应用逻辑
  ```html
  <script>
  function app() {
      return {
          view: 'browse',
          kbName: '知识库',
          atoms: [],
          gaps: [],
          selectedAtom: null,
          typeFilter: '',

          async init() {
              await this.loadData();
          },

          async loadData() {
              try {
                  const atomsRes = await fetch('data/atoms.json');
                  this.atoms = await atomsRes.json();

                  const gapsRes = await fetch('data/gaps.json');
                  this.gaps = await gapsRes.json();
              } catch (e) {
                  console.error('加载数据失败:', e);
              }
          },

          get filteredAtoms() {
              if (!this.typeFilter) return this.atoms;
              return this.atoms.filter(a => a.type === this.typeFilter);
          },

          selectAtom(atom) {
              this.selectedAtom = atom;
          },

          types() {
              const typeSet = new Set(this.atoms.map(a => a.type));
              return Array.from(typeSet);
          }
      }
  }
  </script>
  </body>
  </html>
  ```

- [ ] A-2.4: 完善浏览视图和详情面板
  ```html
  <!-- 浏览视图 -->
  <div x-show="view === 'browse'" x-cloak class="grid grid-cols-3 gap-6">
      <!-- 原子列表 -->
      <div class="col-span-2">
          <div class="bg-white rounded-lg shadow">
              <div class="p-4 border-b border-gray-200">
                  <div class="flex items-center justify-between">
                      <h2 class="text-lg font-medium text-gray-900">知识原子</h2>
                      <select x-model="typeFilter" class="text-sm border border-gray-300 rounded-md px-2 py-1">
                          <option value="">全部类型</option>
                          <template x-for="type in types()" :key="type">
                              <option :value="type" x-text="type"></option>
                          </template>
                      </select>
                  </div>
              </div>
              <div class="divide-y divide-gray-200 max-h-[calc(100vh-250px)] overflow-y-auto">
                  <template x-for="atom in filteredAtoms" :key="atom.id">
                      <div @click="selectAtom(atom)"
                           :class="selectedAtom?.id === atom.id ? 'bg-blue-50 border-l-4 border-blue-500' : 'hover:bg-gray-50'"
                           class="p-4 cursor-pointer">
                          <div class="flex items-start justify-between">
                              <div>
                                  <span class="inline-block px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-600"
                                        x-text="atom.type"></span>
                                  <h3 class="mt-1 text-sm font-medium text-gray-900" x-text="atom.title"></h3>
                                  <p class="mt-1 text-xs text-gray-500 line-clamp-2" x-text="atom.description"></p>
                              </div>
                          </div>
                          <div class="mt-2 flex items-center space-x-2">
                              <template x-for="tag in atom.tags?.slice(0, 3)" :key="tag">
                                  <span class="inline-block px-1.5 py-0.5 text-xs rounded bg-blue-100 text-blue-700"
                                        x-text="tag"></span>
                              </template>
                          </div>
                      </div>
                  </template>
              </div>
          </div>
      </div>

      <!-- 详情面板 -->
      <div class="col-span-1">
          <div class="bg-white rounded-lg shadow sticky top-20" x-show="selectedAtom">
              <div class="p-4 border-b border-gray-200">
                  <h2 class="text-lg font-medium text-gray-900" x-text="selectedAtom?.title">详情</h2>
              </div>
              <div class="p-4 space-y-4">
                  <div>
                      <label class="text-xs font-medium text-gray-500 uppercase">类型</label>
                      <p class="mt-1 text-sm text-gray-900" x-text="selectedAtom?.type"></p>
                  </div>
                  <div>
                      <label class="text-xs font-medium text-gray-500 uppercase">路径</label>
                      <p class="mt-1 text-sm text-gray-600 font-mono" x-text="selectedAtom?.path"></p>
                  </div>
                  <div>
                      <label class="text-xs font-medium text-gray-500 uppercase">描述</label>
                      <p class="mt-1 text-sm text-gray-700" x-text="selectedAtom?.description"></p>
                  </div>
                  <div>
                      <label class="text-xs font-medium text-gray-500 uppercase">内容预览</label>
                      <div class="mt-1 text-sm text-gray-700 prose prose-sm"
                           x-html="selectedAtom ? marked.parse(selectedAtom.content || '') : ''"></div>
                  </div>
                  <div x-show="selectedAtom?.tags?.length">
                      <label class="text-xs font-medium text-gray-500 uppercase">标签</label>
                      <div class="mt-1 flex flex-wrap gap-1">
                          <template x-for="tag in selectedAtom?.tags" :key="tag">
                              <span class="inline-block px-2 py-0.5 text-xs rounded bg-blue-100 text-blue-700"
                                    x-text="tag"></span>
                          </template>
                      </div>
                  </div>
              </div>
          </div>
      </div>
  </div>

  <!-- 缺口视图 -->
  <div x-show="view === 'gaps'" x-cloak>
      <div class="bg-white rounded-lg shadow">
          <div class="p-4 border-b border-gray-200">
              <h2 class="text-lg font-medium text-gray-900">知识缺口</h2>
          </div>
          <div class="divide-y divide-gray-200">
              <template x-for="gap in gaps" :key="gap.description">
                  <div class="p-4">
                      <div class="flex items-start">
                          <span class="inline-block px-2 py-0.5 text-xs rounded bg-yellow-100 text-yellow-800 mr-3"
                                x-text="gap.type"></span>
                          <div>
                              <p class="text-sm text-gray-700" x-text="gap.description"></p>
                              <p class="mt-1 text-xs text-gray-500" x-text="gap.suggestion"></p>
                          </div>
                      </div>
                  </div>
              </template>
          </div>
      </div>
  </div>
  ```

---

### 任务 A-3：修改现有可视化

**文件：** `views/knowledge-graph.html`, `views/timeline.html`
**预估：** 10 分钟

**子任务：**

- [ ] A-3.1: 在 knowledge-graph.html 添加返回入口链接
  ```html
  <!-- 在 body 开头添加 -->
  <div style="position: fixed; top: 10px; left: 10px; z-index: 1000;">
      <a href="index.html" class="px-3 py-1 bg-white rounded shadow text-sm text-gray-600 hover:text-blue-600">
          ← 返回入口
      </a>
  </div>
  ```

- [ ] A-3.2: 在 timeline.html 添加返回入口链接
  ```html
  <!-- 在 body 开头添加 -->
  <div style="position: fixed; top: 10px; left: 10px; z-index: 1000;">
      <a href="index.html" class="px-3 py-1 bg-white rounded shadow text-sm text-gray-600 hover:text-blue-600">
          ← 返回入口
      </a>
  </div>
  ```

---

## 任务组 B：CLI 命令集成

**类型：** 串行
**前置条件：** 任务组 A 完成
**预估时间：** 10 分钟
**文件：**
- 修改: `llm-wiki.py`
- 修改: `lib/__init__.py`

### 任务 B-1：添加 web-data 命令

**文件：** `llm-wiki.py`
**预估：** 10 分钟

**子任务：**

- [ ] B-1.1: 添加 web-data 子命令
  ```python
  # 在 subparsers 部分添加
  webdata_parser = subparsers.add_parser('web-data', help='生成静态 Web UI 数据')
  webdata_parser.add_argument('kb_path', type=Path, nargs='?', help='知识库路径')
  webdata_parser.add_argument('--kb', '-k', dest='knowledge_base', help='知识库名称')
  webdata_parser.set_defaults(func=cmd_web_data)
  ```

- [ ] B-1.2: 实现 cmd_web_data 函数
  ```python
  def cmd_web_data(args):
      """生成静态 Web UI 数据"""
      kb_path = resolve_kb(args)
      if not kb_path:
          return

      from lib import WebDataExporter

      exporter = WebDataExporter(kb_path)
      result = exporter.export_all()

      print(f"\n🌐 静态页面入口: {kb_path / 'views' / 'index.html'}")
  ```

- [ ] B-1.3: 在 lib/__init__.py 导出 WebDataExporter
  ```python
  from .web_data import WebDataExporter
  ```

---

## 任务组 C：FastAPI 后端（待定）

**类型：** 待定
**前置条件：** 任务组 A 和 B 完成，并收集用户反馈后决定是否实施
**预估时间：** 4 小时

**触发条件：**
- 需要实时搜索功能
- 需要一句话创建原子
- 需要知识编辑功能

**暂不拆分详细任务，待用户反馈后决定。**

---

## 验证步骤

### 任务组 A 验证

```bash
# 运行 web-data 命令
python3 llm-wiki.py web-data ./test-kb

# 检查输出文件
ls -la ./test-kb/views/data/

# 打开入口页面
open ./test-kb/views/index.html

# 验证：
# - 知识列表加载显示
# - 类型筛选工作
# - 详情面板显示
# - 图谱 iframe 加载
# - 时间线 iframe 加载
# - 缺口列表显示
```

### 任务组 B 验证

```bash
# 验证 CLI 命令
python3 llm-wiki.py web-data --help
python3 llm-wiki.py web-data ./my-kb
```

---

## 完成标准

**任务组 A 完成标准：**
- [ ] `lib/web_data.py` 可正常导出数据
- [ ] `views/index.html` 可正常打开
- [ ] 知识列表可加载显示
- [ ] 图谱和时间线可嵌入访问
- [ ] 详情面板可显示选中原子

**任务组 B 完成标准：**
- [ ] `llm-wiki web-data` 命令可用
- [ ] 输出正确的静态数据文件

---

## 风险与缓解

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| 静态 JSON 加载慢 | LOW | 使用分页、懒加载 |
| iframe 跨域问题 | LOW | 使用相对路径 |
| Alpine.js 学习曲线 | LOW | 保持简单，仅用基础指令 |
| 图谱/时间线样式冲突 | MEDIUM | 使用 iframe 隔离 |
