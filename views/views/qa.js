/**
 * QA 视图模块 - AI 问答功能
 *
 * 提取自 /views/admin/qa.html，改造为 SPA 模块
 * 采用内联视图风格（overview-container + overview-card）
 */

import { escapeHtml } from '../utils/ui-components.js';

export function render(container) {
    const html = `
    <div class="qa-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- Header Card -->
            <div class="overview-card text-center mb-6" style="padding: 40px;">
                <h1 class="text-3xl font-bold gradient-title mb-2">❓ AI 知识问答</h1>
                <p class="text-on-surface">基于知识库的智能问答助手，支持多轮对话</p>
                <div class="mt-4">
                    <span id="modeIndicator" class="px-3 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700">
                        检索模式
                    </span>
                </div>
            </div>

            <!-- 对话区域 -->
            <div class="overview-card mb-6">
                <h2 class="text-xl font-semibold text-on-base mb-4 flex items-center">
                    <span class="text-2xl mr-2">💬</span>
                    对话历史
                    <button onclick="clearHistory()" class="ml-auto text-sm text-on-muted hover:text-red-500">
                        清空历史
                    </button>
                </h2>

                <!-- 消息列表 -->
                <div id="chatMessages" class="space-y-4 max-h-96 overflow-y-auto p-4 bg-bg-surface-alt rounded-lg">
                    <div class="bg-white rounded-lg p-4">
                        <p class="text-on-surface">👋 你好！我是知识库问答助手。</p>
                        <p class="text-on-muted mt-2 text-sm">我会记住你之前的问题，可以基于上下文继续追问。</p>
                        <div class="mt-4 flex flex-wrap gap-2">
                            <button onclick="askQuestion('最近有什么新内容？')"
                                class="px-3 py-1.5 text-sm bg-accent-soft text-accent rounded-full hover:bg-accent hover:text-on-accent transition-colors">
                                最近有什么新内容？
                            </button>
                            <button onclick="askQuestion('知识库中有哪些类型？')"
                                class="px-3 py-1.5 text-sm bg-accent-soft text-accent rounded-full hover:bg-accent hover:text-on-accent transition-colors">
                                知识库中有哪些类型？
                            </button>
                            <button onclick="askQuestion('总结一下知识库内容')"
                                class="px-3 py-1.5 text-sm bg-accent-soft text-accent rounded-full hover:bg-accent hover:text-on-accent transition-colors">
                                总结一下知识库内容
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 输入区域 -->
                <div class="mt-4 flex gap-3">
                    <input type="text" id="questionInput"
                        class="flex-1 border border-border-th rounded-lg px-4 py-3 bg-bg-surface text-on-base focus:outline-none focus:ring-2 focus:ring-accent"
                        placeholder="输入你的问题..."
                        onkeypress="if(event.key==='Enter') sendQuestion()">
                    <button onclick="sendQuestion()"
                        class="px-6 py-3 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity font-medium">
                        发送
                    </button>
                </div>
                <p class="text-xs text-on-muted text-center mt-2">
                    💡 系统会记住最近 10 轮对话。无 LLM 时使用检索模式，配置 LLM 后获得更智能的回答。
                </p>
            </div>

            <!-- 快捷操作 -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="overview-card">
                    <h3 class="text-lg font-semibold text-on-base mb-3 flex items-center">
                        <span class="text-xl mr-2">⚙️</span>
                        LLM 配置
                    </h3>
                    <p class="text-on-surface text-sm mb-3">配置 LLM API 以获得更智能的回答</p>
                    <button onclick="showLLMConfig()"
                        class="w-full px-4 py-2 bg-bg-surface-alt text-on-surface rounded-lg hover:bg-bg-hover transition-colors text-sm">
                        配置 LLM
                    </button>
                </div>

                <div class="overview-card">
                    <h3 class="text-lg font-semibold text-on-base mb-3 flex items-center">
                        <span class="text-xl mr-2">📚</span>
                        知识库浏览
                    </h3>
                    <p class="text-on-surface text-sm mb-3">在浏览视图中查看所有知识原子</p>
                    <a href="#browse"
                        class="block w-full px-4 py-2 bg-bg-surface-alt text-on-surface rounded-lg hover:bg-bg-hover transition-colors text-sm text-center">
                        浏览知识库
                    </a>
                </div>
            </div>

        </div>
    </div>
    `;

    if (container) {
        container.innerHTML = html;
        initQAView();
    }

    return html;
}

// 初始化 QA 视图
function initQAView() {
    // 暴露全局接口供 onclick 使用
    window.QAView = {
        hideLLMConfig,
        saveLLMConfig,
        updateTemperatureDisplay
    };

    // 加载对话历史
    loadHistory();

    // 检查 LLM 配置并更新模式指示器
    const llmConfig = JSON.parse(localStorage.getItem('llm-config') || '{}');
    const modeIndicator = document.getElementById('modeIndicator');
    if (modeIndicator && llmConfig.apiUrl && llmConfig.apiKey) {
        modeIndicator.textContent = 'LLM 模式';
        modeIndicator.className = 'px-3 py-1 text-xs font-medium rounded-full bg-accent-soft text-accent';
    }
}

// 加载对话历史
async function loadHistory() {
    try {
        const data = await WikiAPI.get('/api/qa/history');
        const history = data.history || [];
        // Debug: 

        // 渲染历史消息
        const container = document.getElementById('chatMessages');
        if (history.length === 0) {
            // 保持默认欢迎消息
            return;
        }

        // 清空现有消息并渲染历史
        container.innerHTML = '';
        history.forEach(msg => {
            if (msg.role === 'user') {
                addMessageToContainer(msg.content, 'user');
            } else {
                addMessageToContainer(msg.content, 'bot');
            }
        });

        // 滚动到底部
        container.scrollTop = container.scrollHeight;
    } catch (error) {
        console.error('[QA View] 加载历史失败:', error);
        // 失败时保持默认欢迎界面
    }
}

// 添加消息到容器（不返回 ID）
function addMessageToContainer(content, type) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');

    if (type === 'user') {
        div.className = 'bg-gradient-brand text-on-accent rounded-lg p-4 ml-auto max-w-2xl';
        div.innerHTML = content;
    } else {
        div.className = 'bg-white rounded-lg p-4 max-w-2xl';
        div.innerHTML = `<div class="text-on-surface">${content}</div>`;
    }

    container.appendChild(div);
}

// 发送问题
window.sendQuestion = async function() {
    const input = document.getElementById('questionInput');
    const question = input.value.trim();

    if (!question) return;

    addMessage(question, 'user');
    input.value = '';

    const loadingId = addMessage('思考中...', 'bot', true);

    try {
        // 统一走 WikiAPI（内置凭据与 401 处理）
        const data = await WikiAPI.post('/api/qa/ask', { question });
        removeMessage(loadingId);
        addMessage(data.answer || data.response || '抱歉，我暂时无法回答这个问题。', 'bot');

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

    if (type === 'user') {
        div.className = 'bg-gradient-brand text-on-accent rounded-lg p-4 ml-auto max-w-2xl';
        div.innerHTML = content;
    } else {
        div.className = 'bg-white rounded-lg p-4 max-w-2xl';
        div.innerHTML = isLoading
            ? `<span class="text-on-muted">${content}</span>`
            : `<div class="text-on-surface">${content}</div>`;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    return id;
}

// 移除消息
function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// 快速提问
window.askQuestion = function(question) {
    document.getElementById('questionInput').value = question;
    sendQuestion();
};

// 清空历史
window.clearHistory = async function() {
    if (confirm('确定要清空所有对话历史吗？')) {
        try {
            const result = await WikiAPI.post('/api/qa/clear');
            if (result.success) {
                document.getElementById('chatMessages').innerHTML = `
                    <div class="bg-white rounded-lg p-4">
                        <p class="text-on-surface">👋 对话历史已清空。开始新的对话吧！</p>
                        <p class="text-on-muted mt-2 text-sm">我会记住你之前的问题，可以基于上下文继续追问。</p>
                        <div class="mt-4 flex flex-wrap gap-2">
                            <button onclick="askQuestion('最近有什么新内容？')"
                                class="px-3 py-1.5 text-sm bg-accent-soft text-accent rounded-full hover:bg-accent hover:text-on-accent transition-colors">
                                最近有什么新内容？
                            </button>
                            <button onclick="askQuestion('知识库中有哪些类型？')"
                                class="px-3 py-1.5 text-sm bg-accent-soft text-accent rounded-full hover:bg-accent hover:text-on-accent transition-colors">
                                知识库中有哪些类型？
                            </button>
                            <button onclick="askQuestion('总结一下知识库内容')"
                                class="px-3 py-1.5 text-sm bg-accent-soft text-accent rounded-full hover:bg-accent hover:text-on-accent transition-colors">
                                总结一下知识库内容
                            </button>
                        </div>
                    </div>
                `;
                // Debug: 
            } else {
                alert('清空失败: ' + (result.error || '未知错误'));
            }
        } catch (error) {
            console.error('[QA View] 清空历史失败:', error);
            alert('清空失败: ' + error.message);
        }
    }
};

// 显示 LLM 配置
window.showLLMConfig = function() {
    // 从 localStorage 加载现有配置
    const savedConfig = JSON.parse(localStorage.getItem('llm-config') || '{}');
    const currentUrl = savedConfig.apiUrl || '';
    const currentKey = savedConfig.apiKey || '';
    const currentModel = savedConfig.model || 'gpt-3.5-turbo';
    const currentTemperature = savedConfig.temperature || 0.7;

    const modalHtml = `
    <div id="llm-config-modal-overlay" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
         onclick="if(event.target.id==='llm-config-modal-overlay') window.QAView.hideLLMConfig()">
        <div class="bg-bg-surface rounded-lg shadow-xl p-6 max-w-md w-full mx-4 animate-fade-in">
            <h3 class="text-lg font-semibold text-on-base mb-4 flex items-center">
                <span class="text-xl mr-2">⚙️</span>
                LLM 配置
            </h3>

            <!-- API URL -->
            <div class="mb-4">
                <label class="block text-sm font-medium text-on-base mb-1">API URL:</label>
                <input type="text" id="llmApiUrl" value="${escapeHtml(currentUrl)}"
                    class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                    placeholder="例如: https://api.openai.com/v1">
            </div>

            <!-- API Key -->
            <div class="mb-4">
                <label class="block text-sm font-medium text-on-base mb-1">API Key:</label>
                <input type="password" id="llmApiKey" value="${escapeHtml(currentKey)}"
                    class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                    placeholder="sk-...">
                <p class="text-xs text-on-muted mt-1">⚠️ API Key 将保存在本地浏览器中</p>
            </div>

            <!-- 模型选择 -->
            <div class="mb-4">
                <label class="block text-sm font-medium text-on-base mb-1">模型:</label>
                <select id="llmModel" class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm focus:outline-none focus:ring-2 focus:ring-accent">
                    <option value="gpt-4" ${currentModel === 'gpt-4' ? 'selected' : ''}>GPT-4</option>
                    <option value="gpt-4-turbo" ${currentModel === 'gpt-4-turbo' ? 'selected' : ''}>GPT-4 Turbo</option>
                    <option value="gpt-3.5-turbo" ${currentModel === 'gpt-3.5-turbo' ? 'selected' : ''}>GPT-3.5 Turbo</option>
                    <option value="claude-3-opus" ${currentModel === 'claude-3-opus' ? 'selected' : ''}>Claude 3 Opus</option>
                    <option value="claude-3-sonnet" ${currentModel === 'claude-3-sonnet' ? 'selected' : ''}>Claude 3 Sonnet</option>
                    <option value="claude-3-haiku" ${currentModel === 'claude-3-haiku' ? 'selected' : ''}>Claude 3 Haiku</option>
                    <option value="custom" ${currentModel === 'custom' ? 'selected' : ''}>自定义模型</option>
                </select>
            </div>

            <!-- 自定义模型名称（仅在 custom 时显示） -->
            <div class="mb-4" id="customModelInput" style="${currentModel !== 'custom' ? 'display:none' : ''}">
                <label class="block text-sm font-medium text-on-base mb-1">自定义模型名称:</label>
                <input type="text" id="llmCustomModel" value="${escapeHtml(savedConfig.customModel || '')}"
                    class="w-full px-3 py-2 border border-border rounded bg-bg-surface text-on-base text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                    placeholder="模型名称">
            </div>

            <!-- 温度滑块 -->
            <div class="mb-4">
                <label class="block text-sm font-medium text-on-base mb-1">温度 (Temperature):</label>
                <div class="flex items-center gap-3">
                    <input type="range" id="llmTemperature" min="0" max="1" step="0.1" value="${currentTemperature}"
                        class="flex-1 accent-accent cursor-pointer"
                        oninput="window.QAView.updateTemperatureDisplay(this.value)">
                    <span id="temperatureValue" class="text-sm font-semibold text-accent w-8">${currentTemperature}</span>
                </div>
                <p class="text-xs text-on-muted mt-1">较低温度更保守，较高温度更有创意</p>
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-3 justify-end">
                <button onclick="window.QAView.hideLLMConfig()" class="px-4 py-2 bg-bg-surface-alt text-on-surface rounded-lg hover:bg-bg-hover transition-colors text-sm">
                    取消
                </button>
                <button onclick="window.QAView.saveLLMConfig()" class="px-4 py-2 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity text-sm">
                    保存配置
                </button>
            </div>
        </div>
    </div>
    `;

    // 插入弹窗到 body
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // 监听模型选择变化
    document.getElementById('llmModel').addEventListener('change', function(e) {
        const customInput = document.getElementById('customModelInput');
        if (e.target.value === 'custom') {
            customInput.style.display = '';
        } else {
            customInput.style.display = 'none';
        }
    });
};

// 更新温度显示
function updateTemperatureDisplay(value) {
    document.getElementById('temperatureValue').textContent = value;
}

// 隐藏 LLM 配置弹窗
function hideLLMConfig() {
    const overlay = document.getElementById('llm-config-modal-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// 保存 LLM 配置
function saveLLMConfig() {
    const apiUrl = document.getElementById('llmApiUrl').value.trim();
    const apiKey = document.getElementById('llmApiKey').value.trim();
    const modelSelect = document.getElementById('llmModel');
    const model = modelSelect.value;
    const customModel = document.getElementById('llmCustomModel').value.trim();
    const temperature = parseFloat(document.getElementById('llmTemperature').value);

    // 验证必填字段
    if (!apiUrl) {
        alert('请填写 API URL');
        return;
    }

    if (!apiKey) {
        alert('请填写 API Key');
        return;
    }

    // 保存配置到 localStorage
    const config = {
        apiUrl,
        apiKey,
        model,
        customModel: model === 'custom' ? customModel : '',
        temperature,
        updatedAt: new Date().toISOString()
    };

    localStorage.setItem('llm-config', JSON.stringify(config));

    // Debug: 

    // 更新模式指示器
    const modeIndicator = document.getElementById('modeIndicator');
    if (modeIndicator) {
        modeIndicator.textContent = 'LLM 模式';
        modeIndicator.className = 'px-3 py-1 text-xs font-medium rounded-full bg-accent-soft text-accent';
    }

    alert('✅ LLM 配置已保存！\n\n配置将用于后续的问答请求。');

    hideLLMConfig();
}

export default {
    render: render,
    name: 'AI 问答',
    icon: '❓'
};