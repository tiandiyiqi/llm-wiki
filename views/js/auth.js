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
     * 获取 SSO 提供商列表
     */
    async getSSOProviders() {
        try {
            const result = await this.get('/api/auth/sso/providers');
            return result.providers || [];
        } catch (e) {
            return [];
        }
    },

    /**
     * 发起 SSO 登录（重定向到 Casdoor）
     */
    ssoLogin(provider) {
        window.location.href = '/api/auth/sso/login' + (provider ? '?provider=' + encodeURIComponent(provider) : '');
    },

    /**
     * 处理 SSO 回调（从 URL 解析 code 和 state）
     */
    async handleSSOCallback() {
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        const state = params.get('state');
        return { code, state };
    },

    /**
     * SSO 是否可用
     */
    isSSOEnabled() {
        return this._ssoProviders && this._ssoProviders.length > 0;
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

/**
 * PWA 安装提示
 * 监听 beforeinstallprompt 事件，显示自定义安装横幅
 */
const PWAInstall = {
    /** 保存浏览器安装提示事件 */
    deferredPrompt: null,

    /** 安装横幅是否已显示 */
    bannerShown: false,

    /**
     * 初始化 PWA 安装提示
     */
    init() {
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallBanner();
        });

        window.addEventListener('appinstalled', () => {
            this.deferredPrompt = null;
            this.hideInstallBanner();
            console.log('[PWA] App installed successfully');
        });
    },

    /**
     * 显示安装横幅
     */
    showInstallBanner() {
        if (this.bannerShown) return;
        this.bannerShown = true;

        const banner = document.createElement('div');
        banner.id = 'pwa-install-banner';
        banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9998;background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,0.2);font-family:system-ui,sans-serif;';

        banner.innerHTML = `
            <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                <span style="font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">安装 LLM Wiki 到桌面，离线也能使用</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
                <button id="pwa-install-btn" style="background:white;color:#667eea;border:none;padding:6px 16px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;">安装</button>
                <button id="pwa-dismiss-btn" style="background:transparent;color:white;border:1px solid rgba(255,255,255,0.4);padding:6px 12px;border-radius:6px;font-size:13px;cursor:pointer;">稍后</button>
            </div>
        `;

        document.body.prepend(banner);

        // 调整页面顶部偏移以避免遮挡
        const mainContent = document.querySelector('.flex.pt-28');
        if (mainContent) {
            mainContent.style.paddingTop = 'calc(7rem + 48px)';
        }

        document.getElementById('pwa-install-btn').addEventListener('click', () => {
            this.installApp();
        });
        document.getElementById('pwa-dismiss-btn').addEventListener('click', () => {
            this.hideInstallBanner();
        });
    },

    /**
     * 触发安装
     */
    async installApp() {
        if (!this.deferredPrompt) return;
        this.deferredPrompt.prompt();
        const { outcome } = await this.deferredPrompt.userChoice;
        console.log('[PWA] Install prompt outcome:', outcome);
        this.deferredPrompt = null;
    },

    /**
     * 隐藏安装横幅
     */
    hideInstallBanner() {
        const banner = document.getElementById('pwa-install-banner');
        if (banner) {
            banner.remove();
        }
        // 恢复页面顶部偏移
        const mainContent = document.querySelector('.flex.pt-28');
        if (mainContent) {
            mainContent.style.paddingTop = '';
        }
        this.bannerShown = false;
    },
};

// 自动初始化
if (typeof window !== 'undefined') {
    window.API = API;
    window.PWAInstall = PWAInstall;
    PWAInstall.init();
}

export default API;
