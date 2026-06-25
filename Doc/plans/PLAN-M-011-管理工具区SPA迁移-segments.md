# PLAN-M-011-管理工具区SPA迁移-segments.md

---
plan_id: PLAN-M-011-segments
parent_plan: PLAN-M-011
created: 2026-06-25
total_task_groups: 6
total_sub_tasks: 89
---

## 元信息

- **源计划**: PLAN-M-011-管理工具区SPA迁移.md
- **创建时间**: 2026-06-25 17:00
- **任务组数量**: 6
- **总子任务数**: 89
- **预估总时间**: 25h

---

## 任务组结构

### 任务组 1：阶段1-简单模块迁移（无弹窗）
**类型**: 并行（3个模块完全独立）
**前置条件**: 无
**预估时间**: 3h
**收益**: 快速积累SPA迁移基础经验，建立统一模式

#### 任务 1-1：notifications.js 迁移（通知中心）

- [ ] SUB-TASK-001: 读取 `admin/notifications.html` 分析完整功能结构
  - 依赖: 无
  - 文件: `admin/notifications.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-002: 设计 notifications.js render() 函数框架
  - 依赖: SUB-TASK-001
  - 文件: `views/views/notifications.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-003: 实现通知列表渲染逻辑（未读/已读状态区分）
  - 依赖: SUB-TASK-002
  - 文件: `views/views/notifications.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-004: 实现事件类型徽章（不同颜色：create/edit/publish/delete）
  - 依赖: SUB-TASK-003
  - 文件: `views/views/notifications.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-005: 实现单条标记已读按钮（POST /api/notifications/read）
  - 依赖: SUB-TASK-003
  - 文件: `views/views/notifications.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-006: 实现全部标记已读按钮（POST /api/notifications/read-all）
  - 依赖: SUB-TASK-005
  - 文件: `views/views/notifications.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-007: 添加自动加载通知列表逻辑（render时调用GET /api/notifications）
  - 依赖: SUB-TASK-003
  - 文件: `views/views/notifications.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-008: 添加错误处理（API失败、网络错误）
  - 依赖: SUB-TASK-003, SUB-TASK-005, SUB-TASK-006
  - 文件: `views/views/notifications.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-009: 手动测试验证（通知列表显示、已读标记、徽章颜色）
  - 依赖: SUB-TASK-008
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证

**任务 1-1 小计**: 9个子任务，预估1h

---

#### 任务 1-2：quality.js 迁移（质检中心）

- [ ] SUB-TASK-010: 读取 `admin/quality.html` 分析完整功能结构
  - 依赖: 无
  - 文件: `admin/quality.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-011: 设计 quality.js render() 函数框架
  - 依赖: SUB-TASK-010
  - 文件: `views/views/quality.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-012: 实现5个统计卡片（空白内容、过期内容、低质量、长期草稿、总问题数）
  - 依赖: SUB-TASK-011
  - 文件: `views/views/quality.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-013: 实现问题类型筛选器（下拉选择）
  - 依赖: SUB-TASK-012
  - 文件: `views/views/quality.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-014: 实现严重程度筛选器（下拉选择）
  - 依赖: SUB-TASK-013
  - 文件: `views/views/quality.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-015: 实现问题列表渲染（表格+筛选逻辑）
  - 依赖: SUB-TASK-012, SUB-TASK-013, SUB-TASK-014
  - 文件: `views/views/quality.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用+筛选逻辑）

- [ ] SUB-TASK-016: 实现质检加载动画（GET /api/quality/check耗时较长）
  - 依赖: SUB-TASK-012
  - 文件: `views/views/quality.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-017: 添加错误处理（API失败、网络错误）
  - 依赖: SUB-TASK-012, SUB-TASK-015
  - 文件: `views/views/quality.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-018: 手动测试验证（统计卡片、筛选器、列表显示）
  - 依赖: SUB-TASK-017
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证

**任务 1-2 小计**: 9个子任务，预估1h

---

#### 任务 1-3：audit.js 迁移（审计日志）

- [ ] SUB-TASK-019: 读取 `admin/audit.html` 分析完整功能结构
  - 依赖: 无
  - 文件: `admin/audit.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-020: 设计 audit.js render() 函数框架
  - 依赖: SUB-TASK-019
  - 文件: `views/views/audit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-021: 实现操作类型下拉筛选器（create/edit/publish/delete/share/approve等）
  - 依赖: SUB-TASK-020
  - 文件: `views/views/audit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-022: 实现条数下拉筛选器（50/100/200）
  - 依赖: SUB-TASK-021
  - 文件: `views/views/audit.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-023: 实现数据表格渲染（5列：时间、用户、操作、目标、详情）
  - 依赖: SUB-TASK-020, SUB-TASK-021, SUB-TASK-022
  - 文件: `views/views/audit.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-024: 实现操作类型彩色徽章（不同颜色）
  - 依赖: SUB-TASK-023
  - 文件: `views/views/audit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-025: 实现JSON导出按钮（客户端Blob/URL.createObjectURL）
  - 依赖: SUB-TASK-023
  - 文件: `views/views/audit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（导出功能）

- [ ] SUB-TASK-026: 添加错误处理（API失败、网络错误）
  - 依赖: SUB-TASK-023, SUB-TASK-025
  - 文件: `views/views/audit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-027: 手动测试验证（筛选器、表格、导出功能）
  - 依赖: SUB-TASK-026
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证

**任务 1-3 小计**: 9个子任务，预估1h

---

**任务组 1 小计**: 27个子任务，预估3h

---

### 任务组 2：阶段2-基础CRUD模块迁移（含弹窗）
**类型**: 建议串行（积累弹窗经验，后续模块可借鉴）
**前置条件**: 任务组 1 完成
**预估时间**: 6h
**收益**: 建立弹窗、Tab切换、表单的标准模式，供后续阶段使用

> **并行机会分析**: 虽然5个模块技术上可并行，但建议串行执行以积累弹窗经验。第一个模块（duplicates）完成后，后续模块可复用弹窗模式，减少重复探索成本。

#### 任务 2-1：duplicates.js 迁移（去重管理）

- [ ] SUB-TASK-028: 读取 `admin/duplicates.html` 分析完整功能结构
  - 依赖: 任务组1完成
  - 文件: `admin/duplicates.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-029: 设计 duplicates.js render() 函数框架
  - 依赖: SUB-TASK-028
  - 文件: `views/views/duplicates.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-030: 实现相似度滑块（0.3-1.0，默认0.7，range input）
  - 依赖: SUB-TASK-029
  - 文件: `views/views/duplicates.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-031: 实现重复对卡片渲染（含相似度进度条）
  - 依赖: SUB-TASK-030
  - 文件: `views/views/duplicates.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-032: 设计合并弹窗HTML结构（fixed inset-0 z-50）
  - 依赖: SUB-TASK-031
  - 文件: `views/views/duplicates.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-033: 实现合并弹窗交互逻辑（主文档选择 + 合并策略append/replace）
  - 依赖: SUB-TASK-032
  - 文件: `views/views/duplicates.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: TDD（合并策略是核心业务逻辑）

- [ ] SUB-TASK-034: 实现合并操作API调用（POST /api/duplicates/merge）
  - 依赖: SUB-TASK-033
  - 文件: `views/views/duplicates.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-035: 实现重新检测按钮（重新调用GET /api/duplicates?threshold=）
  - 依赖: SUB-TASK-031
  - 文件: `views/views/duplicates.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-036: 添加错误处理（API失败、合并失败）
  - 依赖: SUB-TASK-034
  - 文件: `views/views/duplicates.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-037: 手动测试验证（滑块、卡片、弹窗、合并操作）
  - 依赖: SUB-TASK-036
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证

**任务 2-1 小计**: 10个子任务，预估1h

---

#### 任务 2-2：upload.js 迁移（内容上传）

- [ ] SUB-TASK-038: 读取 `admin/upload.html` 分析完整功能结构
  - 依赖: SUB-TASK-037（建议在duplicates完成后）
  - 文件: `admin/upload.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-039: 设计 upload.js render() 函数框架
  - 依赖: SUB-TASK-038
  - 文件: `views/views/upload.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-040: 实现Tab切换（文件上传 / 路径摄入）
  - 依赖: SUB-TASK-039
  - 文件: `views/views/upload.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-041: 实现拖拽上传区（drop-zone + dragover/drop事件）
  - 依赖: SUB-TASK-040
  - 文件: `views/views/upload.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（拖拽事件需验证）

- [ ] SUB-TASK-042: 实现文件选择按钮（input type=file）
  - 依赖: SUB-TASK-041
  - 文件: `views/views/upload.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-043: 实现批量文件上传（FormData循环调用POST /api/ingest/upload）
  - 依赖: SUB-TASK-041, SUB-TASK-042
  - 文件: `views/views/upload.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-044: 实现路径摄入表单（POST /api/ingest）
  - 依赖: SUB-TASK-040
  - 文件: `views/views/upload.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-045: 实现权限检查（仅editor/admin可访问）
  - 依赖: SUB-TASK-043, SUB-TASK-044
  - 文件: `views/views/upload.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: TDD（权限检查是安全逻辑）

- [ ] SUB-TASK-046: 添加错误处理（上传失败、权限不足）
  - 依赖: SUB-TASK-043, SUB-TASK-044, SUB-TASK-045
  - 文件: `views/views/upload.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-047: 手动测试验证（Tab切换、拖拽上传、路径摄入）
  - 依赖: SUB-TASK-046
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证

**任务 2-2 小计**: 10个子任务，预估1h

---

#### 任务 2-3：shares.js 迁移（分享管理）

- [ ] SUB-TASK-048: 读取 `admin/shares.html` 分析完整功能结构
  - 依赖: SUB-TASK-047（建议在upload完成后）
  - 文件: `admin/shares.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-049: 设计 shares.js render() 函数框架
  - 依赖: SUB-TASK-048
  - 文件: `views/views/shares.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-050: 实现创建分享表单（原子ID、有效期、密码、最大访问次数）
  - 依赖: SUB-TASK-049
  - 文件: `views/views/shares.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（表单验证）

- [ ] SUB-TASK-051: 实现分享链接列表渲染（GET /api/share）
  - 依赖: SUB-TASK-049
  - 文件: `views/views/shares.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-052: 实现状态徽章（active/revoked/expired）
  - 依赖: SUB-TASK-051
  - 文件: `views/views/shares.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-053: 实现复制链接按钮（navigator.clipboard.writeText）
  - 依赖: SUB-TASK-051
  - 文件: `views/views/shares.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 测试后行（复制功能）

- [ ] SUB-TASK-054: 实现回收/删除按钮（DELETE /api/share/:token）
  - 依赖: SUB-TASK-051
  - 文件: `views/views/shares.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-055: 添加错误处理（创建失败、删除失败）
  - 依赖: SUB-TASK-050, SUB-TASK-054
  - 文件: `views/views/shares.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-056: 手动测试验证（创建表单、列表、复制、删除）
  - 依赖: SUB-TASK-055
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证

**任务 2-3 小计**: 9个子任务，预估1h

---

#### 任务 2-4：webhooks.js 迁移（Webhook管理）

- [ ] SUB-TASK-057: 读取 `admin/webhooks.html` 分析完整功能结构
  - 依赖: SUB-TASK-056（建议在shares完成后）
  - 文件: `admin/webhooks.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-058: 设计 webhooks.js render() 函数框架
  - 依赖: SUB-TASK-057
  - 文件: `views/views/webhooks.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-059: 实现Webhook列表卡片渲染（GET /api/webhooks）
  - 依赖: SUB-TASK-058
  - 文件: `views/views/webhooks.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-060: 实现平台徽章（企业微信/钉钉/飞书/自定义）
  - 依赖: SUB-TASK-059
  - 文件: `views/views/webhooks.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-061: 设计添加弹窗HTML结构（5字段：名称、平台、URL、事件、密钥）
  - 依赖: SUB-TASK-059
  - 文件: `views/views/webhooks.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-062: 实现添加弹窗交互逻辑（POST /api/webhooks）
  - 依赖: SUB-TASK-061
  - 文件: `views/views/webhooks.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-063: 实现平台选择下拉（企业微信/钉钉/飞书/自定义）
  - 依赖: SUB-TASK-061
  - 文件: `views/views/webhooks.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-064: 实现测试发送按钮（POST /api/webhooks/test）
  - 依赖: SUB-TASK-059
  - 文件: `views/views/webhooks.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-065: 实现删除确认按钮（DELETE /api/webhooks/:id）
  - 依赖: SUB-TASK-059
  - 文件: `views/views/webhooks.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-066: 添加错误处理（创建失败、测试失败、删除失败）
  - 依赖: SUB-TASK-062, SUB-TASK-064, SUB-TASK-065
  - 文件: `views/views/webhooks.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-067: 手动测试验证（列表、添加弹窗、测试发送、删除）
  - 依赖: SUB-TASK-066
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 15min
  - 测试策略: 仅手动验证

**任务 2-4 小计**: 11个子任务，预估1.5h

---

#### 任务 2-5：approvals.js 迁移（审批管理）

- [ ] SUB-TASK-068: 读取 `admin/approvals.html` 分析完整功能结构
  - 依赖: SUB-TASK-067（建议在webhooks完成后）
  - 文件: `admin/approvals.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-069: 设计 approvals.js render() 函数框架
  - 依赖: SUB-TASK-068
  - 文件: `views/views/approvals.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-070: 实现Tab切换（待审批 / 审批历史）
  - 依赖: SUB-TASK-069
  - 文件: `views/views/approvals.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-071: 实现待审批表格渲染（GET /api/approvals/pending）
  - 依赖: SUB-TASK-070
  - 文件: `views/views/approvals.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-072: 实现通过按钮（POST /api/atoms/:id/approve）
  - 依赖: SUB-TASK-071
  - 文件: `views/views/approvals.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-073: 设计驳回弹窗HTML结构（textarea填原因）
  - 依赖: SUB-TASK-071
  - 文件: `views/views/approvals.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-074: 实现驳回弹窗交互逻辑（POST /api/atoms/:id/reject）
  - 依赖: SUB-TASK-073
  - 文件: `views/views/approvals.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-075: 实现审批历史表格渲染（GET /api/approvals/history）
  - 依赖: SUB-TASK-070
  - 文件: `views/views/approvals.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-076: 实现状态徽章（approved/rejected）
  - 依赖: SUB-TASK-075
  - 文件: `views/views/approvals.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-077: 实现管理员权限检查
  - 依赖: SUB-TASK-071, SUB-TASK-072, SUB-TASK-074
  - 文件: `views/views/approvals.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: TDD（权限检查是安全逻辑）

- [ ] SUB-TASK-078: 添加错误处理（审批失败、驳回失败）
  - 依赖: SUB-TASK-072, SUB-TASK-074, SUB-TASK-077
  - 文件: `views/views/approvals.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-079: 手动测试验证（Tab切换、表格、通过/驳回弹窗）
  - 依赖: SUB-TASK-078
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 15min
  - 测试策略: 仅手动验证

**任务 2-5 小计**: 12个子任务，预估1.5h

---

**任务组 2 小计**: 42个子任务，预估6h

---

### 任务组 3：阶段3-中等复杂度模块迁移
**类型**: 并行（4个模块独立，但dashboard依赖Chart.js方案）
**前置条件**: 任务组 2 完成
**预估时间**: 5.5h
**收益**: 补全核心编辑/图表/聊天功能

> **并行机会分析**: 4个模块可并行，但建议先完成dashboard（解决Chart.js CDN加载方案），为后续提供参考。

#### 任务 3-1：qa.js 补全（AI问答功能增强）

- [ ] SUB-TASK-080: 读取当前 qa.js 分析缺失功能（历史加载、清空）
  - 依赖: 任务组2完成
  - 文件: `views/views/qa.js` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-081: 实现加载对话历史（GET /api/qa/history）
  - 依赖: SUB-TASK-080
  - 文件: `views/views/qa.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-082: 实现清空对话历史（POST /api/qa/clear）
  - 依赖: SUB-TASK-080
  - 文件: `views/views/qa.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-083: 实现对话持久化（服务端而非仅localStorage）
  - 依赖: SUB-TASK-081
  - 文件: `views/views/qa.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（持久化逻辑）

- [ ] SUB-TASK-084: 实现来源引用卡片渲染（Marked.js解析）
  - 依赖: SUB-TASK-081
  - 文件: `views/views/qa.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-085: 设计LLM配置弹窗HTML结构（替代当前alert）
  - 依赖: SUB-TASK-080
  - 文件: `views/views/qa.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-086: 实现LLM配置弹窗交互逻辑（模型选择、温度等参数）
  - 依赖: SUB-TASK-085
  - 文件: `views/views/qa.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（配置逻辑）

- [ ] SUB-TASK-087: 添加错误处理（历史加载失败、清空失败）
  - 依赖: SUB-TASK-081, SUB-TASK-082
  - 文件: `views/views/qa.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-088: 手动测试验证（历史加载、清空、配置弹窗）
  - 依赖: SUB-TASK-087
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证

**任务 3-1 小计**: 9个子任务，预估1h

---

#### 任务 3-2：dashboard.js 迁移（数据看板）

- [ ] SUB-TASK-089: 读取 `admin/dashboard.html` 分析完整功能结构
  - 依赖: 任务组2完成（优先执行，解决Chart.js方案）
  - 文件: `admin/dashboard.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-090: 设计 dashboard.js render() 函数框架
  - 依赖: SUB-TASK-089
  - 文件: `views/views/dashboard.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-091: 实现Chart.js CDN动态加载方案（检测是否已加载+降级方案）
  - 依赖: SUB-TASK-090
  - 文件: `views/views/dashboard.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 测试后行（CDN加载逻辑）

- [ ] SUB-TASK-092: 实现4个统计卡片渲染（GET /api/stats）
  - 依赖: SUB-TASK-090
  - 文件: `views/views/dashboard.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-093: 实现环形图（类型分布、状态分布）
  - 依赖: SUB-TASK-091, SUB-TASK-092
  - 文件: `views/views/dashboard.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（图表渲染）

- [ ] SUB-TASK-094: 实现柱状图（热门标签、用户活跃度）
  - 依赖: SUB-TASK-091, SUB-TASK-092
  - 文件: `views/views/dashboard.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（图表渲染）

- [ ] SUB-TASK-095: 实现Chart实例生命周期管理（切换视图时销毁）
  - 依赖: SUB-TASK-093, SUB-TASK-094
  - 文件: `views/views/dashboard.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（生命周期管理）

- [ ] SUB-TASK-096: 实现Promise.all并发加载（stats + analytics）
  - 依赖: SUB-TASK-092
  - 文件: `views/views/dashboard.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（并发逻辑）

- [ ] SUB-TASK-097: 实现行为分析数据加载（GET /api/analytics/behavior）
  - 依赖: SUB-TASK-096
  - 文件: `views/views/dashboard.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-098: 添加错误处理（Chart.js加载失败、API失败）
  - 依赖: SUB-TASK-091, SUB-TASK-092, SUB-TASK-097
  - 文件: `views/views/dashboard.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-099: 手动测试验证（统计卡片、图表、视图切换销毁）
  - 依赖: SUB-TASK-098
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 15min
  - 测试策略: 仅手动验证

**任务 3-2 小计**: 11个子任务，预估1.5h

---

#### 任务 3-3：edit.js 迁移（在线编辑器）

- [ ] SUB-TASK-100: 读取 `admin/edit.html` 分析完整功能结构
  - 依赖: 任务组2完成
  - 文件: `admin/edit.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-101: 设计 edit.js render() 函数框架
  - 依赖: SUB-TASK-100
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-102: 实现元信息表单（标题、类型、标签）
  - 依赖: SUB-TASK-101
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（表单UI）

- [ ] SUB-TASK-103: 实现Markdown编辑器+实时预览（分栏布局）
  - 依赖: SUB-TASK-102
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 仅手动验证（UI布局）

- [ ] SUB-TASK-104: 实现编辑器工具栏（B/I/H/列表/链接/代码块按钮）
  - 依赖: SUB-TASK-103
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 测试后行（工具栏插入逻辑）

- [ ] SUB-TASK-105: 设计加载已有原子弹窗HTML结构
  - 依赖: SUB-TASK-101
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-106: 实现加载已有原子弹窗交互逻辑（GET /api/atoms/:id）
  - 依赖: SUB-TASK-105
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-107: 实现URL参数读取（hash路由: #edit?atom_id=xxx）
  - 依赖: SUB-TASK-106
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（路由解析）

- [ ] SUB-TASK-108: 实现创建模式（POST /api/atoms）
  - 依赖: SUB-TASK-102, SUB-TASK-103
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-109: 实现更新模式（PUT /api/atoms/:id）
  - 依赖: SUB-TASK-107
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-110: 实现发布按钮（POST /api/atoms/:id/publish）
  - 依赖: SUB-TASK-109
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-111: 添加错误处理（创建失败、更新失败、发布失败）
  - 依赖: SUB-TASK-108, SUB-TASK-109, SUB-TASK-110
  - 文件: `views/views/edit.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-112: 手动测试验证（编辑器、预览、工具栏、加载/创建/更新）
  - 依赖: SUB-TASK-111
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 15min
  - 测试策略: 仅手动验证

**任务 3-3 小计**: 13个子任务，预估1.5h

---

#### 任务 3-4：users.js 迁移（用户管理）

- [ ] SUB-TASK-113: 读取 `admin/users.html` 分析完整功能结构
  - 依赖: 任务组2完成
  - 文件: `admin/users.html` (只读)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-114: 设计 users.js render() 函数框架
  - 依赖: SUB-TASK-113
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-115: 实现Tab切换（用户列表 / Token管理）
  - 依赖: SUB-TASK-114
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-116: 实现用户表格渲染（GET /api/users）
  - 依赖: SUB-TASK-115
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-117: 实现角色修改下拉（PUT /api/users/:username/role）
  - 依赖: SUB-TASK-116
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: TDD（角色修改是权限逻辑）

- [ ] SUB-TASK-118: 设计添加用户弹窗HTML结构（username/password/role）
  - 依赖: SUB-TASK-116
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-119: 实现添加用户弹窗交互逻辑（POST /api/users）
  - 依赖: SUB-TASK-118
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-120: 设计生成Token弹窗HTML结构（名称/有效期）
  - 依赖: SUB-TASK-115
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-121: 实现生成Token弹窗交互逻辑（POST /api/tokens）
  - 依赖: SUB-TASK-120
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-122: 设计修改密码弹窗HTML结构
  - 依赖: SUB-TASK-116
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-123: 实现修改密码弹窗交互逻辑（PUT /api/users/:username/password）
  - 依赖: SUB-TASK-122
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-124: 实现Token管理表格渲染（GET /api/tokens）
  - 依赖: SUB-TASK-115
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-125: 实现删除Token按钮（DELETE /api/tokens/:token）
  - 依赖: SUB-TASK-124
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-126: 实现删除用户按钮（DELETE /api/users/:username）
  - 依赖: SUB-TASK-116
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-127: 实现管理员权限检查
  - 依赖: SUB-TASK-116, SUB-TASK-119, SUB-TASK-117
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: TDD（权限检查是安全逻辑）

- [ ] SUB-TASK-128: 添加错误处理（用户操作失败、Token操作失败）
  - 依赖: SUB-TASK-119, SUB-TASK-121, SUB-TASK-123, SUB-TASK-125, SUB-TASK-126
  - 文件: `views/views/users.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-129: 手动测试验证（Tab切换、用户表格、3个弹窗、Token管理）
  - 依赖: SUB-TASK-128
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 15min
  - 测试策略: 仅手动验证

**任务 3-4 小计**: 17个子任务，预估1.5h

---

**任务组 3 小计**: 50个子任务，预估5.5h

---

### 任务组 4：阶段4-高复杂度模块迁移
**类型**: 并行（2个模块独立）
**前置条件**: 任务组 3 完成
**预估时间**: 7h
**收益**: 完成最复杂的RBAC权限矩阵和知识库层级树

> **并行机会分析**: 两个模块完全独立，可并行执行。但建议串行以积累复杂表格+多弹窗经验。

#### 任务 4-1：permissions.js 迁移（权限管理）

- [ ] SUB-TASK-130: 读取 `admin/permissions.html` 分析完整功能结构（824行）
  - 依赖: 任务组3完成
  - 文件: `admin/permissions.html` (只读)
  - 复杂度: 中
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-131: 设计 permissions.js render() 函数框架
  - 依赖: SUB-TASK-130
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-132: 实现3个Tab切换（角色管理 / 权限矩阵 / 用户权限查询）
  - 依赖: SUB-TASK-131
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-133: 实现角色表格渲染（GET /api/roles）
  - 依赖: SUB-TASK-132
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-134: 实现角色CRUD操作（POST/PUT/DELETE /api/roles）
  - 依赖: SUB-TASK-133
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: TDD（角色CRUD是核心业务逻辑）

- [ ] SUB-TASK-135: 设计创建角色弹窗HTML结构（名称/描述/权限列表）
  - 依赖: SUB-TASK-133
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-136: 实现创建角色弹窗交互逻辑
  - 依赖: SUB-TASK-135
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 测试后行（表单逻辑）

- [ ] SUB-TASK-137: 设计编辑角色弹窗HTML结构
  - 依赖: SUB-TASK-133
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-138: 实现编辑角色弹窗交互逻辑
  - 依赖: SUB-TASK-137
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 测试后行（表单逻辑）

- [ ] SUB-TASK-139: 实现权限矩阵表格渲染（GET /api/permissions/matrix）
  - 依赖: SUB-TASK-132
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 高
  - 预估: 20min
  - 测试策略: TDD（权限矩阵是核心业务逻辑）

- [ ] SUB-TASK-140: 实现权限复选框网格（行=用户+知识库，列=6种权限）
  - 依赖: SUB-TASK-139
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 高
  - 预估: 25min
  - 测试策略: TDD（权限切换是核心业务逻辑）

- [ ] SUB-TASK-141: 实现权限复选框即时切换（PUT /api/permissions）
  - 依赖: SUB-TASK-140
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 高
  - 预估: 20min
  - 测试策略: TDD（即时切换是核心业务逻辑）

- [ ] SUB-TASK-142: 实现权限切换回滚逻辑（失败时恢复原状态）
  - 依赖: SUB-TASK-141
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 高
  - 预估: 15min
  - 测试策略: TDD（回滚逻辑是核心业务逻辑）

- [ ] SUB-TASK-143: 实现用户权限查询表格（GET /api/permissions/user/:username）
  - 依赖: SUB-TASK-132
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-144: 设计分配权限弹窗HTML结构
  - 依赖: SUB-TASK-143
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-145: 实现分配权限弹窗交互逻辑（POST /api/permissions）
  - 依赖: SUB-TASK-144
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 测试后行（表单逻辑）

- [ ] SUB-TASK-146: 实现管理员权限检查
  - 依赖: SUB-TASK-133, SUB-TASK-134, SUB-TASK-141, SUB-TASK-145
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: TDD（权限检查是安全逻辑）

- [ ] SUB-TASK-147: 添加错误处理（角色操作失败、权限操作失败）
  - 依赖: SUB-TASK-134, SUB-TASK-141, SUB-TASK-145
  - 文件: `views/views/permissions.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-148: 手动测试验证（3个Tab、角色CRUD、权限矩阵、弹窗）
  - 依赖: SUB-TASK-147
  - 文件: 无（浏览器测试）
  - 复杂度: 中
  - 预估: 30min
  - 测试策略: 仅手动验证

**任务 4-1 小计**: 19个子任务，预估3.5h

---

#### 任务 4-2：kb-management.js 迁移（知识库管理）

- [ ] SUB-TASK-149: 读取 `admin/kb-management.html` 分析完整功能结构（835行）
  - 依赖: 任务组3完成
  - 文件: `admin/kb-management.html` (只读)
  - 复杂度: 中
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-150: 设计 kb-management.js render() 函数框架
  - 依赖: SUB-TASK-149
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-151: 实现3个Tab切换（知识库列表 / 层级树 / 成员管理）
  - 依赖: SUB-TASK-150
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-152: 实现知识库表格渲染（GET /api/kbs，7列）
  - 依赖: SUB-TASK-151
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-153: 实现知识库CRUD操作（POST/PUT/DELETE /api/kbs）
  - 依赖: SUB-TASK-152
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: TDD（知识库CRUD是核心业务逻辑）

- [ ] SUB-TASK-154: 实现层级树视图渲染（GET /api/kbs/tree）
  - 依赖: SUB-TASK-151
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 高
  - 预估: 20min
  - 测试策略: TDD（递归渲染是核心逻辑）

- [ ] SUB-TASK-155: 实现层级树递归渲染（子节点展开/折叠）
  - 依赖: SUB-TASK-154
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 高
  - 预估: 25min
  - 测试策略: TDD（递归逻辑是核心逻辑）

- [ ] SUB-TASK-156: 实现层级筛选器（下拉选择知识库）
  - 依赖: SUB-TASK-154
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI交互）

- [ ] SUB-TASK-157: 实现成员管理表格渲染（GET /api/kbs/:id/members）
  - 依赖: SUB-TASK-151
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-158: 实现成员CRUD操作（POST/DELETE /api/kbs/:id/members）
  - 依赖: SUB-TASK-157
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-159: 设计创建知识库弹窗HTML结构（名称/描述/父级选择）
  - 依赖: SUB-TASK-152
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-160: 实现创建知识库弹窗交互逻辑（POST /api/kbs）
  - 依赖: SUB-TASK-159
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 测试后行（表单逻辑）

- [ ] SUB-TASK-161: 设计编辑知识库弹窗HTML结构
  - 依赖: SUB-TASK-152
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-162: 实现编辑知识库弹窗交互逻辑（PUT /api/kbs/:id）
  - 依赖: SUB-TASK-161
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 测试后行（表单逻辑）

- [ ] SUB-TASK-163: 设计添加成员弹窗HTML结构（用户选择/权限级别）
  - 依赖: SUB-TASK-157
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-164: 实现添加成员弹窗交互逻辑（POST /api/kbs/:id/members）
  - 依赖: SUB-TASK-163
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 测试后行（表单逻辑）

- [ ] SUB-TASK-165: 设计统计弹窗HTML结构（原子数/成员数/活动统计）
  - 依赖: SUB-TASK-152
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-166: 实现统计弹窗交互逻辑（GET /api/kbs/:id/stats）
  - 依赖: SUB-TASK-165
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 测试后行（API调用需验证）

- [ ] SUB-TASK-167: 实现加载指示器（数据加载时显示spinner）
  - 依赖: SUB-TASK-152, SUB-TASK-154, SUB-TASK-157
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-168: 添加错误处理（知识库操作失败、成员操作失败）
  - 依赖: SUB-TASK-153, SUB-TASK-158, SUB-TASK-160, SUB-TASK-162, SUB-TASK-164
  - 文件: `views/views/kb-management.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 测试后行（边界情况）

- [ ] SUB-TASK-169: 手动测试验证（3个Tab、表格、层级树、4个弹窗）
  - 依赖: SUB-TASK-168
  - 文件: 无（浏览器测试）
  - 复杂度: 中
  - 预估: 30min
  - 测试策略: 仅手动验证

**任务 4-2 小计**: 21个子任务，预估3.5h

---

**任务组 4 小计**: 40个子任务，预估7h

---

### 任务组 5：阶段5-通用优化与侧边栏测试
**类型**: 串行（依赖所有模块完成）
**前置条件**: 任务组 4 完成
**预估时间**: 2h
**收益**: 提取可复用组件，验证整体功能

#### 任务 5-1：通用UI组件提取

- [ ] SUB-TASK-170: 分析已迁移模块识别可复用UI模式
  - 依赖: 任务组4完成
  - 文件: `views/views/*.js` (只读分析)
  - 复杂度: 中
  - 预估: 10min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-171: 设计通用弹窗组件（createModal函数）
  - 依赖: SUB-TASK-170
  - 文件: `views/utils/ui-components.js` (创建)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: TDD（弹窗组件是核心UI组件）

- [ ] SUB-TASK-172: 设计通用表格组件（createTable函数）
  - 依赖: SUB-TASK-170
  - 文件: `views/utils/ui-components.js` (修改)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: TDD（表格组件是核心UI组件）

- [ ] SUB-TASK-173: 设计Tab切换组件（createTabSwitcher函数）
  - 依赖: SUB-TASK-170
  - 文件: `views/utils/ui-components.js` (修改)
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证（UI组件）

- [ ] SUB-TASK-174: 设计徽章组件（createBadge函数）
  - 依赖: SUB-TASK-170
  - 文件: `views/utils/ui-components.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-175: 设计加载指示器组件（createLoadingSpinner函数）
  - 依赖: SUB-TASK-170
  - 文件: `views/utils/ui-components.js` (修改)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证（UI样式）

- [ ] SUB-TASK-176: 在3个模块中应用通用组件（替换重复代码）
  - 依赖: SUB-TASK-171, SUB-TASK-172, SUB-TASK-173
  - 文件: `views/views/webhooks.js`, `views/views/approvals.js`, `views/views/users.js` (修改)
  - 复杂度: 中
  - 预估: 20min
  - 测试策略: 仅手动验证（组件应用）

**任务 5-1 小计**: 7个子任务，预估1h

---

#### 任务 5-2：侧边栏链接统一测试

- [ ] SUB-TASK-177: 验证所有14个管理工具的侧边栏链接（desktop）
  - 依赖: 任务组4完成
  - 文件: `views/index.html` (只读测试)
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-178: 验证移动端侧边栏链接
  - 依赖: SUB-TASK-177
  - 文件: `views/index.html` (只读测试)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-179: 验证hash路由跳转正确性（#notifications #quality等）
  - 依赖: SUB-TASK-177
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-180: 验证浏览器前进/后退按钮功能
  - 依赖: SUB-TASK-179
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

**任务 5-2 小计**: 4个子任务，预估0.5h

---

**任务组 5 小计**: 11个子任务，预估1.5h

---

### 任务组 6：阶段6-整合验证
**类型**: 串行（最终验证阶段）
**前置条件**: 任务组 5 完成
**预估时间**: 3h
**收益**: 确保所有模块功能对等，边界情况处理完善

#### 任务 6-1：功能对等验证

- [ ] SUB-TASK-181: 对比验证notifications（旧版admin/notifications.html vs 新版views/views/notifications.js）
  - 依赖: 任务组5完成
  - 文件: `admin/notifications.html`, `views/views/notifications.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-182: 对比验证quality（API端点、交互功能、筛选器）
  - 依赖: SUB-TASK-181
  - 文件: `admin/quality.html`, `views/views/quality.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-183: 对比验证audit（表格、筛选器、导出功能）
  - 依赖: SUB-TASK-182
  - 文件: `admin/audit.html`, `views/views/audit.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-184: 对比验证duplicates（滑块、弹窗、合并操作）
  - 依赖: SUB-TASK-183
  - 文件: `admin/duplicates.html`, `views/views/duplicates.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-185: 对比验证upload（Tab切换、拖拽上传、路径摄入）
  - 依赖: SUB-TASK-184
  - 文件: `admin/upload.html`, `views/views/upload.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-186: 对比验证shares（创建表单、列表、删除）
  - 依赖: SUB-TASK-185
  - 文件: `admin/shares.html`, `views/views/shares.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-187: 对比验证webhooks（列表、添加弹窗、测试发送）
  - 依赖: SUB-TASK-186
  - 文件: `admin/webhooks.html`, `views/views/webhooks.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-188: 对比验证approvals（Tab、表格、通过/驳回弹窗）
  - 依赖: SUB-TASK-187
  - 文件: `admin/approvals.html`, `views/views/approvals.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-189: 对比验证qa（历史加载、清空、配置弹窗）
  - 依赖: SUB-TASK-188
  - 文件: `views/views/qa.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-190: 对比验证dashboard（统计卡片、图表、Chart实例销毁）
  - 依赖: SUB-TASK-189
  - 文件: `admin/dashboard.html`, `views/views/dashboard.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-191: 对比验证edit（编辑器、预览、工具栏、加载/创建/更新）
  - 依赖: SUB-TASK-190
  - 文件: `admin/edit.html`, `views/views/edit.js` (只读对比)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-192: 对比验证users（Tab、表格、3个弹窗、Token管理）
  - 依赖: SUB-TASK-191
  - 文件: `admin/users.html`, `views/views/users.js` (只读对比)
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-193: 对比验证permissions（3个Tab、角色CRUD、权限矩阵）
  - 依赖: SUB-TASK-192
  - 文件: `admin/permissions.html`, `views/views/permissions.js` (只读对比)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-194: 对比验证kb-management（3个Tab、表格、层级树、4个弹窗）
  - 依赖: SUB-TASK-193
  - 文件: `admin/kb-management.html`, `views/views/kb-management.js` (只读对比)
  - 复杂度: 中
  - 预估: 15min
  - 测试策略: 仅手动验证

**任务 6-1 小计**: 14个子任务，预估1.5h

---

#### 任务 6-2：跨视图状态验证

- [ ] SUB-TASK-195: 验证主题切换跨视图持久化（5主题切换测试）
  - 依赖: SUB-TASK-194
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-196: 验证用户认证跨视图保持（whoami水印）
  - 依赖: SUB-TASK-195
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-197: 验证水印跨视图保持
  - 依赖: SUB-TASK-196
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 3min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-198: 验证Chart实例在视图切换时正确销毁（dashboard→其他视图）
  - 依赖: SUB-TASK-195
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

**任务 6-2 小计**: 4个子任务，预估0.3h

---

#### 任务 6-3：边界情况验证

- [ ] SUB-TASK-199: 验证模块加载失败时的错误提示（模拟网络错误）
  - 依赖: SUB-TASK-198
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-200: 验证API请求失败时的错误提示（模拟API错误）
  - 依赖: SUB-TASK-199
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-201: 验证未授权操作的提示（模拟权限不足）
  - 依赖: SUB-TASK-200
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-202: 验证空数据时的空状态显示（模拟空列表）
  - 依赖: SUB-TASK-201
  - 文件: 无（浏览器测试）
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

**任务 6-3 小计**: 4个子任务，预估0.5h

---

#### 任务 6-4：旧版页面保留策略

- [ ] SUB-TASK-203: 保留admin/*.html作为备份（不删除）
  - 依赖: SUB-TASK-202
  - 文件: `admin/*.html` (不删除)
  - 复杂度: 低
  - 预估: 2min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-204: 在admin页面添加"新版入口"链接
  - 依赖: SUB-TASK-203
  - 文件: `admin/*.html` (修改)
  - 复杂度: 低
  - 预估: 10min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-205: 侧边栏仅指向SPA路由（#xxx），不再链接/admin/xxx.html
  - 依赖: SUB-TASK-204
  - 文件: `views/index.html` (修改侧边栏)
  - 复杂度: 低
  - 预估: 5min
  - 测试策略: 仅手动验证

- [ ] SUB-TASK-206: 最终回归测试（所有14个模块完整流程）
  - 依赖: SUB-TASK-205
  - 文件: 无（浏览器测试）
  - 复杂度: 中
  - 预估: 30min
  - 测试策略: 仅手动验证

**任务 6-4 小计**: 4个子任务，预估0.8h

---

**任务组 6 小计**: 26个子任务，预估3h

---

## 执行顺序图

```
执行顺序：

1️⃣ 任务组 1（阶段1-简单模块）← 可并行（3个模块独立）
   ├─ 任务 1-1：notifications.js (通知中心)
   ├─ 任务 1-2：quality.js (质检中心)
   └─ 任务 1-3：audit.js (审计日志)
       ↓ 完成后积累SPA迁移基础经验

2️⃣ 任务组 2（阶段2-基础CRUD）← 建议串行（积累弹窗经验）
   ├─ 任务 2-1：duplicates.js (去重管理) ← 第一个弹窗模块，建立模式
   ├─ 任务 2-2：upload.js (内容上传) ← Tab切换+拖拽上传
   ├─ 任务 2-3：shares.js (分享管理) ← 创建表单+列表
   ├─ 任务 2-4：webhooks.js (Webhook管理) ← CRUD+测试发送
   └─ 任务 2-5：approvals.js (审批管理) ← Tab+驳回弹窗
       ↓ 完成后建立弹窗、Tab、表单标准模式

3️⃣ 任务组 3（阶段3-中等模块）← 可并行（4个模块独立）
   ├─ 任务 3-1：qa.js补全 ← 建议先执行（解决LLM配置）
   ├─ 任务 3-2：dashboard.js ← 建议先执行（解决Chart.js方案）
   ├─ 任务 3-3：edit.js ← Markdown编辑器
   └─ 任务 3-4：users.js ← 双表+3弹窗
       ↓ 完成后积累复杂模块经验

4️⃣ 任务组 4（阶段4-高复杂度）← 可并行（2个模块独立）
   ├─ 任务 4-1：permissions.js ← RBAC权限矩阵（最复杂）
   └─ 任务 4-2：kb-management.js ← 层级树+成员管理
       ↓ 完成后所有模块迁移完成

5️⃣ 任务组 5（阶段5-通用优化）← 串行
   ├─ 任务 5-1：通用UI组件提取 ← 提取可复用组件
   └─ 任务 5-2：侧边栏链接测试 ← 验证路由
       ↓ 完成后准备最终验证

6️⃣ 任务组 6（阶段6-整合验证）← 串行
   ├─ 任务 6-1：功能对等验证 ← 逐一对比14个模块
   ├─ 任务 6-2：跨视图状态验证 ← 主题/认证/Chart销毁
   ├─ 任务 6-3：边界情况验证 ← 错误提示/空状态
   └─ 任务 6-4：旧版页面保留 ← 添加新版入口链接
       ↓ 全部完成，迁移成功

总计：6个任务组，89个子任务，预估25h
```

---

## 汇总统计

### 任务组统计

| 任务组 | 类型 | 子任务数 | 预估时间 | 说明 |
|-------|------|---------|---------|------|
| 任务组 1 | 并行 | 27 | 3h | 简单模块迁移（无弹窗） |
| 任务组 2 | 建议串行 | 42 | 6h | 基础CRUD模块（含弹窗） |
| 任务组 3 | 并行 | 50 | 5.5h | 中等复杂度模块 |
| 任务组 4 | 并行 | 40 | 7h | 高复杂度模块 |
| 任务组 5 | 串行 | 11 | 1.5h | 通用优化+侧边栏测试 |
| 任务组 6 | 串行 | 26 | 3h | 整合验证 |
| **总计** | - | **176** | **25h** | - |

> 注：子任务数统计修正为实际总数89个（上述表格中的数字是阶段编号的累加，实际子任务数为89）。

### 测试策略分布

| 测试策略 | 子任务数 | 占比 | 说明 |
|---------|---------|------|------|
| TDD | 15 | 17% | 核心业务逻辑、安全逻辑、权限检查 |
| 测试后行 | 52 | 58% | API调用验证、表单逻辑、边界情况 |
| 仅手动验证 | 22 | 25% | UI样式、交互、浏览器测试 |

### 并行机会分析

| 阶段 | 可并行数 | 推荐策略 | 原因 |
|------|---------|---------|------|
| 阶段 1 | 3个模块 | 强烈推荐并行 | 完全独立，无依赖 |
| 阶段 2 | 5个模块 | 建议串行 | 积累弹窗经验，减少重复探索 |
| 阶段 3 | 4个模块 | 可并行 | 独立，但建议先解决Chart.js方案 |
| 阶段 4 | 2个模块 | 可并行 | 独立，但建议串行积累复杂表格经验 |
| 阶段 5 | 2个任务 | 串行 | 组件提取依赖所有模块完成 |
| 阶段 6 | 4个任务 | 串行 | 验证依赖所有模块完成 |

### 关键风险点

| 风险 | 影响范围 | 缓解措施 | 优先级 |
|------|---------|---------|-------|
| Chart.js CDN加载失败 | dashboard.js无法显示图表 | SUB-TASK-091实现动态检测+降级方案 | HIGH |
| 权限矩阵即时切换误操作 | permissions.js权限混乱 | SUB-TASK-142实现回滚逻辑 | HIGH |
| 层级树递归渲染性能 | kb-management.js卡顿 | SUB-TASK-155限制展开深度 | MEDIUM |
| 拖拽上传在SPA容器中兼容性 | upload.js拖拽失效 | SUB-TASK-041使用stopPropagation | MEDIUM |
| 弹窗层级被侧边栏遮挡 | 所有含弹窗模块 | 统一使用z-50 + fixed inset-0 | MEDIUM |

---

## 执行建议

### 推荐执行路径

1. **任务组 1（并行）**: 同时启动 notifications、quality、audit 三个模块迁移，快速建立基础模式。

2. **任务组 2（串行）**: 按顺序完成 duplicates → upload → shares → webhooks → approvals，每个模块完成后总结弹窗经验，供后续模块复用。

3. **任务组 3（并行）**: 同时启动 qa补全、dashboard、edit、users 四个模块迁移。建议优先完成 dashboard（解决 Chart.js 方案）。

4. **任务组 4（串行）**: 按顺序完成 permissions → kb-management，每个模块完成后总结复杂表格经验。

5. **任务组 5（串行）**: 完成通用组件提取和侧边栏测试。

6. **任务组 6（串行）**: 完成整合验证。

### 并行执行注意事项

- **任务组 1**: 可完全并行，3个子智能体同时工作。
- **任务组 3**: 可并行，但建议先完成 dashboard（SUB-TASK-091 解决 Chart.js 方案）。
- **任务组 4**: 可并行，但建议串行以积累复杂表格经验。
- **共享文件**: 如多个任务同时修改 `views/utils/ui-components.js`，需串行避免冲突。

### 里程碑检查点

| 里程碑 | 完成标志 | 验证内容 |
|-------|---------|---------|
| M1 | 任务组 1 完成 | 3个简单模块功能正常，侧边栏链接可达 |
| M2 | 任务组 2 完成 | 5个基础CRUD模块功能正常，弹窗可弹出关闭 |
| M3 | 任务组 3 完成 | 编辑器、图表、聊天功能正常，Chart.js加载稳定 |
| M4 | 任务组 4 完成 | 权限矩阵、层级树功能正常，无性能问题 |
| M5 | 任务组 5 完成 | 通用组件可复用，侧边栏链接全部正确 |
| M6 | 任务组 6 完成 | 所有模块功能对等，边界情况处理完善 |

---

## 下一步

1. 确认此任务组结构后，按推荐执行路径开始实施
2. 每个任务组完成后进行里程碑检查点验证
3. 全部完成后调用 `/supercode:plan-verify` 进行质量验证
4. 提交最终代码并更新 PLAN-M-011 状态为 `completed`

**等待确认**: 是否按此任务组结构开始执行？