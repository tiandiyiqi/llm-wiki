/**
 * Webhook 视图模块（完整功能）
 *
 * 功能：
 * - Webhook 列表卡片渲染
 * - 平台徽章（企业微信/钉钉/飞书/自定义）
 * - 添加弹窗（名称、平台、URL、事件、密钥）
 * - 测试发送按钮
 * - 删除确认
 */

import { escapeHtml } from '../utils/ui-components.js';

// 全局状态
let currentWebhooks = [];

// 平台名称映射
const PLATFORM_NAMES = {
    wechat: '企业微信',
    dingtalk: '钉钉',
    feishu: '飞书',
    custom: '自定义'
};

/**
 * 渲染 Webhook 视图
 */
export function render(container) {
    const html = `<div class="webhooks-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- 标题卡片 -->
            <div class="overview-card text-center mb-6" style="padding: 32px;">
                <h1 class="text-2xl font-bold gradient-title mb-2">🔔 消息通知配置</h1>
                <p class="text-on-surface">多渠道消息通知集成</p>
            </div>

            <!-- 功能介绍卡片 -->
            <div class="overview-card mb-6 bg-info-container border-l-4 border-info">
                <h3 class="font-semibold text-info mb-1">📢 多渠道消息通知</h3>
                <p class="text-sm text-on-surface">配置企业微信/钉钉/飞书 Webhook，自动推送审批通知、评论提醒、内容更新等事件。</p>
            </div>

            <!-- Webhook 列表卡片 -->
            <div class="overview-card mb-6">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-lg font-semibold text-on-base">已配置的 Webhook</h2>
                    <div class="flex gap-3">
                        <button onclick="window.WebhooksView.showAddModal()" class="btn-primary">
                            + 添加 Webhook
                        </button>
                        <button onclick="window.WebhooksView.testAll()" class="btn-secondary">
                            测试发送
                        </button>
                    </div>
                </div>
                <div id="webhookList" class="space-y-3">
                    <div class="text-center text-on-muted py-8">加载中...</div>
                </div>
            </div>

            <!-- 事件类型说明卡片 -->
            <div class="overview-card">
                <h2 class="text-lg font-semibold text-on-base mb-3">支持的事件类型</h2>
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 text-sm">
                    <div class="bg-bg-surface-alt p-3 rounded">
                        <code class="text-brand-primary">all</code>
                        <span class="text-on-muted"> - 所有事件</span>
                    </div>
                    <div class="bg-bg-surface-alt p-3 rounded">
                        <code class="text-brand-primary">submit</code>
                        <span class="text-on-muted"> - 提交审核</span>
                    </div>
                    <div class="bg-bg-surface-alt p-3 rounded">
                        <code class="text-brand-primary">approve</code>
                        <span class="text-on-muted"> - 审核通过</span>
                    </div>
                    <div class="bg-bg-surface-alt p-3 rounded">
                        <code class="text-brand-primary">reject</code>
                        <span class="text-on-muted"> - 审核驳回</span>
                    </div>
                    <div class="bg-bg-surface-alt p-3 rounded">
                        <code class="text-brand-primary">comment</code>
                        <span class="text-on-muted"> - 新评论</span>
                    </div>
                    <div class="bg-bg-surface-alt p-3 rounded">
                        <code class="text-brand-primary">publish</code>
                        <span class="text-on-muted"> - 内容发布</span>
                    </div>
                    <div class="bg-bg-surface-alt p-3 rounded">
                        <code class="text-brand-primary">share_create</code>
                        <span class="text-on-muted"> - 创建分享</span>
                    </div>
                    <div class="bg-bg-surface-alt p-3 rounded">
                        <code class="text-brand-primary">qa_ask</code>
                        <span class="text-on-muted"> - AI 问答</span>
                    </div>
                    <div class="bg-bg-surface-alt p-3 rounded">
                        <code class="text-brand-primary">test</code>
                        <span class="text-on-muted"> - 测试通知</span>
                    </div>
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
    window.WebhooksView = {
        loadWebhooks,
        showAddModal,
        hideAddModal,
        createWebhook,
        removeWebhook,
        testWebhook,
        testAll
    };

    // 自动加载 Webhook 列表
    setTimeout(() => loadWebhooks(), 100);
}

/**
 * 加载 Webhook 列表
 */
async function loadWebhooks() {
    const listEl = document.getElementById('webhookList');

    listEl.innerHTML = '<div class="text-center text-on-muted py-8">加载中...</div>';

    try {
        const data = await WikiAPI.get('/api/webhooks');
        currentWebhooks = data.webhooks || [];
        renderWebhooks();
    } catch (e) {
        listEl.innerHTML = `<div class="text-center text-error py-8">加载失败: ${escapeHtml(e.message)}</div>`;
    }
}

/**
 * 渲染 Webhook 列表
 */
function renderWebhooks() {
    const container = document.getElementById('webhookList');

    if (currentWebhooks.length === 0) {
        container.innerHTML = '<div class="text-center text-on-muted py-8">暂无 Webhook 配置，点击"添加 Webhook"开始</div>';
        return;
    }

    container.innerHTML = currentWebhooks.map(w => {
        const platformClass = getPlatformClass(w.platform);
        const shortUrl = w.url.length > 60 ? w.url.substring(0, 60) + '...' : w.url;

        return `
        <div class="border border-border rounded-lg p-4 bg-bg-surface">
            <div class="flex items-center justify-between">
                <div class="flex-1">
                    <div class="flex items-center gap-2 mb-1">
                        <strong class="text-on-base">${escapeHtml(w.name)}</strong>
                        <span class="${platformClass} px-2 py-0.5 rounded text-xs font-medium">
                            ${PLATFORM_NAMES[w.platform] || w.platform}
                        </span>
                        ${w.active
                            ? '<span class="text-xs text-success">● 启用</span>'
                            : '<span class="text-xs text-on-muted">○ 停用</span>'
                        }
                    </div>
                    <div class="text-xs text-on-muted mb-1">
                        URL: ${escapeHtml(shortUrl)}
                    </div>
                    <div class="text-xs text-on-muted">
                        订阅事件: ${(w.events || ['all']).map(e =>
                            `<code class="bg-bg-surface-alt px-1 rounded">${escapeHtml(e)}</code>`
                        ).join(' ')}
                        · 访问次数: ${w.views || 0}
                        · 创建于: ${formatDate(w.created_at)}
                    </div>
                </div>
                <div class="flex gap-2">
                    <button onclick="window.WebhooksView.testWebhook('${w.id}')"
                            class="btn-secondary text-sm">
                        测试
                    </button>
                    <button onclick="window.WebhooksView.removeWebhook('${w.id}', '${escapeHtml(w.name)}')"
                            class="btn-danger text-sm">
                        删除
                    </button>
                </div>
            </div>
        </div>
        `;
    }).join('');
}

/**
 * 获取平台徽章样式类
 */
function getPlatformClass(platform) {
    const classMap = {
        wechat: 'bg-success-container text-success',
        dingtalk: 'bg-info-container text-info',
        feishu: 'bg-purple-100 text-purple-700',
        custom: 'bg-bg-surface-alt text-on-muted'
    };
    return classMap[platform] || 'bg-bg-surface-alt text-on-muted';
}

/**
 * 显示添加 Webhook 弹窗
 */
function showAddModal() {
    const modalHtml = `
    <div id="webhook-modal-overlay" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
         onclick="if(event.target.id==='webhook-modal-overlay') window.WebhooksView.hideAddModal()">
        <div class="bg-bg-surface rounded-lg shadow-xl p-6 max-w-lg w-full mx-4">
            <h3 class="text-lg font-semibold text-on-base mb-4">添加 Webhook</h3>

            <!-- 表单字段 -->
            <div class="space-y-3">
                <div>
                    <label class="block text-sm font-medium text-on-base mb-1">名称</label>
                    <input type="text" id="webhookName"
                           class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm"
                           placeholder="例如：团队群通知">
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-base mb-1">平台</label>
                    <select id="webhookPlatform"
                            class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm">
                        <option value="wechat">企业微信</option>
                        <option value="dingtalk">钉钉</option>
                        <option value="feishu">飞书</option>
                        <option value="custom">自定义</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-base mb-1">Webhook URL</label>
                    <input type="text" id="webhookUrl"
                           class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm"
                           placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx">
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-base mb-1">订阅事件（逗号分隔，留空表示全部）</label>
                    <input type="text" id="webhookEvents"
                           class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm"
                           placeholder="例如：submit,approve,reject">
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-base mb-1">签名密钥（可选）</label>
                    <input type="text" id="webhookSecret"
                           class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm"
                           placeholder="用于签名验证">
                </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-3 justify-end mt-6">
                <button onclick="window.WebhooksView.hideAddModal()" class="btn-secondary">
                    取消
                </button>
                <button onclick="window.WebhooksView.createWebhook()" class="btn-primary">
                    创建
                </button>
            </div>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * 隐藏添加弹窗
 */
function hideAddModal() {
    const overlay = document.getElementById('webhook-modal-overlay');
    if (overlay) {
        overlay.remove();
    }
}

/**
 * 创建 Webhook
 */
async function createWebhook() {
    const name = document.getElementById('webhookName').value.trim();
    const platform = document.getElementById('webhookPlatform').value;
    const url = document.getElementById('webhookUrl').value.trim();
    const eventsStr = document.getElementById('webhookEvents').value.trim();
    const secret = document.getElementById('webhookSecret').value.trim();

    if (!name || !url) {
        alert('名称和 URL 不能为空');
        return;
    }

    const events = eventsStr ? eventsStr.split(',').map(s => s.trim()).filter(Boolean) : ['all'];

    try {
        const result = await WikiAPI.post('/api/webhooks', {
            name,
            platform,
            url,
            events,
            secret
        });

        if (result.success || result.id) {
            hideAddModal();
            await loadWebhooks();
        } else {
            alert('添加失败: ' + (result.error || '未知错误'));
        }
    } catch (e) {
        alert('添加失败: ' + e.message);
    }
}

/**
 * 删除 Webhook
 */
async function removeWebhook(id, name) {
    if (!confirm(`确认删除 Webhook "${name}"？`)) return;

    try {
        const result = await WikiAPI.delete('/api/webhooks/' + id);

        if (result.success) {
            await loadWebhooks();
        } else {
            alert('删除失败: ' + (result.error || '未知错误'));
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

/**
 * 测试单个 Webhook
 */
async function testWebhook(id) {
    try {
        const result = await WikiAPI.post('/api/webhooks/test', { webhook_id: id });

        if (result.success) {
            alert('测试通知已发送');
        } else {
            alert('测试失败: ' + (result.error || '未知错误'));
        }
    } catch (e) {
        alert('测试失败: ' + e.message);
    }
}

/**
 * 测试所有 Webhook
 */
async function testAll() {
    try {
        const result = await WikiAPI.post('/api/webhooks/test');

        if (result.sent_count > 0) {
            alert(`测试通知已发送到 ${result.sent_count} 个 Webhook`);
        } else {
            alert('没有可用的 Webhook（请检查是否启用）');
        }
    } catch (e) {
        alert('测试失败: ' + e.message);
    }
}

/**
 * 格式化日期
 */
function formatDate(iso) {
    if (!iso) return '-';
    try {
        return new Date(iso).toLocaleString('zh-CN');
    } catch (e) {
        return iso;
    }
}

export default {
    render,
    name: 'Webhook',
    icon: '🔔'
};