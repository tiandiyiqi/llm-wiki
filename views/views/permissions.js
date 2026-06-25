/**
 * 权限管理视图模块
 *
 * 提取自 /views/admin/permissions.html（824 行）
 * 功能：角色管理、权限矩阵、用户权限查询
 * 采用内联视图风格 + Tab 切换
 */

export function render(container) {
    const html = `<div class="permissions-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- Header -->
            <div class="overview-card mb-6">
                <div class="flex justify-between items-center">
                    <h1 class="text-2xl font-bold gradient-title flex items-center">
                        <span class="text-3xl mr-3">🔐</span>
                        权限管理
                    </h1>
                    <a href="#overview" class="text-on-muted hover:text-on-surface transition-colors">
                        ← 返回概览
                    </a>
                </div>
            </div>

            <!-- Tab 切换 -->
            <div class="overview-card mb-6">
                <div class="flex flex-wrap gap-2 border-b border-border mb-4">
                    <button onclick="window.permissionsModule.switchTab('roles')" id="tab-roles" class="px-4 py-2 rounded-b-none transition-colors tab-active">
                        角色管理
                    </button>
                    <button onclick="window.permissionsModule.switchTab('matrix')" id="tab-matrix" class="px-4 py-2 rounded-b-none transition-colors">
                        权限矩阵
                    </button>
                    <button onclick="window.permissionsModule.switchTab('users')" id="tab-users" class="px-4 py-2 rounded-b-none transition-colors">
                        用户权限查询
                    </button>
                </div>
            </div>

            <!-- 角色管理面板 -->
            <div id="rolesPanel" class="overview-card mb-6">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-lg font-semibold text-on-base">角色列表</h2>
                    <button onclick="window.permissionsModule.showCreateRoleModal()" class="px-4 py-2 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity">
                        + 创建角色
                    </button>
                </div>
                <div id="rolesContent" class="overflow-x-auto">
                    <p class="text-on-muted text-center py-8">加载中...</p>
                </div>
            </div>

            <!-- 权限矩阵面板 -->
            <div id="matrixPanel" class="overview-card mb-6 hidden">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-lg font-semibold text-on-base">权限矩阵</h2>
                    <div class="flex gap-2">
                        <select id="matrixKBFilter" onchange="window.permissionsModule.loadPermissionMatrix()" class="px-3 py-2 border border-border rounded-lg bg-bg-surface">
                            <option value="">全部知识库</option>
                        </select>
                        <button onclick="window.permissionsModule.loadPermissionMatrix()" class="px-4 py-2 bg-bg-surface-alt text-on-surface rounded-lg hover:bg-bg-surface transition-colors">
                            刷新
                        </button>
                    </div>
                </div>
                <div id="matrixContent" class="overflow-x-auto">
                    <p class="text-on-muted text-center py-8">加载中...</p>
                </div>
            </div>

            <!-- 用户权限查询面板 -->
            <div id="usersPanel" class="overview-card mb-6 hidden">
                <div class="mb-4">
                    <h2 class="text-lg font-semibold text-on-base mb-4">用户权限查询</h2>
                    <div class="flex gap-2">
                        <select id="userSelect" onchange="window.permissionsModule.loadUserPermissions()" class="px-3 py-2 border border-border rounded-lg bg-bg-surface">
                            <option value="">选择用户...</option>
                        </select>
                        <button onclick="window.permissionsModule.loadUserPermissions()" class="px-4 py-2 bg-bg-surface-alt text-on-surface rounded-lg hover:bg-bg-surface transition-colors">
                            查询
                        </button>
                    </div>
                </div>
                <div id="userPermissionsContent" class="overflow-x-auto">
                    <p class="text-on-muted text-center py-8">请选择用户查看权限</p>
                </div>
            </div>

        </div>
    </div>

    <!-- 创建角色弹窗 -->
    <div id="createRoleModal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
        <div class="bg-bg-surface rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto m-4">
            <h3 class="text-lg font-bold text-on-base mb-4">创建角色</h3>
            <form id="createRoleForm" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">角色名称 *</label>
                    <input type="text" id="roleName" class="w-full px-3 py-2 border border-border rounded-lg bg-bg-surface focus:border-brand-primary" placeholder="例如: data_scientist" required>
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">显示名称 *</label>
                    <input type="text" id="roleDisplayName" class="w-full px-3 py-2 border border-border rounded-lg bg-bg-surface focus:border-brand-primary" placeholder="例如: 数据科学家" required>
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">描述</label>
                    <textarea id="roleDescription" class="w-full px-3 py-2 border border-border rounded-lg bg-bg-surface focus:border-brand-primary" rows="3" placeholder="角色描述"></textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">权限</label>
                    <div id="permissionCheckboxes" class="space-y-2">
                        ${buildPermissionCheckboxes()}
                    </div>
                </div>
            </form>
            <div class="flex gap-2 mt-6">
                <button onclick="window.permissionsModule.closeModal('createRoleModal')" class="flex-1 px-4 py-2 bg-bg-surface-alt text-on-surface rounded-lg hover:bg-bg-surface transition-colors">
                    取消
                </button>
                <button onclick="window.permissionsModule.createRole()" class="flex-1 px-4 py-2 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity">
                    创建
                </button>
            </div>
        </div>
    </div>

    <!-- 编辑角色弹窗 -->
    <div id="editRoleModal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
        <div class="bg-bg-surface rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto m-4">
            <h3 class="text-lg font-bold text-on-base mb-4">编辑角色</h3>
            <input type="hidden" id="editRoleId">
            <form id="editRoleForm" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">角色名称</label>
                    <input type="text" id="editRoleName" class="w-full px-3 py-2 border border-border rounded-lg bg-bg-surface-alt text-on-muted" disabled>
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">显示名称 *</label>
                    <input type="text" id="editRoleDisplayName" class="w-full px-3 py-2 border border-border rounded-lg bg-bg-surface focus:border-brand-primary" required>
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">描述</label>
                    <textarea id="editRoleDescription" class="w-full px-3 py-2 border border-border rounded-lg bg-bg-surface focus:border-brand-primary" rows="3"></textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">权限</label>
                    <div id="editPermissionCheckboxes" class="space-y-2">
                        ${buildPermissionCheckboxes()}
                    </div>
                </div>
            </form>
            <div class="flex gap-2 mt-6">
                <button onclick="window.permissionsModule.closeModal('editRoleModal')" class="flex-1 px-4 py-2 bg-bg-surface-alt text-on-surface rounded-lg hover:bg-bg-surface transition-colors">
                    取消
                </button>
                <button onclick="window.permissionsModule.updateRole()" class="flex-1 px-4 py-2 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity">
                    保存
                </button>
            </div>
        </div>
    </div>

    <!-- 分配权限弹窗 -->
    <div id="assignPermissionModal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
        <div class="bg-bg-surface rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto m-4">
            <h3 class="text-lg font-bold text-on-base mb-4">分配权限</h3>
            <input type="hidden" id="assignUserId">
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">用户</label>
                    <input type="text" id="assignUsername" class="w-full px-3 py-2 border border-border rounded-lg bg-bg-surface-alt text-on-muted" disabled>
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">知识库</label>
                    <select id="assignKBSelect" class="w-full px-3 py-2 border border-border rounded-lg bg-bg-surface">
                        <option value="">选择知识库...</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">角色</label>
                    <select id="assignRole" class="w-full px-3 py-2 border border-border rounded-lg bg-bg-surface">
                        <option value="reader">reader（只读）</option>
                        <option value="editor">editor（编辑）</option>
                        <option value="admin">admin（管理）</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-on-surface mb-1">自定义权限</label>
                    <div id="assignPermissionCheckboxes" class="space-y-2">
                        <label class="flex items-center text-on-surface">
                            <input type="checkbox" value="read" class="mr-2"> 读取
                        </label>
                        <label class="flex items-center text-on-surface">
                            <input type="checkbox" value="write" class="mr-2"> 写入
                        </label>
                        <label class="flex items-center text-on-surface">
                            <input type="checkbox" value="delete" class="mr-2"> 删除
                        </label>
                        <label class="flex items-center text-on-surface">
                            <input type="checkbox" value="admin" class="mr-2"> 管理
                        </label>
                    </div>
                </div>
            </div>
            <div class="flex gap-2 mt-6">
                <button onclick="window.permissionsModule.closeModal('assignPermissionModal')" class="flex-1 px-4 py-2 bg-bg-surface-alt text-on-surface rounded-lg hover:bg-bg-surface transition-colors">
                    取消
                </button>
                <button onclick="window.permissionsModule.assignPermission()" class="flex-1 px-4 py-2 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity">
                    分配
                </button>
            </div>
        </div>
    </div>`;

    if (container) {
        container.innerHTML = html;
    }

    // 初始化模块
    window.permissionsModule = {
        currentTab: 'roles',
        allRoles: [],
        allUsers: [],
        allKBs: [],

        async init() {
            // 检查用户权限
            if (!window.WikiAPI.currentUser || window.WikiAPI.currentUser.role !== 'admin') {
                alert('仅管理员可访问权限管理页面');
                window.location.hash = '#overview';
                return;
            }

            // 加载初始数据
            await Promise.all([
                this.loadRoles(),
                this.loadUsers(),
                this.loadKBs()
            ]);
        },

        /**
         * 切换 Tab
         */
        switchTab(tab) {
            this.currentTab = tab;

            // 显示/隐藏面板
            document.getElementById('rolesPanel').classList.toggle('hidden', tab !== 'roles');
            document.getElementById('matrixPanel').classList.toggle('hidden', tab !== 'matrix');
            document.getElementById('usersPanel').classList.toggle('hidden', tab !== 'users');

            // 更新 Tab 样式
            ['roles', 'matrix', 'users'].forEach(t => {
                const el = document.getElementById(`tab-${t}`);
                if (el) {
                    el.className = tab === t
                        ? 'px-4 py-2 rounded-b-none transition-colors tab-active'
                        : 'px-4 py-2 rounded-b-none transition-colors text-on-surface hover:bg-bg-surface-alt';
                }
            });

            // 切换到矩阵时自动加载
            if (tab === 'matrix') {
                this.loadPermissionMatrix();
            }
        },

        /**
         * 加载角色列表
         */
        async loadRoles() {
            const content = document.getElementById('rolesContent');
            if (!content) return;

            content.innerHTML = '<p class="text-on-muted text-center py-8">加载中...</p>';

            try {
                const data = await WikiAPI.get('/api/enterprise/roles');
                this.allRoles = data.roles || [];

                if (this.allRoles.length === 0) {
                    content.innerHTML = `
                        <div class="text-center py-8">
                            <p class="text-on-muted">暂无自定义角色</p>
                            <p class="text-on-muted text-sm mt-2">系统默认角色：admin, editor, reader</p>
                        </div>
                    `;
                    return;
                }

                content.innerHTML = `
                    <table class="w-full">
                        <thead>
                            <tr class="border-b-2 border-border text-left text-on-surface">
                                <th class="py-3 px-4">角色名</th>
                                <th class="py-3 px-4">显示名称</th>
                                <th class="py-3 px-4">权限</th>
                                <th class="py-3 px-4">描述</th>
                                <th class="py-3 px-4">操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${this.allRoles.map(role => `
                                <tr class="border-b border-border hover:bg-bg-surface-alt">
                                    <td class="py-3 px-4 font-mono text-sm text-on-base">${escapeHtml(role.name)}</td>
                                    <td class="py-3 px-4 font-medium text-on-base">${escapeHtml(role.display_name || role.name)}</td>
                                    <td class="py-3 px-4">
                                        ${(role.permissions || []).map(p => `
                                            <span class="px-2 py-1 rounded-full text-xs font-semibold bg-brand-light text-on-base mr-1">
                                                ${p}
                                            </span>
                                        `).join('')}
                                    </td>
                                    <td class="py-3 px-4 text-sm text-on-muted">${escapeHtml(role.description || '-')}</td>
                                    <td class="py-3 px-4">
                                        <button onclick="window.permissionsModule.showEditRoleModal('${role.id || role.name}')"
                                            class="px-2 py-1 text-xs bg-bg-surface-alt text-on-surface rounded hover:bg-bg-surface transition-colors mr-1">
                                            编辑
                                        </button>
                                        <button onclick="window.permissionsModule.deleteRole('${role.id || role.name}')"
                                            class="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors">
                                            删除
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            } catch (error) {
                content.innerHTML = `<p class="text-red-500 text-center py-8">加载失败: ${escapeHtml(error.message)}</p>`;
            }
        },

        /**
         * 加载权限矩阵
         */
        async loadPermissionMatrix() {
            const content = document.getElementById('matrixContent');
            if (!content) return;

            content.innerHTML = '<p class="text-on-muted text-center py-8">加载中...</p>';

            try {
                const kbId = document.getElementById('matrixKBFilter')?.value || '';
                const url = kbId
                    ? `/api/enterprise/permissions/matrix?kb_id=${kbId}`
                    : '/api/enterprise/permissions/matrix';

                const data = await WikiAPI.get(url);
                const matrix = data.matrix || [];
                const kbs = data.kbs || [];

                // 更新知识库筛选器
                const filterSelect = document.getElementById('matrixKBFilter');
                if (filterSelect) {
                    filterSelect.innerHTML = '<option value="">全部知识库</option>';
                    kbs.forEach(kb => {
                        filterSelect.innerHTML += `<option value="${kb.id}">${escapeHtml(kb.name)}</option>`;
                    });
                }

                if (matrix.length === 0) {
                    content.innerHTML = '<p class="text-on-muted text-center py-8">暂无权限数据</p>';
                    return;
                }

                // 权限列：read, write, delete, admin, share, export
                const permissions = ['read', 'write', 'delete', 'admin', 'share', 'export'];

                content.innerHTML = `
                    <table class="w-full border-collapse">
                        <thead>
                            <tr class="bg-bg-surface-alt">
                                <th class="py-3 px-4 text-left border border-border">用户</th>
                                <th class="py-3 px-4 text-left border border-border">知识库</th>
                                ${permissions.map(p => `
                                    <th class="py-3 px-2 border border-border text-center text-on-surface">${p}</th>
                                `).join('')}
                                <th class="py-3 px-4 border border-border text-center">操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${matrix.map(row => `
                                <tr class="hover:bg-bg-surface-alt">
                                    <td class="py-2 px-4 border border-border font-medium text-on-base">${escapeHtml(row.username)}</td>
                                    <td class="py-2 px-4 border border-border text-on-surface">${escapeHtml(row.kb_name)}</td>
                                    ${permissions.map(p => `
                                        <td class="py-2 px-2 border border-border text-center">
                                            <input type="checkbox"
                                                class="w-6 h-6 cursor-pointer"
                                                data-user="${row.user_id}"
                                                data-kb="${row.kb_id}"
                                                data-permission="${p}"
                                                ${row.permissions && row.permissions.includes(p) ? 'checked' : ''}
                                                onchange="window.permissionsModule.togglePermission(this)">
                                        </td>
                                    `).join('')}
                                    <td class="py-2 px-4 border border-border text-center">
                                        <button onclick="window.permissionsModule.revokePermission('${row.user_id}', '${row.kb_id}')"
                                            class="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors">
                                            撤销
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            } catch (error) {
                content.innerHTML = `<p class="text-red-500 text-center py-8">加载失败: ${escapeHtml(error.message)}</p>`;
            }
        },

        /**
         * 加载用户权限
         */
        async loadUserPermissions() {
            const userId = document.getElementById('userSelect')?.value || '';
            const content = document.getElementById('userPermissionsContent');
            if (!content) return;

            if (!userId) {
                content.innerHTML = '<p class="text-on-muted text-center py-8">请选择用户查看权限</p>';
                return;
            }

            content.innerHTML = '<p class="text-on-muted text-center py-8">加载中...</p>';

            try {
                const data = await WikiAPI.get(`/api/enterprise/users/${userId}/permissions`);
                const permissions = data.permissions || [];
                const user = data.user || {};

                if (permissions.length === 0) {
                    content.innerHTML = `
                        <div class="text-center py-8">
                            <p class="text-on-muted">该用户暂无知识库权限</p>
                            <button onclick="window.permissionsModule.showAssignPermissionModal('${userId}', '${escapeHtml(user.username)}')"
                                class="mt-4 px-4 py-2 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity">
                                + 分配权限
                            </button>
                        </div>
                    `;
                    return;
                }

                content.innerHTML = `
                    <div class="flex justify-end mb-4">
                        <button onclick="window.permissionsModule.showAssignPermissionModal('${userId}', '${escapeHtml(user.username)}')"
                            class="px-4 py-2 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity">
                            + 分配权限
                        </button>
                    </div>
                    <table class="w-full">
                        <thead>
                            <tr class="border-b-2 border-border text-left text-on-surface">
                                <th class="py-3 px-4">知识库</th>
                                <th class="py-3 px-4">角色</th>
                                <th class="py-3 px-4">权限</th>
                                <th class="py-3 px-4">来源</th>
                                <th class="py-3 px-4">操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${permissions.map(p => `
                                <tr class="border-b border-border hover:bg-bg-surface-alt">
                                    <td class="py-3 px-4 font-medium text-on-base">${escapeHtml(p.kb_name)}</td>
                                    <td class="py-3 px-4">
                                        <span class="px-2 py-1 rounded-full text-xs font-semibold ${
                                            p.role === 'admin' ? 'bg-red-100 text-red-700' :
                                            p.role === 'editor' ? 'bg-blue-100 text-blue-700' :
                                            'bg-green-100 text-green-700'
                                        }">
                                            ${p.role}
                                        </span>
                                    </td>
                                    <td class="py-3 px-4">
                                        ${(p.permissions || []).map(perm => `
                                            <span class="px-2 py-1 rounded-full text-xs font-semibold bg-brand-light text-on-base mr-1">
                                                ${perm}
                                            </span>
                                        `).join('')}
                                    </td>
                                    <td class="py-3 px-4 text-sm text-on-muted">${p.source || 'direct'}</td>
                                    <td class="py-3 px-4">
                                        <button onclick="window.permissionsModule.revokeUserKBPermission('${userId}', '${p.kb_id}')"
                                            class="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors">
                                            撤销
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            } catch (error) {
                content.innerHTML = `<p class="text-red-500 text-center py-8">加载失败: ${escapeHtml(error.message)}</p>`;
            }
        },

        /**
         * 加载用户列表
         */
        async loadUsers() {
            try {
                const data = await WikiAPI.get('/api/users');
                this.allUsers = data.users || [];

                const select = document.getElementById('userSelect');
                if (select) {
                    select.innerHTML = '<option value="">选择用户...</option>';
                    this.allUsers.forEach(u => {
                        select.innerHTML += `<option value="${u.id || u.username}">${escapeHtml(u.username)} (${u.role})</option>`;
                    });
                }
            } catch (error) {
                console.error('加载用户失败:', error);
            }
        },

        /**
         * 加载知识库列表
         */
        async loadKBs() {
            try {
                const data = await WikiAPI.get('/api/enterprise/kbs');
                this.allKBs = data.kbs || [];

                // 更新分配权限选择器
                const assignSelect = document.getElementById('assignKBSelect');
                if (assignSelect) {
                    assignSelect.innerHTML = '<option value="">选择知识库...</option>';
                    this.allKBs.forEach(kb => {
                        assignSelect.innerHTML += `<option value="${kb.id}">${escapeHtml(kb.name)}</option>`;
                    });
                }
            } catch (error) {
                console.error('加载知识库失败:', error);
            }
        },

        /**
         * 显示创建角色弹窗
         */
        showCreateRoleModal() {
            const nameEl = document.getElementById('roleName');
            const displayNameEl = document.getElementById('roleDisplayName');
            const descriptionEl = document.getElementById('roleDescription');

            if (nameEl) nameEl.value = '';
            if (displayNameEl) displayNameEl.value = '';
            if (descriptionEl) descriptionEl.value = '';

            document.querySelectorAll('#permissionCheckboxes input').forEach(cb => cb.checked = false);

            const modal = document.getElementById('createRoleModal');
            if (modal) modal.classList.remove('hidden');
            if (modal) modal.classList.add('flex');
        },

        /**
         * 创建角色
         */
        async createRole() {
            const name = document.getElementById('roleName')?.value?.trim() || '';
            const displayName = document.getElementById('roleDisplayName')?.value?.trim() || '';
            const description = document.getElementById('roleDescription')?.value?.trim() || '';
            const permissions = Array.from(document.querySelectorAll('#permissionCheckboxes input:checked')).map(cb => cb.value);

            if (!name || !displayName) {
                alert('角色名称和显示名称不能为空');
                return;
            }

            try {
                const data = await WikiAPI.post('/api/enterprise/roles', {
                    name,
                    display_name: displayName,
                    description,
                    permissions
                });

                if (data.status === 'ok' || data.id) {
                    this.closeModal('createRoleModal');
                    await this.loadRoles();
                    alert('角色创建成功');
                } else {
                    alert(data.error || '创建失败');
                }
            } catch (error) {
                alert('创建失败: ' + error.message);
            }
        },

        /**
         * 显示编辑角色弹窗
         */
        showEditRoleModal(roleId) {
            const role = this.allRoles.find(r => (r.id || r.name) === roleId);
            if (!role) {
                alert('角色不存在');
                return;
            }

            const roleIdEl = document.getElementById('editRoleId');
            const roleNameEl = document.getElementById('editRoleName');
            const displayNameEl = document.getElementById('editRoleDisplayName');
            const descriptionEl = document.getElementById('editRoleDescription');

            if (roleIdEl) roleIdEl.value = roleId;
            if (roleNameEl) roleNameEl.value = role.name;
            if (displayNameEl) displayNameEl.value = role.display_name || role.name;
            if (descriptionEl) descriptionEl.value = role.description || '';

            document.querySelectorAll('#editPermissionCheckboxes input').forEach(cb => {
                cb.checked = (role.permissions || []).includes(cb.value);
            });

            const modal = document.getElementById('editRoleModal');
            if (modal) modal.classList.remove('hidden');
            if (modal) modal.classList.add('flex');
        },

        /**
         * 更新角色
         */
        async updateRole() {
            const roleId = document.getElementById('editRoleId')?.value || '';
            const displayName = document.getElementById('editRoleDisplayName')?.value?.trim() || '';
            const description = document.getElementById('editRoleDescription')?.value?.trim() || '';
            const permissions = Array.from(document.querySelectorAll('#editPermissionCheckboxes input:checked')).map(cb => cb.value);

            if (!displayName) {
                alert('显示名称不能为空');
                return;
            }

            try {
                const data = await WikiAPI.put(`/api/enterprise/roles/${roleId}`, {
                    display_name: displayName,
                    description,
                    permissions
                });

                if (data.status === 'ok') {
                    this.closeModal('editRoleModal');
                    await this.loadRoles();
                    alert('角色更新成功');
                } else {
                    alert(data.error || '更新失败');
                }
            } catch (error) {
                alert('更新失败: ' + error.message);
            }
        },

        /**
         * 删除角色
         */
        async deleteRole(roleId) {
            if (!confirm('确定删除此角色？此操作不可恢复。')) return;

            try {
                const data = await WikiAPI.delete(`/api/enterprise/roles/${roleId}`);
                if (data.status === 'ok') {
                    await this.loadRoles();
                    alert('角色已删除');
                } else {
                    alert(data.error || '删除失败');
                }
            } catch (error) {
                alert('删除失败: ' + error.message);
            }
        },

        /**
         * 显示分配权限弹窗
         */
        showAssignPermissionModal(userId, username) {
            const userIdEl = document.getElementById('assignUserId');
            const usernameEl = document.getElementById('assignUsername');
            const kbSelectEl = document.getElementById('assignKBSelect');
            const roleEl = document.getElementById('assignRole');

            if (userIdEl) userIdEl.value = userId;
            if (usernameEl) usernameEl.value = username;
            if (kbSelectEl) kbSelectEl.value = '';
            if (roleEl) roleEl.value = 'reader';

            document.querySelectorAll('#assignPermissionCheckboxes input').forEach(cb => cb.checked = false);

            const modal = document.getElementById('assignPermissionModal');
            if (modal) modal.classList.remove('hidden');
            if (modal) modal.classList.add('flex');
        },

        /**
         * 分配权限
         */
        async assignPermission() {
            const userId = document.getElementById('assignUserId')?.value || '';
            const kbId = document.getElementById('assignKBSelect')?.value || '';
            const role = document.getElementById('assignRole')?.value || 'reader';
            const permissions = Array.from(document.querySelectorAll('#assignPermissionCheckboxes input:checked')).map(cb => cb.value);

            if (!kbId) {
                alert('请选择知识库');
                return;
            }

            try {
                const data = await WikiAPI.post(`/api/enterprise/users/${userId}/permissions`, {
                    kb_id: parseInt(kbId),
                    role,
                    permissions
                });

                if (data.status === 'ok') {
                    this.closeModal('assignPermissionModal');
                    await this.loadUserPermissions();
                    alert('权限已分配');
                } else {
                    alert(data.error || '分配失败');
                }
            } catch (error) {
                alert('分配失败: ' + error.message);
            }
        },

        /**
         * 即时切换权限（关键实现）
         */
        async togglePermission(checkbox) {
            const userId = checkbox.dataset.user;
            const kbId = checkbox.dataset.kb;
            const permission = checkbox.dataset.permission;
            const granted = checkbox.checked;

            // 记录原始状态用于回滚
            const originalState = !granted;

            try {
                checkbox.disabled = true;

                const data = await WikiAPI.put(`/api/enterprise/users/${userId}/permissions/${kbId}`, {
                    permission,
                    granted
                });

                if (data.status !== 'ok') {
                    // 回滚
                    checkbox.checked = originalState;
                    alert(data.error || '更新失败');
                }
            } catch (error) {
                // 回滚
                checkbox.checked = originalState;
                alert('更新失败: ' + error.message);
            } finally {
                checkbox.disabled = false;
            }
        },

        /**
         * 撤销权限
         */
        async revokePermission(userId, kbId) {
            if (!confirm('确定撤销此用户对该知识库的所有权限？')) return;

            try {
                const data = await WikiAPI.delete(`/api/enterprise/users/${userId}/permissions/${kbId}`);
                if (data.status === 'ok') {
                    await this.loadPermissionMatrix();
                    alert('权限已撤销');
                } else {
                    alert(data.error || '撤销失败');
                }
            } catch (error) {
                alert('撤销失败: ' + error.message);
            }
        },

        /**
         * 撤销用户对知识库的权限
         */
        async revokeUserKBPermission(userId, kbId) {
            if (!confirm('确定撤销此权限？')) return;

            try {
                const data = await WikiAPI.delete(`/api/enterprise/users/${userId}/permissions/${kbId}`);
                if (data.status === 'ok') {
                    await this.loadUserPermissions();
                    alert('权限已撤销');
                } else {
                    alert(data.error || '撤销失败');
                }
            } catch (error) {
                alert('撤销失败: ' + error.message);
            }
        },

        /**
         * 关闭弹窗
         */
        closeModal(modalId) {
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('hidden');
                modal.classList.remove('flex');
            }
        }
    };

    // 初始化
    window.permissionsModule.init();

    return html;
}

/**
 * 构建权限复选框
 */
function buildPermissionCheckboxes() {
    const permissions = [
        { value: 'read', label: '读取' },
        { value: 'write', label: '写入' },
        { value: 'delete', label: '删除' },
        { value: 'admin', label: '管理' },
        { value: 'share', label: '分享' },
        { value: 'export', label: '导出' }
    ];

    return permissions.map(p => `
        <label class="flex items-center text-on-surface">
            <input type="checkbox" value="${p.value}" class="mr-2"> ${p.label}
        </label>
    `).join('');
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
    name: '权限管理',
    icon: '🔐'
};