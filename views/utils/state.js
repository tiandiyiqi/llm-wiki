/**
 * 状态管理模块 - 全局状态管理
 *
 * 功能：
 * - 全局状态对象
 * - 状态订阅/发布机制
 * - localStorage 持久化
 */

export class StateManager {
    constructor() {
        // 全局状态
        this.state = {
            // 用户相关
            currentUser: null,
            currentView: 'overview',

            // 主题
            theme: localStorage.getItem('llm-wiki-theme') || 'classic',

            // 数据
            atoms: [],
            gaps: [],

            // UI 状态
            sidebarOpen: false,
            loading: false,

            // 图谱相关
            graphData: { nodes: [], edges: [] },
            graphFilters: { types: [] },
            graphSettings: {
                layout: 'fcose',
                nodeSize: 1.0,
                edgeWidth: 1.0,
                edgeColor: '#ccc',
                showOrphans: true,
                gravity: 0.35,
                gravityRange: 3.8,
                nodeRepulsion: 9000,
                idealEdgeLength: 100,
                edgeElasticity: 0.40,
                numIter: 2500
            }
        };

        // 订阅者列表
        this.subscribers = new Set();

        // 持久化键
        this.persistKeys = ['theme', 'graphSettings'];
    }

    /**
     * 获取状态
     * @returns {Object} 状态对象
     */
    getState() {
        return this.state;
    }

    /**
     * 设置状态
     * @param {Object} updates - 状态更新
     */
    setState(updates) {
        // 合并状态
        this.state = { ...this.state, ...updates };

        // 持久化指定键
        this.persist(updates);

        // 通知订阅者
        this.notify();
    }

    /**
     * 获取单个状态值
     * @param {string} key - 状态键
     * @returns {*} 状态值
     */
    get(key) {
        return this.state[key];
    }

    /**
     * 设置单个状态值
     * @param {string} key - 状态键
     * @param {*} value - 状态值
     */
    set(key, value) {
        this.setState({ [key]: value });
    }

    /**
     * 订阅状态变化
     * @param {Function} callback - 回调函数
     * @returns {Function} 取消订阅函数
     */
    subscribe(callback) {
        this.subscribers.add(callback);

        // 返回取消订阅函数
        return () => {
            this.subscribers.delete(callback);
        };
    }

    /**
     * 通知所有订阅者
     */
    notify() {
        this.subscribers.forEach(callback => {
            try {
                callback(this.state);
            } catch (error) {
                console.error('状态订阅者回调失败:', error);
            }
        });
    }

    /**
     * 持久化状态
     * @param {Object} updates - 更新的状态
     */
    persist(updates) {
        Object.keys(updates).forEach(key => {
            if (this.persistKeys.includes(key)) {
                try {
                    localStorage.setItem(`llm-wiki-${key}`, JSON.stringify(updates[key]));
                } catch (error) {
                    console.error(`持久化状态 ${key} 失败:`, error);
                }
            }
        });
    }

    /**
     * 恢复持久化状态
     */
    restore() {
        this.persistKeys.forEach(key => {
            try {
                const value = localStorage.getItem(`llm-wiki-${key}`);
                if (value !== null) {
                    this.state[key] = JSON.parse(value);
                }
            } catch (error) {
                console.error(`恢复状态 ${key} 失败:`, error);
            }
        });
    }

    /**
     * 重置状态
     * @param {Array<string>} keys - 要重置的状态键（可选）
     */
    reset(keys) {
        if (keys) {
            keys.forEach(key => {
                delete this.state[key];
                localStorage.removeItem(`llm-wiki-${key}`);
            });
        } else {
            this.state = {};
            localStorage.clear();
        }
        this.notify();
    }
}

// 创建全局状态管理实例
export const stateManager = new StateManager();

// 恢复持久化状态
stateManager.restore();
