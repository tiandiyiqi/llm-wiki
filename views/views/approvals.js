/**
 * 审批视图模块
 *
 * 功能：
 * - Tab 切换（待审批 / 审批历史）
 * - 待审批表格渲染（GET /api/approvals/pending）
 * - 通过按钮（POST /api/atoms/:id/approve）
 * - 驳回弹窗（textarea 填原因）
 * - 审批历史表格（GET /api/approvals/history）
 * - 状态徽章（approved/rejected）
 * - 管理员权限检查
 */

// 全局状态
let currentTab = 'pending';
let pendingAtomId = null;

/**
 * 渲染审批视图
 */
export function render(container) {
    const html = `<div class="approvals-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- 标题卡片 -->
            <div class="overview-card text-center mb-6" style="padding: 32px;">
                <h1 class="text-2xl font-bold gradient-title mb-2">📝 审批中心</h1>
                <p class="text-on-surface">审核待批准的内容</p>
            </div>

            <!-- Tab 切换 -->
            <div class="overview-card mb-6">
                <div class="flex items-center gap-3 flex-wrap">
                    <button id="tab-pending" onclick="window.ApprovalsView.switchTab('pending')"
                        class="px-4 py-2 rounded-lg font-medium text-sm transition-all bg-brand-primary text-on-accent">
                        待审批
                    </button>
                    <button id="tab-history" onclick="window.ApprovalsView.switchTab('history')"
                        class="px-4 py-2 rounded-lg font-medium text-sm transition-all bg-bg-surface-alt text-on-surface hover:bg-brand-secondary">
                        审批历史
                    </button>
                </div>
            </div>

            <!-- 待审批列表 -->
            <div id="pendingPanel" class="overview-card">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-lg font-semibold text-on-base">待审批列表</h2>
                    <button onclick="window.ApprovalsView.loadPending()" class="btn-secondary text-sm">
                        🔄 刷新
                    </button>
                </div>
                <div id="pendingEmpty" class="text-center text-on-muted py-12 hidden">
                    <p class="text-lg">🎉 暂无待审批内容</p>
                </div>
                <div id="pendingTableWrapper" class="overflow-x-auto hidden">
                    <table class="w-full">
                        <thead>
                            <tr class="border-b-2 border-border text-left text-on-muted">
                                <th class="py-3 px-4">原子 ID</th>
                                <th class="py-3 px-4">提交者</th>
                                <th class="py-3 px-4">提交时间</th>
                                <th class="py-3 px-4">状态</th>
                                <th class="py-3 px-4">操作</th>
                            </tr>
                        </thead>
                        <tbody id="pendingTableBody"></tbody>
                    </table>
                </div>
            </div>

            <!-- 审批历史 -->
            <div id="historyPanel" class="overview-card hidden">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-lg font-semibold text-on-base">审批历史</h2>
                    <button onclick="window.ApprovalsView.loadHistory()" class="btn-secondary text-sm">
                        🔄 刷新
                    </button>
                </div>
                <div id="historyEmpty" class="text-center text-on-muted py-12 hidden">
                    <p class="text-lg">暂无审批历史</p>
                </div>
                <div id="historyTableWrapper" class="overflow-x-auto hidden">
                    <table class="w-full">
                        <thead>
                            <tr class="border-b-2 border-border text-left text-on-muted">
                                <th class="py-3 px-4">原子 ID</th>
                                <th class="py-3 px-4">提交者</th>
                                <th class="py-3 px-4">审核者</th>
                                <th class="py-3 px-4">结果</th>
                                <th class="py-3 px-4">时间</th>
                                <th class="py-3 px-4">备注</th>
                            </tr>
                        </thead>
                        <tbody id="historyTableBody"></tbody>
                    </table>
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
    window.ApprovalsView = {
        switchTab,
        loadPending,
        loadHistory,
        approveAtom,
        showRejectModal,
        hideRejectModal,
        confirmReject,
        checkPermission
    };

    // 检查权限并加载数据
    setTimeout(() => checkPermission(), 100);
}

/**
 * 检查管理员权限
 */
async function checkPermission() {
    try {
        const user = await WikiAPI.get('/api/auth/whoami');
        if (!user || !user.user) {
            alert('请先登录');
            window.location.hash = '#login';
            return;
        }
        if (user.user.role !== 'admin') {
            alert('仅管理员可访问审批中心');
            window.location.hash = '#overview';
            return;
        }
        // 权限验证通过，加载数据
        loadPending();
        loadHistory();
    } catch (e) {
        alert('权限检查失败: ' + e.message);
        window.location.hash = '#login';
    }
}

/**
 * 切换 Tab
 */
function switchTab(tab) {
    currentTab = tab;

    // 更新面板显示
    const pendingPanel = document.getElementById('pendingPanel');
    const historyPanel = document.getElementById('historyPanel');
    pendingPanel.classList.toggle('hidden', tab !== 'pending');
    historyPanel.classList.toggle('hidden', tab !== 'history');

    // 更新 Tab 按钮样式
    const tabPending = document.getElementById('tab-pending');
    const tabHistory = document.getElementById('tab-history');

    if (tab === 'pending') {
        tabPending.className = 'px-4 py-2 rounded-lg font-medium text-sm transition-all bg-brand-primary text-on-accent';
        tabHistory.className = 'px-4 py-2 rounded-lg font-medium text-sm transition-all bg-bg-surface-alt text-on-surface hover:bg-brand-secondary';
    } else {
        tabPending.className = 'px-4 py-2 rounded-lg font-medium text-sm transition-all bg-bg-surface-alt text-on-surface hover:bg-brand-secondary';
        tabHistory.className = 'px-4 py-2 rounded-lg font-medium text-sm transition-all bg-brand-primary text-on-accent';
    }
}

/**
 * 加载待审批列表
 */
async function loadPending() {
    const tbody = document.getElementById('pendingTableBody');
    const empty = document.getElementById('pendingEmpty');
    const tableWrapper = document.getElementById('pendingTableWrapper');

    tbody.innerHTML = '';
    empty.classList.add('hidden');
    tableWrapper.classList.add('hidden');

    try {
        const data = await WikiAPI.get('/api/approvals/pending');

        if (!data.pending || data.pending.length === 0) {
            empty.classList.remove('hidden');
            return;
        }

        tableWrapper.classList.remove('hidden');

        for (const item of data.pending) {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-border hover:bg-bg-surface-alt transition-colors';
            const atomId = item.atom_id || item.atomId || '-';

            tr.innerHTML = `
                <td class="py-3 px-4 font-mono text-sm text-on-base">${escapeHtml(atomId)}</td>
                <td class="py-3 px-4 text-on-surface">${escapeHtml(item.submitter || '-')}</td>
                <td class="py-3 px-4 text-sm text-on-muted">${escapeHtml(item.submitted_at || item.timestamp || '-')}</td>
                <td class="py-3 px-4">
                    <span class="px-2 py-1 rounded text-xs font-semibold bg-warning-container text-warning">pending</span>
                </td>
                <td class="py-3 px-4">
                    <button onclick="window.ApprovalsView.approveAtom('${escapeAttr(atomId)}')"
                        class="px-3 py-1.5 rounded text-xs font-medium bg-success-container text-success hover:opacity-80 mr-1">
                        ✓ 通过
                    </button>
                    <button onclick="window.ApprovalsView.showRejectModal('${escapeAttr(atomId)}')"
                        class="px-3 py-1.5 rounded text-xs font-medium bg-error-container text-error hover:opacity-80">
                        ✗ 驳回
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        }
    } catch (e) {
        console.error('加载待审批失败:', e);
        tbody.innerHTML = `<tr><td colspan="5" class="py-8 text-center text-error">加载失败: ${escapeHtml(e.message)}</td></tr>`;
        tableWrapper.classList.remove('hidden');
    }
}

/**
 * 加载审批历史
 */
async function loadHistory() {
    const tbody = document.getElementById('historyTableBody');
    const empty = document.getElementById('historyEmpty');
    const tableWrapper = document.getElementById('historyTableWrapper');

    tbody.innerHTML = '';
    empty.classList.add('hidden');
    tableWrapper.classList.add('hidden');

    try {
        const data = await WikiAPI.get('/api/approvals/history');

        if (!data.history || data.history.length === 0) {
            empty.classList.remove('hidden');
            return;
        }

        tableWrapper.classList.remove('hidden');

        for (const item of data.history) {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-border hover:bg-bg-surface-alt transition-colors';
            const status = item.status || 'unknown';

            // 状态徽章样式
            let badgeClass = '';
            let badgeText = '';
            if (status === 'approved') {
                badgeClass = 'bg-success-container text-success';
                badgeText = 'approved';
            } else if (status === 'rejected') {
                badgeClass = 'bg-error-container text-error';
                badgeText = 'rejected';
            } else {
                badgeClass = 'bg-info-container text-info';
                badgeText = status;
            }

            tr.innerHTML = `
                <td class="py-3 px-4 font-mono text-sm text-on-base">${escapeHtml(item.atom_id || '-')}</td>
                <td class="py-3 px-4 text-on-surface">${escapeHtml(item.submitter || '-')}</td>
                <td class="py-3 px-4 text-on-surface">${escapeHtml(item.reviewer || '-')}</td>
                <td class="py-3 px-4">
                    <span class="px-2 py-1 rounded text-xs font-semibold ${badgeClass}">${escapeHtml(badgeText)}</span>
                </td>
                <td class="py-3 px-4 text-sm text-on-muted">${escapeHtml(item.reviewed_at || item.timestamp || '-')}</td>
                <td class="py-3 px-4 text-sm text-on-muted">${escapeHtml(item.reason || item.detail || '-')}</td>
            `;
            tbody.appendChild(tr);
        }
    } catch (e) {
        console.error('加载审批历史失败:', e);
        tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-error">加载失败: ${escapeHtml(e.message)}</td></tr>`;
        tableWrapper.classList.remove('hidden');
    }
}

/**
 * 通过审批
 */
async function approveAtom(atomId) {
    if (!confirm(`确认通过此审批？\n原子: ${atomId}`)) return;

    try {
        const encoded = encodeURIComponent(atomId);
        const result = await WikiAPI.post(`/api/atoms/${encoded}/approve`);

        if (result.success) {
            alert('已审核通过');
            loadPending();
            loadHistory();
        } else {
            alert('审核失败: ' + (result.error || '未知错误'));
        }
    } catch (e) {
        alert('审核失败: ' + e.message);
    }
}

/**
 * 显示驳回弹窗
 */
function showRejectModal(atomId) {
    pendingAtomId = atomId;

    const modalHtml = `
    <div id="reject-modal-overlay" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
        onclick="if(event.target.id==='reject-modal-overlay') window.ApprovalsView.hideRejectModal()">
        <div class="bg-bg-surface rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 class="text-lg font-semibold text-on-base mb-4">驳回审批</h3>

            <!-- 信息展示 -->
            <div class="text-sm text-on-surface mb-4">
                原子 ID: <strong class="text-on-base font-mono">${escapeHtml(atomId)}</strong>
            </div>

            <!-- 驳回原因输入 -->
            <div class="mb-4">
                <label class="block text-sm font-medium text-on-base mb-1">驳回原因:</label>
                <textarea id="rejectReason"
                    class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm resize-none"
                    rows="4"
                    placeholder="请输入驳回原因..."></textarea>
            </div>

            <!-- 警告提示 -->
            <div class="bg-warning-container border-l-4 border-warning p-3 text-sm text-on-surface mb-4">
                ⚠️ 驳回后，提交者需要重新修改内容才能再次提交审批
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-3 justify-end">
                <button onclick="window.ApprovalsView.hideRejectModal()" class="btn-secondary">
                    取消
                </button>
                <button onclick="window.ApprovalsView.confirmReject()" class="btn-error">
                    确认驳回
                </button>
            </div>
        </div>
    </div>
    `;

    // 插入弹窗到 body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * 隐藏驳回弹窗
 */
function hideRejectModal() {
    const overlay = document.getElementById('reject-modal-overlay');
    if (overlay) {
        overlay.remove();
    }
    pendingAtomId = null;
}

/**
 * 确认驳回
 */
async function confirmReject() {
    if (!pendingAtomId) return;

    const reasonInput = document.getElementById('rejectReason');
    const reason = reasonInput.value.trim();

    if (!reason) {
        alert('请输入驳回原因');
        return;
    }

    try {
        const encoded = encodeURIComponent(pendingAtomId);
        const result = await WikiAPI.post(`/api/atoms/${encoded}/reject`, { reason });

        if (result.success) {
            alert('已驳回');
            hideRejectModal();
            loadPending();
            loadHistory();
        } else {
            alert('驳回失败: ' + (result.error || '未知错误'));
        }
    } catch (e) {
        alert('驳回失败: ' + e.message);
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

/**
 * 属性转义
 */
function escapeAttr(str) {
    return String(str || '').replace(/'/g, "\\'");
}

export default {
    render,
    name: '审批',
    icon: '📝'
};