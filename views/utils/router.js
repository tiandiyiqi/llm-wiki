/**
 * 路由模块 - SPA Hash 路由管理
 *
 * 功能：
 * - Hash 路由监听
 * - 路由映射表
 * - 浏览器前进/后退支持
 * - 路由跳转方法
 */

export class Router {
    constructor() {
        this.routes = new Map();
        this.currentRoute = 'overview';
        this.beforeHooks = [];
        this.afterHooks = [];

        // 初始化监听
        this.init();
    }

    /**
     * 初始化路由监听
     */
    init() {
        // 监听 hash 变化
        window.addEventListener('hashchange', () => this.handleRoute());

        // 页面加载时读取 hash
        window.addEventListener('load', () => this.handleRoute());
    }

    /**
     * 注册路由
     * @param {string} path - 路由路径
     * @param {Object} config - 路由配置
     */
    register(path, config) {
        this.routes.set(path, config);
    }

    /**
     * 批量注册路由
     * @param {Object} routes - 路由映射表
     */
    registerAll(routes) {
        Object.entries(routes).forEach(([path, config]) => {
            this.register(path, config);
        });
    }

    /**
     * 处理路由变化
     */
    handleRoute() {
        const hash = window.location.hash.slice(1) || 'overview';
        const previousRoute = this.currentRoute;

        // 检查路由是否存在
        if (!this.routes.has(hash)) {
            console.warn(`路由 ${hash} 未注册，跳转到默认路由`);
            this.navigate('overview');
            return;
        }

        // 执行前置钩子
        for (const hook of this.beforeHooks) {
            const result = hook(hash, previousRoute);
            if (result === false) {
                return; // 阻止路由跳转
            }
        }

        // 更新当前路由
        this.currentRoute = hash;

        // 触发 Alpine.js 响应式更新
        if (window.Alpine && Alpine.store('app')) {
            Alpine.store('app').currentView = hash;
        }

        // 执行后置钩子
        for (const hook of this.afterHooks) {
            hook(hash, previousRoute);
        }
    }

    /**
     * 路由跳转
     * @param {string} path - 目标路由
     */
    navigate(path) {
        window.location.hash = path;
    }

    /**
     * 返回上一页
     */
    back() {
        window.history.back();
    }

    /**
     * 前进下一页
     */
    forward() {
        window.history.forward();
    }

    /**
     * 添加前置钩子
     * @param {Function} hook - 钩子函数
     */
    beforeEach(hook) {
        this.beforeHooks.push(hook);
    }

    /**
     * 添加后置钩子
     * @param {Function} hook - 钩子函数
     */
    afterEach(hook) {
        this.afterHooks.push(hook);
    }

    /**
     * 获取当前路由
     */
    getCurrentRoute() {
        return this.currentRoute;
    }

    /**
     * 获取路由配置
     * @param {string} path - 路由路径
     */
    getRouteConfig(path) {
        return this.routes.get(path);
    }
}

// 创建全局路由实例
export const router = new Router();

// 默认路由配置
export const defaultRoutes = {
    // 内联视图
    'overview': { inline: true },
    'browse': { inline: true },
    'graph': { inline: true },
    'timeline': { inline: true },
    'gaps': { inline: true },

    // 管理工具（动态加载）
    'qa': { module: '/views/views/qa.js' },
    'dashboard': { module: '/views/views/dashboard.js' },
    'quality': { module: '/views/views/quality.js' },
    'duplicates': { module: '/views/views/duplicates.js' },
    'shares': { module: '/views/views/shares.js' },
    'webhooks': { module: '/views/views/webhooks.js' },
    'edit': { module: '/views/views/edit.js' },
    'upload': { module: '/views/views/upload.js' },
    'users': { module: '/views/views/users.js' },
    'approvals': { module: '/views/views/approvals.js' },
    'audit': { module: '/views/views/audit.js' },
    'permissions': { module: '/views/views/permissions.js' },
    'kb-management': { module: '/views/views/kb-management.js' },
    'notifications': { module: '/views/views/notifications.js' }
};

// 注册默认路由
router.registerAll(defaultRoutes);
