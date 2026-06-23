---
name: PLAN-004-phase3
description: PLAN-004 Phase 3 — API 层改造（web_server 从文件 I/O 切换到 StorageInterface）
status: draft
created: 2026-06-23
phase: 3
priority: P0
estimated_duration: 4-5 天
depends_on:
  - PLAN-004 Phase 2 (已完成)
---

# PLAN-004 Phase 3：API 层改造

> **创建时间**：2026-06-23
> **状态**：草稿
> **预计周期**：4-5 天
> **优先级**：P0

---

## 一、需求重述

将 `web_server.py` 从直接文件 I/O 切换到 `StorageInterface`，实现双模式透明切换：
- **file_mode**：行为与当前完全一致（Markdown 文件 + frontmatter）
- **db_mode**：通过 StorageInterface 代理到 PostgreSQL

核心问题：web_server.py 的 50+ 个 API 端点全部基于 `self.kb_dir`（Path）做文件操作，需要逐步替换为 `self.storage`（StorageInterface）。

---

## 二、当前状态

| 组件 | 现状 | 问题 |
|------|------|------|
| `UnifiedWebServer.__init__` | 接收 `kb_dir: Path` | 无 StorageInterface 注入 |
| `UnifiedRequestHandler` | 类属性 `kb_dir: Path` | 所有端点通过 `self.kb_dir` 做文件 I/O |
| `_load_atoms()` | `rglob('*.md')` 遍历文件 | 无法适配 db_mode |
| `_resolve_atom_path()` | 文件路径解析 | 无法适配 db_mode |
| `_api_atom_list/get/create/update` | 直接读写 Markdown | 需要切换到 StorageInterface |
| `_api_search` | 使用 KnowledgeQuerier | db_mode 应使用 PostgreSQLSearchEngine |
| `_api_batch_tag` | 修改 frontmatter | db_mode 应使用 tags/atom_tags 表 |
| `_api_stats/audit` | 文件系统扫描 | db_mode 应查询数据库 |
| OCR/Preview API | 不存在 | 需要新建 |

---

## 三、实施步骤

### Step 3.1：构造函数注入 StorageInterface（1 天）

**目标**：`UnifiedWebServer` 和 `UnifiedRequestHandler` 支持 StorageInterface 注入，保持向后兼容。

**修改文件**：`lib/web_server.py`

**具体改动**：

1. `UnifiedWebServer.__init__` 新增 `storage: Optional[StorageInterface] = None` 参数
   - 如果传入 storage → 使用它（db_mode 或外部注入）
   - 如果未传入 → 自动创建 FileSystemStorage(kb_dir)（file_mode 兼容）

2. `UnifiedRequestHandler` 新增类属性 `storage: StorageInterface`
   - `_create_handler()` 中将 storage 传递给 Handler 类

3. 添加 `storage_mode` 属性（`self.storage.mode`），供路由和日志使用

4. **不修改任何现有端点行为**——此步骤仅注入依赖，确保现有功能不变

**验收**：现有 863 个测试全部通过，file_mode 行为不变

---

### Step 3.2：改造核心 CRUD 端点（1.5 天）

**目标**：原子列表/详情/创建/更新端点切换到 StorageInterface

**修改文件**：`lib/web_server.py`

**改造方法**：

| 端点 | 当前实现 | 改造后 |
|------|---------|--------|
| `_api_atom_list` | `_load_atoms()` (rglob) | `self.storage.list_atoms(kb_id)` |
| `_api_atom_get` | 读文件 + 解析 frontmatter | `self.storage.get_atom(atom_id)` |
| `_api_atom_create` | 写 Markdown 文件 | `self.storage.create_atom(atom_data)` |
| `_api_atom_update` | 读-改-写 Markdown | `self.storage.update_atom(atom_id, data)` |

**关键兼容处理**：

- `_load_atoms()` 保留为 file_mode 的备用方法（当 storage.mode == 'file' 且需要特殊 frontmatter 解析时）
- `_resolve_atom_path()` 仅在 file_mode 下使用
- db_mode 下 atom_id 是数字，file_mode 下是路径字符串——需要统一处理
- 响应格式保持一致（id, path, frontmatter, content, body, tags）

**验收**：file_mode 和 db_mode 下的 CRUD 端点返回一致格式

---

### Step 3.3：改造搜索端点（0.5 天）

**目标**：搜索端点在 db_mode 下使用 PostgreSQLSearchEngine

**修改文件**：`lib/web_server.py`

**改造方法**：

| 端点 | 当前实现 | 改造后 |
|------|---------|--------|
| `_api_search` | `KnowledgeQuerier(kb_dir).query()` | `self.storage.search_atoms(query)` |
| `_api_search_suggest` | `KnowledgeQuerier.get_suggestions()` | `self.storage.search_atoms(prefix)` + 前缀过滤 |

**兼容处理**：
- file_mode：仍使用 KnowledgeQuerier（全文搜索能力弱但兼容）
- db_mode：使用 DatabaseStorage.search_atoms() → PostgreSQLManager.search_atoms()（全文搜索 + pg_trgm）

---

### Step 3.4：添加 OCR API 端点（0.5 天）

**目标**：暴露 OCR 功能为 REST API

**新建文件**：`lib/api/ocr_api.py`

**端点设计**：

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/ocr/submit` | 提交 OCR 任务（上传图片） |
| GET | `/api/ocr/tasks/{task_id}` | 查询 OCR 任务状态/结果 |
| GET | `/api/ocr/assets/{asset_id}` | 查询资产的所有 OCR 结果 |

**集成**：在 `_route_api()` 中添加路由，调用 `self.storage.submit_ocr_task()` 等方法

**file_mode 兼容**：返回 501 Not Implemented（OCR 仅 db_mode 支持）

---

### Step 3.5：添加 Preview API 端点（0.5 天）

**目标**：暴露在线预览功能为 REST API

**新建文件**：`lib/api/preview_api.py`

**端点设计**：

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/preview/{atom_id}` | 获取原子内容的预览 URL |
| GET | `/api/preview/{atom_id}/cache` | 获取预览缓存状态 |

**集成**：在 `_route_api()` 中添加路由，调用 `self.storage.get_preview_url()` 等方法

**file_mode 兼容**：返回 501 Not Implemented

---

### Step 3.6：配置端点 + 辅助端点改造（0.5 天）

**目标**：添加模式切换端点，改造统计/审计/标签端点

**修改文件**：`lib/web_server.py`

**新增端点**：

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/config/mode` | 获取当前存储模式 |
| GET | `/api/config/status` | 获取数据库连接状态（db_mode） |

**改造端点**：

| 端点 | 改造内容 |
|------|---------|
| `_api_stats` | 使用 `self.storage.get_stats()` |
| `_api_audit` | 使用 `self.storage.query_audit()` |
| `_api_batch_tag` | db_mode 使用 `self.storage.add_atom_tag()` |

---

## 四、依赖关系

```
3.1（注入 StorageInterface）
  ├── 3.2（CRUD 改造）
  ├── 3.4（OCR API）  ← 可与 3.2 并行
  └── 3.5（Preview API） ← 可与 3.2 并行
        ↓
      3.3（搜索改造）← 依赖 3.2
        ↓
      3.6（配置 + 辅助）← 依赖 3.2, 3.3
```

---

## 五、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 🔴 web_server 1741 行，改动量大 | HIGH | 分步改造，每步验证测试 |
| 🔴 file_mode 回归（改造后原有功能异常） | HIGH | 每步改造后运行完整测试套件 |
| 🟡 atom_id 格式不统一（数字 vs 路径字符串） | MEDIUM | 统一为字符串，db_mode 内部转换 |
| 🟡 响应格式变化导致前端不兼容 | MEDIUM | 保持响应格式一致，添加兼容字段 |
| 🟢 KnowledgeQuerier 在 db_mode 下无用 | LOW | file_mode 继续使用，db_mode 切换 |

---

## 六、预估工作量

| 步骤 | 编码 | 测试 | 合计 |
|------|------|------|------|
| 3.1 注入 | 0.5 天 | 0.5 天 | 1 天 |
| 3.2 CRUD | 1 天 | 0.5 天 | 1.5 天 |
| 3.3 搜索 | 0.5 天 | 0 天 | 0.5 天 |
| 3.4 OCR API | 0.5 天 | 0 天 | 0.5 天 |
| 3.5 Preview API | 0.5 天 | 0 天 | 0.5 天 |
| 3.6 配置+辅助 | 0.5 天 | 0 天 | 0.5 天 |
| **总计** | **3.5 天** | **1 天** | **4.5 天** |

---

## 七、验证计划

1. **每步完成后**：运行 `python3 -m pytest tests/ -q --ignore=tests/e2e --ignore=tests/search/test_summary.py`
2. **Phase 完成后**：
   - file_mode：启动服务器，curl 测试所有 CRUD 端点
   - db_mode：配置 PostgreSQL，启动服务器，curl 测试所有端点
   - 双模式切换：运行时切换模式，验证行为正确

---

**创建时间**：2026-06-23
**最后更新时间**：2026-06-23
