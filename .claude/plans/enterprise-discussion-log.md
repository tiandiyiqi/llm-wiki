# llm-wiki 企业化改造讨论记录

> 讨论开始时间：2026-06-21
> 基准文档：企业知识库评分与差距分析报告.md
> 当前评分：60.25/100

---

## 讨论顺序（按优先级）

### P0 级差距（阻塞性，必须解决）
| 序号 | 差距项 | 状态 |
|:---:|--------|:----:|
| 1 | 高可用架构 | ✅ 已讨论 |
| 2 | SSO 集成 | ✅ 已讨论 |
| 3 | 实时协同编辑 | ⏬ 降级 P2 |
| 4 | 版本管理系统 | ✅ 已讨论 |
| 5 | 容器化部署 | ✅ 已讨论 |

### P1 级差距（影响竞争力）
| 序号 | 差距项 | 状态 |
|:---:|--------|:----:|
| 6 | 搜索高亮和联想 | ✅ 已讨论 |
| 7 | OCR 扫描件识别 | ✅ 已讨论 |
| 8 | 在线预览 | ✅ 已讨论 |
| 9 | 移动端优化 | ✅ 已讨论 |

### P2 级差距（特定行业必需）
| 序号 | 差距项 | 状态 |
|:---:|--------|:----:|
| 10 | 等保三级/密评 | ⏸️ 暂缓 |
| 11 | 审计日志不可篡改 | ✅ 已讨论 |
| 12 | 数据加密存储 | ✅ 已讨论 |
| 13 | 实时协同编辑 | ❌ 不执行 |

---

## 补充讨论：内容存储方式

### 讨论时间
2026-06-21

### 问题背景
```
当前状态：
  ├─ Markdown 文件存储在文件系统
  ├─ SQLite 索引数据
  └─ 不支持多用户协作、权限控制
```

### 结论
**PostgreSQL 存储 + Markdown 导出（混合方案）**

### 存储方案
```
主存储：PostgreSQL
  ├─ atoms 表：文档内容
  ├─ atom_versions 表：版本历史
  ├─ atom_assets 表：图像资源
  └─ metadata JSONB：frontmatter 属性

保留导出能力：
  ├─ export 命令：导出为 Markdown
  ├─ import 命令：从 Markdown 导入
  └─ Git 友好：可导出到 Git 仓库
```

### 存储方案对比
| 维度 | 文件存储（当前） | 数据库存储 |
|------|:----------------:|:----------:|
| 多用户协作 | ❌ | ✅ |
| 权限控制 | ❌ | ✅ |
| 版本管理 | ⚠️ | ✅ |
| Git 友好 | ✅ | ⚠️ 需导出 |

---

## 补充讨论：多级 Wiki 管理

### 讨论时间
2026-06-21

### 问题背景
```
需求场景：
  ├─ 个人知识库：员工私有，不公开
  ├─ 部门知识库：部门成员可见
  ├─ 项目知识库：项目成员可见（临时）
  └─ 公司知识库：聚合多个子知识库
```

### 结论
**多级知识库架构**

### 数据模型
```
组织
  └─ 知识库（knowledge_bases）
      ├─ type: personal/department/project/company
      ├─ visibility: private/team/public
      └─ is_aggregated: 是否为聚合知识库
```

### 表结构设计
```sql
-- 知识库表
CREATE TABLE knowledge_bases (
  id SERIAL PRIMARY KEY,
  name VARCHAR(256),
  type VARCHAR(32),  -- personal/department/project/company
  organization_id VARCHAR(64),
  owner_id VARCHAR(64),
  department_id VARCHAR(64),
  project_id VARCHAR(64),
  visibility VARCHAR(32) DEFAULT 'private',
  is_aggregated BOOLEAN DEFAULT false
);

-- 知识库成员表
CREATE TABLE kb_members (
  kb_id INTEGER REFERENCES knowledge_bases(id),
  user_id VARCHAR(64) REFERENCES users(id),
  role VARCHAR(32),  -- owner/editor/reader
  PRIMARY KEY (kb_id, user_id)
);

-- 聚合配置（公司知识库包含哪些子知识库）
CREATE TABLE kb_aggregations (
  parent_kb_id INTEGER REFERENCES knowledge_bases(id),
  child_kb_id INTEGER REFERENCES knowledge_bases(id),
  include_private BOOLEAN DEFAULT false,
  PRIMARY KEY (parent_kb_id, child_kb_id)
);
```

### 权限模型
```
知识库类型与默认权限：
  ├─ 个人知识库：仅自己可见，可分享
  ├─ 部门知识库：部门成员可见
  ├─ 项目知识库：项目成员可见
  └─ 公司知识库：聚合子知识库的公开内容
```

---

## 补充讨论：双模式架构与 Skill 保留

### 讨论时间
2026-06-21

### 问题背景
```
项目初衷（karpathy-llm-wiki.md + OKF-SPEC.md）：
  ├─ 文件即知识（Markdown 文件为主存储）
  ├─ Git 原生集成
  ├─ Obsidian 直接编辑
  ├─ Claude Code Skill 集成
  └─ 无外部依赖，单文件部署

担忧：
  ├─ 企业化改造后是否丢失项目初衷？
  └─ 是否还能作为 Skill 使用？
```

### 结论
**双模式架构，file_mode 完全保留 Skill 特性**

### 双模式设计

#### file_mode（Skill 模式）
```
定位：
  ├─ 个人知识库（karpathy 原设计）
  ├─ Claude Code Skill 集成
  └─ 开箱即用

特性保留：
  ├─ 文件即知识（atoms/ 目录）
  ├─ Git 原生集成
  ├─ Obsidian 直接编辑
  ├─ OKF v0.1 规范完全兼容
  ├─ 无外部依赖
  └─ 单文件部署

Skill 使用：
  ├─ ingest：导入来源 → 写 Markdown
  ├─ query：读 Markdown → 回答问题
  ├─ lint：检查文件 → 标记问题
  └─ export：打包 OKF bundle
```

#### db_mode（企业模式）
```
定位：
  ├─ 团队/企业知识库
  ├─ Web UI 使用
  └─ 多用户协作

特性：
  ├─ PostgreSQL 存储
  ├─ 多用户权限控制
  ├─ 版本管理
  └─ OKF bundle 导入导出（保持兼容）
```

#### 模式切换
```
切换路径：
  ├─ file_mode → db_mode：个人升级为团队
  ├─ db_mode → file_mode：导出 OKF bundle
  └─ 两种模式可互操作
```

### 特性保留对比
| 特性 | file_mode | db_mode | 保留 |
|------|:---------:|:-------:|:----:|
| 文件即知识 | ✅ | ⚠️ 导出 | ✅ |
| Git 原生集成 | ✅ | ⚠️ 导出后 | ✅ |
| Obsidian 直接编辑 | ✅ | ⚠️ 导出后 | ✅ |
| OKF v0.1 规范 | ✅ | ✅ | ✅ |
| Claude Code Skill | ✅ | ❌ | ✅ |
| 单文件部署 | ✅ | ❌ | ⚠️ |
| 无外部依赖 | ✅ | ❌ | ⚠️ |
| 多用户协作 | ❌ | ✅ | ✅ 新增 |

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| file_mode 保留 | 2-3万元 | 保持当前架构 |
| db_mode 实现 | 5-8万元 | PostgreSQL 存储 |
| 双模式切换 | 3-5万元 | API 统一 |
| OKF 导入导出 | 2-3万元 | 连接两种模式 |
| **合计** | **12-19万元** | 已计入多级 Wiki 管理 |

### 关键结论
```
1. Skill 模式完全保留
   ├─ file_mode 下 Claude 直接操作文件
   ├─ 无需数据库、API 层
   └─ 与原设计一致

2. 企业模式不影响个人用户
   ├─ 个人用户继续使用 file_mode
   ├─ 企业客户使用 db_mode
   └─ 两种用户群体互不干扰

3. 项目初衷不丢失
   ├─ karpathy-llm-wiki 理念保留（file_mode）
   ├─ OKF-SPEC 规范保留（两种模式）
   └─ Claude Code Skill 集成保留（file_mode）
```

---

## 补充讨论：Obsidian 兼容性

### 讨论时间
2026-06-21

### 问题背景
```
Obsidian 是个人知识管理工具：
  ├─ 基于 Markdown 文件
  ├─ 本地文件夹作为"库"（Vault）
  ├─ 支持双链 [[]]、图谱视图、插件
  └─ 与 karpathy-llm-wiki 设计理念一致
```

### 结论
**file_mode 完全兼容 Obsidian，db_mode 通过导出兼容**

### 兼容性分析

#### file_mode（完全兼容）
```
兼容项：
  ├─ 文件格式：Markdown (.md) ✅
  ├─ 存储方式：本地文件系统 ✅
  ├─ YAML frontmatter：OKF 规范兼容 ✅
  ├─ 标签：tags 字段支持 ✅
  ├─ 图谱视图：Obsidian 内置 ✅
  ├─ 插件生态：全部可用 ✅
  └─ 双链 [[]]：需适配器解析 ⚠️

使用方式：
  1. Obsidian 打开 atoms/ 目录
  2. 直接浏览、编辑知识点
  3. llm-wiki 读取更新
  4. Skill 写入新文件，Obsidian 实时可见
```

#### db_mode（导入导出兼容）
```
兼容项：
  ├─ 打开 Vault：需先导出 ⚠️
  ├─ 编辑 Markdown：导出后编辑 ✅
  ├─ 导入更新：需手动导入 ⚠️
  └─ 实时同步：可选自动同步 ⚠️

使用方式：
  1. 导出 OKF bundle
  2. Obsidian 打开导出目录
  3. 编辑后导入更新
```

### 技术适配

#### 双链语法适配
```python
# Obsidian 双链：[[文件名]] 或 [[文件名|显示名]]
# 标准链接：[显示名](/path/to/file.md)

class ObsidianAdapter:
    def wikilink_to_markdown(self, content):
        # [[微服务架构]] → [微服务架构](/atoms/microservices.md)
        pass
    
    def markdown_to_wikilink(self, content):
        # 反向转换
        pass
```

#### 自动同步（可选）
```python
class ObsidianSync:
    def export_to_obsidian(self):
        # PostgreSQL → 文件系统
        pass
    
    def import_from_obsidian(self):
        # 文件系统 → PostgreSQL
        pass
    
    def watch_and_sync(self):
        # 监听文件变化，自动同步
        pass
```

### 兼容性总结
| 模式 | 直接打开 | 实时编辑 | 双链支持 | 图谱视图 |
|------|:--------:|:--------:|:--------:|:--------:|
| file_mode | ✅ | ✅ | ⚠️ 需适配 | ✅ |
| db_mode | ⚠️ 导出 | ⚠️ 导出后 | ⚠️ 需适配 | ✅ |

---

## 最终决策汇总

### 存储架构
| 决策项 | 结论 |
|--------|------|
| 存储方式 | 双模式（file_mode + db_mode） |
| Skill 兼容 | ✅ file_mode 完全支持 |
| Obsidian 兼容 | ✅ file_mode 完全支持 |
| OKF 规范 | ✅ 两种模式都支持 |

### 投入汇总
| 类别 | 投入 |
|------|------|
| P0（基础架构） | 40-63万元 |
| P1（用户体验） | 14-23万元 |
| P2（合规安全） | 7-12万元 |
| 图像存储 | 7-11万元 |
| 多级 Wiki + 双模式 | 12-19万元 |
| **合计** | **73-109万元** |

### 暂缓项目
| 项目 | 预留投入 | 触发条件 |
|------|----------|----------|
| 等保三级/密评 | 30-125万元 | 政企/金融客户要求 |
| 实时协同编辑 | - | 不执行 |

---

## 下一步行动

### 阶段 1：基础设施（3-6个月）
```
优先级 P0：
  1. PostgreSQL 迁移（db_mode 基础）
  2. 双模式架构实现
  3. Casdoor SSO 集成
  4. 版本管理系统
  5. 审计日志改造
  6. 数据加密存储
  7. 容器化部署

保留 file_mode：
  8. 确保 atoms/ 目录结构不变
  9. 确保 Skill 正常工作
  10. 确保 Obsidian 可直接打开
```

### 阶段 2：多级知识库（2-3个月）
```
优先级 P0 补充：
  1. knowledge_bases 表设计
  2. 权限模型实现
  3. 知识库管理 UI
  4. OKF 导入导出
```

### 阶段 3：用户体验（2-3个月）
```
优先级 P1：
  1. 搜索优化
  2. OCR 能力
  3. 在线预览
  4. 移动端优化
  5. 图像存储
```

### 阶段 4：合规认证（按需）
```
优先级 P2：
  1. 等保三级（如有客户要求）
  2. 密评（如有客户要求）
```

### 立即行动项
```
1. 确认预算范围
2. 确定实施优先级
3. 设计 PostgreSQL 表结构
4. 设计双模式 API 接口
5. 开始阶段 1 技术方案细化
```

---

**讨论完成时间**：2026-06-21

---

## 执行计划

### 优先级确认结果

| 问题 | 确认结果 |
|------|----------|
| 阶段顺序 | ✅ 阶段 1→2→3 |
| 阶段 1 内部顺序 | ✅ PostgreSQL → 双模式 → 多级 Wiki |
| P1 启动时机 | ✅ 阶段 1 完成后 |
| 阶段 1 预算 | ✅ 30-48万元可接受 |

### 总体执行顺序

```
阶段 1：核心基础（3-4个月，30-48万元）
  ├─ 步骤 1：PostgreSQL 迁移（4-6周，18-29万元）
  │   ├─ 数据库连接层抽象
  │   ├─ 核心表结构设计
  │   └─ 数据迁移脚本
  │
  ├─ 步骤 2：双模式架构设计（2周）
  │   ├─ file_mode 保持现有功能
  │   ├─ db_mode 实现
  │   └─ API 统一接口
  │
  └─ 步骤 3：多级 Wiki 管理（4-6周，12-19万元）
      ├─ knowledge_bases 表
      ├─ 权限模型
      └─ 知识库管理 UI

阶段 2：企业功能（3-4个月，29-46万元）
  ├─ Casdoor SSO 集成（11-17万元）
  ├─ 版本管理系统（8-11万元）
  ├─ 审计日志不可篡改（3-5万元）
  ├─ 数据加密存储（4-7万元）
  └─ 容器化部署（3-6万元）

阶段 3：用户体验（2-3个月，21-34万元）
  ├─ 图像存储（7-11万元）
  ├─ 搜索高亮和联想（3-5万元）
  ├─ OCR 扫描件识别（4-7万元）
  ├─ 在线预览（4-6万元）
  └─ 移动端优化（3-5万元）

总投入：80-128万元
总周期：8-11个月
```

### 阶段依赖关系

```
PostgreSQL 迁移（基础）
  └─→ 双模式架构设计
        └─→ 多级 Wiki 管理
              └─→ 阶段 2 所有模块
                    └─→ 阶段 3 所有模块
```

### 关键里程碑

| 里程碑 | 时间 | 交付物 |
|--------|------|--------|
| M1 | 1.5个月 | PostgreSQL 迁移完成 |
| M2 | 2个月 | 双模式架构上线 |
| M3 | 4个月 | 多级 Wiki 管理上线 |
| M4 | 8个月 | 阶段 2 完成（企业功能） |
| M5 | 11个月 | 阶段 3 完成（全部上线） |

---

**下一步**：阶段 1 步骤 1（PostgreSQL 迁移）详细设计

---

## 讨论 1：数据库选型（高可用架构核心）

### 讨论时间
2026-06-21

### 问题背景
- 当前使用 SQLite 单机存储，存在单点故障
- 数据库选型不仅影响高可用性，还影响后续的用户管理、权限管理、数据隔离
- 需要选择一个能支撑企业级使用的数据库

### 讨论选项
对比了 PostgreSQL、MySQL、MongoDB、SQLite（当前）

### 结论
**选定 PostgreSQL 作为目标数据库**

### 核心理由

#### 1. 一库多能，减少技术栈复杂度
```
当前架构：
  ├─ SQLite（结构化数据）
  ├─ Chromadb（向量检索）
  └─ FTS5（全文检索）

PostgreSQL 一库搞定：
  ├─ 结构化数据（用户、权限、文档元数据）
  ├─ JSONB（灵活的文档属性、frontmatter）
  ├─ pgvector（向量检索，替代 Chromadb）
  └─ tsvector（全文检索，替代 FTS5）
```

**优势**：减少 2 个外部依赖（Chromadb、FTS5），降低部署复杂度

#### 2. 行级安全策略（Row-Level Security）— 权限管理的关键
```sql
-- 用户只能看到自己部门的文档
CREATE POLICY department_isolation ON atoms
  USING (department_id = current_user_department());

-- 文档级权限：编辑者只能修改自己的文档
CREATE POLICY editor_own_docs ON atoms
  FOR UPDATE USING (author_id = current_user_id());
```

**优势**：原生支持多租户隔离和细粒度权限，无需在应用层实现

#### 3. pgvector — 向量检索原生支持
```sql
-- 直接在 PostgreSQL 中完成向量检索
SELECT id, title, 1 - (embedding <=> :query_vector) as similarity
FROM atoms
WHERE 1 - (embedding <=> :query_vector) > 0.8
ORDER BY embedding <=> :query_vector
LIMIT 10;
```

**优势**：向量检索与结构化数据在同一数据库，避免跨库查询

#### 4. JSONB — 灵活的元数据存储
```sql
-- 存储 YAML frontmatter 的灵活属性
INSERT INTO atoms (title, content, metadata)
VALUES (
  'API 文档',
  '内容...',
  '{"tags": ["api", "v2"], "confidence": 0.95, "status": "published"}'::jsonb
);

-- 高效查询 JSON 字段（GIN 索引）
SELECT * FROM atoms WHERE metadata @> '{"tags": ["api"]}';
```

**优势**：保持当前 Markdown + frontmatter 的灵活性，无需改动数据模型

#### 5. 信创兼容 — 国产替代路径清晰
| 国产数据库 | 兼容性 | 说明 |
|------------|--------|------|
| 人大金仓 KingbaseES | 高 | PostgreSQL 内核，语法 95% 兼容 |
| 瀚高数据库 HighGo | 高 | 基于 PostgreSQL 二次开发 |
| 达梦 DM8 | 中 | 有 PostgreSQL 兼容模式 |

**优势**：后期信创适配只需更换数据库连接，代码改动极小

### 迁移路径
```
阶段 1：SQLite → PostgreSQL（基础迁移）
  ├─ 数据库连接层抽象（统一接口）
  ├─ 核心表结构迁移（atoms, tags, users）
  ├─ FTS5 → tsvector 全文索引
  └─ 周期：2-3周

阶段 2：集成 pgvector（向量检索）
  ├─ 安装 pgvector 扩展
  ├─ Chromadb 数据迁移
  ├─ 统一向量查询接口
  └─ 周期：1-2周

阶段 3：权限模型升级（行级安全）
  ├─ RLS 策略设计
  ├─ 多租户隔离
  ├─ 细粒度权限控制
  └─ 周期：2-3周

阶段 4：高可用部署（主从复制）
  ├─ 流复制配置
  ├─ 读写分离
  ├─ 自动故障转移
  └─ 周期：1-2周
```

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| PostgreSQL 基础迁移 | 5-8万元 | 数据库层重构 |
| pgvector 集成 | 3-5万元 | 向量检索统一 |
| 权限模型升级 | 5-8万元 | RLS + 多租户 |
| 高可用部署 | 5-8万元 | 主从 + 故障转移 |
| **合计** | **18-29万元** | 可分阶段投入 |

### 技术栈变化
```
改造前：
  Python + SQLite + FTS5 + Chromadb（可选）

改造后：
  Python + PostgreSQL + pgvector + tsvector
```

### 下一步行动
- 设计 PostgreSQL 表结构（atoms, users, permissions, audit_logs）
- 实现数据库连接抽象层（支持 SQLite/PostgreSQL 双模式过渡）
- 评估 pgvector 与当前 Chromadb 的兼容性

---

## 讨论 2：SSO 集成

### 讨论时间
2026-06-21

### 问题背景
- 当前使用自建 Token 认证（无标准协议）
- 无法对接企业统一身份体系（企业微信/钉钉/飞书/LDAP）
- 成为企业准入门槛
- 需支持多协议（SAML/OAuth/OIDC/LDAP）

### 用户约束
- 暂无统一身份平台
- 需要支持多协议
- 希望自建方案（数据自控）

### 讨论过程

#### 选项对比
| 方案 | 多协议支持 | 开发成本 | 运维成本 | 信创友好 | 推荐度 |
|------|:--------:|:--------:|:--------:|:--------:|:------:|
| Keycloak | ✅ 全覆盖 | 低 | 中 | ✅ 开源可控 | ⭐⭐⭐⭐⭐ |
| **Casdoor** | ✅ 全覆盖 | 低 | 低 | ✅ 国产开源 | ⭐⭐⭐⭐ |
| Dex | ⚠️ 仅 OIDC/OAuth | 低 | 低 | ✅ 云原生 | ⭐⭐⭐ |
| 自研 | 需逐一开发 | 高 | 低 | ✅ 完全可控 | ⭐⭐ |

#### 关键问题讨论

**Q1: Keycloak 是 Java 项目，是否与 Python 项目兼容？**

**A: 完全兼容。** SSO 架构是独立的：
```
用户浏览器
    ↓ 登录跳转
Keycloak（独立部署，Java）
    ↓ 返回 JWT Token
llm-wiki（Python）
    ↓ 验证 Token（纯 Python JWT 解码）
```

Keycloak 和 llm-wiki 通过 HTTP 协议通信，技术栈隔离。

**Q2: Keycloak 算是自建方案吗？**

**A: 是的。** Keycloak 属于"自建 + 开源"方案：
- 数据完全自控（符合信创要求）
- 一次部署，无持续付费
- 需承担部署运维成本

**Q3: 既然需要国产 + 信创，是否有更优方案？**

**A: 推荐 Casdoor（国产开源）。**

### 结论
**选定 Casdoor 作为 SSO 方案**

### 核心理由

#### 1. 国产 IM 内置支持
```
Casdoor 内置 Identity Provider：
  ├─ 企业微信（WeCom）
  ├─ 钉钉
  ├─ 飞书
  ├─ 微信/支付宝/微博
  └─ LDAP/AD 域控
```

**优势**：无需自行配置企业微信/钉钉/飞书集成，开箱即用

#### 2. Go 技术栈（运维简单）
```
Casdoor 技术特点：
  ├─ Go 语言（单二进制部署）
  ├─ 无 JVM 依赖（内存占用低）
  ├─ 容器镜像小（< 50MB）
  └─ 与 PostgreSQL 统一存储
```

**优势**：相比 Keycloak（Java），部署运维更简单

#### 3. 协议全覆盖
```
支持协议：
  ├─ OAuth 2.0
  ├─ OIDC（OpenID Connect）
  ├─ SAML 2.0
  ├─ CAS
  └─ LDAP/AD
```

**优势**：满足"支持多协议"需求

#### 4. Casbin 权限模型联动
```
Casdoor + Casbin：
  ├─ RBAC（基于角色）
  ├─ ABAC（基于属性）
  ├─ 与 PostgreSQL 联动
  └─ Python SDK（casbin-py）无缝集成
```

**优势**：与 PostgreSQL 权限模型设计一致，集成简单

#### 5. 国产 + 信创友好
```
信创优势：
  ├─ 国产开源（Casbin 团队，中国开发者）
  ├─ 完全可控（数据自托管）
  ├─ 中文文档/社区支持
  └─ 符合信创"自主可控"要求
```

### 集成架构
```
┌─────────────────────────────────────────┐
│           用户浏览器                      │
└─────────────────────────────────────────┘
              ↓ 点击登录
┌─────────────────────────────────────────┐
│  llm-wiki Web UI                         │
│  - 显示"企业微信/钉钉/飞书"登录按钮       │
└─────────────────────────────────────────┘
              ↓ 跳转认证
┌─────────────────────────────────────────┐
│  Casdoor（独立部署）                      │
│  - 处理 OAuth/OIDC/SAML/LDAP            │
│  - 用户账号管理                          │
│  - 生成 JWT Token                       │
│  - 存储：PostgreSQL（统一）              │
└─────────────────────────────────────────┘
              ↓ 返回 Token
┌─────────────────────────────────────────┐
│  llm-wiki（Python）                      │
│  - 验证 JWT Token                       │
│  - 获取用户信息/权限                     │
│  - Casbin 权限校验                       │
│  - 存储：PostgreSQL（统一）              │
└─────────────────────────────────────────┘
```

### 迁移路径
```
阶段 1：Casdoor 部署（1周）
  ├─ Docker 部署 Casdoor
  ├─ PostgreSQL 作为 Casdoor 存储
  ├─ 配置企业微信/钉钉/飞书 Provider
  └─ 创建 llm-wiki 应用（OIDC）

阶段 2：llm-wiki OIDC 集成（2周）
  ├─ 安装 authlib/pyjwt
  ├─ 实现登录跳转逻辑
  ├─ JWT Token 验证
  ├─ 用户信息获取

阶段 3：权限模型联动（2周）
  ├─ Casbin 权限策略设计
  ├─ PostgreSQL 权限表
  ├─ RBAC/ABAC 权限校验
  ├─ 与 Casdoor 用户角色同步

阶段 4：多协议支持（1周）
  ├─ SAML 2.0 配置（可选）
  ├─ LDAP/AD 集成（可选）
  └─ 多登录方式 UI
```

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| Casdoor 部署 | 3-5万元 | Docker + PostgreSQL 配置 |
| OIDC 集成 | 5-7万元 | Python 认证模块重构 |
| 权限模型联动 | 3-5万元 | Casbin + PostgreSQL |
| **合计** | **11-17万元** | 比自研节省 50% |

### 技术栈变化
```
改造前：
  Python + 自建 Token + IP 白名单

改造后：
  Python + Casdoor（OIDC）+ Casbin + PostgreSQL
```

### 下一步行动
- 部署 Casdoor（Docker + PostgreSQL）
- 配置企业微信/钉钉/飞书 Provider
- 设计 llm-wiki OIDC 集成方案
- 设计 Casbin 权限策略

---

## 讨论 3：实时协同编辑

### 讨论时间
2026-06-21

### 用户质疑
> "知识库实时协同编辑的必要性不大，同一个知识点要不同的人在同一时间编辑，我觉得是没有太大必要的。"

### 结论
**移除实时协同编辑功能，不作为 P0 差距项**

### 核心理由

#### 1. 知识库 ≠ 协作文档
```
知识库定位：
  ├─ 核心场景：知识沉淀、查询、复用
  ├─ 编辑频率：低频（知识稳定）
  ├─ 编辑人数：通常 1 人负责
  └─ 实时性需求：低（异步协作即可）

协作文档定位（Notion/飞书文档）：
  ├─ 核心场景：多人共创、实时讨论
  ├─ 编辑频率：高频（频繁修改）
  ├─ 编辑人数：多人同时编辑
  └─ 实时性需求：高（实时同步）
```

#### 2. 实际使用场景分析
```
典型知识库场景（异步协作）：
  ├─ 技术文档编写：开发者 A 编写 → 审核者 B 评论 → A 修改
  ├─ 知识条目创建：产品经理创建 → 开发者补充 → 测试补充
  ├─ 知识更新：所有者定期更新 → 其他人提交纠错建议

实时协同的真实场景（非知识库核心）：
  ├─ 会议纪要（多人同时记录）← 飞书/钉钉文档已解决
  ├─ 头脑风暴（多人贡献想法）← 同上
  └─ 这些场景有现成工具，无需知识库重复实现
```

#### 3. 原定级 P0 的偏差原因
```
偏差分析：
  ├─ 对标 Confluence/语雀的影响（"标配功能"）
  ├─ 高难度 + 高成本 → 错误关联"重要性"
  └─ 忽略了使用场景分析（难度 ≠ 必要性）
```

#### 4. 替代方案更具价值
```
异步协作方案（已有基础）：
  ├─ 评论/批注（FeedbackManager）✅ 已有
  ├─ 审批流（WorkflowManager）✅ 已有
  ├─ 编辑锁（_api_atom_lock）✅ 已有
  └─ 版本管理 ← 需补充，比实时协同更重要
```

### 成本节省
- 原估算：30-50万元（CRDT/OT 开发）
- **节省：30-50万元**

### 决策
- 实时协同编辑从 P0 移除
- 如未来有明确客户需求，可作为 P2 可选增强
- 当前专注版本管理 + 评论批注 + 审批流

---

## 讨论 4：版本管理系统

### 讨论时间
2026-06-21

### 问题背景
- 当前仅有 timeline 时间线浏览
- 无版本内容快照
- 无 Diff 对比功能
- 无回滚机制

### 用户约束
- 需要版本管理功能
- 不需要分支功能（暂时）
- 需要限制快照数量（控制存储空间）

### 讨论过程

#### 技术选型对比
| 方案 | 外部依赖 | 部署复杂度 | 数据统一性 | 存储空间 |
|------|----------|------------|------------|----------|
| Git-style | Git 二进制 + pygit2 | 高 | 分散（Git + PostgreSQL） | 小 |
| **Snapshot** | 无 | 低 | 统一 | 较大（可控） |

#### Git-style 外部依赖问题
```
Git-style 需要的外部依赖：
  ├─ Git 二进制（服务器安装）
  ├─ libgit2 / pygit2（Python Git 库）
  ├─ Git 仓库管理（.git 目录）
  └─ 可能需要 Git 服务器（GitLab/Gitea）

问题：
  ├─ 部署复杂度增加
  ├─ 跨平台兼容问题（Windows）
  ├─ 并发提交冲突处理
  └─ 数据分散（文件系统 + 数据库）
```

### 结论
**选定 Snapshot 方案（PostgreSQL 原生存储）**

### 核心理由
- 无外部依赖（纯 PostgreSQL）
- 部署简单、数据统一
- 快照数量可控（存储空间可控）

### 设计方案

#### 表结构
```sql
-- 版本表
CREATE TABLE atom_versions (
  id SERIAL PRIMARY KEY,
  atom_id INTEGER REFERENCES atoms(id),
  version_number INTEGER NOT NULL,
  title VARCHAR(512),
  content TEXT,  -- 完整快照
  metadata JSONB,  -- 版本元数据（备注、标签）
  author_id VARCHAR(64) REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  change_summary VARCHAR(512),  -- 变更摘要
  UNIQUE(atom_id, version_number)
);
```

#### 快照数量限制策略
```
混合策略（推荐）：
  ├─ 最近 10 个版本：全部保留
  ├─ 10-30 个版本：每天保留 1 个
  ├─ 30-90 个版本：每周保留 1 个
  ├─ 90 天以上：每月保留 1 个
  └─ 最大保留：100 个版本（可配置）

简单策略（备选）：
  └─ 保留最近 N 个版本（如 100 个）
```

#### 核心功能
```
版本管理功能：
  ├─ 自动版本：每次保存自动创建新版本
  ├─ 版本列表：查询历史版本
  ├─ 版本对比：前端 diff-match-patch 库
  ├─ 一键回滚：恢复到指定版本
  ├─ 版本备注：记录变更摘要
  └─ 自动清理：超出数量限制自动删除最旧版本
```

#### 存储空间估算
```
假设：
  ├─ 平均文档大小：10 KB
  ├─ 最大版本数：100
  └─ 单文档版本存储：10 KB × 100 = 1 MB

10,000 个文档：
  ├─ 当前版本：100 MB
  ├─ 历史版本：10 GB
  └─ 总计：约 10 GB（可接受）
```

### 迁移路径
```
阶段 1：表结构与基础 API（1周）
  ├─ 创建 atom_versions 表
  ├─ VersionManager 类实现
  ├─ create_version / get_versions / get_version_content
  └─ 自动清理逻辑

阶段 2：前端版本管理界面（1周）
  ├─ 版本历史列表页面
  ├─ 版本详情查看
  ├─ Diff 对比视图（diff-match-patch）
  └─ 回滚确认交互

阶段 3：回滚与配置（1周）
  ├─ rollback_to_version 实现
  ├─ 版本保留策略配置
  ├─ 定时清理任务
  └─ 管理员配置界面
```

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| 表结构与 API | 3-4万元 | VersionManager 实现 |
| 前端界面 | 3-4万元 | 版本列表 + Diff 对比 |
| 回滚与配置 | 2-3万元 | 回滚逻辑 + 清理任务 |
| **合计** | **8-11万元** | 比原估算节省 2-9万元 |

### 技术栈变化
```
改造前：
  timeline 时间线浏览（仅展示修改时间）

改造后：
  PostgreSQL 版本表 + VersionManager + diff-match-patch
```

### 下一步行动
- 设计 atom_versions 表结构
- 实现 VersionManager 类
- 集成 diff-match-patch 前端库

---

## 补充说明：图像存储方案

### 关联讨论
讨论 4：版本管理系统

### 问题背景
讨论 4 聚焦于文本知识点的版本管理，但知识库中的知识点可能包含图像资源：
- Markdown 文档中通过 `![](image.png)` 引用图像
- 图像作为知识点的辅助说明（截图、流程图、示意图等）
- 需要确定图像的存储策略

### 存储方案对比

#### 方案一：BYTEA（二进制存储）
```sql
-- 图像直接存储在数据库中
CREATE TABLE atom_assets (
  id SERIAL PRIMARY KEY,
  atom_id INTEGER REFERENCES atoms(id),
  filename VARCHAR(255),
  mime_type VARCHAR(64),
  data BYTEA,  -- 二进制数据
  size INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);
```

**优势**：
- 数据完全统一（图像与文本在同一事务中）
- 备份/恢复简单（单一数据源）
- 权限控制统一（PostgreSQL RLS）
- 无需额外文件服务

**劣势**：
- 数据库体积膨胀快
- 大文件影响查询性能
- 内存占用较高（加载全量数据）

#### 方案二：文件路径引用
```sql
-- 仅存储文件路径
CREATE TABLE atom_assets (
  id SERIAL PRIMARY KEY,
  atom_id INTEGER REFERENCES atoms(id),
  filename VARCHAR(255),
  file_path VARCHAR(512),  -- 文件系统路径或对象存储 URL
  mime_type VARCHAR(64),
  size INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);
```

**优势**：
- 数据库轻量
- 文件可使用 CDN 加速
- 支持流式传输
- 易于迁移到对象存储

**劣势**：
- 数据分散（数据库 + 文件系统/对象存储）
- 备份需协调多个数据源
- 权限控制需额外实现
- 事务一致性复杂

### 推荐方案：混合存储

根据文件大小采用不同策略：

```sql
-- 统一资产表（支持两种存储方式）
CREATE TABLE atom_assets (
  id SERIAL PRIMARY KEY,
  atom_id INTEGER REFERENCES atoms(id) ON DELETE CASCADE,
  filename VARCHAR(255) NOT NULL,
  mime_type VARCHAR(64) NOT NULL,
  size INTEGER NOT NULL,  -- 字节数

  -- 存储方式
  storage_type VARCHAR(16) NOT NULL,  -- 'inline' | 'external'

  -- 内联存储（小文件）
  data BYTEA,

  -- 外部存储（大文件）
  storage_path VARCHAR(512),  -- 对象存储路径
  storage_provider VARCHAR(32),  -- 'local' | 's3' | 'minio' | 'oss'

  -- 元数据
  checksum VARCHAR(64),  -- SHA256 校验
  created_at TIMESTAMP DEFAULT NOW(),
  created_by VARCHAR(64) REFERENCES users(id),

  CONSTRAINT check_storage_consistency CHECK (
    (storage_type = 'inline' AND data IS NOT NULL) OR
    (storage_type = 'external' AND storage_path IS NOT NULL)
  )
);

CREATE INDEX idx_atom_assets_atom_id ON atom_assets(atom_id);
CREATE INDEX idx_atom_assets_storage_type ON atom_assets(storage_type);
```

#### 存储策略阈值
```
文件大小阈值（可配置）：
  ├─ < 100 KB：内联存储（BYTEA）
  │   └─ 适合：小图标、缩略图、简单示意图
  │
  └─ >= 100 KB：外部存储（对象存储）
      └─ 适合：大截图、高清图片、PDF 附件

推荐对象存储：
  ├─ MinIO（自建，信创友好）
  ├─ 阿里云 OSS
  ├─ 腾讯云 COS
  └─ AWS S3（海外）
```

### 与 Markdown 文档的集成

#### 1. 图像引用方式
```
Markdown 文档中保持标准格式：
![描述文字](assets/ image.png)

系统自动处理：
  ├─ 存储时：上传图像 → atom_assets 表 → 替换路径为资产 ID
  └─ 渲染时：查询 atom_assets → 生成访问 URL
```

#### 2. 图像上传流程
```
用户上传图像：
  ↓
检查文件大小
  ├─ < 100 KB → 存储为 BYTEA
  └─ >= 100 KB → 上传到对象存储
  ↓
生成资产记录（atom_assets）
  ↓
返回 Markdown 引用路径
  └─ ![图片](asset://123) 或 ![图片](/api/assets/123)
```

#### 3. 图像访问流程
```
请求 /api/assets/{id}
  ↓
查询 atom_assets 表
  ↓
权限检查（RLS + atom_id 关联）
  ├─ 无权限 → 403
  └─ 有权限 → 继续
  ↓
获取图像数据
  ├─ storage_type = 'inline' → 直接返回 BYTEA
  └─ storage_type = 'external' → 重定向到对象存储 URL
  ↓
返回图像响应（Content-Type, Cache-Control）
```

### 版本管理联动

#### 图像变化触发版本创建
```
图像操作与版本管理的关联：
  ├─ 新增图像 → 创建新版本（含图像资产记录）
  ├─ 删除图像 → 创建新版本（移除图像资产记录）
  └─ 替换图像 → 创建新版本（更新图像资产记录）

版本快照包含：
  ├─ 文本内容（atom_versions.content）
  └─ 关联图像（atom_versions.assets JSONB）
      └─ [{"asset_id": 1, "filename": "image.png", "storage_path": "..."}]
```

#### 版本回滚时图像处理
```
回滚到指定版本：
  ├─ 恢复文本内容
  └─ 恢复图像关联
      ├─ 当前版本有、目标版本无 → 删除图像引用
      ├─ 当前版本无、目标版本有 → 恢复图像引用
      └─ 两版本都有但不同 → 替换为版本图像

注意：
  └─ 图像资产表不删除物理文件，仅更新关联
      └─ 原因：其他版本可能引用同一图像
```

#### 图像版本快照存储策略
```
atom_versions 表扩展：
CREATE TABLE atom_versions (
  id SERIAL PRIMARY KEY,
  atom_id INTEGER REFERENCES atoms(id),
  version_number INTEGER NOT NULL,
  title VARCHAR(512),
  content TEXT,
  metadata JSONB,

  -- 新增：版本关联的图像资产快照
  assets_snapshot JSONB,  -- 资产 ID 列表快照

  author_id VARCHAR(64) REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  change_summary VARCHAR(512)
);
```

### 存储空间估算
```
假设场景：
  ├─ 10,000 个知识点
  ├─ 平均每知识点 2 张图像
  ├─ 平均图像大小 200 KB

存储需求：
  ├─ 小文件（< 100 KB，约 30%）：
  │   └─ 10,000 × 2 × 30% × 50 KB = 300 MB（数据库）
  │
  └─ 大文件（>= 100 KB，约 70%）：
      └─ 10,000 × 2 × 70% × 200 KB = 2.8 GB（对象存储）

版本管理额外开销（假设保留 100 版本）：
  ├─ 文本版本：10,000 × 10 KB × 100 = 10 GB
  └─ 图像版本：共享存储（图像不变时引用同一资产）
```

### 实施建议
```
阶段 1：基础存储（1周）
  ├─ 创建 atom_assets 表
  ├─ 实现图像上传 API（内联存储）
  └─ 图像访问 API

阶段 2：对象存储集成（1周）
  ├─ MinIO / 阿里云 OSS 集成
  ├─ 大文件上传流程
  └─ 存储策略阈值配置

阶段 3：Markdown 集成（1周）
  ├─ 编辑器图像上传
  ├─ 图像引用解析
  └─ 渲染时图像访问

阶段 4：版本管理联动（1周）
  ├─ 图像变化触发版本创建
  ├─ 版本快照包含图像资产
  └─ 回滚时恢复图像关联
```

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| 基础存储 + 对象存储 | 3-5万元 | atom_assets 表 + MinIO/OSS |
| Markdown 集成 | 2-3万元 | 编辑器 + 渲染器 |
| 版本管理联动 | 2-3万元 | 图像版本快照 |
| **合计** | **7-11万元** | 与版本管理系统协同开发 |

---

## 讨论 5：容器化部署

### 讨论时间
2026-06-21

### 问题背景
- 当前单文件部署（llm-wiki.py）
- 无 Docker 镜像
- 无 Kubernetes 部署方案
- 无 CI/CD 集成

### 用户约束
- 需要了解 Kubernetes 和 CI/CD 概念
- 需要标准化部署方案

### 概念解释

#### Kubernetes（K8s）
```
定义：容器编排平台，自动化部署、扩展和管理容器化应用

简单理解：
  Docker = 把应用打包成"集装箱"（容器）
  Kubernetes = 管理"集装箱码头"（容器集群）

解决的问题：
  ├─ 自动重启：容器挂了自动拉起
  ├─ 自动扩缩容：流量大自动增加实例
  ├─ 故障转移：服务器挂了自动迁移
  ├─ 服务发现：容器之间自动找到彼此
  └─ 负载均衡：自动分配流量

是否需要：
  ├─ 单机部署（<100 用户）→ 不需要，Docker Compose 足够
  ├─ 小集群（100-500 用户）→ 可选
  └─ 大规模（>500 用户）或高可用 → 需要
```

#### CI/CD
```
定义：Continuous Integration / Continuous Delivery（持续集成/持续交付）

CI（持续集成）：
  代码提交 → 自动构建 → 自动测试 → 自动检查

CD（持续交付）：
  测试通过 → 自动打包 → 自动部署

传统流程 vs CI/CD：
  传统：手动测试 → 手动打包 → 手动上传 → 手动重启（1-2小时）
  CI/CD：提交代码 → 自动完成（5-10分钟）
```

### 结论
**Docker Compose + GitHub Actions（起步方案）**

### 核心理由
- Docker Compose 满足中小规模部署
- GitHub Actions 开源项目免费
- Kubernetes 暂不投入，后期按需扩展

### 部署架构
```yaml
# docker-compose.yml
services:
  llm-wiki:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/llmwiki
      - CASDOOR_URL=http://casdoor:8000
    depends_on:
      - db
      - casdoor

  db:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data

  casdoor:
    image: casbin/casdoor:latest
    ports:
      - "8001:8000"
    depends_on:
      - db

volumes:
  pgdata:
```

### CI/CD 流程（GitHub Actions）
```yaml
# .github/workflows/build.yml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    steps:
      - name: Build Docker image
      - name: Push to registry
      - name: Deploy to server
```

### 分阶段实施
```
阶段 1：Docker 镜像（1周）
  ├─ 编写 Dockerfile
  ├─ 本地构建测试
  └─ 推送到 Docker Hub/私有仓库

阶段 2：Docker Compose（1周）
  ├─ 编写 docker-compose.yml
  ├─ PostgreSQL + Casdoor + llm-wiki 编排
  ├─ 环境变量配置
  └─ 一键启动脚本

阶段 3：CI/CD 集成（1周）
  ├─ GitHub Actions 配置
  ├─ 自动构建镜像
  ├─ 自动部署到测试环境
  └─ 手动确认部署到生产

阶段 4：Kubernetes（可选，后期）
  ├─ Helm Charts 编写
  ├─ K8s 部署配置
  └─ 触发条件：客户要求或规模增长
```

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| Docker 镜像 | 1-2万元 | Dockerfile + 构建流程 |
| Docker Compose | 1-2万元 | 编排配置 + 启动脚本 |
| CI/CD 集成 | 1-2万元 | GitHub Actions 配置 |
| **合计** | **3-6万元** | 不含 Kubernetes |

### 技术栈变化
```
改造前：
  Python 单文件部署

改造后：
  Docker + Docker Compose + GitHub Actions
  （Kubernetes 可选）
```

### 下一步行动
- 编写 Dockerfile
- 编写 docker-compose.yml
- 配置 GitHub Actions

---

## 讨论总结

### 当前决策汇总

#### P0 级差距（阻塞性，必须解决）
| 项目 | 决策 | 投入 |
|------|------|------|
| 数据库选型 | PostgreSQL | 18-29万元 |
| SSO 集成 | Casdoor | 11-17万元 |
| 实时协同编辑 | 降级 P2，暂缓 | 节省 30-50万元 |
| 版本管理系统 | Snapshot | 8-11万元 |
| 容器化部署 | Docker Compose + GitHub Actions | 3-6万元 |

#### P1 级差距（影响竞争力）
| 项目 | 决策 | 投入 |
|------|------|------|
| 搜索高亮和联想 | mark.js + 建议API | 3-5万元 |
| OCR 扫描件识别 | 云服务 API → PaddleOCR | 4-7万元 |
| 在线预览 | PDF.js + KKFileView | 4-6万元 |
| 移动端优化 | 响应式 + PWA | 3-5万元 |

#### P2 级差距（特定行业必需）
| 项目 | 决策 | 投入 |
|------|------|------|
| 等保三级/密评 | 暂缓，按需执行 | 预留 30-125万元 |
| 审计日志不可篡改 | 链式哈希校验 | 3-5万元 |
| 数据加密存储 | pgcrypto + 应用层加密 | 4-7万元 |
| 实时协同编辑 | 暂缓 | - |

### 累计投入估算

```
已确定投入：
  ├─ P0（不含实时协同）：40-63万元
  ├─ P1：14-23万元
  ├─ P2（不含等保）：7-12万元
  ├─ 图像存储（补充）：7-11万元
  ├─ 多级 Wiki 管理（补充）：12-19万元
  └─ 合计：73-109万元

暂缓/不执行：
  ├─ 实时协同编辑：不执行（保留编辑锁）
  └─ 等保三级/密评：预留 30-125万元（按需）
```

### 资源需求汇总

```
完整部署资源：
  ├─ llm-wiki 主服务：2核4G
  ├─ PostgreSQL：2核4G
  ├─ Casdoor：1核2G
  ├─ PaddleOCR：4核8G
  ├─ KKFileView：2核4G
  └─ 总计：10-12核，20-24G 内存
```

### 实施阶段建议

```
阶段 1：基础设施（3-6个月）
  ├─ PostgreSQL 迁移
  ├─ Casdoor SSO 集成
  ├─ 版本管理系统
  ├─ 审计日志改造
  ├─ 数据加密存储
  └─ 容器化部署
  └─ 投入：40-63万元

阶段 2：用户体验（2-3个月）
  ├─ 搜索优化
  ├─ OCR 能力
  ├─ 在线预览
  ├─ 移动端优化
  ├─ 图像存储
  └─ 投入：21-32万元

阶段 3：合规认证（按需）
  ├─ 等保三级
  ├─ 密评
  └─ 投入：30-125万元
```

---

**文件创建时间**：2026-06-21
**讨论完成时间**：2026-06-21

---

## P1 级差距讨论

---

## 讨论 6：搜索高亮和联想

### 讨论时间
2026-06-21

### 问题背景
```
当前搜索能力：
  ├─ FTS5 分词检索 ✅
  ├─ 向量语义检索 ✅
  ├─ 搜索历史记录 ✅
  └─ 搜索体验不足：
      ├─ 无关键词高亮
      ├─ 无下拉联想词
      ├─ 无热门搜索推荐
      └─ 无搜索结果摘要
```

### 结论
**同意搜索体验优化方案**

### 解决方案

| 功能 | 技术方案 | 难度 | 工作量 |
|------|----------|:----:|--------|
| 关键词高亮 | mark.js（前端） | 低 | 1-2天 |
| 搜索建议 | 基于 search_history.json | 低 | 2-3天 |
| 搜索结果摘要 | PostgreSQL ts_headline | 中 | 2-3天 |
| 热门搜索 | 统计搜索历史 | 低 | 1天 |

### 技术实现要点

#### 关键词高亮
```javascript
// 前端实现（mark.js）
import Mark from 'mark.js';

function highlightKeywords(container, keyword) {
  const markInstance = new Mark(container);
  markInstance.mark(keyword, {
    className: 'highlight',
    separateWordSearch: false
  });
}
```

#### 搜索建议
```python
# 后端 API
def get_search_suggestions(query: str, limit: int = 10) -> list:
    """基于搜索历史和热门词提供建议"""
    # 1. 从搜索历史匹配
    # 2. 从标签匹配
    # 3. 返回建议列表
```

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| 关键词高亮 | 0.5-1万元 | mark.js 前端集成 |
| 搜索建议 | 1-2万元 | API + 前端组件 |
| 搜索结果摘要 | 1-2万元 | PostgreSQL ts_headline |
| 热门搜索 | 0.5万元 | 统计 + 展示 |
| **合计** | **3-5万元** | 周期：1-2周 |

---

## 讨论 7：OCR 扫描件识别

### 讨论时间
2026-06-21

### 问题背景
```
当前缺失能力：
  ├─ PDF 扫描件（图片型）无法识别
  ├─ 图片中的文字无法提取
  └─ 传真/扫描文档无法处理

企业级需求：
  ├─ 合同扫描件识别
  ├─ 发票/票据识别
  ├─ 纸质文档数字化
  └─ 历史档案录入
```

### 用户约束
- 同意分阶段方案
- 关注部署复杂度和资源要求

### 结论
**分阶段方案：云服务 API → PaddleOCR 本地部署**

### OCR 技术选型
| 方案 | 说明 | 优点 | 缺点 |
|------|------|------|------|
| 云服务 API | 百度/腾讯/阿里 OCR | 快速上线、识别率高 | 按量付费、数据外传 |
| **PaddleOCR** | 国产开源 | 本地部署、数据自控、信创友好 | 需服务器资源 |

### 分阶段实施
```
阶段 1（MVP）：云服务 API
  ├─ 快速上线（1周）
  ├─ 低成本验证需求
  ├─ 百度/腾讯 OCR API 集成
  └─ 适合：初期量少、快速验证

阶段 2（企业化）：PaddleOCR
  ├─ 触发条件：扫描件量大或有隐私/信创要求
  ├─ 本地部署（2-3周）
  ├─ Docker 一键部署
  └─ 适合：政企客户、信创要求
```

### PaddleOCR 部署分析

#### 部署方式
```yaml
# Docker Compose 添加 OCR 服务
services:
  ocr:
    image: paddleocr/paddleocr:latest
    ports:
      - "8868:8868"
    environment:
      - USE_GPU=false  # CPU 模式
    deploy:
      resources:
        limits:
          memory: 4G
```

#### 资源要求
| 配置项 | 最低要求 | 推荐配置 |
|--------|----------|----------|
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| GPU | 无需 | 可选（加速 10-50 倍） |
| 存储 | 2 GB | 5 GB+ |

#### CPU vs GPU 性能
```
CPU 模式（4核）：
  ├─ 简单文档：2-5 秒/张
  ├─ 复杂文档：5-15 秒/张
  └─ 适合：每天 < 100 张，异步处理

GPU 模式：
  ├─ 简单文档：0.2-0.5 秒/张
  └─ 适合：每天 > 1000 张，实时处理
```

#### 部署复杂度评估
| 方面 | 复杂度 | 说明 |
|------|:------:|------|
| Docker 部署 | 🟢 低 | docker-compose up 即可 |
| API 集成 | 🟢 低 | 标准 HTTP 接口 |
| 中文识别效果 | 🟢 好 | 开箱即用 |
| GPU 配置 | 🟡 中 | 需要 NVIDIA 驱动（可选） |

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| 云服务 API 集成 | 1-2万元 | 快速上线 |
| PaddleOCR 部署 | 3-5万元 | 本地部署 + 集成 |
| **合计（分阶段）** | **4-7万元** | 可按需切换 |

### llm-wiki 全栈资源需求
```
总计（含 OCR）：
  ├─ llm-wiki 主服务：2核4G
  ├─ PostgreSQL：2核4G
  ├─ Casdoor：1核2G
  ├─ PaddleOCR：4核8G（CPU 模式）
  └─ 总计：8-10核，16-20G 内存
```

---

## 讨论 8：在线预览

### 讨论时间
2026-06-21

### 问题背景
```
当前缺失能力：
  ├─ PDF 无法在线预览（需下载）
  ├─ Office 文档无法预览
  └─ 图片/视频需下载查看
```

### 用户约束
- 同意分阶段方案
- 询问"信创友好"含义

### 概念解释：信创友好
```
信创 = 信息技术应用创新

信创友好标准：
  ├─ 国产/开源可控：无国外商业控制
  ├─ 可本地部署：数据不出服务器
  ├─ 无国外供应链风险：不受制裁影响
  └─ 支持国产软硬件：麒麟/统信/达梦等

示例对比：
  ├─ KKFileView ✅ 信创友好：国产开源、本地部署
  └─ Office Online ❌ 不友好：微软服务、数据外传
```

### 结论
**分阶段实施方案**

### 技术选型
| 文件类型 | 技术方案 | 说明 |
|----------|----------|------|
| PDF | PDF.js（Mozilla） | 纯前端，成熟稳定 |
| Office | KKFileView | 国产开源，信创友好 |
| 图片/视频 | HTML5 原生 | 直接支持 |

### 分阶段实施
```
阶段 1：PDF 在线预览（1周）
  ├─ 集成 PDF.js
  └─ 投入：1-2万元

阶段 2：图片/视频预览（1周）
  ├─ 图片浏览器（lightbox）
  ├─ 视频播放器
  └─ 投入：1万元

阶段 3：Office 文档预览（2周）
  ├─ KKFileView 部署（国产开源、信创友好）
  ├─ 支持：doc/docx/xls/xlsx/ppt/pptx
  └─ 投入：2-3万元
```

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| PDF 在线预览 | 1-2万元 | PDF.js 集成 |
| 图片/视频预览 | 1万元 | 前端组件 |
| Office 文档预览 | 2-3万元 | KKFileView 部署 |
| **合计** | **4-6万元** | 周期：3-4周 |

### 资源需求
```
添加文件预览后：
  ├─ llm-wiki：2核4G
  ├─ PostgreSQL：2核4G
  ├─ Casdoor：1核2G
  ├─ PaddleOCR：4核8G
  ├─ KKFileView：2核4G
  └─ 总计：10-12核，20-24G 内存
```

---

## 讨论 9：移动端优化

### 讨论时间
2026-06-21

### 问题背景
```
当前缺失能力：
  ├─ 未针对移动端优化
  ├─ 小屏幕体验差
  └─ 无 PWA 离线能力
```

### 结论
**响应式设计 + PWA 方案**

### 分阶段实施
```
阶段 1：响应式设计（2周）
  ├─ 优化核心页面布局
  ├─ 移动端导航菜单
  ├─ 表格/表单适配
  └─ 投入：2-3万元

阶段 2：PWA 能力（1周）
  ├─ manifest.json 配置
  ├─ Service Worker 缓存策略
  ├─ 离线浏览基础内容
  └─ 投入：1-2万元

阶段 3：移动端专项优化（可选）
  ├─ 手势操作
  ├─ 移动端编辑器优化
  └─ 投入：2万元
```

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| 响应式设计 | 2-3万元 | Tailwind CSS 适配 |
| PWA 能力 | 1-2万元 | 离线缓存 + 可安装 |
| 移动端专项优化 | 2万元（可选） | 手势、编辑器 |
| **合计** | **3-5万元** | 周期：2-3周 |

---

## 讨论 10：等保三级/密评

### 讨论时间
2026-06-21

### 问题背景
```
等保三级 = 信息安全等级保护第三级
适用行业：政企/金融/医疗/关键基础设施

密评 = 商用密码应用安全性评估
要求使用国密算法（SM2/SM3/SM4）
```

### 用户约束
暂缓，按需再执行

### 结论
**暂缓等保三级/密评认证，后续按需投入**

### 决策依据
```
不需要（当前情况）：
  ├─ 无明确政企/金融客户
  ├─ 无合规强制要求
  └─ 建议：暂不投入

需要（触发条件）：
  ├─ 有政企/金融客户明确要求
  ├─ 有合规强制要求
  └─ 建议：投入认证
```

### 预留投入
| 项目 | 投入 | 说明 |
|------|------|------|
| 等保三级 | 30-55万 | 测评费 + 整改费 |
| 密评 | 30-70万（可选） | 测评费 + 整改费 |
| **预留** | **30-125万** | 暂不投入，按需执行 |

---

## 讨论 11：审计日志不可篡改

### 讨论时间
2026-06-21

### 问题背景
```
当前问题：
  ├─ 审计日志存储在 audit.json
  ├─ 可删除、可修改
  └─ 不满足合规要求

合规要求：
  ├─ 审计日志不可篡改
  ├─ 审计日志不可删除
  ├─ 保留 180 天以上
  └─ 可追溯、可审计
```

### 用户约束
需要投入

### 结论
**数据库追加写入 + 链式哈希校验方案**

### 技术方案

#### 审计日志表设计
```sql
CREATE TABLE audit_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  action VARCHAR(32) NOT NULL,
  resource_type VARCHAR(32),
  resource_id VARCHAR(64),
  details JSONB,
  ip_address VARCHAR(45),
  created_at TIMESTAMP DEFAULT NOW(),
  
  -- 链式哈希校验
  record_hash VARCHAR(64),  -- 当前记录哈希
  prev_hash VARCHAR(64),    -- 前一条记录哈希
  CONSTRAINT audit_readonly CHECK (true)
);

-- 禁止 UPDATE 和 DELETE
REVOKE UPDATE, DELETE ON audit_logs FROM PUBLIC;
```

#### 链式哈希校验
```
插入时：
  ├─ 获取上一条记录哈希
  ├─ 计算当前记录哈希（含上一条哈希）
  └─ 形成链式结构

验证时：
  ├─ 遍历所有记录
  ├─ 重新计算哈希
  ├─ 校验链是否完整
  └─ 检测篡改
```

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| 审计日志表改造 | 2-3万元 | PostgreSQL 追加写入 |
| 哈希校验实现 | 1-2万元 | 链式哈希 + 验证 API |
| 日志保留策略 | 0.5万元 | 180 天自动归档 |
| **合计** | **3-5万元** | 周期：1-2周 |

### 下一步行动
- 创建 audit_logs 表
- 实现链式哈希插入逻辑
- 实现完整性验证 API

---

## 讨论 12：数据加密存储

### 讨论时间
2026-06-21

### 问题背景
```
当前问题：
  ├─ Markdown 文件明文存储
  ├─ 数据库数据明文存储
  └─ 敏感数据无加密保护

合规要求：
  ├─ 敏感数据加密存储
  ├─ 数据库字段级加密
  └─ 密钥安全管理
```

### 用户约束
需要投入

### 结论
**PostgreSQL pgcrypto + 应用层加密（分层策略）**

### 加密范围
| 数据类型 | 加密需求 |
|----------|:--------:|
| 文档内容 | 可选 |
| 用户密码 | ✅ 已有 |
| 个人信息（手机/邮箱） | ✅ 需要 |
| 系统配置/API 密钥 | ✅ 需要 |
| 审计日志 | 可选 |

### 技术方案

#### PostgreSQL pgcrypto
```sql
-- 启用扩展
CREATE EXTENSION pgcrypto;

-- 加密存储
INSERT INTO users (name, phone)
VALUES ('张三', pgp_sym_encrypt('13812345678', 'key'));

-- 解密查询
SELECT name, pgp_sym_decrypt(phone, 'key') as phone
FROM users;
```

#### 分层加密策略
```
1. 数据库层：pgcrypto
   └─ 敏感字段（手机、邮箱、身份证）

2. 应用层：Python cryptography
   └─ 特别敏感数据（API 密钥）

3. 传输层：HTTPS（TLS 1.3）
   └─ Nginx/反向代理配置
```

#### 密钥管理
```
策略：
  ├─ 主密钥：环境变量
  ├─ 数据加密密钥：被主密钥加密
  └─ 定期轮换：每年一次

存储选项：
  ├─ 环境变量（简单）
  ├─ Vault（开源专业方案）
  └─ 云服务 KMS
```

### 成本估算
| 项目 | 投入 | 说明 |
|------|------|------|
| pgcrypto 集成 | 2-3万元 | 字段加密改造 |
| 应用层加密 | 1-2万元 | API 密钥等 |
| 密钥管理 | 1-2万元 | 轮换、存储 |
| HTTPS 配置 | 0.5万元 | Nginx + 证书 |
| **合计** | **4-7万元** | 周期：2-3周 |

### 下一步行动
- 启用 PostgreSQL pgcrypto 扩展
- 改造敏感字段加密
- 配置 HTTPS

---

## 全部讨论完成