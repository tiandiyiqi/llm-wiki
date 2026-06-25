/**
 * 去重视图模块（完整功能）
 *
 * 功能：
 * - 相似度阈值滑块（0.3-1.0）
 * - 重复对卡片渲染（含相似度进度条）
 * - 合并弹窗（主文档选择 + 合并策略）
 * - 重新检测按钮
 * - 合并操作 API 调用
 */

// 全局状态
let currentDuplicates = [];
let currentMergeIndex = null;

/**
 * 渲染去重视图
 */
export function render(container) {
    const html = `<div class="duplicates-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- 标题卡片 -->
            <div class="overview-card text-center mb-6" style="padding: 32px;">
                <h1 class="text-2xl font-bold gradient-title mb-2">📋 内容去重</h1>
                <p class="text-on-surface">发现和处理重复内容</p>
            </div>

            <!-- 阈值控制卡片 -->
            <div class="overview-card mb-6">
                <div class="flex items-center gap-4 flex-wrap">
                    <label class="text-sm text-on-surface font-medium">相似度阈值:</label>
                    <input type="range" id="thresholdSlider" min="0.3" max="1" step="0.05" value="0.7"
                        class="flex-1 max-w-xs accent-brand-primary cursor-pointer"
                        oninput="window.DuplicatesView.updateThresholdDisplay(this.value)">
                    <span id="thresholdValue" class="text-sm font-semibold text-brand-primary w-12">0.7</span>
                    <button onclick="window.DuplicatesView.loadDuplicates()" class="btn-secondary">
                        🔍 重新检测
                    </button>
                    <div class="ml-auto text-sm text-on-muted" id="duplicatesCount"></div>
                </div>
            </div>

            <!-- 重复内容列表 -->
            <div class="overview-card">
                <h2 class="text-lg font-semibold text-on-base mb-4">检测到的重复内容</h2>
                <div id="duplicatesList" class="space-y-4">
                    <div class="text-center text-on-muted py-8">点击"重新检测"开始</div>
                </div>
            </div>

        </div>
    </div>`;

    if (container) {
        container.innerHTML = html;
    }

    // 初始化事件
    initializeEvents();

    return html;
}

/**
 * 初始化事件监听
 */
function initializeEvents() {
    // 暴露全局接口供 onclick 使用
    window.DuplicatesView = {
        loadDuplicates,
        updateThresholdDisplay,
        showMergeModal,
        hideMergeModal,
        executeMerge
    };

    // 自动加载一次
    setTimeout(() => loadDuplicates(), 100);
}

/**
 * 更新阈值显示
 */
function updateThresholdDisplay(value) {
    document.getElementById('thresholdValue').textContent = value;
}

/**
 * 加载重复内容
 */
async function loadDuplicates() {
    const threshold = document.getElementById('thresholdSlider').value;
    const listEl = document.getElementById('duplicatesList');
    const countEl = document.getElementById('duplicatesCount');

    listEl.innerHTML = '<div class="text-center text-on-muted py-8">检测中...</div>';

    try {
        const data = await WikiAPI.get(`/api/duplicates?threshold=${threshold}`);
        currentDuplicates = data.duplicates || [];
        countEl.textContent = `共 ${currentDuplicates.length} 对重复`;
        renderDuplicates();
    } catch (e) {
        listEl.innerHTML = `<div class="text-center text-error py-8">检测失败: ${escapeHtml(e.message)}</div>`;
    }
}

/**
 * 渲染重复对列表
 */
function renderDuplicates() {
    const container = document.getElementById('duplicatesList');

    if (currentDuplicates.length === 0) {
        container.innerHTML = '<div class="text-center text-on-muted py-8">🎉 未检测到重复内容！</div>';
        return;
    }

    container.innerHTML = currentDuplicates.map((d, i) => {
        const simPercent = Math.round(d.similarity * 100);
        const simColorClass = simPercent >= 90 ? 'text-error' : simPercent >= 70 ? 'text-warning' : 'text-yellow-600';
        const barColorClass = simPercent >= 90 ? 'bg-error' : simPercent >= 70 ? 'bg-warning' : 'bg-yellow-500';

        return `
        <div class="border border-border rounded-lg p-4 bg-bg-surface">
            <div class="flex items-center justify-between mb-3">
                <div class="text-sm text-on-muted">重复对 #${i + 1}</div>
                <div class="flex items-center gap-3">
                    <span class="text-sm ${simColorClass} font-semibold">相似度: ${simPercent}%</span>
                    <button onclick="window.DuplicatesView.showMergeModal(${i})" class="btn-primary text-sm">
                        合并
                    </button>
                </div>
            </div>

            <!-- 相似度进度条 -->
            <div class="h-1.5 rounded-full bg-bg-surface-alt mb-4">
                <div class="h-full rounded-full ${barColorClass}" style="width: ${simPercent}%"></div>
            </div>

            <!-- 文档对 -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="bg-bg-surface-alt p-3 rounded">
                    <div class="text-xs text-on-muted mb-1">文档 A</div>
                    <a href="#overview?atom=${encodeURIComponent(d.atom1)}"
                       class="text-sm font-medium text-brand-primary hover:underline">
                        ${escapeHtml(d.atom1_title)}
                    </a>
                    <div class="text-xs text-on-muted mt-1">${escapeHtml(d.atom1)}</div>
                </div>
                <div class="bg-bg-surface-alt p-3 rounded">
                    <div class="text-xs text-on-muted mb-1">文档 B</div>
                    <a href="#overview?atom=${encodeURIComponent(d.atom2)}"
                       class="text-sm font-medium text-brand-primary hover:underline">
                        ${escapeHtml(d.atom2_title)}
                    </a>
                    <div class="text-xs text-on-muted mt-1">${escapeHtml(d.atom2)}</div>
                </div>
            </div>
        </div>
        `;
    }).join('');
}

/**
 * 显示合并弹窗
 */
function showMergeModal(idx) {
    const d = currentDuplicates[idx];
    currentMergeIndex = idx;

    const modalHtml = `
    <div id="merge-modal-overlay" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center" onclick="if(event.target.id==='merge-modal-overlay') window.DuplicatesView.hideMergeModal()">
        <div class="bg-bg-surface rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 class="text-lg font-semibold text-on-base mb-4">合并重复内容</h3>

            <!-- 信息展示 -->
            <div class="text-sm text-on-surface mb-4">
                将合并以下两个文档（相似度 ${Math.round(d.similarity * 100)}%）：<br>
                <strong class="text-on-base">A: ${escapeHtml(d.atom1_title)}</strong>
                <span class="text-on-muted">(${escapeHtml(d.atom1)})</span><br>
                <strong class="text-on-base">B: ${escapeHtml(d.atom2_title)}</strong>
                <span class="text-on-muted">(${escapeHtml(d.atom2)})</span>
            </div>

            <!-- 主文档选择 -->
            <div class="mb-3">
                <label class="block text-sm font-medium text-on-base mb-1">主文档（保留）:</label>
                <select id="primaryAtom" class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm">
                    <option value="${escapeHtml(d.atom1)}">A: ${escapeHtml(d.atom1_title)}</option>
                    <option value="${escapeHtml(d.atom2)}">B: ${escapeHtml(d.atom2_title)}</option>
                </select>
            </div>

            <!-- 合并策略选择 -->
            <div class="mb-3">
                <label class="block text-sm font-medium text-on-base mb-1">合并策略:</label>
                <select id="mergeStrategy" class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm">
                    <option value="append">追加（保留两者内容）</option>
                    <option value="replace">替换（用副文档覆盖主文档）</option>
                    <option value="ignore">忽略内容（仅保留主文档）</option>
                </select>
            </div>

            <!-- 警告提示 -->
            <div class="bg-warning-container border-l-4 border-warning p-3 text-sm text-on-surface mb-4">
                ⚠️ 合并后，副文档将被归档为 .merged.md 文件
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-3 justify-end">
                <button onclick="window.DuplicatesView.hideMergeModal()" class="btn-secondary">
                    取消
                </button>
                <button onclick="window.DuplicatesView.executeMerge()" class="btn-primary">
                    确认合并
                </button>
            </div>
        </div>
    </div>
    `;

    // 插入弹窗到 body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * 隐藏合并弹窗
 */
function hideMergeModal() {
    const overlay = document.getElementById('merge-modal-overlay');
    if (overlay) {
        overlay.remove();
    }
    currentMergeIndex = null;
}

/**
 * 执行合并操作
 */
async function executeMerge() {
    if (currentMergeIndex === null) return;

    const d = currentDuplicates[currentMergeIndex];
    const primary = document.getElementById('primaryAtom').value;
    const secondary = primary === d.atom1 ? d.atom2 : d.atom1;
    const strategy = document.getElementById('mergeStrategy').value;

    if (!confirm('确认合并？副文档将被归档。')) return;

    try {
        const result = await WikiAPI.post('/api/duplicates/merge', {
            primary,
            secondary,
            strategy
        });

        if (result.success) {
            alert('合并成功！' + (result.message || ''));
            hideMergeModal();
            await loadDuplicates();
        } else {
            alert('合并失败: ' + (result.error || '未知错误'));
        }
    } catch (e) {
        alert('合并失败: ' + e.message);
    }
}

/**
 * HTML 转义
 */
function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[m]));
}

export default {
    render,
    name: '去重',
    icon: '📋'
};
