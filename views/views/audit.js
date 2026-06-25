/**
 * 审计视图模块
 *
 * 提取自 /views/admin/audit.html，改造为 SPA 模块
 * 功能：审计日志查看、筛选、导出
 */

export function render(container) {
    const html = `<div class="audit-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- Header Card -->
            <div class="overview-card text-center mb-6" style="padding: 40px;">
                <h1 class="text-3xl font-bold gradient-title mb-2">🔍 审计日志</h1>
                <p class="text-on-surface">查看系统操作记录</p>
            </div>

            <!-- 筛选栏 -->
            <div class="overview-card mb-6">
                <div class="flex flex-wrap gap-3 items-center">
                    <div>
                        <label class="text-xs text-on-muted mr-2">操作类型</label>
                        <select id="auditFilterAction" class="input-field">
                            <option value="">全部</option>
                            <option value="comment">评论</option>
                            <option value="favorite">收藏</option>
                            <option value="rate">评分</option>
                            <option value="submit">提交审核</option>
                            <option value="approve">审核通过</option>
                            <option value="reject">审核驳回</option>
                            <option value="status:published">发布</option>
                            <option value="status:archived">归档</option>
                            <option value="status:deprecated">废弃</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-xs text-on-muted mr-2">条数</label>
                        <select id="auditFilterLimit" class="input-field">
                            <option value="50">50</option>
                            <option value="100">100</option>
                            <option value="200">200</option>
                            <option value="500">500</option>
                        </select>
                    </div>
                    <button id="auditQueryBtn" class="btn-primary">查询</button>
                    <button id="auditExportBtn" class="btn-secondary">导出 JSON</button>
                    <div class="ml-auto text-sm text-on-muted">
                        共 <strong id="auditTotalCount">0</strong> 条记录
                    </div>
                </div>
            </div>

            <!-- 日志表格 -->
            <div class="overview-card overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-bg-surface-alt">
                            <tr class="text-left text-on-muted border-b border-border-color">
                                <th class="py-3 px-4">时间</th>
                                <th class="py-3 px-4">操作</th>
                                <th class="py-3 px-4">用户</th>
                                <th class="py-3 px-4">目标</th>
                                <th class="py-3 px-4">详情</th>
                            </tr>
                        </thead>
                        <tbody id="auditTableBody">
                            <tr><td colspan="5" class="text-center py-12 text-on-muted">加载中...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    </div>`;

    if (container) {
        container.innerHTML = html;
        bindEvents();
        loadAudit(); // 自动加载
    }

    return html;
}

// 模块状态
let auditData = [];

/**
 * 绑定事件
 */
function bindEvents() {
    // 查询按钮
    document.getElementById('auditQueryBtn').addEventListener('click', loadAudit);

    // 筛选器变化自动查询
    document.getElementById('auditFilterAction').addEventListener('change', loadAudit);
    document.getElementById('auditFilterLimit').addEventListener('change', loadAudit);

    // 导出按钮
    document.getElementById('auditExportBtn').addEventListener('click', exportToJSON);
}

/**
 * 加载审计日志
 */
async function loadAudit() {
    const action = document.getElementById('auditFilterAction').value;
    const limit = document.getElementById('auditFilterLimit').value;

    const params = new URLSearchParams({ limit });
    if (action) params.set('action', action);

    try {
        const data = await WikiAPI.get(`/api/audit?${params.toString()}`);
        auditData = data.entries || [];
        document.getElementById('auditTotalCount').textContent = data.count || auditData.length;
        renderTable(auditData);
    } catch (e) {
        console.error('加载审计日志失败:', e);
        document.getElementById('auditTableBody').innerHTML =
            `<tr><td colspan="5" class="text-center py-12 text-error">加载失败: ${escapeHtml(e.message)}</td></tr>`;
    }
}

/**
 * 渲染表格
 */
function renderTable(entries) {
    const tbody = document.getElementById('auditTableBody');

    if (entries.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-12 text-on-muted">📭 暂无审计日志</td></tr>`;
        return;
    }

    let html = '';
    for (const e of entries) {
        const action = e.action || '';
        const badgeClass = getActionBadgeClass(action);
        html += `
            <tr class="border-b border-border-color hover:bg-bg-surface-alt transition-colors">
                <td class="py-3 px-4 text-sm text-on-muted">${escapeHtml(e.timestamp || e.time || '-')}</td>
                <td class="py-3 px-4"><span class="badge ${badgeClass}">${escapeHtml(action)}</span></td>
                <td class="py-3 px-4 text-sm">${escapeHtml(e.user || '-')}</td>
                <td class="py-3 px-4 text-sm font-mono break-all">${escapeHtml(e.target || e.path || '-')}</td>
                <td class="py-3 px-4 text-sm text-on-muted">${escapeHtml(e.detail || '-')}</td>
            </tr>`;
    }
    tbody.innerHTML = html;
}

/**
 * 根据操作类型获取 badge 样式
 */
function getActionBadgeClass(action) {
    if (!action) return 'badge-neutral';

    if (action.includes('approve') || action.includes('publish')) return 'badge-success';
    if (action.includes('reject') || action.includes('delete') || action.includes('deprecate')) return 'badge-error';
    if (action.includes('submit') || action.includes('archive')) return 'badge-warning';
    if (action.includes('comment') || action.includes('favorite') || action.includes('rate')) return 'badge-info';

    return 'badge-neutral';
}

/**
 * 导出审计日志为 JSON
 */
function exportToJSON() {
    if (auditData.length === 0) {
        alert('暂无数据可导出');
        return;
    }

    const blob = new Blob([JSON.stringify(auditData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * HTML 转义
 */
function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[m]));
}

export default {
    render: render,
    name: '审计日志',
    icon: '🔍'
};