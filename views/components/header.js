/**
 * Header 组件 - 提取自 index.html
 *
 * 功能：
 * - 渲染 Header HTML
 * - 集成 Theme Switcher
 * - 用户信息显示
 */

export function renderHeader(container) {
    const html = `
    <header class="bg-bg-surface shadow-sm border-b border-border-th fixed top-0 left-0 right-0 z-50">
        <div class="flex items-center justify-between px-4 py-3">
            <h1 class="text-xl font-semibold gradient-title">LLM Wiki</h1>
            <div class="flex items-center space-x-4">
                <span class="text-sm text-on-muted" x-text="atoms.length + ' 个原子'"></span>

                <!-- Theme Switcher -->
                <div class="relative" @click.away="themeMenuOpen = false">
                    <button @click="themeMenuOpen = !themeMenuOpen"
                        class="flex items-center space-x-1 text-sm text-on-surface hover:text-on-base px-2 py-1 rounded hover:bg-bg-hover"
                        title="切换主题">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                        </svg>
                        <span x-text="themes.find(t => t.id === currentTheme)?.name"></span>
                    </button>
                    <div x-show="themeMenuOpen" x-transition
                        class="absolute right-0 mt-2 w-44 bg-bg-surface rounded-lg shadow-lg border border-border-th overflow-hidden z-50">
                        <template x-for="theme in themes" :key="theme.id">
                            <button @click="setTheme(theme.id)"
                                :class="currentTheme === theme.id ? 'bg-accent-soft text-accent' : 'text-on-base hover:bg-bg-hover'"
                                class="w-full flex items-center space-x-3 px-3 py-2 text-sm">
                                <span class="w-4 h-4 rounded-full border border-border-th flex-shrink-0"
                                    :style="'background:' + theme.swatch"></span>
                                <span x-text="theme.name"></span>
                                <span x-show="currentTheme === theme.id" class="ml-auto text-accent">&#10003;</span>
                            </button>
                        </template>
                    </div>
                </div>

                <span class="text-xs bg-gradient-brand text-on-accent px-2 py-1 rounded">OKF v0.1</span>

                <!-- 用户信息 -->
                <div class="flex items-center space-x-3 border-l border-border-th pl-4">
                    <span class="text-sm text-on-surface" id="userInfo">-</span>
                </div>
                    <!-- 管理入口已统一至侧边栏（nav-config，PLAN-M-012）；保留 hash 路由以兼容此组件被复用的场景 -->
                    <a href="#approvals" class="hidden text-sm text-accent hover:underline"
                        id="adminLink">审批</a>
                    <a href="#notifications" class="hidden text-sm text-accent hover:underline"
                        id="notifLink">通知</a>
                    <a href="#audit" class="hidden text-sm text-accent hover:underline" id="auditLink">审计</a>
                    <a href="#users" class="hidden text-sm text-accent hover:underline" id="usersLink">用户</a>
                    <button onclick="WikiAPI.logout()" class="text-sm text-on-muted hover:text-red-500">退出</button>
                </div>
            </div>
        </div>
    </header>
    `;

    if (container) {
        container.innerHTML = html;
    }

    return html;
}
