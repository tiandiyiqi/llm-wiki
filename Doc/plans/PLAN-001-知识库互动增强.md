# 实施计划：知识库互动增强 - 四大核心功能

## 元信息

| 属性 | 值 |
|------|-----|
| 状态 | completed |
| 创建时间 | 2026-06-19 |
| 完成时间 | 2026-06-19 |
| 所属阶段 | 阶段 3 - 开发 |
| 预估复杂度 | 高 |

---

## Context

用户请求增强 LLM Wiki 知识库的互动体验，从"命令驱动"升级为"智能对话"。

### 当前问题

1. **摄入门槛高**：用户需要准备完整文档，无法快速记录一句话知识
2. **被动检索**：用户需要主动搜索才知道知识库有什么
3. **命令记忆负担**：需要记住 CLI 命令或自然语言描述方式
4. **可视化单一**：仅有知识图谱，缺少时间线等多维视图

### 目标

实现四个核心功能：

1. **零感知摄入**：文件监控自动摄入 + 一句话创建原子
2. **Heads Up 主动推送**：上下文感知 + 知识缺口检测 + 关联发现
3. **自然对话**：Chat 模式 + 对话式编辑 + Web UI
4. **可视化探索**：实时图谱 + 时间线视图 + 交互式编辑

---

## 目标

将 LLM Wiki 从"命令行工具"升级为"智能知识伙伴"，实现：
- 用户无需记忆命令，自然对话即可操作知识库
- AI 主动发现知识缺口并推送相关信息
- 可视化帮助用户理解知识结构和演化

---

## 实施阶段

### Phase 1: 智能摄入增强 (P0)

**目标**：让摄入知识变得"零摩擦"

#### 1.1 一句话创建原子

**新模块**: `lib/quick_capture.py`

```python
class QuickCapture:
    """一句话快速创建知识原子"""

    def __init__(self, kb_dir: Path)
    def capture(self, text: str) -> Tuple[bool, str]
        """
        从一句话提取知识并创建原子

        示例输入：
        - "记一下：Redis 默认端口 6379"
        - "Ubuntu 22.04 LTS 支持到 2027 年"
        - "Nextcloud 需要 PHP 8.0+"

        返回：(成功?, 原子路径或错误信息)
        """
    def _parse_fact(self, text: str) -> Dict
    def _detect_type(self, text: str) -> str
```

**CLI 命令**:
```bash
llm-wiki capture ./my-kb "Redis 默认端口 6379"
# ✅ 已创建 atoms/facts/redis-default-port.md
```

**Claude Skill 集成**:
```
用户: 记一下：Redis 默认端口 6379
Claude: [调用 /llm-wiki capture]
        ✅ 已创建 atoms/facts/redis-default-port.md
```

#### 1.2 文件监控自动摄入

**新模块**: `lib/watcher.py`

```python
class KnowledgeWatcher:
    """文件监控自动摄入"""

    def __init__(self, kb_dir: Path, registry: KBRegistry)
    def start(self, watch_paths: List[Path]) -> None
    def stop(self) -> None
    def on_file_created(self, event: FileSystemEvent) -> None
    def on_file_modified(self, event: FileSystemEvent) -> None
    def set_progress_callback(self, callback: Callable[[str], None]) -> None
```

**CLI 命令**:
```bash
llm-wiki watch ./my-kb --paths raw/ --auto-ingest

# 后台运行，监控 raw/ 目录
# 新文件自动摄入，静默完成
# 按 Ctrl+C 停止
```

**依赖**: `watchdog` 库

**文件**:
- 创建: `lib/quick_capture.py` (~150 行)
- 创建: `lib/watcher.py` (~200 行)
- 修改: `llm-wiki.py` (添加 `capture` 和 `watch` 命令)
- 修改: `lib/__init__.py` (导出新类)

---

### Phase 2: Heads Up 主动推送 (P0)

**目标**：AI 主动发现和推送，而非等待用户搜索

#### 2.1 知识缺口检测

**新模块**: `lib/discovery.py`

```python
class DiscoveryEngine:
    """智能发现引擎"""

    def __init__(self, kb_dir: Path, semantic_engine: SemanticSearchEngine)

    def find_gaps(self) -> List[Dict]:
        """
        发现知识缺口

        检测策略：
        1. 高频提及但无知识原子（从对话/搜索中统计）
        2. 孤立节点（无链接的知识）
        3. 过期知识（很久未更新）

        返回：[{topic, reason, suggestion}, ...]
        """

    def find_relations(self, atom_id: str) -> List[Dict]:
        """
        发现潜在关联

        基于语义相似度 + 标签重叠 + 类型关联
        返回可能相关但未建立链接的原子
        """

    def heads_up(self, context: str, top_k: int = 5) -> List[Dict]:
        """
        主动推送相关上下文

        输入：用户当前讨论的话题
        返回：最相关的知识点（用于 Claude Code 集成）
        """
```

#### 2.2 Claude Code Skill 集成

修改 `SKILL.md`，添加主动推送行为：

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

**文件**:
- 创建: `lib/discovery.py` (~250 行)
- 修改: `SKILL.md` (添加主动行为定义)
- 修改: `lib/__init__.py` (导出新类)

---

### Phase 3: Web UI (P0) - 待讨论

**目标**：为人类提供知识库的可视化交互界面

> **状态**: 必选，但实现细节待讨论
>
> **原因**: AI 操作知识库不需要界面，但人类需要。
> CLI Chat 模式已移除，因为相比 Claude Code 等 Agent 对话无优势。

#### 3.1 设计要点（待讨论）

**核心问题**：
1. **技术栈选择**：Flask vs FastAPI vs 纯静态？
2. **与可视化的融合**：如何与 Phase 4 的图谱、时间线整合？
3. **功能范围**：
   - 知识浏览（列表、详情、搜索）
   - 知识编辑（创建、修改、删除原子）
   - 可视化入口（图谱、时间线）
   - 系统设置（注册知识库、配置）

**参考设计**：
- Mem Chat 界面
- Notion AI 界面
- Obsidian + AI Copilot 侧边栏

#### 3.2 API 设计（初步）

```
GET  /api/kb                    # 列出知识库
GET  /api/kb/{name}             # 知识库详情
GET  /api/kb/{name}/atoms       # 原子列表
GET  /api/kb/{name}/atoms/{id}  # 原子详情
POST /api/kb/{name}/atoms       # 创建原子
PUT  /api/kb/{name}/atoms/{id}  # 更新原子
DELETE /api/kb/{name}/atoms/{id} # 删除原子
GET  /api/kb/{name}/visualize   # 图谱视图
GET  /api/kb/{name}/timeline    # 时间线视图
```

**文件**（待讨论后确定）:
- 创建: `lib/web_server.py`
- 创建: `views/` 目录（前端资源）
- 修改: `llm-wiki.py` (添加 `web` 命令)

---

### Phase 4: 可视化探索增强 (P1)

**目标**：多维视图帮助用户理解和探索知识

> **状态**: 代码实现部分可以开始，前端融合待 Web UI 设计确定

#### 4.1 实时图谱（后端部分）

**扩展现有 `lib/visualizer.py`**:

```python
class KnowledgeVisualizer:
    # 现有方法...

    def generate_json_data(self) -> Dict:
        """
        生成图谱 JSON 数据（供 API 使用）

        返回格式：
        {
            "nodes": [{id, label, type, description, path, color}, ...],
            "edges": [{id, source, target}, ...]
        }
        """

    def generate_interactive_html(self) -> str:
        """
        生成可交互的静态 HTML（不依赖服务器）

        支持操作：
        - 拖拽节点：调整布局
        - 点击节点：显示详情面板
        - 搜索过滤
        - 类型过滤
        """
```

**CLI 命令**:
```bash
llm-wiki visualize ./my-kb --interactive

# 生成 views/knowledge-graph.html
# 纯静态文件，可直接打开
# 支持交互但不支持实时更新
```

#### 4.2 时间线视图（后端部分）

**新模块**: `lib/timeline.py`

```python
class TimelineGenerator:
    """时间线视图生成器"""

    def __init__(self, kb_dir: Path)
    
    def generate_json_data(self) -> Dict:
        """
        生成时间线 JSON 数据（供 API 使用）

        返回格式：
        {
            "events": [{date, atom_id, title, type, path}, ...],
            "stats": {total, by_type, by_month}
        }
        """

    def generate(self, output_path: Path) -> bool:
        """
        生成时间线 HTML（纯静态）

        按时间排序知识原子：
        - 日视图：今天添加的知识
        - 周视图：本周添加的知识
        - 月视图：本月添加的知识
        - 全览：所有知识的时序分布
        """
```

**CLI 命令**:
```bash
llm-wiki timeline ./my-kb

# 输出到 views/timeline.html
# 纯静态文件，可直接打开
```

#### 4.3 与 Web UI 融合（待讨论）

当 Web UI 设计确定后：
- 图谱和时间线可作为 API 端点
- 前端直接嵌入或独立页面
- 统一导航和交互体验

**文件**:
- 创建: `lib/timeline.py` (~150 行)
- 扩展: `lib/visualizer.py` (添加 JSON 数据导出)
- 创建: `views/timeline.html` (~400 行)
- 修改: `llm-wiki.py` (添加 `timeline` 命令)
- 修改: `lib/__init__.py` (导出新类)

---

## 执行顺序

**立即可执行**：
1. Phase 1: 智能摄入增强（quick_capture.py, watcher.py）
2. Phase 2: Heads Up 主动推送（discovery.py, SKILL.md）
3. Phase 4: 可视化探索增强（timeline.py, visualizer.py 扩展）

**待讨论后执行**：
4. Phase 3: Web UI 设计与实现

---

## 依赖关系

```
Phase 1 (智能摄入) ← 可独立开始
    ├─ quick_capture.py (独立)
    └─ watcher.py (依赖 quick_capture)

Phase 2 (Heads Up) ← 可独立开始
    └─ discovery.py (依赖 semantic.py, querier.py)

Phase 4 (可视化增强) ← 可独立开始
    ├─ visualizer.py 扩展 (独立)
    └─ timeline.py (独立)

Phase 3 (Web UI) ← 待讨论，将整合以上所有功能
    └─ web_server.py + 前端
```

---

## 风险

| 级别 | 风险 | 缓解措施 |
|------|------|----------|
| HIGH | 一句话解析准确率低 | 使用 LLM 辅助解析，提供确认机制 |
| HIGH | Chat 模式需要 LLM API | 提供多种后端选项，支持本地模型 |
| MEDIUM | 文件监控资源占用 | 使用增量摄入，支持忽略规则 |
| MEDIUM | 实时图谱性能 | 限制节点数量，使用虚拟滚动 |
| LOW | Web UI 安全性 | 仅绑定 localhost，无需认证 |

---

## 预估复杂度：高

| 阶段 | 状态 | 预估工时 | 核心文件 |
|------|------|----------|----------|
| Phase 1 | 可执行 | 4-6 小时 | quick_capture.py, watcher.py |
| Phase 2 | 可执行 | 3-4 小时 | discovery.py, SKILL.md |
| Phase 4 | 可执行 | 4-5 小时 | timeline.py, visualizer.py 扩展 |
| Phase 3 | 待讨论 | 6-8 小时 | web_server.py, 前端资源 |
| **可执行部分** | - | **11-15 小时** | |

---

## 验证计划

### Phase 1 验证
```bash
# 测试一句话捕获
llm-wiki capture ./test-kb "Redis 默认端口 6379"
llm-wiki query ./test-kb "Redis"

# 测试文件监控
llm-wiki watch ./test-kb --paths raw/ --auto-ingest
echo "# Test Document" > raw/test.md
# 等待自动摄入
llm-wiki query ./test-kb "Test"
```

### Phase 2 验证
```bash
# 测试缺口检测
llm-wiki gaps ./test-kb

# 测试关联发现
llm-wiki relations ./test-kb redis-installation

# 测试 Heads Up (Claude Code 集成)
# 在对话中提到 Redis，观察是否推送相关知识
```

### Phase 4 验证
```bash
# 测试交互式图谱
llm-wiki visualize ./test-kb --interactive
# 打开 views/knowledge-graph.html，验证交互功能

# 测试时间线
llm-wiki timeline ./test-kb
# 打开 views/timeline.html，验证时间线显示
```

### Phase 3 验证（待讨论后）
```bash
# 启动 Web 服务器
llm-wiki web ./test-kb --port 8080
# 打开 http://localhost:8080
# 验证知识浏览、编辑、可视化功能
```

---

## 完成标准

**可执行部分**：
- [ ] Phase 1: 一句话捕获 + 文件监控正常工作
- [ ] Phase 2: Heads Up 在 Claude Code 中生效
- [ ] Phase 4: 交互式图谱 + 时间线可视化正常
- [ ] 所有新增模块 < 350 行
- [ ] 所有测试通过

**待讨论部分**：
- [ ] Phase 3: Web UI 技术栈确定
- [ ] Phase 3: 与可视化融合方案确定
- [ ] Phase 3: 功能范围确定
- [ ] README 更新（新功能文档）
