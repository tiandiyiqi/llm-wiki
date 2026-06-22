# PostgreSQL 迁移指南

本文档介绍如何将 llm-wiki 从文件存储模式迁移到 PostgreSQL 数据库模式。

## 概述

llm-wiki 支持两种存储模式：

| 模式 | 存储 | 适用场景 |
|------|------|----------|
| `file_mode` | Markdown 文件 + JSON | 个人使用、Obsidian 兼容 |
| `db_mode` | PostgreSQL | 团队协作、企业部署 |

## 前置条件

### 系统要求

- PostgreSQL 15+
- Python 3.8+
- 可选：pgvector 扩展（向量搜索）

### 安装依赖

```bash
# 安装 PostgreSQL 依赖
pip install asyncpg

# 可选：向量搜索支持
pip install pgvector
```

### 数据库准备

```bash
# 创建数据库
createdb llm_wiki

# 启用扩展
psql -d llm_wiki -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d llm_wiki -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

# 执行 Schema
psql -d llm_wiki -f lib/db/schema.sql
psql -d llm_wiki -f lib/db/indexes.sql
psql -d llm_wiki -f lib/db/functions.sql
psql -d llm_wiki -f lib/db/rls.sql
```

## 配置

### 环境变量

```bash
# 存储类型
export LLM_WIKI_STORAGE_TYPE=postgres

# PostgreSQL 连接
export LLM_WIKI_POSTGRES_URL="postgresql://user:pass@localhost:5432/llm_wiki"

# 连接池配置
export LLM_WIKI_POOL_SIZE=10
export LLM_WIKI_MAX_OVERFLOW=20
```

### 配置文件

创建 `~/.llm-wiki/config.yaml`：

```yaml
storage:
  type: postgres
  postgres_url: postgresql://user:pass@localhost:5432/llm_wiki
  pool_size: 10
  max_overflow: 20

migration:
  keep_files: true
  validate: true
  batch_size: 100
```

## 迁移命令

### 迁移单个知识库

```bash
# 基本迁移
llm-wiki migrate my-kb --to postgres

# 保留原文件（推荐）
llm-wiki migrate my-kb --to postgres --keep-files

# 迁移后验证
llm-wiki migrate my-kb --to postgres --validate

# 预演模式（不实际迁移）
llm-wiki migrate my-kb --to postgres --dry-run
```

### 迁移所有知识库

```bash
# 迁移所有注册的知识库
llm-wiki migrate --all --to postgres
```

### 增量迁移

```bash
# 只迁移变更的内容
llm-wiki migrate my-kb --to postgres --incremental
```

## 迁移流程

```
1. 读取 registry.json
   └── 提取知识库元数据
        ↓
2. 创建 PostgreSQL 知识库记录
   └── 生成 kb_id
        ↓
3. 扫描 atoms/ 目录
   └── 解析 Markdown 文件
        ↓
4. 插入 atoms 表
   └── 提取 frontmatter → JSONB
        ↓
5. 迁移链接关系
   └── [[wikilinks]] → atom_links
        ↓
6. 生成向量嵌入
   └── Chromadb → pgvector
        ↓
7. 构建索引
   └── 全文索引 + 向量索引
        ↓
8. 数据验证
   └── 记录数对比 + 内容校验
        ↓
9. 更新元数据
   └── kb_meta.mode = 'db'
```

## 验证

### 验证迁移结果

```bash
# 完整验证
llm-wiki migrate my-kb --validate

# 验证项目：
# - 知识库数量一致
# - 原子数量一致
# - 链接关系完整
# - 搜索功能正常
```

### 搜索测试

```bash
# 测试全文搜索
llm-wiki search "machine learning" --kb my-kb

# 测试向量搜索（需要嵌入）
llm-wiki search "machine learning" --kb my-kb --semantic
```

## 回滚

如果迁移失败，可以回滚：

```bash
# 回滚到文件模式
llm-wiki config set storage.type sqlite

# 删除 PostgreSQL 数据（谨慎！）
llm-wiki kb delete my-kb --from postgres
```

## 常见问题

### Q: 迁移后原文件还在吗？

默认情况下，迁移会保留原文件。使用 `--keep-files` 参数确保这一点。

### Q: 迁移需要多长时间？

迁移时间取决于数据量：
- 100 个原子：约 10 秒
- 1000 个原子：约 1 分钟
- 10000 个原子：约 5 分钟

### Q: 如何处理向量嵌入？

如果已有 Chromadb 数据，迁移工具会自动迁移向量。如果没有，可以使用：

```bash
llm-wiki embed my-kb --model all-MiniLM-L6-v2
```

### Q: 迁移后如何切换回文件模式？

```bash
# 导出为 OKF Bundle
llm-wiki export my-kb -o my-kb-bundle.tar.gz

# 解压到新目录
tar -xzf my-kb-bundle.tar.gz -C /path/to/new/kb
```

## 技术细节

### 数据映射

| 文件模式 | PostgreSQL | 说明 |
|----------|------------|------|
| `kb_meta.yaml` | `knowledge_bases` 表 | 知识库元数据 |
| `atoms/*.md` | `atoms` 表 | 知识原子 |
| `frontmatter` | `atoms.metadata` (JSONB) | YAML 元数据 |
| `[[links]]` | `atom_links` 表 | 链接关系 |
| `#tags` | `tags` + `atom_tags` 表 | 标签 |
| Chromadb | `atoms.embedding` (vector) | 向量嵌入 |

### 性能优化

1. **批量插入**：使用批量插入减少数据库往返
2. **索引延迟**：迁移完成后一次性构建索引
3. **并行迁移**：多个知识库可并行迁移

## 相关命令

```bash
llm-wiki migrate --help     # 查看帮助
llm-wiki config list        # 查看当前配置
llm-wiki kb list            # 列出知识库
llm-wiki search --help      # 搜索帮助
```

## 实现说明

### 模块结构

```
lib/
├── core/                   # 存储抽象层
│   ├── db_manager.py       # DatabaseManager 抽象基类
│   ├── sqlite_manager.py   # SQLite 实现
│   ├── postgres_manager.py # PostgreSQL 实现（asyncpg）
│   ├── config.py           # StorageConfig / StorageType
│   └── factory.py          # create_manager() 工厂函数
├── db/                     # SQL Schema 定义
│   ├── schema.sql          # 核心表（knowledge_bases, atoms）
│   ├── indexes.sql         # 全文索引 + 向量索引
│   ├── functions.sql       # RLS 辅助函数
│   └── rls.sql             # Row Level Security 策略
├── migration/              # 迁移工具
│   ├── migrate.py          # MigrationManager
│   ├── validators.py       # MigrationValidator
│   └── cli.py              # CLI 命令 + MigrationCLI 类
└── search/                 # 搜索引擎
    ├── engine.py           # SearchEngine 抽象基类 + SearchResult
    ├── postgres_search.py  # PostgreSQLSearchEngine
    └── hybrid_search.py    # HybridSearchOptimizer
```

### Python API

```python
from lib.migration import MigrationManager
from lib.core import StorageConfig, StorageType, create_manager

# 工厂函数创建管理器
manager = await create_manager(StorageConfig(type=StorageType.SQLITE))

# 迁移管理器（dry-run 模式不需要真实 PostgreSQL）
mgr = MigrationManager(postgres_url='postgresql://localhost/wiki', dry_run=True)
result = await mgr.migrate_kb(Path('./my-kb'))
print(f"dry_run={result.dry_run}, success={result.success}")

# 搜索
from lib.search import PostgreSQLSearchEngine
engine = PostgreSQLSearchEngine(pool)
results = await engine.search('knowledge graph', kb_id=1)
```

### 注意事项

1. **dry-run 模式**：不需要 PostgreSQL 连接，可用于预览迁移计划
2. **懒初始化**：`MigrationManager` 在需要写入时才建立数据库连接
3. **幂等设计**：重复运行迁移会更新已有记录而非重复创建
4. **连接池**：PostgreSQL 模式使用 asyncpg 连接池，默认 10 个连接

---

**文档版本**：1.1
**最后更新**：2026-06-22
