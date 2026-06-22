---
name: PLAN-003-phase3-ux-enhancement-segments
description: 阶段3 用户体验增强 - 任务组拆分
created: 2026-06-23
plan_ref: PLAN-003-phase3-ux-enhancement
status: ready
---

# PLAN-003 任务组拆分

## 执行顺序

```
Wave 1（基础设施，可并行）
├── TG1: 图像存储基础设施（阶段3.1 后端）
├── TG2: 图像 Web UI（阶段3.1 前端）← 依赖 TG1
└── TG3: 搜索引擎增强（阶段3.2 后端）← 与 TG1 并行
        ↓
Wave 2（OCR + 预览，TG1 完成后可并行）
├── TG4: 搜索 API & UI（阶段3.2 前端）← 依赖 TG3
├── TG5: OCR 基础设施（阶段3.3 后端）← 依赖 TG1
├── TG6: OCR 集成 UI（阶段3.3 前端）← 依赖 TG5
└── TG7: 预览基础设施（阶段3.4 后端）← 依赖阶段1（与 TG5 并行）
        ↓
Wave 3（预览 UI + 移动端，Wave 2 完成后）
├── TG8: 预览 UI（阶段3.4 前端）← 依赖 TG7
└── TG9: 响应式设计（阶段3.5）← 依赖所有前序 TG
        ↓
Wave 4（PWA 支持）
└── TG10: PWA 支持（阶段3.5）← 依赖 TG9
```

---

## Wave 1：基础设施（可并行）

> 前置条件：阶段1 已完成（PostgreSQL + 存储抽象层 + pgvector）
> TG1 和 TG3 无互相依赖，可并行执行。

### 任务组 1：图像存储基础设施

**类型：** 串行（内部子任务有依赖）
**阶段：** 3.1
**前置条件：** 阶段1 已完成
**并行于：** TG3（搜索引擎增强）

#### 子任务

- [x] TG1-001: 扩展 atom_assets 表，增加多尺寸变体支持字段
  - 文件：`lib/db/schema.sql`, `lib/migration/migrate.py`
  - 依赖：无
  - 复杂度：中
  - 说明：在现有 atom_assets 表上增加 variant_type（original/thumbnail/medium/large）、variant_of_id（自引用变体关系）字段；通过 migrate.py 添加增量迁移

- [x] TG1-002: 编写 atom_assets 变体扩展迁移的单元测试
  - 文件：`tests/media/test_schema_migration.py`
  - 依赖：无
  - 复杂度：低
  - 说明：验证迁移前后 schema 一致性，变体字段正确创建

- [x] TG1-003: 实现 ImageStorageService 核心类
  - 文件：`lib/media/image_storage.py`
  - 依赖：TG1-001
  - 复杂度：高
  - 说明：复用 StorageInterface 统一接口，实现图像元数据提取、格式验证、存储路径管理；支持 inline/external 双模式

- [x] TG1-004: 编写 ImageStorageService 单元测试
  - 文件：`tests/media/test_image_storage.py`
  - 依赖：TG1-003
  - 复杂度：中
  - 说明：测试 JPEG/PNG/WebP/GIF 格式验证、元数据提取、存储路径生成、checksum 计算

- [x] TG1-005: 实现缩略图生成模块（Pillow）
  - 文件：`lib/media/thumbnail.py`
  - 依赖：TG1-001（需要变体字段定义）
  - 复杂度：中
  - 说明：生成 3 种尺寸缩略图（small 200x200, medium 600x600, large 1200x1200）；支持 JPEG/PNG/WebP 输出格式

- [x] TG1-006: 编写缩略图生成模块单元测试
  - 文件：`tests/media/test_thumbnail.py`
  - 依赖：TG1-005
  - 复杂度：低
  - 说明：测试各尺寸生成、格式转换、异常图片处理、大文件处理

- [x] TG1-007: 实现图像上传 API
  - 文件：`lib/api/image_api.py`
  - 依赖：TG1-003, TG1-005
  - 复杂度：中
  - 说明：复用 API 框架（参考 kb_management.py），实现上传/删除/列表/详情端点；集成权限中间件

- [x] TG1-008: 编写图像上传 API 集成测试
  - 文件：`tests/media/test_image_api.py`
  - 依赖：TG1-007
  - 复杂度：中
  - 说明：测试上传流程（文件验证 + 元数据提取 + 缩略图生成 + 存储）、权限控制、边界情况

- [x] TG1-009: 图像服务端到端验证
  - 文件：`tests/media/test_image_e2e.py`
  - 依赖：TG1-008
  - 复杂度：中
  - 说明：完整流程测试：上传 -> 缩略图生成 -> 变体查询 -> 删除级联

---

### 任务组 2：图像 Web UI

**类型：** 串行（内部子任务有依赖）
**阶段：** 3.1
**前置条件：** TG1 完成（需要图像上传 API）

#### 子任务

- [ ] TG2-001: 实现图像上传组件（拖拽 + 粘贴）
  - 文件：`views/components/image-upload.html`
  - 依赖：TG1-007（图像上传 API）
  - 复杂度：中
  - 说明：拖拽上传、粘贴上传、格式验证前端预检、上传进度条、多文件批量上传

- [ ] TG2-002: 实现图像库管理页面
  - 文件：`views/media/gallery.html`
  - 依赖：TG1-007（图像列表 API）
  - 复杂度：中
  - 说明：网格/列表视图切换、图像预览、搜索筛选、批量操作；复用 UI 框架（参考 kb-management.html）

- [ ] TG2-003: 实现图像选择器（Markdown 插入）
  - 文件：`views/components/image-picker.html`
  - 依赖：TG2-002
  - 复杂度：中
  - 说明：从图像库选择图像插入 Markdown、支持缩略图预览、自动生成 `![alt](url)` 语法

---

### 任务组 3：搜索引擎增强

**类型：** 串行（内部子任务有依赖）
**阶段：** 3.2
**前置条件：** 阶段1 已完成
**并行于：** TG1（图像存储基础设施）

#### 子任务

- [x] TG3-001: 启用 pg_trgm 扩展 + 中文搜索支持迁移
  - 文件：`lib/db/schema.sql`, `lib/migration/migrate.py`
  - 依赖：无
  - 复杂度：中
  - 说明：在现有 GIN 全文索引基础上，启用 pg_trgm 扩展支持模糊匹配；添加 zhparser 中文分词配置；通过 migrate.py 执行迁移

- [x] TG3-002: 编写中文搜索迁移的单元测试
  - 文件：`tests/search/test_search_migration.py`
  - 依赖：无
  - 复杂度：低
  - 说明：验证 pg_trgm 扩展启用、zhparser 配置、模糊搜索功能

- [x] TG3-003: 增强搜索高亮模块（多字段高亮、自定义片段）
  - 文件：`lib/search/highlight.py`
  - 依赖：无
  - 复杂度：中
  - 说明：增强现有 postgres_search.py 的 search_with_highlights；支持多字段高亮、自定义片段长度、高亮标签配置

- [x] TG3-004: 编写搜索高亮增强单元测试
  - 文件：`tests/search/test_highlight.py`
  - 依赖：TG3-003
  - 复杂度：低
  - 说明：测试多字段高亮、片段截取、中文高亮、边界情况

- [x] TG3-005: 增强搜索联想模块（历史搜索、热门建议）
  - 文件：`lib/search/suggest.py`
  - 依赖：TG3-001（需要 pg_trgm）
  - 复杂度：中
  - 说明：增强现有 postgres_search.py 的 suggest 功能；增加历史搜索记录、热门搜索词统计、模糊匹配建议

- [x] TG3-006: 编写搜索联想增强单元测试
  - 文件：`tests/search/test_suggest.py`
  - 依赖：TG3-005
  - 复杂度：低
  - 说明：测试模糊匹配、热门排序、历史记录、中文联想

- [x] TG3-007: 实现 LLM 摘要生成模块
  - 文件：`lib/search/summary.py`
  - 依赖：无
  - 复杂度：高
  - 说明：调用 LLM 从搜索结果中抽取摘要；支持批量摘要生成、摘要缓存、超时控制

- [x] TG3-008: 编写 LLM 摘要生成单元测试
  - 文件：`tests/search/test_summary.py`
  - 依赖：TG3-007
  - 复杂度：中
  - 说明：测试摘要生成、缓存命中、超时降级、空结果处理；Mock LLM 调用

- [x] TG3-009: 优化向量搜索索引策略和批量嵌入
  - 文件：`lib/search/vector_search.py`
  - 依赖：无
  - 复杂度：中
  - 说明：基于现有 pgvector 集成，优化索引创建时机（写入后异步建索引）；实现批量嵌入接口；优化 HNSW 索引参数

- [x] TG3-010: 编写向量搜索优化单元测试
  - 文件：`tests/search/test_vector_search.py`
  - 依赖：TG3-009
  - 复杂度：低
  - 说明：测试批量嵌入、索引创建时机、搜索精度和性能

---

## Wave 2：OCR + 预览 + 搜索 UI

> 前置条件：TG1 完成（OCR 依赖图像存储）、TG3 完成（搜索 UI 依赖搜索后端）
> TG4、TG5、TG7 可并行执行。

### 任务组 4：搜索 API & UI

**类型：** 串行（内部子任务有依赖）
**阶段：** 3.2
**前置条件：** TG3 完成（搜索引擎增强）

#### 子任务

- [ ] TG4-001: 实现统一搜索 API
  - 文件：`lib/api/search_api.py`
  - 依赖：TG3-003, TG3-005, TG3-007, TG3-009
  - 复杂度：中
  - 说明：统一接口对接现有 SearchEngine；支持关键词搜索、向量搜索、混合搜索；集成高亮、联想、摘要功能

- [ ] TG4-002: 编写搜索 API 集成测试
  - 文件：`tests/search/test_search_api.py`
  - 依赖：TG4-001
  - 复杂度：中
  - 说明：测试搜索端点、参数验证、响应格式、性能（< 200ms）、并发搜索

- [ ] TG4-003: 实现搜索前端组件
  - 文件：`views/components/search-box.html`
  - 依赖：TG4-001
  - 复杂度：高
  - 说明：搜索输入框、联想下拉、高亮预览、搜索历史；防抖处理、键盘快捷键

- [ ] TG4-004: 实现搜索结果页面
  - 文件：`views/search/results.html`
  - 依赖：TG4-003
  - 复杂度：中
  - 说明：结果列表、高亮展示、分页、筛选器、摘要展示；复用 UI 框架

---

### 任务组 5：OCR 基础设施

**类型：** 串行（内部子任务有依赖）
**阶段：** 3.3
**前置条件：** TG1 完成（图像存储）
**并行于：** TG7（预览基础设施）

#### 子任务

- [ ] TG5-001: 设计并创建 OCR 任务表
  - 文件：`lib/db/schema.sql`, `lib/migration/migrate.py`
  - 依赖：TG1-001（需要 atom_assets 变体支持）
  - 复杂度：中
  - 说明：ocr_tasks 表（id, asset_id, status, result, error, retry_count, created_at, updated_at）；关联 atom_assets

- [ ] TG5-002: 编写 OCR 任务表迁移单元测试
  - 文件：`tests/ocr/test_schema_migration.py`
  - 依赖：无
  - 复杂度：低
  - 说明：验证表创建、外键约束、状态枚举

- [ ] TG5-003: 集成 PaddleOCR 核心模块
  - 文件：`lib/ocr/paddle_ocr.py`
  - 依赖：TG5-001
  - 复杂度：高
  - 说明：PaddleOCR 初始化配置、图像预处理、文字识别、结果后处理；支持中英文识别、超时 60s/页

- [ ] TG5-004: 编写 PaddleOCR 集成单元测试
  - 文件：`tests/ocr/test_paddle_ocr.py`
  - 依赖：TG5-003
  - 复杂度：中
  - 说明：Mock PaddleOCR 调用，测试预处理、识别、后处理、超时处理；真实图片集成测试标记为 @pytest.mark.slow

- [ ] TG5-005: 实现 OCR 任务队列（Celery + Redis）
  - 文件：`lib/ocr/task_queue.py`
  - 依赖：TG5-001
  - 复杂度：高
  - 说明：Celery 任务定义、Redis broker 配置、任务调度、重试策略（3 次指数退避）、死信队列、超时处理（整文档 10min）

- [ ] TG5-006: 编写 OCR 任务队列单元测试
  - 文件：`tests/ocr/test_task_queue.py`
  - 依赖：TG5-005
  - 复杂度：中
  - 说明：测试任务提交、重试逻辑、死信队列、超时处理；Mock Celery 和 Redis

- [ ] TG5-007: 实现 OCR 结果存储模块
  - 文件：`lib/ocr/result_store.py`
  - 依赖：TG5-003
  - 复杂度：中
  - 说明：OCR 文本结果存 PostgreSQL、结构化 JSON 存文件系统；复用 StorageInterface

- [ ] TG5-008: 编写 OCR 结果存储单元测试
  - 文件：`tests/ocr/test_result_store.py`
  - 依赖：TG5-007
  - 复杂度：低
  - 说明：测试结果存储、查询、JSON 序列化、大结果处理

- [ ] TG5-009: OCR 基础设施集成验证
  - 文件：`tests/ocr/test_ocr_e2e.py`
  - 依赖：TG5-008
  - 复杂度：中
  - 说明：完整流程：上传图像 -> 创建 OCR 任务 -> 执行识别 -> 结果存储 -> 状态查询

---

### 任务组 6：OCR 集成 UI

**类型：** 串行（内部子任务有依赖）
**阶段：** 3.3
**前置条件：** TG5 完成（OCR 基础设施）

#### 子任务

- [ ] TG6-001: 实现 OCR 上传和状态查询 API
  - 文件：`lib/api/ocr_api.py`
  - 依赖：TG5-005, TG5-007
  - 复杂度：中
  - 说明：上传扫描件创建 OCR 任务、查询任务状态、获取识别结果、重试失败任务

- [ ] TG6-002: 编写 OCR API 集成测试
  - 文件：`tests/ocr/test_ocr_api.py`
  - 依赖：TG6-001
  - 复杂度：中
  - 说明：测试 API 端点、权限控制、任务状态流转、并发请求

- [ ] TG6-003: 实现 OCR 结果查看 UI
  - 文件：`views/ocr/results.html`
  - 依赖：TG6-001
  - 复杂度：中
  - 说明：OCR 结果展示、原文对照、编辑修正、导出文本

- [ ] TG6-004: 实现 OCR 配置管理页面
  - 文件：`views/admin/ocr-settings.html`
  - 依赖：TG6-001
  - 复杂度：低
  - 说明：OCR 引擎配置、并发数设置、超时配置、语言选择

---

### 任务组 7：预览基础设施

**类型：** 串行（内部子任务有依赖）
**阶段：** 3.4
**前置条件：** 阶段1 已完成
**并行于：** TG5（OCR 基础设施）

#### 子任务

- [ ] TG7-001: 设计并创建预览表（previews）
  - 文件：`lib/db/schema.sql`, `lib/migration/migrate.py`
  - 依赖：无
  - 复杂度：中
  - 说明：previews 表（id, atom_id, format, cache_path, cache_expires_at, created_at）；关联 atoms 表

- [ ] TG7-002: 编写预览表迁移单元测试
  - 文件：`tests/preview/test_schema_migration.py`
  - 依赖：无
  - 复杂度：低
  - 说明：验证表创建、外键约束、缓存过期逻辑

- [ ] TG7-003: 集成 PDF.js 前端组件（浏览器端 PDF 渲染）
  - 文件：`views/components/pdf-viewer.html`, `views/lib/pdf.js/`
  - 依赖：无
  - 复杂度：高
  - 说明：PDF.js 为前端组件（非后端服务）；集成 viewer、页面导航、缩放、搜索、文本选择

- [ ] TG7-004: 集成 KKFileView（Office 文档转换服务）
  - 文件：`lib/preview/office_viewer.py`
  - 依赖：TG7-001
  - 复杂度：高
  - 说明：KKFileView 后端服务集成；Office 文档转换、预览 URL 生成、错误处理

- [ ] TG7-005: 实现预览缓存管理模块
  - 文件：`lib/preview/cache_manager.py`
  - 依赖：TG7-001
  - 复杂度：中
  - 说明：Redis + 文件系统双缓存；缓存生命周期管理、自动清理、缓存命中率统计

- [ ] TG7-006: 编写预览基础设施单元测试
  - 文件：`tests/preview/test_preview_infra.py`
  - 依赖：TG7-004, TG7-005
  - 复杂度：中
  - 说明：测试 PDF 渲染、Office 转换、缓存管理、格式支持验证

---

## Wave 3：预览 UI + 响应式设计

> 前置条件：TG7 完成（预览 UI 依赖预览基础设施）、Wave 1+2 的所有 UI 完成后开始响应式设计

### 任务组 8：预览 UI

**类型：** 串行（内部子任务有依赖）
**阶段：** 3.4
**前置条件：** TG7 完成（预览基础设施）

#### 子任务

- [ ] TG8-001: 实现预览 API
  - 文件：`lib/api/preview_api.py`
  - 依赖：TG7-004, TG7-005
  - 复杂度：中
  - 说明：预览请求端点、格式检测、缓存查询与更新、权限控制

- [ ] TG8-002: 编写预览 API 集成测试
  - 文件：`tests/preview/test_preview_api.py`
  - 依赖：TG8-001
  - 复杂度：中
  - 说明：测试各格式预览、缓存行为、权限控制、并发预览

- [ ] TG8-003: 实现 PDF 预览组件
  - 文件：`views/components/pdf-viewer.html`（增强 TG7-003 基础版）
  - 依赖：TG7-003, TG8-001
  - 复杂度：中
  - 说明：在基础 PDF.js 集成上增加：缩略图导航、书签、页面跳转、全屏模式

- [ ] TG8-004: 实现 Office 预览组件
  - 文件：`views/components/office-viewer.html`
  - 依赖：TG7-004, TG8-001
  - 复杂度：中
  - 说明：KKFileView iframe 嵌入、加载状态、错误处理、全屏切换

- [ ] TG8-005: 实现预览管理页面
  - 文件：`views/admin/preview-settings.html`
  - 依赖：TG8-001
  - 复杂度：低
  - 说明：缓存管理、预览服务配置、格式支持开关、统计信息

---

### 任务组 9：响应式设计

**类型：** 串行（内部子任务有依赖）
**阶段：** 3.5
**前置条件：** Wave 1+2+3 的所有 UI 组件完成（TG2, TG4, TG6, TG8）

#### 子任务

- [ ] TG9-001: 实现响应式布局框架
  - 文件：`views/layouts/responsive.html`
  - 依赖：TG2-003, TG4-004, TG6-003, TG8-004
  - 复杂度：高
  - 说明：Tailwind CSS + CSS Grid 响应式框架；断点定义（sm/md/lg/xl）、布局容器、栅格系统

- [ ] TG9-002: 实现移动端导航组件
  - 文件：`views/components/mobile-nav.html`
  - 依赖：TG9-001
  - 复杂度：中
  - 说明：汉堡菜单、底部导航栏、侧滑抽屉、面包屑折叠

- [ ] TG9-003: 实现移动端编辑器
  - 文件：`views/components/mobile-editor.html`
  - 依赖：TG9-001
  - 复杂度：高
  - 说明：触摸友好的 Markdown 编辑器、工具栏简化、手势操作、虚拟键盘适配

- [ ] TG9-004: 实现触摸手势支持
  - 文件：`views/js/touch-gestures.js`
  - 依赖：TG9-001
  - 复杂度：中
  - 说明：滑动翻页、双指缩放、长按操作、下拉刷新；事件委托和防抖

- [ ] TG9-005: 评估现有 JS 库移动端兼容性
  - 文件：`views/lib/`（cytoscape 等）
  - 依赖：无（可提前进行）
  - 复杂度：低
  - 说明：评估 cytoscape-fcose.js、layout-base.js 等库的移动端支持情况；记录兼容性问题和替代方案

---

## Wave 4：PWA 支持

> 前置条件：TG9 完成（响应式设计就绪）

### 任务组 10：PWA 支持

**类型：** 串行（内部子任务有依赖）
**阶段：** 3.5
**前置条件：** TG9 完成（响应式设计）

#### 子任务

- [ ] TG10-001: 实现 Service Worker
  - 文件：`views/js/sw.js`
  - 依赖：TG9-001
  - 复杂度：高
  - 说明：Service Worker 注册和生命周期管理；缓存策略定义、后台同步、请求拦截

- [ ] TG10-002: 实现离线缓存策略
  - 文件：`views/js/offline-cache.js`
  - 依赖：TG10-001
  - 复杂度：高
  - 说明：Cache API + IndexedDB 策略；离线页面缓存、数据同步队列、冲突解决

- [ ] TG10-003: 实现 PWA 安装提示组件
  - 文件：`views/components/pwa-install.html`
  - 依赖：TG10-001
  - 复杂度：低
  - 说明：安装提示横幅、自定义安装按钮、安装状态检测

- [ ] TG10-004: 实现 Push 通知后端服务
  - 文件：`lib/push/notification.py`
  - 依赖：TG10-001
  - 复杂度：高
  - 说明：Web Push 协议实现、订阅管理、通知发送、VAPID 密钥管理

- [ ] TG10-005: 编写 PWA 功能集成测试
  - 文件：`tests/pwa/test_pwa_e2e.py`
  - 依赖：TG10-004
  - 复杂度：中
  - 说明：测试离线访问、缓存策略、安装流程、通知接收

---

## 任务组汇总

| Wave | 任务组 | 类型 | 子任务数 | 预计周期 | 前置条件 |
|------|--------|------|----------|----------|----------|
| 1 | TG1: 图像存储基础设施 | 串行 | 9 | 9天 | 阶段1 |
| 1 | TG2: 图像 Web UI | 串行 | 3 | 6天 | TG1 |
| 1 | TG3: 搜索引擎增强 | 串行 | 10 | 8天 | 阶段1 |
| 2 | TG4: 搜索 API & UI | 串行 | 4 | 6天 | TG3 |
| 2 | TG5: OCR 基础设施 | 串行 | 9 | 12天 | TG1 |
| 2 | TG6: OCR 集成 UI | 串行 | 4 | 8天 | TG5 |
| 2 | TG7: 预览基础设施 | 串行 | 6 | 14天 | 阶段1 |
| 3 | TG8: 预览 UI | 串行 | 5 | 11天 | TG7 |
| 3 | TG9: 响应式设计 | 串行 | 5 | 14天 | TG2+TG4+TG6+TG8 |
| 4 | TG10: PWA 支持 | 串行 | 5 | 12天 | TG9 |

**总计：** 10 个任务组，60 个子任务

---

## 并行机会

| 并行组 | 任务组 | 条件 | 预计节省 |
|--------|--------|------|----------|
| P1 | TG1 + TG3 | 阶段1 已完成（无互相依赖） | ~8天 |
| P2 | TG5 + TG7 | TG1 完成（OCR 依赖图像存储，预览依赖阶段1） | ~12天 |
| P3 | TG4 + TG5 + TG7 | TG1+TG3 完成（搜索UI、OCR、预览可同时推进） | ~6天 |
| P4 | TG9-005（兼容性评估）可提前 | 无依赖，可在 Wave 1 期间执行 | ~1天 |

### 关键路径

```
TG1 (9天) → TG5 (12天) → TG6 (8天) → TG9 (14天) → TG10 (12天)
总关键路径：55天

并行优化后关键路径：
TG1 (9天) → TG5 (12天) → TG9 (14天) → TG10 (12天) = 47天
（TG6 与 TG9 部分重叠，TG7 与 TG5 并行）
```

### 资源冲突注意

| 资源 | 冲突任务组 | 建议处理 |
|------|-----------|---------|
| `lib/db/schema.sql` | TG1-001, TG3-001, TG5-001, TG7-001 | 串行执行迁移，避免并发修改 |
| `lib/migration/migrate.py` | 所有迁移任务 | 串行执行迁移 |
| `lib/api/` 目录 | TG1-007, TG4-001, TG6-001, TG8-001 | 不同文件，可并行 |
| `views/js/` 目录 | TG9-004, TG10-001, TG10-002 | 不同文件，可并行 |
| PostgreSQL 连接 | 所有 TG | 连接池管理，注意并发限制 |

---

## 依赖关系图

```
阶段1 (✅)
  │
  ├──→ TG1: 图像存储基础设施 ──────→ TG2: 图像 Web UI ─────────┐
  │         (9天)                       (6天)                    │
  │                                                            │
  ├──→ TG3: 搜索引擎增强 ───→ TG4: 搜索 API & UI ─────────────┤
  │         (8天)                 (6天)                         │
  │                                                            │
  │     ┌─── TG5: OCR 基础设施 ──→ TG6: OCR 集成 UI ──────────┤
  │     │     (12天)                  (8天)                     │
  │     │                                                      │
  └────┼─── TG7: 预览基础设施 ──→ TG8: 预览 UI ───────────────┤
           (14天)                  (11天)                       │
                                                               │
                                          TG9: 响应式设计 ←────┘
                                               (14天)
                                                 │
                                          TG10: PWA 支持
                                               (12天)
```

---

## 执行建议

### 第一批启动（Wave 1）

同时启动 TG1 和 TG3，最大化并行收益：
- **开发者 A**：TG1（图像存储基础设施）
- **开发者 B**：TG3（搜索引擎增强）
- **额外**：TG9-005（JS 库兼容性评估）可由任一开发者空闲时处理

### 第二批启动（Wave 2）

TG1 完成后，启动 TG2、TG5、TG7：
- **开发者 A**：TG2（图像 UI）+ TG5（OCR 基础设施）
- **开发者 B**：TG7（预览基础设施）
- TG3 完成后立即启动 TG4（搜索 UI）

### 第三批启动（Wave 3）

所有 UI 组件就绪后启动 TG8、TG9：
- **开发者 A**：TG8（预览 UI）
- **开发者 B**：TG9（响应式设计）

### 第四批启动（Wave 4）

TG9 完成后启动 TG10（PWA 支持）。
