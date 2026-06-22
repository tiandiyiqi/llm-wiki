# 任务组结构：PostgreSQL 迁移

## 元信息
- **源计划**：PLAN-001-postgresql-migration.md
- **创建时间**：2026-06-21
- **任务组数量**：13
- **总任务数**：36

---

## 执行顺序

### 任务组 1：核心目录初始化
**类型：** 并行
**前置条件：** 无
**阶段：** 阶段 1 + 阶段 2（可并行启动）

#### 任务 1-1：创建 core 目录结构
- [x] SUB-TASK-001: 创建 `lib/core/` 目录结构
  - 依赖：无
  - 文件：`lib/core/__init__.py`
  - 复杂度：低
  - 状态：✅ 已完成（2026-06-21）

#### 任务 1-2：创建 db 目录结构
- [x] SUB-TASK-002: 创建 `lib/db/` 目录结构
  - 依赖：无
  - 文件：`lib/db/`（目录创建）
  - 复杂度：低
  - 状态：✅ 已完成（2026-06-21）

---

### 任务组 2：数据库抽象层实现
**类型：** 串行
**前置条件：** 任务组 1 完成（SUB-TASK-001）
**阶段：** 阶段 1

#### 任务 2-1：实现 DatabaseManager 抽象基类
- [x] SUB-TASK-003: 实现 `DatabaseManager` 抽象基类
  - 依赖：SUB-TASK-001
  - 文件：`lib/core/db_manager.py`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-21）

#### 任务 2-2：实现 SQLiteManager
- [x] SUB-TASK-004: 实现 `SQLiteManager`（封装现有文件操作）
  - 依赖：SUB-TASK-003
  - 文件：`lib/core/sqlite_manager.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 2-3：实现 PostgreSQLManager
- [x] SUB-TASK-005: 实现 `PostgreSQLManager`（asyncpg 连接池）
  - 依赖：SUB-TASK-003
  - 文件：`lib/core/postgres_manager.py`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-21）

#### 任务 2-4：实现配置切换机制
- [x] SUB-TASK-006: 实现配置切换机制（`storage.type = sqlite | postgres`）
  - 依赖：SUB-TASK-003, SUB-TASK-004, SUB-TASK-005
  - 文件：`lib/core/config.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

---

### 任务组 3：PostgreSQL Schema 定义
**类型：** 串行
**前置条件：** 任务组 1 完成（SUB-TASK-002）
**阶段：** 阶段 2

#### 任务 3-1：创建核心表 Schema
- [x] SUB-TASK-007: 创建核心表 Schema（knowledge_bases, atoms, users, kb_members）
  - 依赖：SUB-TASK-002
  - 文件：`lib/db/schema.sql`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-21）

#### 任务 3-2：创建审计日志表
- [x] SUB-TASK-008: 创建审计日志表（audit_logs，带分区策略）
  - 依赖：SUB-TASK-007
  - 文件：`lib/db/schema.sql`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 3-3：创建版本快照表
- [x] SUB-TASK-009: 创建版本快照表（snapshots）
  - 依赖：SUB-TASK-007
  - 文件：`lib/db/schema.sql`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 3-4：创建全文索引定义
- [x] SUB-TASK-010: 创建全文索引定义（tsvector）
  - 依赖：SUB-TASK-007
  - 文件：`lib/db/indexes.sql`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 3-5：创建向量索引定义
- [x] SUB-TASK-011: 创建向量索引定义（pgvector ivfflat）
  - 依赖：SUB-TASK-007
  - 文件：`lib/db/indexes.sql`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 3-6：创建 RLS 策略函数
- [x] SUB-TASK-012: 创建 RLS 策略函数（set_current_user_id, current_user_id）
  - 依赖：SUB-TASK-007
  - 文件：`lib/db/functions.sql`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 3-7：创建 RLS 策略定义
- [x] SUB-TASK-013: 创建 RLS 策略定义
  - 依赖：SUB-TASK-012
  - 文件：`lib/db/rls.sql`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-21）

---

### 任务组 4：单元测试编写（抽象层）
**类型：** 并行
**前置条件：** 任务组 2 完成
**阶段：** 阶段 1

#### 任务 4-1：编写 DatabaseManager 单元测试
- [x] SUB-TASK-014: 编写 `DatabaseManager` 单元测试
  - 依赖：SUB-TASK-006
  - 文件：`tests/core/test_db_manager.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 4-2：编写 SQLiteManager 单元测试
- [x] SUB-TASK-015: 编写 `SQLiteManager` 单元测试
  - 依赖：SUB-TASK-006
  - 文件：`tests/core/test_sqlite_manager.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 4-3：编写 PostgreSQLManager 单元测试
- [x] SUB-TASK-016: 编写 `PostgreSQLManager` 单元测试
  - 依赖：SUB-TASK-006
  - 文件：`tests/core/test_postgres_manager.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

---

### 任务组 5：迁移工具目录初始化
**类型：** 串行
**前置条件：** 任务组 2 完成 + 任务组 3 完成
**阶段：** 阶段 3

#### 任务 5-1：创建 migration 目录结构
- [x] SUB-TASK-017: 创建 `lib/migration/` 目录结构
  - 依赖：SUB-TASK-006, SUB-TASK-013
  - 文件：`lib/migration/__init__.py`
  - 复杂度：低
  - 状态：✅ 已完成（2026-06-21）

#### 任务 5-2：实现知识库元数据迁移
- [x] SUB-TASK-018: 实现知识库元数据迁移（registry.json → knowledge_bases）
  - 依赖：SUB-TASK-017
  - 文件：`lib/migration/migrate.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 5-3：实现原子数据迁移
- [x] SUB-TASK-019: 实现原子数据迁移（Markdown → atoms 表）
  - 依赖：SUB-TASK-018
  - 文件：`lib/migration/migrate.py`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-21）

#### 任务 5-4：实现链接关系迁移
- [x] SUB-TASK-020: 实现链接关系迁移（wikilinks → atom_links）
  - 依赖：SUB-TASK-019
  - 文件：`lib/migration/migrate.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 5-5：实现向量嵌入迁移
- [x] SUB-TASK-021: 实现向量嵌入迁移（Chromadb → pgvector）
  - 依赖：SUB-TASK-019
  - 文件：`lib/migration/migrate.py`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-21）

#### 任务 5-6：实现全文索引构建
- [x] SUB-TASK-022: 实现全文索引构建（tsvector）
  - 依赖：SUB-TASK-019
  - 文件：`lib/migration/migrate.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 5-7：实现数据验证器
- [x] SUB-TASK-023: 实现数据验证器（记录数对比、内容一致性）
  - 依赖：SUB-TASK-018, SUB-TASK-019, SUB-TASK-020, SUB-TASK-021
  - 文件：`lib/migration/validators.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 5-8：实现 CLI 命令
- [x] SUB-TASK-024: 实现 CLI 命令（`llm-wiki migrate <kb> --to postgres`）
  - 依赖：SUB-TASK-023
  - 文件：`lib/migration/cli.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

---

### 任务组 6：搜索引擎目录初始化
**类型：** 串行
**前置条件：** 任务组 3 完成
**阶段：** 阶段 4

#### 任务 6-1：创建 search 目录结构
- [x] SUB-TASK-025: 创建 `lib/search/` 目录结构
  - 依赖：SUB-TASK-013
  - 文件：`lib/search/__init__.py`
  - 复杂度：低
  - 状态：✅ 已完成（2026-06-21）

#### 任务 6-2：实现 SearchEngine 抽象基类
- [x] SUB-TASK-026: 实现 `SearchEngine` 抽象基类
  - 依赖：SUB-TASK-025
  - 文件：`lib/search/engine.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

#### 任务 6-3：实现 PostgreSQL 全文检索
- [x] SUB-TASK-027: 实现 PostgreSQL 全文检索（tsvector + tsquery）
  - 依赖：SUB-TASK-026
  - 文件：`lib/search/postgres_search.py`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-21）

#### 任务 6-4：实现 PostgreSQL 向量检索
- [x] SUB-TASK-028: 实现 PostgreSQL 向量检索（pgvector 余弦相似度）
  - 依赖：SUB-TASK-026
  - 文件：`lib/search/postgres_search.py`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-21）

#### 任务 6-5：实现混合检索
- [x] SUB-TASK-029: 实现混合检索（全文 + 向量 + 重排序）
  - 依赖：SUB-TASK-027, SUB-TASK-028
  - 文件：`lib/search/hybrid_search.py`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-21）

#### 任务 6-6：实现搜索结果高亮
- [x] SUB-TASK-030: 实现搜索结果高亮（PostgreSQL `ts_headline`）
  - 依赖：SUB-TASK-027
  - 文件：`lib/search/postgres_search.py`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-21）

---

### 任务组 7：端到端迁移测试
**类型：** 串行
**前置条件：** 任务组 5 完成 + 任务组 6 完成
**阶段：** 阶段 5

#### 任务 7-1：编写端到端迁移测试
- [x] SUB-TASK-031: 编写端到端迁移测试
  - 依赖：SUB-TASK-024, SUB-TASK-029
  - 文件：`tests/e2e/test_migration.py`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-21）

---

### 任务组 8：CLI 验证
**类型：** 串行
**前置条件：** 任务组 5 完成
**阶段：** 阶段 5

#### 任务 8-1：验证 CLI 命令
- [x] SUB-TASK-032: 验证所有 CLI 命令在 PostgreSQL 模式下正常工作
  - 依赖：SUB-TASK-024
  - 文件：无（验证任务）
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-22）

---

### 任务组 9：Web UI 验证
**类型：** 串行
**前置条件：** 任务组 6 完成
**阶段：** 阶段 5

#### 任务 9-1：验证 Web UI
- [x] SUB-TASK-033: 验证 Web UI 在 PostgreSQL 模式下正常工作
  - 依赖：SUB-TASK-029
  - 文件：无（验证任务）
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-22）

---

### 任务组 10：性能基准测试
**类型：** 串行
**前置条件：** 任务组 8 完成 + 任务组 9 完成
**阶段：** 阶段 5

#### 任务 10-1：性能基准测试
- [x] SUB-TASK-034: 性能基准测试（查询延迟、写入吞吐）
  - 依赖：SUB-TASK-032, SUB-TASK-033
  - 文件：`tests/benchmarks/`
  - 复杂度：高
  - 状态：✅ 已完成（2026-06-22），4 个 benchmark 全部通过

---

### 任务组 11：迁移文档编写
**类型：** 串行
**前置条件：** 任务组 5 完成
**阶段：** 阶段 5

#### 任务 11-1：编写迁移文档
- [x] SUB-TASK-035: 编写迁移文档（`Doc/MIGRATION.md`）
  - 依赖：SUB-TASK-024
  - 文件：`Doc/MIGRATION.md`
  - 复杂度：中
  - 状态：✅ 已完成（2026-06-22），更新至 v1.1

---

### 任务组 12：项目进度更新
**类型：** 串行
**前置条件：** 所有任务组完成
**阶段：** 阶段 5

#### 任务 12-1：更新项目进度
- [x] SUB-TASK-036: 更新 `.claude/project.md` 进度
  - 依赖：SUB-TASK-031, SUB-TASK-034, SUB-TASK-035
  - 文件：`.claude/project.md`
  - 复杂度：低
  - 状态：✅ 已完成（2026-06-22）

---

## 执行顺序可视化

```
执行顺序：

1️⃣ 任务组 1：核心目录初始化（并行）
   ├─ 任务 1-1：创建 core 目录结构
   └─ 任务 1-2：创建 db 目录结构
       ↓
2️⃣ 任务组 2：数据库抽象层实现（串行）         3️⃣ 任务组 3：PostgreSQL Schema 定义（串行）
   ├─ 任务 2-1：DatabaseManager 抽象基类          ├─ 任务 3-1：核心表 Schema
   ├─ 任务 2-2：SQLiteManager                     ├─ 任务 3-2：审计日志表
   ├─ 任务 2-3：PostgreSQLManager                 ├─ 任务 3-3：版本快照表
   └─ 任务 2-4：配置切换机制                      ├─ 任务 3-4：全文索引定义
       ↓                                          ├─ 任务 3-5：向量索引定义
4️⃣ 任务组 4：单元测试编写（并行）               ├─ 任务 3-6：RLS 策略函数
   ├─ 任务 4-1：DatabaseManager 测试              └─ 任务 3-7：RLS 策略定义
   ├─ 任务 4-2：SQLiteManager 测试                    ↓
   └─ 任务 4-3：PostgreSQLManager 测试            6️⃣ 任务组 6：搜索引擎目录初始化（串行）
       ↓                                          ├─ 任务 6-1：创建 search 目录
5️⃣ 任务组 5：迁移工具目录初始化（串行）          ├─ 任务 6-2：SearchEngine 抽象基类
   ├─ 任务 5-1：创建 migration 目录               ├─ 任务 6-3：PostgreSQL 全文检索
   ├─ 任务 5-2：知识库元数据迁移                  ├─ 任务 6-4：PostgreSQL 向量检索
   ├─ 任务 5-3：原子数据迁移                      ├─ 任务 6-5：混合检索
   ├─ 任务 5-4：链接关系迁移                      └─ 任务 6-6：搜索结果高亮
   ├─ 任务 5-5：向量嵌入迁移                          ↓
   ├─ 任务 5-6：全文索引构建                      9️⃣ 任务组 9：Web UI 验证（串行）
   ├─ 任务 5-7：数据验证器                        └─ 任务 9-1：验证 Web UI
   └─ 任务 5-8：CLI 命令                              ↓
       ↓                                      🔟 任务组 10：性能基准测试（串行）
7️⃣ 任务组 7：端到端迁移测试（串行）             └─ 任务 10-1：性能基准测试
   └─ 任务 7-1：端到端迁移测试                       ↓
       ↓                                      1️⃣1️⃣ 任务组 12：项目进度更新（串行）
8️⃣ 任务组 8：CLI 验证（串行）                   └─ 任务 12-1：更新项目进度
   └─ 任务 8-1：验证 CLI 命令
       ↓
1️⃣1️⃣ 任务组 11：迁移文档编写（串行）
   └─ 任务 11-1：编写迁移文档

关键路径：
任务组 1 → 任务组 2 → 任务组 4 → 任务组 5 → 任务组 7 → 任务组 10 → 任务组 12
          ↘ 任务组 3 → 任务组 6 → 任务组 9 ↗
                      ↘ 任务组 8 ↗
```

---

## 并行执行建议

### 最高优先级并行（阶段 1 和 阶段 2 同时启动）

| 任务组 | 任务内容 | 执行者建议 |
|--------|----------|------------|
| 任务组 1-1 | 创建 `lib/core/` 目录 | Agent A |
| 任务组 1-2 | 创建 `lib/db/` 目录 | Agent B |

完成后：

| 任务组 | 任务内容 | 执行者建议 |
|--------|----------|------------|
| 任务组 2 | 数据库抽象层实现 | Agent A（串行） |
| 任务组 3 | PostgreSQL Schema 定义 | Agent B（串行） |

### 次级并行（任务组 4 内部）

| 任务组 | 任务内容 | 执行者建议 |
|--------|----------|------------|
| 任务组 4-1 | DatabaseManager 单元测试 | Agent A |
| 任务组 4-2 | SQLiteManager 单元测试 | Agent B |
| 任务组 4-3 | PostgreSQLManager 单元测试 | Agent C |

### 第三级并行（阶段 3 和 阶段 4）

当任务组 2 和任务组 3 都完成后，可并行启动：

| 任务组 | 任务内容 | 执行者建议 |
|--------|----------|------------|
| 任务组 5 | 迁移工具目录初始化 | Agent A（串行） |
| 任务组 6 | 搜索引擎目录初始化 | Agent B（串行） |

### 最后阶段并行（阶段 5）

| 任务组 | 任务内容 | 前置条件 | 执行者建议 |
|--------|----------|----------|------------|
| 任务组 7 | 端到端迁移测试 | 任务组 5 + 6 | Agent A |
| 任务组 8 | CLI 验证 | 任务组 5 | Agent B |
| 任务组 9 | Web UI 验证 | 任务组 6 | Agent C |
| 任务组 11 | 迁移文档编写 | 任务组 5 | Agent D |

---

## 资源冲突分析

| 资源 | 涉及任务组 | 冲突风险 | 建议 |
|------|------------|----------|------|
| `lib/core/` | 任务组 1, 2 | 低 | 同一 Agent 执行 |
| `lib/db/` | 任务组 1, 3 | 低 | 同一 Agent 执行 |
| `lib/migration/` | 任务组 5 | 独占 | 无冲突 |
| `lib/search/` | 任务组 6 | 独占 | 无冲突 |
| `tests/` | 任务组 4, 7 | 低 | 不同子目录 |
| PostgreSQL 连接 | 任务组 3, 5, 6, 7 | 中 | 使用独立测试数据库 |

---

## 关键里程碑

| 里程碑 | 完成标志 | 预计时间 |
|--------|----------|----------|
| M1：基础设施就绪 | 任务组 1-4 完成 | 第 2 周末 |
| M2：Schema 定义完成 | 任务组 3 完成 | 第 1 周末 |
| M3：迁移工具可用 | 任务组 5 完成 | 第 4 周末 |
| M4：搜索功能可用 | 任务组 6 完成 | 第 4 周末 |
| M5：迁移完成 | 所有任务组完成 | 第 6 周末 |

---

## 任务组依赖矩阵

```
              TG1 TG2 TG3 TG4 TG5 TG6 TG7 TG8 TG9 TG10 TG11 TG12
TG1 (目录)     -   x   x   -   -   -   -   -   -   -    -    -
TG2 (抽象层)   -   -   -   x   x   -   -   -   -   -    -    -
TG3 (Schema)   -   -   -   -   x   x   -   -   -   -    -    -
TG4 (测试)     -   -   -   -   x   -   -   -   -   -    -    -
TG5 (迁移)     -   -   -   -   -   -   x   x   -   -    x    -
TG6 (搜索)     -   -   -   -   -   -   x   -   x   -    -    -
TG7 (E2E测试)  -   -   -   -   -   -   -   -   -   x    -    x
TG8 (CLI验证)  -   -   -   -   -   -   -   -   -   x    -    -
TG9 (Web验证)  -   -   -   -   -   -   -   -   -   x    -    -
TG10 (性能)    -   -   -   -   -   -   -   -   -   -    -    x
TG11 (文档)    -   -   -   -   -   -   -   -   -   -    -    x
TG12 (更新)    -   -   -   -   -   -   -   -   -   -    -    -

x = 依赖关系
TG = Task Group（任务组）
```

---

**创建时间**：2026-06-21
**最后更新**：2026-06-22（全部 36/36 任务完成）
