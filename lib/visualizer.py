"""Generates interactive knowledge graph HTML."""

import html
import json
from pathlib import Path
from typing import Dict, List, Optional

from .validator import OKFValidator


class KnowledgeVisualizer:
    """Generates interactive knowledge graph HTML."""

    # Color mapping for types
    TYPE_COLORS = {
        'method': '#3498db',
        'fact': '#2ecc71',
        'definition': '#9b59b6',
        'opinion': '#e74c3c',
        'data': '#f39c12',
        'question': '#1abc9c',
        'reference': '#34495e'
    }

    def __init__(self, kb_dir: Path, output_path: Path):
        self.kb_dir = kb_dir
        self.output_path = output_path
        self.validator = OKFValidator()
        self._concepts_loaded = False

    def _ensure_concepts_loaded(self):
        """Load concepts if not already loaded."""
        if not self._concepts_loaded:
            self.validator.validate_bundle(self.kb_dir)
            self._concepts_loaded = True

    def visualize(self, name: Optional[str] = None) -> bool:
        print(f"📊 Generating knowledge graph: {self.kb_dir}")
        print(f"   Output: {self.output_path}")

        # Validate and load concepts
        is_valid, errors, warnings = self.validator.validate_bundle(self.kb_dir)
        self._concepts_loaded = True

        if not self.validator.concepts:
            print("   No concepts found in knowledge base")
            return False

        print(f"   Concepts: {len(self.validator.concepts)}")

        # Generate HTML
        html_content = self._generate_html(name or self.kb_dir.name)

        # Write output
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(html_content, encoding='utf-8')

        print(f"\n✅ Visualization created: {self.output_path}")
        print(f"   Open in browser to view interactive graph")

        return True

    def generate_json_data(self) -> Dict:
        """Generate graph data as JSON-compatible dictionary.

        Returns:
            Dict with 'nodes' and 'edges' lists for graph visualization.
        """
        self._ensure_concepts_loaded()

        nodes: List[Dict] = []
        edges: List[Dict] = []

        for concept in self.validator.concepts:
            node_id = concept['id']
            node_type = concept['type']
            color = self.TYPE_COLORS.get(node_type, '#95a5a6')

            nodes.append({
                'id': node_id,
                'label': concept['title'][:50],  # Allow longer labels in JSON
                'type': node_type,
                'description': concept['description'],
                'path': concept['path'],
                'color': color
            })

            # Add edges from links
            for link in concept.get('links', []):
                # Normalize link to node id
                target_id = link.replace('.md', '').replace('/', '').replace('./', '')
                if target_id:
                    edges.append({
                        'id': f"{node_id}->{target_id}",
                        'source': node_id,
                        'target': target_id
                    })

        return {'nodes': nodes, 'edges': edges}

    def generate_interactive_html(self, output_path: Path) -> bool:
        """Generate interactive HTML with enhanced features.

        Features:
        - Force-directed layout with D3.js-style physics
        - Drag and drop nodes
        - Click to show details
        - Search filtering
        - Type filtering
        - Zoom and pan

        Args:
            output_path: Path to write the HTML file.

        Returns:
            True if successful, False otherwise.
        """
        self._ensure_concepts_loaded()

        if not self.validator.concepts:
            print("   No concepts found in knowledge base")
            return False

        json_data = self.generate_json_data()
        html_content = self._generate_enhanced_html(json_data)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding='utf-8')

        print(f"✅ Interactive HTML created: {output_path}")
        return True

    def _generate_html(self, name: str) -> str:
        """Generate single-file HTML visualization."""

        # Prepare nodes and edges for Cytoscape.js
        nodes = []
        edges = []

        # Color mapping for types
        type_colors = {
            'method': '#3498db',
            'fact': '#2ecc71',
            'definition': '#9b59b6',
            'opinion': '#e74c3c',
            'data': '#f39c12',
            'question': '#1abc9c',
            'reference': '#34495e'
        }

        for concept in self.validator.concepts:
            node_id = concept['id']
            node_type = concept['type']
            color = type_colors.get(node_type, '#95a5a6')

            nodes.append({
                'data': {
                    'id': node_id,
                    'label': concept['title'][:30],
                    'type': node_type,
                    'description': concept['description'],
                    'path': concept['path'],
                    'color': color
                }
            })

            # Add edges from links
            for link in concept.get('links', []):
                # Normalize link to node id
                target_id = link.replace('.md', '').replace('/', '').replace('./', '')
                if target_id:
                    edges.append({
                        'data': {
                            'id': f"{node_id}->{target_id}",
                            'source': node_id,
                            'target': target_id
                        }
                    })

        # Build nodes JSON
        nodes_json = json.dumps(nodes)
        edges_json = json.dumps(edges)
        escaped_name = html.escape(name)

        # Generate HTML template using string concatenation to avoid f-string issues
        html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>''' + escaped_name + ''' - Knowledge Graph</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            height: 100vh;
            display: flex;
        }
        #sidebar {
            width: 300px;
            background: #fff;
            border-right: 1px solid #ddd;
            display: flex;
            flex-direction: column;
        }
        #header {
            padding: 20px;
            border-bottom: 1px solid #ddd;
        }
        #header h1 { font-size: 18px; margin-bottom: 5px; }
        #header p { color: #666; font-size: 14px; }
        #search { padding: 10px 20px; border-bottom: 1px solid #ddd; }
        #search input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        #filters { padding: 10px 20px; border-bottom: 1px solid #ddd; }
        #filters label {
            display: inline-block;
            margin: 2px 4px;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
        }
        #stats { padding: 10px 20px; border-bottom: 1px solid #ddd; font-size: 12px; color: #666; }
        #detail {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        #detail h2 { margin-bottom: 10px; }
        #detail .meta { color: #666; font-size: 14px; margin-bottom: 10px; }
        #graph { flex: 1; background: #fff; }
        .type-method { background: #3498db; color: #fff; }
        .type-fact { background: #2ecc71; color: #fff; }
        .type-definition { background: #9b59b6; color: #fff; }
        .type-opinion { background: #e74c3c; color: #fff; }
        .type-data { background: #f39c12; color: #fff; }
        .type-question { background: #1abc9c; color: #fff; }
        .type-reference { background: #34495e; color: #fff; }
    </style>
</head>
<body>
    <div id="sidebar">
        <div id="header">
            <h1>''' + escaped_name + '''</h1>
            <p>Knowledge Graph Visualization</p>
        </div>
        <div id="search">
            <input type="text" placeholder="Search..." id="searchInput">
        </div>
        <div id="filters">
            <label class="type-method"><input type="checkbox" checked data-type="method"> method</label>
            <label class="type-fact"><input type="checkbox" checked data-type="fact"> fact</label>
            <label class="type-definition"><input type="checkbox" checked data-type="definition"> definition</label>
            <label class="type-opinion"><input type="checkbox" checked data-type="opinion"> opinion</label>
            <label class="type-data"><input type="checkbox" checked data-type="data"> data</label>
            <label class="type-question"><input type="checkbox" checked data-type="question"> question</label>
            <label class="type-reference"><input type="checkbox" checked data-type="reference"> reference</label>
        </div>
        <div id="stats">
            Concepts: ''' + str(len(nodes)) + ''' | Links: ''' + str(len(edges)) + '''
        </div>
        <div id="detail">
            <p style="color: #999;">Click a node to view details</p>
        </div>
    </div>
    <div id="graph"></div>
    <script>
        var nodes = ''' + nodes_json + ''';
        var edges = ''' + edges_json + ''';
        var cy = cytoscape({
            container: document.getElementById('graph'),
            elements: nodes.concat(edges),
            style: [
                {selector: 'node', style: {
                    'label': 'data(label)',
                    'background-color': 'data(color)',
                    'width': 60, 'height': 60,
                    'font-size': 10,
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'color': '#fff'
                }},
                {selector: 'edge', style: {
                    'width': 1,
                    'line-color': '#ccc',
                    'curve-style': 'bezier'
                }}
            ],
            layout: {name: 'cose', animate: true, animationDuration: 500}
        });
        cy.on('tap', 'node', function(evt) {
            var node = evt.target;
            var data = node.data();
            document.getElementById('detail').innerHTML =
                '<h2>' + data.label + '</h2>' +
                '<div class="meta"><span class="type-' + data.type + '">' + data.type + '</span> | ' + data.path + '</div>' +
                '<p>' + data.description + '</p>';
        });
        document.getElementById('searchInput').addEventListener('input', function(e) {
            var query = e.target.value.toLowerCase();
            cy.nodes().forEach(function(node) {
                var label = node.data('label').toLowerCase();
                node.style('display', (query && label.indexOf(query) === -1) ? 'none' : 'element');
            });
        });
        document.querySelectorAll('#filters input').forEach(function(input) {
            input.addEventListener('change', function() {
                var type = this.dataset.type;
                var checked = this.checked;
                cy.nodes().forEach(function(node) {
                    if (node.data('type') === type) {
                        node.style('display', checked ? 'element' : 'none');
                    }
                });
            });
        });
    </script>
</body>
</html>'''

        return html_content

    def _generate_enhanced_html(self, json_data: Dict) -> str:
        """Generate enhanced interactive HTML with full features.

        Args:
            json_data: Graph data with 'nodes' and 'edges'.

        Returns:
            Complete HTML string.
        """
        nodes_json = json.dumps(json_data['nodes'])
        edges_json = json.dumps(json_data['edges'])
        kb_name = html.escape(self.kb_dir.name)

        # Build HTML template
        html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>''' + kb_name + ''' - Interactive Knowledge Graph</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            height: 100vh;
            display: flex;
        }
        #sidebar {
            width: 320px;
            background: #fff;
            border-right: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
            box-shadow: 2px 0 8px rgba(0,0,0,0.05);
        }
        #header {
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
        }
        #header h1 { font-size: 20px; margin-bottom: 5px; font-weight: 600; }
        #header p { opacity: 0.9; font-size: 13px; }
        #controls {
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
        }
        #search {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        #search:focus {
            outline: none;
            border-color: #667eea;
        }
        #filters {
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
        }
        #filters h3 {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .filter-btn {
            display: inline-block;
            margin: 3px 4px 3px 0;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            transition: opacity 0.2s;
            border: none;
        }
        .filter-btn.inactive { opacity: 0.4; }
        .filter-method { background: #3498db; color: #fff; }
        .filter-fact { background: #2ecc71; color: #fff; }
        .filter-definition { background: #9b59b6; color: #fff; }
        .filter-opinion { background: #e74c3c; color: #fff; }
        .filter-data { background: #f39c12; color: #fff; }
        .filter-question { background: #1abc9c; color: #fff; }
        .filter-reference { background: #34495e; color: #fff; }
        #stats {
            padding: 12px 20px;
            background: #f8f9fa;
            font-size: 12px;
            color: #666;
            border-bottom: 1px solid #eee;
        }
        #detail {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        #detail h2 {
            font-size: 18px;
            margin-bottom: 8px;
            color: #333;
        }
        #detail .meta {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        #detail .type-badge {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            color: #fff;
        }
        #detail .path {
            color: #888;
            font-size: 12px;
        }
        #detail .description {
            color: #555;
            line-height: 1.6;
        }
        #detail .no-selection {
            color: #999;
            text-align: center;
            padding: 40px 20px;
        }
        #graph {
            flex: 1;
            background: #fff;
            position: relative;
        }
        #zoom-controls {
            position: absolute;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 5px;
        }
        .zoom-btn {
            width: 36px;
            height: 36px;
            border: 1px solid #ddd;
            background: #fff;
            border-radius: 6px;
            cursor: pointer;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }
        .zoom-btn:hover { background: #f5f5f5; }
    </style>
</head>
<body>
    <div id="sidebar">
        <div id="header">
            <h1>''' + kb_name + '''</h1>
            <p>Interactive Knowledge Graph</p>
        </div>
        <div id="controls">
            <input type="text" id="searchInput" placeholder="Search nodes..." autocomplete="off">
        </div>
        <div id="filters">
            <h3>Filter by Type</h3>
            <button class="filter-btn filter-method active" data-type="method">method</button>
            <button class="filter-btn filter-fact active" data-type="fact">fact</button>
            <button class="filter-btn filter-definition active" data-type="definition">definition</button>
            <button class="filter-btn filter-opinion active" data-type="opinion">opinion</button>
            <button class="filter-btn filter-data active" data-type="data">data</button>
            <button class="filter-btn filter-question active" data-type="question">question</button>
            <button class="filter-btn filter-reference active" data-type="reference">reference</button>
        </div>
        <div id="stats">
            Nodes: <span id="nodeCount">''' + str(len(json_data['nodes'])) + '''</span> |
            Edges: <span id="edgeCount">''' + str(len(json_data['edges'])) + '''</span> |
            Visible: <span id="visibleCount">''' + str(len(json_data['nodes'])) + '''</span>
        </div>
        <div id="detail">
            <div class="no-selection">
                <p>Click a node to view details</p>
                <p style="margin-top: 10px; font-size: 12px;">Drag nodes to reposition</p>
            </div>
        </div>
    </div>
    <div id="graph">
        <div id="zoom-controls">
            <button class="zoom-btn" id="zoomIn">+</button>
            <button class="zoom-btn" id="zoomOut">-</button>
            <button class="zoom-btn" id="resetZoom">R</button>
        </div>
    </div>
    <script>
        var graphData = {
            nodes: ''' + nodes_json + ''',
            edges: ''' + edges_json + '''
        };

        var cy = cytoscape({
            container: document.getElementById('graph'),
            elements: graphData.nodes.map(function(n) {
                return { data: n };
            }).concat(graphData.edges.map(function(e) {
                return { data: e };
            })),
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'background-color': 'data(color)',
                        'width': 70,
                        'height': 70,
                        'font-size': 11,
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'color': '#fff',
                        'text-wrap': 'wrap',
                        'text-max-width': 60,
                        'border-width': 2,
                        'border-color': '#fff',
                        'transition-property': 'width, height, border-width',
                        'transition-duration': 0.2
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-width': 4,
                        'border-color': '#667eea',
                        'width': 80,
                        'height': 80
                    }
                },
                {
                    selector: 'node:active',
                    style: {
                        'overlay-color': '#667eea',
                        'overlay-opacity': 0.3
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#ddd',
                        'curve-style': 'bezier',
                        'target-arrow-shape': 'triangle',
                        'target-arrow-color': '#ddd',
                        'arrow-scale': 0.8
                    }
                },
                {
                    selector: 'edge.highlighted',
                    style: {
                        'line-color': '#667eea',
                        'target-arrow-color': '#667eea',
                        'width': 3
                    }
                }
            ],
            layout: {
                name: 'cose',
                animate: true,
                animationDuration: 800,
                randomize: true,
                nodeRepulsion: function() { return 8000; },
                idealEdgeLength: 100,
                nodeOverlap: 20,
                fit: true,
                padding: 30
            },
            minZoom: 0.3,
            maxZoom: 3,
            wheelSensitivity: 0.3
        });

        // Node click handler
        cy.on('tap', 'node', function(evt) {
            var node = evt.target;
            var data = node.data();

            // Clear previous highlights
            cy.edges().removeClass('highlighted');
            cy.nodes().style('opacity', 1);

            // Highlight connected edges
            node.connectedEdges().addClass('highlighted');

            // Dim unconnected nodes
            cy.nodes().not(node).not(node.neighborhood('node')).style('opacity', 0.3);

            // Update detail panel
            document.getElementById('detail').innerHTML =
                '<h2>' + escapeHtml(data.label) + '</h2>' +
                '<div class="meta">' +
                '<span class="type-badge filter-' + data.type + '">' + data.type + '</span>' +
                '<span class="path">' + escapeHtml(data.path) + '</span>' +
                '</div>' +
                '<p class="description">' + escapeHtml(data.description || 'No description') + '</p>';
        });

        // Click on background to reset
        cy.on('tap', function(evt) {
            if (evt.target === cy) {
                cy.nodes().style('opacity', 1);
                cy.edges().removeClass('highlighted');
                document.getElementById('detail').innerHTML =
                    '<div class="no-selection">' +
                    '<p>Click a node to view details</p>' +
                    '<p style="margin-top: 10px; font-size: 12px;">Drag nodes to reposition</p>' +
                    '</div>';
            }
        });

        // Search functionality
        document.getElementById('searchInput').addEventListener('input', function(e) {
            var query = e.target.value.toLowerCase().trim();
            var visibleCount = 0;

            cy.nodes().forEach(function(node) {
                var label = (node.data('label') || '').toLowerCase();
                var desc = (node.data('description') || '').toLowerCase();
                var matches = query === '' || label.indexOf(query) !== -1 || desc.indexOf(query) !== -1;
                node.style('display', matches ? 'element' : 'none');
                if (matches) visibleCount++;
            });

            document.getElementById('visibleCount').textContent = visibleCount;
        });

        // Type filter buttons
        document.querySelectorAll('.filter-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var type = this.dataset.type;
                var isActive = this.classList.contains('active');

                if (isActive) {
                    this.classList.remove('active');
                    this.classList.add('inactive');
                } else {
                    this.classList.add('active');
                    this.classList.remove('inactive');
                }

                updateVisibility();
            });
        });

        function updateVisibility() {
            var activeTypes = {};
            document.querySelectorAll('.filter-btn.active').forEach(function(btn) {
                activeTypes[btn.dataset.type] = true;
            });

            var visibleCount = 0;
            cy.nodes().forEach(function(node) {
                var type = node.data('type');
                var visible = activeTypes[type];
                node.style('display', visible ? 'element' : 'none');
                if (visible) visibleCount++;
            });

            document.getElementById('visibleCount').textContent = visibleCount;
        }

        // Zoom controls
        document.getElementById('zoomIn').addEventListener('click', function() {
            cy.zoom(cy.zoom() * 1.2);
        });

        document.getElementById('zoomOut').addEventListener('click', function() {
            cy.zoom(cy.zoom() / 1.2);
        });

        document.getElementById('resetZoom').addEventListener('click', function() {
            cy.fit(null, 30);
        });

        // HTML escape utility
        function escapeHtml(text) {
            var div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Fit to view on load
        cy.ready(function() {
            cy.fit(null, 30);
        });
    </script>
</body>
</html>'''

        return html_content