/**
 * LLM-Wiki 前端认证与 API 工具模块
 *
 * 功能：
 * - API 请求封装（自动处理认证、错误）
 * - 登录/登出/会话管理
 * - 权限控制辅助函数
 * - 用户信息管理
 */

const API = {
    /** 基础 URL */
    baseUrl: '',

    /** 当前用户信息 */
    currentUser: null,

    /**
     * 初始化：检查登录状态
     */
    async init() {
        try {
            const user = await this.get('/api/auth/whoami');
            if (user && user.user) {
                this.currentUser = user.user;
                return true;
            }
        } catch (e) {
            console.log('未登录');
        }
        return false;
    },

    /**
     * 发送 GET 请求
     */
    async get(url, params = {}) {
        const query = new URLSearchParams(params).toString();
        const fullUrl = query ? `${url}?${query}` : url;
        return this._request('GET', fullUrl);
    },

    /**
     * 发送 POST 请求
     */
    async post(url, data = {}) {
        return this._request('POST', url, data);
    },

    /**
     * 发送 PUT 请求
     */
    async put(url, data = {}) {
        return this._request('PUT', url, data);
    },

    /**
     * 发送 DELETE 请求
     */
    async delete(url) {
        return this._request('DELETE', url);
    },

    /**
     * 文件上传
     */
    async upload(url, formData) {
        const response = await fetch(this.baseUrl + url, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin',
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${response.status}`);
        }
        return response.json();
    },

    /**
     * 核心请求方法
     */
    async _request(method, url, data = null) {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
        };
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }
        const response = await fetch(this.baseUrl + url, options);
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
            // 401 未登录：跳转登录页
            if (response.status === 401) {
                this._redirectLogin();
                throw new Error('未登录');
            }
            throw new Error(result.error || `HTTP ${response.status}`);
        }
        return result;
    },

    /**
     * 登录
     */
    async login(username, password) {
        const result = await this.post('/api/auth/login', { username, password });
        if (result.user) {
            this.currentUser = result.user;
        }
        return result;
    },

    /**
     * 登出
     */
    async logout() {
        try {
            await this.post('/api/auth/logout');
        } catch (e) {}
        this.currentUser = null;
        this._redirectLogin();
    },

    /**
     * 获取当前用户
     */
    getCurrentUser() {
        return this.currentUser;
    },

    /**
     * 是否已登录
     */
    isLoggedIn() {
        return this.currentUser !== null;
    },

    /**
     * 是否是 admin
     */
    isAdmin() {
        return this.currentUser && this.currentUser.role === 'admin';
    },

    /**
     * 是否是 editor 或更高
     */
    isEditor() {
        if (!this.currentUser) return false;
        return ['editor', 'admin'].includes(this.currentUser.role);
    },

    /**
     * 检查权限
     */
    hasPermission(level) {
        if (!this.currentUser) return false;
        const levels = { reader: 1, editor: 2, admin: 3 };
        return (levels[this.currentUser.role] || 0) >= (levels[level] || 0);
    },

    /**
     * 跳转登录页
     */
    _redirectLogin() {
        if (!window.location.pathname.endsWith('login.html')) {
            window.location.href = '/login.html';
        }
    },

    /**
     * 应用权限控制：隐藏无权限的元素
     */
    applyPermissions() {
        if (!this.currentUser) return;
        // 隐藏需要特定权限的元素
        document.querySelectorAll('[data-permission]').forEach(el => {
            const required = el.getAttribute('data-permission');
            if (!this.hasPermission(required)) {
                el.style.display = 'none';
            }
        });
        // 显示当前用户信息
        document.querySelectorAll('[data-user-name]').forEach(el => {
            el.textContent = this.currentUser.username;
        });
        document.querySelectorAll('[data-user-role]').forEach(el => {
            el.textContent = this.currentUser.role;
        });
    },
};

// 自动初始化
if (typeof window !== 'undefined') {
    window.API = API;
}

export default API;
