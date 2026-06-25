/**
 * 质检视图模块
 *
 * 提取自 /views/admin/quality.html，改造为 SPA 模块
 * 功能：知识原子质量检查、问题统计、筛选与展示
 */

export function render(container) {
  const html = `<div class="quality-view animate-fade-in">
    <div class="overview-container p-6">

      <!-- Header Card -->
      <div class="overview-card text-center mb-6" style="padding: 40px;">
        <h1 class="text-3xl font-bold gradient-title mb-2">✅ 知识质检中心</h1>
        <p class="text-on-surface">检测知识库质量问题，提升内容质量</p>
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 mb-6">
        <div class="overview-card">
          <div class="stat-value text-blue-600" id="qa-totalAtoms">-</div>
          <div class="stat-label text-on-muted">总原子数</div>
        </div>
        <div class="overview-card">
          <div class="stat-value text-red-600" id="qa-totalIssues">-</div>
          <div class="stat-label text-on-muted">问题总数</div>
        </div>
        <div class="overview-card">
          <div class="stat-value text-red-600" id="qa-highSeverity">-</div>
          <div class="stat-label text-on-muted">高优先级</div>
        </div>
        <div class="overview-card">
          <div class="stat-value text-yellow-600" id="qa-mediumSeverity">-</div>
          <div class="stat-label text-on-muted">中优先级</div>
        </div>
        <div class="overview-card">
          <div class="stat-value text-blue-600" id="qa-lowSeverity">-</div>
          <div class="stat-label text-on-muted">低优先级</div>
        </div>
      </div>

      <!-- 筛选器 -->
      <div class="overview-card p-4 mb-4">
        <div class="flex items-center gap-2 flex-wrap">
          <div>
            <label class="text-sm text-on-muted mr-2">问题类型:</label>
            <select id="qa-filterType" class="px-3 py-1 border rounded text-sm bg-bg-surface-alt text-on-base">
              <option value="">全部</option>
              <option value="empty">空白内容</option>
              <option value="outdated">过期内容</option>
              <option value="low_quality">低质量</option>
              <option value="stale_draft">长期草稿</option>
            </select>
          </div>
          <div>
            <label class="text-sm text-on-muted mr-2">严重程度:</label>
            <select id="qa-filterSeverity" class="px-3 py-1 border rounded text-sm bg-bg-surface-alt text-on-base">
              <option value="">全部</option>
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </div>
          <button onclick="window.qaRunCheck()" class="ml-4 px-4 py-2 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity text-sm">
            🔍 重新检测
          </button>
          <div class="ml-auto text-sm text-on-muted" id="qa-checkTime">-</div>
        </div>
      </div>

      <!-- 问题列表 -->
      <div class="overview-card p-6">
        <h2 class="text-lg font-semibold text-on-base mb-4">问题清单</h2>
        <div id="qa-issuesList" class="space-y-3">
          <div class="text-center text-on-muted py-8">点击"重新检测"开始</div>
        </div>
      </div>

    </div>
  </div>`;

  if (container) {
    container.innerHTML = html;
    initQualityView();
  }

  return html;
}

// 模块内部状态
let allIssues = [];

// 初始化视图
function initQualityView() {
  // 绑定筛选器事件
  document.getElementById('qa-filterType').addEventListener('change', renderIssues);
  document.getElementById('qa-filterSeverity').addEventListener('change', renderIssues);

  // 暴露全局函数（供按钮调用）
  window.qaRunCheck = runCheck;

  // 自动执行首次检测
  runCheck();
}

// 执行质检检测
async function runCheck() {
  const listContainer = document.getElementById('qa-issuesList');
  listContainer.innerHTML = '<div class="text-center text-on-muted py-8"><div class="animate-spin inline-block w-6 h-6 border-2 border-current border-r-transparent rounded-full mr-2"></div>检测中，请稍候...</div>';

  try {
    const data = await WikiAPI.get('/api/quality/check');
    allIssues = data.issues || [];

    // 更新统计
    document.getElementById('qa-totalAtoms').textContent = data.total_atoms || 0;
    document.getElementById('qa-totalIssues').textContent = data.total_issues || 0;

    const sc = data.severity_counts || {};
    document.getElementById('qa-highSeverity').textContent = sc.high || 0;
    document.getElementById('qa-mediumSeverity').textContent = sc.medium || 0;
    document.getElementById('qa-lowSeverity').textContent = sc.low || 0;

    document.getElementById('qa-checkTime').textContent = '检测时间: ' + formatDate(data.checked_at);

    renderIssues();
  } catch (e) {
    listContainer.innerHTML = `<div class="text-red-500 text-center py-8">检测失败: ${e.message}</div>`;
  }
}

// 渲染问题列表
function renderIssues() {
  const filterType = document.getElementById('qa-filterType').value;
  const filterSeverity = document.getElementById('qa-filterSeverity').value;

  let filtered = allIssues;
  if (filterType) filtered = filtered.filter(i => i.issue_type === filterType);
  if (filterSeverity) filtered = filtered.filter(i => i.severity === filterSeverity);

  const container = document.getElementById('qa-issuesList');

  if (filtered.length === 0) {
    container.innerHTML = '<div class="text-center text-on-muted py-8">🎉 没有发现问题，知识库质量良好！</div>';
    return;
  }

  const typeNames = {
    empty: '空白内容',
    outdated: '过期内容',
    low_quality: '低质量',
    stale_draft: '长期草稿'
  };

  container.innerHTML = filtered.map(issue => `
    <div class="border border-gray-200 rounded-lg p-4 flex items-center justify-between bg-bg-surface-alt">
      <div class="flex-1">
        <div class="flex items-center gap-2 mb-1">
          <strong class="text-on-base">${escapeHtml(issue.title)}</strong>
          <span class="qa-type-${issue.issue_type} px-2 py-0.5 rounded text-xs">${typeNames[issue.issue_type] || issue.issue_type}</span>
          <span class="qa-severity-${issue.severity}">${issue.severity === 'high' ? '高' : issue.severity === 'medium' ? '中' : '低'}</span>
        </div>
        <div class="text-sm text-on-surface">${escapeHtml(issue.message)}</div>
        <div class="text-xs text-on-muted mt-1">原子 ID: ${escapeHtml(issue.atom_id)}</div>
      </div>
      <a href="#?atom=${encodeURIComponent(issue.atom_id)}" class="px-3 py-1 bg-bg-surface text-on-base border rounded hover:bg-bg-surface-alt transition-colors text-sm">查看</a>
    </div>
  `).join('');
}

// 工具函数：HTML转义
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

// 工具函数：日期格式化
function formatDate(iso) {
  if (!iso) return '-';
  try {
    return new Date(iso).toLocaleString('zh-CN');
  } catch (e) {
    return iso;
  }
}

export default {
  render: render,
  name: '质检',
  icon: '✅'
};