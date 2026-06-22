"""文件系统存储适配器

将文件系统操作（registry.json + Markdown）适配到 StorageInterface 统一 API。
保留 file_mode 的 Skill 特性（Claude 直接操作文件）。
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any

from .storage_interface import StorageInterface


class FileSystemStorage(StorageInterface):
    """文件系统模式存储适配器

    将文件系统操作（registry.json + Markdown 文件）适配到统一 API。
    适用于 file_mode，保留 Skill 特性。
    """

    def __init__(self, kb_path: Path):
        """初始化文件系统存储

        Args:
            kb_path: 知识库根目录路径
        """
        self.kb_path = Path(kb_path)
        self.registry_path = self.kb_path / '.llm-wiki' / 'registry.json'
        self.atoms_dir = self.kb_path / 'atoms'
        self._registry: Dict = {'version': '1.0', 'knowledge_bases': {}}
        self._in_transaction = False

    @property
    def mode(self) -> str:
        return 'file'

    @property
    def supports_rls(self) -> bool:
        return False  # 文件模式不支持 RLS

    async def initialize(self) -> None:
        """初始化存储后端"""
        self.kb_path.mkdir(parents=True, exist_ok=True)
        (self.kb_path / '.llm-wiki').mkdir(parents=True, exist_ok=True)
        self.atoms_dir.mkdir(parents=True, exist_ok=True)
        await self._load_registry()

    async def close(self) -> None:
        """关闭存储连接"""
        if self._in_transaction:
            await self.rollback_transaction()

    async def _load_registry(self) -> None:
        """加载 registry.json"""
        if self.registry_path.exists():
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                self._registry = json.load(f)
        else:
            self._registry = {'version': '1.0', 'knowledge_bases': {}}
            await self._save_registry()

    async def _save_registry(self) -> None:
        """保存 registry.json"""
        if not self._in_transaction:
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(self._registry, f, ensure_ascii=False, indent=2)

    # ==================== 知识库操作 ====================

    async def create_kb(self, kb_data: Dict) -> int:
        """创建知识库"""
        kbs = self._registry['knowledge_bases']
        kb_id = max([int(k) for k in kbs.keys()] + [0]) + 1

        kb_info = {
            'id': kb_id,
            'name': kb_data.get('name', 'Untitled'),
            'description': kb_data.get('description', ''),
            'scope': kb_data.get('scope', 'personal'),
            'parent_id': kb_data.get('parent_id'),
            'created_at': kb_data.get('created_at', ''),
            'updated_at': kb_data.get('updated_at', ''),
        }

        kbs[str(kb_id)] = kb_info
        # 创建知识库目录
        (self.kb_path / str(kb_id)).mkdir(parents=True, exist_ok=True)
        (self.kb_path / str(kb_id) / 'atoms').mkdir(parents=True, exist_ok=True)

        await self._save_registry()
        return kb_id

    async def get_kb(self, kb_id: int) -> Optional[Dict]:
        """获取知识库"""
        return self._registry['knowledge_bases'].get(str(kb_id))

    async def list_kbs(self, user_id: Optional[str] = None, scope: Optional[str] = None) -> List[Dict]:
        """列出知识库"""
        kbs = list(self._registry['knowledge_bases'].values())

        if scope:
            kbs = [kb for kb in kbs if kb.get('scope') == scope]

        return kbs

    async def update_kb(self, kb_id: int, kb_data: Dict) -> bool:
        """更新知识库"""
        kb = self._registry['knowledge_bases'].get(str(kb_id))
        if not kb:
            return False

        kb.update(kb_data)
        await self._save_registry()
        return True

    async def delete_kb(self, kb_id: int) -> bool:
        """删除知识库"""
        kbs = self._registry['knowledge_bases']
        if str(kb_id) not in kbs:
            return False

        del kbs[str(kb_id)]
        # 删除知识库目录
        kb_dir = self.kb_path / str(kb_id)
        if kb_dir.exists():
            shutil.rmtree(kb_dir)

        await self._save_registry()
        return True

    # ==================== 知识原子操作 ====================

    async def create_atom(self, atom_data: Dict) -> int:
        """创建知识原子"""
        kb_id = atom_data.get('kb_id')
        if not kb_id:
            raise ValueError("kb_id is required")

        atoms = self._registry.get('atoms', {})
        if str(kb_id) not in atoms:
            atoms[str(kb_id)] = {}

        atom_id = max([int(a) for a in atoms[str(kb_id)].keys()] + [0]) + 1

        atom_info = {
            'id': atom_id,
            'title': atom_data.get('title', 'Untitled'),
            'content': atom_data.get('content', ''),
            'format': atom_data.get('format', 'markdown'),
            'tags': atom_data.get('tags', []),
            'links': atom_data.get('links', []),
            'created_at': atom_data.get('created_at', ''),
            'updated_at': atom_data.get('updated_at', ''),
        }

        atoms[str(kb_id)][str(atom_id)] = atom_info
        self._registry['atoms'] = atoms

        # 保存 Markdown 文件
        atom_path = self.kb_path / str(kb_id) / 'atoms' / f"{atom_id}.md"
        atom_path.write_text(atom_info['content'], encoding='utf-8')

        await self._save_registry()
        return atom_id

    async def get_atom(self, atom_id: int) -> Optional[Dict]:
        """获取知识原子"""
        atoms = self._registry.get('atoms', {})
        for kb_atoms in atoms.values():
            if str(atom_id) in kb_atoms:
                return kb_atoms[str(atom_id)]
        return None

    async def update_atom(self, atom_id: int, atom_data: Dict) -> bool:
        """更新知识原子"""
        atoms = self._registry.get('atoms', {})
        for kb_id, kb_atoms in atoms.items():
            if str(atom_id) in kb_atoms:
                kb_atoms[str(atom_id)].update(atom_data)
                # 更新 Markdown 文件
                atom_path = self.kb_path / kb_id / 'atoms' / f"{atom_id}.md"
                if atom_path.exists():
                    atom_path.write_text(kb_atoms[str(atom_id)]['content'], encoding='utf-8')
                await self._save_registry()
                return True
        return False

    async def delete_atom(self, atom_id: int) -> bool:
        """删除知识原子"""
        atoms = self._registry.get('atoms', {})
        for kb_id, kb_atoms in atoms.items():
            if str(atom_id) in kb_atoms:
                del kb_atoms[str(atom_id)]
                # 删除 Markdown 文件
                atom_path = self.kb_path / kb_id / 'atoms' / f"{atom_id}.md"
                if atom_path.exists():
                    atom_path.unlink()
                await self._save_registry()
                return True
        return False

    async def list_atoms(self, kb_id: int, **kwargs) -> List[Dict]:
        """列出知识库中的原子"""
        atoms = self._registry.get('atoms', {})
        return list(atoms.get(str(kb_id), {}).values())

    # ==================== 搜索操作 ====================

    async def search_atoms(self, query: str, **kwargs) -> List[Dict]:
        """搜索知识原子"""
        results = []
        atoms = self._registry.get('atoms', {})

        for kb_atoms in atoms.values():
            for atom in kb_atoms.values():
                if query.lower() in atom.get('title', '').lower() or query.lower() in atom.get('content', '').lower():
                    results.append(atom)

        return results

    # ==================== 事务支持 ====================

    async def begin_transaction(self) -> None:
        """开始事务"""
        self._in_transaction = True

    async def commit_transaction(self) -> None:
        """提交事务"""
        await self._save_registry()
        self._in_transaction = False

    async def rollback_transaction(self) -> None:
        """回滚事务"""
        await self._load_registry()
        self._in_transaction = False

    # ==================== 统计操作 ====================

    async def get_stats(self, kb_id: Optional[int] = None) -> Dict:
        """获取统计信息"""
        if kb_id:
            atoms = self._registry.get('atoms', {}).get(str(kb_id), {})
            return {
                'kb_id': kb_id,
                'atom_count': len(atoms),
            }

        total_atoms = sum(len(atoms) for atoms in self._registry.get('atoms', {}).values())
        return {
            'kb_count': len(self._registry['knowledge_bases']),
            'total_atoms': total_atoms,
        }