/**
 * 导航数据层（单一来源 · Single Source of Truth）
 *
 * 统一桌面侧边栏、移动端 drawer、路由白名单三处的导航配置，
 * 消除「桌面 9 项 vs 移动 4 项」不一致与多处硬编码路由数组。
 *
 * 使用方（ES Module）：
 *   - index.html 内联脚本：动态 import 后注入 Alpine app() 数据
 *   - handleRoute() / isExternalView()：复用 getRoutableViews()
 *
 * 约定：
 *   - icon 字段存放 SVG <path> 的 d 属性值，模板统一包裹 <svg class="w-4 h-4">
 *   - roles 为可见角色白名单；缺省视为全部登录用户可见
 *   - group 用于侧边栏二级分组呈现（内容操作 / 系统管理）
 */

/** 角色常量（避免散落字符串拼写错误） */
export const ROLE_ALL = ['viewer', 'editor', 'admin'];
export const ROLE_EDITOR = ['editor', 'admin'];
export const ROLE_ADMIN = ['admin'];

/**
 * 主视图（内联视图，由 Alpine `view` 状态切换，不走动态模块加载）
 * 字段：label / view / icon / badge
 *  - badge 为可选，指向 app() 中的数组属性名（如 'gaps'），用于显示数量徽章
 */
export const MAIN_VIEWS = [
    { label: '概览', view: 'overview', icon: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z' },
    { label: '浏览', view: 'browse', icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
    { label: '图谱', view: 'graph', icon: 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064' },
    { label: '时间线', view: 'timeline', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
    { label: '缺口', view: 'gaps', icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z', badge: 'gaps' },
];

/**
 * 管理工具（hash 路由，按 route 动态 import `views/views/{route}.js`）
 * 字段：label / route / icon / roles / group
 *
 * 语义修正（PLAN-M-012 0.1）：
 *  - 旧侧边栏「通知」实际指向 #webhooks（出站推送），属语义错配。
 *  - 现拆为两条独立项：
 *      · 通知        → #notifications（站内消息中心，铃铛图标）
 *      · 集成/Webhook → #webhooks（出站推送配置，链接图标）
 */
export const ADMIN_TOOLS = [
    // —— 内容操作 ——
    { label: 'AI 问答', route: 'qa', roles: ROLE_ALL, group: '内容操作', icon: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
    { label: '质检', route: 'quality', roles: ROLE_ALL, group: '内容操作', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
    { label: '去重', route: 'duplicates', roles: ROLE_ALL, group: '内容操作', icon: 'M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z' },
    { label: '新建', route: 'edit', roles: ROLE_EDITOR, group: '内容操作', icon: 'M12 4v16m8-8H4' },
    { label: '上传', route: 'upload', roles: ROLE_EDITOR, group: '内容操作', icon: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12' },
    { label: '分享', route: 'shares', roles: ROLE_EDITOR, group: '内容操作', icon: 'M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 005.568-2.684m0 0a3 3 0 00-5.568-2.684m0 0c-.938 1.165-2.5 1.77-4.184 1.77M9 12a3 3 0 005.568 0m0 0c.938-1.165 2.5-1.77 4.184-1.77M15 12a3 3 0 00-5.568 0m0 0c-.938 1.165-2.5 1.77-4.184 1.77' },

    // —— 系统管理 ——
    { label: '看板', route: 'dashboard', roles: ROLE_ALL, group: '系统管理', icon: 'M9 17V7m0 4a2 2 0 100 4m0-4a2 2 0 110 4m5 6v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2a2 2 0 002-2zm4-6V3m0 4a2 2 0 100 4m0-4a2 2 0 110 4m5 6v-4a2 2 0 00-2-2h-2a2 2 0 00-2 2v4a2 2 0 002 2h2a2 2 0 002-2z' },
    { label: '通知', route: 'notifications', roles: ROLE_ALL, group: '系统管理', icon: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9' },
    { label: '集成/Webhook', route: 'webhooks', roles: ROLE_ADMIN, group: '系统管理', icon: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1' },
    { label: '用户', route: 'users', roles: ROLE_ADMIN, group: '系统管理', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z' },
    { label: '权限', route: 'permissions', roles: ROLE_ADMIN, group: '系统管理', icon: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z' },
    { label: '知识库', route: 'kb-management', roles: ROLE_ADMIN, group: '系统管理', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.247m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.247' },
    { label: '审批', route: 'approvals', roles: ROLE_ADMIN, group: '系统管理', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7l2 2 4-4' },
    { label: '审计', route: 'audit', roles: ROLE_ADMIN, group: '系统管理', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
];

/**
 * 外链入口（新窗口打开，不参与 hash 路由）
 * 字段：label / href / icon / roles
 */
export const EXTERNAL_LINKS = [
    { label: '公开门户', href: '/public.html', roles: ROLE_ALL, icon: 'M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9' },
];

/** 侧边栏分组顺序 */
export const GROUP_ORDER = ['内容操作', '系统管理'];

/**
 * 派生：可路由视图白名单（供 handleRoute / isExternalView 复用）
 * 即所有走动态模块加载的管理工具 route 集合。
 * @returns {string[]}
 */
export function getRoutableViews() {
    return ADMIN_TOOLS.map(tool => tool.route);
}

/**
 * 派生：按角色过滤并按分组归类管理工具，供侧边栏分组渲染。
 * @param {string} role 当前用户角色
 * @returns {{ name: string, items: Array }[]}
 */
export function getAdminGroups(role) {
    const visible = ADMIN_TOOLS.filter(tool => tool.roles.includes(role));
    return GROUP_ORDER
        .map(name => ({ name, items: visible.filter(tool => tool.group === name) }))
        .filter(group => group.items.length > 0);
}
