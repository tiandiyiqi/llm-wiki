"""文件系统存储适配器

将文件系统操作（registry.json + Markdown）适配到 StorageInterface 统一 API。
保留 file_mode 的 Skill 特性（Claude 直接操作文件）。
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from .storage_interface import StorageInterface, UnsupportedOperationError


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

    # ==================== 标签操作 ====================

    async def create_tag(self, kb_id: int, tag_data: Dict) -> int:
        """创建标签 — file_mode 不支持独立标签表"""
        raise UnsupportedOperationError('create_tag', self.mode)

    async def get_tag(self, tag_id: int) -> Optional[Dict]:
        """获取标签详情 — file_mode 不支持独立标签表"""
        raise UnsupportedOperationError('get_tag', self.mode)

    async def update_tag(self, tag_id: int, tag_data: Dict) -> bool:
        """更新标签 — file_mode 不支持独立标签表"""
        raise UnsupportedOperationError('update_tag', self.mode)

    async def delete_tag(self, tag_id: int) -> bool:
        """删除标签 — file_mode 不支持独立标签表"""
        raise UnsupportedOperationError('delete_tag', self.mode)

    async def add_atom_tag(self, atom_id: int, tag_id: int) -> bool:
        """为原子添加标签 — file_mode 更新原子 metadata.tags

        tag_id 在 file_mode 下作为标签名称字符串使用。
        """
        atom = await self.get_atom(atom_id)
        if not atom:
            return False

        current_tags = atom.get('tags', [])
        # tag_id 在 file_mode 下作为标签名称
        tag_name = str(tag_id)
        if tag_name in current_tags:
            return True  # 已存在，幂等返回

        # 不可变性：创建新列表
        new_tags = [*current_tags, tag_name]
        atoms = self._registry.get('atoms', {})
        for kb_id, kb_atoms in atoms.items():
            if str(atom_id) in kb_atoms:
                kb_atoms[str(atom_id)]['tags'] = new_tags
                await self._save_registry()
                return True
        return False

    async def remove_atom_tag(self, atom_id: int, tag_id: int) -> bool:
        """移除原子的标签 — file_mode 从 metadata.tags 移除

        tag_id 在 file_mode 下作为标签名称字符串使用。
        """
        atom = await self.get_atom(atom_id)
        if not atom:
            return False

        current_tags = atom.get('tags', [])
        # tag_id 在 file_mode 下作为标签名称
        tag_name = str(tag_id)
        if tag_name not in current_tags:
            return True  # 不存在，幂等返回

        # 不可变性：创建新列表，过滤掉目标标签
        new_tags = [t for t in current_tags if t != tag_name]
        atoms = self._registry.get('atoms', {})
        for kb_id, kb_atoms in atoms.items():
            if str(atom_id) in kb_atoms:
                kb_atoms[str(atom_id)]['tags'] = new_tags
                await self._save_registry()
                return True
        return False

    # ==================== 资产操作（file_mode 不支持）====================

    async def upload_asset(self, atom_id: int, asset_data: bytes,
                           filename: str, mime_type: str,
                           user_id: Optional[str] = None) -> Dict:
        """上传资产 — file_mode 不支持"""
        raise UnsupportedOperationError('upload_asset', self.mode)

    async def get_asset(self, asset_id: int) -> Optional[Dict]:
        """获取资产详情 — file_mode 不支持"""
        raise UnsupportedOperationError('get_asset', self.mode)

    async def list_assets(self, atom_id: int, variant_type: Optional[str] = None,
                          page: int = 1, limit: int = 20) -> Dict:
        """列出原子的资产 — file_mode 不支持"""
        raise UnsupportedOperationError('list_assets', self.mode)

    async def delete_asset(self, asset_id: int, user_id: Optional[str] = None) -> bool:
        """删除资产 — file_mode 不支持"""
        raise UnsupportedOperationError('delete_asset', self.mode)

    # ==================== 快照操作（file_mode 不支持）====================

    async def create_snapshot(self, kb_id: int, name: str,
                              description: str = '',
                              snapshot_type: str = 'manual',
                              user_id: Optional[str] = None) -> int:
        """创建快照 — file_mode 不支持"""
        raise UnsupportedOperationError('create_snapshot', self.mode)

    async def get_snapshot(self, snapshot_id: int) -> Optional[Dict]:
        """获取快照详情 — file_mode 不支持"""
        raise UnsupportedOperationError('get_snapshot', self.mode)

    async def list_snapshots(self, kb_id: int, limit: int = 20,
                             offset: int = 0) -> List[Dict]:
        """列出快照 — file_mode 不支持"""
        raise UnsupportedOperationError('list_snapshots', self.mode)

    async def restore_snapshot(self, snapshot_id: int,
                               user_id: Optional[str] = None) -> bool:
        """恢复快照 — file_mode 不支持"""
        raise UnsupportedOperationError('restore_snapshot', self.mode)

    async def delete_snapshot(self, snapshot_id: int) -> bool:
        """删除快照 — file_mode 不支持"""
        raise UnsupportedOperationError('delete_snapshot', self.mode)

    # ==================== OCR 操作（file_mode 不支持）====================

    async def submit_ocr_task(self, asset_id: int, image_data: bytes,
                              user_id: Optional[str] = None,
                              language: Optional[str] = None) -> Dict:
        """提交 OCR 任务 — file_mode 不支持"""
        raise UnsupportedOperationError('submit_ocr_task', self.mode)

    async def get_ocr_result(self, task_id: int) -> Optional[Dict]:
        """获取 OCR 结果 — file_mode 不支持"""
        raise UnsupportedOperationError('get_ocr_result', self.mode)

    async def get_ocr_results_by_asset(self, asset_id: int) -> List[Dict]:
        """获取资产的 OCR 结果 — file_mode 不支持"""
        raise UnsupportedOperationError('get_ocr_results_by_asset', self.mode)

    # ==================== 预览操作（file_mode 不支持）====================

    async def get_preview_url(self, atom_id: int, format: str = 'html',
                              source_mime_type: Optional[str] = None) -> Dict:
        """获取预览 URL — file_mode 不支持"""
        raise UnsupportedOperationError('get_preview_url', self.mode)

    async def get_preview_cache(self, atom_id: int,
                                format: str = 'html') -> Optional[Dict]:
        """获取预览缓存 — file_mode 不支持"""
        raise UnsupportedOperationError('get_preview_cache', self.mode)

    # ==================== 审计操作 ====================

    @property
    def _audit_path(self) -> Path:
        """审计日志文件路径"""
        return self.kb_path / '.llm-wiki' / 'audit' / 'audit.jsonl'

    def _ensure_audit_dir(self) -> None:
        """确保审计日志目录存在"""
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)

    async def log_audit(self, event_type: str, user_id: Optional[str] = None,
                        resource: Optional[str] = None,
                        action: Optional[str] = None,
                        details: Optional[Dict] = None) -> None:
        """记录审计事件 — file_mode 写入 JSONL 文件

        每行一个 JSON 对象，包含 timestamp, event_type, user_id,
        resource, action, details。
        """
        self._ensure_audit_dir()

        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'details': details,
        }

        with open(self._audit_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    async def query_audit(self, event_type: Optional[str] = None,
                          user_id: Optional[str] = None,
                          start_time: Optional[str] = None,
                          end_time: Optional[str] = None,
                          limit: int = 100) -> List[Dict]:
        """查询审计日志 — file_mode 读取 JSONL 文件

        支持按 event_type、user_id、时间范围过滤。
        """
        if not self._audit_path.exists():
            return []

        results: List[Dict] = []
        with open(self._audit_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # 按 event_type 过滤
                if event_type and entry.get('event_type') != event_type:
                    continue
                # 按 user_id 过滤
                if user_id and entry.get('user_id') != user_id:
                    continue
                # 按时间范围过滤
                entry_ts = entry.get('timestamp', '')
                if start_time and entry_ts < start_time:
                    continue
                if end_time and entry_ts > end_time:
                    continue

                results.append(entry)
                if len(results) >= limit:
                    break

        return results

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