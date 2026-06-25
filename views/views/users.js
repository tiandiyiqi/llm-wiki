/**
 * 用户管理视图模块
 *
 * 提供用户 CRUD 和 Token 管理功能
 * - Tab 切换（用户列表 / Token 管理）
 * - 用户表格（角色修改下拉）
 * - 添加用户弹窗
 * - 生成 Token 弹窗
 * - 修改密码弹窗
 * - 删除用户确认
 * - Token 列表 + 吊销功能
 */

import { escapeHtml } from '../utils/ui-components.js';

// 全局状态
let currentTab = 'users';
let currentUser = null;
let usersList = [];
let tokensList = [];

/**
 * 渲染用户管理视图
 */
export function render(container) {
    const html = `<div class="users-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- 标题卡片 -->
            <div class="overview-card text-center mb-6" style="padding: 32px;">
                <h1 class="text-2xl font-bold gradient-title mb-2">👥 用户管理</h1>
                <p class="text-on-surface">管理系统用户和 API Token</p>
            </div>

            <!-- Tab 切换 -->
            <div class="overview-card mb-6">
                <div class="flex flex-wrap gap-2">
                    <button onclick="window.UsersView.switchTab('users')" id="tab-users" class="btn-primary">
                        用户列表
                    </button>
                    <button onclick="window.UsersView.switchTab('tokens')" id="tab-tokens" class="btn-secondary">
                        Token 管理
                    </button>
                    <div class="ml-auto text-sm text-on-muted">
                        当前用户: <strong id="currentUserName">-</strong>
                        (<span id="currentUserRole">-</span>)
                    </div>
                </div>
            </div>

            <!-- 用户列表面板 -->
            <div id="usersPanel" class="overview-card">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-lg font-semibold text-on-base">用户列表</h2>
                    <button onclick="window.UsersView.showAddUserModal()" class="btn-primary">
                        + 添加用户
                    </button>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead>
                            <tr class="border-b-2 border-border text-left text-on-muted">
                                <th class="py-3 px-4">用户名</th>
                                <th class="py-3 px-4">角色</th>
                                <th class="py-3 px-4">创建时间</th>
                                <th class="py-3 px-4">操作</th>
                            </tr>
                        </thead>
                        <tbody id="usersTableBody">
                            <tr><td colspan="4" class="py-8 text-center text-on-muted">加载中...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Token 管理面板 -->
            <div id="tokensPanel" class="overview-card hidden">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-lg font-semibold text-on-base">Token 列表</h2>
                    <button onclick="window.UsersView.showGenerateTokenModal()" class="btn-primary">
                        + 生成 Token
                    </button>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead>
                            <tr class="border-b-2 border-border text-left text-on-muted">
                                <th class="py-3 px-4">Token</th>
                                <th class="py-3 px-4">用户</th>
                                <th class="py-3 px-4">角色</th>
                                <th class="py-3 px-4">创建时间</th>
                                <th class="py-3 px-4">操作</th>
                            </tr>
                        </thead>
                        <tbody id="tokensTableBody">
                            <tr><td colspan="5" class="py-8 text-center text-on-muted">加载中...</td></tr>
                        </tbody>
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
    window.UsersView = {
        switchTab,
        loadUsers,
        loadTokens,
        showAddUserModal,
        hideAddUserModal,
        addUser,
        removeUser,
        changeRole,
        showPasswordModal,
        hidePasswordModal,
        changePassword,
        showGenerateTokenModal,
        hideGenerateTokenModal,
        generateToken,
        revokeToken
    };

    // 自动加载
    setTimeout(() => initialize(), 100);
}

/**
 * 初始化 - 检查管理员权限
 */
async function initialize() {
    try {
        const data = await WikiAPI.get('/api/auth/whoami');
        if (data.user) {
            currentUser = data.user;
            document.getElementById('currentUserName').textContent = data.user.username;
            document.getElementById('currentUserRole').textContent = data.user.role;

            // 检查管理员权限
            if (currentUser.role !== 'admin') {
                alert('仅管理员可访问用户管理页面');
                window.location.hash = '#overview';
                return;
            }

            // 加载用户和 Token 列表
            await loadUsers();
            await loadTokens();
        } else {
            window.location.hash = '#login';
        }
    } catch (e) {
        console.error('初始化失败:', e);
        window.location.hash = '#login';
    }
}

/**
 * 切换 Tab
 */
function switchTab(tab) {
    currentTab = tab;

    const usersPanel = document.getElementById('usersPanel');
    const tokensPanel = document.getElementById('tokensPanel');
    const tabUsers = document.getElementById('tab-users');
    const tabTokens = document.getElementById('tab-tokens');

    if (tab === 'users') {
        usersPanel.classList.remove('hidden');
        tokensPanel.classList.add('hidden');
        tabUsers.className = 'btn-primary';
        tabTokens.className = 'btn-secondary';
    } else {
        usersPanel.classList.add('hidden');
        tokensPanel.classList.remove('hidden');
        tabUsers.className = 'btn-secondary';
        tabTokens.className = 'btn-primary';
    }
}

/**
 * 加载用户列表
 */
async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');

    try {
        const data = await WikiAPI.get('/api/users');
        usersList = data.users || [];

        if (usersList.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="py-8 text-center text-on-muted">暂无用户</td></tr>';
            return;
        }

        tbody.innerHTML = usersList.map(u => {
            const roleBadge = getRoleBadge(u.role);
            const isSelf = currentUser && u.username === currentUser.username;
            const createdTime = (u.created || '').slice(0, 10);

            return `
            <tr class="border-b border-border">
                <td class="py-3 px-4 font-medium text-on-base">
                    ${escapeHtml(u.username)}
                    ${isSelf ? '<span class="text-xs text-on-muted ml-1">(你)</span>' : ''}
                </td>
                <td class="py-3 px-4">${roleBadge}</td>
                <td class="py-3 px-4 text-sm text-on-muted">${createdTime}</td>
                <td class="py-3 px-4">
                    <button onclick="window.UsersView.showPasswordModal('${escapeHtml(u.username)}')"
                            class="btn-secondary text-xs mr-1">改密</button>
                    <button onclick="window.UsersView.changeRole('${escapeHtml(u.username)}', '${u.role}')"
                            class="btn-secondary text-xs mr-1">改角色</button>
                    ${!isSelf ? `
                        <button onclick="window.UsersView.removeUser('${escapeHtml(u.username)}')"
                                class="btn-danger text-xs">删除</button>
                    ` : ''}
                </td>
            </tr>
            `;
        }).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" class="py-8 text-center text-error">加载失败: ${escapeHtml(e.message)}</td></tr>`;
    }
}

/**
 * 加载 Token 列表
 */
async function loadTokens() {
    const tbody = document.getElementById('tokensTableBody');

    try {
        const data = await WikiAPI.get('/api/tokens');
        tokensList = data.tokens || [];

        if (tokensList.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="py-8 text-center text-on-muted">暂无 Token</td></tr>';
            return;
        }

        tbody.innerHTML = tokensList.map(t => {
            const roleBadge = getRoleBadge(t.role);
            const createdTime = (t.created || '').slice(0, 10);

            return `
            <tr class="border-b border-border">
                <td class="py-3 px-4 font-mono text-sm text-on-base">${escapeHtml(t.token)}</td>
                <td class="py-3 px-4 text-on-base">${escapeHtml(t.username)}</td>
                <td class="py-3 px-4">${roleBadge}</td>
                <td class="py-3 px-4 text-sm text-on-muted">${createdTime}</td>
                <td class="py-3 px-4">
                    <button onclick="window.UsersView.revokeToken('${escapeHtml(t.token)}')"
                            class="btn-danger text-xs">吊销</button>
                </td>
            </tr>
            `;
        }).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" class="py-8 text-center text-error">加载失败: ${escapeHtml(e.message)}</td></tr>`;
    }
}

/**
 * 显示添加用户弹窗
 */
function showAddUserModal() {
    const modalHtml = `
    <div id="add-user-modal-overlay" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
         onclick="if(event.target.id==='add-user-modal-overlay') window.UsersView.hideAddUserModal()">
        <div class="bg-bg-surface rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 class="text-lg font-semibold text-on-base mb-4">添加用户</h3>

            <!-- 用户名 -->
            <div class="mb-3">
                <label class="block text-sm font-medium text-on-base mb-1">用户名</label>
                <input type="text" id="newUsername"
                       class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm"
                       placeholder="输入用户名">
            </div>

            <!-- 密码 -->
            <div class="mb-3">
                <label class="block text-sm font-medium text-on-base mb-1">密码</label>
                <input type="password" id="newPassword"
                       class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm"
                       placeholder="输入密码">
            </div>

            <!-- 角色 -->
            <div class="mb-4">
                <label class="block text-sm font-medium text-on-base mb-1">角色</label>
                <select id="newRole"
                        class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm">
                    <option value="reader">reader（只读）</option>
                    <option value="editor">editor（编辑）</option>
                    <option value="admin">admin（管理）</option>
                </select>
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-3 justify-end">
                <button onclick="window.UsersView.hideAddUserModal()" class="btn-secondary">
                    取消
                </button>
                <button onclick="window.UsersView.addUser()" class="btn-primary">
                    添加
                </button>
            </div>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * 隐藏添加用户弹窗
 */
function hideAddUserModal() {
    const overlay = document.getElementById('add-user-modal-overlay');
    if (overlay) {
        overlay.remove();
    }
}

/**
 * 添加用户
 */
async function addUser() {
    const username = document.getElementById('newUsername').value.trim();
    const password = document.getElementById('newPassword').value;
    const role = document.getElementById('newRole').value;

    if (!username || !password) {
        alert('用户名和密码不能为空');
        return;
    }

    try {
        const data = await WikiAPI.post('/api/users', { username, password, role });

        if (data.status === 'ok') {
            hideAddUserModal();
            await loadUsers();
        } else {
            alert(data.error || '添加失败');
        }
    } catch (e) {
        alert('添加失败: ' + e.message);
    }
}

/**
 * 删除用户
 */
async function removeUser(username) {
    if (!confirm(`确定删除用户 "${username}"？`)) return;

    try {
        await WikiAPI.delete(`/api/users/${username}`);
        await loadUsers();
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

/**
 * 修改角色
 */
async function changeRole(username, currentRole) {
    const roles = ['reader', 'editor', 'admin'];
    const newRole = prompt(`修改 ${username} 的角色（当前: ${currentRole}）`, currentRole);

    if (!newRole || !roles.includes(newRole) || newRole === currentRole) {
        return;
    }

    try {
        await WikiAPI.put(`/api/users/${username}/role`, { role: newRole });
        await loadUsers();
    } catch (e) {
        alert('修改失败: ' + e.message);
    }
}

/**
 * 显示修改密码弹窗
 */
function showPasswordModal(username) {
    const modalHtml = `
    <div id="password-modal-overlay" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
         onclick="if(event.target.id==='password-modal-overlay') window.UsersView.hidePasswordModal()">
        <div class="bg-bg-surface rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 class="text-lg font-semibold text-on-base mb-4">修改密码</h3>

            <div class="text-sm text-on-surface mb-4">
                用户: <strong class="text-on-base">${escapeHtml(username)}</strong>
            </div>

            <!-- 新密码 -->
            <div class="mb-4">
                <label class="block text-sm font-medium text-on-base mb-1">新密码</label>
                <input type="password" id="newUserPassword"
                       class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm"
                       placeholder="输入新密码">
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-3 justify-end">
                <button onclick="window.UsersView.hidePasswordModal()" class="btn-secondary">
                    取消
                </button>
                <button onclick="window.UsersView.changePassword('${escapeHtml(username)}')" class="btn-primary">
                    修改
                </button>
            </div>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * 隐藏修改密码弹窗
 */
function hidePasswordModal() {
    const overlay = document.getElementById('password-modal-overlay');
    if (overlay) {
        overlay.remove();
    }
}

/**
 * 修改密码
 */
async function changePassword(username) {
    const password = document.getElementById('newUserPassword').value;

    if (!password) {
        alert('密码不能为空');
        return;
    }

    try {
        await WikiAPI.put(`/api/users/${username}/password`, { password });
        hidePasswordModal();
        alert('密码已修改');
    } catch (e) {
        alert('修改失败: ' + e.message);
    }
}

/**
 * 显示生成 Token 弹窗
 */
async function showGenerateTokenModal() {
    // 构建用户下拉选项
    const userOptions = usersList.map(u =>
        `<option value="${escapeHtml(u.username)}">${escapeHtml(u.username)} (${u.role})</option>`
    ).join('');

    const modalHtml = `
    <div id="generate-token-modal-overlay" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
         onclick="if(event.target.id==='generate-token-modal-overlay') window.UsersView.hideGenerateTokenModal()">
        <div class="bg-bg-surface rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 class="text-lg font-semibold text-on-base mb-4">生成 API Token</h3>

            <!-- 用户选择 -->
            <div class="mb-3">
                <label class="block text-sm font-medium text-on-base mb-1">为用户生成 Token</label>
                <select id="tokenUsername"
                        class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm">
                    ${userOptions}
                </select>
            </div>

            <!-- 角色覆盖 -->
            <div class="mb-4">
                <label class="block text-sm font-medium text-on-base mb-1">角色覆盖（可选）</label>
                <select id="tokenRole"
                        class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm">
                    <option value="">使用用户默认角色</option>
                    <option value="reader">reader</option>
                    <option value="editor">editor</option>
                    <option value="admin">admin</option>
                </select>
            </div>

            <!-- Token 结果 -->
            <div id="tokenResult" class="mb-4 p-3 bg-bg-surface-alt rounded hidden">
                <p class="text-sm text-on-muted mb-1">Token 已生成（仅显示一次）：</p>
                <code id="tokenValue" class="text-sm text-on-base break-all font-mono"></code>
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-3 justify-end">
                <button onclick="window.UsersView.hideGenerateTokenModal()" class="btn-secondary">
                    关闭
                </button>
                <button onclick="window.UsersView.generateToken()" id="genTokenBtn" class="btn-primary">
                    生成
                </button>
            </div>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * 隐藏生成 Token 弹窗
 */
function hideGenerateTokenModal() {
    const overlay = document.getElementById('generate-token-modal-overlay');
    if (overlay) {
        overlay.remove();
    }
}

/**
 * 生成 Token
 */
async function generateToken() {
    const username = document.getElementById('tokenUsername').value;
    const role = document.getElementById('tokenRole').value || null;

    try {
        const data = await WikiAPI.post('/api/tokens', { username, role });

        if (data.status === 'ok') {
            document.getElementById('tokenValue').textContent = data.token;
            document.getElementById('tokenResult').classList.remove('hidden');
            await loadTokens();
        } else {
            alert(data.error || '生成失败');
        }
    } catch (e) {
        alert('生成失败: ' + e.message);
    }
}

/**
 * 吊销 Token
 */
async function revokeToken(token) {
    if (!confirm('确定吊销此 Token？')) return;

    try {
        await WikiAPI.delete(`/api/tokens/${token}`);
        await loadTokens();
    } catch (e) {
        alert('吊销失败: ' + e.message);
    }
}

/**
 * 获取角色徽章
 */
function getRoleBadge(role) {
    const classes = {
        admin: 'bg-red-100 text-red-700',
        editor: 'bg-blue-100 text-blue-700',
        reader: 'bg-green-100 text-green-700'
    };

    const cls = classes[role] || 'bg-gray-100 text-gray-700';
    return `<span class="inline-block px-2 py-1 rounded text-xs font-semibold ${cls}">${escapeHtml(role)}</span>`;
}

export default {
    render,
    name: '用户管理',
    icon: '👥'
};