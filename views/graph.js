/**
 * Cytoscape.js 知识图谱渲染模块
 *
 * 为 LLM Wiki 提供交互式知识图谱可视化功能
 * 使用 cose 布局算法（内置），支持节点选择、筛选、搜索等交互
 * 主题感知：从 CSS 变量读取颜色，支持运行时主题切换
 */

// 全局变量
let cy = null;  // Cytoscape 实例
let alpineApp = null;  // Alpine.js 应用引用
let nodeSizeScale = 1.0;
let edgeWidthScale = 1.0;
let edgeColorValue = '#ccc';  // 连线颜色

// fcose 四档预置参数（基于原子数量）
const FCOSE_PRESETS = {
    small: {   // ≤20 个节点：舒展、边长大、斥力小
        label: '小',
        idealEdgeLength: 150,
        nodeRepulsion: 5000,
        gravity: 0.25,
        gravityRange: 3.0,
        edgeElasticity: 0.30,
        numIter: 2000,
        initialTemp: 250,
        componentSpacing: 60,
    },
    medium: {  // 21–60 个节点：均衡
        label: '中',
        idealEdgeLength: 100,
        nodeRepulsion: 9000,
        gravity: 0.35,
        gravityRange: 3.8,
        edgeElasticity: 0.40,
        numIter: 2500,
        initialTemp: 200,
        componentSpacing: 80,
    },
    large: {   // 61–150 个节点：紧凑、向心力增强
        label: '大',
        idealEdgeLength: 75,
        nodeRepulsion: 13000,
        gravity: 0.45,
        gravityRange: 4.5,
        edgeElasticity: 0.45,
        numIter: 3000,
        initialTemp: 150,
        componentSpacing: 100,
    },
    xlarge: {  // >150 个节点：强向心、高斥力防重叠
        label: '超大',
        idealEdgeLength: 55,
        nodeRepulsion: 20000,
        gravity: 0.60,
        gravityRange: 5.5,
        edgeElasticity: 0.50,
        numIter: 4000,
        initialTemp: 120,
        componentSpacing: 120,
    }
};

/**
 * 根据节点数量推断最适合的预置档位名称
 * @param {number} nodeCount
 * @returns {'small'|'medium'|'large'|'xlarge'}
 */
function getFcosePresetName(nodeCount) {
    if (nodeCount <= 20) return 'small';
    if (nodeCount <= 60) return 'medium';
    if (nodeCount <= 150) return 'large';
    return 'xlarge';
}

/**
 * 获取 fcose 预置参数对象（不含 label）
 * @param {string} presetName
 * @returns {Object}
 */
function getFcosePreset(presetName) {
    const preset = FCOSE_PRESETS[presetName] || FCOSE_PRESETS['medium'];
    const { label, ...params } = preset;
    return params;
}

// 暴露给 Alpine.js
window.FCOSE_PRESETS = FCOSE_PRESETS;
window.getFcosePresetName = getFcosePresetName;
window.getFcosePreset = getFcosePreset;

// 尝试注册 fcose（如果可用）
let fcoseAvailable = false;
try {
    if (typeof cytoscape !== 'undefined' && typeof cytoscapeFcose !== 'undefined') {
        cytoscape.use(cytoscapeFcose);
        fcoseAvailable = true;
        console.log('fcose 布局已注册');
    }
} catch (e) {
    console.warn('fcose 注册失败，将使用 cose 布局:', e.message);
}

// 类型到 CSS 变量名的映射
const TYPE_CSS_VARS = {
    'method': '--color-type-method',
    'fact': '--color-type-fact',
    'definition': '--color-type-definition',
    'opinion': '--color-type-opinion',
    'data': '--color-type-data',
    'question': '--color-type-question',
    'reference': '--color-type-reference'
};

/**
 * 从 CSS 变量读取主题颜色
 * @param {string} varName - CSS 变量名（如 '--color-accent-primary'）
 * @returns {string} 颜色值
 */
function getThemeColor(varName) {
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

/**
 * 获取类型颜色（从 CSS 变量读取）
 * @param {string} type - 知识原子类型
 * @returns {string} 颜色值
 */
function getTypeColor(type) {
    const cssVar = TYPE_CSS_VARS[type] || TYPE_CSS_VARS['reference'];
    return getThemeColor(cssVar) || '#95a5a6';
}

/**
 * 初始化 Cytoscape 图谱
 * @param {Object} app - Alpine.js 应用实例
 */
function initCytoscapeGraph(app) {
    alpineApp = app;

    const container = document.getElementById('cy');
    if (!container) {
        console.error('图谱容器 #cy 未找到');
        return;
    }

    // 转换数据为 Cytoscape 格式
    const elements = convertToElements(app.graphData);

    if (elements.length === 0) {
        console.warn('没有图谱数据');
        return;
    }

    // 确定布局：优先使用 fcose，如果不可用则使用 cose
    const layoutName = fcoseAvailable ? 'fcose' : 'cose';
    console.log('使用布局:', layoutName);

    // 根据节点数量自动选择预置，并合并到 graphSettings（首次初始化）
    if (layoutName === 'fcose' && app.graphSettings) {
        const nodeCount = app.graphData.nodes.length;
        const autoPreset = getFcosePresetName(nodeCount);
        const presetParams = getFcosePreset(autoPreset);
        // 仅当用户未手动调整过时，自动应用预置
        if (!app.graphSettings._presetApplied) {
            Object.assign(app.graphSettings, presetParams, { _presetApplied: true, _currentPreset: autoPreset });
            console.log(`自动应用 fcose 预置「${FCOSE_PRESETS[autoPreset].label}」（${nodeCount} 节点）`);
        }
    }

    // 初始化 Cytoscape
    // 移动端优化配置
    const isMobile = window.innerWidth < 768;

    cy = cytoscape({
        container: container,
        elements: elements,
        style: getStylesheet(),
        layout: getLayoutOptions(layoutName, app.graphSettings),
        renderer: {
            name: 'canvas'
        },
        wheelSensitivity: 0.3,
        minZoom: 0.2,
        maxZoom: 3,
        // 触摸交互优化
        touchTapThreshold: 8,
        desktopTapThreshold: 4,
        boxSelectionEnabled: !isMobile,
        // 捏合缩放
        zoomOnPinch: true,
        pinchToZoom: true,
        // 拖拽平移
        panningEnabled: true,
        // 移动端减少运动
        motionBlur: !isMobile
    });

    // 绑定事件
    bindEvents();

    console.log('图谱初始化完成，节点数:', app.graphData.nodes.length);
}

/**
 * 转换数据为 Cytoscape 元素格式
 * @param {Object} data - graph-data.json 数据
 * @returns {Array} Cytoscape 元素数组
 */
function convertToElements(data) {
    const elements = [];

    // 添加节点
    for (const node of data.nodes) {
        elements.push({
            data: {
                id: node.id,
                label: truncateLabel(node.label, 15),
                fullLabel: node.label,
                type: node.type,
                description: node.description || '',
                path: node.path,
                color: getTypeColor(node.type),
                in_degree: node.in_degree || 0,
                out_degree: node.out_degree || 0,
                tags: node.tags || []
            }
        });
    }

    // 添加边
    for (const edge of data.edges) {
        elements.push({
            data: {
                id: edge.id,
                source: edge.source,
                target: edge.target
            }
        });
    }

    return elements;
}

/**
 * 获取 Cytoscape 样式定义（主题感知）
 * @returns {Array} 样式数组
 */
function getStylesheet() {
    const accentPrimary = getThemeColor('--color-accent-primary');
    const accentMedium = getThemeColor('--color-accent-medium');
    const textPrimary = getThemeColor('--color-text-primary');
    const bgSurface = getThemeColor('--color-bg-surface');
    const confidenceHigh = getThemeColor('--color-confidence-high');
    const confidenceMedium = getThemeColor('--color-confidence-medium');

    return [
        // 节点默认样式
        {
            selector: 'node',
            style: {
                'label': 'data(label)',
                'text-valign': 'center',
                'text-halign': 'center',
                'font-size': '10px',
                'color': textPrimary || '#333',
                'text-outline-color': bgSurface || '#fff',
                'text-outline-width': '2px',
                'background-color': 'data(color)',
                'width': function(ele) {
                    const degree = (ele.data('in_degree') || 0) + (ele.data('out_degree') || 0);
                    return Math.max(20, Math.min(60, 20 + degree * 5)) * nodeSizeScale;
                },
                'height': function(ele) {
                    const degree = (ele.data('in_degree') || 0) + (ele.data('out_degree') || 0);
                    return Math.max(20, Math.min(60, 20 + degree * 5)) * nodeSizeScale;
                },
                'border-width': '0',
                'opacity': 1
            }
        },
        // 节点悬停样式
        {
            selector: 'node:active',
            style: {
                'overlay-color': accentPrimary || '#667eea',
                'overlay-padding': '5px',
                'overlay-opacity': '0.3'
            }
        },
        // 选中节点样式
        {
            selector: 'node.selected',
            style: {
                'border-width': '3px',
                'border-color': accentPrimary || '#667eea',
                'border-style': 'solid',
                'shadow-color': accentPrimary || '#667eea',
                'shadow-blur': '10px',
                'shadow-offset-x': '0',
                'shadow-offset-y': '0'
            }
        },
        // 高亮节点样式（邻居）
        {
            selector: 'node.highlighted',
            style: {
                'border-width': '2px',
                'border-color': accentMedium || '#a855f7',
                'border-style': 'solid'
            }
        },
        // 淡化节点样式
        {
            selector: 'node.faded',
            style: {
                'opacity': 0.2
            }
        },
        // 孤立节点样式
        {
            selector: 'node.orphan',
            style: {
                'border-width': '1px',
                'border-color': confidenceMedium || '#fbbf24',
                'border-style': 'dashed'
            }
        },
        // 边默认样式
        {
            selector: 'edge',
            style: {
                'width': function() { return 1.5 * edgeWidthScale; },
                'line-color': edgeColorValue,
                'target-arrow-color': edgeColorValue,
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'opacity': 0.7
            }
        },
        // 高亮边样式
        {
            selector: 'edge.highlighted',
            style: {
                'width': function() { return 3 * edgeWidthScale; },
                'line-color': accentPrimary || '#667eea',
                'target-arrow-color': accentPrimary || '#667eea',
                'opacity': 1
            }
        },
        // 淡化边样式
        {
            selector: 'edge.faded',
            style: {
                'opacity': 0.1
            }
        },
        // 搜索匹配节点样式
        {
            selector: 'node.search-match',
            style: {
                'border-width': '3px',
                'border-color': confidenceHigh || '#22c55e',
                'border-style': 'solid',
                'shadow-color': confidenceHigh || '#22c55e',
                'shadow-blur': '15px'
            }
        }
    ];
}

/**
 * 主题切换时重新应用图谱样式
 */
function applyThemeToGraph() {
    if (!cy) return;

    // 重新应用样式表
    cy.style(getStylesheet());

    // 更新每个节点的类型颜色
    cy.nodes().forEach(node => {
        const type = node.data('type');
        node.data('color', getTypeColor(type));
    });

    // 重置连线颜色为默认
    const borderColor = getThemeColor('--color-border');
    edgeColorValue = borderColor || '#ccc';
}

/**
 * 获取布局选项
 * @param {string} layoutName - 布局名称
 * @param {Object} settings - 图谱设置（含 fcose 专属参数）
 * @returns {Object} 布局配置
 */
function getLayoutOptions(layoutName, settings = {}) {
    const layouts = {
        'fcose': {
            name: 'fcose',
            animate: true,
            animationDuration: 600,
            fit: true,
            padding: 60,
            nodeDimensionsIncludeLabels: true,
            // 核心力学参数——从 settings 读取，保证 UI 控件生效
            idealEdgeLength: Number(settings.idealEdgeLength) || 100,
            nodeRepulsion: Number(settings.nodeRepulsion) || 9000,
            gravity: Number(settings.gravity) || 0.35,
            gravityRange: Number(settings.gravityRange) || 3.8,
            edgeElasticity: Number(settings.edgeElasticity) || 0.40,
            numIter: Number(settings.numIter) || 2500,
            initialTemp: Number(settings.initialTemp) || 200,
            componentSpacing: Number(settings.componentSpacing) || 80,
            // 固定参数
            coolingFactor: 0.95,
            minTemp: 1.0,
            randomize: true,
            nestingFactor: 1.2,
            nodeOverlap: 10,
            uniformNodeDimensions: false,
            samplingType: true,
            sampleSize: 25,
            nodeSeparation: 75,
            piTol: 0.0000001,
            // 孤立子图聚拢：向中心的牵引（防止散落边角）
            gravityCompound: 1.0,
            gravityRangeCompound: 1.5,
        },
        'cose': {
            name: 'cose',
            animate: true,
            animationDuration: 500,
            fit: true,
            padding: 50,
            nodeDimensionsIncludeLabels: true,
            idealEdgeLength: Number(settings.idealEdgeLength) || 100,
            nodeRepulsion: Number(settings.nodeRepulsion) || 9000,
            gravity: Number(settings.gravity) || 0.35,
            numIter: Number(settings.numIter) || 2000,
            initialTemp: 200,
            coolingFactor: 0.95,
            minTemp: 1.0,
            randomize: true,
            componentSpacing: 80,
            nestingFactor: 1.2,
            edgeElasticity: Number(settings.edgeElasticity) || 0.40,
            nodeOverlap: 20,
        },
        'grid': {
            name: 'grid',
            animate: true,
            fit: true,
            padding: 30,
            spacingFactor: 1.5
        },
        'circle': {
            name: 'circle',
            animate: true,
            fit: true,
            padding: 30,
            spacingFactor: 1.2
        },
        'concentric': {
            name: 'concentric',
            animate: true,
            fit: true,
            padding: 30,
            concentric: function(node) {
                return (node.data('in_degree') || 0) + (node.data('out_degree') || 0);
            },
            levelWidth: function() { return 2; }
        }
    };

    return layouts[layoutName] || layouts['cose'];
}

/**
 * 绑定事件处理器
 */
function bindEvents() {
    if (!cy) return;

    // 节点点击：选中并显示详情
    cy.on('tap', 'node', function(evt) {
        const node = evt.target;
        selectNode(node);
    });

    // 节点双击：跳转到详情页
    cy.on('dblclick', 'node', function(evt) {
        const node = evt.target;
        const nodeData = node.data();
        if (alpineApp) {
            const atom = alpineApp.atoms.find(a => a.id === nodeData.id);
            if (atom) {
                alpineApp.selectAtom(atom);
                alpineApp.view = 'browse';
            }
        }
    });

    // 画布点击：取消选中
    cy.on('tap', function(evt) {
        if (evt.target === cy) {
            clearSelection();
        }
    });

    // 鼠标悬停：显示 tooltip
    cy.on('mouseover', 'node', function(evt) {
        const node = evt.target;
        showTooltip(node);
    });

    cy.on('mouseout', 'node', function(evt) {
        hideTooltip();
    });
}

/**
 * 选中节点并高亮邻居
 * @param {Object} node - Cytoscape 节点
 */
function selectNode(node) {
    // 清除之前的选中状态
    cy.elements().removeClass('selected highlighted faded');

    // 标记选中节点
    node.addClass('selected');

    // 获取邻居节点和边
    const neighborhood = node.neighborhood().add(node);

    // 高亮邻居
    neighborhood.nodes().addClass('highlighted');
    neighborhood.edges().addClass('highlighted');

    // 淡化其他节点
    cy.elements().not(neighborhood).addClass('faded');

    // 更新 Alpine.js 数据
    if (alpineApp) {
        alpineApp.graphSelectedNode = {
            id: node.data('id'),
            label: node.data('fullLabel') || node.data('label'),
            type: node.data('type'),
            description: node.data('description'),
            path: node.data('path'),
            in_degree: node.data('in_degree'),
            out_degree: node.data('out_degree'),
            tags: node.data('tags')
        };
    }
}

/**
 * 清除选中状态
 */
function clearSelection() {
    if (!cy) return;

    cy.elements().removeClass('selected highlighted faded');

    if (alpineApp) {
        alpineApp.graphSelectedNode = null;
    }
}

/**
 * 截断标签
 * @param {string} label - 原始标签
 * @param {number} maxLen - 最大长度
 * @returns {string} 截断后的标签
 */
function truncateLabel(label, maxLen) {
    if (!label) return '';
    if (label.length <= maxLen) return label;
    return label.substring(0, maxLen - 2) + '...';
}

// Tooltip 相关
let tooltipEl = null;

function showTooltip(node) {
    const label = node.data('fullLabel') || node.data('label');
    if (!label || label.length <= 15) return;

    if (!tooltipEl) {
        tooltipEl = document.createElement('div');
        tooltipEl.className = 'graph-tooltip';
        const bgOverlay = getThemeColor('--color-bg-overlay') || 'rgba(0,0,0,0.8)';
        const textInverse = getThemeColor('--color-text-inverse') || '#fff';
        tooltipEl.style.cssText = `position: absolute; background: ${bgOverlay}; color: ${textInverse}; padding: 4px 8px; border-radius: 4px; font-size: 12px; z-index: 1000; pointer-events: none;`;
        document.body.appendChild(tooltipEl);
    }

    tooltipEl.textContent = label;
    tooltipEl.style.display = 'block';

    const pos = node.renderedPosition();
    const container = document.getElementById('cy');
    const rect = container.getBoundingClientRect();

    tooltipEl.style.left = (rect.left + pos.x + 20) + 'px';
    tooltipEl.style.top = (rect.top + pos.y - 10) + 'px';
}

function hideTooltip() {
    if (tooltipEl) {
        tooltipEl.style.display = 'none';
    }
}

// ==================== 控制面板回调函数 ====================

/**
 * 应用筛选器
 * @param {Object} filters - 筛选条件 { types: [] }
 */
function applyGraphFilters(filters) {
    if (!cy) return;

    cy.elements().removeClass('hidden');

    // 按类型筛选
    if (filters.types && filters.types.length > 0) {
        cy.nodes().forEach(node => {
            const type = node.data('type');
            if (!filters.types.includes(type)) {
                node.addClass('hidden');
                node.connectedEdges().addClass('hidden');
            }
        });
    }

    // 更新布局
    runGraphLayout(alpineApp?.graphSettings?.layout);
}

/**
 * 切换孤立节点显示
 * @param {boolean} show - 是否显示
 */
function toggleOrphanNodesDisplay(show) {
    if (!cy) return;

    cy.nodes().forEach(node => {
        const inDeg = node.data('in_degree') || 0;
        const outDeg = node.data('out_degree') || 0;
        if (inDeg === 0 && outDeg === 0) {
            if (show) {
                node.removeClass('hidden');
            } else {
                node.addClass('hidden');
            }
        }
    });
}

/**
 * 运行布局算法
 * @param {string} layoutName - 布局名称
 */
function runGraphLayout(layoutName) {
    if (!cy) return;

    const layout = cy.layout(getLayoutOptions(layoutName, alpineApp?.graphSettings));
    layout.run();
}

/**
 * 使用设置运行布局
 * @param {Object} settings - 布局设置
 */
function runGraphLayoutWithSettings(settings) {
    if (!cy) return;

    const layout = cy.layout(getLayoutOptions(settings.layout || 'cose', settings));
    layout.run();
}

/**
 * 更新节点大小
 * @param {number} scale - 缩放比例
 */
function updateGraphNodeSize(scale) {
    nodeSizeScale = scale;
    if (!cy) return;

    cy.style(getStylesheet());
}

/**
 * 更新连线粗细
 * @param {number} scale - 缩放比例
 */
function updateGraphEdgeWidth(scale) {
    edgeWidthScale = scale;
    if (!cy) return;

    cy.style(getStylesheet());
}

/**
 * 更新连线颜色
 * @param {string} color - 颜色值
 */
function updateGraphEdgeColor(color) {
    edgeColorValue = color;
    if (!cy) return;

    cy.style(getStylesheet());
}

/**
 * 重置图谱视图
 */
function resetCytoscapeGraph() {
    if (!cy) return;

    // 清除所有状态
    cy.elements().removeClass('selected highlighted faded hidden search-match');

    // 重置大小比例
    nodeSizeScale = 1.0;
    edgeWidthScale = 1.0;
    // 重置连线颜色为主题 border 色
    edgeColorValue = getThemeColor('--color-border') || '#ccc';

    // 重新应用样式
    cy.style(getStylesheet());

    // 运行布局
    runGraphLayout('cose');

    // 适应画布
    cy.fit(null, 50);
}

/**
 * 搜索并聚焦节点
 * @param {string} query - 搜索关键词
 */
function searchAndFocusNode(query) {
    if (!cy || !query) {
        cy.nodes().removeClass('search-match');
        return;
    }

    const lowerQuery = query.toLowerCase();

    // 清除之前的搜索标记
    cy.nodes().removeClass('search-match');

    // 查找匹配节点
    const matched = cy.nodes().filter(node => {
        const label = (node.data('fullLabel') || node.data('label') || '').toLowerCase();
        const desc = (node.data('description') || '').toLowerCase();
        return label.includes(lowerQuery) || desc.includes(lowerQuery);
    });

    if (matched.length > 0) {
        matched.addClass('search-match');

        // 聚焦到第一个匹配节点
        const firstMatch = matched.first();
        cy.animate({
            center: { eles: firstMatch },
            zoom: 1.5,
            duration: 300
        });

        // 选中该节点
        selectNode(firstMatch);
    }
}

// 导出全局函数供 Alpine.js 调用
window.initCytoscapeGraph = initCytoscapeGraph;
window.applyGraphFilters = applyGraphFilters;
window.toggleOrphanNodesDisplay = toggleOrphanNodesDisplay;
window.runGraphLayout = runGraphLayout;
window.runGraphLayoutWithSettings = runGraphLayoutWithSettings;
window.updateGraphNodeSize = updateGraphNodeSize;
window.updateGraphEdgeWidth = updateGraphEdgeWidth;
window.updateGraphEdgeColor = updateGraphEdgeColor;
window.resetCytoscapeGraph = resetCytoscapeGraph;
window.searchAndFocusNode = searchAndFocusNode;
window.applyThemeToGraph = applyThemeToGraph;

/**
 * 备用布局初始化（使用 cose）
 */
function runCytoscapeWithFallback(app) {
    const container = document.getElementById('cy');
    const elements = convertToElements(app.graphData);

    const isMobile = window.innerWidth < 768;

    cy = cytoscape({
        container: container,
        elements: elements,
        style: getStylesheet(),
        layout: getLayoutOptions('cose', app.graphSettings),
        renderer: { name: 'canvas' },
        wheelSensitivity: 0.3,
        minZoom: 0.2,
        maxZoom: 3,
        touchTapThreshold: 8,
        desktopTapThreshold: 4,
        boxSelectionEnabled: !isMobile,
        zoomOnPinch: true,
        pinchToZoom: true,
        panningEnabled: true,
        motionBlur: !isMobile
    });

    bindEvents();
    console.log('使用备用 cose 布局');
}
