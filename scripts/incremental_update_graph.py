#!/usr/bin/env python3
"""增量更新图谱数据 - 只处理新增/修改的原子"""

import json
import sys
from pathlib import Path
from datetime import datetime

def get_mtime_state(state_path: Path) -> dict:
    """获取文件的修改时间状态"""
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text())
    except:
        return {}

def save_mtime_state(state_path: Path, state: dict):
    """保存文件修改时间状态"""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2))

def extract_links(content: str) -> list:
    """提取 [[链接]]"""
    import re
    return re.findall(r'\[\[([^\]]+)\]\]', content)

def parse_atom(atom_path: Path) -> dict:
    """解析原子文件"""
    content = atom_path.read_text(encoding='utf-8')
    if not content.startswith('---'):
        return None

    parts = content.split('---', 2)
    if len(parts) < 3:
        return None

    # 解析 YAML
    metadata = {}
    lines = parts[1].strip().split('\n')
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

    # 提取链接
    links = extract_links(parts[2])

    return {
        'id': atom_path.stem,
        'title': metadata.get('title', atom_path.stem),
        'type': metadata.get('type', 'fact'),
        'description': metadata.get('description', ''),
        'tags': metadata.get('tags', []),
        'timestamp': metadata.get('timestamp', datetime.now().isoformat()),
        'links': links
    }

def incremental_update(kb_dir: Path):
    """增量更新图谱"""
    atoms_dir = kb_dir / 'atoms'
    output_dir = kb_dir / 'views' / 'data'
    state_path = kb_dir / '.llm-wiki' / 'graph-mtime.json'

    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载当前图谱数据
    graph_path = output_dir / 'graph-data.json'
    atoms_path = output_dir / 'atoms.json'

    graph_data = {'nodes': [], 'edges': []}
    atoms_list = []

    if graph_path.exists():
        graph_data = json.loads(graph_path.read_text())
    if atoms_path.exists():
        atoms_list = json.loads(atoms_path.read_text())

    # 加载文件修改时间状态
    mtime_state = get_mtime_state(state_path)

    # 扫描原子文件
    current_files = {}
    new_atoms = []
    modified_atoms = []
    deleted_ids = set(n['id'] for n in graph_data['nodes'])

    for atom_file in atoms_dir.glob('**/*.md'):
        file_mtime = atom_file.stat().st_mtime
        file_id = atom_file.stem
        file_key = str(atom_file.relative_to(kb_dir))

        current_files[file_key] = file_mtime

        # 检查是否新增或修改
        old_mtime = mtime_state.get(file_key)
        if old_mtime is None or old_mtime < file_mtime:
            atom_data = parse_atom(atom_file)
            if atom_data:
                if old_mtime is None:
                    new_atoms.append(atom_data)
                    print(f"  + 新增: {atom_data['title']}")
                else:
                    modified_atoms.append(atom_data)
                    print(f"  * 修改: {atom_data['title']}")

        deleted_ids.discard(file_id)

    # 处理删除的节点
    if deleted_ids:
        print(f"  - 删除: {len(deleted_ids)} 个节点")
        graph_data['nodes'] = [n for n in graph_data['nodes'] if n['id'] not in deleted_ids]
        graph_data['edges'] = [e for e in graph_data['edges']
                              if e['source'] not in deleted_ids and e['target'] not in deleted_ids]
        atoms_list = [a for a in atoms_list if a['id'] not in deleted_ids]

    # 添加新节点
    for atom in new_atoms:
        # 节点数据
        node = {
            'id': f"atoms/{atom['id']}",
            'label': atom['title'][:30],
            'type': atom['type'],
            'description': atom['description'][:200],
            'path': str(atom_file.relative_to(kb_dir)),
            'color': {
                'method': '#3b82f6',
                'fact': '#10b981',
                'definition': '#8b5cf6',
                'opinion': '#ef4444',
                'data': '#f59e0b',
                'question': '#14b8a6',
                'reference': '#64748b'
            }.get(atom['type'], '#64748b'),
            'tags': atom['tags'],
            'in_degree': 0,
            'out_degree': len(atom['links'])
        }
        graph_data['nodes'].append(node)

        # atoms 列表
        atoms_list.append({
            'id': atom['id'],
            'title': atom['title'],
            'type': atom['type'],
            'description': atom['description'],
            'tags': atom['tags'],
            'timestamp': atom['timestamp']
        })

    # 更新边（新增和修改的原子）
    all_atoms_map = {a['id']: a for a in atoms_list}
    for atom in new_atoms + modified_atoms:
        atom_id = f"atoms/{atom['id']}"

        # 移除旧的边
        graph_data['edges'] = [e for e in graph_data['edges'] if e['source'] != atom_id]

        # 添加新的边
        for link in atom['links']:
            # 查找目标原子
            target_id = None
            for a_id, a_data in all_atoms_map.items():
                if a_data['title'] == link or a_id == link:
                    target_id = f"atoms/{a_id}"
                    break

            if target_id and target_id in set(n['id'] for n in graph_data['nodes']):
                graph_data['edges'].append({
                    'id': f"{atom_id}->{target_id}",
                    'source': atom_id,
                    'target': target_id
                })

    # 更新度数统计
    for node in graph_data['nodes']:
        node['in_degree'] = sum(1 for e in graph_data['edges'] if e['target'] == node['id'])
        node['out_degree'] = sum(1 for e in graph_data['edges'] if e['source'] == node['id'])

    # 保存更新后的数据
    graph_path.write_text(json.dumps(graph_data, ensure_ascii=False, indent=2))
    atoms_path.write_text(json.dumps(atoms_list, ensure_ascii=False, indent=2))
    save_mtime_state(state_path, current_files)

    print(f"\n✅ 增量更新完成:")
    print(f"   新增: {len(new_atoms)} 个")
    print(f"   修改: {len(modified_atoms)} 个")
    print(f"   删除: {len(deleted_ids)} 个")
    print(f"   总节点: {len(graph_data['nodes'])}")
    print(f"   总边数: {len(graph_data['edges'])}")

if __name__ == '__main__':
    kb_dir = Path('knowledge-bases')
    incremental_update(kb_dir)