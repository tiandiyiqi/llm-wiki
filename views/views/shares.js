/**
 * 分享管理视图模块
 *
 * 提取自 /views/admin/shares.html，改造为 SPA 模块
 * 采用内联视图风格（overview-container + overview-card）
 */

export function render(container) {
    const html = `<div class="shares-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- Header Card -->
            <div class="overview-card text-center mb-6" style="padding: 40px;">
                <h1 class="text-3xl font-bold gradient-title mb-2">🔗 分享管理</h1>
                <p class="text-on-surface">生成加密分享链接，支持有效期、密码保护、访问次数限制</p>
            </div>

            <!-- 创建分享表单 -->
            <div class="overview-card mb-6">
                <h2 class="text-xl font-semibold text-on-base mb-4 flex items-center">
                    <span class="text-2xl mr-2">✨</span>
                    创建分享链接
                </h2>
                <div class="bg-bg-surface-alt rounded-lg p-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        <div>
                            <label class="block text-sm font-medium text-on-surface mb-2">原子 ID 或路径</label>
                            <input type="text" id="atomId" placeholder="例如：atoms/facts/测试原子"
                                class="w-full px-3 py-2 border border-border-color rounded-lg bg-bg-surface text-on-base
                                       focus:outline-none focus:ring-2 focus:ring-accent-primary">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-on-surface mb-2">有效期（天，0=永久）</label>
                            <input type="number" id="expiresInDays" value="7" min="0" max="365"
                                class="w-full px-3 py-2 border border-border-color rounded-lg bg-bg-surface text-on-base
                                       focus:outline-none focus:ring-2 focus:ring-accent-primary">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-on-surface mb-2">访问密码（可选）</label>
                            <input type="text" id="password" placeholder="留空表示无需密码"
                                class="w-full px-3 py-2 border border-border-color rounded-lg bg-bg-surface text-on-base
                                       focus:outline-none focus:ring-2 focus:ring-accent-primary">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-on-surface mb-2">最大访问次数（0=不限）</label>
                            <input type="number" id="maxViews" value="0" min="0"
                                class="w-full px-3 py-2 border border-border-color rounded-lg bg-bg-surface text-on-base
                                       focus:outline-none focus:ring-2 focus:ring-accent-primary">
                        </div>
                    </div>
                    <button onclick="SharesModule.createShare()"
                        class="px-6 py-2 bg-gradient-brand text-on-accent rounded-lg font-medium
                               hover:opacity-90 transition-opacity">
                        生成分享链接
                    </button>

                    <!-- 分享结果展示 -->
                    <div id="shareResult" class="mt-4 hidden">
                        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                            <div class="text-sm text-green-800 font-medium mb-2">✅ 分享链接已生成</div>
                            <div class="flex items-center gap-2">
                                <input type="text" id="shareUrl" readonly
                                    class="flex-1 px-3 py-2 bg-white border border-border-color rounded text-sm font-mono text-on-base">
                                <button onclick="SharesModule.copyShareUrl()"
                                    class="px-4 py-2 bg-bg-surface-alt text-on-surface rounded-lg text-sm font-medium
                                           hover:bg-border-color transition-colors">
                                    复制
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 分享链接列表 -->
            <div class="overview-card">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-semibold text-on-base flex items-center">
                        <span class="text-2xl mr-2">📋</span>
                        已创建的分享链接
                    </h2>
                    <button onclick="SharesModule.loadLinks()"
                        class="px-4 py-2 bg-bg-surface-alt text-on-surface rounded-lg text-sm font-medium
                               hover:bg-border-color transition-colors">
                        刷新
                    </button>
                </div>
                <div id="linksList" class="space-y-3">
                    <div class="text-center text-on-muted py-8">加载中...</div>
                </div>
            </div>

        </div>
    </div>`;

    if (container) {
        container.innerHTML = html;
        // 初始化加载链接列表
        SharesModule.loadLinks();
    }

    return html;
}

// 工具函数
function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[m]));
}

function formatDate(iso) {
    if (!iso) return '-';
    try {
        return new Date(iso).toLocaleString('zh-CN');
    } catch (e) {
        return iso;
    }
}

// 状态徽章样式映射
function getStatusBadge(link) {
    let status = 'active';
    let statusText = '启用';
    let statusClass = 'bg-green-100 text-green-800';

    if (!link.active) {
        status = 'revoked';
        statusText = '已回收';
        statusClass = 'bg-red-100 text-red-800';
    } else if (link.expires_at) {
        try {
            if (new Date(link.expires_at) < new Date()) {
                status = 'expired';
                statusText = '已过期';
                statusClass = 'bg-yellow-100 text-yellow-800';
            }
        } catch (e) {}
    }

    return { status, statusText, statusClass };
}

// 分享模块对象（挂载到全局供 onclick 调用）
const SharesModule = {
    async createShare() {
        const atom_id = document.getElementById('atomId').value.trim();
        const expires_in_days = parseInt(document.getElementById('expiresInDays').value) || 7;
        const password = document.getElementById('password').value.trim() || null;
        const max_views = parseInt(document.getElementById('maxViews').value) || 0;

        if (!atom_id) {
            alert('请输入原子 ID');
            return;
        }

        try {
            const data = await WikiAPI.post('/api/share', { atom_id, expires_in_days, password, max_views });

            if (data.status === 'ok' && data.link) {
                const fullUrl = window.location.origin + data.link.url;
                document.getElementById('shareUrl').value = fullUrl;
                document.getElementById('shareResult').classList.remove('hidden');
                await this.loadLinks();
            } else {
                alert('创建失败: ' + (data.error || '未知错误'));
            }
        } catch (e) {
            alert('创建失败: ' + e.message);
        }
    },

    copyShareUrl() {
        const url = document.getElementById('shareUrl').value;
        navigator.clipboard.writeText(url).then(() => {
            alert('链接已复制到剪贴板');
        }).catch(() => {
            // 降级方案
            const input = document.getElementById('shareUrl');
            input.select();
            document.execCommand('copy');
            alert('链接已复制到剪贴板');
        });
    },

    async loadLinks() {
        try {
            const data = await WikiAPI.get('/api/share');
            this.renderLinks(data.links || []);
        } catch (e) {
            document.getElementById('linksList').innerHTML =
                `<div class="text-red-500 text-center py-8">加载失败: ${e.message}</div>`;
        }
    },

    renderLinks(links) {
        const container = document.getElementById('linksList');

        if (links.length === 0) {
            container.innerHTML = '<div class="text-center text-on-muted py-8">暂无分享链接</div>';
            return;
        }

        container.innerHTML = links.map(link => {
            const { statusText, statusClass } = getStatusBadge(link);
            const fullUrl = window.location.origin + (link.url || `/share.html?token=${link.token}`);

            return `
            <div class="border border-border-color rounded-lg p-4 bg-bg-surface">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                        <strong class="text-on-base text-sm">${escapeHtml(link.atom_id)}</strong>
                        <span class="px-2 py-1 rounded text-xs ${statusClass}">${statusText}</span>
                        ${link.password ? '<span class="text-xs text-on-muted">🔒 密码保护</span>' : ''}
                    </div>
                    <div class="flex gap-2">
                        <button onclick="SharesModule.copyLink('${escapeHtml(fullUrl)}')"
                            class="px-3 py-1 bg-bg-surface-alt text-on-surface rounded text-xs font-medium
                                   hover:bg-border-color transition-colors">
                            复制链接
                        </button>
                        ${link.active ? `
                        <button onclick="SharesModule.revokeLink('${link.token}')"
                            class="px-3 py-1 bg-red-500 text-white rounded text-xs font-medium
                                   hover:bg-red-600 transition-colors">
                            回收
                        </button>
                        ` : ''}
                    </div>
                </div>
                <div class="text-xs text-on-muted mb-1">链接: ${escapeHtml(fullUrl)}</div>
                <div class="text-xs text-on-muted">
                    创建: ${formatDate(link.created_at)}
                    · 过期: ${link.expires_at ? formatDate(link.expires_at) : '永久'}
                    · 访问: ${link.views || 0}${link.max_views > 0 ? '/' + link.max_views : '（不限）'}
                </div>
            </div>
            `;
        }).join('');
    },

    copyLink(url) {
        navigator.clipboard.writeText(url).then(() => {
            alert('链接已复制');
        }).catch(() => {
            // 降级方案
            const input = document.createElement('textarea');
            input.value = url;
            document.body.appendChild(input);
            input.select();
            document.execCommand('copy');
            document.body.removeChild(input);
            alert('链接已复制');
        });
    },

    async revokeLink(token) {
        if (!confirm('确认回收此分享链接？回收后无法恢复。')) return;

        try {
            await WikiAPI.delete('/api/share/' + token);
            await this.loadLinks();
        } catch (e) {
            alert('回收失败: ' + e.message);
        }
    }
};

// 挂载到全局 window 对象，供 onclick 事件调用
window.SharesModule = SharesModule;

export default {
    render: render,
    name: '分享管理',
    icon: '🔗'
};