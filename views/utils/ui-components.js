/**
 * 共享 UI 组件库（ES Module）
 *
 * 落地 PLAN-M-011 任务组 5-1 规划但未实现的通用组件，消除 14 个视图模块中
 * 重复的 escapeHtml(×13)、手写弹窗(×7)、loading(×10)、徽章映射(×6)。
 *
 * 设计原则：
 *  - 全部返回 HTML 字符串，契合现有 `render()` 拼接模板字符串的风格
 *  - 一律使用语义 class（bg-bg-surface / text-on-base / text-accent / border-border-th …），
 *    组件自带主题适配，无硬编码颜色
 *  - 纯函数、无副作用，便于各模块按需 import
 *
 * 使用（在 views/views/*.js 中）：
 *   import { escapeHtml, createBadge, createLoadingSpinner } from '../utils/ui-components.js';
 */

/**
 * HTML 转义，防止 XSS。
 * @param {*} str 任意值，null/undefined 返回空串
 * @returns {string}
 */
export function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[m]));
}

/** 徽章语义变体 → 主题 class 映射 */
const BADGE_VARIANTS = {
    default: 'bg-bg-surface-alt text-on-surface',
    primary: 'bg-accent-soft text-accent',
    success: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    danger: 'bg-red-100 text-red-700',
    info: 'bg-blue-100 text-blue-700',
};

/**
 * 徽章组件。
 * @param {string} text 文本
 * @param {keyof typeof BADGE_VARIANTS} [variant='default'] 语义变体
 * @param {object} [opts]
 * @param {boolean} [opts.escape=true] 是否转义文本
 * @param {string} [opts.extraClass=''] 追加 class
 * @returns {string}
 */
export function createBadge(text, variant = 'default', opts = {}) {
    const { escape = true, extraClass = '' } = opts;
    const cls = BADGE_VARIANTS[variant] || BADGE_VARIANTS.default;
    const content = escape ? escapeHtml(text) : text;
    return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls} ${extraClass}">${content}</span>`;
}

/**
 * 加载中指示器（spinner）。
 * @param {string} [text='加载中...'] 提示文案
 * @param {object} [opts]
 * @param {string} [opts.size='w-8 h-8'] spinner 尺寸 class
 * @param {string} [opts.extraClass=''] 容器追加 class
 * @returns {string}
 */
export function createLoadingSpinner(text = '加载中...', opts = {}) {
    const { size = 'w-8 h-8', extraClass = '' } = opts;
    return `
    <div class="flex flex-col items-center justify-center py-12 text-on-muted ${extraClass}">
        <svg class="animate-spin ${size} text-accent mb-3" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        ${text ? `<span class="text-sm">${escapeHtml(text)}</span>` : ''}
    </div>`;
}

/**
 * 模态弹窗骨架。返回带遮罩的完整结构（默认隐藏，调用方控制显隐）。
 * @param {object} cfg
 * @param {string} cfg.id 弹窗根元素 id（用于显隐控制）
 * @param {string} cfg.title 标题
 * @param {string} cfg.body 内容 HTML（已自行转义）
 * @param {string} [cfg.footer=''] 底部 HTML（按钮等）
 * @param {string} [cfg.maxWidth='max-w-lg'] 宽度 class
 * @param {string} [cfg.onClose] 关闭按钮的内联事件（如 "document.getElementById('x').classList.add('hidden')"）
 * @returns {string}
 */
export function createModal(cfg = {}) {
    const {
        id = 'modal', title = '', body = '', footer = '',
        maxWidth = 'max-w-lg', onClose = '',
    } = cfg;
    const closeAttr = onClose ? `onclick="${onClose}"` : '';
    return `
    <div id="${id}" class="fixed inset-0 z-50 hidden">
        <div class="absolute inset-0 bg-black/50" ${closeAttr}></div>
        <div class="relative mx-auto mt-20 w-full ${maxWidth} bg-bg-surface rounded-lg shadow-xl border border-border-th">
            <div class="flex items-center justify-between px-5 py-3 border-b border-border-th">
                <h3 class="text-lg font-semibold text-on-base">${escapeHtml(title)}</h3>
                <button type="button" class="text-on-muted hover:text-on-base" ${closeAttr} aria-label="关闭">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>
            <div class="px-5 py-4 text-on-surface">${body}</div>
            ${footer ? `<div class="px-5 py-3 border-t border-border-th flex justify-end gap-2">${footer}</div>` : ''}
        </div>
    </div>`;
}

/**
 * 数据表格。
 * @param {object} cfg
 * @param {Array<{label:string, key?:string, render?:(row:object)=>string, class?:string}>} cfg.columns
 *        列定义；render 优先于 key，render 返回的内容不再转义（由调用方负责）
 * @param {object[]} cfg.rows 行数据
 * @param {string} [cfg.emptyText='暂无数据'] 空数据提示
 * @param {string} [cfg.extraClass=''] table 追加 class
 * @returns {string}
 */
export function createTable(cfg = {}) {
    const { columns = [], rows = [], emptyText = '暂无数据', extraClass = '' } = cfg;
    const head = columns
        .map(col => `<th class="px-4 py-2 text-left text-xs font-semibold text-on-muted uppercase tracking-wider ${col.class || ''}">${escapeHtml(col.label)}</th>`)
        .join('');

    if (!rows.length) {
        return `
        <table class="min-w-full divide-y divide-border-th ${extraClass}">
            <thead class="bg-bg-surface-alt"><tr>${head}</tr></thead>
            <tbody><tr><td colspan="${columns.length}" class="px-4 py-8 text-center text-sm text-on-muted">${escapeHtml(emptyText)}</td></tr></tbody>
        </table>`;
    }

    const body = rows.map(row => {
        const cells = columns.map(col => {
            const content = typeof col.render === 'function'
                ? col.render(row)
                : escapeHtml(row[col.key]);
            return `<td class="px-4 py-2 text-sm text-on-surface ${col.class || ''}">${content}</td>`;
        }).join('');
        return `<tr class="hover:bg-bg-hover">${cells}</tr>`;
    }).join('');

    return `
    <table class="min-w-full divide-y divide-border-th ${extraClass}">
        <thead class="bg-bg-surface-alt"><tr>${head}</tr></thead>
        <tbody class="divide-y divide-border-th">${body}</tbody>
    </table>`;
}

/**
 * 选项卡切换器（仅渲染按钮条；切换逻辑由调用方在 onSelect 中处理）。
 * @param {object} cfg
 * @param {Array<{key:string, label:string}>} cfg.tabs
 * @param {string} cfg.active 当前激活的 tab key
 * @param {string} [cfg.onSelect] 点击内联事件模板，使用 {key} 占位（如 "window.X.switchTab('{key}')"）
 * @param {string} [cfg.extraClass='']
 * @returns {string}
 */
export function createTabSwitcher(cfg = {}) {
    const { tabs = [], active = '', onSelect = '', extraClass = '' } = cfg;
    const buttons = tabs.map(tab => {
        const isActive = tab.key === active;
        const cls = isActive
            ? 'border-accent text-accent'
            : 'border-transparent text-on-muted hover:text-on-surface hover:border-border-th';
        const handler = onSelect ? `onclick="${onSelect.replace(/\{key\}/g, tab.key)}"` : '';
        return `<button type="button" ${handler} class="px-4 py-2 -mb-px border-b-2 text-sm font-medium ${cls}">${escapeHtml(tab.label)}</button>`;
    }).join('');
    return `<div class="flex border-b border-border-th ${extraClass}">${buttons}</div>`;
}

/**
 * 空状态组件（EmptyState）。统一"列表/表格无数据"的呈现。
 * 落地 PLAN-M-013 三态体系（加载 / 空 / 错误）之"空"。
 * @param {object} cfg
 * @param {string} [cfg.title='暂无数据'] 主标题
 * @param {string} [cfg.desc=''] 辅助说明
 * @param {string} [cfg.icon] 自定义图标 SVG path 的 d 值；缺省用通用空盒图标
 * @param {string} [cfg.actionLabel=''] 主操作按钮文案（为空则不渲染）
 * @param {string} [cfg.onAction=''] 主操作按钮的内联事件
 * @param {string} [cfg.extraClass='']
 * @returns {string}
 */
export function createEmptyState(cfg = {}) {
    const {
        title = '暂无数据', desc = '', icon = '',
        actionLabel = '', onAction = '', extraClass = '',
    } = cfg;
    const path = icon || 'M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4';
    const action = actionLabel
        ? `<button type="button" ${onAction ? `onclick="${onAction}"` : ''} class="mt-3 inline-flex items-center h-9 px-3.5 rounded-md bg-accent text-on-accent text-sm font-medium hover:opacity-90">${escapeHtml(actionLabel)}</button>`
        : '';
    return `
    <div class="flex flex-col items-center justify-center py-12 text-center ${extraClass}">
        <div class="w-12 h-12 rounded-lg bg-bg-surface-alt flex items-center justify-center mb-3">
            <svg class="w-6 h-6 text-on-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="${path}"/>
            </svg>
        </div>
        <div class="text-sm font-medium text-on-base">${escapeHtml(title)}</div>
        ${desc ? `<div class="text-xs text-on-muted mt-1">${escapeHtml(desc)}</div>` : ''}
        ${action}
    </div>`;
}

/**
 * 骨架屏（Skeleton）。首屏/加载占位，减少布局抖动。
 * 落地 PLAN-M-013 三态体系之"加载"（结构化占位，区别于纯 spinner）。
 * @param {object} [cfg]
 * @param {number} [cfg.rows=3] 行数
 * @param {'list'|'table'|'card'} [cfg.type='list'] 形态
 * @param {string} [cfg.extraClass='']
 * @returns {string}
 */
export function createSkeleton(cfg = {}) {
    const { rows = 3, type = 'list', extraClass = '' } = cfg;
    const bar = (w) => `<div class="h-3 rounded bg-bg-surface-alt animate-pulse" style="width:${w}"></div>`;
    let items = '';
    if (type === 'card') {
        items = Array.from({ length: rows }).map(() => `
            <div class="p-4 rounded-md border border-border-th bg-bg-surface">
                ${bar('40%')}<div class="mt-3 space-y-2">${bar('100%')}${bar('80%')}</div>
            </div>`).join('');
        return `<div class="grid gap-3 ${extraClass}">${items}</div>`;
    }
    if (type === 'table') {
        items = Array.from({ length: rows }).map(() => `
            <div class="flex items-center gap-4 px-4 py-3 border-b border-border-th">
                ${bar('30%')}${bar('20%')}${bar('15%')}<div class="ml-auto">${bar('48px')}</div>
            </div>`).join('');
        return `<div class="${extraClass}">${items}</div>`;
    }
    // list（默认）
    items = Array.from({ length: rows }).map(() => `
        <div class="flex items-center gap-3 py-3">
            <div class="w-8 h-8 rounded-full bg-bg-surface-alt animate-pulse shrink-0"></div>
            <div class="flex-1 space-y-2">${bar('60%')}${bar('40%')}</div>
        </div>`).join('');
    return `<div class="divide-y divide-border-th ${extraClass}">${items}</div>`;
}

/** 便捷全局挂载（供非模块场景或调试使用，不影响 ESM import） */
if (typeof window !== 'undefined') {
    window.UI = window.UI || {
        escapeHtml, createBadge, createLoadingSpinner, createModal, createTable, createTabSwitcher,
        createEmptyState, createSkeleton,
    };
}
