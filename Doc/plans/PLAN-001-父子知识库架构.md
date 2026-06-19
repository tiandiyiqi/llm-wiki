# 实施计划：父子知识库架构

## 元信息

| 字段 | 值 |
|------|-----|
| 状态 | completed |
| 创建时间 | 2026-06-19 |
| 完成时间 | 2026-06-19 |
| 预估复杂度 | 中 |
| 所属项目 | llm-wiki |

---

## 需求重述

为 llm-wiki 添加**父子知识库架构**支持，满足以下需求：

1. **物理隔离** - 子知识库独立目录，便于搬移和区分
2. **父知识库有知识原子** - 父级也有 `atoms/` 目录存放通用知识
3. **独立导出导入** - 父和子都可以单独导出/导入
4. **跨主题搜索** - 查询父级时聚合搜索所有子库，结果显示来源
5. **关联不隔断** - 通过链接跨库引用，物理隔离不隔断逻辑联系

---

## 目录结构设计

```
office-kb/                        # 父知识库
├── .kb-meta.json                  # 父级元数据（记录子知识库关系）
├── index.md                       # 父级索引（聚合所有子库）
├── log.md                         # 父级日志
├── atoms/                         # 父级知识原子（通用知识）
│   ├── methods/
│   ├── facts/
│   └── ...
├── raw/
├── views/
│
├── word/                          # 子知识库：Word
│   ├── index.md
│   ├── log.md
│   ├── atoms/
│   ├── raw/
│   └── views/
│
└── powerpoint/                    # 子知识库：PowerPoint
    ├── index.md
    ├── log.md
    ├── atoms/
    ├── raw/
    └── views/
```

---

## 实施阶段

### 第 1 阶段：数据结构扩展

**目标：** 定义父子知识库的元数据结构

**步骤：**

- [ ] 1.1 设计 `.kb-meta.json` 格式
  ```json
  {
    "kb_type": "parent",           // 或 "child"
    "name": "office",
    "children": ["word", "powerpoint"],
    "children_paths": {
      "word": "word/",
      "powerpoint": "powerpoint/"
    },
    "parent": null,                // 子知识库填写父级名称
    "parent_path": null            // 子知识库填写父级路径
  }
  ```

- [ ] 1.2 扩展注册表结构（`registry.json`）
  - 新增字段：`kb_type`、`parent`、`children`、`children_paths`

**文件修改：**
- `llm-wiki.py` - `KBRegistry` 类内部结构定义

**预估耗时：** 30 分钟

---

### 第 2 阶段：KBInitializer 扩展

**目标：** 支持 `--parent` 和 `--child` 参数创建知识库

**步骤：**

- [ ] 2.1 修改 `KBInitializer.__init__()` 接收新参数
  - `is_parent: bool = False`
  - `is_child: bool = False`
  - `parent_kb: Optional[Path] = None`

- [ ] 2.2 实现 `init_parent()` 方法
  - 创建父知识库目录结构
  - 创建 `.kb-meta.json`（kb_type: "parent"）
  - 创建空的 children 列表

- [ ] 2.3 实现 `init_child()` 方法
  - 在父知识库目录下创建子目录
  - 创建子知识库目录结构
  - 创建 `.kb-meta.json`（kb_type: "child"）
  - 更新父知识库的 `.kb-meta.json`（添加 children）

- [ ] 2.4 更新 `cmd_init()` 函数
  - 处理 `--parent` 参数
  - 处理 `--child` 和 `--parent-kb` 参数

- [ ] 2.5 更新 argparse
  - `init_parser.add_argument('--parent', action='store_true')`
  - `init_parser.add_argument('--child', action='store_true')`
  - `init_parser.add_argument('--parent-kb', type=Path)`

**文件修改：**
- `llm-wiki.py` - `KBInitializer` 类、`cmd_init()` 函数、argparse

**预估耗时：** 1.5 小时

---

### 第 3 阶段：KBRegistry 扩展

**目标：** 注册表支持父子关系管理

**步骤：**

- [ ] 3.1 扩展 `register()` 方法
  - 支持 `kb_type` 参数（parent/child）
  - 支持 `parent` 参数（子知识库注册时）
  - 自动更新父知识库的 children 字段

- [ ] 3.2 扩展 `list()` 方法
  - 显示层级结构（父 → 子）
  - 标注 kb_type

- [ ] 3.3 新增 `get_children()` 方法
  - 返回指定知识库的所有子知识库

- [ ] 3.4 新增 `get_parent()` 方法
  - 返回指定知识库的父知识库

- [ ] 3.5 扩展 `info()` 输出
  - 显示父子关系
  - 显示聚合统计（父级显示所有子库概念总数）

**文件修改：**
- `llm-wiki.py` - `KBRegistry` 类、`cmd_register()`、`cmd_list()`、`cmd_info()`

**预估耗时：** 1 小时

---

### 第 4 阶段：聚合查询

**目标：** 查询父知识库时聚合搜索所有子知识库

**步骤：**

- [ ] 4.1 新增 `AggregatedQuerier` 类
  - 接收父知识库路径
  - 自动发现所有子知识库
  - 并行查询所有知识库（父级 + 子级）

- [ ] 4.2 实现聚合搜索逻辑
  - 合并所有知识库的 concepts
  - 去重（相同 atom_id）
  - 添加 `source` 字段标注来源

- [ ] 4.3 修改 `cmd_query()` 函数
  - 检测是否为父知识库
  - 如果是父知识库，调用 `AggregatedQuerier`
  - 输出时显示来源（父级 vs 子级）

- [ ] 4.4 支持按子知识库过滤
  - `--child <name>` 参数，仅搜索指定子知识库

**文件修改：**
- `llm-wiki.py` - 新增 `AggregatedQuerier` 类、修改 `cmd_query()`

**查询输出格式：**
```
🔍 Aggregated query across 3 knowledge bases

📋 Results (5):

1. [method] Word 文档格式化
   Source: word [子知识库]
   Path: word/atoms/methods/word-formatting.md
   
2. [method] Office 通用格式设置
   Source: office [父知识库]
   Path: atoms/methods/office-common-formatting.md
```

**预估耗时：** 2 小时

---

### 第 5 阶段：导出导入扩展

**目标：** 支持子知识库独立导出，父知识库可选择是否包含子库

**步骤：**

- [ ] 5.1 修改 `OKFExporter`
  - 检测 `.kb-meta.json` 判断 kb_type
  - 如果是子知识库，仅打包子知识库内容
  - 如果是父知识库，根据 `--include-children` 参数决定是否打包子库

- [ ] 5.2 新增 `--include-children` 参数
  - 默认 false（仅导出父级自身）
  - true 时打包所有子知识库

- [ ] 5.3 修改 `OKFImporter`
  - 检测 bundle 是否包含子知识库
  - 如果包含，恢复完整父子结构
  - 更新 `.kb-meta.json`

- [ ] 5.4 修改 `cmd_export()` 和 `cmd_import()`
  - 处理新参数
  - 显示导出范围提示

**文件修改：**
- `llm-wiki.py` - `OKFExporter`、`OKFImporter`、`cmd_export()`、`cmd_import()`

**预估耗时：** 1.5 小时

---

### 第 6 阶段：文档更新

**目标：** 更新 README 和 SKILL 文档

**步骤：**

- [ ] 6.1 更新 README.md
  - 添加"父子知识库"章节
  - 更新命令参考（init --parent/--child）
  - 更新命令速查表

- [ ] 6.2 更新 SKILL.md
  - 添加父子知识库架构说明
  - 更新命令表格

- [ ] 6.3 更新 CLI 帮助文档（llm-wiki.py 文件头）

**文件修改：**
- `README.md`
- `SKILL.md`
- `llm-wiki.py` 文件头注释

**预估耗时：** 30 分钟

---

### 第 7 阶段：测试验证

**目标：** 验证所有功能正常工作

**步骤：**

- [ ] 7.1 创建测试父知识库
  ```bash
  python3 llm-wiki.py init /tmp/office-kb --parent --name office
  ```

- [ ] 7.2 创建子知识库
  ```bash
  python3 llm-wiki.py init /tmp/office-kb/word --child --parent-kb /tmp/office-kb --name word
  python3 llm-wiki.py init /tmp/office-kb/powerpoint --child --parent-kb /tmp/office-kb --name powerpoint
  ```

- [ ] 7.3 注册到管理器
  ```bash
  python3 llm-wiki.py register /tmp/office-kb --name office
  python3 llm-wiki.py register /tmp/office-kb/word --name word --parent office
  ```

- [ ] 7.4 测试聚合查询
  ```bash
  python3 llm-wiki.py query office "格式化"
  ```

- [ ] 7.5 测试独立导出
  ```bash
  python3 llm-wiki.py export word -o word-bundle.tar.gz
  python3 llm-wiki.py export office -o office-bundle.tar.gz --include-children
  ```

- [ ] 7.6 测试 list/info 命令
  ```bash
  python3 llm-wiki.py list
  python3 llm-wiki.py info office
  ```

**预估耗时：** 30 分钟

---

## 依赖关系

| 阶段 | 依赖 | 说明 |
|------|------|------|
| 第 1 阶段 | 无 | 基础数据结构，可独立开始 |
| 第 2 阶段 | 第 1 阶段 | 需要先定义 .kb-meta.json 格式 |
| 第 3 阶段 | 第 1、2 阶段 | 注册表需要读写 .kb-meta.json |
| 第 4 阶段 | 第 2、3 阶段 | 查询需要能识别父子关系 |
| 第 5 阶段 | 第 1、2 阶段 | 导出需要识别 kb_type |
| 第 6 阶段 | 所有功能完成 | 文档反映最终功能 |
| 第 7 阶段 | 所有功能完成 | 完整测试 |

**可并行阶段：**
- 第 2 阶段和第 3 阶段部分工作可并行
- 第 6 阶段可在功能完成前开始草稿

---

## 风险评估

| 风险 | 级别 | 说明 | 缓解措施 |
|------|------|------|---------|
| 跨库链接解析 | 中 | `[[../word/atoms/xxx]]` 链接需要在可视化中正确解析 | 第 4 阶段实现链接规范化 |
| 聚合查询性能 | 中 | 大量子知识库时查询可能变慢 | 使用并行查询，添加缓存 |
| 导出 bundle 大小 | 低 | 父知识库包含子库时文件变大 | 添加 --include-children 控制 |
| 路径相对性 | 低 | 子知识库移动后链接可能失效 | 使用相对路径，测试路径迁移 |

---

## 预估总耗时

| 阶段 | 耗时 |
|------|------|
| 第 1 阶段 | 30 分钟 |
| 第 2 阶段 | 1.5 小时 |
| 第 3 阶段 | 1 小时 |
| 第 4 阶段 | 2 小时 |
| 第 5 阶段 | 1.5 小时 |
| 第 6 阶段 | 30 分钟 |
| 第 7 阶段 | 30 分钟 |
| **总计** | **约 6.5 小时** |

---

## 新增命令参数

| 命令 | 新参数 | 说明 |
|------|--------|------|
| `init` | `--parent` | 创建父知识库 |
| `init` | `--child` | 创建子知识库 |
| `init` | `--parent-kb` | 指定父知识库路径 |
| `register` | `--parent` | 指定父知识库名称 |
| `query` | `--child` | 仅搜索指定子知识库 |
| `export` | `--include-children` | 导出时包含子知识库 |

---

## 现有命令修改

| 命令 | 修改内容 |
|------|---------|
| `list` | 显示层级结构，标注 kb_type |
| `info` | 显示父子关系，聚合统计 |
| `query` | 父知识库聚合查询，显示来源 |
| `export` | 支持子知识库独立导出 |
| `import` | 支持恢复父子结构 |

---

## 完成标准

- ✅ `init --parent` 创建父知识库成功
- ✅ `init --child` 在父知识库下创建子知识库成功
- ✅ 注册表正确记录父子关系
- ✅ `list` 显示层级结构
- ✅ `info` 显示父子关系和聚合统计
- ✅ `query` 父知识库聚合查询并显示来源
- ✅ `export` 子知识库独立导出成功
- ✅ `export --include-children` 父知识库包含子库导出成功
- ✅ 文档更新完成

---

**等待确认：** 是否继续执行此计划？

选择下一步：
- 方案 1：完整流程（推荐）→ `/plan-segment` → `/plan-execution`
- 方案 2：快速执行（不推荐）→ 直接开始编码
- 方案 3：修改计划 → 提出修改意见