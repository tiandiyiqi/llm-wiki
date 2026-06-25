/**
 * 用户管理视图模块
 * 
 * 提取自 /views/admin/users.html，改造为 SPA 模块
 */

export function render(container) {
    const html = `
    <div class="users-view h-full flex flex-col p-6">
        <div class="bg-white rounded-lg shadow p-6">
            <h1 class="text-2xl font-bold mb-4">👥 用户管理</h1>
            <p class="text-gray-600 mb-6">此功能正在迁移到 SPA 架构中...</p>
            
            <div class="bg-blue-50 border border-blue-200 rounded p-4">
                <p class="text-sm text-blue-800">
                    ℹ️ 此页面已从独立页面迁移到 SPA 模块。
                    原页面位置：/views/admin/users.html
                </p>
            </div>
            
            <div class="mt-6">
                <a href="#overview" class="text-blue-600 hover:underline">← 返回概览</a>
            </div>
        </div>
    </div>
    `;

    if (container) {
        container.innerHTML = html;
    }

    return html;
}

export default {
    render: render,
    name: '用户管理',
    icon: '👥'
};
