---
name: PLAN-008-online-preview
description: 在线预览功能实现 — Open File Viewer 前端集成 + KKFileView 后端备用
priority: P0
status: draft
created: 2026-06-24
updated: 2026-06-24
---

# PLAN-008 - 在线预览功能实现

> **所属项目**：PLAN-000 企业化改造
> **阶段**：阶段 3（用户体验）
> **当前完成度**：0%
> **预估周期**：3-4 天
> **前置依赖**：无（可独立开发）

---

## 一、需求重述

### 1.1 核心需求

为 llm-wiki 提供文件在线预览能力，支持 PDF、Office 文档、图片、视频、音频、代码等多种格式，无需下载即可查看内容。

### 1.2 技术方案

采用**混合模式**：

| 组件 | 角色 | 部署方式 | 本期状态 |
|------|------|----------|:--------:|
| **Open File Viewer** | 主力预览 SDK | 前端 npm 包 | ✅ 本期集成 |
| **KKFileView** | 后端转换服务（复杂格式备用） | Docker 容器 | ⏸️ 接口预留，暂不部署 |

### 1.3 覆盖格式

| 格式类别 | Open File Viewer 支持 | 需后端转换 |
|----------|:---------------------:|:----------:|
| PDF | ✅ 100% | - |
| 图片（jpg/png/gif/webp/svg/tiff/heic） | ✅ 100% | - |
| 视频（mp4/webm/mov/m3u8） | ✅ 100% | - |
| 音频（mp3/wav/ogg/flac） | ✅ 100% | - |
| 代码/文本（txt/md/json/yaml/xml/code） | ✅ 100% | - |
| 简单 Office（docx/xlsx/pptx） | ✅ 90%+ | - |
| 复杂 Office（文本框/绝对定位/自定义字体） | ⚠️ 部分 | ✅ 需后端 |
| 旧格式（.doc/.xls/.ppt） | ❌ 不支持 | ✅ 需后端 |
| CAD（dwg/dxf） | ⚠️ 基础（WASM） | 可选 |
| OFD（中国版式文件） | ⚠️ 基础 | 可选 |

**预估覆盖率**：80-90% 的文件可前端直接预览。

### 1.4 约束条件

| 约束项 | 要求 |
|--------|------|
| 本期不部署 KKFileView | 仅预留接口，返回提示信息 |
| 前端零服务器依赖 | Open File Viewer 纯浏览器渲染 |
| 渐进增强 | 后期可按需启用 KKFileView |
| 保持现有代码 | 保留 `lib/preview/office_viewer.py`，不删除 |

---

## 二、现状分析

### 2.1 已有代码

| 文件 | 说明 | 复用方式 |
|------|------|----------|
| `lib/preview/office_viewer.py` | KKFileView 集成代码 | 保留，后期启用 |
| `lib/preview/__init__.py` | 导出 `OfficeViewerService` | 保留 |
| `lib/preview/cache_manager.py` | 预览缓存管理 | 保留 |
| `tests/preview/test_preview_infra.py` | 20+ 单元测试 | 保留 |

### 2.2 缺失部分

| 缺失项 | 说明 |
|--------|------|
| 前端预览组件 | Open File Viewer 集成 |
| 静态文件服务 | Flask 提供文件下载 URL |
| 转换接口 | `/api/office/convert-to-pdf` |
| 前端 UI 集成 | 预览弹窗/页面 |

---

## 三、实施阶段

### Phase 1：后端接口开发（1 天）

**目标**：提供文件下载 URL + 转换接口预留

#### 步骤 1.1：文件下载端点

- **修改文件**：`lib/web_server.py` 或新建 `lib/api/preview_api.py`
- **新增路由**：
  ```python
  @app.route('/api/files/<file_id>/download')
  def download_file(file_id):
      """提供文件下载 URL，供 Open File Viewer 或 KKFileView 访问"""
      # 1. 根据 file_id 查询文件路径
      # 2. 返回文件流或签名 URL
      return send_file(file_path, as_attachment=False)
  ```
- **权限检查**：验证用户对文件的访问权限

#### 步骤 1.2：转换接口预留

- **新增路由**：
  ```python
  @app.route('/api/office/convert-to-pdf', methods=['POST'])
  def convert_to_pdf():
      """
      复杂 Office 转 PDF（预留接口）
      当前返回提示信息，后期对接 KKFileView
      """
      return jsonify({
          'success': False,
          'error': 'complex_format_not_supported',
          'message': '该文档包含复杂排版，暂不支持在线预览。请联系管理员部署 KKFileView 服务。'
      }), 503
  ```

#### 步骤 1.3：预览元数据 API

- **新增路由**：
  ```python
  @app.route('/api/files/<file_id>/preview-info')
  def get_preview_info(file_id):
      """返回文件预览信息"""
      return jsonify({
          'file_id': file_id,
          'file_name': 'document.pdf',
          'file_size': 1024000,
          'mime_type': 'application/pdf',
          'download_url': f'/api/files/{file_id}/download',
          'preview_type': 'pdf'  # pdf | office | image | video | audio | code | unsupported
      })
  ```

---

### Phase 2：前端 Open File Viewer 集成（2-3 天）

**目标**：前端可预览 PDF/图片/视频/简单 Office

#### 步骤 2.1：安装依赖

```bash
# 在前端项目目录
pnpm add @open-file-viewer/core pdfjs-dist
# 或 npm
npm install @open-file-viewer/core pdfjs-dist
```

#### 步骤 2.2：创建预览组件

- **创建文件**：`static/js/components/FilePreview.js`（原生 JS）或 Vue 组件
- **核心代码**：
  ```javascript
  import {
    createViewer,
    imagePlugin,
    videoPlugin,
    audioPlugin,
    textPlugin,
    pdfPlugin,
    officePlugin,
    archivePlugin,
    fallbackPlugin
  } from '@open-file-viewer/core';
  import '@open-file-viewer/core/style.css';
  import pdfWorkerSrc from 'pdfjs-dist/build/pdf.worker.mjs?url';

  // 配置插件
  const plugins = [
    imagePlugin(),
    videoPlugin(),
    audioPlugin(),
    textPlugin(),
    pdfPlugin({ workerSrc: pdfWorkerSrc }),
    officePlugin({
      // 复杂格式时调用后端转换（当前返回错误提示）
      async convert({ file, arrayBuffer, reason }) {
        const form = new FormData();
        form.append('file', new Blob([arrayBuffer]), file.name);
        form.append('reason', reason);

        const response = await fetch('/api/office/convert-to-pdf', {
          method: 'POST',
          body: form
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.message);
        }

        return {
          blob: await response.blob(),
          fileName: file.name.replace(/\.[^.]+$/, '.pdf'),
          mimeType: 'application/pdf'
        };
      }
    }),
    archivePlugin(),
    fallbackPlugin()
  ];

  // 创建预览器
  function openPreview(fileUrl, fileName) {
    const viewer = createViewer({
      container: '#preview-container',
      file: fileUrl,
      fileName: fileName,
      width: '100%',
      height: '80vh',
      fit: 'contain',
      toolbar: true,
      theme: 'auto',
      plugins: plugins,
      onError(error, file) {
        console.error('预览失败:', error);
        alert(error.message);
      }
    });
  }
  ```

#### 步骤 2.3：UI 集成

- **预览弹窗**：点击文件名 → 弹出预览窗口
- **预览页面**：独立页面 `/preview/<file_id>`
- **文件列表集成**：在文件列表添加"预览"按钮

#### 步骤 2.4：样式适配

- 集成项目主题色
- 响应式布局（移动端适配）
- 明暗主题切换

---

### Phase 3：测试与文档（0.5 天）

**目标**：验证功能 + 更新文档

#### 步骤 3.1：功能测试

- **测试文件**：准备各种格式测试文件
  - PDF（各种大小）
  - 图片（jpg/png/gif/webp/svg/heic）
  - 视频（mp4/webm）
  - Office（简单 docx/xlsx/pptx）
  - Office（复杂文本框/绝对定位）→ 验证错误提示
  - 代码（js/py/md/json）

#### 步骤 3.2：单元测试

- **创建文件**：`tests/preview/test_open_file_viewer.py`
- **测试内容**：
  - 预览信息 API 返回正确
  - 文件下载 API 权限检查
  - 转换接口返回预期错误信息

#### 步骤 3.3：文档更新

- 更新 `README.md` 添加预览功能说明
- 更新 `Doc/ARCH-enterprise-llm-wiki.md` 架构图
- 更新 PLAN-000 进度

---

### Phase 4（后期）：部署 KKFileView（可选）

**触发条件**：用户反馈复杂 Office 无法预览，且有强烈需求

#### 步骤 4.1：添加 Docker 配置

```yaml
# docker-compose.yml
services:
  kkfileview:
    image: keking/kkfileview:latest
    ports:
      - "8012:8012"
    environment:
      - KK_TRUST_HOST=*
      - KK_OFFICE_PREVIEW_TYPE=pdf
    volumes:
      - ./files:/opt/kkFileView-5.0.0/file
```

#### 步骤 4.2：修改转换接口

```python
@app.route('/api/office/convert-to-pdf', methods=['POST'])
def convert_to_pdf():
    """调用 KKFileView 转换 Office 为 PDF"""
    file = request.files['file']

    # 调用 KKFileView API
    kkfileview_url = os.getenv('KKFILEVIEW_URL', 'http://kkfileview:8012')
    # ... 现有 office_viewer.py 逻辑

    return jsonify({
        'success': True,
        'pdf_url': pdf_url
    })
```

---

## 四、依赖关系

```
Phase 1（后端接口）→ Phase 2（前端集成）→ Phase 3（测试文档）
                                         ↓
                              Phase 4（后期 KKFileView）
```

---

## 五、风险评估

| 风险 | 严重程度 | 概率 | 缓解措施 |
|------|:--------:|:----:|----------|
| Open File Viewer 新项目，API 可能变化 | 中 | 中 | 锁定版本号，关注 GitHub 更新 |
| 复杂 Office 预览失败率高 | 低 | 中 | 优化错误提示，引导用户下载 |
| 前端包体积增大 | 低 | 低 | pdfjs-dist 按需加载 |
| 浏览器兼容性 | 低 | 低 | 测试主流浏览器 |

---

## 六、文件变更清单

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `lib/api/preview_api.py` | 预览相关 API 路由 |
| `static/js/components/FilePreview.js` | Open File Viewer 集成组件 |
| `static/js/file-preview-init.js` | 预览器初始化逻辑 |
| `templates/preview.html` | 预览页面模板 |
| `tests/preview/test_preview_api.py` | API 单元测试 |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `lib/web_server.py` | 注册预览 API 蓝图 |
| `templates/file_list.html` | 添加预览按钮 |
| `static/css/preview.css` | 预览组件样式 |
| `Doc/plans/PLAN-000-enterprise-overall-plan.md` | 更新进度 |
| `package.json`（如有） | 添加 Open File Viewer 依赖 |

### 保留文件（不删除）

| 文件路径 | 说明 |
|----------|------|
| `lib/preview/office_viewer.py` | KKFileView 集成代码，后期备用 |

---

## 七、验收标准

1. ✅ PDF 文件可在浏览器中预览
2. ✅ 图片/视频/音频可正常播放
3. ✅ 简单 Office（docx/xlsx/pptx）可预览
4. ✅ 复杂 Office 显示友好错误提示
5. ✅ 预览器支持明暗主题
6. ✅ 移动端预览正常
7. ✅ 文件权限检查正确
8. ✅ 单元测试覆盖 API

---

## 八、后续扩展

| 扩展项 | 触发条件 | 工作量 |
|--------|----------|:------:|
| 部署 KKFileView | 复杂 Office 预览需求 | 1 天 |
| 水印支持 | 版权保护需求 | 0.5 天 |
| 批量预览 | 多文件场景 | 0.5 天 |
| 预览缓存 | 性能优化 | 1 天 |
| CAD 高保真预览 | 工程图纸需求 | 2-3 天 |

---

**计划创建时间**：2026-06-24
**计划状态**：draft — 等待审批
