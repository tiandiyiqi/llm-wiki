/**
 * 文件预览初始化
 *
 * 处理文件列表点击事件，触发预览。
 */

document.addEventListener('DOMContentLoaded', function() {
    // 查找所有预览按钮
    const previewButtons = document.querySelectorAll('[data-preview-url]');

    previewButtons.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();

            const fileUrl = this.dataset.previewUrl;
            const fileName = this.dataset.previewName || this.textContent.trim();

            if (window.FilePreview) {
                FilePreview.openModal(fileUrl, fileName);
            } else {
                // 降级：在新窗口打开
                window.open(fileUrl, '_blank');
            }
        });
    });

    // 查找所有文件名链接
    const fileLinks = document.querySelectorAll('.file-name-link[data-file-url]');

    fileLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            const fileUrl = this.dataset.fileUrl;
            const fileName = this.textContent.trim();

            if (window.FilePreview) {
                FilePreview.openModal(fileUrl, fileName);
            } else {
                window.open(fileUrl, '_blank');
            }
        });
    });
});

/**
 * 为文件列表添加预览按钮
 *
 * @param {string} containerSelector 文件列表容器选择器
 * @param {Function} getFileUrl 获取文件 URL 的函数
 */
function initFilePreview(containerSelector, getFileUrl) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    const fileItems = container.querySelectorAll('[data-file-id]');

    fileItems.forEach(function(item) {
        const fileId = item.dataset.fileId;
        const fileName = item.dataset.fileName || item.querySelector('.file-name')?.textContent || '文件';

        // 创建预览按钮
        const previewBtn = document.createElement('button');
        previewBtn.className = 'preview-btn';
        previewBtn.textContent = '预览';
        previewBtn.dataset.previewUrl = '/api/files/' + fileId + '/download';
        previewBtn.dataset.previewName = fileName;

        previewBtn.addEventListener('click', function(e) {
            e.preventDefault();
            FilePreview.openModal(this.dataset.previewUrl, this.dataset.previewName);
        });

        // 添加到文件项
        const actionsCell = item.querySelector('.actions') || item;
        actionsCell.appendChild(previewBtn);
    });
}

// 导出
window.initFilePreview = initFilePreview;
