# llm-wiki 企业化改造技术架构文档

> **版本**：v1.0
> **创建时间**：2026-06-21
> **基准评分**：60.25/100
> **目标评分**：90/100

---

## 一、系统架构概览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户访问层                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  CLI 用户    │  │  Web 用户    │  │  Skill 用户  │  │  移动端用户  │     │
│  │  (file_mode) │  │  (db_mode)   │  │  (Claude)    │  │  (PWA)       │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼─────────────────┼─────────────────┼─────────────────┼─────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           接入层                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐     │
│  │  CLI 入口    │  │  Web 入口（FastAPI + 静态 HTML）                  │     │
│  │  llm-wiki.py │  │  ├── 认证中间件（JWT + Casdoor）                  │     │
│  │              │  │  ├── 权限中间件（Casbin + RLS）                   │     │
│  │  file_mode   │  │  └───────────────────────────────────────────────│     │
│  │  ✅ 直接调用 │  │  db_mode ✅ API 调用                              │     │
│  └──────┬───────┘  └──────────────┬───────────────────────────────────┘     │
└─────────┼─────────────────────────┼─────────────────────────────────────────┘
          │                         │
          ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           核心业务层                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  统一 API 抽象层（StorageAdapter）                                    │  │
│  │  ├── FileAdapter（file_mode）：操作 atoms/ 目录                       │  │
│  │  └── DBAdapter（db_mode）：操作 PostgreSQL                            │  │
│  │  └───────────────────────────────────────────────────────────────────│  │
│  │                                                                      │  │
│  │  核心模块                                                            │  │
│  │  ├── KnowledgeBaseManager    # 多级知识库管理                        │  │
│  │  ├── AtomManager             # 知识原子 CRUD                         │  │
│  │  ├── VersionManager          # 版本管理（Snapshot）                  │  │
│  │  ├── SearchEngine            # 搜索（tsvector + pgvector）           │  │
│  │  ├── Ingestor                # 资料摄入                              │  │
│  │  ├── Exporter/Importer       # OKF Bundle 导入导出                   │  │
│  │  └───────────────────────────────────────────────────────────────────│  │
│  │                                                                      │  │
│  │  企业模块                                                            │  │
│  │  ├── AuthManager             # 认证授权（Casdoor + Casbin）          │  │
│  │  ├── AuditLogger             # 审计日志（链式哈希）                  │  │
│  │  ├── AssetManager            # 图像资产（BYTEA + 对象存储）          │  │
│  │  ├── OCRService              # OCR 识别（PaddleOCR）                 │  │
│  │  ├── PreviewService          # 在线预览（PDF.js + KKFileView）       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据存储层                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  PostgreSQL（主存储）                                                  │ │
│  │  ├── atoms                 # 知识原子内容                             │ │
│  │  ├── atom_versions         # 版本快照                                 │ │
│  │  ├── atom_assets           # 图像资源                                 │ │
│  │  ├── knowledge_bases       # 多级知识库                               │ │
│  │  ├── kb_members            # 知识库成员                               │ │
│  │  ├── kb_aggregations       # 知识库聚合                               │ │
│  │  ├── users                 # 用户                                     │ │
│  │  ├── audit_logs            # 审计日志                                 │ │
│  │  ├── pgvector              # 向量索引                                 │ │
│  │  ├── JSONB                 # 元数据存储                               │ │
│  │  ├── RLS                   # 行级安全                                 │ │
│  │  └─────────────────────────────────────────────────────────────────────│ │
│  │                                                                        │ │
│  │  对象存储（可选）                                                      │ │
│  │  ├── MinIO / 阿里云 OSS  # 大文件存储                                 │ │
│  │  └─────────────────────────────────────────────────────────────────────│ │
│  │                                                                        │ │
│  │  文件系统（file_mode）                                                 │ │
│  │  ├── atoms/                # Markdown 文件                            │ │
│  │  ├── raw/                  # 原始资料                                 │ │
│  │  ├── views/                # 可视化输出                               │ │
│  └────────────────────────────────────────────────────────────────────────┐ │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           基础服务层                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Casdoor     │  │  PaddleOCR   │  │  KKFileView  │  │  Nginx       │     │
│  │  SSO 服务    │  │  OCR 服务    │  │  预览服务    │  │  反向代理    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼─────────────────┼─────────────────┼─────────────────┼─────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           部署层                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Docker Compose                                                        │ │
│  │  ├── llm-wiki        # 主服务（Python）                                │ │
│  │  ├── postgres        # PostgreSQL                                      │ │
│  │  ├── casdoor         # SSO                                             │ │
│  │  ├── paddleocr       # OCR（可选）                                     │ │
│  │  ├── kkfileview      # 预览（可选）                                    │ │
│  │  └─────────────────────────────────────────────────────────────────────│ │
│  │                                                                        │ │
│  │  高可用（可选）                                                        │ │
│  │  ├── PostgreSQL 主从复制                                              │ │
│  │  ├── PgBouncer 连接池                                                 │ │
│  │  ├── Nginx 负载均衡                                                   │ │
│  └────────────────────────────────────────────────────────────────────────┐ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 双模式架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        双模式架构设计                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  用户入口                                                              │  │
│  │  ├── CLI：llm-wiki.py --mode file                                     │  │
│  │  ├── Web：检测知识库类型，自动选择模式                                 │  │
│  │  ├── Skill：固定 file_mode                                            │  │
│  │  └─────────────────────────────────────────────────────────────────────│  │
│  │                                                                       │  │
│  │  ┌─────────────────────┐      ┌─────────────────────┐                │  │
│  │  │  StorageAdapter     │──────│  模式检测           │                │  │
│  │  │  (统一接口)         │      │  kb_meta.mode       │                │  │
│  │  │                     │      │                     │                │  │
│  │  │  ├── create_atom()  │      │  file_mode:         │                │  │
│  │  │  ├── get_atom()     │      │    atoms/*.md       │                │  │
│  │  │  ├── update_atom()  │      │                     │                │  │
│  │  │  ├── delete_atom()  │      │  db_mode:           │                │  │
│  │  │  ├── search()       │      │    PostgreSQL       │                │  │
│  │  │  ├── export()       │      │                     │                │  │
│  │  │  └── import()       │      └─────────────────────┘                │  │
│  │  └─────────────────────┘                                              │  │
│  │          │                                                            │  │
│  │          ├─────────────────────┬─────────────────────┐               │  │
│  │          │                     │                     │               │  │
│  │          ▼                     ▼                     ▼               │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │  │
│  │  │  FileAdapter    │  │  DBAdapter      │  │  HybridAdapter  │      │  │
│  │  │                 │  │                 │  │  (同步)         │      │  │
│  │  │  文件操作       │  │  PostgreSQL     │  │                 │      │  │
│  │  │                 │  │                 │  │  双写 + 导出    │      │  │
│  │  │  ✅ 无依赖      │  │  ✅ 多用户      │  │  ✅ 兼容        │      │  │
│  │  │  ✅ Git 原生    │  │  ✅ 版本管理    │  │                 │      │  │
│  │  │  ✅ Obsidian    │  │  ✅ 权限控制    │  │                 │      │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  模式切换流程：                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  file_mode → db_mode：                                                │  │
│  │    1. 创建 PostgreSQL 知识库                                          │  │
│  │    2. 导入 atoms/ 目录内容                                            │  │
│  │    3. 更新 kb_meta.mode = 'db'                                       │  │
│  │                                                                       │  │
│  │  db_mode → file_mode：                                                │  │
│  │    1. 导出 OKF Bundle                                                 │  │
│  │    2. 解压到目标目录                                                  │  │
│  │    3. 更新 kb_meta.mode = 'file'                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、技术栈

### 2.1 后端技术栈

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **核心语言** | Python | 3.8+ | 兼容现有代码 |
| **Web 框架** | FastAPI | 0.100+ | 异步、高性能、类型注解 |
| **数据库** | PostgreSQL | 15+ | 一库多能 |
| **向量扩展** | pgvector | 0.5+ | 向量索引 |
| **加密扩展** | pgcrypto | 内置 | 字段加密 |
| **全文索引** | tsvector | 内置 | 全文检索 |
| **认证** | Casdoor | 最新 | SSO 服务 |
| **权限** | Casbin | 3.x | RBAC/ABAC |
| **ORM** | SQLAlchemy | 2.x | 异步支持 |
| **连接池** | asyncpg | 0.28+ | 异步 PostgreSQL |

### 2.2 前端技术栈

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **框架** | Alpine.js | 3.x | 轻量响应式 |
| **样式** | Tailwind CSS | 3.x | 原子化 CSS |
| **Markdown** | marked.js | 4.x | Markdown 渲染 |
| **图谱** | Cytoscape.js | 3.x | 知识图谱 |
| **PDF** | PDF.js | 3.x | PDF 预览 |
| **搜索高亮** | mark.js | 8.x | 关键词高亮 |
| **移动端** | PWA | - | Service Worker |

### 2.3 基础设施

| 服务 | 技术 | 说明 |
|------|------|------|
| **容器化** | Docker + Docker Compose | 服务编排 |
| **CI/CD** | GitHub Actions | 自动构建部署 |
| **反向代理** | Nginx | HTTPS + 负载均衡 |
| **OCR** | PaddleOCR（可选） | 本地 OCR 服务 |
| **预览** | KKFileView（可选） | Office 文档预览 |
| **对象存储** | MinIO / 阿里云 OSS | 大文件存储 |

### 2.4 信创兼容

| 国产替代 | 兼容性 | 说明 |
|----------|:------:|------|
| 人大金仓 KingbaseES | ✅ 高 | PostgreSQL 内核 |
| 瀚高数据库 HighGo | ✅ 高 | 基于 PG 二次开发 |
| 达梦 DM8 | ⚠️ 中 | 有 PG 兼容模式 |

---

## 三、模块设计

### 3.1 核心模块划分

```
lib/
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── storage_adapter.py   # StorageAdapter（统一接口）
│   ├── file_adapter.py      # FileAdapter（file_mode）
│   ├── db_adapter.py        # DBAdapter（db_mode）
│   ├── config.py            # 配置管理
│   └── exceptions.py        # 异常定义
│
├── knowledge/               # 知识管理模块
│   ├── __init__.py
│   ├── atom_manager.py      # AtomManager
│   ├── kb_manager.py        # KnowledgeBaseManager
│   ├── version_manager.py   # VersionManager
│   ├── ingestor.py          # KnowledgeIngestor
│   ├── exporter.py          # OKFExporter
│   ├── importer.py          # OKFImporter
│   └── validator.py         # OKFValidator
│
├── search/                  # 搜索模块
│   ├── __init__.py
│   ├── engine.py            # SearchEngine
│   ├── indexer.py           # IndexGenerator
│   ├── semantic.py          # SemanticSearch（pgvector）
│   └── highlight.py         # 搜索高亮
│
├── auth/                    # 认证授权模块
│   ├── __init__.py
│   ├── auth_manager.py      # AuthManager
│   ├── casdoor_client.py    # CasdoorClient
│   ├── casbin_manager.py    # CasbinManager
│   ├── jwt_handler.py       # JWT 处理
│   └── permission.py        # 权限校验
│
├── security/                # 安全模块
│   ├── __init__.py
│   ├── audit_logger.py      # AuditLogger（链式哈希）
│   ├── encryption.py        # EncryptionManager
│   └── crypto_utils.py      # 加密工具
│
├── assets/                  # 资产管理模块
│   ├── __init__.py
│   ├── asset_manager.py     # AssetManager
│   ├── storage.py           # StorageHandler
│   └── image_processor.py   # 图像处理
│
├── services/                # 外部服务模块
│   ├── __init__.py
│   ├── ocr_service.py       # OCRService
│   ├── preview_service.py   # PreviewService
│   └── sync_service.py      # ObsidianSync
│
├── web/                     # Web API 模块
│   ├── __init__.py
│   ├── app.py               # FastAPI 应用
│   ├── routers/
│   │   ├── atoms.py         # 知识原子 API
│   │   ├── kb.py            # 知识库 API
│   │   ├── search.py        # 搜索 API
│   │   ├── auth.py          # 认证 API
│   │   ├── assets.py        # 资产 API
│   │   └── admin.py         # 管理 API
│   ├── middleware/
│   │   ├── auth.py          # 认证中间件
│   │   ├── permission.py    # 权限中间件
│   │   └── audit.py         # 审计中间件
│   └── schemas/
│   │   ├── atom.py          # Atom Schema
│   │   ├── kb.py            # KB Schema
│   │   └── user.py          # User Schema
│
├── cli/                     # CLI 模块
│   ├── __init__.py
│   ├── commands.py          # CLI 命令
│   └── main.py              # 入口（llm-wiki.py）
│
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── yaml_parser.py       # YAML 解析
│   ├── constants.py         # 常量定义
│   └── helpers.py           # 辅助函数
│
└── tests/                   # 测试模块
    ├── __init__.py
    ├── test_storage.py
    ├── test_atoms.py
    ├── test_search.py
    └── ...
```

### 3.2 模块职责

| 模块 | 职责 | 核心类 |
|------|------|--------|
| `storage_adapter` | 统一存储接口，屏蔽 file/db 模式差异 | `StorageAdapter`, `FileAdapter`, `DBAdapter` |
| `atom_manager` | 知识原子 CRUD、类型检测、元数据管理 | `AtomManager` |
| `kb_manager` | 多级知识库管理、权限分配、聚合查询 | `KnowledgeBaseManager` |
| `version_manager` | 版本快照、对比、回滚、清理策略 | `VersionManager` |
| `search` | 全文检索、向量搜索、高亮、联想 | `SearchEngine` |
| `auth_manager` | SSO 登录、JWT 验证、权限校验 | `AuthManager` |
| `audit_logger` | 不可篡改审计日志、链式哈希 | `AuditLogger` |
| `asset_manager` | 图像上传、存储策略、访问控制 | `AssetManager` |
| `ocr_service` | OCR 识别、本地/云服务切换 | `OCRService` |
| `preview_service` | PDF/Office 在线预览 | `PreviewService` |

### 3.3 模块依赖关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           模块依赖图                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  cli/main.py                                                                 │
│      │                                                                       │
│      └──────────┐                                                           │
│                  │                                                           │
│                  ▼                                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  core/storage_adapter.py                                              │  │
│  │      ├── core/file_adapter.py                                         │  │
│  │      └── core/db_adapter.py                                           │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                  │                                                           │
│                  ├──────────────────┬──────────────────┐                    │
│                  │                  │                  │                    │
│                  ▼                  ▼                  ▼                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  knowledge/     │  │  search/        │  │  auth/          │             │
│  │  atom_manager   │  │  engine         │  │  auth_manager   │             │
│  │  kb_manager     │  │                 │  │                 │             │
│  │  version_mgr    │  │                 │  │                 │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│          │                    │                    │                        │
│          │                    │                    │                        │
│          ▼                    ▼                    ▼                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  security/      │  │  assets/        │  │  services/      │             │
│  │  audit_logger   │  │  asset_manager  │  │  ocr_service    │             │
│  │  encryption     │  │                 │  │  preview_svc    │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│          │                    │                    │                        │
│          └────────────────────┴────────────────────┘                        │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  PostgreSQL / 文件系统                                                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 四、数据架构

### 4.1 PostgreSQL 表结构设计

#### 4.1.1 知识库表

```sql
-- 知识库表
CREATE TABLE knowledge_bases (
  id SERIAL PRIMARY KEY,
  name VARCHAR(256) NOT NULL,
  slug VARCHAR(128) UNIQUE NOT NULL,  -- URL 友好标识
  type VARCHAR(32) NOT NULL,           -- personal/department/project/company
  description TEXT,
  
  -- 关联关系
  organization_id INTEGER REFERENCES organizations(id),
  owner_id VARCHAR(64) REFERENCES users(id),
  department_id INTEGER REFERENCES departments(id),
  project_id INTEGER REFERENCES projects(id),
  
  -- 权限配置
  visibility VARCHAR(32) DEFAULT 'private',  -- private/team/public
  is_aggregated BOOLEAN DEFAULT false,
  
  -- 存储模式
  storage_mode VARCHAR(16) DEFAULT 'db',     -- file/db
  
  -- 元数据
  settings JSONB DEFAULT '{}',               -- 知识库配置
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  -- 索引优化
  created_by VARCHAR(64) REFERENCES users(id)
);

CREATE INDEX idx_kb_type ON knowledge_bases(type);
CREATE INDEX idx_kb_owner ON knowledge_bases(owner_id);
CREATE INDEX idx_kb_org ON knowledge_bases(organization_id);
```

#### 4.1.2 知识库成员表

```sql
-- 知识库成员表
CREATE TABLE kb_members (
  kb_id INTEGER REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  user_id VARCHAR(64) REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(32) NOT NULL DEFAULT 'reader',  -- owner/editor/reader
  permissions JSONB DEFAULT '{}',              -- 扩展权限
  
  joined_at TIMESTAMP DEFAULT NOW(),
  invited_by VARCHAR(64) REFERENCES users(id),
  
  PRIMARY KEY (kb_id, user_id)
);

CREATE INDEX idx_kb_members_user ON kb_members(user_id);
CREATE INDEX idx_kb_members_role ON kb_members(role);
```

#### 4.1.3 知识库聚合表

```sql
-- 知识库聚合表（公司知识库包含哪些子知识库）
CREATE TABLE kb_aggregations (
  parent_kb_id INTEGER REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  child_kb_id INTEGER REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  include_private BOOLEAN DEFAULT false,
  priority INTEGER DEFAULT 0,
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  PRIMARY KEY (parent_kb_id, child_kb_id),
  CONSTRAINT no_self_aggregate CHECK (parent_kb_id != child_kb_id)
);
```

#### 4.1.4 知识原子表

```sql
-- 知识原子表
CREATE TABLE atoms (
  id SERIAL PRIMARY KEY,
  kb_id INTEGER REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  
  -- 基本字段
  title VARCHAR(512) NOT NULL,
  slug VARCHAR(256),                       -- URL 友好标识
  type VARCHAR(32) NOT NULL,               -- method/fact/definition/opinion/data/question/reference
  description TEXT,
  content TEXT NOT NULL,
  
  -- 元数据（JSONB 存储 frontmatter）
  metadata JSONB DEFAULT '{}',             -- tags, confidence, source, etc.
  
  -- 关联关系
  author_id VARCHAR(64) REFERENCES users(id),
  
  -- 向量嵌入（pgvector）
  embedding VECTOR(384),                   -- all-MiniLM-L6-v2 维度
  
  -- 全文索引
  content_tsv TSVECTOR GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(content, '')), 'C')
  ) STORED,
  
  -- 状态
  status VARCHAR(16) DEFAULT 'active',     -- active/archived/draft
  is_locked BOOLEAN DEFAULT false,         -- 编辑锁
  
  -- 时间戳
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  -- 完整性约束
  CONSTRAINT valid_type CHECK (type IN ('method', 'fact', 'definition', 'opinion', 'data', 'question', 'reference'))
);

-- 索引
CREATE INDEX idx_atoms_kb ON atoms(kb_id);
CREATE INDEX idx_atoms_type ON atoms(type);
CREATE INDEX idx_atoms_author ON atoms(author_id);
CREATE INDEX idx_atoms_status ON atoms(status);
CREATE INDEX idx_atoms_created ON atoms(created_at DESC);
CREATE INDEX idx_atoms_metadata ON atoms USING GIN(metadata);
CREATE INDEX idx_atoms_tsv ON atoms USING GIN(content_tsv);
CREATE INDEX idx_atoms_embedding ON atoms USING ivfflat (embedding vector_cosine_ops);

-- 触发器：更新 updated_at
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER atoms_updated_at
  BEFORE UPDATE ON atoms
  FOR EACH ROW EXECUTE FUNCTION update_timestamp();
```

#### 4.1.5 知识原子链接表

```sql
-- 知识原子链接表
CREATE TABLE atom_links (
  id SERIAL PRIMARY KEY,
  source_atom_id INTEGER REFERENCES atoms(id) ON DELETE CASCADE,
  target_atom_id INTEGER REFERENCES atoms(id) ON DELETE CASCADE,
  link_type VARCHAR(32) DEFAULT 'reference',  -- reference/citation/seealso
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(source_atom_id, target_atom_id, link_type)
);

CREATE INDEX idx_atom_links_source ON atom_links(source_atom_id);
CREATE INDEX idx_atom_links_target ON atom_links(target_atom_id);
```

#### 4.1.6 版本快照表

```sql
-- 版本快照表
CREATE TABLE atom_versions (
  id SERIAL PRIMARY KEY,
  atom_id INTEGER REFERENCES atoms(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL,
  
  -- 快照内容
  title VARCHAR(512),
  content TEXT,
  metadata JSONB,
  assets_snapshot JSONB,                   -- 关联图像资产快照
  
  -- 版本信息
  author_id VARCHAR(64) REFERENCES users(id),
  change_summary VARCHAR(512),             -- 变更摘要
  change_type VARCHAR(16) DEFAULT 'update', -- create/update/delete
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(atom_id, version_number)
);

CREATE INDEX idx_atom_versions_atom ON atom_versions(atom_id);
CREATE INDEX idx_atom_versions_number ON atom_versions(atom_id, version_number DESC);
```

#### 4.1.7 图像资产表

```sql
-- 图像资产表
CREATE TABLE atom_assets (
  id SERIAL PRIMARY KEY,
  atom_id INTEGER REFERENCES atoms(id) ON DELETE CASCADE,
  
  -- 基本信息
  filename VARCHAR(255) NOT NULL,
  original_filename VARCHAR(255),
  mime_type VARCHAR(64) NOT NULL,
  size INTEGER NOT NULL,                   -- 字节数
  
  -- 存储方式
  storage_type VARCHAR(16) NOT NULL,       -- inline/external
  
  -- 内联存储（小文件）
  data BYTEA,
  
  -- 外部存储（大文件）
  storage_path VARCHAR(512),
  storage_provider VARCHAR(32),            -- local/minio/s3/oss
  
  -- 校验
  checksum VARCHAR(64),                    -- SHA256
  
  -- 元数据
  width INTEGER,
  height INTEGER,
  thumbnail BYTEA,                         -- 缩略图
  
  created_at TIMESTAMP DEFAULT NOW(),
  created_by VARCHAR(64) REFERENCES users(id),
  
  CONSTRAINT check_storage_consistency CHECK (
    (storage_type = 'inline' AND data IS NOT NULL) OR
    (storage_type = 'external' AND storage_path IS NOT NULL)
  )
);

CREATE INDEX idx_atom_assets_atom ON atom_assets(atom_id);
CREATE INDEX idx_atom_assets_type ON atom_assets(storage_type);
```

#### 4.1.8 用户表

```sql
-- 用户表（与 Casdoor 同步）
CREATE TABLE users (
  id VARCHAR(64) PRIMARY KEY,              -- Casdoor 用户 ID
  name VARCHAR(256) NOT NULL,
  email VARCHAR(256),
  phone VARCHAR(32),
  
  -- 加密字段
  phone_encrypted BYTEA,                   -- pgcrypto 加密
  email_encrypted BYTEA,
  
  -- 组织关系
  organization_id INTEGER REFERENCES organizations(id),
  department_id INTEGER REFERENCES departments(id),
  
  -- 角色
  global_role VARCHAR(32) DEFAULT 'user',  -- admin/user
  
  -- 状态
  status VARCHAR(16) DEFAULT 'active',
  
  -- 时间戳
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_login_at TIMESTAMP
);

CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_users_dept ON users(department_id);
```

#### 4.1.9 审计日志表

```sql
-- 审计日志表（不可篡改）
CREATE TABLE audit_logs (
  id BIGSERIAL PRIMARY KEY,
  
  -- 操作信息
  user_id VARCHAR(64) REFERENCES users(id),
  action VARCHAR(32) NOT NULL,             -- create/update/delete/view/export/import
  resource_type VARCHAR(32),               -- atom/kb/user/asset
  resource_id VARCHAR(64),
  
  -- 详细信息
  details JSONB,                           -- 操作详情
  ip_address VARCHAR(45),
  user_agent TEXT,
  
  -- 链式哈希（不可篡改）
  record_hash VARCHAR(64) NOT NULL,        -- 当前记录哈希
  prev_hash VARCHAR(64),                   -- 前一条记录哈希
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  -- 禁止 UPDATE 和 DELETE
  CONSTRAINT audit_readonly CHECK (true)
);

-- 禁止修改和删除
REVOKE UPDATE, DELETE ON audit_logs FROM PUBLIC;

-- 索引
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_time ON audit_logs(created_at DESC);
```

#### 4.1.10 组织架构表

```sql
-- 组织表
CREATE TABLE organizations (
  id SERIAL PRIMARY KEY,
  name VARCHAR(256) NOT NULL,
  slug VARCHAR(128) UNIQUE NOT NULL,
  
  settings JSONB DEFAULT '{}',
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 部门表
CREATE TABLE departments (
  id SERIAL PRIMARY KEY,
  org_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
  name VARCHAR(256) NOT NULL,
  slug VARCHAR(128),
  
  parent_id INTEGER REFERENCES departments(id),
  
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dept_org ON departments(org_id);
CREATE INDEX idx_dept_parent ON departments(parent_id);

-- 项目表（临时知识库）
CREATE TABLE projects (
  id SERIAL PRIMARY KEY,
  org_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
  name VARCHAR(256) NOT NULL,
  slug VARCHAR(128),
  
  start_date DATE,
  end_date DATE,
  
  status VARCHAR(16) DEFAULT 'active',
  
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_project_org ON projects(org_id);
```

### 4.2 行级安全策略（RLS）

#### 4.2.1 RLS 辅助函数定义

```sql
-- 创建用户上下文设置函数
CREATE OR REPLACE FUNCTION set_current_user_id(user_id VARCHAR(64))
RETURNS VOID AS $$
BEGIN
  -- 使用会话级配置参数存储当前用户 ID
  -- 生命周期：当前连接（或直到下一个 SET）
  PERFORM set_config('app.current_user_id', user_id, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 获取当前用户 ID
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS VARCHAR(64) AS $$
BEGIN
  RETURN current_setting('app.current_user_id', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 获取当前用户部门 ID（可选）
CREATE OR REPLACE FUNCTION current_user_department_id()
RETURNS INTEGER AS $$
DECLARE
  dept_id INTEGER;
BEGIN
  SELECT department_id INTO dept_id
  FROM users
  WHERE id = current_user_id();
  RETURN dept_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 4.2.2 连接池兼容方案

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RLS 连接池集成方案                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  方案 A：中间件注入（推荐）                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  # FastAPI 中间件                                                      │  │
│  │  @app.middleware("http")                                               │  │
│  │  async def rls_context_middleware(request, call_next):                 │  │
│  │      user_id = request.state.user.id  # 从 JWT 解析                    │  │
│  │                                                                        │  │
│  │      async with get_db_connection() as conn:                          │  │
│  │          # 在事务开始时设置用户上下文                                  │  │
│  │          await conn.execute(                                          │  │
│  │              text("SELECT set_current_user_id(:uid)"),                 │  │
│  │              {"uid": user_id}                                         │  │
│  │          )                                                             │  │
│  │          request.state.db_conn = conn                                 │  │
│  │          response = await call_next(request)                           │  │
│  │          return response                                               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  方案 B：asyncpg 连接池配置                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  # 每个请求开始时调用                                                  │  │
│  │  async def setup_rls_context(conn: asyncpg.Connection, user_id: str):  │  │
│  │      await conn.execute(                                              │  │
│  │          "SELECT set_current_user_id($1)", user_id                    │  │
│  │      )                                                                │  │
│  │                                                                        │  │
│  │  # 注意：asyncpg 连接池场景                                            │  │
│  │  # - SET LOCAL 仅在当前事务有效                                        │  │
│  │  # - 连接归还池后，配置参数自动清除                                    │  │
│  │  # - 使用 set_config(..., false) 设置会话级参数                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  关键注意事项：                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  1. SET LOCAL 生命周期 = 当前事务，事务结束后自动清除                  │  │
│  │  2. set_config(..., false) 生命周期 = 当前连接，连接归还池后清除      │  │
│  │  3. 连接池场景：每个请求必须重新设置用户上下文                        │  │
│  │  4. 异步框架：确保在同一个连接上执行 SET 和后续查询                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 4.2.3 RLS 策略定义

```sql
-- 启用 RLS
ALTER TABLE atoms ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_bases ENABLE ROW LEVEL SECURITY;

-- 知识库访问策略
CREATE POLICY kb_access_policy ON knowledge_bases
  FOR ALL
  USING (
    -- Owner 完全访问
    owner_id = current_user_id() OR
    -- 成员访问
    EXISTS (
      SELECT 1 FROM kb_members
      WHERE kb_id = id AND user_id = current_user_id()
    ) OR
    -- 公开知识库
    visibility = 'public'
  );

-- 知识原子访问策略
CREATE POLICY atom_access_policy ON atoms
  FOR ALL
  USING (
    -- 知识库成员可访问
    EXISTS (
      SELECT 1 FROM kb_members m
      JOIN knowledge_bases kb ON m.kb_id = kb.id
      WHERE kb.id = kb_id AND m.user_id = current_user_id()
    ) OR
    -- 公开知识库的原子
    EXISTS (
      SELECT 1 FROM knowledge_bases kb
      WHERE kb.id = kb_id AND kb.visibility = 'public'
    )
  );

-- 编辑权限策略
CREATE POLICY atom_edit_policy ON atoms
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM kb_members m
      WHERE m.kb_id = kb_id
        AND m.user_id = current_user_id()
        AND m.role IN ('owner', 'editor')
    )
  );

-- 删除权限策略
CREATE POLICY atom_delete_policy ON atoms
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM kb_members m
      WHERE m.kb_id = kb_id
        AND m.user_id = current_user_id()
        AND m.role = 'owner'
    )
  );
```

### 4.3 数据流设计

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据流设计                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  知识原子创建流程                                                      │  │
│  │                                                                       │  │
│  │  用户创建 → AtomManager.create_atom()                                 │  │
│  │      │                                                                │  │
│  │      ├── 1. 类型检测（自动/手动）                                     │  │
│  │      ├── 2. 元数据提取（title, tags, description）                    │  │
│  │      ├── 3. 权限校验（RLS + Casbin）                                  │  │
│  │      ├── 4. 存储写入（PostgreSQL / 文件）                             │  │
│  │      ├── 5. 向量嵌入生成（可选）                                      │  │
│  │      ├── 6. 全文索引更新                                              │  │
│  │      ├── 7. 版本快照创建（version_number = 1）                        │  │
│  │      ├── 8. 审计日志记录（链式哈希）                                  │  │
│  │      └─────────────────────────────────────────────────────────────────│  │
│  │      └── 返回 atom_id                                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  知识原子查询流程                                                      │  │
│  │                                                                       │  │
│  │  用户查询 → SearchEngine.search()                                     │  │
│  │      │                                                                │  │
│  │      ├── 关键词搜索路径：                                              │  │
│  │      │   ├── 1. tsvector 全文检索                                    │  │
│  │      │   ├── 2. 权限过滤（RLS）                                      │  │
│  │      │   ├── 3. 结果排序（权重）                                     │  │
│  │      │   └── 4. 高亮生成                                              │  │
│  │      │                                                                │  │
│  │      ├── 语义搜索路径：                                                │  │
│  │      │   ├── 1. 向量嵌入生成（query）                                │  │
│  │      │   ├── 2. pgvector 相似度计算                                  │  │
│  │      │   ├── 3. 权限过滤                                              │  │
│  │      │   └── 4. 结果排序（similarity）                               │  │
│  │      │                                                                │  │
│  │      ├── 聚合搜索路径（公司知识库）：                                  │  │
│  │      │   ├── 1. 查询 kb_aggregations                                 │  │
│  │      │   ├── 2. 聚合多个子知识库                                     │  │
│  │      │   ├── 3. 权限过滤                                              │  │
│  │      │   └── 4. 结果合并                                              │  │
│  │      └─────────────────────────────────────────────────────────────────│  │
│  │      └── 返回结果列表                                                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  版本管理流程                                                          │  │
│  │                                                                       │  │
│  │  更新触发 → VersionManager.auto_version()                             │  │
│  │      │                                                                │  │
│  │      ├── 1. 获取当前版本号                                            │  │
│  │      ├── 2. 创建新版本快照                                            │  │
│  │      │   ├── title, content, metadata                                │  │
│  │      │   ├── assets_snapshot                                          │  │
│  │      │   └── change_summary                                           │  │
│  │      ├── 3. 更新原子主记录                                            │  │
│  │      ├── 4. 审计日志记录                                              │  │
│  │      └─────────────────────────────────────────────────────────────────│  │
│  │                                                                       │  │
│  │  版本清理 → VersionManager.cleanup()                                  │  │
│  │      │                                                                │  │
│  │      ├── 1. 检查版本数量                                              │  │
│  │      ├── 2. 应用清理策略                                              │  │
│  │      │   ├── 最近 10 版本：全部保留                                  │  │
│  │      │   ├── 10-30 版本：每天保留 1 个                               │  │
│  │      │   ├── 30-90 版本：每周保留 1 个                               │  │
│  │      │   ├── 90+ 版本：每月保留 1 个                                 │  │
│  │      │   └── 最大 100 版本                                           │  │
│  │      ├── 3. 删除过期版本                                              │  │
│  │      └─────────────────────────────────────────────────────────────────│  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.4 缓存策略

| 数据类型 | 缓存策略 | 缓存位置 | TTL |
|----------|----------|----------|-----|
| 知识原子列表 | 知识库级缓存 | Redis（可选） | 5 分钟 |
| 知识原子详情 | 原子级缓存 | Redis | 10 分钟 |
| 向量嵌入 | 无缓存（计算成本高） | - | - |
| 用户权限 | 权限缓存 | Redis | 30 分钟 |
| 知识库元数据 | 配置缓存 | Redis | 1 小时 |
| 搜索结果 | 查询缓存 | Redis | 1 分钟 |

---

## 五、接口设计

### 5.1 API 接口规范

#### 5.1.1 RESTful API 设计

```
基础 URL: /api/v1

认证方式:
  - Bearer Token（JWT）
  - Casdoor OIDC

响应格式:
  {
    "success": boolean,
    "data": object | array,
    "error": { "code": string, "message": string },
    "meta": { "total": number, "page": number, "limit": number }
  }
```

#### 5.1.2 知识原子 API

```
POST   /api/v1/kb/{kb_id}/atoms              # 创建原子
GET    /api/v1/kb/{kb_id}/atoms              # 列表查询
GET    /api/v1/kb/{kb_id}/atoms/{atom_id}    # 详情查询
PUT    /api/v1/kb/{kb_id}/atoms/{atom_id}    # 更新原子
DELETE /api/v1/kb/{kb_id}/atoms/{atom_id}    # 删除原子

GET    /api/v1/kb/{kb_id}/atoms/{atom_id}/versions      # 版本列表
GET    /api/v1/kb/{kb_id}/atoms/{atom_id}/versions/{v}  # 版本详情
POST   /api/v1/kb/{kb_id}/atoms/{atom_id}/rollback/{v}  # 版本回滚

GET    /api/v1/kb/{kb_id}/atoms/{atom_id}/links         # 链接关系
POST   /api/v1/kb/{kb_id}/atoms/{atom_id}/links         # 创建链接
DELETE /api/v1/kb/{kb_id}/atoms/{atom_id}/links/{id}    # 删除链接
```

#### 5.1.3 知识库 API

```
POST   /api/v1/kb                            # 创建知识库
GET    /api/v1/kb                            # 知识库列表
GET    /api/v1/kb/{kb_id}                    # 知识库详情
PUT    /api/v1/kb/{kb_id}                    # 更新知识库
DELETE /api/v1/kb/{kb_id}                    # 删除知识库

GET    /api/v1/kb/{kb_id}/members            # 成员列表
POST   /api/v1/kb/{kb_id}/members            # 添加成员
PUT    /api/v1/kb/{kb_id}/members/{user_id}  # 更新成员角色
DELETE /api/v1/kb/{kb_id}/members/{user_id}  # 移除成员

POST   /api/v1/kb/{kb_id}/aggregations       # 添加聚合
DELETE /api/v1/kb/{kb_id}/aggregations/{id}  # 移除聚合

POST   /api/v1/kb/{kb_id}/export             # 导出 Bundle
POST   /api/v1/kb/import                     # 导入 Bundle
```

#### 5.1.4 搜索 API

```
GET    /api/v1/search                        # 全文搜索
  ?q={query}                                 # 搜索词
  &kb={kb_id}                                # 知识库（可选，聚合搜索）
  &type={type}                               # 类型过滤
  &limit={n}                                 # 结果数量
  &offset={n}                                # 分页偏移
  &semantic=true                             # 语义搜索
  &highlight=true                            # 高亮结果

GET    /api/v1/suggestions                   # 搜索建议
  ?q={query}                                 # 输入前缀
  &kb={kb_id}                                # 知识库

GET    /api/v1/search/history                # 搜索历史
```

#### 5.1.5 认证 API

```
GET    /api/v1/auth/providers                # SSO 提供商列表
GET    /api/v1/auth/login/{provider}         # 登录跳转
POST   /api/v1/auth/callback                 # OIDC 回调
POST   /api/v1/auth/refresh                  # Token 刷新
POST   /api/v1/auth/logout                   # 登出

GET    /api/v1/user/me                       # 当前用户信息
GET    /api/v1/user/me/kbs                   # 用户知识库列表
```

#### 5.1.6 资产 API

```
POST   /api/v1/assets                        # 上传图像
GET    /api/v1/assets/{asset_id}             # 获取图像
DELETE /api/v1/assets/{asset_id}             # 删除图像

POST   /api/v1/ocr                           # OCR 识别
POST   /api/v1/preview/{asset_id}            # 在线预览
```

### 5.2 CLI 命令设计

```bash
# 知识库管理
llm-wiki init <path> [--mode file|db] [--type personal|department|project]
llm-wiki register <path> --name <name>
llm-wiki list [--scope all|global|project]
llm-wiki use <name>
llm-wiki info <name>

# 知识原子操作
llm-wiki ingest <source> --kb <kb> [--type <type>]
llm-wiki query <query> --kb <kb> [--semantic] [--highlight]
llm-wiki capture <text> --kb <kb>
llm-wiki lint <kb> [--okf-check]

# 知识库操作
llm-wiki index <kb>
llm-wiki export <kb> -o <bundle> [--include-children]
llm-wiki import <bundle> -o <path>
llm-wiki visualize <kb>

# 企业功能
llm-wiki member add <kb> <user> --role <role>
llm-wiki member remove <kb> <user>
llm-wiki version list <kb> <atom>
llm-wiki version rollback <kb> <atom> <version>
llm-wiki audit <kb> [--action <action>]

# 模式切换
llm-wiki migrate <kb> --to db|file
llm-wiki sync <kb> --direction db->file|file->db
```

### 5.3 StorageAdapter 统一接口

```python
class StorageAdapter(ABC):
    """统一存储接口，屏蔽 file/db 模式差异"""
    
    @abstractmethod
    async def create_atom(
        self,
        kb_id: str,
        atom: AtomCreate
    ) -> Atom:
        """创建知识原子"""
        pass
    
    @abstractmethod
    async def get_atom(
        self,
        kb_id: str,
        atom_id: str
    ) -> Optional[Atom]:
        """获取知识原子"""
        pass
    
    @abstractmethod
    async def update_atom(
        self,
        kb_id: str,
        atom_id: str,
        atom: AtomUpdate
    ) -> Atom:
        """更新知识原子"""
        pass
    
    @abstractmethod
    async def delete_atom(
        self,
        kb_id: str,
        atom_id: str
    ) -> bool:
        """删除知识原子"""
        pass
    
    @abstractmethod
    async def search(
        self,
        kb_id: str,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        offset: int = 0
    ) -> SearchResult:
        """搜索知识原子"""
        pass
    
    @abstractmethod
    async def export(
        self,
        kb_id: str,
        include_versions: bool = False
    ) -> OKFBundle:
        """导出 OKF Bundle"""
        pass
    
    @abstractmethod
    async def import(
        self,
        kb_id: str,
        bundle: OKFBundle
    ) -> ImportResult:
        """导入 OKF Bundle"""
        pass


class FileAdapter(StorageAdapter):
    """文件存储适配器（file_mode）"""
    
    def __init__(self, kb_path: str):
        self.kb_path = kb_path
        self.atoms_dir = os.path.join(kb_path, 'atoms')
    
    # 实现所有方法，操作 atoms/ 目录中的 Markdown 文件


class DBAdapter(StorageAdapter):
    """数据库存储适配器（db_mode）"""
    
    def __init__(self, db_url: str, kb_id: int):
        self.db_url = db_url
        self.kb_id = kb_id
    
    # 实现所有方法，操作 PostgreSQL


def get_adapter(kb_path: str) -> StorageAdapter:
    """根据知识库元数据选择适配器"""
    meta = load_kb_meta(kb_path)
    if meta.get('mode') == 'file':
        return FileAdapter(kb_path)
    else:
        return DBAdapter(get_db_url(), meta.get('kb_id'))
```

---

## 六、安全架构

### 6.1 认证授权架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           认证授权架构                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  用户登录流程                                                          │  │
│  │                                                                       │  │
│  │  1. 用户点击"企业微信/钉钉/飞书登录"                                   │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  2. 跳转到 Casdoor                                                     │  │
│  │     ├── Casdoor 处理 OAuth/OIDC                                       │  │
│  │     ├── 与企业 IM Provider 交互                                       │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  3. Casdoor 返回 JWT Token                                             │  │
│  │     ├── Token 包含：user_id, roles, org_id                            │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  4. llm-wiki 验证 Token                                                │  │
│  │     ├── JWT 签名验证                                                   │  │
│  │     ├── 用户信息同步到 users 表                                       │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  5. 创建会话                                                           │  │
│  │     ├── Session 存储在 Redis（可选）                                  │  │
│  │     ├── 返回 Access Token + Refresh Token                             │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  权限校验流程                                                          │  │
│  │                                                                       │  │
│  │  API 请求 → AuthMiddleware                                            │  │
│  │      │                                                                │  │
│  │      ├── 1. Token 验证（JWT）                                         │  │
│  │      ├── 2. 用户信息提取                                              │  │
│  │      ├── 3. Casbin 权限查询                                           │  │
│  │      │   ├── 查询 policy：user, kb, role                              │  │
│  │      │   ├── 检查资源权限：r.sub == user AND r.obj == kb              │  │
│  │      ├── 4. PostgreSQL RLS 过滤                                       │  │
│  │      │   ├── SET LOCAL current_user_id = user_id                     │  │
│  │      │   ├── 查询自动应用 RLS 策略                                    │  │
│  │      └─────────────────────────────────────────────────────────────────│  │
│  │      ├── 权限通过 → 执行业务逻辑                                      │  │
│  │      ├── 权限拒绝 → 返回 403                                          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  权限模型（RBAC + ABAC）：                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Casbin Policy 定义：                                                  │  │
│  │                                                                       │  │
│  │  p = sub, obj, act                                                    │  │
│  │                                                                       │  │
│  │  # 知识库角色                                                          │  │
│  │  p, alice, kb_1, owner    # alice 是 kb_1 的 owner                   │  │
│  │  p, bob, kb_1, editor     # bob 是 kb_1 的 editor                    │  │
│  │  p, charlie, kb_1, reader # charlie 是 kb_1 的 reader                │  │
│  │                                                                       │  │
│  │  # 角色权限定义                                                        │  │
│  │  g, owner, kb_admin      # owner 继承 kb_admin                       │  │
│  │  g, editor, kb_editor    # editor 继承 kb_editor                     │  │
│  │  g, reader, kb_reader    # reader 继承 kb_reader                     │  │
│  │                                                                       │  │
│  │  # 权限动作                                                            │  │
│  │  p, kb_admin, *, *        # kb_admin 可做所有操作                     │  │
│  │  p, kb_editor, atom, write # kb_editor 可写 atom                     │  │
│  │  p, kb_editor, atom, read  # kb_editor 可读 atom                     │  │
│  │  p, kb_reader, atom, read   # kb_reader 仅可读                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 数据加密架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据加密架构                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  加密层级：                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  传输层加密（TLS 1.3）                                          │ │  │
│  │  │  ├── HTTPS 强制启用                                             │ │  │
│  │  │  ├── Nginx 配置 SSL/TLS                                         │ │  │
│  │  │  ├── 证书：Let's Encrypt 或商业证书                             │ │  │
│  │  │  └─────────────────────────────────────────────────────────────────│ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  数据库层加密（pgcrypto）                                       │ │  │
│  │  │  ├── 启用扩展：CREATE EXTENSION pgcrypto;                       │ │  │
│  │  │  ├── 加密字段：                                                 │ │  │
│  │  │  │   ├── users.phone_encrypted                                 │ │  │
│  │  │  │   ├── users.email_encrypted                                 │ │  │
│  │  │  │   └───────────────────────────────────────────────────────────│ │  │
│  │  │  ├── 加密函数：                                                 │ │  │
│  │  │  │   ├── pgp_sym_encrypt(data, key)                            │ │  │
│  │  │  │   ├── pgp_sym_decrypt(data, key)                            │ │  │
│  │  │  │   └───────────────────────────────────────────────────────────│ │  │
│  │  │  └─────────────────────────────────────────────────────────────────│ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  应用层加密（Python cryptography）                              │ │  │
│  │  │  ├── 特别敏感数据：                                             │ │  │
│  │  │  │   ├── API 密钥                                               │ │  │
│  │  │  │   ├── 系统配置                                               │ │  │
│  │  │  │   └───────────────────────────────────────────────────────────│ │  │
│  │  │  ├── 加密算法：AES-256-GCM                                      │ │  │
│  │  │  ├── 密钥来源：环境变量 / Vault                                 │ │  │
│  │  │  └─────────────────────────────────────────────────────────────────│ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  密钥管理：                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  主密钥（Master Key）：                                               │  │
│  │  ├── 存储：环境变量 LLM_WIKI_MASTER_KEY                              │  │
│  │  ├── 格式：256-bit 随机字符串                                        │  │
│  │  ├── 轮换：每年一次                                                   │  │
│  │                                                                       │  │
│  │  数据加密密钥（DEK）：                                                 │  │
│  │  ├── 由主密钥加密存储                                                │  │
│  │  ├── 每个 kb 可有独立密钥                                            │  │
│  │                                                                       │  │
│  │  密钥轮换流程：                                                       │  │
│  │  ├── 1. 生成新主密钥                                                 │  │
│  │  ├── 2. 用旧密钥解密所有 DEK                                        │  │
│  │  ├── 3. 用新密钥重新加密 DEK                                        │  │
│  │  ├── 4. 更新环境变量                                                 │  │
│  │  ├── 5. 保留旧密钥用于历史数据解密                                  │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 审计日志架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           审计日志架构                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  链式哈希设计（并发安全版本）：                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  插入流程（使用数据库序列锁防止竞态）：                                │  │
│  │                                                                       │  │
│  │  方案 A：PostgreSQL 存储过程（推荐）                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  CREATE OR REPLACE FUNCTION insert_audit_log(                   │ │  │
│  │  │      p_user_id VARCHAR(64),                                      │ │  │
│  │  │      p_action VARCHAR(32),                                       │ │  │
│  │  │      p_resource_type VARCHAR(32),                                │ │  │
│  │  │      p_resource_id VARCHAR(64),                                  │ │  │
│  │  │      p_details JSONB,                                            │ │  │
│  │  │      p_ip_address VARCHAR(45)                                    │ │  │
│  │  │  ) RETURNS BIGINT AS $$                                          │ │  │
│  │  │  DECLARE                                                         │ │  │
│  │  │      v_prev_hash VARCHAR(64);                                    │ │  │
│  │  │      v_record_hash VARCHAR(64);                                  │ │  │
│  │  │      v_new_id BIGINT;                                            │ │  │
│  │  │  BEGIN                                                           │ │  │
│  │  │      -- 使用序列锁：获取前一条记录的哈希                          │ │  │
│  │  │      SELECT record_hash INTO v_prev_hash                          │ │  │
│  │  │      FROM audit_logs                                             │ │  │
│  │  │      ORDER BY id DESC                                            │ │  │
│  │  │      LIMIT 1                                                     │ │  │
│  │  │      FOR UPDATE;  -- 关键：行级锁防止并发竞态                    │ │  │
│  │  │                                                                  │ │  │
│  │  │      IF v_prev_hash IS NULL THEN                                 │ │  │
│  │  │          v_prev_hash := '0';                                     │ │  │
│  │  │      END IF;                                                     │ │  │
│  │  │                                                                  │ │  │
│  │  │      -- 计算当前记录哈希                                          │ │  │
│  │  │      v_record_hash := encode(sha256(                             │ │  │
│  │  │          convert_to(                                             │ │  │
│  │  │              p_user_id || '|' || p_action || '|' ||             │ │  │
│  │  │              p_resource_type || '|' || p_resource_id || '|' ||   │ │  │
│  │  │              p_details::text || '|' || p_ip_address || '|' ||    │ │  │
│  │  │              v_prev_hash, 'UTF8'                                  │ │  │
│  │  │          )                                                       │ │  │
│  │  │      ), 'hex');                                                  │ │  │
│  │  │                                                                  │ │  │
│  │  │      -- 插入新记录                                                │ │  │
│  │  │      INSERT INTO audit_logs (                                    │ │  │
│  │  │          user_id, action, resource_type, resource_id,            │ │  │
│  │  │          details, ip_address, prev_hash, record_hash             │ │  │
│  │  │      ) VALUES (                                                   │ │  │
│  │  │          p_user_id, p_action, p_resource_type, p_resource_id,    │ │  │
│  │  │          p_details, p_ip_address, v_prev_hash, v_record_hash     │ │  │
│  │  │      ) RETURNING id INTO v_new_id;                               │ │  │
│  │  │                                                                  │ │  │
│  │  │      RETURN v_new_id;                                            │ │  │
│  │  │  END;                                                            │ │  │
│  │  │  $$ LANGUAGE plpgsql SECURITY DEFINER;                           │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  方案 B：应用层锁（备选）                                             │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  # Python 实现（使用 Redis 分布式锁）                            │ │  │
│  │  │  import redis                                                    │ │  │
│  │  │  import hashlib                                                  │ │  │
│  │  │                                                                  │ │  │
│  │  │  async def insert_audit_log(action, details):                    │ │  │
│  │  │      r = redis.Redis()                                           │ │  │
│  │  │      lock = r.lock('audit_log_insert', timeout=5)                │ │  │
│  │  │      try:                                                        │ │  │
│  │  │          with lock:  # 分布式锁防止并发                          │ │  │
│  │  │              prev = await get_last_audit_log()                   │ │  │
│  │  │              prev_hash = prev.record_hash if prev else '0'       │ │  │
│  │  │              record_hash = calculate_hash(...)                    │ │  │
│  │  │              await insert_to_db(record_hash, prev_hash)          │ │  │
│  │  │      except LockError:                                          │ │  │
│  │  │          # 锁超时，重试或记录错误                                │ │  │
│  │  │          raise AuditLogInsertError("Lock timeout")              │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  方案对比：                                                            │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  方案        │ 优点                    │ 缺点                   │ │  │
│  │  │  ─────────────────────────────────────────────────────────────  │ │  │
│  │  │  存储过程    │ 无外部依赖、原子性强    │ 数据库层逻辑           │ │  │
│  │  │  Redis 锁   │ 灵活、跨服务            │ 引入 Redis 依赖        │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  完整性验证：                                                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  def verify_audit_chain():                                            │  │
│  │      logs = SELECT * FROM audit_logs ORDER BY id                      │  │
│  │                                                                       │  │
│  │      for i, log in enumerate(logs):                                   │  │
│  │          # 1. 重新计算哈希                                            │  │
│  │          expected_hash = sha256(...)                                  │  │
│  │                                                                       │  │
│  │          # 2. 验证哈希一致性                                          │  │
│  │          if log.record_hash != expected_hash:                         │  │
│  │              return False, f"Log {i} tampered"                        │  │
│  │                                                                       │  │
│  │          # 3. 验证链完整性                                            │  │
│  │          if i > 0:                                                    │  │
│  │              if log.prev_hash != logs[i-1].record_hash:               │  │
│  │                  return False, f"Log {i} chain broken"                │  │
│  │                                                                       │  │
│  │      return True, "Audit chain valid"                                 │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  分区策略（性能优化）：                                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  -- 按时间范围分区（推荐）                                            │  │
│  │  CREATE TABLE audit_logs (                                           │  │
│  │      id BIGSERIAL,                                                   │  │
│  │      user_id VARCHAR(64) NOT NULL,                                   │  │
│  │      action VARCHAR(32) NOT NULL,                                    │  │
│  │      resource_type VARCHAR(32),                                       │  │
│  │      resource_id VARCHAR(64),                                         │  │
│  │      details JSONB,                                                   │  │
│  │      ip_address VARCHAR(45),                                          │  │
│  │      created_at TIMESTAMP DEFAULT NOW(),                              │  │
│  │      record_hash VARCHAR(64) NOT NULL,                                │  │
│  │      prev_hash VARCHAR(64),                                           │  │
│  │      PRIMARY KEY (id, created_at)                                     │  │
│  │  ) PARTITION BY RANGE (created_at);                                  │  │
│  │                                                                       │  │
│  │  -- 创建月度分区                                                       │  │
│  │  CREATE TABLE audit_logs_2026_01                                     │  │
│  │      PARTITION OF audit_logs                                         │  │
│  │      FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');               │  │
│  │                                                                       │  │
│  │  CREATE TABLE audit_logs_2026_02                                     │  │
│  │      PARTITION OF audit_logs                                         │  │
│  │      FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');               │  │
│  │                                                                       │  │
│  │  -- 自动分区管理函数                                                   │  │
│  │  CREATE FUNCTION create_audit_partition()                            │  │
│  │  RETURNS VOID AS $$                                                  │  │
│  │  BEGIN                                                               │  │
│  │      -- 自动创建下月分区                                              │  │
│  │      -- 定时任务每月执行一次                                          │  │
│  │  END;                                                                │  │
│  │  $$ LANGUAGE plpgsql;                                                │  │
│  │                                                                       │  │
│  │  -- 分区优势：                                                        │  │
│  │  -- 1. 查询性能：仅扫描相关分区                                       │  │
│  │  -- 2. 维护效率：删除旧分区 = DROP TABLE（秒级）                      │  │
│  │  -- 3. 备份灵活：按分区独立备份                                       │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  数据库保护：                                                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  -- 禁止 UPDATE 和 DELETE                                             │  │
│  │  REVOKE UPDATE, DELETE ON audit_logs FROM PUBLIC;                     │  │
│  │                                                                       │  │
│  │  -- 仅允许 INSERT                                                      │  │
│  │  GRANT INSERT ON audit_logs TO llm_wiki_app;                          │  │
│  │                                                                       │  │
│  │  -- 管理员仅可查询                                                     │  │
│  │  GRANT SELECT ON audit_logs TO llm_wiki_admin;                        │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  日志保留策略：                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  -- 保留 180 天以上                                                    │  │
│  │  -- 归档到冷存储（可选）                                               │  │
│  │                                                                       │  │
│  │  CREATE FUNCTION archive_old_audit_logs()                            │  │
│  │  -- 180 天前的日志导出到冷存储                                        │  │
│  │  -- 不删除，仅标记为已归档                                             │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 七、部署架构

### 7.1 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 主服务
  llm-wiki:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgres://llmwiki:${DB_PASSWORD}@postgres:5432/llmwiki
      - CASDOOR_URL=http://casdoor:8000
      - CASDOOR_CLIENT_ID=${CASDOOR_CLIENT_ID}
      - CASDOOR_CLIENT_SECRET=${CASDOOR_CLIENT_SECRET}
      - LLM_WIKI_MASTER_KEY=${MASTER_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - casdoor
      - redis
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=llmwiki
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=llmwiki
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U llmwiki"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis（可选，缓存）
  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data

  # Casdoor SSO
  casdoor:
    image: casbin/casdoor:latest
    ports:
      - "8001:8000"
    environment:
      - driverName=postgres
      - dataSourceName=postgres://casdoor:${CASDOOR_DB_PASSWORD}@postgres:5432/casdoor
    depends_on:
      - postgres
    volumes:
      - ./casdoor/conf:/conf

  # OCR 服务（可选）
  paddleocr:
    image: paddleocr/paddleocr:latest
    ports:
      - "8868:8868"
    environment:
      - USE_GPU=false
    deploy:
      resources:
        limits:
          memory: 8G
    profiles:
      - ocr

  # 预览服务（可选）
  kkfileview:
    image: keking/kkfileview:latest
    ports:
      - "8012:8012"
    profiles:
      - preview

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - llm-wiki

volumes:
  pgdata:
  redisdata:
```

### 7.2 服务编排

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           服务编排                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  核心服务（必选）：                                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │  llm-wiki    │  │  postgres    │  │  casdoor     │                 │  │
│  │  │  主服务      │  │  数据库      │  │  SSO         │                 │  │
│  │  │  :8000       │  │  :5432       │  │  :8001       │                 │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                 │  │
│  │         │                 │                 │                          │  │
│  │         └─────────────────┼─────────────────┘                          │  │
│  │                           │                                              │  │
│  │                           ▼                                              │  │
│  │  ┌──────────────┐  ┌──────────────┐                                     │  │
│  │  │  redis       │  │  nginx       │                                     │  │
│  │  │  缓存        │  │  反向代理    │                                     │  │
│  │  │  :6379       │  │  :80/443     │                                     │  │
│  │  └──────────────┘  └──────────────┘                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  扩展服务（可选）：                                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────┐  ┌──────────────┐                                     │  │
│  │  │  paddleocr   │  │  kkfileview  │                                     │  │
│  │  │  OCR 服务    │  │  预览服务    │                                     │  │
│  │  │  :8868       │  │  :8012       │                                     │  │
│  │  │  4核8G       │  │  2核4G       │                                     │  │
│  │  └──────────────┘  └──────────────┘                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  启动命令：                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  # 核心服务                                                             │  │
│  │  docker-compose up -d                                                  │  │
│  │                                                                       │  │
│  │  # 含 OCR                                                              │  │
│  │  docker-compose --profile ocr up -d                                   │  │
│  │                                                                       │  │
│  │  # 含预览                                                              │  │
│  │  docker-compose --profile preview up -d                               │  │
│  │                                                                       │  │
│  │  # 全服务                                                              │  │
│  │  docker-compose --profile ocr --profile preview up -d                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  资源需求：                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  服务          CPU    内存    说明                                    │  │
│  │  ────────────────────────────────────────────────────────────────────│  │
│  │  llm-wiki      2核    4G      主服务                                  │  │
│  │  postgres      2核    4G      数据库                                  │  │
│  │  casdoor       1核    2G      SSO                                     │  │
│  │  redis         1核    1G      缓存                                    │  │
│  │  nginx         1核    1G      反向代理                                │  │
│  │  paddleocr     4核    8G      OCR（可选）                             │  │
│  │  kkfileview    2核    4G      预览（可选）                             │  │
│  │  ────────────────────────────────────────────────────────────────────│  │
│  │  核心总计      7核    12G                                             │  │
│  │  全服务总计    13核   24G                                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 高可用方案

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           高可用方案                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PostgreSQL 主从复制：                                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  ┌──────────────┐      ┌──────────────┐                              │  │
│  │  │  Primary     │─────▶│  Standby     │                              │  │
│  │  │  :5432       │      │  :5433       │                              │  │
│  │  │              │      │              │                              │  │
│  │  │  写操作      │      │  读操作      │                              │  │
│  │  │              │      │  同步复制    │                              │  │
│  │  └──────────────┘      └──────────────┘                              │  │
│  │                                                                       │  │
│  │  配置：                                                                │  │
│  │  - synchronous_commit = on                                            │  │
│  │  - max_wal_senders = 3                                                │  │
│  │  - hot_standby = on                                                   │  │
│  │                                                                       │  │
│  │  PgBouncer 连接池：                                                    │  │
│  │  - 读写分离：写→Primary，读→Standby                                   │  │
│  │  - 连接池管理                                                         │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  应用层高可用：                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │  llm-wiki-1  │  │  llm-wiki-2  │  │  llm-wiki-3  │                 │  │
│  │  │  :8001       │  │  :8002       │  │  :8003       │                 │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                 │  │
│  │         │                 │                 │                          │  │
│  │         └─────────────────┼─────────────────┘                          │  │
│  │                           │                                              │  │
│  │                           ▼                                              │  │
│  │  ┌──────────────┐                                                     │  │
│  │  │  Nginx       │                                                     │  │
│  │  │  负载均衡    │                                                     │  │
│  │  │              │                                                     │  │
│  │  │  upstream {  │                                                     │  │
│  │  │    server 1; │                                                     │  │
│  │  │    server 2; │                                                     │  │
│  │  │    server 3; │                                                     │  │
│  │  │  }           │                                                     │  │
│  │  └──────────────┘                                                     │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  故障转移：                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  PostgreSQL 自动故障转移：                                            │  │
│  │  - 使用 Patroni 或 pg_auto_failover                                  │  │
│  │  - Primary 故障 → 自动选举新 Primary                                 │  │
│  │  - 恢复后自动加入集群                                                 │  │
│  │                                                                       │  │
│  │  应用层故障转移：                                                      │  │
│  │  - Nginx 健康检查                                                     │  │
│  │  - 实例故障 → 自动剔除                                                │  │
│  │  - 恢复后自动加入                                                     │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 八、迁移策略

### 8.1 SQLite → PostgreSQL 迁移

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据库迁移策略                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  阶段 1：数据库连接层抽象                                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  当前代码：                                                            │  │
│  │  - registry.py → ~/.llm-wiki/registry.json                           │  │
│  │  - validator.py → 读取 Markdown 文件                                  │  │
│  │  - querier.py → FTS5 全文检索                                         │  │
│  │  - semantic.py → Chromadb 向量检索                                    │  │
│  │                                                                       │  │
│  │  改造目标：                                                            │  │
│  │  - 创建 DatabaseManager 抽象类                                        │  │
│  │  - SQLiteManager（兼容旧数据）                                        │  │
│  │  - PostgreSQLManager（新数据）                                        │  │
│  │  - 配置项：storage.type = sqlite | postgres                          │  │
│  │                                                                       │  │
│  │  改造范围：                                                            │  │
│  │  ├── lib/core/db_manager.py         # 数据库管理抽象                  │  │
│  │  ├── lib/core/sqlite_manager.py    # SQLite 实现                     │  │
│  │  ├── lib/core/postgres_manager.py  # PostgreSQL 实现                 │  │
│  │  └── lib/search/engine.py          # 搜索引擎适配                     │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  阶段 2：数据迁移                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  迁移脚本：migrate_sqlite_to_postgres.py                              │  │
│  │                                                                       │  │
│  │  步骤：                                                                │  │
│  │  1. 创建 PostgreSQL 表结构                                            │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  2. 读取 SQLite 数据                                                  │  │
│  │     ├── registry.json → knowledge_bases 表                           │  │
│  │     ├── atoms/*.md → atoms 表                                        │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  3. 数据转换                                                          │  │
│  │     ├── frontmatter → JSONB metadata                                 │  │
│  │     ├── tags → metadata.tags                                         │  │
│  │     ├── links → atom_links 表                                        │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  4. 生成向量嵌入                                                       │  │
│  │     ├── 内容 → embedding（pgvector）                                 │  │
│  │     ├── Chromadb 数据 → PostgreSQL                                   │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  5. 建立索引                                                          │  │
│  │     ├── 全文索引（tsvector）                                          │  │
│  │     ├── 向量索引（ivfflat）                                           │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  6. 验证数据                                                          │  │
│  │     ├── 记录数对比                                                    │  │
│  │     ├── 内容一致性检查                                                │  │
│  │     ├── 搜索功能验证                                                  │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  7. 切换存储模式                                                       │  │
│  │     ├── kb_meta.mode = 'db'                                          │  │
│  │     ├── config.storage.type = 'postgres'                             │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  迁移命令：                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  llm-wiki migrate <kb> --to postgres                                  │  │
│  │     --keep-files    # 保留 Markdown 文件（推荐）                      │  │
│  │     --validate      # 迁移后验证                                      │  │
│  │     --dry-run       # 演练模式                                        │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 file_mode → db_mode 迁移

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           模式迁移策略                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  file_mode → db_mode：                                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  适用场景：                                                            │  │
│  │  - 个人知识库升级为团队知识库                                          │  │
│  │  - 需要多用户协作                                                      │  │
│  │  - 需要版本管理                                                        │  │
│  │                                                                       │  │
│  │  迁移步骤：                                                            │  │
│  │  1. 创建 PostgreSQL 知识库                                            │  │
│  │     ├── 指定 type（personal/department/project）                      │  │
│  │     ├── 指定 visibility                                               │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  2. 导入 atoms/ 目录                                                  │  │
│  │     ├── 扫描所有 Markdown 文件                                        │  │
│  │     ├── 提取 frontmatter                                              │  │
│  │     ├── 插入 PostgreSQL                                               │  │
│  │     ├── 生成向量嵌入                                                   │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  3. 导入 raw/ 目录                                                    │  │
│  │     ├── 原始资料作为参考                                              │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  4. 导入 views/ 目录                                                  │  │
│  │     ├── 可视化输出保持                                                │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  5. 更新元数据                                                        │  │
│  │     ├── kb_meta.mode = 'db'                                          │  │
│  │     ├── kb_meta.kb_id = postgres_kb_id                               │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  6. 保留 atoms/ 目录（兼容 Obsidian）                                 │  │
│  │     ├── 可配置自动同步                                                │  │
│  │     ├── 或手动导出更新                                                │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  db_mode → file_mode：                                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  适用场景：                                                            │  │
│  │  - 团队知识库导出为个人知识库                                          │  │
│  │  - 知识库迁移到其他系统                                                │  │
│  │  - Git 版本管理                                                        │  │
│  │                                                                       │  │
│  │  导出步骤：                                                            │  │
│  │  1. 导出 OKF Bundle                                                   │  │
│  │     llm-wiki export <kb> -o bundle.tar.gz                             │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  2. 解压到目标目录                                                    │  │
│  │     tar -xzf bundle.tar.gz -C /target/path                            │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  3. 更新元数据                                                        │  │
│  │     kb_meta.mode = 'file'                                            │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │     ↓                                                                 │  │
│  │  4. 验证 OKF 兼容性                                                   │  │
│  │     llm-wiki lint /target/path --okf-check                            │  │
│  │     └──────────────────────────────────────────────────────────────────│  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 九、测试策略

### 9.1 测试框架选择

| 层级 | 框架 | 用途 |
|------|------|------|
| **单元测试** | pytest | 核心逻辑测试 |
| **集成测试** | pytest + asyncpg | 数据库交互测试 |
| **E2E 测试** | Playwright | 用户流程测试 |
| **性能测试** | locust | 负载测试 |

### 9.2 测试覆盖率目标

| 模块 | 覆盖率目标 | 说明 |
|------|:----------:|------|
| `core/` | 90%+ | 核心模块，必须高覆盖 |
| `knowledge/` | 85%+ | 业务逻辑 |
| `auth/` | 95%+ | 安全相关，关键路径 |
| `search/` | 80%+ | 搜索功能 |
| `web/` | 75%+ | API 端点 |

### 9.3 测试分类

```
tests/
├── unit/                    # 单元测试
│   ├── test_storage_adapter.py
│   ├── test_atom_manager.py
│   ├── test_kb_manager.py
│   └── test_version_manager.py
│
├── integration/             # 集成测试
│   ├── test_db_operations.py
│   ├── test_rls_policies.py
│   ├── test_audit_logs.py
│   └── test_search_engine.py
│
├── e2e/                     # E2E 测试
│   ├── test_user_flows.py
│   ├── test_kb_management.py
│   └── test_search.py
│
└── fixtures/                # 测试数据
    ├── sample_atoms.json
    └── test_users.json
```

### 9.4 关键测试场景

| 场景 | 测试类型 | 验证点 |
|------|----------|--------|
| 知识原子 CRUD | 单元 + 集成 | 正常流程、权限拒绝、并发冲突 |
| 版本管理 | 集成 | 版本创建、回滚、清理策略 |
| RLS 策略 | 集成 | 数据隔离、权限边界 |
| 审计日志 | 集成 | 链式哈希、并发插入 |
| 搜索功能 | 集成 + E2E | 全文检索、语义搜索、聚合查询 |
| SSO 登录 | E2E | 企业微信/钉钉/飞书登录流程 |

---

## 十、错误处理策略

### 10.1 错误码体系

```python
class ErrorCode(Enum):
    # 通用错误 (1xxx)
    UNKNOWN_ERROR = 1000
    INVALID_REQUEST = 1001
    RESOURCE_NOT_FOUND = 1002
    
    # 认证错误 (2xxx)
    UNAUTHORIZED = 2000
    TOKEN_EXPIRED = 2001
    TOKEN_INVALID = 2002
    PERMISSION_DENIED = 2003
    
    # 业务错误 (3xxx)
    KB_NOT_FOUND = 3000
    ATOM_NOT_FOUND = 3001
    VERSION_NOT_FOUND = 3002
    DUPLICATE_SLUG = 3003
    
    # 数据库错误 (4xxx)
    DB_CONNECTION_ERROR = 4000
    DB_QUERY_ERROR = 4001
    DB_CONSTRAINT_ERROR = 4002
    
    # 外部服务错误 (5xxx)
    SSO_ERROR = 5000
    OCR_ERROR = 5001
    PREVIEW_ERROR = 5002
```

### 10.2 API 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "用户无权访问该知识库",
    "details": {
      "user_id": "user_123",
      "kb_id": 456,
      "required_role": "reader"
    }
  },
  "request_id": "req_abc123"
}
```

### 10.3 重试策略

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           重试策略                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  数据库操作：                                                                 │
│  ├── 最大重试次数：3                                                         │
│  ├── 初始延迟：100ms                                                         │
│  ├── 延迟增长：指数退避（100ms → 200ms → 400ms）                            │
│  └── 可重试错误：连接超时、死锁、序列化失败                                  │
│                                                                              │
│  外部服务（SSO/OCR）：                                                        │
│  ├── 最大重试次数：2                                                         │
│  ├── 初始延迟：500ms                                                         │
│  ├── 延迟增长：固定间隔                                                      │
│  └── 超时时间：10s                                                           │
│                                                                              │
│  不可重试错误：                                                               │
│  ├── 认证失败（401）                                                         │
│  ├── 权限不足（403）                                                         │
│  ├── 资源不存在（404）                                                       │
│  └── 参数错误（400）                                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.4 超时配置

| 操作类型 | 超时时间 | 说明 |
|----------|----------|------|
| API 请求 | 30s | 标准 API |
| 向量嵌入 | 60s | 嵌入生成 |
| OKF 导出 | 120s | 大知识库导出 |
| OKF 导入 | 180s | 批量导入 |
| OCR 识别 | 60s | 文档识别 |

---

## 十一、性能优化策略

### 11.1 向量索引选择理由

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        pgvector 索引选择说明                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  选择 ivfflat 索引的理由：                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  1. 知识库规模预期                                                    │  │
│  │     ├── 个人知识库：<10,000 atoms                                     │  │
│  │     ├── 部门知识库：<100,000 atoms                                    │  │
│  │     ├── 企业级：<1,000,000 atoms                                      │  │
│  │     └── ivfflat 适合 <1M 规模                                         │  │
│  │                                                                       │  │
│  │  2. ivfflat vs HNSW 对比                                             │  │
│  │     ┌─────────────────────────────────────────────────────────────┐   │  │
│  │     │  特性        │ ivfflat         │ HNSW                      │   │  │
│  │     │  ─────────────────────────────────────────────────────────  │   │  │
│  │     │  构建速度    │ 快              │ 慢                        │   │  │
│  │     │  查询延迟    │ 低              │ 更低                      │   │  │
│  │     │  内存占用    │ 低              │ 高                        │   │  │
│  │     │  准确率      │ 高（可调）      │ 很高                      │   │  │
│  │     │  适用规模    │ <1M             │ >1M                       │   │  │
│  │     └─────────────────────────────────────────────────────────────┘   │  │
│  │                                                                       │  │
│  │  3. 迁移路径                                                          │  │
│  │     └── 规模超过 500K atoms 时，评估迁移到 HNSW                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 向量嵌入生成策略

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        向量嵌入性能策略                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  嵌入生成策略：                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  1. 触发时机                                                           │  │
│  │     ├── 创建原子：同步生成（阻塞）                                    │  │
│  │     ├── 更新原子：异步生成（非阻塞）                                  │  │
│  │     └── 批量导入：批量异步生成                                       │  │
│  │                                                                       │  │
│  │  2. 模型选择                                                           │  │
│  │     ├── 默认：all-MiniLM-L6-v2（384 维，平衡性能/准确率）              │  │
│  │     ├── 可选：BGE-small-zh（中文优化）                                │  │
│  │     └── 企业级：BGE-large-zh（更高准确率，1024 维）                   │  │
│  │                                                                       │  │
│  │  3. 批量生成                                                           │  │
│  │     ├── 批量大小：100 个/批                                           │  │
│  │     ├── 并发控制：最多 4 个并发批次                                   │  │
│  │     └── 进度追踪：记录到导入任务状态                                 │  │
│  │                                                                       │  │
│  │  4. 异步任务队列                                                       │  │
│  │     ├── Celery（推荐，生产环境）                                      │  │
│  │     ├── asyncio.Queue（开发环境）                                     │  │
│  │     └── 失败重试：最多 3 次                                           │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.3 N+1 查询防护

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           N+1 查询防护策略                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  问题场景：                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  # 错误：N+1 查询                                                     │  │
│  │  atoms = SELECT * FROM atoms WHERE kb_id = 123                        │  │
│  │  for atom in atoms:                                                   │  │
│  │      author = SELECT * FROM users WHERE id = atom.author_id  # N 次   │  │
│  │      kb = SELECT * FROM knowledge_bases WHERE id = atom.kb_id        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  解决方案：                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  # 方案 A：JOIN 查询                                                  │  │
│  │  SELECT a.*, u.name as author_name, kb.name as kb_name                │  │
│  │  FROM atoms a                                                         │  │
│  │  LEFT JOIN users u ON a.author_id = u.id                              │  │
│  │  LEFT JOIN knowledge_bases kb ON a.kb_id = kb.id                      │  │
│  │  WHERE a.kb_id = 123                                                  │  │
│  │                                                                       │  │
│  │  # 方案 B：预加载（SQLAlchemy）                                       │  │
│  │  from sqlalchemy.orm import joinedload                                 │  │
│  │  query = session.query(Atom).options(                                │  │
│  │      joinedload(Atom.author),                                         │  │
│  │      joinedload(Atom.knowledge_base)                                  │  │
│  │  ).filter(Atom.kb_id == 123).all()                                    │  │
│  │                                                                       │  │
│  │  # 方案 C：批量查询                                                    │  │
│  │  atoms = SELECT * FROM atoms WHERE kb_id = 123                        │  │
│  │  author_ids = [a.author_id for a in atoms]                            │  │
│  │  authors = SELECT * FROM users WHERE id IN (author_ids)  # 1 次       │  │
│  │  author_map = {a.id: a for a in authors}                              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  强制规则：                                                                   │
│  ├── 列表查询必须使用 JOIN 或预加载                                          │
│  ├── 详情查询可使用延迟加载                                                  │
│  └── 代码审查必须检查 N+1 问题                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.4 Redis 缓存配置

```yaml
# Redis 缓存配置
redis:
  host: redis
  port: 6379
  db: 0
  
  # 连接池
  pool:
    max_connections: 50
    timeout: 5
    
  # 缓存键前缀
  key_prefix: "llmwiki:"
  
  # 缓存策略
  strategies:
    # 知识原子详情
    atom_detail:
      ttl: 600  # 10 分钟
      key_pattern: "atom:{atom_id}"
      
    # 知识库列表
    kb_list:
      ttl: 300  # 5 分钟
      key_pattern: "kb:user:{user_id}:list"
      
    # 用户权限
    user_permissions:
      ttl: 1800  # 30 分钟
      key_pattern: "perm:user:{user_id}"
      
    # 搜索结果
    search_results:
      ttl: 60  # 1 分钟
      key_pattern: "search:{query_hash}"
      
  # 失效策略
  invalidation:
    - 原子更新时清除 atom_detail 和搜索缓存
    - 知识库变更时清除 kb_list 缓存
    - 权限变更时清除 user_permissions 缓存
```

---

## 十二、Dockerfile 示例

### 12.1 主服务 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN useradd -m -u 1000 llmwiki && \
    chown -R llmwiki:llmwiki /app
USER llmwiki

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "lib.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 12.2 多阶段构建（优化版）

```dockerfile
# Dockerfile.multistage
# 阶段 1：构建
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 阶段 2：运行
FROM python:3.11-slim

WORKDIR /app

# 仅复制必要的运行时依赖
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 Python 包
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY --chown=1000:1000 . .

# 创建非 root 用户
RUN useradd -m -u 1000 llmwiki && \
    chown -R llmwiki:llmwiki /app
USER llmwiki

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "lib.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 十三、附录

### 13.1 技术决策记录

| 决策 ID | 决策项 | 选项 | 选定方案 | 理由 | 时间 |
|---------|--------|------|----------|------|------|
| D001 | 数据库 | SQLite/MySQL/MongoDB/PostgreSQL | PostgreSQL | 一库多能（JSONB + pgvector + RLS） | 2026-06-21 |
| D002 | SSO | Keycloak/Casdoor/Dex | Casdoor | 国产开源、企业 IM 内置 | 2026-06-21 |
| D003 | 版本管理 | Git-style/Snapshot | Snapshot | 无外部依赖、数据统一 | 2026-06-21 |
| D004 | 容器化 | Docker/K8s | Docker Compose | 起步简单、可扩展 | 2026-06-21 |
| D005 | OCR | 云服务/PaddleOCR | 分阶段 | 云服务→本地部署 | 2026-06-21 |
| D006 | 预览 | Office Online/KKFileView | KKFileView | 信创友好 | 2026-06-21 |
| D007 | 加密 | 传输层/数据库层/应用层 | 分层加密 | pgcrypto + 应用层 | 2026-06-21 |
| D008 | 实时协同 | CRDT/OT | 不执行 | 非知识库核心场景 | 2026-06-21 |

### 13.2 词汇表

| 术语 | 定义 |
|------|------|
| OKF | Open Knowledge Format，开放知识格式规范 |
| Atom | 知识原子，最小知识单元 |
| KB | Knowledge Base，知识库 |
| RLS | Row-Level Security，行级安全策略 |
| pgvector | PostgreSQL 向量索引扩展 |
| JSONB | PostgreSQL JSON 二进制存储格式 |
| tsvector | PostgreSQL 全文索引数据类型 |
| Casdoor | 国产开源 SSO 服务 |
| Casbin | 国产开源权限管理框架 |
| Snapshot | 版本快照方案 |
| file_mode | 文件存储模式（Skill 模式） |
| db_mode | 数据库存储模式（企业模式） |

### 13.3 参考资料

- [OKF v0.1 规范](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
- [PostgreSQL 官方文档](https://www.postgresql.org/docs/15/)
- [pgvector 文档](https://github.com/pgvector/pgvector)
- [Casdoor 文档](https://casdoor.org/)
- [Casbin 文档](https://casbin.org/)
- [PaddleOCR 文档](https://github.com/PaddlePaddle/PaddleOCR)
- [KKFileView 文档](https://github.com/keking/kkFileView)

---

**文档创建时间**：2026-06-21
**最后更新时间**：2026-06-21
**版本**：v1.1

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.1 | 2026-06-21 | 补充 RLS 函数设计、审计日志并发安全、分区策略；新增测试策略、错误处理、性能优化、Dockerfile 章节 |
| v1.0 | 2026-06-21 | 初始版本 |