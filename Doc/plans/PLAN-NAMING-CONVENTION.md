# 计划编号规范

> **版本**: 1.0
> **创建时间**: 2026-06-22

---

## 📋 编号规则

### PLAN-XXX 格式

| 编号 | 说明 | 示例 |
|------|------|------|
| PLAN-000 | 项目总方案 | PLAN-000-enterprise-overall-plan.md |
| PLAN-001-099 | 阶段1（核心基础） | PLAN-001-postgresql-migration.md |
| PLAN-100-199 | 阶段2（企业功能） | PLAN-101-sso-integration.md（待创建） |
| PLAN-200-299 | 阶段3（用户体验） | PLAN-003-phase3-ux-enhancement.md |
| PLAN-300+ | 扩展阶段 | 预留 |

### 后缀规范

| 后缀 | 说明 | 示例 |
|------|------|------|
| `-segments.md` | 任务拆分详情 | PLAN-001-postgresql-migration-segments.md |
| `-report-YYYY-MM-DD.md` | 执行报告 | PLAN-002-execution-report-2026-06-22.md |

---

## 📊 当前计划清单

### 项目总方案

| 编号 | 文件 | 说明 | 状态 |
|------|------|------|------|
| PLAN-000 | PLAN-000-enterprise-overall-plan.md | 项目总方案 | 🔄 进行中 |

### 阶段1：核心基础（PLAN-001-099）

| 编号 | 文件 | 说明 | 状态 |
|------|------|------|------|
| PLAN-001 | PLAN-001-postgresql-migration.md | PostgreSQL迁移 | ✅ 完成 |
| PLAN-001-segments | PLAN-001-postgresql-migration-segments.md | 任务拆分 | ✅ 完成 |
| PLAN-002 | PLAN-002-双模式架构与多级知识库.md | 双模式架构 | ✅ 完成 |
| PLAN-002-segments | PLAN-002-双模式架构与多级知识库-segments.md | 任务拆分 | ✅ 完成 |

### 阶段2：企业功能（PLAN-100-199）

| 编号 | 文件 | 说明 | 状态 |
|------|------|------|------|
| PLAN-101 | 待创建 | SSO集成 | ⏳ 待开始 |
| PLAN-102 | 待创建 | 版本管理 | ⏳ 待开始 |
| PLAN-103 | 待创建 | 审计日志 | ⏳ 待开始 |
| PLAN-104 | 待创建 | 数据加密 | ⏳ 待开始 |
| PLAN-105 | 待创建 | 容器化部署 | ⏳ 待开始 |

### 阶段3：用户体验（PLAN-200-299）

| 编号 | 文件 | 说明 | 状态 |
|------|------|------|------|
| PLAN-003 | PLAN-003-phase3-ux-enhancement.md | 用户体验增强 | 📝 草稿 |

> **注意**: PLAN-003 包含阶段3所有内容（图像、搜索、OCR、预览、移动端），编号从003开始。

---

## 🔄 状态流转

```
draft → active → completed
                → archived
```

| 状态 | 图标 | 说明 |
|------|:----:|------|
| draft | 📝 | 草稿，等待审批 |
| active | 🔄 | 进行中 |
| completed | ✅ | 已完成 |
| archived | 📦 | 已归档 |

---

## 📁 文件命名示例

```
✅ 正确示例：
  PLAN-000-enterprise-overall-plan.md
  PLAN-001-postgresql-migration.md
  PLAN-001-postgresql-migration-segments.md
  PLAN-002-execution-report-2026-06-22.md

❌ 错误示例：
  enterprise-overall-plan.md（缺少PLAN编号）
  plan-001-xxx.md（大小写错误）
  PLAN-1-xxx.md（编号不足3位）
```

---

## 🎯 使用规范

### 创建新计划

1. **确定阶段编号**：
   - 阶段1 → PLAN-001-099
   - 阶段2 → PLAN-100-199
   - 阶段3 → PLAN-200-299

2. **命名格式**：
   ```
   PLAN-{编号}-{简短描述}.md
   ```

3. **必须包含**：
   - YAML frontmatter（name, description, status, created, updated）
   - 明确的目标
   - 任务分解
   - 验收标准

### 更新索引

创建或重命名计划文件后，必须更新：
- `Doc/plans/README.md` - 计划索引
- `PLAN-000-enterprise-overall-plan.md` - 项目总方案进度表

---

**最后更新**: 2026-06-22
