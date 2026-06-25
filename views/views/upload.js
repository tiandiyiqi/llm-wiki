/**
 * 上传视图模块
 *
 * 提取自 /views/admin/upload.html，改造为 SPA 模块
 * 功能：文件上传、路径摄入
 */

import { escapeHtml } from '../utils/ui-components.js';

export function render(container) {
    const html = `<div class="upload-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- Header Card -->
            <div class="overview-card text-center mb-6" style="padding: 40px;">
                <h1 class="text-3xl font-bold gradient-title mb-2">📤 内容上传</h1>
                <p class="text-on-surface">批量上传 Markdown 文件或从服务器路径摄入</p>
            </div>

            <!-- Tab 切换 -->
            <div class="flex gap-2 mb-6">
                <button id="tab-upload" class="tab-btn tab-active" onclick="window.UploadView.switchTab('upload')">
                    文件上传
                </button>
                <button id="tab-ingest" class="tab-btn tab-inactive" onclick="window.UploadView.switchTab('ingest')">
                    路径摄入
                </button>
            </div>

            <!-- 文件上传面板 -->
            <div id="uploadPanel" class="overview-card p-6">
                <h2 class="text-xl font-semibold text-on-base mb-4 flex items-center">
                    <span class="text-2xl mr-2">📁</span>
                    上传 Markdown 文件
                </h2>

                <!-- 拖拽上传区 -->
                <div id="dropZone" class="drop-zone" onclick="document.getElementById('fileInput').click()">
                    <svg class="mx-auto h-12 w-12 text-on-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <p class="mt-2 text-on-surface">点击选择文件或拖拽文件到此处</p>
                    <p class="text-xs text-on-muted mt-1">支持 .md / .markdown / .txt 文件</p>
                    <input type="file" id="fileInput" class="hidden" multiple accept=".md,.markdown,.txt" onchange="window.UploadView.handleFiles(this.files)">
                </div>

                <!-- 文件列表 -->
                <div id="fileList" class="mt-4 space-y-2"></div>

                <!-- 上传结果 -->
                <div id="uploadResult" class="mt-4"></div>
            </div>

            <!-- 路径摄入面板 -->
            <div id="ingestPanel" class="overview-card p-6 hidden">
                <h2 class="text-xl font-semibold text-on-base mb-4 flex items-center">
                    <span class="text-2xl mr-2">📂</span>
                    从本地路径摄入
                </h2>
                <p class="text-sm text-on-surface mb-4">
                    输入服务器上的文件或目录路径，系统将自动解析并摄入为知识原子。
                </p>
                <div class="space-y-3">
                    <div>
                        <label class="block text-sm font-medium text-on-surface mb-1">源路径</label>
                        <input type="text" id="ingestPath" class="input" placeholder="/path/to/file.md 或 /path/to/dir">
                    </div>
                    <button onclick="window.UploadView.ingestPath()" class="btn btn-primary">开始摄入</button>
                </div>

                <!-- 摄入结果 -->
                <div id="ingestResult" class="mt-4"></div>
            </div>

            <!-- 权限提示 -->
            <div id="permissionWarning" class="overview-card p-6 hidden">
                <div class="text-center">
                    <div class="text-4xl mb-3">⚠️</div>
                    <h3 class="text-lg font-semibold text-on-base mb-2">权限不足</h3>
                    <p class="text-on-surface">仅 editor/admin 可访问上传页面</p>
                    <a href="#overview" class="inline-flex items-center px-6 py-3 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity mt-4">
                        返回概览
                    </a>
                </div>
            </div>

        </div>
    </div>

    <style>
        .drop-zone {
            border: 2px dashed var(--border-default, #cbd5e0);
            border-radius: 12px;
            padding: 48px 24px;
            text-align: center;
            transition: all 0.2s;
            cursor: pointer;
            background: var(--bg-surface-alt, #f7fafc);
        }
        .drop-zone:hover, .drop-zone.dragover {
            border-color: var(--accent-primary, #667eea);
            background: var(--bg-hover, #ebf8ff);
        }
        .drop-zone.border-accent {
            border-color: var(--accent-primary, #667eea);
        }
        .tab-btn {
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
        }
        .tab-active {
            background: var(--accent-primary, #667eea);
            color: var(--on-accent, white);
        }
        .tab-inactive {
            background: var(--bg-surface-alt, #e2e8f0);
            color: var(--on-surface, #4a5568);
        }
        .btn {
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
        }
        .btn-primary {
            background: var(--accent-primary, #667eea);
            color: var(--on-accent, white);
        }
        .btn-primary:hover {
            background: var(--accent-hover, #5a67d8);
        }
        .btn-success {
            background: var(--success, #38a169);
            color: white;
        }
        .btn-success:hover {
            background: var(--success-hover, #2f855a);
        }
        .input {
            width: 100%;
            padding: 8px 12px;
            border: 2px solid var(--border-default, #e2e8f0);
            border-radius: 6px;
            font-size: 14px;
            background: var(--bg-surface, white);
            color: var(--on-base, #1a202c);
        }
        .input:focus {
            outline: none;
            border-color: var(--accent-primary, #667eea);
        }
        .file-item {
            background: var(--bg-surface-alt, #f7fafc);
            border-radius: 8px;
            padding: 12px;
        }
    </style>`;

    if (container) {
        container.innerHTML = html;
    }

    // 初始化
    initUploadView();

    return html;
}

/**
 * 初始化上传视图
 */
async function initUploadView() {
    // 检查权限
    const user = window.WikiAPI?.currentUser;
    if (!user || !['editor', 'admin'].includes(user.role)) {
        document.getElementById('uploadPanel')?.classList.add('hidden');
        document.getElementById('ingestPanel')?.classList.add('hidden');
        document.getElementById('permissionWarning')?.classList.remove('hidden');
        return;
    }

    // 绑定拖拽事件
    const dropZone = document.getElementById('dropZone');
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('border-accent');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('border-accent');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('border-accent');
            const files = e.dataTransfer.files;
            handleFiles(files);
        });
    }
}

/**
 * 选中的文件列表
 */
let selectedFiles = [];

/**
 * 切换 Tab
 */
function switchTab(tab) {
    const uploadPanel = document.getElementById('uploadPanel');
    const ingestPanel = document.getElementById('ingestPanel');
    const tabUpload = document.getElementById('tab-upload');
    const tabIngest = document.getElementById('tab-ingest');

    if (!uploadPanel || !ingestPanel || !tabUpload || !tabIngest) return;

    uploadPanel.classList.toggle('hidden', tab !== 'upload');
    ingestPanel.classList.toggle('hidden', tab !== 'ingest');

    tabUpload.className = tab === 'upload' ? 'tab-btn tab-active' : 'tab-btn tab-inactive';
    tabIngest.className = tab === 'ingest' ? 'tab-btn tab-active' : 'tab-btn tab-inactive';
}

/**
 * 处理选择的文件
 */
function handleFiles(files) {
    selectedFiles = Array.from(files).filter(f => /\.(md|markdown|txt)$/i.test(f.name));

    const list = document.getElementById('fileList');
    if (!list) return;

    list.innerHTML = '';

    if (selectedFiles.length === 0) {
        list.innerHTML = '<p class="text-sm text-on-muted">未选择有效文件</p>';
        return;
    }

    let html = '';
    for (const f of selectedFiles) {
        const size = (f.size / 1024).toFixed(1);
        html += `
            <div class="file-item flex items-center justify-between">
                <div>
                    <p class="font-medium text-on-base">${escapeHtml(f.name)}</p>
                    <p class="text-xs text-on-muted">${size} KB</p>
                </div>
                <span class="text-xs text-on-muted">待上传</span>
            </div>`;
    }
    html += `<button onclick="window.UploadView.uploadFiles()" class="btn btn-success mt-2">上传 ${selectedFiles.length} 个文件</button>`;
    list.innerHTML = html;
}

/**
 * 上传文件
 */
async function uploadFiles() {
    const result = document.getElementById('uploadResult');
    if (!result) return;

    result.innerHTML = '<p class="text-sm text-on-surface">上传中...</p>';

    let success = 0, failed = 0;
    let details = '';

    for (const f of selectedFiles) {
        try {
            const formData = new FormData();
            formData.append('file', f);

            // 统一走 WikiAPI（postForm 处理 multipart/FormData，内置 401 跳转）
            const data = await WikiAPI.postForm('/api/ingest/upload', formData);

            if (data.status === 'ok') {
                success++;
                details += `<p style="color: var(--success, #38a169);">✓ ${escapeHtml(f.name)}: ${escapeHtml(data.message || '成功')}</p>`;
            } else {
                failed++;
                details += `<p style="color: var(--error, #e53e3e);">✗ ${escapeHtml(f.name)}: ${escapeHtml(data.error || '失败')}</p>`;
            }
        } catch (e) {
            failed++;
            details += `<p style="color: var(--error, #e53e3e);">✗ ${escapeHtml(f.name)}: ${escapeHtml(e.message)}</p>`;
        }
    }

    result.innerHTML = `
        <div class="file-item">
            <p class="font-medium text-on-base mb-2">上传完成：成功 ${success} 个，失败 ${failed} 个</p>
            ${details}
        </div>`;

    if (success > 0) {
        document.getElementById('fileList').innerHTML = '';
        selectedFiles = [];
    }
}

/**
 * 路径摄入
 */
async function ingestPath() {
    const path = document.getElementById('ingestPath')?.value?.trim();
    if (!path) {
        alert('请输入路径');
        return;
    }

    const result = document.getElementById('ingestResult');
    if (!result) return;

    result.innerHTML = '<p class="text-sm text-on-surface">摄入中...</p>';

    try {
        const r = await window.WikiAPI.post('/api/ingest', { source: path });

        if (r.status === 'ok') {
            result.innerHTML = `
                <div class="file-item" style="background: var(--success-bg, #c6f6d5); color: var(--success, #22543d);">
                    ✓ 摄入成功: ${escapeHtml(r.source || path)}
                </div>`;
        } else {
            result.innerHTML = `
                <div class="file-item" style="background: var(--error-bg, #fed7d7); color: var(--error, #c53030);">
                    ✗ ${escapeHtml(r.error || '摄入失败')}
                </div>`;
        }
    } catch (e) {
        result.innerHTML = `
            <div class="file-item" style="background: var(--error-bg, #fed7d7); color: var(--error, #c53030);">
                ✗ ${escapeHtml(e.message)}
            </div>`;
    }
}

// 导出全局方法
window.UploadView = {
    switchTab,
    handleFiles,
    uploadFiles,
    ingestPath
};

export default {
    render: render,
    name: '上传',
    icon: '📤'
};
