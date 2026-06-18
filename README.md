# LLM Wiki - OKF 知识库管理工具

[![OKF v0.1](https://img.shields.io/badge/OKF-v0.1-blue.svg)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于 [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) 规范的知识库 CLI 管理工具。

## 特性

- ✅ **OKF v0.1 完全兼容** - 符合 Google Cloud Platform 提出的开放知识格式规范
- ✅ **零外部依赖** - 仅使用 Python 标准库，无需 pip install
- ✅ **八大核心命令** - init/ingest/query/lint/index/export/import/visualize
- ✅ **智能提取** - 自动检测知识类型、提取标题和标签
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

用户: /llm-wiki query ./my-kb "installation"
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
python3 llm-wiki.py ingest ./my-kb raw/document.md

# 3. 查询知识
python3 llm-wiki.py query ./my-kb "installation"

# 4. 验证 OKF 兼容性
python3 llm-wiki.py lint ./my-kb --okf-check

# 5. 生成知识图谱
python3 llm-wiki.py visualize ./my-kb

# 6. 导出 Bundle
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz
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

**示例：**
```bash
python3 llm-wiki.py init ./my-kb
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

### ingest - 摄入资料提取原子

从源文件自动提取知识原子，支持 Markdown 文件。

```bash
python3 llm-wiki.py ingest <knowledge_base> <source> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `knowledge_base` | - | 知识库目录路径（必需） |
| `source` | - | 源文件路径（必需） |
| `--type` | `-t` | 原子类型（默认自动检测） |
| `--auto-type` | - | 自动检测类型（默认开启） |

**示例：**
```bash
# 摄入文档（自动检测类型）
python3 llm-wiki.py ingest ./my-kb raw/document.md

# 指定类型
python3 llm-wiki.py ingest ./my-kb raw/tutorial.md --type method
```

**自动检测规则：**
- 包含 "步骤"、"step"、"how to"、"安装" → `method`
- 包含 "要求"、"requirement"、"版本" → `fact`
- 包含 "定义"、"definition"、"概念" → `definition`
- 包含 "统计"、"数据"、"性能" → `data`

---

### query - 搜索查询知识

在知识库中搜索知识原子。

```bash
python3 llm-wiki.py query <knowledge_base> <query> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `knowledge_base` | - | 知识库目录路径（必需） |
| `query` | - | 查询关键词（必需） |
| `--type` | `-t` | 按类型过滤 |
| `--limit` | `-l` | 结果数量限制（默认：10） |

**示例：**
```bash
# 基本搜索
python3 llm-wiki.py query ./my-kb "installation"

# 按类型过滤
python3 llm-wiki.py query ./my-kb "ubuntu" --type method

# 限制结果数量
python3 llm-wiki.py query ./my-kb "config" --limit 5
```

**搜索优先级：**
1. 标题匹配（最高优先级）
2. 描述匹配
3. 标签匹配
4. 正文匹配

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

**示例：**
```bash
# 基本导出
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz

# 强制导出
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz --force
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

### 典型工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Wiki 工作流程                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 初始化                                                   │
│     $ llm-wiki init ./my-kb                                 │
│                                                             │
│  2. 收集资料 → 放入 raw/ 目录                                 │
│     - 官方文档、博客文章、教程                                │
│     - PDF、Markdown、文本文件                                │
│                                                             │
│  3. 摄入提取                                                 │
│     $ llm-wiki ingest ./my-kb raw/doc.md                    │
│     → 自动提取知识原子到 atoms/                              │
│                                                             │
│  4. 人工审核                                                 │
│     - 检查提取的知识是否准确                                  │
│     - 补充缺失的元数据                                       │
│                                                             │
│  5. 验证                                                     │
│     $ llm-wiki lint ./my-kb --okf-check                     │
│                                                             │
│  6. 查询使用                                                 │
│     $ llm-wiki query ./my-kb "installation"                 │
│     $ llm-wiki visualize ./my-kb                            │
│                                                             │
│  7. 分享备份                                                 │
│     $ llm-wiki export ./my-kb -o bundle.tar.gz              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

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
    llm-wiki ingest ./tech-docs "$f"
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
llm-wiki ingest ./project-kb ./README.md --type reference
llm-wiki ingest ./project-kb ./SETUP.md --type method
llm-wiki ingest ./project-kb ./API.md --type reference

# 3. 查询
llm-wiki query ./project-kb "api"
llm-wiki query ./project-kb "setup" --type method
```

#### 场景三：个人学习笔记

**需求：** 整理学习笔记，建立知识图谱

**步骤：**
```bash
# 1. 初始化
llm-wiki init ./learning-notes

# 2. 摄入笔记
llm-wiki ingest ./learning-notes notes/python-basics.md
llm-wiki ingest ./learning-notes notes/python-advanced.md

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
/llm-wiki ingest ./my-knowledge raw/article.md
/llm-wiki query ./my-knowledge "关键词"
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

## 相关资源

- [OKF 规范 v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
- [OKF 示例 Bundle](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf/bundles)
- [Google Cloud Knowledge Catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)

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