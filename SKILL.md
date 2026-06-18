---
name: llm-wiki
description: 基于 OKF 规范的知识库构建与维护。采用 Markdown + YAML frontmatter 格式，支持知识原子管理、语义搜索、主动发现、版本演化。符合 Open Knowledge Format (OKF) 标准。
version: 3.0
---

# LLM Wiki v3.0 - OKF 兼容知识库架构

> **核心理念**：知识是人类与 AI 共创的、演化的、可追溯的。基于 Open Knowledge Format (OKF) 规范，确保知识的可移植性和互操作性。

---

## 目录

- [OKF 规范核心](#okf-规范核心)
- [六层架构总览](#六层架构总览)
- [知识原子规范](#知识原子规范)
- [核心操作](#核心操作)
- [命令参考](#命令参考)
- [可视化工具](#可视化工具)
- [最佳实践](#最佳实践)

---

## OKF 规范核心

### 什么是 OKF？

OKF (Open Knowledge Format) 是 Google Cloud Platform 提出的开放知识格式规范：
- **通用格式**：Markdown + YAML frontmatter
- **厂商中立**：不依赖特定工具、框架或平台
- **可移植性**：Git 管理，可打包、可同步、可迁移
- **渐进披露**：通过 index.md 支持层级导航

### OKF 核心概念映射

| OKF 术语 | LLM Wiki 术语 | 说明 |
|----------|---------------|------|
| Knowledge Bundle | 知识库 | 整个知识库目录 |
| Concept | Atom（原子） | 单个知识单元 |
| Concept ID | atom_id | 原子的唯一标识 |
| Frontmatter | Frontmatter | YAML 元数据块 |
| Body | Content | Markdown 内容 |
| Cross-link | Relation | 原子间关联 |
| Citation | Source | 外部引用来源 |

### OKF 兼容性检查

知识库符合 OKF v0.1 规范需满足：

1. ✅ 每个 `.md` 文件有 YAML frontmatter
2. ✅ frontmatter 包含 `type` 字段
3. ✅ 使用 `index.md` 进行目录索引
4. ✅ 跨原子链接使用标准 Markdown 格式
5. ✅ 可通过 Git 版本控制

---

## 六层架构总览

```
┌─────────────────────────────────────────────────────────┐
│  Layer 6: 用户交互层 (Interaction)                        │
│   问答 / 浏览 / 可视化 / 导出                             │
└─────────────────────────────────────────────────────────┘
                           ↑
┌─────────────────────────────────────────────────────────┐
│  Layer 5: 智能发现层 (Discovery)                          │
│   语义搜索 / 主动推送 / 缺口检测 / 关联发现                │
└─────────────────────────────────────────────────────────┘
                           ↑
┌─────────────────────────────────────────────────────────┐
│  Layer 4: 知识演化层 (Evolution)                          │
│   版本管理 / 争议追踪 / 置信度评估 / 验证机制              │
└─────────────────────────────────────────────────────────┘
                           ↑
┌─────────────────────────────────────────────────────────┐
│  Layer 3: 多维视图层 (Views)                              │
│   类型视图 / 时间视图 / 争议视图 / 应用视图                │
└─────────────────────────────────────────────────────────┘
                           ↑
┌─────────────────────────────────────────────────────────┐
│  Layer 2: 知识原子层 (Atoms) ← OKF 核心                    │
│   扁平的知识片段（带 frontmatter、语义向量、关系指针）     │
└─────────────────────────────────────────────────────────┘
                           ↑
┌─────────────────────────────────────────────────────────┐
│  Layer 1: 原始资料层 (Sources)                            │
│   文件 / 网页 / 对话 / 观察 —— 不可变的数据源              │
└─────────────────────────────────────────────────────────┘
```

---

## 知识原子规范

### OKF 标准 Frontmatter

```yaml
---
# === OKF 必需字段 ===
type: method                    # 必需：知识类型

# === OKF 推荐字段 ===
title: Ubuntu Apache 安装指南   # 推荐：显示标题
description: Nextcloud 在 Ubuntu 上使用 Apache 的标准安装流程  # 推荐：一句话描述
resource: https://docs.nextcloud.com/server/latest/admin_manual/installation/  # 推荐：资源链接
tags:                           # 推荐：标签列表
  - installation
  - ubuntu
  - apache
timestamp: 2026-06-18T10:30:00Z  # 推荐：最后更新时间

# === OKF 扩展字段 ===
atom_id: nextcloud-installation-ubuntu-apache
created: 2026-06-18
updated: 2026-06-18
source: raw/reference/official-docs.md
source_type: official           # official | academic | blog | user | observation
confidence: 0.95
verified: true
applicable_versions:
  - "30"
  - "31"
  - "32"
  - "33"
  - "34"

# === 关系字段 ===
relations:
  - relates_to: [[nextcloud-system-requirements]]
  - relates_to: [[nextcloud-config-php-extensions]]
  - contradicts: null           # 矛盾原子（用于争议追踪）
  - supports: null              # 支持原子
---
```

### 字段优先级（基于 OKF 规范）

| 优先级 | 字段 | 状态 | 说明 |
|--------|------|------|------|
| **必需** | `type` | ✅ 必须 | 知识类型标识 |
| **P1** | `title` | ✅ 强烈建议 | 显示标题，用于搜索和索引 |
| **P2** | `description` | ✅ 强烈建议 | 一句话描述，用于预览 |
| **P3** | `resource` | ⭐ 建议 | 关联的真实资源 URI |
| **P4** | `tags` | ⭐ 建议 | 跨分类标签 |
| **P5** | `timestamp` | ⭐ 建议 | ISO 8601 时间戳 |

### 知识类型定义

| type 值 | 说明 | 目录 |
|---------|------|------|
| `fact` | 可验证的陈述 | `atoms/facts/` |
| `opinion` | 主观判断 | `atoms/opinions/` |
| `definition` | 概念解释 | `atoms/definitions/` |
| `method` | 操作步骤 | `atoms/methods/` |
| `data` | 数值/统计 | `atoms/data/` |
| `question` | 待解答 | `atoms/questions/` |
| `reference` | 外部参考 | `atoms/references/` |

### 原子内容结构

```markdown
---
# frontmatter（如上）
---

# 标题

## 定义 / 概述

<!-- 核心内容 -->

## 详细说明

<!-- 展开内容 -->

## 示例

<!-- 代码示例、配置示例 -->

## 相关链接

- [[related-atom-1]] - 相关原子 1
- [[related-atom-2]] - 相关原子 2

# Citations

[1] [Nextcloud 官方文档](https://docs.nextcloud.com/...)
[2] [Ubuntu Server Guide](https://ubuntu.com/...)
```

### 链接规范

**OKF 支持两种链接格式：**

1. **绝对路径（推荐）**：从知识库根目录开始
   ```markdown
   参见 [[/methods/nextcloud-installation-ubuntu-apache]]
   ```

2. **相对路径**：相对于当前文件
   ```markdown
   参见 [[./nextcloud-config-apache]]
   ```

3. **简化格式（LLM Wiki 扩展）**：使用 atom_id
   ```markdown
   参见 [[nextcloud-installation-ubuntu-apache]]
   ```

---

## 核心操作

### 1. Ingest（资料摄入）

**OKF 兼容流程：**

```
┌──────────────┐
│  检测新资料   │
└──────┬───────┘
       ↓
┌──────────────┐
│  读取并分析   │
└──────┬───────┘
       ↓
┌──────────────┐
│  提取知识原子 │  生成 OKF 格式原子
└──────┬───────┘
       ↓
┌──────────────┐
│  添加元数据   │  title, description, resource, tags
└──────┬───────┘
       ↓
┌──────────────┐
│  计算置信度   │
└──────┬───────┘
       ↓
┌──────────────┐
│  语义匹配     │  发现关联
└──────┬───────┘
       ↓
┌──────────────┐
│  更新 index   │  更新目录索引
└──────┬───────┘
       ↓
┌──────────────┐
│  添加 Citations│ 记录来源
└──────────────┘
```

**原子生成模板：**

```yaml
---
type: method
title: {自动生成或从标题提取}
description: {从首段提取一句话}
resource: {来源链接}
tags: {从内容提取关键词}
timestamp: {当前时间 ISO 8601}
atom_id: {kebab-case-id}
created: {当前日期}
updated: {当前日期}
source: {原始资料路径}
source_type: {来源类型}
confidence: {计算值}
verified: false
---

# {标题}

## 定义

{核心内容}

## 详细说明

{展开内容}

# Citations

[1] [{来源标题}]({来源链接})
```

---

### 2. Query（知识查询）

**OKF 兼容查询流程：**

```
用户提问
    ↓
语义搜索原子
    ↓
按置信度排序
    ↓
聚合相关原子
    ↓
生成回答（带 OKF 引用格式）
    ↓
返回 Citations 列表
```

**回答格式（OKF 兼容）：**

```markdown
## 回答

{生成的回答}

### 证据

| 原子 | 类型 | 置信度 |
|------|------|--------|
| [[atom-1]] | fact | 0.95 |
| [[atom-2]] | method | 0.90 |

### Citations

[1] [Nextcloud 官方文档](https://docs.nextcloud.com/...)
[2] [安全白皮书](https://nextcloud.com/security/)
```

---

### 3. Lint（健康检查）

**OKF 兼容性检查：**

| 检查项 | 说明 | 级别 |
|--------|------|------|
| `type` 缺失 | OKF 必需字段缺失 | 🔴 致命 |
| `title` 缺失 | OKF 推荐字段缺失 | 🟡 警告 |
| `description` 缺失 | OKF 推荐字段缺失 | 🟡 警告 |
| `timestamp` 缺失 | OKF 推荐字段缺失 | 🟢 提示 |
| 断链检测 | 链接目标不存在 | 🟡 警告 |
| frontmatter 解析错误 | YAML 格式问题 | 🔴 致命 |
| `atom_id` 重复 | 唯一性冲突 | 🔴 致命 |

**运行命令：**

```bash
/llm-wiki lint --okf-check
```

---

### 4. Index（索引生成）

**OKF 要求：每个目录有 `index.md` 支持渐进披露。**

**index.md 模板：**

```markdown
# {目录名} - 知识原子索引

## 统计

- 总原子数：{N}
- 类型分布：
  - methods: {M}
  - facts: {F}
  - definitions: {D}

## 原子列表

### 方法原子 (Methods)

* [Ubuntu Apache 安装](nextcloud-installation-ubuntu-apache.md) - Nextcloud 在 Ubuntu 上使用 Apache 的标准安装流程
* [性能优化配置](nextcloud-config-performance-optimization.md) - 缓存、预览、上传优化配置

### 事实原子 (Facts)

* [系统要求](nextcloud-system-requirements.md) - Nextcloud 服务器系统要求

## 按标签

### installation
* [[nextcloud-installation-ubuntu-apache]]
* [[nextcloud-system-requirements]]

### security
* [[nextcloud-ssl-https-configuration]]
```

---

### 5. Visualize（可视化）

**OKF Bundle 可视化：**

生成单文件 HTML 可视化工具：

```bash
/llm-wiki visualize --output views/knowledge-graph.html
```

**功能：**
- 力导向知识图谱
- 按类型着色节点
- 点击查看详情
- 搜索和过滤
- 反向链接（Cited by）

---

## 命令参考

### 安装与使用

```bash
# 命令位置
~/.claude/skills/llm-wiki/llm-wiki.py

# 使用方式
python3 ~/.claude/skills/llm-wiki/llm-wiki.py <command> [options]

# 或创建别名（添加到 ~/.zshrc 或 ~/.bashrc）
alias llm-wiki='python3 ~/.claude/skills/llm-wiki/llm-wiki.py'
```

### 基本命令

| 命令 | 用途 | 示例 |
|------|------|------|
| `llm-wiki init` | 初始化知识库 | `llm-wiki init ./my-kb` |
| `llm-wiki lint` | OKF 兼容性检查 | `llm-wiki lint ./my-kb --okf-check` |
| `llm-wiki export` | 导出为 OKF Bundle | `llm-wiki export ./my-kb -o bundle.tar.gz` |
| `llm-wiki import` | 导入 OKF Bundle | `llm-wiki import bundle.tar.gz -o ./my-kb` |
| `llm-wiki index` | 生成目录索引 | `llm-wiki index ./my-kb` |

### 命令详解

#### init - 初始化知识库

创建符合 OKF 规范的知识库目录结构。

```bash
llm-wiki init ./my-kb
```

创建的目录结构：
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

#### lint - OKF 兼容性检查

验证知识库是否符合 OKF v0.1 规范。

```bash
llm-wiki lint ./my-kb
llm-wiki lint ./my-kb --okf-check  # 显示详细规范检查
```

检查项目：
- 每个 `.md` 文件是否有 YAML frontmatter
- frontmatter 是否包含必需的 `type` 字段
- 推荐字段（title, description, timestamp）是否缺失
- 保留文件（index.md, log.md）是否符合规范

#### export - 导出 OKF Bundle

将知识库打包为符合 OKF 规范的 tar.gz 文件。

```bash
# 基本导出（自动验证）
llm-wiki export ./my-kb -o bundle.tar.gz

# 强制导出（忽略验证错误）
llm-wiki export ./my-kb -o bundle.tar.gz --force

# 跳过验证
llm-wiki export ./my-kb -o bundle.tar.gz --no-validate
```

导出内容：
- `manifest.json` - 知识库元数据（概念清单、统计）
- 所有 `.md` 文件（保留目录结构）
- 支持文件（图片等，排除隐藏文件）

#### import - 导入 OKF Bundle

从 tar.gz 文件恢复知识库。

```bash
# 导入到新目录
llm-wiki import bundle.tar.gz -o ./restored-kb

# 导入并覆盖现有目录
llm-wiki import bundle.tar.gz -o ./existing-kb --overwrite
```

#### index - 生成目录索引

为知识库目录生成 index.md 文件（渐进披露）。

```bash
llm-wiki index ./my-kb
llm-wiki index ./my-kb -d ./my-kb/atoms/methods  # 指定目录
```

### OKF 特定命令

```bash
# 检查 OKF 兼容性
llm-wiki lint ./my-kb --okf-check

# 导出为 OKF Bundle
llm-wiki export ./my-kb --format okf --output bundle.tar.gz

# 从 OKF Bundle 导入
llm-wiki import bundle.tar.gz --output ./my-kb
```

---

## 可视化工具

### OKF Bundle Visualizer

生成单文件 HTML 可视化：

```bash
/llm-wiki visualize \
  --bundle ./atoms \
  --output ./views/knowledge-graph.html \
  --name "Nextcloud Knowledge Base"
```

**技术栈：**
- Cytoscape.js - 图谱渲染
- marked - Markdown 渲染
- 单文件 HTML - 无需后端

**功能：**
1. 力导向图布局
2. 节点按 type 着色
3. 点击节点显示详情
4. 搜索框（匹配 title, atom_id, tags）
5. 类型过滤
6. 布局切换（cose/concentric/circle/grid）
7. 反向链接列表

---

## 最佳实践

### OKF 兼容性检查清单

- [ ] 每个原子有 `type` 字段（必需）
- [ ] 每个原子有 `title` 字段（推荐）
- [ ] 每个原子有 `description` 字段（推荐）
- [ ] 每个原子有 `timestamp` 字段（推荐）
- [ ] 每个目录有 `index.md`（渐进披露）
- [ ] 使用标准 Markdown 链接格式
- [ ] 原子末尾有 `# Citations` 部分
- [ ] 可通过 Git 版本控制

### 用户职责

1. **资料筛选**：选择高质量来源
2. **置信度把关**：验证低置信度原子
3. **争议裁决**：决定争议处理方式
4. **标题审核**：确保 title 准确描述
5. **描述优化**：确保 description 简洁明了

### LLM 职责

1. **原子提取**：拆分资料为原子
2. **元数据生成**：自动生成 title, description, tags
3. **置信度计算**：评估知识可信度
4. **关联发现**：主动推送发现
5. **索引维护**：更新 index.md
6. **可视化支持**：生成图谱

### 推荐工作流

```
用户                          LLM
 │                            │
 ├─ 提供新资料 ─────────────────→ 提取原子
 │                            │
 │                            → 生成 OKF 元数据
 │                            │ (type, title, description, tags, timestamp)
 │                            │
 │ ←─ 发现推送 ────────────────┤ "发现关联..."
 │                            │ "发现缺口..."
 │                            │
 ├─ 确认/补充 ─────────────────→ 更新原子
 │                            │
 │                            → 更新 index.md
 │                            │
 │                            → 添加 Citations
 │                            │
 ├─ 提出问题 ─────────────────→ 语义搜索
 │                            │
 │ ←─ 回答（带 Citations）─────┤
 │                            │
 ├─（定期）────────────────────→ OKF 兼容性检查
 │                            │
 │ ←─ 健康报告 ────────────────┤
```

---

## 迁移指南：从 v2.0 到 v3.0

### 主要变化

| 变化项 | v2.0 | v3.0 (OKF) |
|--------|------|------------|
| `atom_id` 格式 | `atom-YYYY-MM-DD-NNN` | `kebab-case-name` |
| 必需字段 | `atom_id`, `type` | `type` (OKF) |
| 新增字段 | - | `title`, `description`, `timestamp` |
| 链接格式 | `[[atom-id]]` | `[[/path/to/atom.md]]` 或 `[[atom-id]]` |
| 索引文件 | 仅根目录 `index.md` | 每个目录 `index.md` |
| 引用来源 | `source` 字段 | `# Citations` 部分 |

### Frontmatter 迁移

**v2.0 格式：**
```yaml
---
atom_id: atom-2026-06-17-001
type: method
created: 2026-06-17
source: raw/doc.pdf
confidence: 0.85
---
```

**v3.0 (OKF) 格式：**
```yaml
---
type: method
title: Nextcloud 安装指南
description: Ubuntu Apache 标准安装流程
timestamp: 2026-06-17T10:00:00Z
atom_id: nextcloud-installation-ubuntu-apache
created: 2026-06-17
source: raw/doc.pdf
confidence: 0.85
tags:
  - installation
  - ubuntu
---
```

### 批量迁移命令

```bash
# 添加 title 和 description
/llm-wiki migrate --add-title --add-description

# 更新 timestamp 格式
/llm-wiki migrate --fix-timestamp

# 生成所有目录的 index.md
/llm-wiki migrate --generate-indexes

# 添加 Citations 部分
/llm-wiki migrate --add-citations
```

---

## 附录

### A. OKF Bundle 结构

```
knowledge-base/
├── index.md                    # 知识库根索引
├── log.md                      # 更新日志（可选）
├── atoms/                      # 知识原子
│   ├── index.md
│   ├── methods/
│   │   ├── index.md
│   │   ├── nextcloud-installation-ubuntu-apache.md
│   │   └── ...
│   ├── facts/
│   │   ├── index.md
│   │   └── ...
│   └── definitions/
│       ├── index.md
│       └── ...
├── views/                      # 多维视图
│   └── knowledge-graph.html
└── raw/                        # 原始资料
    ├── reference/
    └── observations/
```

### B. 置信度计算

```
置信度 = 来源可信度 × 验证系数 × 共识系数

来源可信度：
- 官方文档：0.9
- 学术论文：0.8
- 源码分析：0.85
- 技术博客：0.6
- 用户观察：0.5

验证系数：
- 已验证：1.0
- 待验证：0.7
- 有争议：0.5

共识系数：
- 多来源一致：1.0
- 单来源：0.8
- 有分歧：0.6
```

### C. 参考资源

- [OKF 规范 v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
- [OKF 示例 Bundle](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf/bundles)
- [Cytoscape.js](https://js.cytoscape.org/) - 图谱可视化
- [marked](https://marked.js.org/) - Markdown 渲染

---

## 版本历史

| 版本 | 日期 | 主要变化 |
|------|------|----------|
| v1.0 | 2026-06-17 | 基于 Karpathy 原始理念 |
| v2.0 | 2026-06-17 | 六层架构、知识原子、多维视图、智能发现、知识演化 |
| v3.0 | 2026-06-18 | **OKF 兼容**：符合 Open Knowledge Format 规范，添加 title/description/timestamp，渐进披露，Citations 支持 |
