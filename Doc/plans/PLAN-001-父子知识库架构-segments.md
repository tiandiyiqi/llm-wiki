# 任务组结构：父子知识库架构

## 元信息
- 源计划：PLAN-001-父子知识库架构.md
- 创建时间：2026-06-19
- 任务组数量：8
- **状态：已完成** ✅

## 依赖分析总览

### 阶段依赖图

```
阶段 1（数据结构） ──┬──→ 阶段 2（KBInitializer）
                    │
                    ├──→ 阶段 3（KBRegistry）──┬──→ 阶段 4（聚合查询）
                    │                          │
                    └──→ 阶段 5（导出导入）    │
                                               │
阶段 2（KBInitializer）───→ 阶段 3（KBRegistry）─┘
                              │
阶段 2（KBInitializer）───→ 阶段 5（导出导入）

阶段 1-5 全部完成 ──→ 阶段 6（文档）
阶段 1-6 全部完成 ──→ 阶段 7（测试）
```

### 并行机会识别

| 并行组 | 可并行内容 | 收益评估 |
|--------|------------|----------|
| A+B | 阶段 2 与阶段 3 部分任务 | 中等（共享 registry.json 操作） |
| C+D | 阶段 4 与阶段 5（弱依赖） | 高（完全独立类） |
| 文档预备 | 阶段 6 可在阶段 5 完成前开始草稿 | 低（需后期更新） |

### 资源冲突分析

| 资源 | 冲突任务 | 建议 |
|------|----------|------|
| `llm-wiki.py` | 所有阶段 | 串行修改同一文件 |
| `KBRegistry` 类 | 阶段 1、3 | 合并为同一任务组 |
| `registry.json` 结构 | 阶段 1、3 | 需在同一任务组内完成 |
| `.kb-meta.json` 格式 | 阶段 1、2、5 | 阶段 1 先定义，后续依赖 |

---

## 执行顺序

### 任务组 1：数据结构基础（串行）

**类型：** 串行
**前置条件：** 无

#### 任务 1-1：设计 .kb-meta.json 格式
- [ ] SUB-TASK-001: 在 KBRegistry 类中定义 KB_META_SCHEMA 常量
  - 依赖：无
  - 文件：`llm-wiki.py`（约第 80 行附近）
  - 复杂度：低
  - 代码片段：
    ```python
    KB_META_SCHEMA = {
        'kb_type': 'standalone',  # standalone/parent/child
        'name': '',
        'children': [],
        'children_paths': {},
        'parent': None,
        'parent_path': None
    }
    ```

#### 任务 1-2：扩展注册表结构定义
- [ ] SUB-TASK-002: 在 registry.json 的 knowledge_bases 条目中新增字段定义
  - 依赖：SUB-TASK-001
  - 文件：`llm-wiki.py`（`KBRegistry.register()` 方法，约第 151-186 行）
  - 复杂度：低
  - 新增字段：`kb_type`、`parent`、`children`、`children_paths`

#### 任务 1-3：添加 kb_meta 读写辅助方法
- [ ] SUB-TASK-003: 在 KBRegistry 类中添加 `_read_kb_meta()` 和 `_write_kb_meta()` 方法
  - 依赖：SUB-TASK-002
  - 文件：`llm-wiki.py`（约第 280 行后新增）
  - 复杂度：低

---

### 任务组 2：KBInitializer 扩展（串行）

**类型：** 串行
**前置条件：** 任务组 1 完成

#### 任务 2-1：修改 KBInitializer 构造函数
- [ ] SUB-TASK-004: 添加新参数到 `KBInitializer.__init__()`
  - 依赖：SUB-TASK-003
  - 文件：`llm-wiki.py`（约第 650-655 行）
  - 复杂度：低
  - 新参数：
    ```python
    def __init__(self, kb_dir: Path, is_parent: bool = False,
                 is_child: bool = False, parent_kb: Optional[Path] = None):
    ```

#### 任务 2-2：实现 init_parent() 方法
- [ ] SUB-TASK-005: 创建父知识库初始化逻辑
  - 依赖：SUB-TASK-004
  - 文件：`llm-wiki.py`（KBInitializer 类内新增方法）
  - 复杂度：中
  - 内容：
    - 创建父知识库目录结构（同普通 + atoms/）
    - 创建 `.kb-meta.json`（kb_type: "parent"）
    - 初始化空 children 列表

#### 任务 2-3：实现 init_child() 方法
- [ ] SUB-TASK-006: 创建子知识库初始化逻辑
  - 依赖：SUB-TASK-005
  - 文件：`llm-wiki.py`（KBInitializer 类内新增方法）
  - 复杂度：中
  - 内容：
    - 在父知识库目录下创建子目录
    - 创建子知识库目录结构
    - 创建 `.kb-meta.json`（kb_type: "child"）
    - 更新父知识库的 `.kb-meta.json`（添加 children）

#### 任务 2-4：重构 init() 方法
- [ ] SUB-TASK-007: 修改现有 init() 方法以支持三种模式
  - 依赖：SUB-TASK-006
  - 文件：`llm-wiki.py`（约第 656-738 行）
  - 复杂度：中
  - 内容：
    - 根据 is_parent/is_child 参数分发到不同方法
    - 保持原有 standalone 模式不变

#### 任务 2-5：更新 argparse init 子命令
- [ ] SUB-TASK-008: 添加 --parent、--child、--parent-kb 参数
  - 依赖：SUB-TASK-007
  - 文件：`llm-wiki.py`（约第 1951-1959 行）
  - 复杂度：低
  - 内容：
    ```python
    init_parser.add_argument('--parent', action='store_true', help='创建父知识库')
    init_parser.add_argument('--child', action='store_true', help='创建子知识库')
    init_parser.add_argument('--parent-kb', type=Path, help='父知识库路径')
    ```

#### 任务 2-6：更新 cmd_init() 函数
- [ ] SUB-TASK-009: 处理新参数并调用 KBInitializer
  - 依赖：SUB-TASK-008
  - 文件：`llm-wiki.py`（约第 1761-1777 行）
  - 复杂度：低

---

### 任务组 3：KBRegistry 扩展（串行）

**类型：** 串行
**前置条件：** 任务组 1 完成（可与任务组 2 部分并行）

#### 任务 3-1：扩展 register() 方法
- [ ] SUB-TASK-010: 支持 kb_type 和 parent 参数
  - 依赖：SUB-TASK-002
  - 文件：`llm-wiki.py`（约第 151-186 行）
  - 复杂度：中
  - 内容：
    - 新增参数：`kb_type: str = 'standalone'`、`parent: Optional[str] = None`
    - 自动更新父知识库的 children 字段
    - 读取并写入 `.kb-meta.json`

#### 任务 3-2：扩展 list() 方法
- [ ] SUB-TASK-011: 显示层级结构和 kb_type
  - 依赖：SUB-TASK-010
  - 文件：`llm-wiki.py`（约第 214-230 行）
  - 复杂度：中
  - 内容：
    - 父知识库显示子知识库列表
    - 子知识库标注父级名称
    - 使用树形结构展示（如：`office -> word, powerpoint`）

#### 任务 3-3：新增 get_children() 方法
- [ ] SUB-TASK-012: 返回指定知识库的所有子知识库
  - 依赖：SUB-TASK-010
  - 文件：`llm-wiki.py`（KBRegistry 类内新增）
  - 复杂度：低

#### 任务 3-4：新增 get_parent() 方法
- [ ] SUB-TASK-013: 返回指定知识库的父知识库
  - 依赖：SUB-TASK-010
  - 文件：`llm-wiki.py`（KBRegistry 类内新增）
  - 复杂度：低

#### 任务 3-5：扩展 info() 输出
- [ ] SUB-TASK-014: 显示父子关系和聚合统计
  - 依赖：SUB-TASK-011、SUB-TASK-012、SUB-TASK-013
  - 文件：`llm-wiki.py`（约第 1715-1758 行）
  - 复杂度：中
  - 内容：
    - 父知识库显示：子知识库列表、聚合概念数（所有子库总和）
    - 子知识库显示：父知识库名称、路径

#### 任务 3-6：更新 cmd_register() 函数
- [ ] SUB-TASK-015: 处理 --parent 参数
  - 依赖：SUB-TASK-010
  - 文件：`llm-wiki.py`（约第 1652-1664 行）
  - 复杂度：低

#### 任务 3-7：更新 argparse register 子命令
- [ ] SUB-TASK-016: 添加 --parent 参数
  - 依赖：SUB-TASK-015
  - 文件：`llm-wiki.py`（约第 1961-1968 行）
  - 复杂度：低

---

### 任务组 4：聚合查询（串行）

**类型：** 串行
**前置条件：** 任务组 2、任务组 3 完成

#### 任务 4-1：新增 AggregatedQuerier 类骨架
- [ ] SUB-TASK-017: 创建新类的基本结构
  - 依赖：SUB-TASK-012（get_children）
  - 文件：`llm-wiki.py`（约第 1069 行后新增）
  - 复杂度：低
  - 内容：
    ```python
    class AggregatedQuerier:
        def __init__(self, kb_dir: Path, registry: KBRegistry):
            self.kb_dir = kb_dir
            self.registry = registry
            self.children = []
    ```

#### 任务 4-2：实现 discover_children() 方法
- [ ] SUB-TASK-018: 发现并加载所有子知识库
  - 依赖：SUB-TASK-017
  - 文件：`llm-wiki.py`（AggregatedQuerier 类内）
  - 复杂度：中
  - 内容：
    - 读取 `.kb-meta.json` 获取 children_paths
    - 加载每个子知识库的 concepts

#### 任务 4-3：实现 aggregate_query() 方法
- [ ] SUB-TASK-019: 聚合搜索所有知识库
  - 依赖：SUB-TASK-018
  - 文件：`llm-wiki.py`（AggregatedQuerier 类内）
  - 复杂度：高
  - 内容：
    - 并行查询父级 + 所有子级
    - 合并结果，添加 source 字段
    - 去重（相同 atom_id）
    - 按相关性排序

#### 任务 4-4：修改 cmd_query() 函数
- [ ] SUB-TASK-020: 检测父知识库并调用 AggregatedQuerier
  - 依赖：SUB-TASK-019
  - 文件：`llm-wiki.py`（约第 1806-1847 行）
  - 复杂度：中
  - 内容：
    - 检测 kb_type 是否为 parent
    - 输出时显示来源（父级 vs 子级）
    - 添加聚合查询提示信息

#### 任务 4-5：更新 argparse query 子命令
- [ ] SUB-TASK-021: 添加 --child 参数用于过滤
  - 依赖：SUB-TASK-020
  - 文件：`llm-wiki.py`（约第 2006-2013 行）
  - 复杂度：低

---

### 任务组 5：导出导入扩展（串行）

**类型：** 串行
**前置条件：** 任务组 1、任务组 2 完成（可与任务组 4 并行）

#### 任务 5-1：修改 OKFExporter 构造函数
- [ ] SUB-TASK-022: 添加 include_children 参数
  - 依赖：SUB-TASK-003（kb_meta 读写）
  - 文件：`llm-wiki.py`（约第 492-505 行）
  - 复杂度：低

#### 任务 5-2：实现 _detect_kb_type() 方法
- [ ] SUB-TASK-023: 检测知识库类型
  - 依赖：SUB-TASK-022
  - 文件：`llm-wiki.py`（OKFExporter 类内）
  - 复杂度：低
  - 内容：
    - 读取 `.kb-meta.json`
    - 返回 kb_type

#### 任务 5-3：实现 _pack_children() 方法
- [ ] SUB-TASK-024: 打包子知识库到 tarball
  - 依赖：SUB-TASK-023
  - 文件：`llm-wiki.py`（OKFExporter 类内）
  - 复杂度：中
  - 内容：
    - 根据 children_paths 发现子知识库
    - 将子知识库内容打包到 tarball

#### 任务 5-4：修改 export() 方法
- [ ] SUB-TASK-025: 支持 --include-children 参数
  - 依赖：SUB-TASK-024
  - 文件：`llm-wiki.py`（约第 507-550 行）
  - 复杂度：中
  - 内容：
    - 父知识库默认仅导出父级自身
    - include_children=true 时打包所有子知识库
    - 子知识库仅打包自己

#### 任务 5-5：修改 OKFImporter 构造函数
- [ ] SUB-TASK-026: 添加父子结构恢复支持
  - 依赖：SUB-TASK-003
  - 文件：`llm-wiki.py`（约第 579-587 行）
  - 复杂度：低

#### 任务 5-6：修改 import_bundle() 方法
- [ ] SUB-TASK-027: 检测并恢复父子结构
  - 依赖：SUB-TASK-026
  - 文件：`llm-wiki.py`（约第 588-646 行）
  - 复杂度：中
  - 内容：
    - 检测 bundle manifest 是否包含子知识库
    - 恢复完整父子结构
    - 更新 `.kb-meta.json`

#### 任务 5-7：更新 cmd_export() 函数
- [ ] SUB-TASK-028: 处理 --include-children 参数
  - 依赖：SUB-TASK-025
  - 文件：`llm-wiki.py`（约第 1906-1918 行）
  - 复杂度：低

#### 任务 5-8：更新 argparse export 子命令
- [ ] SUB-TASK-029: 添加 --include-children 参数
  - 依赖：SUB-TASK-028
  - 文件：`llm-wiki.py`（约第 2027-2034 行）
  - 复杂度：低

---

### 任务组 6：文档更新（串行）

**类型：** 串行
**前置条件：** 任务组 1-5 全部完成

#### 任务 6-1：更新 README.md 父子知识库章节
- [ ] SUB-TASK-030: 添加功能说明和使用示例
  - 依赖：SUB-TASK-001 至 SUB-TASK-029
  - 文件：`README.md`
  - 复杂度：中
  - 内容：
    - 添加"父子知识库架构"章节
    - 目录结构示例
    - 命令示例

#### 任务 6-2：更新 README.md 命令参考
- [ ] SUB-TASK-031: 更新命令参数表格
  - 依赖：SUB-TASK-030
  - 文件：`README.md`
  - 复杂度：低
  - 内容：
    - init 命令新增参数
    - register 命令新增参数
    - query 命令新增参数
    - export 命令新增参数

#### 任务 6-3：更新 SKILL.md
- [ ] SUB-TASK-032: 添加父子知识库架构说明
  - 依赖：SUB-TASK-030
  - 文件：`SKILL.md`
  - 复杂度：低

#### 任务 6-4：更新 CLI 文件头注释
- [ ] SUB-TASK-033: 更新 llm-wiki.py 文件头 Usage 部分
  - 依赖：SUB-TASK-031
  - 文件：`llm-wiki.py`（第 1-30 行）
  - 复杂度：低

---

### 任务组 7：测试验证（串行）

**类型：** 串行
**前置条件：** 任务组 1-6 全部完成

#### 任务 7-1：创建父知识库
- [ ] SUB-TASK-034: 测试 init --parent 命令
  - 依赖：SUB-TASK-009
  - 文件：无（命令行测试）
  - 复杂度：低
  - 命令：
    ```bash
    python3 llm-wiki.py init /tmp/office-kb --parent --name office
    ```

#### 任务 7-2：创建子知识库 Word
- [ ] SUB-TASK-035: 测试 init --child 命令
  - 依赖：SUB-TASK-034
  - 文件：无（命令行测试）
  - 复杂度：低
  - 命令：
    ```bash
    python3 llm-wiki.py init /tmp/office-kb/word --child --parent-kb /tmp/office-kb --name word
    ```

#### 任务 7-3：创建子知识库 PowerPoint
- [ ] SUB-TASK-036: 测试第二个子知识库
  - 依赖：SUB-TASK-035
  - 文件：无（命令行测试）
  - 复杂度：低
  - 命令：
    ```bash
    python3 llm-wiki.py init /tmp/office-kb/powerpoint --child --parent-kb /tmp/office-kb --name powerpoint
    ```

#### 任务 7-4：注册知识库
- [ ] SUB-TASK-037: 测试 register 命令（含 --parent）
  - 依赖：SUB-TASK-036
  - 文件：无（命令行测试）
  - 复杂度：低
  - 命令：
    ```bash
    python3 llm-wiki.py register /tmp/office-kb --name office
    python3 llm-wiki.py register /tmp/office-kb/word --name word --parent office
    ```

#### 任务 7-5：验证 list/info 输出
- [ ] SUB-TASK-038: 测试层级显示
  - 依赖：SUB-TASK-037
  - 文件：无（命令行测试）
  - 复杂度：低
  - 命令：
    ```bash
    python3 llm-wiki.py list
    python3 llm-wiki.py info office
    ```

#### 任务 7-6：添加测试数据
- [ ] SUB-TASK-039: 在父/子知识库中创建测试原子
  - 依赖：SUB-TASK-037
  - 文件：`/tmp/office-kb/atoms/...`（手动创建或使用 ingest）
  - 复杂度：低
  - 内容：
    - 在父知识库创建一个 method 原子
    - 在 word 子知识库创建一个 method 原子
    - 在 powerpoint 子知识库创建一个 method 原子

#### 任务 7-7：测试聚合查询
- [ ] SUB-TASK-040: 测试父知识库聚合搜索
  - 依赖：SUB-TASK-039
  - 文件：无（命令行测试）
  - 复杂度：低
  - 命令：
    ```bash
    python3 llm-wiki.py query office "格式化"
    ```

#### 任务 7-8：测试独立导出
- [ ] SUB-TASK-041: 测试子知识库独立导出
  - 依赖：SUB-TASK-039
  - 文件：无（命令行测试）
  - 复杂度：低
  - 命令：
    ```bash
    python3 llm-wiki.py export word -o /tmp/word-bundle.tar.gz
    ```

#### 任务 7-9：测试包含子库导出
- [ ] SUB-TASK-042: 测试父知识库 --include-children 导出
  - 依赖：SUB-TASK-041
  - 文件：无（命令行测试）
  - 复杂度：低
  - 命令：
    ```bash
    python3 llm-wiki.py export office -o /tmp/office-full-bundle.tar.gz --include-children
    ```

#### 任务 7-10：测试导入恢复
- [ ] SUB-TASK-043: 测试导入并验证父子结构恢复
  - 依赖：SUB-TASK-042
  - 文件：无（命令行测试）
  - 复杂度：低
  - 命令：
    ```bash
    python3 llm-wiki.py import /tmp/office-full-bundle.tar.gz -o /tmp/restored-kb --overwrite
    python3 llm-wiki.py info /tmp/restored-kb
    ```

---

### 任务组 8：最终验证（串行）

**类型：** 串行
**前置条件：** 任务组 7 全部通过

#### 任务 8-1：清理测试数据
- [ ] SUB-TASK-044: 清理 /tmp 测试目录
  - 依赖：SUB-TASK-043
  - 文件：无
  - 复杂度：低

#### 任务 8-2：提交代码
- [ ] SUB-TASK-045: Git commit 所有变更
  - 依赖：SUB-TASK-044
  - 文件：`.git`
  - 复杂度：低

---

## 执行顺序可视化

```
执行顺序：

1️⃣ 任务组 A：数据结构基础（串行）
   ├─ SUB-TASK-001：定义 KB_META_SCHEMA
   ├─ SUB-TASK-002：扩展注册表字段
   └─ SUB-TASK-003：添加 kb_meta 读写方法
       ↓

2️⃣ 任务组 B：KBInitializer 扩展（串行）
   ├─ SUB-TASK-004：修改构造函数
   ├─ SUB-TASK-005：实现 init_parent()
   ├─ SUB-TASK-006：实现 init_child()
   ├─ SUB-TASK-007：重构 init()
   ├─ SUB-TASK-008：更新 argparse
   └─ SUB-TASK-009：更新 cmd_init()
       ↓

3️⃣ 任务组 C：KBRegistry 扩展（串行）
   ├─ SUB-TASK-010：扩展 register()
   ├─ SUB-TASK-011：扩展 list()
   ├─ SUB-TASK-012：新增 get_children()
   ├─ SUB-TASK-013：新增 get_parent()
   ├─ SUB-TASK-014：扩展 info()
   ├─ SUB-TASK-015：更新 cmd_register()
   └─ SUB-TASK-016：更新 argparse
       ↓

4️⃣ 任务组 D：聚合查询（串行）← 与 E 可并行
   ├─ SUB-TASK-017：AggregatedQuerier 骨架
   ├─ SUB-TASK-018：discover_children()
   ├─ SUB-TASK-019：aggregate_query()
   ├─ SUB-TASK-020：修改 cmd_query()
   └─ SUB-TASK-021：更新 argparse
       ↓

5️⃣ 任务组 E：导出导入扩展（串行）← 与 D 可并行
   ├─ SUB-TASK-022：OKFExporter 构造函数
   ├─ SUB-TASK-023：_detect_kb_type()
   ├─ SUB-TASK-024：_pack_children()
   ├─ SUB-TASK-025：修改 export()
   ├─ SUB-TASK-026：OKFImporter 构造函数
   ├─ SUB-TASK-027：修改 import_bundle()
   ├─ SUB-TASK-028：更新 cmd_export()
   └─ SUB-TASK-029：更新 argparse
       ↓

6️⃣ 任务组 F：文档更新（串行）
   ├─ SUB-TASK-030：README 父子知识库章节
   ├─ SUB-TASK-031：README 命令参考
   ├─ SUB-TASK-032：SKILL.md
   └─ SUB-TASK-033：CLI 文件头
       ↓

7️⃣ 任务组 G：测试验证（串行）
   ├─ SUB-TASK-034：创建父知识库
   ├─ SUB-TASK-035：创建子知识库 Word
   ├─ SUB-TASK-036：创建子知识库 PowerPoint
   ├─ SUB-TASK-037：注册知识库
   ├─ SUB-TASK-038：验证 list/info
   ├─ SUB-TASK-039：添加测试数据
   ├─ SUB-TASK-040：测试聚合查询
   ├─ SUB-TASK-041：测试独立导出
   ├─ SUB-TASK-042：测试包含子库导出
   └─ SUB-TASK-043：测试导入恢复
       ↓

8️⃣ 任务组 H：最终验证（串行）
   ├─ SUB-TASK-044：清理测试数据
   └─ SUB-TASK-045：提交代码
```

---

## 并行执行建议

### 高收益并行组合

| 组合 | 任务组 D + 任务组 E | 预估节省时间 |
|------|---------------------|--------------|
| 收益 | 两个任务组涉及不同类，无文件冲突 | 约 30 分钟 |
| 条件 | 任务组 C 完成后同时启动 | 需两个执行智能体 |

### 中收益并行组合

| 组合 | 任务组 B + 任务组 C 部分 | 预估节省时间 |
|------|--------------------------|--------------|
| 收益 | KBRegistry.register() 修改可独立进行 | 约 15 分钟 |
| 风险 | 可能产生 registry.json 结构冲突 | 需协调 |

### 低收益并行组合

| 组合 | 文档预备（任务组 F） | 预估节省时间 |
|------|---------------------|--------------|
| 收益 | 可提前编写文档草稿 | 约 5 分钟 |
| 风险 | 功能完成前文档不准确 | 需后期更新 |

---

## 预估时间统计

| 任务组 | 子任务数 | 预估时间 |
|--------|----------|----------|
| 任务组 1 | 3 | 15 分钟 |
| 任务组 2 | 6 | 45 分钟 |
| 任务组 3 | 7 | 40 分钟 |
| 任务组 4 | 5 | 50 分钟 |
| 任务组 5 | 8 | 45 分钟 |
| 任务组 6 | 4 | 20 分钟 |
| 任务组 7 | 10 | 30 分钟 |
| 任务组 8 | 2 | 5 分钟 |
| **总计** | **45** | **约 3.5 小时** |

注：预估时间基于串行执行，并行执行可节省约 30-45 分钟。

---

## 关键依赖链

```
SUB-TASK-001 ──→ SUB-TASK-002 ──→ SUB-TASK-003
                    │
                    ├──→ SUB-TASK-010 ──→ SUB-TASK-012 ──→ SUB-TASK-017
                    │                           │
                    │                           └→ SUB-TASK-019 ──→ SUB-TASK-020
                    │
                    └→ SUB-TASK-004 ──→ SUB-TASK-005 ──→ SUB-TASK-006
                                        │
                                        ├──→ SUB-TASK-022 ──→ SUB-TASK-025
                                        │
                                        └→ SUB-TASK-007 ──→ SUB-TASK-009
```

---

## 阻塞风险提示

1. **SUB-TASK-003** 是关键阻塞点 - 多个后续任务依赖 kb_meta 读写方法
2. **SUB-TASK-010** 是次要阻塞点 - 聚合查询和 info() 都依赖 get_children()
3. **任务组 D 和 E** 可并行但需在任务组 C 完成后启动
4. **测试任务组** 必须串行执行，每个测试依赖前一个测试的结果