# LLM Wiki - OKF 知识库管理工具

[![OKF v0.1](https://img.shields.io/badge/OKF-v0.1-blue.svg)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于 [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) 规范的知识库 CLI 管理工具。

## 特性

- ✅ **OKF v0.1 完全兼容** - 符合 Google Cloud Platform 提出的开放知识格式规范
- ✅ **零外部依赖** - 核心功能仅使用 Python 标准库
- ✅ **十四大核心命令** - init/register/unregister/list/use/info/ingest/embed/query/lint/index/export/import/visualize
- ✅ **多知识库管理** - 注册、切换、列出多个知识库
- ✅ **智能提取** - 自动检测知识类型、提取标题和标签
- ✅ **语义搜索** - 支持向量嵌入和语义查询（可选）
- ✅ **知识图谱** - 生成交互式 HTML 可视化
- ✅ **单文件部署** - 一个 `.py` 文件即可使用

## 安装

### 方式一：直接使用（推荐）

```bash
# 克隆仓库
git clone https://github.com/Tiandiyiqi/llm-wiki.git
cd llm-wiki

# 直接运行
python3 llm-wiki.py --help
```

### 方式二：作为 Claude Code Skill 安装

将本项目作为 Claude Code 的 Skill 安装，可在对话中直接调用：

```bash
# 创建 skills 目录（如果不存在）
mkdir -p ~/.claude/skills

# 克隆到 skills 目录
git clone https://github.com/Tiandiyiqi/llm-wiki.git ~/.claude/skills/llm-wiki
```

**安装后，在 Claude Code 对话中可以这样使用：**

```
用户: /llm-wiki init ./my-kb
Claude: 正在初始化知识库...

用户: /llm-wiki query "installation" --kb ./my-kb
Claude: 正在搜索知识...
```

### 方式三：创建别名（可选）

添加到 `~/.zshrc` 或 `~/.bashrc`：

```bash
alias llm-wiki='python3 /path/to/llm-wiki/llm-wiki.py'
```

## 快速开始

```bash
# 1. 初始化知识库
python3 llm-wiki.py init ./my-kb

# 2. 摄入资料（自动提取知识原子）
python3 llm-wiki.py ingest raw/document.md --kb ./my-kb

# 3. 查询知识（关键词搜索）
python3 llm-wiki.py query "installation" --kb ./my-kb

# 4. 语义搜索（可选，需先安装依赖）
pip install chromadb sentence-transformers
python3 llm-wiki.py embed ./my-kb
python3 llm-wiki.py query "如何部署" --kb ./my-kb --semantic

# 5. 验证 OKF 兼容性
python3 llm-wiki.py lint ./my-kb --okf-check

# 6. 生成知识图谱
python3 llm-wiki.py visualize ./my-kb

# 7. 导出 Bundle
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz
```

## 多知识库管理

当创建多个知识库时，可以使用注册表管理：

```bash
# 1. 注册知识库
python3 llm-wiki.py register ./my-kb --name my-project --description "项目知识库"

# 2. 列出所有知识库
python3 llm-wiki.py list

# 3. 设置当前知识库
python3 llm-wiki.py use my-project

# 4. 省略路径查询（使用当前知识库）
python3 llm-wiki.py query "installation" --kb my-project

# 5. 通过名称引用
python3 llm-wiki.py query "installation" --kb my-project

# 6. 查看知识库详情
python3 llm-wiki.py info my-project

# 7. 注销知识库
python3 llm-wiki.py unregister my-project
```

**注册表存储：**
- 全局：`~/.llm-wiki/registry.json`
- 项目级：`<project>/.llm-wiki/registry.json`（可选）

**scope 参数：**
- `--scope global`：注册到全局注册表
- `--scope project`：注册到项目级注册表
- `--scope auto`：自动选择（默认）

## 父子知识库架构

当管理一组相关的知识库时，可以使用**父子知识库架构**：

- **物理隔离**：每个子知识库独立目录，便于搬移
- **父知识库有知识原子**：父级也有 `atoms/` 存放通用知识
- **独立导出导入**：父和子都可以单独导出/导入
- **跨主题搜索**：查询父级时聚合搜索所有子库
- **关联不隔断**：通过链接跨库引用

### 目录结构

```
office-kb/                        # 父知识库
├── .kb-meta.json                  # 元数据（记录子知识库关系）
├── index.md                       # 父级索引
├── atoms/                         # 父级知识原子（通用知识）
│   └── methods/
│       └── common-formatting.md
├── raw/
├── views/
│
├── word/                          # 子知识库：Word
│   ├── .kb-meta.json
│   ├── index.md
│   ├── atoms/
│   └── raw/
│
└── powerpoint/                    # 子知识库：PowerPoint
    ├── .kb-meta.json
    ├── index.md
    ├── atoms/
    └── raw/
```

### 创建父子知识库

```bash
# 1. 创建父知识库
python3 llm-wiki.py init /path/to/office-kb --parent --name office

# 2. 创建子知识库
python3 llm-wiki.py init /path/to/office-kb/word --child --parent-kb /path/to/office-kb --name word
python3 llm-wiki.py init /path/to/office-kb/powerpoint --child --parent-kb /path/to/office-kb --name powerpoint

# 3. 注册知识库
python3 llm-wiki.py register /path/to/office-kb --name office
python3 llm-wiki.py register /path/to/office-kb/word --name word
```

### 聚合查询

查询父知识库时，自动聚合搜索所有子知识库：

```bash
# 聚合查询（搜索父级 + 所有子级）
python3 llm-wiki.py query "格式化" --kb office

# 仅搜索指定子知识库
python3 llm-wiki.py query "格式化" --kb office --child word
```

**输出示例：**
```
🔍 Aggregated query: '格式化'
   Parent knowledge base: /path/to/office-kb
   Child knowledge bases: 2
      - word
      - powerpoint

   Total concepts (aggregated): 5

📋 Results (3):

1. [method] Word 文档格式化
   Source: word [子知识库]
   Path: word/atoms/methods/word-formatting.md

2. [method] Office 通用格式设置
   Source: office [父知识库]
   Path: atoms/methods/common-formatting.md
```

### 导出导入

```bash
# 子知识库独立导出
python3 llm-wiki.py export word -o word-bundle.tar.gz

# 父知识库包含子库导出
python3 llm-wiki.py export office -o office-full-bundle.tar.gz --include-children

# 仅导出父知识库（不含子库）
python3 llm-wiki.py export office -o office-bundle.tar.gz
```

### 跨库链接

使用相对路径进行跨库引用：

```markdown
<!-- 在子知识库中引用父级 -->
参见 [[../atoms/methods/common-formatting]] 获取通用格式设置方法。

<!-- 在父知识库中引用子级 -->
参见 [[word/atoms/methods/word-formatting]] 获取 Word 特定格式化方法。
```

## 命令参考

### 查看帮助

```bash
python3 llm-wiki.py --help
python3 llm-wiki.py <command> --help  # 查看子命令帮助
```

---

### init - 初始化知识库

创建符合 OKF 规范的目录结构。

```bash
python3 llm-wiki.py init <knowledge_base>
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `knowledge_base` | - | 知识库目录路径（必需） |
| `--register` | - | 初始化后注册 |
| `--name` | `-n` | 知识库别名 |
| `--description` | `-d` | 描述 |
| `--tags` | `-t` | 标签（逗号分隔） |
| `--scope` | `-s` | 注册范围（auto/project/global） |
| `--parent` | - | 创建父知识库 |
| `--child` | - | 创建子知识库 |
| `--parent-kb` | - | 父知识库路径（创建子知识库时必需） |

**示例：**
```bash
# 基本初始化
python3 llm-wiki.py init ./my-kb

# 初始化并注册
python3 llm-wiki.py init ./my-kb --register --name my-project --description "项目知识库"

# 创建父知识库
python3 llm-wiki.py init ./office-kb --parent --name office

# 创建子知识库
python3 llm-wiki.py init ./office-kb/word --child --parent-kb ./office-kb --name word
```

**创建的目录结构：**
```
my-kb/
├── index.md          # 知识库索引
├── log.md            # 更新日志
├── atoms/            # 知识原子
│   ├── methods/      # 方法/步骤
│   ├── facts/        # 事实
│   ├── definitions/  # 定义
│   ├── opinions/     # 观点
│   ├── data/         # 数据
│   ├── questions/    # 问题
│   └── references/   # 参考
├── raw/              # 原始资料
└── views/            # 视图/可视化
```

---

### register - 注册知识库

将现有知识库注册到注册表，支持通过名称引用。

```bash
python3 llm-wiki.py register <path> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `path` | - | 知识库路径（必需） |
| `--name` | `-n` | 知识库别名（默认：目录名） |
| `--description` | `-d` | 描述 |
| `--tags` | `-t` | 标签（逗号分隔） |
| `--scope` | `-s` | 注册范围（auto/project/global，默认：auto） |
| `--parent` | `-p` | 父知识库名称（注册子知识库时使用） |

**示例：**
```bash
# 注册到全局
python3 llm-wiki.py register ./my-kb --name my-project --description "项目知识库"

# 注册到项目级
python3 llm-wiki.py register ./my-kb --name my-project --scope project

# 注册子知识库
python3 llm-wiki.py register ./office-kb/word --name word --parent office
```

---

### unregister - 注销知识库

从注册表中移除知识库。

```bash
python3 llm-wiki.py unregister <name> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `name` | - | 知识库别名（必需） |
| `--scope` | `-s` | 注销范围（auto/project/global/all，默认：all） |

**示例：**
```bash
# 从所有注册表注销
python3 llm-wiki.py unregister my-project

# 仅从全局注销
python3 llm-wiki.py unregister my-project --scope global
```

---

### list - 列出所有知识库

列出已注册的所有知识库。

```bash
python3 llm-wiki.py list [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `--scope` | `-s` | 列出范围（all/project/global，默认：all） |
| `--verbose` | `-v` | 详细输出 |

**示例：**
```bash
# 列出所有
python3 llm-wiki.py list

# 详细输出
python3 llm-wiki.py list -v

# 仅列出全局
python3 llm-wiki.py list --scope global
```

---

### use - 设置当前知识库

设置当前知识库，后续命令可省略知识库路径。

```bash
python3 llm-wiki.py use <name>
```

**示例：**
```bash
python3 llm-wiki.py use my-project

# 之后的命令可省略路径
python3 llm-wiki.py query "installation"
```

---

### info - 查看知识库详情

查看知识库的详细信息。

```bash
python3 llm-wiki.py info [<name>]
```

**参数：**

| 参数 | 说明 |
|------|------|
| `name` | 知识库别名（默认：当前知识库） |

**示例：**
```bash
# 查看当前知识库
python3 llm-wiki.py info

# 查看指定知识库
python3 llm-wiki.py info my-project
```

---

### ingest - 摄入资料提取原子

从源文件自动提取知识原子，支持 Markdown 文件。

```bash
python3 llm-wiki.py ingest <source> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `source` | - | 源文件路径（必需） |
| `--kb` | `-k` | 知识库路径或名称（默认：当前知识库） |
| `--type` | `-t` | 原子类型（默认自动检测） |
| `--auto-type` | - | 自动检测类型（默认开启） |

**示例：**
```bash
# 摄入文档到当前知识库（使用 use 设置）
llm-wiki use my-project
llm-wiki ingest raw/document.md

# 指定知识库
llm-wiki ingest raw/document.md --kb ./my-kb

# 指定类型
llm-wiki ingest raw/tutorial.md --kb ./my-kb --type method
```

**自动检测规则：**
- 包含 "步骤"、"step"、"how to"、"安装" → `method`
- 包含 "要求"、"requirement"、"版本" → `fact`
- 包含 "定义"、"definition"、"概念" → `definition`
- 包含 "统计"、"数据"、"性能" → `data`

---

### query - 搜索查询知识

在知识库中搜索知识原子。支持**关键词搜索**和**语义搜索**两种模式。

```bash
python3 llm-wiki.py query <query> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `query` | - | 查询关键词或问题（必需） |
| `--kb` | `-k` | 知识库路径或名称（默认：当前知识库） |
| `--type` | `-t` | 按类型过滤 |
| `--limit` | `-l` | 结果数量限制（默认：10） |
| `--semantic` | `-s` | 启用语义搜索（需要先运行 `embed`） |
| `--child` | `-c` | 仅搜索指定子知识库（父知识库聚合查询时） |

**示例：**
```bash
# 关键词搜索（使用当前知识库）
llm-wiki use my-project
llm-wiki query "installation"

# 指定知识库搜索
llm-wiki query "installation" --kb ./my-kb

# 按类型过滤
llm-wiki query "ubuntu" --kb ./my-kb --type method

# 限制结果数量
llm-wiki query "config" --kb ./my-kb --limit 5

# 语义搜索（需要先安装依赖并运行 embed）
llm-wiki query "如何部署服务" --kb ./my-kb --semantic

# 父知识库聚合查询
llm-wiki query "格式化" --kb office

# 仅搜索指定子知识库
llm-wiki query "格式化" --kb office --child word
```

**关键词搜索优先级：**
1. 标题匹配（最高优先级）
2. 描述匹配
3. 标签匹配
4. 正文匹配

**语义搜索：**
- 理解查询意图，而非字面匹配
- 支持同义词、相关概念
- 需要 ChromaDB 和 sentence-transformers

**父知识库聚合查询：**
- 查询父知识库时自动聚合所有子知识库
- 结果显示来源（父级 vs 子级）
- 使用 `--child` 参数限定搜索范围

---

### embed - 生成向量嵌入

为知识库生成向量嵌入，用于语义搜索。

```bash
python3 llm-wiki.py embed <knowledge_base>
```

**依赖安装：**
```bash
pip install chromadb sentence-transformers
```

**示例：**
```bash
# 生成嵌入
python3 llm-wiki.py embed ./my-kb

# 然后使用语义搜索
python3 llm-wiki.py query ./my-kb "如何安装" --semantic
```

**技术说明：**
- 使用 `all-MiniLM-L6-v2` 模型生成嵌入
- 嵌入存储在 `.chroma/` 目录中
- 首次运行会下载模型（约 90MB）

---

### lint - OKF 兼容性检查

验证知识库是否符合 OKF v0.1 规范。

```bash
python3 llm-wiki.py lint <knowledge_base> [--okf-check]
```

**示例：**
```bash
# 基本检查
python3 llm-wiki.py lint ./my-kb

# 详细检查
python3 llm-wiki.py lint ./my-kb --okf-check
```

**检查项目：**

| 检查项 | 级别 | 说明 |
|--------|------|------|
| YAML frontmatter | 🔴 致命 | 每个 `.md` 文件必须有 frontmatter |
| `type` 字段 | 🔴 致命 | frontmatter 必须包含 type |
| `title` 字段 | 🟡 警告 | 推荐添加 |
| `description` 字段 | 🟡 警告 | 推荐添加 |
| `timestamp` 字段 | 🟡 警告 | 推荐添加，ISO 8601 格式 |

---

### index - 生成目录索引

为知识库目录生成 `index.md` 文件（渐进披露）。

```bash
python3 llm-wiki.py index <knowledge_base> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `knowledge_base` | - | 知识库目录路径（必需） |
| `--directory` | `-d` | 指定要生成索引的子目录 |

**示例：**
```bash
# 为整个知识库生成索引
python3 llm-wiki.py index ./my-kb

# 为指定目录生成索引
python3 llm-wiki.py index ./my-kb -d ./my-kb/atoms/methods
```

---

### export - 导出 OKF Bundle

将知识库打包为 `.tar.gz` 文件。

```bash
python3 llm-wiki.py export <knowledge_base> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `knowledge_base` | - | 知识库目录路径（必需） |
| `--output` | `-o` | 输出文件路径 |
| `--validate` | `-v` | 验证 OKF 符合性（默认开启） |
| `--no-validate` | - | 跳过验证 |
| `--force` | `-f` | 强制导出（忽略验证错误） |
| `--include-children` | - | 包含子知识库（仅父知识库） |

**示例：**
```bash
# 基本导出
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz

# 强制导出
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz --force

# 子知识库独立导出
python3 llm-wiki.py export word -o word-bundle.tar.gz

# 父知识库包含子库导出
python3 llm-wiki.py export office -o office-full-bundle.tar.gz --include-children
```

---

### import - 导入 OKF Bundle

从 `.tar.gz` 文件恢复知识库。

```bash
python3 llm-wiki.py import <bundle> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `bundle` | - | Bundle 文件路径（必需） |
| `--output` | `-o` | 输出目录（默认：当前目录） |
| `--overwrite` | - | 覆盖现有文件 |

**示例：**
```bash
# 导入到新目录
python3 llm-wiki.py import bundle.tar.gz -o ./restored-kb

# 覆盖现有目录
python3 llm-wiki.py import bundle.tar.gz -o ./existing-kb --overwrite
```

---

### visualize - 生成知识图谱

生成交互式 HTML 知识图谱可视化。

```bash
python3 llm-wiki.py visualize <knowledge_base> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `knowledge_base` | - | 知识库目录路径（必需） |
| `--output` | `-o` | 输出 HTML 文件路径 |
| `--name` | `-n` | 图谱名称 |

**示例：**
```bash
# 生成可视化（默认输出到 views/knowledge-graph.html）
python3 llm-wiki.py visualize ./my-kb

# 指定输出路径
python3 llm-wiki.py visualize ./my-kb -o ./graph.html

# 指定名称
python3 llm-wiki.py visualize ./my-kb --name "My Knowledge Base"
```

**可视化功能：**
- 🔍 搜索节点
- 🏷️ 按类型过滤
- 🔗 显示节点关系
- 📊 点击查看详情

---

## 使用指南

### 两种使用方式

LLM Wiki 支持两种使用方式：

#### 方式一：命令行（CLI）

直接在终端执行命令：

```bash
python3 llm-wiki.py init ./my-kb
python3 llm-wiki.py ingest raw/doc.md --kb ./my-kb
python3 llm-wiki.py query "installation" --kb ./my-kb
```

#### 方式二：自然语言（Claude Code Skill）

安装为 Skill 后，在 Claude Code 对话中用自然语言描述需求：

**自然语言示例：**

```
用户: 帮我初始化一个知识库，路径是 ./nextcloud-docs

用户: 把 raw/nextcloud-install.md 这个文档加入知识库

用户: 搜索关于 installation 的知识

用户: 检查一下知识库是否符合 OKF 规范

用户: 生成知识图谱

用户: 把知识库打包导出
```

**自然语言与命令对照表：**

| 自然语言描述 | 等效命令 |
|-------------|---------|
| "初始化一个知识库" | `llm-wiki init` |
| "加入/摄入这个文档" | `llm-wiki ingest` |
| "搜索/查询关于 X 的知识" | `llm-wiki query` |
| "检查/验证 OKF 规范" | `llm-wiki lint` |
| "生成索引" | `llm-wiki index` |
| "导出/打包知识库" | `llm-wiki export` |
| "导入/恢复知识库" | `llm-wiki import` |
| "生成知识图谱/可视化" | `llm-wiki visualize` |

---

### 全周期使用示例：构建 Nextcloud 知识库

以下是一个完整的知识库构建周期，包含所有 8 个命令的使用。

#### 背景

假设你收集了一系列 Nextcloud 相关文档，想要构建一个结构化的知识库。

---

#### 第一步：初始化知识库（init）

**CLI 方式：**
```bash
python3 llm-wiki.py init ./nextcloud-kb
```

**自然语言方式：**
```
用户: 帮我初始化一个 Nextcloud 知识库，路径是 ./nextcloud-kb

Claude: 📦 Initializing knowledge base: ./nextcloud-kb
   Created: atoms/methods
   Created: atoms/facts
   Created: atoms/definitions
   ...
   ✅ Knowledge base initialized!
   Path: ./nextcloud-kb
```

**输出结果：**
```
nextcloud-kb/
├── index.md          # 知识库索引
├── log.md            # 更新日志
├── atoms/            # 知识原子目录
│   ├── methods/
│   ├── facts/
│   ├── definitions/
│   └── ...
├── raw/              # 原始资料目录
└── views/            # 可视化输出目录
```

---

#### 第二步：收集原始资料

将文档放入 `raw/` 目录：

```bash
# 复制收集的文档
cp ~/Documents/nextcloud-install.md ./nextcloud-kb/raw/
cp ~/Documents/nextcloud-requirements.md ./nextcloud-kb/raw/
cp ~/Documents/nextcloud-security.md ./nextcloud-kb/raw/
```

---

#### 第三步：摄入资料（ingest）

**CLI 方式：**
```bash
# 摄入安装文档（自动检测类型）
python3 llm-wiki.py ingest raw/nextcloud-install.md --kb ./nextcloud-kb

# 摄入需求文档
python3 llm-wiki.py ingest raw/nextcloud-requirements.md --kb ./nextcloud-kb

# 摄入安全文档，指定类型
python3 llm-wiki.py ingest raw/nextcloud-security.md --kb ./nextcloud-kb --type method
```

**自然语言方式：**
```
用户: 把 raw/nextcloud-install.md 加入知识库

Claude: 📦 Ingesting source: raw/nextcloud-install.md
   Knowledge base: ./nextcloud-kb
   Source type: official
   Title: Nextcloud Installation Guide
   Atom type: method
   ✅ Atom created: atoms/methods/nextcloud-installation-guide-20260618120000.md

用户: 把 raw/nextcloud-requirements.md 也加进去

Claude: 📦 Ingesting source: raw/nextcloud-requirements.md
   Atom type: fact
   ✅ Atom created: atoms/facts/nextcloud-requirements-20260618120100.md
```

**生成的原子文件示例：**

```markdown
# atoms/methods/nextcloud-installation-guide-20260618120000.md

---
type: method
title: Nextcloud Installation Guide
description: Complete installation guide for Nextcloud on Ubuntu Server
tags:
  - installation
  - ubuntu
  - apache
timestamp: 2026-06-18T12:00:00
source: raw/nextcloud-install.md
source_type: official
---

# Nextcloud Installation Guide

## 概述

Complete installation guide for Nextcloud on Ubuntu Server...

## 详细内容

[从原文档提取的内容...]

# Citations

[1] [nextcloud-install.md](raw/nextcloud-install.md)
```

---

#### 第四步：验证知识库（lint）

**CLI 方式：**
```bash
# 基本验证
python3 llm-wiki.py lint ./nextcloud-kb

# 详细 OKF 规范检查
python3 llm-wiki.py lint ./nextcloud-kb --okf-check
```

**自然语言方式：**
```
用户: 检查知识库是否符合 OKF 规范

Claude: 📦 Validating OKF conformance: ./nextcloud-kb

📊 Results:
   Concepts: 3
   Valid: ✅ Yes

📋 OKF v0.1 Conformance Check:
   ✅ All .md files have frontmatter: True
   ✅ All frontmatter have 'type': True
   ✅ Reserved files valid: True
```

---

#### 第五步：生成索引（index）

**CLI 方式：**
```bash
# 为整个知识库生成索引
python3 llm-wiki.py index ./nextcloud-kb

# 为特定目录生成索引
python3 llm-wiki.py index ./nextcloud-kb -d ./nextcloud-kb/atoms/methods
```

**自然语言方式：**
```
用户: 生成知识库的索引文件

Claude: 📦 Generating index.md for: ./nextcloud-kb
   Generated: ./nextcloud-kb/index.md
   Concepts: 3
```

---

#### 第六步：查询知识（query）

**CLI 方式：**
```bash
# 基本搜索
python3 llm-wiki.py query "installation" --kb ./nextcloud-kb

# 按类型过滤
python3 llm-wiki.py query "ubuntu" --kb ./nextcloud-kb --type method

# 限制结果数量
python3 llm-wiki.py query "config" --kb ./nextcloud-kb --limit 5
```

**自然语言方式：**
```
用户: 搜索关于 installation 的知识

Claude: 🔍 Querying: 'installation'
   Knowledge base: ./nextcloud-kb
   Total concepts: 3

📋 Results (2):

1. [method] Nextcloud Installation Guide
   Path: atoms/methods/nextcloud-installation-guide-20260618120000.md
   Complete installation guide for Nextcloud on Ubuntu Server...
   Tags: installation, ubuntu, apache

2. [fact] Nextcloud System Requirements
   Path: atoms/facts/nextcloud-requirements-20260618120100.md
   System requirements for Nextcloud server...
   Tags: requirements, server

用户: 只看 method 类型的安装知识

Claude: 🔍 Querying: 'installation' (type: method)

📋 Results (1):

1. [method] Nextcloud Installation Guide
   Path: atoms/methods/nextcloud-installation-guide-20260618120000.md
```

---

#### 第 6.5 步：语义搜索（embed + query --semantic）

**可选步骤**：启用语义搜索，支持自然语言查询。

**CLI 方式：**
```bash
# 安装依赖（首次使用）
pip install chromadb sentence-transformers

# 生成向量嵌入
python3 llm-wiki.py embed ./nextcloud-kb

# 语义搜索
python3 llm-wiki.py query "如何配置服务器" --kb ./nextcloud-kb --semantic
```

**自然语言方式：**
```
用户: 启用语义搜索

Claude: 📊 Generating embeddings for: ./nextcloud-kb
   Concepts to embed: 3
   Loading embedding model (first run may take a while)...
   Generating embeddings...
   Storing in ChromaDB...

✅ Embeddings generated for 3 concepts

用户: 用语义搜索查找如何配置服务器

Claude: 🔍 Semantic search results (2):

1. [method] Nextcloud Installation Guide
   Path: atoms/methods/nextcloud-installation-guide-20260618120000.md
   Similarity: 0.856
   Complete installation guide for Nextcloud on Ubuntu Server...

2. [fact] Nextcloud System Requirements
   Path: atoms/facts/nextcloud-requirements-20260618120100.md
   Similarity: 0.723
   System requirements for Nextcloud server...
```

---

#### 第七步：可视化知识图谱（visualize）

**CLI 方式：**
```bash
# 生成可视化（默认输出到 views/knowledge-graph.html）
python3 llm-wiki.py visualize ./nextcloud-kb

# 指定输出路径和名称
python3 llm-wiki.py visualize ./nextcloud-kb -o ./nextcloud-graph.html --name "Nextcloud Knowledge Base"
```

**自然语言方式：**
```
用户: 生成知识图谱

Claude: 📊 Generating knowledge graph: ./nextcloud-kb
   Output: ./nextcloud-kb/views/knowledge-graph.html
   Concepts: 3

✅ Visualization created: ./nextcloud-kb/views/knowledge-graph.html
   Open in browser to view interactive graph
```

**可视化功能：**
- 🔍 搜索节点
- 🏷️ 按类型过滤（method/fact/definition 等）
- 🔗 显示知识关联
- 📊 点击节点查看详情

---

#### 第八步：导出备份（export）

**CLI 方式：**
```bash
# 导出为 Bundle
python3 llm-wiki.py export ./nextcloud-kb -o nextcloud-bundle.tar.gz

# 强制导出（忽略验证错误）
python3 llm-wiki.py export ./nextcloud-kb -o nextcloud-bundle.tar.gz --force
```

**自然语言方式：**
```
用户: 把知识库打包导出

Claude: 📦 Exporting OKF bundle from: ./nextcloud-kb

📊 Validation Results:
   Concepts: 3
   Errors: 0
   Warnings: 0

📦 Creating bundle: nextcloud-bundle.tar.gz

✅ Export complete!
   Bundle: nextcloud-bundle.tar.gz
   Concepts: 3
   Size: 2.5 KB
```

---

#### 第九步：导入恢复（import）

**CLI 方式：**
```bash
# 导入到新目录
python3 llm-wiki.py import nextcloud-bundle.tar.gz -o ./restored-kb

# 覆盖现有目录
python3 llm-wiki.py import nextcloud-bundle.tar.gz -o ./existing-kb --overwrite
```

**自然语言方式：**
```
用户: 从 nextcloud-bundle.tar.gz 恢复知识库到 ./restored-kb

Claude: 📦 Importing OKF bundle: nextcloud-bundle.tar.gz

📦 Extracting to: ./restored-kb

📊 Bundle Info:
   OKF Version: 0.1
   Concepts: 3
   Types:
     - method: 2
     - fact: 1

✅ Import complete!
   Files imported: 5
```

---

### 命令速查表

| 命令 | CLI | 自然语言关键词 | 用途 |
|------|-----|---------------|------|
| init | `llm-wiki init ./kb` | "初始化知识库" | 创建目录结构 |
| register | `llm-wiki register ./kb --name my-kb` | "注册知识库" | 注册到管理器 |
| unregister | `llm-wiki unregister my-kb` | "注销知识库" | 从管理器移除 |
| list | `llm-wiki list` | "列出知识库" | 查看所有知识库 |
| use | `llm-wiki use my-kb` | "切换知识库" | 设置当前知识库 |
| info | `llm-wiki info my-kb` | "知识库详情" | 查看详细信息 |
| ingest | `llm-wiki ingest raw/doc.md --kb ./kb` | "加入文档"、"摄入资料" | 提取知识原子 |
| embed | `llm-wiki embed ./kb` | "生成嵌入"、"向量化" | 生成语义搜索嵌入 |
| query | `llm-wiki query "关键词" --kb ./kb` | "搜索"、"查询" | 检索知识 |
| lint | `llm-wiki lint ./kb` | "检查"、"验证" | OKF 规范检查 |
| index | `llm-wiki index ./kb` | "生成索引" | 创建目录索引 |
| export | `llm-wiki export ./kb -o bundle.tar.gz` | "导出"、"打包" | 备份知识库 |
| import | `llm-wiki import bundle.tar.gz -o ./kb` | "导入"、"恢复" | 恢复知识库 |
| visualize | `llm-wiki visualize ./kb` | "知识图谱"、"可视化" | 生成交互图 |

---

### 典型应用场景

#### 场景一：技术文档知识库

**需求：** 将分散的技术文档整理成可搜索的知识库

**步骤：**
```bash
# 1. 初始化
llm-wiki init ./tech-docs

# 2. 放入原始文档
cp ~/Downloads/*.md ./tech-docs/raw/

# 3. 批量摄入
for f in ./tech-docs/raw/*.md; do
    llm-wiki ingest "$f" --kb ./tech-docs
done

# 4. 验证
llm-wiki lint ./tech-docs

# 5. 可视化
llm-wiki visualize ./tech-docs
```

#### 场景二：项目知识管理

**需求：** 为团队项目建立知识库，支持快速查询

**步骤：**
```bash
# 1. 初始化
llm-wiki init ./project-kb

# 2. 添加项目文档
llm-wiki ingest ./README.md --kb ./project-kb --type reference
llm-wiki ingest ./SETUP.md --kb ./project-kb --type method
llm-wiki ingest ./API.md --kb ./project-kb --type reference

# 3. 查询
llm-wiki query "api" --kb ./project-kb
llm-wiki query "setup" --kb ./project-kb --type method
```

#### 场景三：个人学习笔记

**需求：** 整理学习笔记，建立知识图谱

**步骤：**
```bash
# 1. 初始化
llm-wiki init ./learning-notes

# 2. 摄入笔记
llm-wiki ingest notes/python-basics.md --kb ./learning-notes
llm-wiki ingest notes/python-advanced.md --kb ./learning-notes

# 3. 生成图谱
llm-wiki visualize ./learning-notes --name "Python Learning"

# 4. 导出备份
llm-wiki export ./learning-notes -o notes-backup.tar.gz
```

#### 场景四：Claude Code 知识增强

**需求：** 作为 Claude Code 的外部知识源

**步骤：**
```bash
# 1. 安装为 Skill
git clone https://github.com/Tiandiyiqi/llm-wiki.git ~/.claude/skills/llm-wiki

# 2. 在 Claude Code 对话中使用
/llm-wiki init ./my-knowledge
/llm-wiki ingest raw/article.md --kb ./my-knowledge
/llm-wiki query "关键词" --kb ./my-knowledge
```

---

## OKF 规范

### 什么是 OKF？

OKF (Open Knowledge Format) 是 Google Cloud Platform 提出的开放知识格式规范：
- **通用格式**：Markdown + YAML frontmatter
- **厂商中立**：不依赖特定工具或平台
- **可移植性**：Git 管理，可打包、可迁移

### OKF 核心要求

知识库符合 OKF v0.1 规范需满足：

1. ✅ 每个 `.md` 文件有 YAML frontmatter
2. ✅ frontmatter 包含 `type` 字段（必需）
3. ✅ 推荐：`title`, `description`, `timestamp` 字段
4. ✅ 使用 `index.md` 进行目录索引

### 知识原子格式

```yaml
---
type: method                    # 必需：知识类型
title: 标题                      # 推荐：显示标题
description: 一句话描述           # 推荐：预览用
resource: https://example.com    # 推荐：资源链接
tags:                            # 推荐：标签列表
  - tag1
  - tag2
timestamp: 2026-06-18T10:00:00Z  # 推荐：ISO 8601 时间戳
---

# 标题

内容...

## 详细说明

更多内容...

# Citations

[1] [参考来源](https://...)
```

### 知识类型

| type | 说明 | 目录 |
|------|------|------|
| `fact` | 可验证的陈述 | `atoms/facts/` |
| `method` | 操作步骤 | `atoms/methods/` |
| `definition` | 概念解释 | `atoms/definitions/` |
| `opinion` | 主观判断 | `atoms/opinions/` |
| `data` | 数值/统计 | `atoms/data/` |
| `question` | 待解答 | `atoms/questions/` |
| `reference` | 外部参考 | `atoms/references/` |

## 示例

查看 `examples/nextcloud-kb/` 目录中的示例知识库：

```
examples/nextcloud-kb/
├── index.md
└── atoms/
    ├── methods/
    │   └── nextcloud-installation-ubuntu-apache.md
    └── facts/
        └── nextcloud-system-requirements.md
```

## 模块结构

llm-wiki 采用模块化架构，将原本 2775 行的单体文件拆分为多个独立模块：

```
llm-wiki/
├── llm-wiki.py              # CLI 入口（argparse + cmd_*）约 590 行
├── lib/
│   ├── __init__.py          # 模块初始化 + 导出
│   ├── constants.py         # 常量定义（RESERVED_FILES 等）
│   ├── registry.py          # KBRegistry 知识库注册表
│   ├── yaml_parser.py       # SimpleYAMLParser YAML 解析
│   ├── validator.py         # OKFValidator OKF 规范验证
│   ├── exporter.py          # OKFExporter 导出 Bundle
│   ├── importer.py          # OKFImporter 导入 Bundle
│   ├── initializer.py       # KBInitializer 知识库初始化
│   ├── indexer.py           # IndexGenerator 索引生成
│   ├── ingestor.py          # KnowledgeIngestor 资料摄入
│   ├── querier.py           # AggregatedQuerier + KnowledgeQuerier 查询
│   ├── semantic.py          # SemanticSearchEngine 语义搜索
│   └── visualizer.py        # KnowledgeVisualizer 可视化
```

**设计原则：**

- **CLI 入口**：`llm-wiki.py` 仅包含 argparse 和 `cmd_*` 命令函数
- **核心模块**：每个模块职责单一，文件大小不超过 350 行
- **类型注解**：所有内部方法添加类型注解
- **异常处理**：使用具体异常类型而非裸 `except:`

## 相关资源

- [OKF 规范 v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
- [OKF 示例 Bundle](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf/bundles)
- [Google Cloud Knowledge Catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)

## 技术说明

### 核心技术

| 技术 | 用途 | 说明 |
|------|------|------|
| Python 标准库 | 核心功能 | 无外部依赖（语义搜索除外） |
| SimpleYAMLParser | YAML 解析 | 自实现，避免 PyYAML 依赖 |
| ChromaDB | 向量存储 | 语义搜索（可选） |
| sentence-transformers | 嵌入模型 | `all-MiniLM-L6-v2`（可选） |
| Cytoscape.js | 知识图谱 | 可视化 HTML |

### 搜索技术对比

| 特性 | 关键词搜索 | 语义搜索 |
|------|-----------|---------|
| 依赖 | 无 | ChromaDB + sentence-transformers |
| 理解能力 | 字面匹配 | 意义理解 |
| 同义词 | ❌ 不支持 | ✅ 支持 |
| 多语言 | ✅ 支持 | ✅ 支持（模型决定） |
| 准确度 | 高（精确匹配） | 高（相关匹配） |
| 速度 | 快 | 较慢（需要嵌入） |

### 增强搜索的建议

当前语义搜索使用 `all-MiniLM-L6-v2` 模型。以下是增强建议：

1. **同义词扩展**
   - 使用 WordNet 或自定义同义词词典
   - 在关键词搜索中扩展查询词

2. **全文索引**
   - 集成 SQLite FTS5（Python 内置）
   - 支持更高效的文本检索

3. **混合搜索**
   - 结合关键词和语义搜索结果
   - 优先精确匹配，补充语义相关

4. **多语言嵌入模型**
   - 使用 `paraphrase-multilingual-MiniLM-L12-v2`
   - 支持中英文混合查询

5. **领域微调**
   - 在特定领域数据上微调嵌入模型
   - 提升专业术语的理解能力

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

[MIT License](LICENSE)

Copyright (c) 2026 Tiandiyiqi