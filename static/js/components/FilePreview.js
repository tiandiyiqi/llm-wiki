/**
 * 文件预览组件
 *
 * 集成 Open File Viewer，提供文件在线预览能力。
 *
 * 支持：
 * - PDF（pdfjs-dist）
 * - 图片（jpg/png/gif/webp/svg/heic）
 * - 视频（mp4/webm/mov）
 * - 音频（mp3/wav/ogg/flac）
 * - 代码/文本（txt/md/json/yaml/xml/code）
 * - 简单 Office（docx/xlsx/pptx）
 *
 * 复杂 Office 需要后端转换服务（当前返回错误提示）。
 */

// 全局预览器实例
let currentViewer = null;

/**
 * 创建预览器
 *
 * @param {Object} options 配置选项
 * @param {string|HTMLElement} options.container 预览容器（选择器或元素）
 * @param {string|File|Blob} options.file 文件 URL 或 File 对象
 * @param {string} options.fileName 文件名（用于扩展名识别）
 * @param {Object} options.plugins 插件配置
 * @returns {Object} 预览器实例
 */
function createFilePreview(options) {
    const {
        container,
        file,
        fileName,
        width = '100%',
        height = '80vh',
        fit = 'contain',
        toolbar = true,
        theme = 'auto',
        onError,
        onLoad,
    } = options;

    // 销毁现有预览器
    if (currentViewer) {
        try {
            currentViewer.destroy();
        } catch (e) {
            console.warn('销毁预览器失败:', e);
        }
        currentViewer = null;
    }

    // 获取容器元素
    const containerEl = typeof container === 'string'
        ? document.querySelector(container)
        : container;

    if (!containerEl) {
        console.error('预览容器不存在:', container);
        return null;
    }

    // 清空容器
    containerEl.innerHTML = '';

    // 创建 iframe 作为预览容器（用于隔离样式）
    const iframe = document.createElement('iframe');
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.style.backgroundColor = 'transparent';
    containerEl.appendChild(iframe);

    // 写入 iframe 内容
    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
    iframeDoc.open();
    iframeDoc.write(generatePreviewHTML(file, fileName, {
        width,
        height,
        fit,
        toolbar,
        theme,
    }));
    iframeDoc.close();

    // 返回控制接口
    currentViewer = {
        iframe,
        container: containerEl,

        /**
         * 重新加载文件
         */
        reload(newFile, newFileName) {
            if (newFile && newFileName) {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                doc.open();
                doc.write(generatePreviewHTML(newFile, newFileName, {
                    width, height, fit, toolbar, theme
                }));
                doc.close();
            }
        },

        /**
         * 销毁预览器
         */
        destroy() {
            if (iframe && iframe.parentNode) {
                iframe.parentNode.removeChild(iframe);
            }
            containerEl.innerHTML = '';
            currentViewer = null;
        },

        /**
         * 调整尺寸
         */
        resize() {
            // iframe 自动适应容器
        }
    };

    return currentViewer;
}

/**
 * 生成预览 HTML
 */
function generatePreviewHTML(file, fileName, options) {
    const { width, height, fit, toolbar, theme } = options;

    // 获取文件扩展名
    const ext = fileName ? fileName.split('.').pop().toLowerCase() : '';

    // 根据文件类型选择预览方式
    const previewType = classifyPreviewType(ext);

    // CDN 基础 URL
    const pdfjsCdn = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174';

    return `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文件预览 - ${escapeHtml(fileName || '未知文件')}</title>
    <script src="${pdfjsCdn}/pdf.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: var(--bg-color, #f5f5f5);
            color: var(--text-color, #333);
            overflow: hidden;
        }

        /* 主题 */
        @media (prefers-color-scheme: dark) {
            body.auto-theme {
                --bg-color: #1a1a1a;
                --text-color: #e0e0e0;
                --border-color: #333;
            }
        }
        body.dark-theme {
            --bg-color: #1a1a1a;
            --text-color: #e0e0e0;
            --border-color: #333;
        }
        body.light-theme {
            --bg-color: #f5f5f5;
            --text-color: #333;
            --border-color: #ddd;
        }

        /* 预览容器 */
        #preview-container {
            width: 100%;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* 工具栏 */
        .toolbar {
            display: flex;
            align-items: center;
            padding: 8px 16px;
            background: var(--bg-color);
            border-bottom: 1px solid var(--border-color);
            gap: 12px;
        }
        .toolbar-title {
            flex: 1;
            font-size: 14px;
            font-weight: 500;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .toolbar-btn {
            padding: 6px 12px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: var(--bg-color);
            color: var(--text-color);
            cursor: pointer;
            font-size: 13px;
        }
        .toolbar-btn:hover {
            background: var(--border-color);
        }

        /* 内容区域 */
        .content {
            flex: 1;
            overflow: auto;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* PDF 预览 */
        .pdf-viewer {
            width: 100%;
            height: 100%;
        }
        .pdf-canvas {
            max-width: 100%;
            height: auto;
        }

        /* 图片预览 */
        .image-viewer img {
            max-width: 100%;
            max-height: calc(100vh - 50px);
            object-fit: ${fit};
        }

        /* 视频预览 */
        .video-viewer video,
        .audio-viewer audio {
            max-width: 100%;
            max-height: calc(100vh - 50px);
        }

        /* 代码预览 */
        .code-viewer {
            width: 100%;
            height: 100%;
            overflow: auto;
            padding: 16px;
            font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Code", monospace;
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-all;
        }

        /* 错误/不支持提示 */
        .error-message {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-color);
        }
        .error-message h3 {
            margin-bottom: 16px;
            color: #e74c3c;
        }
        .error-message p {
            margin-bottom: 12px;
            opacity: 0.8;
        }
        .error-message .suggestion {
            margin-top: 20px;
            padding: 16px;
            background: var(--border-color);
            border-radius: 8px;
        }

        /* Loading */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
        }
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--border-color);
            border-top-color: #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="${theme}-theme">
    <div id="preview-container">
        ${toolbar ? `
        <div class="toolbar">
            <span class="toolbar-title">${escapeHtml(fileName || '文件预览')}</span>
            <button class="toolbar-btn" onclick="downloadFile()">下载</button>
        </div>
        ` : ''}
        <div class="content" id="content">
            <div class="loading">
                <div class="spinner"></div>
            </div>
        </div>
    </div>

    <script>
        // PDF.js worker
        pdfjsLib.workerSrc = '${pdfjsCdn}/pdf.worker.min.js';

        const fileUrl = '${typeof file === 'string' ? file : ''}';
        const fileName = '${escapeHtml(fileName || '')}';
        const previewType = '${previewType}';

        // 初始化预览
        document.addEventListener('DOMContentLoaded', async () => {
            try {
                await initPreview();
            } catch (error) {
                showError(error.message || '预览失败');
            }
        });

        async function initPreview() {
            const content = document.getElementById('content');

            switch (previewType) {
                case 'pdf':
                    await renderPdf(content);
                    break;
                case 'image':
                    renderImage(content);
                    break;
                case 'video':
                    renderVideo(content);
                    break;
                case 'audio':
                    renderAudio(content);
                    break;
                case 'code':
                    await renderCode(content);
                    break;
                case 'office':
                    await renderOffice(content);
                    break;
                default:
                    showError('不支持预览此文件格式');
            }
        }

        // PDF 渲染
        async function renderPdf(container) {
            const loadingTask = pdfjsLib.getDocument(fileUrl);
            const pdf = await loadingTask.promise;

            container.innerHTML = '<div class="pdf-viewer"></div>';
            const viewer = container.querySelector('.pdf-viewer');

            for (let i = 1; i <= pdf.numPages; i++) {
                const page = await pdf.getPage(i);
                const scale = 1.5;
                const viewport = page.getViewport({ scale });

                const canvas = document.createElement('canvas');
                canvas.className = 'pdf-canvas';
                canvas.width = viewport.width;
                canvas.height = viewport.height;

                const context = canvas.getContext('2d');
                await page.render({
                    canvasContext: context,
                    viewport: viewport
                }).promise;

                viewer.appendChild(canvas);
            }
        }

        // 图片渲染
        function renderImage(container) {
            container.innerHTML = '<div class="image-viewer"><img src="' + fileUrl + '" alt="' + fileName + '"></div>';
        }

        // 视频渲染
        function renderVideo(container) {
            container.innerHTML = '<div class="video-viewer"><video controls><source src="' + fileUrl + '">您的浏览器不支持视频播放</video></div>';
        }

        // 音频渲染
        function renderAudio(container) {
            container.innerHTML = '<div class="audio-viewer"><audio controls><source src="' + fileUrl + '">您的浏览器不支持音频播放</audio></div>';
        }

        // 代码渲染
        async function renderCode(container) {
            const response = await fetch(fileUrl);
            const text = await response.text();
            container.innerHTML = '<pre class="code-viewer">' + escapeHtml(text) + '</pre>';
        }

        // Office 渲染（调用后端转换）
        async function renderOffice(container) {
            // 先尝试获取文件
            try {
                const response = await fetch(fileUrl);
                const blob = await response.blob();
                const file = new File([blob], fileName);

                // 调用转换 API
                const formData = new FormData();
                formData.append('file', file);
                formData.append('reason', 'complex-docx');

                const convertResponse = await fetch('/api/office/convert-to-pdf', {
                    method: 'POST',
                    body: formData
                });

                if (!convertResponse.ok) {
                    const error = await convertResponse.json();
                    throw new Error(error.message || '转换失败');
                }

                // 如果成功，渲染返回的 PDF
                const result = await convertResponse.json();
                if (result.pdf_url) {
                    fileUrl = result.pdf_url;
                    await renderPdf(container);
                }
            } catch (error) {
                showError(error.message, '该文档包含复杂排版，暂不支持在线预览。您可以下载后使用本地软件打开。');
            }
        }

        // 显示错误
        function showError(message, suggestion) {
            const content = document.getElementById('content');
            content.innerHTML = \`
                <div class="error-message">
                    <h3>预览失败</h3>
                    <p>\${escapeHtml(message)}</p>
                    \${suggestion ? \`
                    <div class="suggestion">
                        <p>\${escapeHtml(suggestion)}</p>
                    </div>
                    \` : ''}
                    <button class="toolbar-btn" onclick="downloadFile()" style="margin-top: 16px;">下载文件</button>
                </div>
            \`;
        }

        // 下载文件
        function downloadFile() {
            const a = document.createElement('a');
            a.href = fileUrl || '/api/files/' + encodeURIComponent(fileName) + '/download';
            a.download = fileName;
            a.click();
        }

        // HTML 转义
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
    `;
}

/**
 * 分类预览类型
 */
function classifyPreviewType(ext) {
    const extLower = ext.toLowerCase();

    // PDF
    if (extLower === 'pdf') return 'pdf';

    // 图片
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'tiff', 'heic', 'heif'];
    if (imageExts.includes(extLower)) return 'image';

    // 视频
    const videoExts = ['mp4', 'webm', 'mov', 'avi', 'mkv', 'flv', 'm3u8'];
    if (videoExts.includes(extLower)) return 'video';

    // 音频
    const audioExts = ['mp3', 'wav', 'ogg', 'aac', 'm4a', 'flac'];
    if (audioExts.includes(extLower)) return 'audio';

    // 代码/文本
    const codeExts = ['txt', 'md', 'json', 'yaml', 'yml', 'xml', 'csv',
        'js', 'ts', 'tsx', 'jsx', 'py', 'go', 'rs', 'java', 'c', 'cpp',
        'html', 'css', 'sql', 'sh', 'vue', 'svelte'];
    if (codeExts.includes(extLower)) return 'code';

    // Office
    const officeExts = ['docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt', 'odt', 'ods', 'odp'];
    if (officeExts.includes(extLower)) return 'office';

    return 'unsupported';
}

/**
 * HTML 转义
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 打开预览弹窗
 */
function openPreviewModal(fileUrl, fileName) {
    // 创建弹窗容器
    let modal = document.getElementById('preview-modal');

    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'preview-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        document.body.appendChild(modal);

        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closePreviewModal();
            }
        });
    }

    // 创建预览容器
    modal.innerHTML = `
        <div style="width: 90%; height: 90%; background: white; border-radius: 8px; overflow: hidden; position: relative;">
            <button onclick="closePreviewModal()" style="
                position: absolute;
                top: 10px;
                right: 10px;
                width: 32px;
                height: 32px;
                border: none;
                background: #333;
                color: white;
                border-radius: 50%;
                cursor: pointer;
                font-size: 18px;
                z-index: 1;
            ">×</button>
            <div id="preview-content" style="width: 100%; height: 100%;"></div>
        </div>
    `;

    modal.style.display = 'flex';

    // 创建预览器
    createFilePreview({
        container: '#preview-content',
        file: fileUrl,
        fileName: fileName,
        width: '100%',
        height: '100%',
        fit: 'contain',
        toolbar: true,
        theme: 'auto',
    });
}

/**
 * 关闭预览弹窗
 */
function closePreviewModal() {
    const modal = document.getElementById('preview-modal');
    if (modal) {
        // 销毁预览器
        if (currentViewer) {
            currentViewer.destroy();
        }
        modal.style.display = 'none';
    }
}

// 导出函数
window.FilePreview = {
    create: createFilePreview,
    openModal: openPreviewModal,
    closeModal: closePreviewModal,
    classifyType: classifyPreviewType,
};
