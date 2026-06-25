/**
 * 新建/编辑视图模块
 *
 * 迁移自 /views/admin/edit.html
 * 提供 Markdown 编辑器、实时预览、原子创建/更新功能
 */

export function render(container) {
    const html = `<div class="edit-view animate-fade-in">
        <div class="overview-container p-6">

            <!-- Header Card -->
            <div class="overview-card text-center mb-6" style="padding: 40px;">
                <h1 class="text-3xl font-bold gradient-title mb-2" id="pageTitle">✏️ 新建原子</h1>
                <p class="text-on-surface">创建和编辑知识原子</p>
            </div>

            <!-- 元信息表单 -->
            <div class="overview-card mb-4 p-6">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">标题 *</label>
                        <input type="text" id="atomTitle" class="w-full px-3 py-2 border-2 border-border-base rounded-lg focus:outline-none focus:border-accent-primary transition-colors" placeholder="原子标题">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">类型</label>
                        <select id="atomType" class="w-full px-3 py-2 border-2 border-border-base rounded-lg focus:outline-none focus:border-accent-primary transition-colors">
                            <option value="fact">fact（事实）</option>
                            <option value="method">method（方法）</option>
                            <option value="definition">definition（定义）</option>
                            <option value="opinion">opinion（观点）</option>
                            <option value="data">data（数据）</option>
                            <option value="question">question（问题）</option>
                            <option value="reference">reference（参考）</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-on-base mb-1">标签（逗号分隔）</label>
                        <input type="text" id="atomTags" class="w-full px-3 py-2 border-2 border-border-base rounded-lg focus:outline-none focus:border-accent-primary transition-colors" placeholder="标签1, 标签2">
                    </div>
                </div>
            </div>

            <!-- 编辑器 + 预览 -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div class="overview-card p-4">
                    <div class="flex items-center justify-between mb-2">
                        <h2 class="text-sm font-medium text-on-base">Markdown 编辑器</h2>
                        <div class="flex flex-wrap gap-1">
                            <button onclick="window.EditView.insertText('**', '**', '粗体')" class="px-2 py-1 text-xs bg-bg-surface-alt text-on-base rounded hover:bg-accent-primary hover:text-on-accent transition-colors">B</button>
                            <button onclick="window.EditView.insertText('*', '*', '斜体')" class="px-2 py-1 text-xs bg-bg-surface-alt text-on-base rounded hover:bg-accent-primary hover:text-on-accent transition-colors">I</button>
                            <button onclick="window.EditView.insertText('## ', '', '标题')" class="px-2 py-1 text-xs bg-bg-surface-alt text-on-base rounded hover:bg-accent-primary hover:text-on-accent transition-colors">H</button>
                            <button onclick="window.EditView.insertText('- ', '', '列表项')" class="px-2 py-1 text-xs bg-bg-surface-alt text-on-base rounded hover:bg-accent-primary hover:text-on-accent transition-colors">•</button>
                            <button onclick="window.EditView.insertText('[', '](url)', '链接')" class="px-2 py-1 text-xs bg-bg-surface-alt text-on-base rounded hover:bg-accent-primary hover:text-on-accent transition-colors">🔗</button>
                            <button onclick="window.EditView.insertText('\`\`\`\n', '\n\`\`\`', '代码块')" class="px-2 py-1 text-xs bg-bg-surface-alt text-on-base rounded hover:bg-accent-primary hover:text-on-accent transition-colors">{ }</button>
                        </div>
                    </div>
                    <textarea id="editor" class="w-full px-3 py-2 border-2 border-border-base rounded-lg focus:outline-none focus:border-accent-primary transition-colors font-mono text-sm leading-relaxed resize-y" rows="20" placeholder="在此输入 Markdown 内容..."># 标题

在这里输入内容...</textarea>
                </div>
                <div class="overview-card p-4">
                    <h2 class="text-sm font-medium text-on-base mb-2">实时预览</h2>
                    <div id="preview" class="prose max-w-none text-on-base"></div>
                </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex flex-wrap gap-2 mt-4">
                <button onclick="window.EditView.saveAtom()" class="px-4 py-2 bg-status-success text-on-accent rounded-lg hover:opacity-90 transition-opacity">保存原子</button>
                <button onclick="window.EditView.saveAndPublish()" class="px-4 py-2 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity">保存并发布</button>
                <button onclick="window.EditView.showLoadModal()" class="px-4 py-2 bg-bg-surface-alt text-on-base rounded-lg hover:bg-border-base transition-colors">加载已有原子</button>
                <a href="#overview" class="px-4 py-2 bg-bg-surface-alt text-on-base rounded-lg hover:bg-border-base transition-colors inline-flex items-center">取消</a>
            </div>

            <!-- 加载原子的弹窗 -->
            <div id="loadModal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
                <div class="bg-bg-surface rounded-xl p-6 w-full max-w-md">
                    <h3 class="text-lg font-bold text-on-base mb-4">加载已有原子</h3>
                    <div class="space-y-3">
                        <input type="text" id="loadAtomId" class="w-full px-3 py-2 border-2 border-border-base rounded-lg focus:outline-none focus:border-accent-primary transition-colors" placeholder="原子 ID 或路径（如 atoms/facts/xxx）">
                        <button onclick="window.EditView.doLoadAtom()" class="w-full px-4 py-2 bg-gradient-brand text-on-accent rounded-lg hover:opacity-90 transition-opacity">加载</button>
                    </div>
                    <button onclick="window.EditView.hideLoadModal()" class="w-full mt-2 px-4 py-2 bg-bg-surface-alt text-on-base rounded-lg hover:bg-border-base transition-colors">取消</button>
                </div>
            </div>

        </div>
    </div>`;

    if (container) {
        container.innerHTML = html;
    }

    // 初始化
    initEditor();

    return html;
}

// 状态变量
let currentAtomId = null;

/**
 * 初始化编辑器
 */
function initEditor() {
    // 读取 URL 参数
    const params = new URLSearchParams(window.location.hash.split('?')[1]);
    const atomId = params.get('atom_id');

    if (atomId) {
        currentAtomId = atomId;
        loadAtomById(atomId);
    }

    // 设置实时预览
    const editor = document.getElementById('editor');
    if (editor) {
        editor.addEventListener('input', updatePreview);
        updatePreview(); // 初始预览
    }
}

/**
 * 更新预览
 */
function updatePreview() {
    const editor = document.getElementById('editor');
    const preview = document.getElementById('preview');

    if (editor && preview && window.marked) {
        preview.innerHTML = window.marked.parse(editor.value);
    }
}

/**
 * 插入文本（工具栏按钮）
 */
function insertText(prefix, suffix, placeholder) {
    const editor = document.getElementById('editor');
    if (!editor) return;

    const start = editor.selectionStart;
    const end = editor.selectionEnd;
    const selected = editor.value.substring(start, end) || placeholder;
    const newText = prefix + selected + suffix;

    editor.value = editor.value.substring(0, start) + newText + editor.value.substring(end);
    editor.focus();
    editor.selectionStart = start + prefix.length;
    editor.selectionEnd = start + prefix.length + selected.length;

    updatePreview();
}

/**
 * 保存原子
 */
async function saveAtom(publish = false) {
    const titleEl = document.getElementById('atomTitle');
    const typeEl = document.getElementById('atomType');
    const tagsEl = document.getElementById('atomTags');
    const editorEl = document.getElementById('editor');

    const title = titleEl?.value.trim();
    const type = typeEl?.value;
    const tagsStr = tagsEl?.value.trim();
    const body = editorEl?.value;

    if (!title) {
        alert('请输入标题');
        return;
    }

    if (!body?.trim()) {
        alert('请输入内容');
        return;
    }

    const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [];

    try {
        let result;

        if (currentAtomId) {
            // 更新已有原子
            result = await window.WikiAPI.put('/api/atoms/' + encodeURIComponent(currentAtomId), { body, title, tags });
        } else {
            // 创建新原子
            result = await window.WikiAPI.post('/api/atoms', { type, title, body, tags });
            if (result.status === 'ok' && result.id) {
                currentAtomId = result.id;
            }
        }

        if (result.status === 'ok') {
            if (publish && currentAtomId) {
                await window.WikiAPI.post('/api/atoms/' + encodeURIComponent(currentAtomId) + '/publish');
                alert('已保存并发布');
            } else {
                alert('保存成功');
            }

            const pageTitle = document.getElementById('pageTitle');
            if (pageTitle) {
                pageTitle.textContent = `编辑: ${title}`;
            }
        } else {
            alert('保存失败: ' + (result.error || '未知错误'));
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

/**
 * 保存并发布
 */
function saveAndPublish() {
    saveAtom(true);
}

/**
 * 显示加载弹窗
 */
function showLoadModal() {
    const modal = document.getElementById('loadModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

/**
 * 隐藏加载弹窗
 */
function hideLoadModal() {
    const modal = document.getElementById('loadModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

/**
 * 执行加载（从弹窗输入）
 */
async function doLoadAtom() {
    const inputEl = document.getElementById('loadAtomId');
    const id = inputEl?.value.trim();

    if (!id) {
        alert('请输入原子 ID');
        return;
    }

    await loadAtomById(id);
    hideLoadModal();
}

/**
 * 根据 ID 加载原子
 */
async function loadAtomById(id) {
    try {
        const data = await window.WikiAPI.get('/api/atoms/' + encodeURIComponent(id));

        if (data.error) {
            alert(data.error);
            return;
        }

        currentAtomId = id;

        // 填充表单
        const fm = data.frontmatter || {};

        const titleEl = document.getElementById('atomTitle');
        const typeEl = document.getElementById('atomType');
        const tagsEl = document.getElementById('atomTags');
        const editorEl = document.getElementById('editor');

        if (titleEl) titleEl.value = fm.title || '';
        if (typeEl) typeEl.value = fm.type || 'fact';
        if (tagsEl) tagsEl.value = (fm.tags || []).join(', ');

        // 提取 body（去掉 frontmatter）
        let body = data.body || data.content || '';
        if (editorEl) editorEl.value = body.trim();

        const pageTitle = document.getElementById('pageTitle');
        if (pageTitle) {
            pageTitle.textContent = `编辑: ${fm.title || id}`;
        }

        updatePreview();
    } catch (e) {
        alert('加载失败: ' + e.message);
    }
}

// 导出到全局（供按钮 onclick 调用）
window.EditView = {
    insertText,
    saveAtom,
    saveAndPublish,
    showLoadModal,
    hideLoadModal,
    doLoadAtom
};

export default {
    render: render,
    name: '新建/编辑',
    icon: '✏️'
};
