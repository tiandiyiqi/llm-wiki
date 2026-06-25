/**
 * 模块加载器 - 动态加载 ES6 模块
 *
 * 功能：
 * - 动态 import
 * - 模块缓存
 * - 加载失败重试
 * - 加载进度提示
 */

export class ModuleLoader {
    constructor() {
        // 模块缓存
        this.cache = new Map();

        // 加载中的模块
        this.loading = new Map();

        // 最大缓存数量
        this.maxCache = 10;

        // 重试次数
        this.maxRetries = 3;

        // 重试延迟（毫秒）
        this.retryDelay = 1000;
    }

    /**
     * 加载模块
     * @param {string} name - 模块名称
     * @param {string} path - 模块路径
     * @returns {Promise<Object>} 模块对象
     */
    async load(name, path) {
        // 检查缓存
        if (this.cache.has(name)) {
            console.log(`[Loader] 从缓存加载模块: ${name}`);
            return this.cache.get(name);
        }

        // 检查是否正在加载
        if (this.loading.has(name)) {
            console.log(`[Loader] 等待模块加载完成: ${name}`);
            return this.loading.get(name);
        }

        // 开始加载
        console.log(`[Loader] 开始加载模块: ${name} (${path})`);
        const loadPromise = this.loadWithRetry(name, path);
        this.loading.set(name, loadPromise);

        try {
            const module = await loadPromise;

            // 缓存模块
            this.cacheModule(name, module);

            return module;
        } finally {
            // 移除加载标记
            this.loading.delete(name);
        }
    }

    /**
     * 带重试的模块加载
     * @param {string} name - 模块名称
     * @param {string} path - 模块路径
     * @param {number} retryCount - 重试次数
     * @returns {Promise<Object>} 模块对象
     */
    async loadWithRetry(name, path, retryCount = 0) {
        try {
            const module = await import(path);
            console.log(`[Loader] 模块加载成功: ${name}`);
            return module.default || module;
        } catch (error) {
            console.error(`[Loader] 模块加载失败 (${retryCount + 1}/${this.maxRetries}):`, name, error);

            if (retryCount < this.maxRetries - 1) {
                // 等待后重试
                await this.delay(this.retryDelay * (retryCount + 1));
                return this.loadWithRetry(name, path, retryCount + 1);
            }

            throw new Error(`模块加载失败: ${name} (${error.message})`);
        }
    }

    /**
     * 缓存模块
     * @param {string} name - 模块名称
     * @param {Object} module - 模块对象
     */
    cacheModule(name, module) {
        // 检查缓存大小
        if (this.cache.size >= this.maxCache) {
            // 删除最早的缓存
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
            console.log(`[Loader] 清理缓存: ${firstKey}`);
        }

        this.cache.set(name, module);
        console.log(`[Loader] 模块已缓存: ${name}`);
    }

    /**
     * 预加载模块
     * @param {Array<{name: string, path: string}>} modules - 模块列表
     */
    async preload(modules) {
        console.log(`[Loader] 预加载 ${modules.length} 个模块...`);

        const promises = modules.map(({ name, path }) =>
            this.load(name, path).catch(error => {
                console.warn(`[Loader] 预加载失败: ${name}`, error);
                return null;
            })
        );

        await Promise.all(promises);
        console.log(`[Loader] 预加载完成`);
    }

    /**
     * 清除缓存
     * @param {string} name - 模块名称（可选，不传则清除全部）
     */
    clearCache(name) {
        if (name) {
            this.cache.delete(name);
            console.log(`[Loader] 清除缓存: ${name}`);
        } else {
            this.cache.clear();
            console.log(`[Loader] 清除所有缓存`);
        }
    }

    /**
     * 获取缓存大小
     * @returns {number}
     */
    getCacheSize() {
        return this.cache.size;
    }

    /**
     * 延迟函数
     * @param {number} ms - 延迟毫秒数
     * @returns {Promise<void>}
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 检查模块是否已加载
     * @param {string} name - 模块名称
     * @returns {boolean}
     */
    isLoaded(name) {
        return this.cache.has(name);
    }

    /**
     * 显示加载进度
     */
    showLoading() {
        // 可以集成到 UI 中，例如显示加载动画
        document.body.classList.add('module-loading');
    }

    /**
     * 隐藏加载进度
     */
    hideLoading() {
        document.body.classList.remove('module-loading');
    }
}

// 创建全局加载器实例
export const moduleLoader = new ModuleLoader();
