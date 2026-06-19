"""知识库注册表管理（支持全局和项目本地两级）"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .constants import KB_META_SCHEMA


class KBRegistry:
    """知识库注册表管理（支持全局和项目本地两级）"""

    GLOBAL_DIR = Path.home() / '.llm-wiki'
    GLOBAL_REGISTRY = GLOBAL_DIR / 'registry.json'
    GLOBAL_CONFIG = GLOBAL_DIR / 'config.json'

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir
        self.project_registry = project_dir / '.llm-wiki' / 'registry.json' if project_dir else None
        self.project_config = project_dir / '.llm-wiki' / 'config.json' if project_dir else None
        self._ensure_registries()

    def _ensure_registries(self) -> None:
        """确保注册表目录和文件存在"""
        # 全局注册表
        self.GLOBAL_DIR.mkdir(parents=True, exist_ok=True)

        if not self.GLOBAL_REGISTRY.exists():
            self._write_registry(self.GLOBAL_REGISTRY, {'version': '1.0', 'knowledge_bases': {}})

        if not self.GLOBAL_CONFIG.exists():
            self._write_config(self.GLOBAL_CONFIG, {'current_kb': None})

        # 项目级注册表（可选）
        if self.project_dir:
            project_llm_dir = self.project_dir / '.llm-wiki'
            project_llm_dir.mkdir(parents=True, exist_ok=True)

            if self.project_registry and not self.project_registry.exists():
                self._write_registry(self.project_registry, {'version': '1.0', 'knowledge_bases': {}})

            if self.project_config and not self.project_config.exists():
                self._write_config(self.project_config, {'current_kb': None})

    def _read_registry(self, path: Path) -> Dict:
        """读取注册表"""
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return {'version': '1.0', 'knowledge_bases': {}}

    def _write_registry(self, path: Path, data: Dict) -> None:
        """写入注册表"""
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    def _read_config(self, path: Path) -> Dict:
        """读取配置"""
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return {'current_kb': None}

    def _write_config(self, path: Path, data: Dict) -> None:
        """写入配置"""
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    def _get_registry_for_scope(self, scope: str) -> Tuple[Path, Dict]:
        """获取指定范围的注册表路径和数据"""
        if scope == 'project' and self.project_registry:
            return self.project_registry, self._read_registry(self.project_registry)
        elif scope == 'global':
            return self.GLOBAL_REGISTRY, self._read_registry(self.GLOBAL_REGISTRY)
        else:  # auto
            # 优先项目级
            if self.project_registry and self.project_registry.exists():
                data = self._read_registry(self.project_registry)
                if data.get('knowledge_bases'):
                    return self.project_registry, data
            return self.GLOBAL_REGISTRY, self._read_registry(self.GLOBAL_REGISTRY)

    def register(self, path: Path, name: str, description: str = "", tags: List[str] = None,
                 scope: str = 'auto', kb_type: str = 'standalone', parent: str = None,
                 validator: Any = None) -> bool:
        """注册知识库

        Args:
            path: 知识库路径
            name: 知识库名称/别名
            description: 描述
            tags: 标签列表
            scope: 注册范围 (auto/project/global)
            kb_type: 知识库类型 (standalone/parent/child)
            parent: 父知识库名称（仅当 kb_type=child 时使用）
            validator: OKFValidator 实例（可选，用于统计）
        """
        if not path.exists():
            print(f"❌ Path does not exist: {path}")
            return False

        registry_path, registry = self._get_registry_for_scope(scope)

        # 检查名称是否已存在
        if name in registry.get('knowledge_bases', {}):
            print(f"❌ Knowledge base '{name}' already registered")
            return False

        # 统计知识库信息（如果有 validator）
        concepts_count = 0
        types_count = {}
        if validator:
            validator.validate_bundle(path)
            concepts_count = len(validator.concepts)
            types_count = validator._count_types() if hasattr(validator, '_count_types') else {}

        # 添加注册信息
        kb_info = {
            'path': str(path.resolve()),
            'alias': name,
            'created': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'description': description,
            'tags': tags or [],
            'kb_type': kb_type,
            'parent': parent,
            'children': [],
            'children_paths': {},
            'statistics': {
                'concepts': concepts_count,
                'types': types_count
            }
        }

        registry.setdefault('knowledge_bases', {})[name] = kb_info
        self._write_registry(registry_path, registry)

        # 如果是子知识库，更新父知识库的 children 列表
        if kb_type == 'child' and parent:
            if not self.register_child(parent, name, path.name + '/'):
                print(f"⚠️ 警告: 无法注册子知识库关系到父知识库")
            # 更新父知识库的注册信息
            parent_kb = self.get(parent)
            if parent_kb:
                parent_info = registry['knowledge_bases'].get(parent)
                if parent_info and name not in parent_info.get('children', []):
                    parent_info.setdefault('children', []).append(name)
                if parent_info:
                    parent_info.setdefault('children_paths', {})[name] = path.name + '/'
                    parent_info['kb_type'] = 'parent'
                    self._write_registry(registry_path, registry)

        print(f"✅ Registered knowledge base: {name}")
        print(f"   Path: {path}")
        print(f"   Scope: {scope}")
        if kb_type != 'standalone':
            print(f"   Type: {kb_type}")
            if parent:
                print(f"   Parent: {parent}")
        return True

    def unregister(self, name: str, scope: str = 'all') -> bool:
        """注销知识库"""
        found = False

        if scope in ('all', 'project') and self.project_registry:
            registry = self._read_registry(self.project_registry)
            if name in registry.get('knowledge_bases', {}):
                del registry['knowledge_bases'][name]
                self._write_registry(self.project_registry, registry)
                found = True
                print(f"✅ Unregistered from project: {name}")

        if scope in ('all', 'global'):
            registry = self._read_registry(self.GLOBAL_REGISTRY)
            if name in registry.get('knowledge_bases', {}):
                del registry['knowledge_bases'][name]
                self._write_registry(self.GLOBAL_REGISTRY, registry)
                found = True
                print(f"✅ Unregistered from global: {name}")

        if not found:
            print(f"❌ Knowledge base not found: {name}")
            return False

        return True

    def list(self, scope: str = 'all') -> List[Dict]:
        """列出所有知识库"""
        kbs = []

        if scope in ('all', 'project') and self.project_registry:
            registry = self._read_registry(self.project_registry)
            for name, info in registry.get('knowledge_bases', {}).items():
                kbs.append({'name': name, 'scope': 'project', **info})

        if scope in ('all', 'global'):
            registry = self._read_registry(self.GLOBAL_REGISTRY)
            for name, info in registry.get('knowledge_bases', {}).items():
                # 避免重复（项目级优先）
                if not any(kb['name'] == name for kb in kbs):
                    kbs.append({'name': name, 'scope': 'global', **info})

        return kbs

    def get(self, name: str) -> Optional[Dict]:
        """获取知识库信息"""
        # 优先项目级
        if self.project_registry:
            registry = self._read_registry(self.project_registry)
            if name in registry.get('knowledge_bases', {}):
                return {'name': name, 'scope': 'project', **registry['knowledge_bases'][name]}

        # 全局
        registry = self._read_registry(self.GLOBAL_REGISTRY)
        if name in registry.get('knowledge_bases', {}):
            return {'name': name, 'scope': 'global', **registry['knowledge_bases'][name]}

        return None

    def set_current(self, name: str, scope: str = 'auto') -> bool:
        """设置当前知识库"""
        kb = self.get(name)
        if not kb:
            print(f"❌ Knowledge base not found: {name}")
            return False

        # 确定配置文件
        if scope == 'project' and self.project_config:
            config_path = self.project_config
        elif scope == 'global':
            config_path = self.GLOBAL_CONFIG
        else:  # auto
            config_path = self.project_config if self.project_config and kb['scope'] == 'project' else self.GLOBAL_CONFIG

        config = self._read_config(config_path)
        config['current_kb'] = name
        self._write_config(config_path, config)
        return True

    def get_current(self) -> Optional[str]:
        """获取当前知识库名称"""
        # 优先项目级
        if self.project_config:
            config = self._read_config(self.project_config)
            if config.get('current_kb'):
                return config['current_kb']

        # 全局
        config = self._read_config(self.GLOBAL_CONFIG)
        return config.get('current_kb')

    def resolve_path(self, name_or_path: str) -> Optional[Path]:
        """解析名称或路径为实际路径"""
        # 尝试作为名称解析
        kb = self.get(name_or_path)
        if kb:
            return Path(kb['path'])

        # 尝试作为路径
        path = Path(name_or_path)
        if path.exists():
            return path

        return None

    # ========== 父子知识库支持方法 ==========

    def _read_kb_meta(self, kb_path: Path) -> Dict[str, Any]:
        """读取知识库的 .kb-meta.json 文件"""
        meta_path = kb_path / '.kb-meta.json'
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text(encoding='utf-8'))
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        # 返回默认 schema
        return KB_META_SCHEMA.copy()

    def _write_kb_meta(self, kb_path: Path, meta: Dict[str, Any]) -> None:
        """写入知识库的 .kb-meta.json 文件"""
        meta_path = kb_path / '.kb-meta.json'
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')

    def get_children(self, name: str) -> List[str]:
        """获取知识库的所有子知识库名称"""
        kb = self.get(name)
        if not kb:
            return []
        kb_path = Path(kb['path'])
        meta = self._read_kb_meta(kb_path)
        return meta.get('children', [])

    def get_parent(self, name: str) -> Optional[str]:
        """获取知识库的父知识库名称"""
        kb = self.get(name)
        if not kb:
            return None
        kb_path = Path(kb['path'])
        meta = self._read_kb_meta(kb_path)
        return meta.get('parent')

    def get_kb_type(self, name: str) -> str:
        """获取知识库类型（standalone/parent/child）"""
        kb = self.get(name)
        if not kb:
            return 'standalone'
        kb_path = Path(kb['path'])
        meta = self._read_kb_meta(kb_path)
        return meta.get('kb_type', 'standalone')

    def register_child(self, parent_name: str, child_name: str, child_path: str) -> bool:
        """注册子知识库到父知识库"""
        parent_kb = self.get(parent_name)
        if not parent_kb:
            return False
        parent_path = Path(parent_kb['path'])
        meta = self._read_kb_meta(parent_path)

        if child_name not in meta.get('children', []):
            meta.setdefault('children', []).append(child_name)
        meta.setdefault('children_paths', {})[child_name] = child_path
        meta['kb_type'] = 'parent'

        self._write_kb_meta(parent_path, meta)
        return True