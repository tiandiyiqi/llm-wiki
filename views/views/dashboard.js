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

let chartInstances = [];

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
        container.innerHTML = '<p class="text-gray-500 text-center py-8">暂无数据</p>';
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
                borderColor: '#fff'
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
                        padding: 12
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
        container.innerHTML = '<p class="text-gray-500 text-center py-8">暂无数据</p>';
        return;
    }

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: values,
                backgroundColor: '#667eea',
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
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
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
        container.innerHTML = '<p class="text-gray-500 text-center py-4">暂无数据</p>';
        return;
    }

    container.innerHTML = docs.slice(0, 10).map((doc, index) => `
        <div class="flex items-center justify-between p-2 hover:bg-gray-50 rounded transition-colors">
            <div class="flex items-center gap-3">
                <span class="text-gray-400 font-bold w-6">${index + 1}</span>
                <span class="text-sm font-medium text-gray-800">${escapeHtml(doc.title || doc.id || '-')}</span>
            </div>
            <span class="text-xs text-gray-500">${doc.views || doc.count || 0} 次访问</span>
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
        container.innerHTML = '<p class="text-gray-500 text-center py-4">暂无活动</p>';
        return;
    }

    container.innerHTML = activities.slice(0, 10).map(activity => `
        <div class="flex items-center justify-between p-2 hover:bg-gray-50 rounded transition-colors">
            <div>
                <span class="text-sm font-medium text-gray-800">${escapeHtml(activity.action || activity.type || '-')}</span>
                <span class="text-xs text-gray-500 ml-2">${escapeHtml(activity.target || activity.target_path || '')}</span>
            </div>
            <span class="text-xs text-gray-400">${escapeHtml(activity.user || '')} · ${escapeHtml(activity.timestamp || '')}</span>
        </div>
    `).join('');
}

/**
 * 生成颜色数组
 */
function generateColors(count) {
    const palette = [
        '#667eea', '#764ba2', '#38a169', '#e53e3e', '#dd6b20',
        '#3182ce', '#805ad5', '#319795', '#d69e2e', '#718096'
    ];
    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(palette[i % palette.length]);
    }
    return colors;
}

/**
 * HTML 转义
 */
function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[m]));
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
                    <h1 class="text-2xl font-bold text-gray-800">📊 数据看板</h1>
                    <p class="text-gray-600 text-sm mt-1">系统数据统计与可视化分析</p>
                </div>

                <!-- 刷新按钮 -->
                <div class="mb-4">
                    <button onclick="window.DashboardRefresh()" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors text-sm">
                        刷新数据
                    </button>
                </div>

                <!-- 统计卡片 -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div class="bg-white rounded-lg shadow p-5">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-2xl font-bold text-gray-800" id="totalAtoms">0</div>
                                <div class="text-sm text-gray-500 mt-1">原子总数</div>
                            </div>
                            <div class="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center text-2xl">
                                📄
                            </div>
                        </div>
                    </div>
                    <div class="bg-white rounded-lg shadow p-5">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-2xl font-bold text-gray-800" id="totalTags">0</div>
                                <div class="text-sm text-gray-500 mt-1">标签数</div>
                            </div>
                            <div class="w-12 h-12 bg-green-100 text-green-600 rounded-lg flex items-center justify-center text-2xl">
                                🏷️
                            </div>
                        </div>
                    </div>
                    <div class="bg-white rounded-lg shadow p-5">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-2xl font-bold text-gray-800" id="totalAuthors">0</div>
                                <div class="text-sm text-gray-500 mt-1">作者数</div>
                            </div>
                            <div class="w-12 h-12 bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center text-2xl">
                                👤
                            </div>
                        </div>
                    </div>
                    <div class="bg-white rounded-lg shadow p-5">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-2xl font-bold text-gray-800" id="totalActions">0</div>
                                <div class="text-sm text-gray-500 mt-1">操作总数</div>
                            </div>
                            <div class="w-12 h-12 bg-orange-100 text-orange-600 rounded-lg flex items-center justify-center text-2xl">
                                ⚡
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 图表区域 - 第一行 -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                    <div class="bg-white rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-gray-800 mb-4">按类型分布</h2>
                        <div style="height: 250px;">
                            <canvas id="typeChart"></canvas>
                        </div>
                    </div>
                    <div class="bg-white rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-gray-800 mb-4">按状态分布</h2>
                        <div style="height: 250px;">
                            <canvas id="statusChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- 图表区域 - 第二行 -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                    <div class="bg-white rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-gray-800 mb-4">热门标签 Top 10</h2>
                        <div style="height: 250px;">
                            <canvas id="tagChart"></canvas>
                        </div>
                    </div>
                    <div class="bg-white rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-gray-800 mb-4">用户活跃度</h2>
                        <div style="height: 250px;">
                            <canvas id="userChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- 列表区域 -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div class="bg-white rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-gray-800 mb-4">热门文档</h2>
                        <div id="popularDocs" class="space-y-1">
                            <p class="text-gray-500 text-center py-4">加载中...</p>
                        </div>
                    </div>
                    <div class="bg-white rounded-lg shadow p-6">
                        <h2 class="text-lg font-bold text-gray-800 mb-4">最近活动</h2>
                        <div id="recentActivity" class="space-y-1">
                            <p class="text-gray-500 text-center py-4">加载中...</p>
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

    // 注册全局清理函数
    window.DashboardCleanup = destroyCharts;
    window.DashboardRefresh = loadData;

    return html;
}

export default {
    render,
    name: '数据看板',
    icon: '📊'
};
