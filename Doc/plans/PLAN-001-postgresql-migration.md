---
name: PLAN-001-postgresql-migration
description: 阶段 1.1 PostgreSQL 迁移详细计划
status: segmented
created: 2026-06-21
updated: 2026-06-21
phase: 阶段 3（开发）
depends_on: []
segments: PLAN-001-postgresql-migration-segments.md
---

# 实施计划：阶段 1.1 PostgreSQL 迁移

## 目标

将 llm-wiki 从当前的文件存储模式（JSON 注册表 + Markdown 文件 + FTS5 全文检索 + Chromadb 向量检索）迁移到 PostgreSQL 统一存储，同时保留 file_mode 的 Skill 特性兼容。

**核心目标**：
1. 创建数据库连接层抽象（DatabaseManager）
2. 实现 PostgreSQL Schema（知识库、原子、用户、权限、审计日志）
3. 实现数据迁移工具（SQLite/文件 → PostgreSQL）
4. 实现全文检索（pg tsvector）和向量检索替代方案
5. 确保向后兼容（file_mode 不受影响）

---

## 任务分解

### 第 1 阶段：数据库连接层抽象（2 周）

**目标**：创建存储抽象层，支持 SQLite 和 PostgreSQL 双模式

#### 串行任务

- [ ] TASK-001: 创建 `lib/core/` 目录结构
- [ ] TASK-002: 实现 `DatabaseManager` 抽象基类
- [ ] TASK-003: 实现 `SQLiteManager`（封装现有文件操作）
- [ ] TASK-004: 实现 `PostgreSQLManager`（asyncpg 连接池）
- [ ] TASK-005: 实现配置切换机制（`storage.type = sqlite | postgres`）

#### 并行任务（TASK-005 完成后）

- [ ] TASK-006: 编写 `DatabaseManager` 单元测试
- [ ] TASK-007: 编写 `SQLiteManager` 单元测试
- [ ] TASK-008: 编写 `PostgreSQLManager` 单元测试

**产出物**：
```
lib/core/
├── __init__.py
├── db_manager.py         # DatabaseManager 抽象基类
├── sqlite_manager.py     # SQLite 实现
├── postgres_manager.py   # PostgreSQL 实现
└── config.py             # 存储配置
```

---

### 第 2 阶段：PostgreSQL Schema 设计（1 周）

**目标**：设计并创建 PostgreSQL 表结构

#### 串行任务

- [ ] TASK-009: 创建 `lib/db/` 目录结构
- [ ] TASK-010: 创建核心表 Schema（knowledge_bases, atoms, users, kb_members）
- [ ] TASK-011: 创建审计日志表（audit_logs，带分区策略）
- [ ] TASK-012: 创建版本快照表（snapshots）
- [ ] TASK-013: 创建全文索引定义（tsvector）
- [ ] TASK-014: 创建向量索引定义（pgvector ivfflat）
- [ ] TASK-015: 创建 RLS 策略函数（set_current_user_id, current_user_id）
- [ ] TASK-016: 创建 RLS 策略定义

**产出物**：
```
lib/db/
├── schema.sql            # 表结构定义
├── rls.sql               # RLS 策略
├── indexes.sql           # 索引定义
└── functions.sql         # 存储过程和函数
```

---

### 第 3 阶段：数据迁移工具（2 周）

**目标**：实现文件数据到 PostgreSQL 的迁移

#### 串行任务

- [ ] TASK-017: 创建 `lib/migration/` 目录结构
- [ ] TASK-018: 实现知识库元数据迁移（registry.json → knowledge_bases）
- [ ] TASK-019: 实现原子数据迁移（Markdown → atoms 表）
- [ ] TASK-020: 实现链接关系迁移（wikilinks → atom_links）
- [ ] TASK-021: 实现向量嵌入迁移（Chromadb → pgvector）
- [ ] TASK-022: 实现全文索引构建（tsvector）
- [ ] TASK-023: 实现数据验证器（记录数对比、内容一致性）
- [ ] TASK-024: 实现 CLI 命令（`llm-wiki migrate <kb> --to postgres`）

**产出物**：
```
lib/migration/
├── __init__.py
├── migrate.py            # 迁移主逻辑
├── validators.py         # 数据验证
└── cli.py                # CLI 命令
```

---

### 第 4 阶段：搜索引擎适配（1.5 周）

**目标**：适配现有搜索接口到 PostgreSQL

#### 串行任务

- [ ] TASK-025: 创建 `lib/search/` 目录结构
- [ ] TASK-026: 实现 `SearchEngine` 抽象基类
- [ ] TASK-027: 实现 PostgreSQL 全文检索（tsvector + tsquery）
- [ ] TASK-028: 实现 PostgreSQL 向量检索（pgvector 余弦相似度）
- [ ] TASK-029: 实现混合检索（全文 + 向量 + 重排序）
- [ ] TASK-030: 实现搜索结果高亮（PostgreSQL `ts_headline`）

**产出物**：
```
lib/search/
├── __init__.py
├── engine.py             # 搜索引擎抽象
├── postgres_search.py    # PostgreSQL 实现
└── hybrid_search.py      # 混合检索
```

---

### 第 5 阶段：集成测试与验证（1 周）

**目标**：验证迁移完整性和功能正确性

#### 串行任务

- [ ] TASK-031: 编写端到端迁移测试
- [ ] TASK-032: 验证所有 CLI 命令在 PostgreSQL 模式下正常工作
- [ ] TASK-033: 验证 Web UI 在 PostgreSQL 模式下正常工作
- [ ] TASK-034: 性能基准测试（查询延迟、写入吞吐）
- [ ] TASK-035: 编写迁移文档（`Doc/MIGRATION.md`）
- [ ] TASK-036: 更新 `.claude/project.md` 进度

---

## 依赖关系

```
阶段 1（抽象层）
    ↓
阶段 2（Schema）← 可并行开始（无代码依赖）
    ↓
阶段 3（迁移工具）← 依赖阶段 1 + 2
    ↓
阶段 4（搜索适配）← 依赖阶段 2
    ↓
阶段 5（集成测试）← 依赖阶段 3 + 4
```

**并行机会**：
- 阶段 1 和阶段 2 可并行进行（Schema 设计与代码抽象无依赖）
- 阶段 3 和阶段 4 部分任务可并行（迁移工具与搜索适配独立）

---

## 风险评估

| 风险 | 等级 | 影响 | 缓解措施 |
|------|:----:|------|----------|
| 数据迁移丢失 | 高 | 知识库数据损坏 | 实现演练模式（`--dry-run`）、迁移前后校验、保留原文件 |
| 性能下降 | 中 | 用户体验变差 | 性能基准测试、索引优化、连接池配置 |
| 向量检索精度下降 | 中 | 搜索结果质量变差 | 对比测试 ivfflat vs Chromadb、调整 probes 参数 |
| RLS 策略错误 | 高 | 数据泄露 | 安全审查、集成测试覆盖权限边界 |
| 连接池配置不当 | 中 | 连接耗尽、性能问题 | 参考架构文档配置、压力测试 |

---

## 预估复杂度

**等级**：高（HIGH）

| 阶段 | 工作量 | 说明 |
|------|--------|------|
| 阶段 1 | 40-60 小时 | 抽象层设计 + 双实现 |
| 阶段 2 | 20-30 小时 | Schema 设计 + RLS |
| 阶段 3 | 50-70 小时 | 迁移工具 + CLI |
| 阶段 4 | 30-40 小时 | 搜索适配 |
| 阶段 5 | 20-30 小时 | 测试 + 文档 |
| **总计** | **160-230 小时** | 约 4-6 周（1 人） |

---

## 技术决策

| 决策项 | 选定方案 | 理由 |
|--------|----------|------|
| 连接池 | asyncpg | 高性能异步、原生支持 PostgreSQL |
| 向量索引 | ivfflat | 适合 <1M 规模、构建快、内存低 |
| 全文索引 | tsvector | PostgreSQL 原生、无外部依赖 |
| 迁移策略 | 增量迁移 | 支持演练、可回滚、保留原文件 |
| 配置管理 | 环境变量 + YAML | 12-factor app、灵活配置 |

---

## 发现与记录

> 在实施过程中记录重要发现、技术决策变更、问题解决方案。

_（待实施时填充）_

---

## 完成总结

> 任务全部完成后填写。

- **实际耗时**：_待完成_
- **遇到的问题**：_待完成_
- **经验总结**：_待完成_
- **下一步建议**：_待完成_

---

**计划创建时间**：2026-06-21
**最后更新时间**：2026-06-21
