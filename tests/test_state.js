/**
 * 状态管理模块测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { StateManager, state } from '../views/utils/state.js';

describe('StateManager', () => {
    let stateManager;

    beforeEach(() => {
        // 清空 localStorage
        localStorage.clear();
        stateManager = new StateManager();
    });

    describe('SUB-TASK-007: 状态对象初始化', () => {
        it('应该初始化默认状态', () => {
            expect(stateManager.state).toBeDefined();
            expect(stateManager.state.user).toBeNull();
            expect(stateManager.state.theme).toBe('light');
            expect(stateManager.state.currentView).toBe('overview');
        });

        it('应该支持自定义初始状态', () => {
            const customState = new StateManager({
                theme: 'dark',
                customKey: 'customValue'
            });

            expect(customState.state.theme).toBe('dark');
            expect(customState.state.customKey).toBe('customValue');
        });

        it('应该支持读取和设置状态', () => {
            stateManager.setState('user', { name: 'test' });

            expect(stateManager.getState('user')).toEqual({ name: 'test' });
        });

        it('应该支持批量设置状态', () => {
            stateManager.setState({
                user: { name: 'test' },
                theme: 'dark'
            });

            expect(stateManager.getState('user')).toEqual({ name: 'test' });
            expect(stateManager.getState('theme')).toBe('dark');
        });
    });

    describe('SUB-TASK-008: 状态订阅机制', () => {
        it('应该支持订阅状态变化', () => {
            const callback = vi.fn();
            stateManager.subscribe('theme', callback);

            stateManager.setState('theme', 'dark');

            expect(callback).toHaveBeenCalledWith('dark', 'light');
        });

        it('应该支持取消订阅', () => {
            const callback = vi.fn();
            const unsubscribe = stateManager.subscribe('theme', callback);

            unsubscribe();
            stateManager.setState('theme', 'dark');

            expect(callback).not.toHaveBeenCalled();
        });

        it('应该支持多个订阅者', () => {
            const callback1 = vi.fn();
            const callback2 = vi.fn();

            stateManager.subscribe('theme', callback1);
            stateManager.subscribe('theme', callback2);

            stateManager.setState('theme', 'dark');

            expect(callback1).toHaveBeenCalled();
            expect(callback2).toHaveBeenCalled();
        });

        it('应该在状态未变化时不触发订阅', () => {
            const callback = vi.fn();
            stateManager.subscribe('theme', callback);

            stateManager.setState('theme', 'light'); // 与默认值相同

            expect(callback).not.toHaveBeenCalled();
        });
    });

    describe('SUB-TASK-009: localStorage 持久化', () => {
        it('应该持久化指定的状态键', () => {
            stateManager.persist(['theme', 'user']);

            stateManager.setState('theme', 'dark');
            stateManager.setState('user', { name: 'test' });

            const stored = JSON.parse(localStorage.getItem('app-state'));
            expect(stored.theme).toBe('dark');
            expect(stored.user).toEqual({ name: 'test' });
        });

        it('应该从 localStorage 恢复状态', () => {
            localStorage.setItem('app-state', JSON.stringify({
                theme: 'dark',
                user: { name: 'restored' }
            }));

            const newStateManager = new StateManager();
            newStateManager.persist(['theme', 'user']);

            expect(newStateManager.getState('theme')).toBe('dark');
            expect(newStateManager.getState('user')).toEqual({ name: 'restored' });
        });

        it('应该在 setState 时自动持久化', () => {
            stateManager.persist(['theme']);

            stateManager.setState('theme', 'dark');

            const stored = JSON.parse(localStorage.getItem('app-state'));
            expect(stored.theme).toBe('dark');
        });

        it('应该处理 localStorage 错误', () => {
            const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

            // 模拟 localStorage 满了
            const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
            setItemSpy.mockImplementation(() => {
                throw new Error('QuotaExceededError');
            });

            stateManager.persist(['theme']);
            stateManager.setState('theme', 'dark');

            // 不应该抛出错误
            expect(consoleError).toHaveBeenCalled();

            setItemSpy.mockRestore();
            consoleError.mockRestore();
        });
    });
});
