/**
 * QA 视图模块 - AI 问答功能
 *
 * 提取自 /views/admin/qa.html，改造为 SPA 模块
 */

export function render(container) {
    const html = `
    <div class="qa-view h-full flex flex-col">
        <!-- Header -->
        <header class="bg-white shadow-sm">
            <div class="max-w-5xl mx-auto px-6 py-4 flex flex-wrap gap-2 items-center justify-between">
                <div class="flex items-center gap-4">
                    <h1 class="text-xl font-bold text-gray-800">AI 知识问答</h1>
                    <span id="modeIndicator" class="mode-badge mode-retrieval">检索模式</span>
                </div>
                <div class="flex items-center gap-4">
                    <button onclick="showLLMConfig()" class="btn btn-secondary text-sm">⚙️ LLM 配置</button>
                    <button onclick="clearHistory()" class="btn btn-secondary text-sm">清空历史</button>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <div class="flex-1 overflow-hidden">
            <div class="h-full flex">
                <!-- 对话历史侧边栏 -->
                <aside class="w-64 bg-gray-50 border-r overflow-y-auto hidden md:block">
                    <div class="p-4">
                        <h2 class="text-sm font-semibold text-gray-700 mb-3">💬 对话历史</h2>
                        <div id="historyList" class="space-y-2"></div>
                    </div>
                </aside>

                <!-- 对话区域 -->
                <main class="flex-1 flex flex-col bg-white">
                    <!-- 消息列表 -->
                    <div id="chatMessages" class="flex-1 overflow-y-auto p-6 space-y-4">
                        <div class="msg-bot">
                            <p>👋 你好！我是知识库问答助手，支持多轮对话。</p>
                            <p class="mt-2">试试以下问题：</p>
                            <div class="mt-3 space-x-2">
                                <button onclick="askQuestion('最近有什么新内容？')" class="suggestion-chip">最近有什么新内容？</button>
                                <button onclick="askQuestion('知识库中有哪些类型？')" class="suggestion-chip">知识库中有哪些类型？</button>
                                <button onclick="askQuestion('总结一下知识库内容')" class="suggestion-chip">总结一下知识库内容</button>
                            </div>
                        </div>
                    </div>

                    <!-- 输入区域 -->
                    <div class="border-t bg-white p-4">
                        <div class="max-w-4xl mx-auto flex gap-3">
                            <input type="text" id="questionInput"
                                class="flex-1 border rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="输入你的问题..." onkeypress="handleKeyPress(event)">
                            <button onclick="sendQuestion()" class="btn btn-primary px-6">
                                发送
                            </button>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    </div>

    <style>
        .mode-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
        .mode-retrieval { background: #f3f4f6; color: #374151; }
        .mode-llm { background: #dbeafe; color: #1d4ed8; }
        .msg-user { background: #667eea; color: white; padding: 12px 16px; border-radius: 12px 12px 4px 12px; max-width: 80%; margin-left: auto; }
        .msg-bot { background: #f7fafc; color: #2d3748; padding: 12px 16px; border-radius: 12px 12px 12px 4px; max-width: 80%; border: 1px solid #e2e8f0; }
        .suggestion-chip { display: inline-block; padding: 4px 12px; background: #ebf8ff; color: #2b6cb0; border-radius: 16px; font-size: 13px; cursor: pointer; margin: 4px; transition: all 0.2s; }
        .suggestion-chip:hover { background: #bee3f8; }
        .btn { padding: 8px 16px; border-radius: 6px; font-size: 14px; cursor: pointer; transition: all 0.2s; border: none; }
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover { background: #5a67d8; }
        .btn-secondary { background: #e2e8f0; color: #4a5568; }
        .btn-secondary:hover { background: #cbd5e0; }
    </style>
    `;

    if (container) {
        container.innerHTML = html;
        initQAView();
    }

    return html;
}

// 初始化 QA 视图
function initQAView() {
    console.log('[QA View] 初始化 AI 问答模块');

    // 加载对话历史
    loadHistory();

    // 设置当前用户（如果元素存在）
    const userElement = document.getElementById('currentUserName');
    const user = window.__currentUser;
    if (userElement && user) {
        userElement.textContent = user.username || user;
    }
}

// 加载对话历史
function loadHistory() {
    const historyList = document.getElementById('historyList');
    if (!historyList) return;

    // 从 localStorage 加载历史
    const history = JSON.parse(localStorage.getItem('qa-history') || '[]');

    historyList.innerHTML = history.map((item, idx) => `
        <div class="history-item" onclick="loadConversation(${idx})">
            <div class="text-sm font-medium text-gray-700">${item.title}</div>
            <div class="text-xs text-gray-500">${item.date}</div>
        </div>
    `).join('');
}

// 发送问题
window.sendQuestion = async function() {
    const input = document.getElementById('questionInput');
    const question = input.value.trim();

    if (!question) return;

    // 添加用户消息
    addMessage(question, 'user');
    input.value = '';

    // 显示加载状态
    const loadingId = addMessage('思考中...', 'bot', true);

    try {
        // 调用 API
        const response = await fetch('/api/qa/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        // 移除加载状态
        removeMessage(loadingId);

        // 显示回答
        addMessage(data.answer || data.response, 'bot');

    } catch (error) {
        removeMessage(loadingId);
        addMessage('抱歉，发生了错误：' + error.message, 'bot');
    }
};

// 添加消息
function addMessage(content, type, isLoading = false) {
    const container = document.getElementById('chatMessages');
    const id = 'msg-' + Date.now();

    const div = document.createElement('div');
    div.id = id;
    div.className = type === 'user' ? 'msg-user' : 'msg-bot';
    div.innerHTML = isLoading ? `<span class="typing">${content}</span>` : content;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    return id;
}

// 移除消息
function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// 按键处理
window.handleKeyPress = function(event) {
    if (event.key === 'Enter') {
        sendQuestion();
    }
};

// 快速提问
window.askQuestion = function(question) {
    document.getElementById('questionInput').value = question;
    sendQuestion();
};

// 清空历史
window.clearHistory = function() {
    if (confirm('确定要清空所有对话历史吗？')) {
        localStorage.removeItem('qa-history');
        loadHistory();
        document.getElementById('chatMessages').innerHTML = `
            <div class="msg-bot">
                <p>👋 对话历史已清空。开始新的对话吧！</p>
            </div>
        `;
    }
};

// 显示 LLM 配置
window.showLLMConfig = function() {
    alert('LLM 配置功能开发中...');
};

export default {
    render: render,
    name: 'AI 问答',
    icon: '❓'
};
