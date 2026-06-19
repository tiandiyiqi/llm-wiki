# 任务拆分：知识库互动增强 - 并行执行方案

## 元信息

| 属性 | 值 |
|------|-----|
| 状态 | completed |
| 创建时间 | 2026-06-19 |
| 完成时间 | 2026-06-19 |
| 来源计划 | PLAN-001-知识库互动增强.md |
| 并行组数 | 2 |
| 串行组数 | 1 |

---

## 依赖关系图

```
并行组 1（同时开始）
├─ 任务组 A: Phase 1.1 一句话捕获 (quick_capture.py)
├─ 任务组 B: Phase 2 主动推送 (discovery.py + SKILL.md)
├─ 任务组 C: Phase 4.1 图谱扩展 (visualizer.py)
└─ 任务组 D: Phase 4.2 时间线 (timeline.py)
         ↓
并行组 2（组 A 完成后）
└─ 任务组 E: Phase 1.2 文件监控 (watcher.py)
```

---

## 任务组详情

---

## 任务组 A：一句话捕获 (Phase 1.1)

**类型：** 并行
**预估时间：** 15-20 分钟
**文件：**
- 创建: `lib/quick_capture.py`
- 修改: `lib/__init__.py`
- 修改: `llm-wiki.py`

### 任务 A-1：编写 QuickCapture 类骨架

**文件：** `lib/quick_capture.py`
**预估：** 2 分钟

```python
"""一句话快速创建知识原子"""

from pathlib import Path
from typing import Tuple, Dict, Optional
from datetime import datetime
import re


class QuickCapture:
    """一句话快速创建知识原子"""

    def __init__(self, kb_dir: Path):
        self.kb_dir = Path(kb_dir)
        self.atoms_dir = self.kb_dir / "atoms"

    def capture(self, text: str) -> Tuple[bool, str]:
        """
        从一句话提取知识并创建原子

        返回：(成功?, 原子路径或错误信息)
        """
        raise NotImplementedError

    def _parse_fact(self, text: str) -> Dict:
        """解析事实信息"""
        raise NotImplementedError

    def _detect_type(self, text: str) -> str:
        """检测知识类型"""
        raise NotImplementedError
```

### 任务 A-2：实现 _detect_type 方法

**文件：** `lib/quick_capture.py`
**预估：** 3 分钟

```python
def _detect_type(self, text: str) -> str:
    """检测知识类型"""
    text_lower = text.lower()

    # 端口号
    if re.search(r'端口|port\s*[:：]?\s*\d+', text_lower):
        return "facts"

    # 配置
    if re.search(r'配置|config|设置|setting', text_lower):
        return "config"

    # 命令
    if re.search(r'命令|command|运行|run', text_lower):
        return "commands"

    # 安装
    if re.search(r'安装|install|部署|deploy', text_lower):
        return "guides"

    # 版本
    if re.search(r'版本|version|支持到|lts', text_lower):
        return "facts"

    # 默认为 facts
    return "facts"
```

### 任务 A-3：实现 _parse_fact 方法

**文件：** `lib/quick_capture.py`
**预估：** 5 分钟

```python
def _parse_fact(self, text: str) -> Dict:
    """解析事实信息"""
    # 移除"记一下："等前缀
    clean_text = re.sub(r'^(记一下|记录|笔记)[：:,]?\s*', '', text.strip())

    # 提取主题（第一个名词短语）
    # 例如："Redis 默认端口 6379" -> "Redis"
    subject_match = re.match(r'^([A-Za-z]+)', clean_text)
    subject = subject_match.group(1) if subject_match else "knowledge"

    # 生成 slug
    slug = re.sub(r'[^a-z0-9-]', '-', clean_text.lower())[:50]
    slug = re.sub(r'-+', '-', slug).strip('-')

    return {
        "subject": subject,
        "slug": slug,
        "content": clean_text,
        "type": self._detect_type(text)
    }
```

### 任务 A-4：实现 capture 方法

**文件：** `lib/quick_capture.py`
**预估：** 5 分钟

```python
def capture(self, text: str) -> Tuple[bool, str]:
    """从一句话提取知识并创建原子"""
    if not text or not text.strip():
        return False, "文本不能为空"

    try:
        parsed = self._parse_fact(text)

        # 确定类型目录
        type_dir = self.atoms_dir / parsed["type"]
        type_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{parsed['slug']}-{timestamp}.md"
        atom_path = type_dir / filename

        # 写入原子文件
        content = f"""# {parsed['subject']}

{parsed['content']}

---
type: {parsed['type']}
created: {datetime.now().isoformat()}
"""

        atom_path.write_text(content, encoding='utf-8')

        return True, str(atom_path.relative_to(self.kb_dir))

    except Exception as e:
        return False, f"创建失败: {e}"
```

### 任务 A-5：导出 QuickCapture 类

**文件：** `lib/__init__.py`
**预估：** 1 分钟

```python
# 在现有导出列表中添加
from .quick_capture import QuickCapture
```

### 任务 A-6：添加 capture 命令

**文件：** `llm-wiki.py`
**预估：** 3 分钟

```python
# 在 imports 部分
from lib.quick_capture import QuickCapture

# 在 CLI 命令部分
@app.command("capture")
def capture_cmd(kb_dir: str, text: str):
    """一句话快速创建知识原子"""
    capture = QuickCapture(Path(kb_dir))
    success, result = capture.capture(text)

    if success:
        console.print(f"[green]✅ 已创建 {result}[/green]")
    else:
        console.print(f"[red]❌ {result}[/red]")
```

### 任务 A-7：验证 capture 命令

**预估：** 2 分钟

```bash
# 测试一句话捕获
llm-wiki capture ./test-kb "Redis 默认端口 6379"

# 验证文件创建
ls -la ./test-kb/atoms/facts/

# 预期：看到新创建的 atom 文件
```

---

## 任务组 B：Heads Up 主动推送 (Phase 2)

**类型：** 并行
**预估时间：** 20-25 分钟
**文件：**
- 创建: `lib/discovery.py`
- 修改: `SKILL.md`
- 修改: `lib/__init__.py`
- 修改: `llm-wiki.py`

### 任务 B-1：编写 DiscoveryEngine 类骨架

**文件：** `lib/discovery.py`
**预估：** 2 分钟

```python
"""智能发现引擎"""

from pathlib import Path
from typing import List, Dict, Optional
from .semantic import SemanticSearchEngine


class DiscoveryEngine:
    """智能发现引擎"""

    def __init__(self, kb_dir: Path, semantic_engine: Optional[SemanticSearchEngine] = None):
        self.kb_dir = Path(kb_dir)
        self.atoms_dir = self.kb_dir / "atoms"
        self.semantic_engine = semantic_engine

    def find_gaps(self) -> List[Dict]:
        """发现知识缺口"""
        raise NotImplementedError

    def find_relations(self, atom_id: str) -> List[Dict]:
        """发现潜在关联"""
        raise NotImplementedError

    def heads_up(self, context: str, top_k: int = 5) -> List[Dict]:
        """主动推送相关上下文"""
        raise NotImplementedError
```

### 任务 B-2：实现 find_gaps 方法

**文件：** `lib/discovery.py`
**预估：** 5 分钟

```python
def find_gaps(self) -> List[Dict]:
    """发现知识缺口"""
    gaps = []

    # 策略 1: 孤立节点（无链接的知识）
    for atom_file in self.atoms_dir.rglob("*.md"):
        content = atom_file.read_text(encoding='utf-8')

        # 检查是否有出链
        has_links = bool(re.search(r'\[\[.*?\]\]', content))

        if not has_links:
            gaps.append({
                "topic": atom_file.stem,
                "reason": "孤立节点：无链接到其他知识",
                "suggestion": f"考虑添加关联知识或补充上下文",
                "path": str(atom_file.relative_to(self.kb_dir))
            })

    # 策略 2: 过期知识（超过 90 天未更新）
    # ... 省略过期检测代码（约 10 行）

    return gaps
```

### 任务 B-3：实现 find_relations 方法

**文件：** `lib/discovery.py`
**预估：** 5 分钟

```python
def find_relations(self, atom_id: str) -> List[Dict]:
    """发现潜在关联"""
    if not self.semantic_engine:
        return []

    # 使用语义搜索找到相似内容
    atom_path = self.atoms_dir / f"{atom_id}.md"
    if not atom_path.exists():
        # 尝试在所有类型目录中查找
        for type_dir in self.atoms_dir.iterdir():
            if type_dir.is_dir():
                candidate = type_dir / f"{atom_id}.md"
                if candidate.exists():
                    atom_path = candidate
                    break

    if not atom_path.exists():
        return []

    content = atom_path.read_text(encoding='utf-8')

    # 语义搜索相似内容
    results = self.semantic_engine.search(content[:200], top_k=10)

    # 过滤掉自身
    return [
        {"atom_id": r["id"], "similarity": r["score"], "path": r["path"]}
        for r in results
        if r["id"] != atom_id
    ]
```

### 任务 B-4：实现 heads_up 方法

**文件：** `lib/discovery.py`
**预估：** 4 分钟

```python
def heads_up(self, context: str, top_k: int = 5) -> List[Dict]:
    """主动推送相关上下文"""
    if not self.semantic_engine:
        return []

    # 提取关键词（简单实现：提取英文单词和中文词汇）
    keywords = re.findall(r'[A-Z][a-z]+|[一-龥]{2,}', context)

    if not keywords:
        return []

    # 对每个关键词搜索
    results = []
    for keyword in keywords[:3]:  # 限制关键词数量
        search_results = self.semantic_engine.search(keyword, top_k=top_k)
        results.extend(search_results)

    # 去重并排序
    seen = set()
    unique_results = []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique_results.append(r)

    return unique_results[:top_k]
```

### 任务 B-5：导出 DiscoveryEngine 类

**文件：** `lib/__init__.py`
**预估：** 1 分钟

```python
# 在现有导出列表中添加
from .discovery import DiscoveryEngine
```

### 任务 B-6：添加 discovery 命令

**文件：** `llm-wiki.py`
**预估：** 3 分钟

```python
# 在 imports 部分
from lib.discovery import DiscoveryEngine

# 在 CLI 命令部分
@app.command("gaps")
def gaps_cmd(kb_dir: str):
    """发现知识缺口"""
    discovery = DiscoveryEngine(Path(kb_dir))
    gaps = discovery.find_gaps()

    if not gaps:
        console.print("[green]✅ 未发现明显知识缺口[/green]")
        return

    console.print(f"[yellow]发现 {len(gaps)} 个知识缺口：[/yellow]\n")
    for gap in gaps:
        console.print(f"  • {gap['topic']}: {gap['reason']}")


@app.command("relations")
def relations_cmd(kb_dir: str, atom_id: str):
    """发现潜在关联"""
    discovery = DiscoveryEngine(Path(kb_dir))
    relations = discovery.find_relations(atom_id)

    if not relations:
        console.print("[yellow]未发现潜在关联[/yellow]")
        return

    console.print(f"[cyan]发现 {len(relations)} 个潜在关联：[/cyan]\n")
    for r in relations:
        console.print(f"  • {r['atom_id']} (相似度: {r['similarity']:.2f})")
```

### 任务 B-7：更新 SKILL.md

**文件：** `SKILL.md`
**预估：** 5 分钟

在 SKILL.md 中添加主动行为定义：

```markdown
## 主动行为

当用户在讨论某个技术话题时，自动检查知识库：

1. **Heads Up 触发条件**：
   - 用户提到技术名词（如 "Redis", "Docker", "Kubernetes"）
   - 用户在描述问题或需求

2. **推送格式**：
   ```
   📚 相关知识：
   - [[atom-id-1]] - 简短描述
   - [[atom-id-2]] - 简短描述
   ```

3. **知识缺口检测**：
   - 发现用户多次提及但知识库无相关内容时：
   ```
   💡 发现知识缺口：
   你最近 3 次提到 Kubernetes，但知识库里还没有相关内容。
   要我帮你收集一些基础知识吗？
   ```
```

### 任务 B-8：验证 discovery 命令

**预估：** 2 分钟

```bash
# 测试缺口检测
llm-wiki gaps ./test-kb

# 测试关联发现
llm-wiki relations ./test-kb redis-default-port

# 预期：看到缺口或关联列表
```

---

## 任务组 C：图谱扩展 (Phase 4.1)

**类型：** 并行
**预估时间：** 15-20 分钟
**文件：**
- 扩展: `lib/visualizer.py`
- 修改: `llm-wiki.py`

### 任务 C-1：读取现有 visualizer.py

**文件：** `lib/visualizer.py`
**预估：** 1 分钟

```bash
# 读取现有代码，了解当前结构
cat lib/visualizer.py
```

### 任务 C-2：添加 generate_json_data 方法

**文件：** `lib/visualizer.py`
**预估：** 5 分钟

```python
def generate_json_data(self) -> Dict:
    """
    生成图谱 JSON 数据（供 API 使用）

    返回格式：
    {
        "nodes": [{id, label, type, description, path, color}, ...],
        "edges": [{id, source, target}, ...]
    }
    """
    nodes = []
    edges = []

    # 从知识库读取所有原子
    for atom_file in self.kb_dir.rglob("*.md"):
        # 解析 frontmatter 和内容
        # ... 实现节点生成

        # 解析链接
        # ... 实现边生成

    return {"nodes": nodes, "edges": edges}
```

### 任务 C-3：添加 generate_interactive_html 方法

**文件：** `lib/visualizer.py`
**预估：** 8 分钟

```python
def generate_interactive_html(self, output_path: Path) -> bool:
    """
    生成可交互的静态 HTML（不依赖服务器）

    支持操作：
    - 拖拽节点：调整布局
    - 点击节点：显示详情面板
    - 搜索过滤
    - 类型过滤
    """
    data = self.generate_json_data()

    html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>知识图谱 - 交互式视图</title>
    <!-- D3.js CDN -->
</head>
<body>
    <!-- 交互式图谱 HTML -->
    <script>
        // 图谱数据
        const data = {data_json};

        // D3.js 力导向图实现
        // ... 交互逻辑
    </script>
</body>
</html>
"""

    # 写入文件
    output_path.write_text(
        html_template.replace("{data_json}", json.dumps(data))
    )

    return True
```

### 任务 C-4：添加 --interactive 选项

**文件：** `llm-wiki.py`
**预估：** 3 分钟

```python
# 修改现有 visualize 命令
@app.command("visualize")
def visualize_cmd(kb_dir: str, interactive: bool = False):
    """可视化知识图谱"""
    visualizer = KnowledgeVisualizer(Path(kb_dir))

    if interactive:
        output_path = Path(kb_dir) / "views" / "knowledge-graph.html"
        visualizer.generate_interactive_html(output_path)
        console.print(f"[green]✅ 已生成交互式图谱: {output_path}[/green]")
    else:
        # 现有静态图谱逻辑
        pass
```

### 任务 C-5：验证交互式图谱

**预估：** 2 分钟

```bash
# 生成交互式图谱
llm-wiki visualize ./test-kb --interactive

# 打开文件验证
open ./test-kb/views/knowledge-graph.html

# 预期：可以看到可交互的图谱
```

---

## 任务组 D：时间线视图 (Phase 4.2)

**类型：** 并行
**预估时间：** 15-20 分钟
**文件：**
- 创建: `lib/timeline.py`
- 修改: `lib/__init__.py`
- 修改: `llm-wiki.py`

### 任务 D-1：编写 TimelineGenerator 类骨架

**文件：** `lib/timeline.py`
**预估：** 2 分钟

```python
"""时间线视图生成器"""

from pathlib import Path
from typing import Dict
from datetime import datetime
import json


class TimelineGenerator:
    """时间线视图生成器"""

    def __init__(self, kb_dir: Path):
        self.kb_dir = Path(kb_dir)
        self.atoms_dir = self.kb_dir / "atoms"

    def generate_json_data(self) -> Dict:
        """生成时间线 JSON 数据"""
        raise NotImplementedError

    def generate(self, output_path: Path) -> bool:
        """生成时间线 HTML"""
        raise NotImplementedError
```

### 任务 D-2：实现 generate_json_data 方法

**文件：** `lib/timeline.py`
**预估：** 5 分钟

```python
def generate_json_data(self) -> Dict:
    """生成时间线 JSON 数据"""
    events = []
    stats = {"total": 0, "by_type": {}, "by_month": {}}

    for atom_file in self.atoms_dir.rglob("*.md"):
        content = atom_file.read_text(encoding='utf-8')

        # 解析创建时间
        created_match = re.search(r'created:\s*(.+)', content)
        if created_match:
            created_str = created_match.group(1).strip()
            try:
                created = datetime.fromisoformat(created_str)
            except:
                created = datetime.fromtimestamp(atom_file.stat().st_mtime)
        else:
            created = datetime.fromtimestamp(atom_file.stat().st_mtime)

        # 解析类型
        type_match = re.search(r'type:\s*(\w+)', content)
        atom_type = type_match.group(1) if type_match else "unknown"

        events.append({
            "date": created.isoformat(),
            "atom_id": atom_file.stem,
            "title": atom_file.stem,
            "type": atom_type,
            "path": str(atom_file.relative_to(self.kb_dir))
        })

        # 更新统计
        stats["total"] += 1
        stats["by_type"][atom_type] = stats["by_type"].get(atom_type, 0) + 1

        month_key = created.strftime("%Y-%m")
        stats["by_month"][month_key] = stats["by_month"].get(month_key, 0) + 1

    # 按时间排序
    events.sort(key=lambda x: x["date"], reverse=True)

    return {"events": events, "stats": stats}
```

### 任务 D-3：实现 generate 方法

**文件：** `lib/timeline.py`
**预估：** 8 分钟

```python
def generate(self, output_path: Path) -> bool:
    """生成时间线 HTML"""
    data = self.generate_json_data()

    html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>知识时间线</title>
    <style>
        /* 时间线样式 */
    </style>
</head>
<body>
    <h1>知识时间线</h1>
    <div class="stats">
        总计: {total} 个知识原子
    </div>
    <div class="timeline">
        <!-- 时间线内容 -->
    </div>
    <script>
        const events = {events_json};
        // 渲染时间线
    </script>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        html_template
            .replace("{total}", str(data["stats"]["total"]))
            .replace("{events_json}", json.dumps(data["events"]))
    )

    return True
```

### 任务 D-4：导出 TimelineGenerator 类

**文件：** `lib/__init__.py`
**预估：** 1 分钟

```python
# 在现有导出列表中添加
from .timeline import TimelineGenerator
```

### 任务 D-5：添加 timeline 命令

**文件：** `llm-wiki.py`
**预估：** 3 分钟

```python
# 在 imports 部分
from lib.timeline import TimelineGenerator

# 在 CLI 命令部分
@app.command("timeline")
def timeline_cmd(kb_dir: str):
    """生成知识时间线"""
    timeline = TimelineGenerator(Path(kb_dir))
    output_path = Path(kb_dir) / "views" / "timeline.html"

    if timeline.generate(output_path):
        console.print(f"[green]✅ 已生成时间线: {output_path}[/green]")
    else:
        console.print("[red]❌ 生成失败[/red]")
```

### 任务 D-6：验证 timeline 命令

**预估：** 2 分钟

```bash
# 生成时间线
llm-wiki timeline ./test-kb

# 打开文件验证
open ./test-kb/views/timeline.html

# 预期：可以看到按时间排序的知识时间线
```

---

## 任务组 E：文件监控 (Phase 1.2)

**类型：** 串行
**依赖：** 任务组 A 完成
**预估时间：** 15-20 分钟
**文件：**
- 创建: `lib/watcher.py`
- 修改: `lib/__init__.py`
- 修改: `llm-wiki.py`

### 任务 E-1：编写 KnowledgeWatcher 类骨架

**文件：** `lib/watcher.py`
**预估：** 2 分钟

```python
"""文件监控自动摄入"""

from pathlib import Path
from typing import List, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from .registry import KBRegistry
from .quick_capture import QuickCapture


class KnowledgeWatcher(FileSystemEventHandler):
    """文件监控自动摄入"""

    def __init__(self, kb_dir: Path, registry: KBRegistry):
        self.kb_dir = Path(kb_dir)
        self.registry = registry
        self.quick_capture = QuickCapture(kb_dir)
        self.observer = Observer()
        self.progress_callback: Optional[Callable[[str], None]] = None

    def start(self, watch_paths: List[Path]) -> None:
        """开始监控"""
        raise NotImplementedError

    def stop(self) -> None:
        """停止监控"""
        raise NotImplementedError

    def on_file_created(self, event: FileSystemEvent) -> None:
        """文件创建事件"""
        raise NotImplementedError

    def on_file_modified(self, event: FileSystemEvent) -> None:
        """文件修改事件"""
        raise NotImplementedError

    def set_progress_callback(self, callback: Callable[[str], None]) -> None:
        """设置进度回调"""
        self.progress_callback = callback
```

### 任务 E-2：实现 start 和 stop 方法

**文件：** `lib/watcher.py`
**预估：** 3 分钟

```python
def start(self, watch_paths: List[Path]) -> None:
    """开始监控"""
    for path in watch_paths:
        if path.exists():
            self.observer.schedule(self, str(path), recursive=True)

    self.observer.start()

    if self.progress_callback:
        self.progress_callback(f"开始监控 {len(watch_paths)} 个目录...")

def stop(self) -> None:
    """停止监控"""
    self.observer.stop()
    self.observer.join()

    if self.progress_callback:
        self.progress_callback("监控已停止")
```

### 任务 E-3：实现文件事件处理

**文件：** `lib/watcher.py`
**预估：** 5 分钟

```python
def on_file_created(self, event: FileSystemEvent) -> None:
    """文件创建事件"""
    if event.is_directory:
        return

    file_path = Path(event.src_path)

    # 只处理 .md 文件
    if file_path.suffix != '.md':
        return

    # 忽略 atoms 目录（避免循环）
    if 'atoms' in file_path.parts:
        return

    if self.progress_callback:
        self.progress_callback(f"发现新文件: {file_path.name}")

    # 自动摄入
    try:
        content = file_path.read_text(encoding='utf-8')

        # 如果内容很短，使用 quick_capture
        if len(content) < 200:
            success, result = self.quick_capture.capture(content)
            if success:
                if self.progress_callback:
                    self.progress_callback(f"✅ 已摄入: {result}")
            else:
                if self.progress_callback:
                    self.progress_callback(f"⚠️ 摄入失败: {result}")
        else:
            # 较长内容，使用 registry 的 ingest 方法
            # ... 实现逻辑
            pass

    except Exception as e:
        if self.progress_callback:
            self.progress_callback(f"❌ 处理失败: {e}")

def on_file_modified(self, event: FileSystemEvent) -> None:
    """文件修改事件"""
    # 可以选择重新摄入或更新
    # 简单实现：忽略修改事件
    pass
```

### 任务 E-4：导出 KnowledgeWatcher 类

**文件：** `lib/__init__.py`
**预估：** 1 分钟

```python
# 在现有导出列表中添加
from .watcher import KnowledgeWatcher
```

### 任务 E-5：添加 watch 命令

**文件：** `llm-wiki.py`
**预估：** 3 分钟

```python
# 在 imports 部分
from lib.watcher import KnowledgeWatcher

# 在 CLI 命令部分
@app.command("watch")
def watch_cmd(
    kb_dir: str,
    paths: List[str] = None,
    auto_ingest: bool = True
):
    """文件监控自动摄入"""
    registry = KBRegistry(Path(kb_dir))
    watcher = KnowledgeWatcher(Path(kb_dir), registry)

    # 设置进度回调
    watcher.set_progress_callback(lambda msg: console.print(f"[dim]{msg}[/dim]"))

    # 默认监控 raw/ 目录
    watch_paths = [Path(p) for p in (paths or ["raw/"])]

    console.print(f"[cyan]开始监控... (Ctrl+C 停止)[/cyan]")
    watcher.start(watch_paths)

    try:
        # 保持运行
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        console.print("\n[yellow]监控已停止[/yellow]")
```

### 任务 E-6：验证 watch 命令

**预估：** 2 分钟

```bash
# 创建测试目录
mkdir -p ./test-kb/raw

# 启动监控（后台运行）
llm-wiki watch ./test-kb --paths raw/ &

# 创建新文件
echo "# Test Document\nRedis 默认端口 6379" > ./test-kb/raw/test.md

# 等待摄入（约 2 秒）
sleep 2

# 验证
llm-wiki query ./test-kb "Redis"

# 预期：看到自动摄入的知识
```

---

## 执行计划

### 阶段 1：并行执行（同时开始）

启动 4 个并行智能体：

```
智能体 1 → 任务组 A (quick_capture.py)
智能体 2 → 任务组 B (discovery.py)
智能体 3 → 任务组 C (visualizer 扩展)
智能体 4 → 任务组 D (timeline.py)
```

### 阶段 2：串行执行

等待任务组 A 完成后：

```
智能体 → 任务组 E (watcher.py)
```

### 预估总时间

- 并行组：约 20-25 分钟（最长任务组）
- 串行组：约 15-20 分钟
- **总计：约 35-45 分钟**

---

## 验收清单

### 任务组 A 验收

- [ ] `lib/quick_capture.py` 创建完成（< 150 行）
- [ ] `capture` 命令正常工作
- [ ] 测试：`llm-wiki capture ./test-kb "Redis 默认端口 6379"`

### 任务组 B 验收

- [ ] `lib/discovery.py` 创建完成（< 250 行）
- [ ] `gaps` 和 `relations` 命令正常工作
- [ ] `SKILL.md` 已更新

### 任务组 C 验收

- [ ] `lib/visualizer.py` 扩展完成
- [ ] `--interactive` 选项正常工作
- [ ] 生成的 HTML 可交互

### 任务组 D 验收

- [ ] `lib/timeline.py` 创建完成（< 150 行）
- [ ] `timeline` 命令正常工作
- [ ] 生成的 HTML 显示正确

### 任务组 E 验收

- [ ] `lib/watcher.py` 创建完成（< 200 行）
- [ ] `watch` 命令正常工作
- [ ] 文件监控自动摄入正常

---

## 风险提示

| 风险 | 缓解措施 |
|------|----------|
| 并行编辑 `lib/__init__.py` 冲突 | 合并时手动解决，最后统一导出 |
| 并行编辑 `llm-wiki.py` 冲突 | 合并时手动解决，或拆分为独立文件 |
| 测试环境不一致 | 使用同一个 test-kb 目录 |
