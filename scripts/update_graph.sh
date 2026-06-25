#!/bin/bash
# 更新知识图谱和原子列表
# 使用方法：./scripts/update_graph.sh

set -e

echo "🔄 开始更新知识图谱..."

# 激活虚拟环境
source .venv/bin/activate

# 生成图谱数据
echo "📊 生成图谱数据..."
python llm-wiki.py visualize knowledge-bases --output knowledge-bases/views/data/graph-data.json

# 生成原子列表
echo "📝 生成原子列表..."
python3 << 'PYTHON_EOF'
from pathlib import Path
import json
from datetime import datetime

atoms_dir = Path('knowledge-bases/atoms')
atoms = []

for atom_file in atoms_dir.glob('**/*.md'):
    content = atom_file.read_text(encoding='utf-8')

    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            yaml_part = parts[1]
            metadata = {}
            lines = yaml_part.strip().split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                if ':' in line and not line.startswith(' '):
                    key, value = line.split(':', 1)
                    if key.strip() == 'tags':
                        metadata['tags'] = []
                        i += 1
                        while i < len(lines) and lines[i].startswith('  - '):
                            metadata['tags'].append(lines[i].strip('- ').strip())
                            i += 1
                        continue
                    else:
                        metadata[key.strip()] = value.strip()
                i += 1

            atom_data = {
                'id': atom_file.stem,
                'path': str(atom_file.relative_to('knowledge-bases')),
                'title': metadata.get('title', atom_file.stem),
                'type': metadata.get('type', 'fact'),
                'description': metadata.get('description', ''),
                'tags': metadata.get('tags', []),
                'timestamp': metadata.get('timestamp', datetime.now().isoformat())
            }
            atoms.append(atom_data)

output_dir = Path('knowledge-bases/views/data')
with open(output_dir / 'atoms.json', 'w', encoding='utf-8') as f:
    json.dump(atoms, f, ensure_ascii=False, indent=2)

print(f"✅ 更新 atoms.json: {len(atoms)} 个原子")
PYTHON_EOF

# 统计结果
nodes=$(cat knowledge-bases/views/data/graph-data.json | jq '.nodes | length')
edges=$(cat knowledge-bases/views/data/graph-data.json | jq '.edges | length')
atoms_count=$(cat knowledge-bases/views/data/atoms.json | jq 'length')

echo ""
echo "✅ 更新完成！"
echo "   节点数: $nodes"
echo "   链接数: $edges"
echo "   原子数: $atoms_count"
echo ""
echo "💡 提示: 刷新浏览器页面查看更新（Ctrl+Shift+R 或 Cmd+Shift+R）"