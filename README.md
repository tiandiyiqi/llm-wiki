# LLM Wiki - OKF 知识库管理工具

[![OKF v0.1](https://img.shields.io/badge/OKF-v0.1-blue.svg)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于 [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) 规范的知识库 CLI 管理工具。

## 特性

- ✅ **OKF v0.1 完全兼容** - 符合 Google Cloud Platform 提出的开放知识格式规范
- ✅ **零外部依赖** - 仅使用 Python 标准库，无需 pip install
- ✅ **五大核心命令** - init/export/import/lint/index
- ✅ **自动验证** - OKF 规范符合性检查
- ✅ **单文件部署** - 一个 `.py` 文件即可使用
- ✅ **Claude Code 集成** - 可作为 Skill 使用

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

用户: /llm-wiki lint ./my-kb --okf-check
Claude: 正在检查 OKF 兼容性...
```

### 方式三：创建别名（可选）

添加到 `~/.zshrc` 或 `~/.bashrc`：

```bash
alias llm-wiki='python3 /path/to/llm-wiki/llm-wiki.py'
```

然后可以直接使用：

```bash
llm-wiki init ./my-kb
llm-wiki export ./my-kb -o bundle.tar.gz
```

## 快速开始

### 1. 初始化知识库

```bash
python3 llm-wiki.py init ./my-knowledge-base
```

### 2. 添加知识原子

在 `my-knowledge-base/atoms/methods/` 创建文件：

```markdown
---
type: method
title: 示例方法
description: 这是一个示例知识原子
tags:
  - example
timestamp: 2026-06-18T10:00:00Z
---

# 示例方法

## 步骤

1. 第一步
2. 第二步

# Citations

[1] [参考来源](https://example.com)
```

### 3. 验证

```bash
python3 llm-wiki.py lint ./my-knowledge-base --okf-check
```

### 4. 导出

```bash
python3 llm-wiki.py export ./my-knowledge-base -o knowledge-bundle.tar.gz
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

**用法：**

```bash
python3 llm-wiki.py init <knowledge_base>
```

**参数：**

| 参数 | 说明 |
|------|------|
| `knowledge_base` | 知识库目录路径（必需） |

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
│   ├── reference/    # 参考资料
│   └── observations/ # 观察
└── views/            # 视图/可视化
```

---

### lint - OKF 兼容性检查

验证知识库是否符合 OKF v0.1 规范。

**用法：**

```bash
python3 llm-wiki.py lint <knowledge_base> [--okf-check]
```

**参数：**

| 参数 | 说明 |
|------|------|
| `knowledge_base` | 知识库目录路径（必需） |
| `--okf-check` | 显示详细的 OKF 规范检查结果 |

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
| `index.md` 结构 | 🟡 警告 | 保留文件应符合规范 |

---

### export - 导出 OKF Bundle

将知识库打包为 `.tar.gz` 文件，包含 `manifest.json` 元数据。

**用法：**

```bash
python3 llm-wiki.py export <knowledge_base> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `knowledge_base` | - | 知识库目录路径（必需） |
| `--output <path>` | `-o` | 输出文件路径（默认：`<kb_name>-okf-bundle.tar.gz`） |
| `--validate` | `-v` | 验证 OKF 符合性（默认开启） |
| `--no-validate` | - | 跳过验证 |
| `--force` | `-f` | 强制导出（忽略验证错误） |

**示例：**

```bash
# 基本导出（自动验证）
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz

# 强制导出（忽略验证错误）
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz --force

# 跳过验证
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz --no-validate
```

**输出内容：**

```
bundle.tar.gz
├── manifest.json              # 元数据（概念清单、统计）
├── index.md                   # 知识库索引
├── atoms/
│   ├── methods/
│   │   └── *.md
│   └── facts/
│       └── *.md
└── ...
```

**manifest.json 示例：**

```json
{
  "okf_version": "0.1",
  "export_time": "2026-06-18T10:00:00",
  "source_dir": "/path/to/kb",
  "concepts": [
    {
      "id": "atoms/methods/example",
      "type": "method",
      "title": "示例方法",
      "description": "..."
    }
  ],
  "statistics": {
    "total_concepts": 5,
    "types": {
      "method": 3,
      "fact": 2
    }
  }
}
```

---

### import - 导入 OKF Bundle

从 `.tar.gz` 文件恢复知识库。

**用法：**

```bash
python3 llm-wiki.py import <bundle> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `bundle` | - | Bundle 文件路径（必需） |
| `--output <dir>` | `-o` | 输出目录（默认：当前目录） |
| `--overwrite` | - | 覆盖现有文件 |

**示例：**

```bash
# 导入到新目录
python3 llm-wiki.py import bundle.tar.gz -o ./restored-kb

# 导入并覆盖现有目录
python3 llm-wiki.py import bundle.tar.gz -o ./existing-kb --overwrite

# 导入到当前目录
python3 llm-wiki.py import bundle.tar.gz
```

---

### index - 生成目录索引

为知识库目录生成 `index.md` 文件（渐进披露）。

**用法：**

```bash
python3 llm-wiki.py index <knowledge_base> [options]
```

**参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `knowledge_base` | - | 知识库目录路径（必需） |
| `--directory <dir>` | `-d` | 指定要生成索引的子目录 |

**示例：**

```bash
# 为整个知识库生成索引
python3 llm-wiki.py index ./my-kb

# 为指定目录生成索引
python3 llm-wiki.py index ./my-kb -d ./my-kb/atoms/methods
```

**生成的 index.md 示例：**

```markdown
# Knowledge Concepts Index

## Statistics

- Total concepts: 5

## Concepts

### method

* [示例方法](/atoms/methods/example.md) - 这是一个示例方法

### fact

* [示例事实](/atoms/facts/example-fact.md) - 这是一个示例事实
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
[2] [另一个来源](https://...)
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