/**
 * 命令面板（Command Palette · ⌘K / Ctrl+K）
 *
 * PLAN-M-013 交互增强：全局唤起，聚合「跳转视图」+「搜索知识原子」。
 *
 * 设计原则（与项目既有架构对齐）：
 *  - 导航复用 `nav-config.js` 单一来源（MAIN_VIEWS / ADMIN_TOOLS），按当前角色过滤。
 *  - 跳转一律通过 `window.location.hash`，由 index.html 的 handleRoute() 接管，
 *    不触碰 Alpine 内部状态（零耦合、低风险）。
 *  - 搜索对接 `window.WikiAPI`（/api/search），缺省优雅降级为「待对接」提示。
 *  - 全部语义 class，自动适配 5 套主题。
 *
 * 用法：本文件以 <script type="module"> 引入即自注册键盘监听；
 *      亦可调用 window.openCommandPalette() / closeCommandPalette()。
 */
import { MAIN_VIEWS, getAdminGroups } from '../utils/nav-config.js';

const ICON = (d) => `<svg class="w-4 h-4 shrink-0 text-on-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${d}"/></svg>`;
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));

let rootEl = null;     // 面板根 DOM
let items = [];        // 当前可选项（扁平化，含 type/label/hash 等）
let activeIdx = 0;     // 键盘高亮索引
let searchSeq = 0;     // 搜索请求序号（防竞态）

/** 读取当前角色（只读 app 实例；缺省 viewer 最小可见集） */
function currentRole() {
    try { return window.__wikiApp?.currentUser?.role || 'viewer'; }
    catch { return 'viewer'; }
}

/** 构建「跳转」条目（主视图 + 按角色过滤的管理工具） */
function navItems(query) {
    const q = (query || '').trim().toLowerCase();
    const main = MAIN_VIEWS.map(v => ({ type: 'view', label: v.label, hash: v.view, icon: v.icon, group: '跳转' }));
    const admin = getAdminGroups(currentRole())
        .flatMap(g => g.items.map(it => ({ type: 'route', label: it.label, hash: it.route, icon: it.icon, group: '跳转' })));
    const all = [...main, ...admin];
    return q ? all.filter(i => i.label.toLowerCase().includes(q)) : all;
}

/** 异步搜索知识原子（对接 WikiAPI，失败/缺省降级） */
async function searchAtoms(query, seq) {
    const q = (query || '').trim();
    if (!q || typeof window.WikiAPI?.get !== 'function') return [];
    try {
        const res = await window.WikiAPI.get(`/api/search?q=${encodeURIComponent(q)}&limit=6`);
        if (seq !== searchSeq) return null; // 已被更新的请求取代，丢弃
        const list = Array.isArray(res) ? res : (res.data || res.results || res.atoms || []);
        return list.slice(0, 6).map(a => ({
            type: 'atom', label: a.title || a.name || a.id || '(未命名)',
            hash: null, atomType: a.type || '', id: a.id, group: '知识原子',
        }));
    } catch { return []; }
}

/** 重新渲染列表区 */
function renderList(query, atoms, loading) {
    const nav = navItems(query);
    items = [...nav, ...(atoms || [])];
    if (activeIdx >= items.length) activeIdx = Math.max(0, items.length - 1);

    const groupBlock = (name, arr, startIdx) => {
        if (!arr.length) return '';
        const rows = arr.map((it, i) => {
            const idx = startIdx + i;
            const active = idx === activeIdx ? 'bg-accent-soft' : '';
            const right = it.type === 'atom'
                ? `<span class="ml-auto text-xs font-mono text-on-muted">${esc(it.atomType)}</span>`
                : '';
            return `<button type="button" data-idx="${idx}" class="cmdk-row w-full flex items-center gap-3 px-4 py-2 text-sm text-on-base text-left hover:bg-accent-soft ${active}">
                ${ICON(it.icon || 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z')}
                <span class="flex-1 truncate">${esc(it.label)}</span>${right}
            </button>`;
        }).join('');
        return `<div class="px-4 py-1.5 text-xs font-medium text-on-muted uppercase tracking-wide">${esc(name)}</div>${rows}`;
    };

    const listEl = rootEl.querySelector('#cmdkList');
    const navCount = items.filter(i => i.group === '跳转').length;
    let html = groupBlock('跳转', nav, 0);
    if (query && query.trim()) {
        if (loading) {
            html += `<div class="px-4 py-1.5 text-xs font-medium text-on-muted uppercase tracking-wide">知识原子</div>
                     <div class="px-4 py-3 text-sm text-on-muted flex items-center gap-2">
                        <svg class="animate-spin w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>搜索中…</div>`;
        } else if (atoms && atoms.length) {
            html += groupBlock('知识原子', atoms, navCount);
        } else if (atoms !== null) {
            const tip = typeof window.WikiAPI?.get === 'function' ? '未找到匹配的知识原子' : '搜索接口待对接（WikiAPI 不可用）';
            html += `<div class="px-4 py-1.5 text-xs font-medium text-on-muted uppercase tracking-wide">知识原子</div>
                     <div class="px-4 py-3 text-sm text-on-muted">${tip}</div>`;
        }
    }
    if (!items.length && !(query && query.trim())) {
        html = `<div class="px-4 py-8 text-center text-sm text-on-muted">无匹配项</div>`;
    }
    listEl.innerHTML = html;
}

/** 执行当前高亮项 */
function execActive() {
    const it = items[activeIdx];
    if (!it) return;
    if (it.type === 'atom') {
        // 知识原子：跳浏览视图（详情对接可后续增强）
        window.location.hash = '#browse';
    } else {
        window.location.hash = '#' + it.hash;
    }
    closeCommandPalette();
}

let debounceTimer = null;
function onInput(e) {
    const q = e.target.value;
    renderList(q, q.trim() ? undefined : [], !!q.trim());
    clearTimeout(debounceTimer);
    if (!q.trim()) return;
    const seq = ++searchSeq;
    debounceTimer = setTimeout(async () => {
        const atoms = await searchAtoms(q, seq);
        if (atoms === null) return; // 竞态丢弃
        if (rootEl && !rootEl.classList.contains('hidden')) renderList(q, atoms, false);
    }, 220);
}

function onKeydown(e) {
    if (!rootEl || rootEl.classList.contains('hidden')) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); activeIdx = Math.min(items.length - 1, activeIdx + 1); refreshActive(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); activeIdx = Math.max(0, activeIdx - 1); refreshActive(); }
    else if (e.key === 'Enter') { e.preventDefault(); execActive(); }
    else if (e.key === 'Escape') { e.preventDefault(); closeCommandPalette(); }
}

/** 仅更新高亮态（不重渲染） */
function refreshActive() {
    rootEl.querySelectorAll('.cmdk-row').forEach(el => {
        const on = Number(el.dataset.idx) === activeIdx;
        el.classList.toggle('bg-accent-soft', on);
        if (on) el.scrollIntoView({ block: 'nearest' });
    });
}

function ensureRoot() {
    if (rootEl) return rootEl;
    rootEl = document.createElement('div');
    rootEl.id = 'commandPalette';
    rootEl.className = 'fixed inset-0 z-[60] hidden';
    rootEl.innerHTML = `
        <div class="absolute inset-0 bg-bg-overlay" data-cmdk-close></div>
        <div class="relative max-w-xl mx-auto mt-[12vh] bg-bg-surface border border-border-th rounded-lg shadow-xl overflow-hidden">
            <div class="flex items-center gap-3 px-4 h-12 border-b border-border-th">
                ${ICON('M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z')}
                <input id="cmdkInput" autocomplete="off" placeholder="搜索知识原子、跳转视图…" class="flex-1 bg-transparent outline-none text-sm text-on-base placeholder:text-on-muted">
                <kbd class="text-[11px] font-mono px-1.5 py-0.5 rounded border border-border-th text-on-muted">ESC</kbd>
            </div>
            <div id="cmdkList" class="max-h-80 overflow-y-auto py-2"></div>
        </div>`;
    document.body.appendChild(rootEl);
    rootEl.querySelector('[data-cmdk-close]').addEventListener('click', closeCommandPalette);
    rootEl.querySelector('#cmdkInput').addEventListener('input', onInput);
    rootEl.querySelector('#cmdkList').addEventListener('click', (e) => {
        const row = e.target.closest('.cmdk-row');
        if (row) { activeIdx = Number(row.dataset.idx); execActive(); }
    });
    return rootEl;
}

export function openCommandPalette() {
    ensureRoot();
    activeIdx = 0;
    rootEl.classList.remove('hidden');
    const input = rootEl.querySelector('#cmdkInput');
    input.value = '';
    renderList('', [], false);
    setTimeout(() => input.focus(), 0);
}

export function closeCommandPalette() {
    if (rootEl) rootEl.classList.add('hidden');
}

// 全局键盘唤起 + 暴露 API
window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openCommandPalette(); }
});
window.addEventListener('keydown', onKeydown);
window.openCommandPalette = openCommandPalette;
window.closeCommandPalette = closeCommandPalette;
