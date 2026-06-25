/**
 * 数据看板视图模块
 *
 * 功能：
 * - 4 个统计卡片（原子总数、标签数、作者数、操作总数）
 * - 2 个环形图（类型分布、状态分布）
 * - 2 个柱状图（热门标签、用户活跃度）
 * - 热门文档列表
 * - 最近活动列表
 */

import { escapeHtml } from '../utils/ui-components.js';

let chartInstances = [];

/**
 * 读取当前主题的 CSS 变量值（用于 Chart.js 配色，随主题切换而变）
 * @param {string} name 变量名（含 --）
 * @param {string} fallback 兜底色
 */
function cssVar(name, fallback) {
    try {
        const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return v || fallback;
    } catch (e) {
        return fallback;
    }
}

/**
 * 动态加载 Chart.js
 */
async function loadChartJS() {
    if (window.Chart) return; // 已加载

    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        script.onload = resolve;
        script.onerror = () => reject(new Error('Chart.js 加载失败'));
        document.head.appendChild(script);
    });
}

/**
 * 销毁所有图表实例
 */
function destroyCharts() {
    chartInstances.forEach(chart => {
        if (chart) chart.destroy();
    });
    chartInstances = [];
}

/**
 * 加载所有数据
 */
async function loadData() {
    // 先销毁旧图表，避免重复渲染到同一 canvas 报错（修复刷新/主题重绘）
    destroyCharts();
    try {
        const [stats, behavior] = await Promise.all([
            WikiAPI.get('/api/stats'),
            WikiAPI.get('/api/analytics/behavior')
        ]);

        renderStats(stats);
        renderBehavior(behavior);
    } catch (error) {
        console.error('加载数据失败:', error);
        showError('加载数据失败，请刷新重试');
    }
}

/**
 * 渲染统计数据
 */
function renderStats(stats) {
    // 更新统计卡片
    document.getElementById('totalAtoms').textContent = stats.total_atoms || 0;
    document.getElementById('totalTags').textContent = stats.total_tags || 0;
    document.getElementById('totalAuthors').textContent = stats.total_authors || 0;

    // 类型分布环形图
    const typeData = stats.by_type || {};
    renderDoughnutChart('typeChart', typeData);

    // 状态分布环形图
    const statusData = stats.by_status || {};
    renderDoughnutChart('statusChart', statusData);

    // 热门标签柱状图
    const tagData = stats.by_tag || {};
    renderBarChart('tagChart', '数量', tagData, 10);

    // 热门文档
    renderPopularDocs(stats.popular_docs || []);

    // 最近活动
    renderRecentActivity(stats.recent_activity || []);
}

/**
 * 渲染行为分析
 */
function renderBehavior(behavior) {
    const actionCounts = behavior.action_counts || {};
    const totalActions = Object.values(actionCounts).reduce((a, b) => a + b, 0);
    document.getElementById('totalActions').textContent = totalActions;

    // 用户活跃度柱状图
    const userCounts = behavior.user_counts || {};
    renderBarChart('userChart', '操作数', userCounts, 10);
}

/**
 * 渲染环形图（Doughnut Chart）
 */
function renderDoughnutChart(canvasId, data) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const labels = Object.keys(data);
    const values = Object.values(data);

    // 无数据时显示提示
    if (labels.length === 0) {
        const container = canvas.parentElement;
        container.innerHTML = '<p class="text-on-muted text-center py-8">暂无数据</p>';
        return;
    }

    const colors = generateColors(labels.length);

    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: cssVar('--color-bg-surface', '#ffffff')
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        font: { size: 12 },
                        padding: 12,
                        color: cssVar('--color-text-secondary', '#4b5563')
                    }
                }
            }
        }
    });

    chartInstances.push(chart);
}

/**
 * 渲染柱状图（Bar Chart）
 */
function renderBarChart(canvasId, label, data, limit = 10) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const entries = Object.entries(data)
        .sort((a, b) => b[1] - a[1])
        .slice(0, limit);

    const labels = entries.map(e => e[0]);
    const values = entries.map(e => e[1]);

    // 无数据时显示提示
    if (labels.length === 0) {
        const container = canvas.parentElement;
        container.innerHTML = '<p class="text-on-muted text-center py-8">暂无数据</p>';
        return;
    }

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: values,
                backgroundColor: cssVar('--color-accent-primary', '#667eea'),
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    ticks: { color: cssVar('--color-text-secondary', '#4b5563') },
                    grid: { color: cssVar('--color-border', '#e5e7eb') }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        color: cssVar('--color-text-secondary', '#4b5563')
                    },
                    grid: { color: cssVar('--color-border', '#e5e7eb') }
                }
            }
        }
    });

    chartInstances.push(chart);
}

/**
 * 渲染热门文档列表
 */
function renderPopularDocs(docs) {
    const container = document.getElementById('popularDocs');
    if (!container) return;

    if (docs.length === 0) {
        container.innerHTML = '<p class="text-on-muted text-center py-4">暂无数据</p>';
        return;
    }

    container.innerHTML = docs.slice(0, 10).map((doc, index) => `
        <div class="flex items-center justify-between p-2 hover:bg-bg-hover rounded transition-colors">
            <div class="flex items-center gap-3">
                <span class="text-on-muted font-bold w-6">${index + 1}</span>
                <span class="text-sm font-medium text-on-base">${escapeHtml(doc.title || doc.id || '-')}</span>
            </div>
            <span class="text-xs text-on-muted">${doc.views || doc.count || 0} 次访问</span>
        </div>
    `).join('');
}

/**
 * 渲染最近活动列表
 */
function renderRecentActivity(activities) {
    const container = document.getElementById('recentActivity');
    if (!container) return;

    if (activities.length === 0) {
        container.innerHTML = '<p class="text-on-muted text-center py-4">暂无活动</p>';
        return;
    }

    container.innerHTML = activities.slice(0, 10).map(activity => `
        <div class="flex items-center justify-between p-2 hover:bg-bg-hover rounded transition-colors">
            <div>
                <span class="text-sm font-medium text-on-base">${escapeHtml(activity.action || activity.type || '-')}</span>
                <span class="text-xs text-on-muted ml-2">${escapeHtml(activity.target || activity.target_path || '')}</span>
            </div>
            <span class="text-xs text-on-muted">${escapeHtml(activity.user || '')} · ${escapeHtml(activity.timestamp || '')}</span>
        </div>
    `).join('');
}

/**
 * 生成颜色数组
 */
function generateColors(count) {
    // 调色板取自当前主题的语义类型色变量，随主题切换换肤；带 hex 兜底
    const palette = [
        cssVar('--color-accent-primary', '#667eea'),
        cssVar('--color-accent-secondary', '#764ba2'),
        cssVar('--color-type-fact', '#22c55e'),
        cssVar('--color-type-opinion', '#ef4444'),
        cssVar('--color-type-data', '#f97316'),
        cssVar('--color-type-method', '#3b82f6'),
        cssVar('--color-type-definition', '#a855f7'),
        cssVar('--color-type-question', '#14b8a6'),
        cssVar('--color-confidence-high', '#16a34a'),
        cssVar('--color-type-reference', '#6b7280'),
    ];
    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(palette[i % palette.length]);
    }
    return colors;
}

/**
 * 显示错误信息
 */
function showError(message) {
    const container = document.querySelector('.dashboard-view');
    if (!container) return;

    const errorDiv = document.createElement('div');
    errorDiv.className = 'bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4';
    errorDiv.innerHTML = `
        <div class="flex items-center justify-between">
            <span>${escapeHtml(message)}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="text-red-500 hover:text-red-700">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        </div>
    `;
    container.insertBefore(errorDiv, container.firstChild);
}

/**
 * 主渲染函数
 */
export async function render(container) {
    // 渲染 HTML 结构
    const html = `
        <div class="dashboard-view animate-fade-in">
            <div class="p-6">
                <!-- 页面标题 -->
                <div class="mb-6">
                    <h1 class="text-2xl font-bold text-on-base">📊 数据看板</h1>
                    <p class="text-on-surface text-sm mt-1">系统数据统计与可视化分析</p>
                </div>

                <!-- 刷新按钮 -->
                <div class="mb-4">
                    <button onclick="window.DashboardRefresh()" class="px-4 py-2 bg-gradient-brand text-on-accent rounded hover:opacity-90 transition-opacity text-sm">
                        刷新数据
                    </button>
                </div>

                <!-- 统计卡片 -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div class="bg-bg-surface rounded-lg shadow p-5">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-2xl font-bold text-on-base" id="totalAtoms">0</div>
                                <div class="text-sm text-on-muted mt-1">原子总数</div>
                            </div>
                            <div class="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center text-2xl">
                                📄
                            </div>
                        </div>
                    </div>
                    <div class="bg-bg-surface rounded-lg shadow p-5">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-2xl font-bold text-on-base" id="totalTags">0</div>
                                <div class="text-sm text-on-muted mt-1">标签数</div>
                            </div>
                            <div class="w-12 h-12 bg-green-100 text-green-600 rounded-lg flex items-center justify-center text-2xl">
                                🏷️
                            </div>
                        </div>
                    </div>
                    <div class="bg-bg-surface rounded-lg shadow p-5">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-2xl font-bold text-on-base" id="totalAuthors">0</div>
                                <div class="text-sm text-on-muted mt-1">作者数</div>
                            </div>
                            <div class="w-12 h-12 bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center text-2xl">
                                👤
                            </div>
                        </div>
                    </div>
                    <div class="bg-bg-surface rounded-lg shadow p-5">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-2xl font-bold text-on-base" id="totalActions">0</div>
                                <div class="text-sm text-on-muted mt-1">操作总数</div>
                            </div>
                            <div class="w-12 h-12 bg-orange-100 text-orange-600 rounded-lg flex items-center justify-center text-2xl">
                                ⚡
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 图表区域 - 第一行 -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                    <div class="bg-bg-surface rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-on-base mb-4">按类型分布</h2>
                        <div style="height: 250px;">
                            <canvas id="typeChart"></canvas>
                        </div>
                    </div>
                    <div class="bg-bg-surface rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-on-base mb-4">按状态分布</h2>
                        <div style="height: 250px;">
                            <canvas id="statusChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- 图表区域 - 第二行 -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                    <div class="bg-bg-surface rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-on-base mb-4">热门标签 Top 10</h2>
                        <div style="height: 250px;">
                            <canvas id="tagChart"></canvas>
                        </div>
                    </div>
                    <div class="bg-bg-surface rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-on-base mb-4">用户活跃度</h2>
                        <div style="height: 250px;">
                            <canvas id="userChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- 列表区域 -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div class="bg-bg-surface rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-on-base mb-4">热门文档</h2>
                        <div id="popularDocs" class="space-y-1">
                            <p class="text-on-muted text-center py-4">加载中...</p>
                        </div>
                    </div>
                    <div class="bg-bg-surface rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-on-base mb-4">最近活动</h2>
                        <div id="recentActivity" class="space-y-1">
                            <p class="text-on-muted text-center py-4">加载中...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    if (container) {
        container.innerHTML = html;
    }

    // 尝试加载 Chart.js 并初始化图表
    try {
        await loadChartJS();
        await loadData();
    } catch (error) {
        console.error('Chart.js 加载失败，使用降级方案:', error);
        // 降级方案：仅显示数字统计
        showError('图表加载失败，仅显示数字统计');
        await loadData();
    }

    // 注册全局清理 / 刷新 / 主题重绘函数
    window.DashboardCleanup = destroyCharts;
    window.DashboardRefresh = loadData;
    // 主题切换时由 index.html setTheme() 调用，重新读取 CSS 变量并重绘图表
    window.DashboardRerender = loadData;

    return html;
}

export default {
    render,
    name: '数据看板',
    icon: '📊'
};
