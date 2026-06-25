/**
 * 知识库管理视图模块
 *
 * 功能：
 * - 3 个 Tab：知识库列表、层级树、成员管理
 * - 知识库表格（7 列）
 * - 层级树视图（递归渲染 + 展开/折叠）
 * - 成员管理表格
 * - 4 个弹窗：创建知识库、编辑知识库、添加成员、统计信息
 */

import { escapeHtml } from '../utils/ui-components.js';

// 模块状态
let currentTab = 'list';
let allKBs = [];
let allUsers = [];

/**
 * 渲染主视图
 */
export function render(container) {
    const html = `
<div class="kb-management-view animate-fade-in">
    <!-- Tab 切换 -->
    <div class="overview-container p-6">
        <div class="flex flex-wrap gap-2 mb-6">
            <button onclick="window.KBManagement.switchTab('list')" id="kb-tab-list" class="btn btn-primary">
                知识库列表
            </button>
            <button onclick="window.KBManagement.switchTab('tree')" id="kb-tab-tree" class="btn btn-secondary">
                层级树
            </button>
            <button onclick="window.KBManagement.switchTab('members')" id="kb-tab-members" class="btn btn-secondary">
                成员管理
            </button>
        </div>

        <!-- 知识库列表 -->
        <div id="kb-list-panel" class="overview-card p-6">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-lg font-bold text-on-base">知识库列表</h2>
                <div class="flex gap-2">
                    <select id="kb-level-filter" onchange="window.KBManagement.loadKBs()" class="input w-auto">
                        <option value="">全部层级</option>
                        <option value="personal">个人</option>
                        <option value="department">部门</option>
                        <option value="project">项目</option>
                        <option value="company">公司</option>
                        <option value="standalone">独立</option>
                    </select>
                    <button onclick="window.KBManagement.showCreateKBModal()" class="btn btn-primary">
                        + 创建知识库
                    </button>
                </div>
            </div>

            <!-- 加载状态 -->
            <div id="kb-loading" class="text-center py-8 hidden">
                <div class="animate-spin inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
                <p class="text-on-muted mt-2">加载中...</p>
            </div>

            <!-- 知识库表格 -->
            <div class="overflow-x-auto">
                <table class="w-full" id="kb-table">
                    <thead>
                        <tr class="border-b-2 border-gray-200 text-left text-on-muted">
                            <th class="py-3 px-4">ID</th>
                            <th class="py-3 px-4">名称</th>
                            <th class="py-3 px-4">层级/类型</th>
                            <th class="py-3 px-4">路径</th>
                            <th class="py-3 px-4">原子数</th>
                            <th class="py-3 px-4">创建时间</th>
                            <th class="py-3 px-4">操作</th>
                        </tr>
                    </thead>
                    <tbody id="kb-table-body"></tbody>
                </table>
            </div>
        </div>

        <!-- 层级树 -->
        <div id="kb-tree-panel" class="overview-card p-6 hidden">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-lg font-bold text-on-base">知识库层级树</h2>
                <button onclick="window.KBManagement.loadKBTree()" class="btn btn-secondary">刷新</button>
            </div>
            <div id="kb-tree-container" class="space-y-2">
                <p class="text-on-muted text-center py-8">加载中...</p>
            </div>
        </div>

        <!-- 成员管理 -->
        <div id="kb-members-panel" class="overview-card p-6 hidden">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-lg font-bold text-on-base">成员管理</h2>
                <select id="kb-member-select" onchange="window.KBManagement.loadMembers()" class="input w-auto">
                    <option value="">选择知识库...</option>
                </select>
            </div>
            <div id="kb-members-content" class="overflow-x-auto">
                <p class="text-on-muted text-center py-8">请先选择知识库</p>
            </div>
        </div>
    </div>

    <!-- 弹窗容器 -->
    <div id="kb-modals-container"></div>
</div>`;

    if (container) {
        container.innerHTML = html;
    }

    // 初始化模块
    initKBManagement();

    return html;
}

/**
 * 初始化模块
 */
async function initKBManagement() {
    // 暴露到全局
    window.KBManagement = {
        switchTab,
        loadKBs,
        loadKBTree,
        loadMembers,
        showCreateKBModal,
        showEditKBModal,
        deleteKB,
        createKB,
        updateKB,
        showStats,
        showAddMemberModal,
        addMember,
        changeMemberRole,
        removeMember,
        closeModal,
        toggleTreeNode
    };

    // 并行加载数据
    await Promise.all([
        loadKBs(),
        loadUsers()
    ]);
}

/**
 * 切换 Tab
 */
function switchTab(tab) {
    currentTab = tab;

    // 切换面板显示
    document.getElementById('kb-list-panel').classList.toggle('hidden', tab !== 'list');
    document.getElementById('kb-tree-panel').classList.toggle('hidden', tab !== 'tree');
    document.getElementById('kb-members-panel').classList.toggle('hidden', tab !== 'members');

    // 切换按钮样式
    ['list', 'tree', 'members'].forEach(t => {
        const btn = document.getElementById(`kb-tab-${t}`);
        if (btn) {
            btn.className = tab === t ? 'btn btn-primary' : 'btn btn-secondary';
        }
    });

    // 切换到层级树时自动加载
    if (tab === 'tree') {
        loadKBTree();
    }
}

/**
 * 加载知识库列表
 */
async function loadKBs() {
    const loading = document.getElementById('kb-loading');
    const tbody = document.getElementById('kb-table-body');

    loading.classList.remove('hidden');
    tbody.innerHTML = '';

    try {
        const level = document.getElementById('kb-level-filter').value;
        const url = level
            ? `/api/enterprise/kbs?level=${level}`
            : '/api/enterprise/kbs';

        const data = await WikiAPI.get(url);
        allKBs = data.kbs || [];

        if (allKBs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="py-8 text-center text-on-muted">暂无知识库</td></tr>';
            return;
        }

        // 更新成员管理选择器
        const memberSelect = document.getElementById('kb-member-select');
        memberSelect.innerHTML = '<option value="">选择知识库...</option>';
        allKBs.forEach(kb => {
            memberSelect.innerHTML += `<option value="${kb.id}">${kb.name} (${kb.type || kb.level || 'standalone'})</option>`;
        });

        // 渲染表格
        for (const kb of allKBs) {
            const levelBadge = getLevelBadge(kb.type || kb.level || 'standalone');
            const atomCount = kb.atom_count || kb.stats?.atom_count || 0;

            tbody.innerHTML += `
                <tr class="border-b border-gray-100 hover:bg-gray-50">
                    <td class="py-3 px-4 font-mono text-sm">${kb.id}</td>
                    <td class="py-3 px-4 font-medium">${escapeHtml(kb.name)}</td>
                    <td class="py-3 px-4">${levelBadge}</td>
                    <td class="py-3 px-4 font-mono text-sm text-on-muted">${escapeHtml(kb.path || '-')}</td>
                    <td class="py-3 px-4">${atomCount}</td>
                    <td class="py-3 px-4 text-sm text-on-muted">${(kb.created_at || kb.created || '').slice(0, 10)}</td>
                    <td class="py-3 px-4">
                        <button onclick="window.KBManagement.showStats(${kb.id})" class="btn btn-secondary text-xs mr-1">统计</button>
                        <button onclick="window.KBManagement.showEditKBModal(${kb.id})" class="btn btn-secondary text-xs mr-1">编辑</button>
                        <button onclick="window.KBManagement.deleteKB(${kb.id}, '${escapeHtml(kb.name)}')" class="btn btn-danger text-xs">删除</button>
                    </td>
                </tr>
            `;
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-red-500">加载失败: ${escapeHtml(e.message)}</td></tr>`;
    } finally {
        loading.classList.add('hidden');
    }
}

/**
 * 加载层级树
 */
async function loadKBTree() {
    const container = document.getElementById('kb-tree-container');
    container.innerHTML = '<p class="text-on-muted text-center py-8">加载中...</p>';

    try {
        const data = await WikiAPI.get('/api/enterprise/kbs/tree');
        const tree = data.tree || [];

        if (tree.length === 0) {
            container.innerHTML = '<p class="text-on-muted text-center py-8">暂无层级数据</p>';
            return;
        }

        container.innerHTML = renderTree(tree, 0);
    } catch (e) {
        container.innerHTML = `<p class="text-red-500 text-center py-8">加载失败: ${escapeHtml(e.message)}</p>`;
    }
}

/**
 * 渲染树节点（递归）
 */
function renderTree(nodes, depth) {
    return nodes.map(node => {
        const levelBadge = getLevelBadge(node.type || 'standalone');
        const hasChildren = node.children && node.children.length > 0;
        const indent = depth * 20;

        return `
            <div class="tree-node" style="margin-left: ${indent}px">
                <div class="flex items-center gap-2 p-2 hover:bg-gray-50 rounded">
                    <span class="tree-toggle cursor-pointer ${hasChildren ? '' : 'opacity-0'}" onclick="window.KBManagement.toggleTreeNode(this)">
                        ${hasChildren ? '▶' : '•'}
                    </span>
                    <span class="font-medium">${escapeHtml(node.name)}</span>
                    ${levelBadge}
                    <span class="text-xs text-on-muted">(${node.atom_count || 0} 原子)</span>
                </div>
                ${hasChildren ? `<div class="tree-children hidden">${renderTree(node.children, depth + 1)}</div>` : ''}
            </div>
        `;
    }).join('');
}

/**
 * 展开/折叠树节点
 */
function toggleTreeNode(el) {
    const children = el.parentElement.nextElementSibling;
    if (!children) return;

    const isHidden = children.classList.contains('hidden');
    children.classList.toggle('hidden');
    el.textContent = isHidden ? '▼' : '▶';
}

/**
 * 加载用户列表
 */
async function loadUsers() {
    try {
        const data = await WikiAPI.get('/api/users');
        allUsers = data.users || [];
    } catch (e) {
        console.error('加载用户失败:', e);
    }
}

/**
 * 加载成员列表
 */
async function loadMembers() {
    const kbId = document.getElementById('kb-member-select').value;
    const content = document.getElementById('kb-members-content');

    if (!kbId) {
        content.innerHTML = '<p class="text-on-muted text-center py-8">请先选择知识库</p>';
        return;
    }

    content.innerHTML = '<p class="text-on-muted text-center py-8">加载中...</p>';

    try {
        const data = await WikiAPI.get(`/api/enterprise/kbs/${kbId}/members`);
        const members = data.members || [];

        if (members.length === 0) {
            content.innerHTML = `
                <div class="text-center py-8">
                    <p class="text-on-muted">此知识库暂无成员</p>
                    <button onclick="window.KBManagement.showAddMemberModal(${kbId})" class="btn btn-primary mt-4">+ 添加成员</button>
                </div>
            `;
            return;
        }

        content.innerHTML = `
            <div class="flex justify-end mb-4">
                <button onclick="window.KBManagement.showAddMemberModal(${kbId})" class="btn btn-primary">+ 添加成员</button>
            </div>
            <table class="w-full">
                <thead>
                    <tr class="border-b-2 border-gray-200 text-left text-on-muted">
                        <th class="py-3 px-4">用户名</th>
                        <th class="py-3 px-4">角色</th>
                        <th class="py-3 px-4">添加时间</th>
                        <th class="py-3 px-4">操作</th>
                    </tr>
                </thead>
                <tbody id="members-table-body">
                    ${members.map(m => `
                        <tr class="border-b border-gray-100 hover:bg-gray-50">
                            <td class="py-3 px-4 font-medium">${escapeHtml(m.username)}</td>
                            <td class="py-3 px-4"><span class="badge badge-${m.role}">${m.role}</span></td>
                            <td class="py-3 px-4 text-sm text-on-muted">${(m.created_at || '').slice(0, 10)}</td>
                            <td class="py-3 px-4">
                                <button onclick="window.KBManagement.changeMemberRole(${kbId}, '${m.username}', '${m.role}')" class="btn btn-secondary text-xs mr-1">改角色</button>
                                <button onclick="window.KBManagement.removeMember(${kbId}, '${m.username}')" class="btn btn-danger text-xs">移除</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (e) {
        content.innerHTML = `<p class="text-red-500 text-center py-8">加载失败: ${escapeHtml(e.message)}</p>`;
    }
}

/**
 * 显示创建知识库弹窗
 */
function showCreateKBModal() {
    const container = document.getElementById('kb-modals-container');
    container.innerHTML = `
        <div id="create-kb-modal" class="modal-overlay" style="display: flex;">
            <div class="modal modal-fullscreen-mobile">
                <h3 class="text-lg font-bold mb-4">创建知识库</h3>
                <form id="create-kb-form" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">名称 *</label>
                        <input type="text" id="kb-name" class="input" placeholder="输入知识库名称" required>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">路径 *</label>
                        <input type="text" id="kb-path" class="input" placeholder="例如: /kb/engineering" required>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">层级</label>
                        <select id="kb-level" class="input">
                            <option value="standalone">独立知识库</option>
                            <option value="personal">个人知识库</option>
                            <option value="department">部门知识库</option>
                            <option value="project">项目知识库</option>
                            <option value="company">公司知识库</option>
                        </select>
                    </div>
                    <div id="parent-kb-select" class="hidden">
                        <label class="block text-sm font-medium text-on-base mb-1">父知识库</label>
                        <select id="kb-parent" class="input">
                            <option value="">无</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">描述</label>
                        <textarea id="kb-description" class="input" rows="3" placeholder="知识库描述（可选）"></textarea>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">标签</label>
                        <input type="text" id="kb-tags" class="input" placeholder="多个标签用逗号分隔">
                    </div>
                </form>
                <div class="flex gap-2 mt-6">
                    <button onclick="window.KBManagement.closeModal('create-kb-modal')" class="btn btn-secondary flex-1">取消</button>
                    <button onclick="window.KBManagement.createKB()" class="btn btn-primary flex-1">创建</button>
                </div>
            </div>
        </div>
    `;

    // 加载父知识库选项
    const parentSelect = document.getElementById('kb-parent');
    parentSelect.innerHTML = '<option value="">无</option>';
    allKBs.filter(kb => kb.type === 'parent' || kb.level === 'company' || kb.level === 'department').forEach(kb => {
        parentSelect.innerHTML += `<option value="${kb.id}">${kb.name}</option>`;
    });
}

/**
 * 创建知识库
 */
async function createKB() {
    const name = document.getElementById('kb-name').value.trim();
    const path = document.getElementById('kb-path').value.trim();
    const level = document.getElementById('kb-level').value;
    const description = document.getElementById('kb-description').value.trim();
    const tags = document.getElementById('kb-tags').value.split(',').map(t => t.trim()).filter(t => t);
    const parentId = document.getElementById('kb-parent').value;

    if (!name || !path) {
        alert('名称和路径不能为空');
        return;
    }

    try {
        const data = await WikiAPI.post('/api/enterprise/kbs', {
            name,
            path,
            type: level,
            description,
            tags,
            parent_id: parentId ? parseInt(parentId) : null
        });

        if (data.status === 'ok' || data.id) {
            closeModal('create-kb-modal');
            await loadKBs();
            alert('知识库创建成功');
        } else {
            alert(data.error || '创建失败');
        }
    } catch (e) {
        alert('创建失败: ' + e.message);
    }
}

/**
 * 显示编辑知识库弹窗
 */
function showEditKBModal(kbId) {
    const kb = allKBs.find(k => k.id === kbId);
    if (!kb) {
        alert('知识库不存在');
        return;
    }

    const container = document.getElementById('kb-modals-container');
    container.innerHTML = `
        <div id="edit-kb-modal" class="modal-overlay" style="display: flex;">
            <div class="modal modal-fullscreen-mobile">
                <h3 class="text-lg font-bold mb-4">编辑知识库</h3>
                <input type="hidden" id="edit-kb-id" value="${kbId}">
                <form id="edit-kb-form" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">名称 *</label>
                        <input type="text" id="edit-kb-name" class="input" value="${escapeHtml(kb.name || '')}" required>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">路径 *</label>
                        <input type="text" id="edit-kb-path" class="input" value="${escapeHtml(kb.path || '')}" required>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">层级</label>
                        <select id="edit-kb-level" class="input">
                            <option value="standalone" ${kb.type === 'standalone' ? 'selected' : ''}>独立知识库</option>
                            <option value="personal" ${kb.type === 'personal' ? 'selected' : ''}>个人知识库</option>
                            <option value="department" ${kb.type === 'department' ? 'selected' : ''}>部门知识库</option>
                            <option value="project" ${kb.type === 'project' ? 'selected' : ''}>项目知识库</option>
                            <option value="company" ${kb.type === 'company' ? 'selected' : ''}>公司知识库</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">描述</label>
                        <textarea id="edit-kb-description" class="input" rows="3">${escapeHtml(kb.description || '')}</textarea>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">标签</label>
                        <input type="text" id="edit-kb-tags" class="input" value="${escapeHtml((kb.tags || []).join(', '))}">
                    </div>
                </form>
                <div class="flex gap-2 mt-6">
                    <button onclick="window.KBManagement.closeModal('edit-kb-modal')" class="btn btn-secondary flex-1">取消</button>
                    <button onclick="window.KBManagement.updateKB()" class="btn btn-primary flex-1">保存</button>
                </div>
            </div>
        </div>
    `;
}

/**
 * 更新知识库
 */
async function updateKB() {
    const kbId = document.getElementById('edit-kb-id').value;
    const name = document.getElementById('edit-kb-name').value.trim();
    const path = document.getElementById('edit-kb-path').value.trim();
    const level = document.getElementById('edit-kb-level').value;
    const description = document.getElementById('edit-kb-description').value.trim();
    const tags = document.getElementById('edit-kb-tags').value.split(',').map(t => t.trim()).filter(t => t);

    if (!name || !path) {
        alert('名称和路径不能为空');
        return;
    }

    try {
        const data = await WikiAPI.put(`/api/enterprise/kbs/${kbId}`, {
            name,
            path,
            type: level,
            description,
            tags
        });

        if (data.status === 'ok') {
            closeModal('edit-kb-modal');
            await loadKBs();
            alert('知识库更新成功');
        } else {
            alert(data.error || '更新失败');
        }
    } catch (e) {
        alert('更新失败: ' + e.message);
    }
}

/**
 * 删除知识库
 */
async function deleteKB(kbId, kbName) {
    if (!confirm(`确定删除知识库 "${kbName}"？\n此操作将删除该知识库及其所有原子数据，不可恢复。`)) {
        return;
    }

    try {
        const data = await WikiAPI.delete(`/api/enterprise/kbs/${kbId}`);
        if (data.status === 'ok') {
            await loadKBs();
            alert('知识库已删除');
        } else {
            alert(data.error || '删除失败');
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

/**
 * 显示统计信息
 */
async function showStats(kbId) {
    const container = document.getElementById('kb-modals-container');
    container.innerHTML = `
        <div id="stats-modal" class="modal-overlay" style="display: flex;">
            <div class="modal modal-fullscreen-mobile">
                <h3 class="text-lg font-bold mb-4">知识库统计</h3>
                <div id="stats-content" class="space-y-4">
                    <p class="text-on-muted text-center py-4">加载中...</p>
                </div>
                <div class="flex gap-2 mt-6">
                    <button onclick="window.KBManagement.closeModal('stats-modal')" class="btn btn-secondary flex-1">关闭</button>
                </div>
            </div>
        </div>
    `;

    const content = document.getElementById('stats-content');

    try {
        const data = await WikiAPI.get(`/api/enterprise/kbs/${kbId}/stats`);
        const stats = data.stats || {};

        content.innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div class="p-4 bg-blue-50 rounded">
                    <div class="text-2xl font-bold text-blue-600">${stats.atom_count || 0}</div>
                    <div class="text-sm text-on-muted">原子总数</div>
                </div>
                <div class="p-4 bg-green-50 rounded">
                    <div class="text-2xl font-bold text-green-600">${stats.tag_count || 0}</div>
                    <div class="text-sm text-on-muted">标签数</div>
                </div>
                <div class="p-4 bg-purple-50 rounded">
                    <div class="text-2xl font-bold text-purple-600">${stats.member_count || 0}</div>
                    <div class="text-sm text-on-muted">成员数</div>
                </div>
                <div class="p-4 bg-orange-50 rounded">
                    <div class="text-2xl font-bold text-orange-600">${stats.child_count || 0}</div>
                    <div class="text-sm text-on-muted">子知识库</div>
                </div>
            </div>
            <div class="mt-4">
                <h4 class="font-medium text-on-base mb-2">按类型分布</h4>
                <div class="space-y-1">
                    ${Object.entries(stats.by_type || {}).map(([type, count]) => `
                        <div class="flex justify-between text-sm">
                            <span>${type}</span>
                            <span class="font-medium">${count}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } catch (e) {
        content.innerHTML = `<p class="text-red-500 text-center py-4">加载失败: ${escapeHtml(e.message)}</p>`;
    }
}

/**
 * 显示添加成员弹窗
 */
function showAddMemberModal(kbId) {
    const container = document.getElementById('kb-modals-container');
    container.innerHTML = `
        <div id="add-member-modal" class="modal-overlay" style="display: flex;">
            <div class="modal modal-fullscreen-mobile">
                <h3 class="text-lg font-bold mb-4">添加成员</h3>
                <input type="hidden" id="member-kb-id" value="${kbId}">
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">用户名</label>
                        <select id="member-username" class="input">
                            ${allUsers.map(u => `<option value="${u.username}">${u.username} (${u.role})</option>`).join('')}
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">角色</label>
                        <select id="member-role" class="input">
                            <option value="reader">reader（只读）</option>
                            <option value="editor">editor（编辑）</option>
                            <option value="admin">admin（管理）</option>
                        </select>
                    </div>
                </div>
                <div class="flex gap-2 mt-6">
                    <button onclick="window.KBManagement.closeModal('add-member-modal')" class="btn btn-secondary flex-1">取消</button>
                    <button onclick="window.KBManagement.addMember()" class="btn btn-primary flex-1">添加</button>
                </div>
            </div>
        </div>
    `;
}

/**
 * 添加成员
 */
async function addMember() {
    const kbId = document.getElementById('member-kb-id').value;
    const username = document.getElementById('member-username').value;
    const role = document.getElementById('member-role').value;

    if (!username) {
        alert('请选择用户');
        return;
    }

    try {
        const data = await WikiAPI.post(`/api/enterprise/kbs/${kbId}/members`, {
            username,
            role
        });

        if (data.status === 'ok') {
            closeModal('add-member-modal');
            await loadMembers();
            alert('成员已添加');
        } else {
            alert(data.error || '添加失败');
        }
    } catch (e) {
        alert('添加失败: ' + e.message);
    }
}

/**
 * 修改成员角色
 */
async function changeMemberRole(kbId, username, currentRole) {
    const roles = ['reader', 'editor', 'admin'];
    const newRole = prompt(`修改 ${username} 的角色（当前: ${currentRole}）\n可选: reader, editor, admin`, currentRole);
    if (!newRole || !roles.includes(newRole) || newRole === currentRole) return;

    try {
        await WikiAPI.put(`/api/enterprise/kbs/${kbId}/members/${username}`, { role: newRole });
        await loadMembers();
        alert('角色已修改');
    } catch (e) {
        alert('修改失败: ' + e.message);
    }
}

/**
 * 移除成员
 */
async function removeMember(kbId, username) {
    if (!confirm(`确定移除成员 "${username}"？`)) return;

    try {
        await WikiAPI.delete(`/api/enterprise/kbs/${kbId}/members/${username}`);
        await loadMembers();
        alert('成员已移除');
    } catch (e) {
        alert('移除失败: ' + e.message);
    }
}

/**
 * 关闭弹窗
 */
function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.remove();
    }
}

/**
 * 获取层级徽章
 */
function getLevelBadge(level) {
    const badgeClass = {
        'personal': 'badge-personal',
        'department': 'badge-department',
        'project': 'badge-project',
        'company': 'badge-company',
        'standalone': 'badge-standalone',
        'parent': 'badge-parent',
        'child': 'badge-child'
    }[level] || 'badge-standalone';

    return `<span class="badge ${badgeClass}">${level}</span>`;
}

export default {
    render: render,
    name: '知识库管理',
    icon: '📚'
};
