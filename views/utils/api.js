/**
 * API 封装模块 - 统一 API 调用
 *
 * 功能：
 * - HTTP 方法封装（GET/POST/PUT/DELETE）
 * - 认证检查
 * - 统一错误处理
 */

export const WikiAPI = {
    /**
     * GET 请求
     * @param {string} url - 请求 URL
     * @param {Object} params - 查询参数
     * @returns {Promise<Object>} 响应数据
     */
    async get(url, params = {}) {
        const query = new URLSearchParams(params).toString();
        const fullUrl = query ? `${url}?${query}` : url;

        const response = await fetch(fullUrl, {
            credentials: 'same-origin'
        });

        this.checkAuth(response);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    },

    /**
     * POST 请求
     * @param {string} url - 请求 URL
     * @param {Object} data - 请求数据
     * @returns {Promise<Object>} 响应数据
     */
    async post(url, data = {}) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data),
            credentials: 'same-origin'
        });

        this.checkAuth(response);

        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: response.statusText }));
            throw new Error(error.error || `HTTP ${response.status}`);
        }

        return response.json();
    },

    /**
     * PUT 请求
     * @param {string} url - 请求 URL
     * @param {Object} data - 请求数据
     * @returns {Promise<Object>} 响应数据
     */
    async put(url, data = {}) {
        const response = await fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data),
            credentials: 'same-origin'
        });

        this.checkAuth(response);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    },

    /**
     * DELETE 请求
     * @param {string} url - 请求 URL
     * @returns {Promise<Object>} 响应数据
     */
    async delete(url) {
        const response = await fetch(url, {
            method: 'DELETE',
            credentials: 'same-origin'
        });

        this.checkAuth(response);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    },

    /**
     * 检查认证状态
     * @param {Response} response - Fetch 响应对象
     */
    checkAuth(response) {
        if (response.status === 401) {
            // 未登录，跳转到登录页
            window.location.href = '/login.html';
            throw new Error('未登录');
        }
    },

    /**
     * 登出
     */
    async logout() {
        try {
            await this.post('/api/auth/logout');
        } catch (error) {
            console.warn('登出请求失败:', error);
        }
        window.location.href = '/login.html';
    },

    /**
     * 获取当前用户
     * @returns {Object|null} 用户对象
     */
    getCurrentUser() {
        return window.__currentUser || null;
    },

    /**
     * 是否已登录
     * @returns {boolean}
     */
    isLoggedIn() {
        return window.__currentUser != null;
    },

    /**
     * 是否是管理员
     * @returns {boolean}
     */
    isAdmin() {
        const user = this.getCurrentUser();
        return user && user.role === 'admin';
    },

    /**
     * 是否是编辑者
     * @returns {boolean}
     */
    isEditor() {
        const user = this.getCurrentUser();
        return user && ['editor', 'admin'].includes(user.role);
    }
};

// 暴露到全局（兼容旧代码）
window.WikiAPI = WikiAPI;
