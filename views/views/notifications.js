/**
 * 通知中心视图模块
 *
 * 提取自 /views/admin/notifications.html
 * 核心功能：通知列表、已读/未读状态、事件类型徽章、批量操作
 */

import { escapeHtml } from '../utils/ui-components.js';

export function render(container) {
    const html = `<div class="notifications-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- Header Card -->
            <div class="overview-card text-center mb-6" style="padding: 40px;">
                <h1 class="text-3xl font-bold gradient-title mb-2">🔔 通知中心</h1>
                <p class="text-on-surface">系统通知和提醒消息</p>
            </div>

            <!-- 操作栏 -->
            <div class="overview-card mb-6">
                <div class="flex justify-between items-center p-4 border-b border-border-th">
                    <h2 class="text-lg font-bold text-on-base">通知列表</h2>
                    <div class="flex gap-2 flex-wrap">
                        <button id="markAllReadBtn" onclick="window.NotificationsView.markAllRead()" class="px-4 py-2 text-sm bg-bg-surface-alt text-on-surface rounded-lg hover:bg-bg-hover transition-colors">
                            全部标为已读
                        </button>
                        <button onclick="window.NotificationsView.loadNotifications()" class="px-4 py-2 text-sm bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity">
                            刷新
                        </button>
                    </div>
                </div>

                <!-- 通知列表容器 -->
                <div id="notifList">
                    <div class="text-center py-12 text-on-muted">
                        <p class="text-lg">加载中...</p>
                    </div>
                </div>
            </div>

        </div>
    </div>`;

    if (container) {
        container.innerHTML = html;
    }

    // 初始化数据加载
    setTimeout(() => {
        window.NotificationsView.loadNotifications();
    }, 100);

    return html;
}

/**
 * 辅助函数：根据事件类型获取 badge 样式
 */
function getEventBadgeClass(event) {
    if (!event) return 'bg-blue-100 text-blue-800';
    if (event.includes('approve') || event.includes('success')) return 'bg-green-100 text-green-800';
    if (event.includes('reject') || event.includes('error')) return 'bg-red-100 text-red-800';
    if (event.includes('submit') || event.includes('review')) return 'bg-yellow-100 text-yellow-800';
    return 'bg-blue-100 text-blue-800';
}

/**
 * 辅助函数：事件类型中文标签
 */
function getEventLabel(event) {
    const map = {
        'review_requested': '审核请求',
        'review_approved': '审核通过',
        'review_rejected': '审核驳回',
        'atom_published': '已发布',
        'atom_archived': '已归档',
        'atom_deprecated': '已废弃',
        'comment_added': '新评论',
        'mention': '提及'
    };
    return map[event] || event || '通知';
}

/**
 * 加载通知列表
 */
async function loadNotifications() {
    const list = document.getElementById('notifList');
    if (!list) return;

    try {
        const data = await window.WikiAPI.get('/api/notifications');
        const notifs = data.notifications || [];

        if (notifs.length === 0) {
            list.innerHTML = `
                <div class="text-center py-12 text-on-muted">
                    <p class="text-lg">📭 暂无通知</p>
                </div>`;
            return;
        }

        let html = '';
        for (const n of notifs) {
            const isUnread = !n.read;
            const eventClass = getEventBadgeClass(n.event);
            const eventLabel = getEventLabel(n.event);

            html += `
                <div class="notif-item ${isUnread ? 'bg-accent-soft hover:bg-accent-med' : 'hover:bg-bg-hover'} p-4 border-b border-border-th cursor-pointer transition-colors"
                     onclick="window.NotificationsView.markRead('${n.id || ''}')">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-1 flex-wrap">
                                <span class="px-2 py-1 text-xs font-semibold rounded-full ${eventClass}">${escapeHtml(eventLabel)}</span>
                                ${isUnread ? '<span class="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">未读</span>' : ''}
                                <span class="text-xs text-on-muted">${escapeHtml(n.timestamp || n.created || '')}</span>
                            </div>
                            <p class="font-medium text-on-base">${escapeHtml(n.title || '无标题')}</p>
                            <p class="text-sm text-on-surface mt-1">${escapeHtml(n.message || n.body || '')}</p>
                        </div>
                    </div>
                </div>`;
        }

        list.innerHTML = html;
    } catch (error) {
        console.error('加载通知失败:', error);
        list.innerHTML = `
            <div class="text-center py-12 text-red-500">
                <p>加载失败: ${escapeHtml(error.message || '未知错误')}</p>
                <button onclick="window.NotificationsView.loadNotifications()" class="mt-4 px-4 py-2 text-sm bg-gradient-brand text-on-accent rounded-lg">
                    重试
                </button>
            </div>`;
    }
}

/**
 * 标记单条为已读
 */
async function markRead(id) {
    if (!id) return;

    try {
        await window.WikiAPI.post('/api/notifications/read', { id });
        await loadNotifications();
    } catch (error) {
        console.warn('标记已读失败:', error);
        // 静默失败，不影响用户体验
    }
}

/**
 * 全部标为已读
 */
async function markAllRead() {
    try {
        await window.WikiAPI.post('/api/notifications/read-all');
        await loadNotifications();
    } catch (error) {
        alert('操作失败: ' + (error.message || '未知错误'));
    }
}

// 暴露到全局作用域，供 onclick 调用
window.NotificationsView = {
    loadNotifications,
    markRead,
    markAllRead
};

export default {
    render,
    name: '通知中心',
    icon: '🔔'
};
