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

## 快速开始

### 下载

```bash
git clone https://github.com/Tiandiyiqi/llm-wiki.git
cd llm-wiki
```

### 初始化知识库

```bash
python3 llm-wiki.py init ./my-knowledge-base
```

### 添加知识原子

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

### 验证

```bash
python3 llm-wiki.py lint ./my-knowledge-base --okf-check
```

### 导出

```bash
python3 llm-wiki.py export ./my-knowledge-base -o knowledge-bundle.tar.gz
```

## 命令参考

| 命令 | 用途 | 示例 |
|------|------|------|
| `init` | 初始化知识库目录结构 | `llm-wiki.py init ./kb` |
| `lint` | OKF 兼容性检查 | `llm-wiki.py lint ./kb --okf-check` |
| `export` | 导出为 OKF Bundle | `llm-wiki.py export ./kb -o bundle.tar.gz` |
| `import` | 导入 OKF Bundle | `llm-wiki.py import bundle.tar.gz -o ./kb` |
| `index` | 生成目录索引 | `llm-wiki.py index ./kb` |

### init - 初始化知识库

创建符合 OKF 规范的目录结构：

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

### lint - OKF 兼容性检查

验证知识库是否符合 OKF v0.1 规范：

```bash
python3 llm-wiki.py lint ./my-kb --okf-check
```

检查项目：
- 每个 `.md` 文件是否有 YAML frontmatter
- frontmatter 是否包含必需的 `type` 字段
- 推荐字段（title, description, timestamp）是否缺失

### export - 导出 OKF Bundle

将知识库打包为 `.tar.gz` 文件：

```bash
# 基本导出
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz

# 强制导出（忽略验证错误）
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz --force

# 跳过验证
python3 llm-wiki.py export ./my-kb -o bundle.tar.gz --no-validate
```

### import - 导入 OKF Bundle

从 `.tar.gz` 文件恢复知识库：

```bash
python3 llm-wiki.py import bundle.tar.gz -o ./restored-kb
```

### index - 生成目录索引

为知识库目录生成 `index.md` 文件（渐进披露）：

```bash
python3 llm-wiki.py index ./my-kb
```

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

查看 `examples/nextcloud-kb/` 目录中的示例知识库。

## 相关资源

- [OKF 规范 v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
- [OKF 示例 Bundle](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf/bundles)
- [Google Cloud Knowledge Catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT License](LICENSE)

Copyright (c) 2026 Tiandiyiqi