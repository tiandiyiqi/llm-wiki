"""AI 引擎模块，支持多轮对话问答、内容去重检测、知识质检.

特性：
    - 多轮对话问答（基于检索 + 上下文记忆）
    - 内容去重检测（基于文本相似度）
    - 知识质检（过期/空白/低质量内容识别）
    - 可选 LLM 集成（无 LLM 时降级为纯检索模式）
"""

import json
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .yaml_parser import SimpleYAMLParser
from .constants import RESERVED_FILES


class QAEngine:
    """问答引擎，支持多轮对话和上下文记忆.

    设计原则：
        - 无 LLM API 时降级为纯检索模式
        - 上下文记忆最近 5 轮对话
        - 答案附带原文出处
    """

    MAX_HISTORY = 10  # 最多保留 10 轮对话

    def __init__(self, kb_dir: Path):
        """初始化问答引擎.

        Args:
            kb_dir: 知识库目录路径
        """
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()
        self.history_path = kb_dir / '.llm-wiki' / 'qa-history.json'
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def ask(self, question: str, session_id: str = 'default',
            llm_config: Optional[Dict] = None) -> Dict[str, Any]:
        """回答问题.

        Args:
            question: 用户问题
            session_id: 会话 ID（用于多轮对话）
            llm_config: LLM 配置（api_key, model, base_url），可选

        Returns:
            包含 answer、sources、history 的字典
        """
        # 1. 检索相关知识
        from .querier import KnowledgeQuerier
        querier = KnowledgeQuerier(self.kb_dir)
        results = querier.query(question, limit=5, semantic=True)

        # 2. 获取上下文（最近几轮对话）
        history = self._load_history(session_id)
        recent_turns = history[-self.MAX_HISTORY:] if history else []

        # 3. 生成回答
        if llm_config and llm_config.get('api_key'):
            answer = self._generate_with_llm(question, results, recent_turns, llm_config)
        else:
            answer = self._generate_from_retrieval(question, results, recent_turns)

        # 4. 记录对话历史
        self._append_history(session_id, question, answer, results)

        return {
            'answer': answer,
            'sources': [{'id': r.get('id', ''), 'title': r.get('title', ''),
                         'type': r.get('type', ''), 'score': r.get('score', 0)}
                        for r in results[:3]],
            'history': recent_turns + [{'q': question, 'a': answer}],
            'session_id': session_id,
            'mode': 'llm' if llm_config and llm_config.get('api_key') else 'retrieval',
        }

    def _generate_with_llm(self, question: str, results: List[Dict],
                           history: List[Dict], llm_config: Dict) -> str:
        """使用 LLM 生成回答（可选）.

        Args:
            question: 用户问题
            results: 检索结果
            history: 历史对话
            llm_config: LLM 配置

        Returns:
            LLM 生成的回答
        """
        try:
            # 尝试调用 OpenAI 兼容接口
            import urllib.request
            api_key = llm_config.get('api_key', '')
            base_url = llm_config.get('base_url', 'https://api.openai.com/v1')
            model = llm_config.get('model', 'gpt-3.5-turbo')

            # 构建上下文
            context_parts = []
            for i, r in enumerate(results[:3], 1):
                context_parts.append(
                    f"[{i}] {r.get('title', '')}\n{r.get('body', r.get('description', ''))[:500]}"
                )
            context = '\n\n'.join(context_parts)

            # 构建对话历史
            messages = [{'role': 'system', 'content':
                '你是一个知识库问答助手。基于以下知识库内容回答用户问题。'
                '回答末尾请引用参考来源编号。若知识库无相关内容，请如实告知。\n\n'
                f'知识库内容：\n{context}'}]
            for h in history[-3:]:
                messages.append({'role': 'user', 'content': h.get('q', '')})
                messages.append({'role': 'assistant', 'content': h.get('a', '')})
            messages.append({'role': 'user', 'content': question})

            payload = json.dumps({
                'model': model,
                'messages': messages,
                'temperature': 0.3,
                'max_tokens': 800,
            }).encode('utf-8')

            req = urllib.request.Request(
                f"{base_url.rstrip('/')}/chat/completions",
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}',
                },
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data.get('choices', [{}])[0].get('message', {}).get('content', '')
        except Exception as e:
            # LLM 调用失败，降级为检索模式
            return self._generate_from_retrieval(question, results, history) + \
                f"\n\n> ⚠️ LLM 调用失败，已降级为检索模式（错误：{str(e)[:100]}）"

    def _generate_from_retrieval(self, question: str, results: List[Dict],
                                 history: List[Dict]) -> str:
        """基于检索结果生成回答（无 LLM 时使用）.

        Args:
            question: 用户问题
            results: 检索结果
            history: 历史对话

        Returns:
            基于检索结果的回答
        """
        if not results:
            # 检查是否是追问
            if history:
                last_q = history[-1].get('q', '')
                return f"您刚才问的是「{last_q}」，我没有在知识库中找到关于「{question}」的更多内容。" \
                       f"建议尝试更具体的关键词，或换一种问法。"
            return f"抱歉，我在知识库中没有找到与「{question}」相关的内容。\n\n" \
                   "建议：\n" \
                   "1. 换用更具体的关键词\n" \
                   "2. 检查拼写\n" \
                   "3. 通过「上传」功能添加相关内容"

        # 构建回答
        answer_parts = [f"根据知识库检索，找到了 **{len(results)}** 条与「{question}」相关的内容：\n"]

        for i, r in enumerate(results[:5], 1):
            title = r.get('title', r.get('id', '未知'))
            atom_type = r.get('type', '')
            description = r.get('description', '')
            tags = r.get('tags', [])

            answer_parts.append(f"### {i}. {title}")
            if atom_type:
                answer_parts.append(f"**类型**：{atom_type}")
            if description:
                # 截取前 200 字
                desc = description[:200] + ('...' if len(description) > 200 else '')
                answer_parts.append(desc)
            if tags:
                answer_parts.append(f"**标签**：{', '.join(tags[:5])}")
            answer_parts.append("")

        # 上下文提示
        if history:
            last_q = history[-1].get('q', '')
            answer_parts.append(f"> 💡 结合您刚才的问题「{last_q}」，以上内容可能更贴合您的需求。")

        answer_parts.append("\n> 📚 点击下方参考来源可查看完整内容。如需更详细的解答，请配置 LLM API。")
        return '\n'.join(answer_parts)

    def _load_history(self, session_id: str) -> List[Dict]:
        """加载会话历史.

        Args:
            session_id: 会话 ID

        Returns:
            历史对话列表
        """
        try:
            if self.history_path.exists():
                data = json.loads(self.history_path.read_text(encoding='utf-8'))
                return data.get(session_id, [])
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return []

    def _append_history(self, session_id: str, question: str,
                        answer: str, results: List[Dict]) -> None:
        """追加对话历史.

        Args:
            session_id: 会话 ID
            question: 用户问题
            answer: 系统回答
            results: 检索结果
        """
        try:
            data = {}
            if self.history_path.exists():
                data = json.loads(self.history_path.read_text(encoding='utf-8'))
            history = data.setdefault(session_id, [])
            history.append({
                'q': question,
                'a': answer,
                'timestamp': datetime.now().isoformat(),
                'sources_count': len(results),
            })
            # 限制历史长度
            if len(history) > self.MAX_HISTORY * 2:
                data[session_id] = history[-self.MAX_HISTORY:]
            self.history_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass

    def clear_history(self, session_id: str = 'default') -> bool:
        """清空会话历史.

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        try:
            if self.history_path.exists():
                data = json.loads(self.history_path.read_text(encoding='utf-8'))
                if session_id in data:
                    del data[session_id]
                    self.history_path.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            return True
        except Exception:
            return False


class DuplicateDetector:
    """内容去重检测器，基于文本相似度识别重复内容."""

    def __init__(self, kb_dir: Path):
        """初始化去重检测器.

        Args:
            kb_dir: 知识库目录路径
        """
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()

    def find_duplicates(self, atom_id: Optional[str] = None,
                        threshold: float = 0.7) -> List[Dict]:
        """查找重复内容.

        Args:
            atom_id: 指定原子 ID（仅查找与该原子相似的内容），None 表示全局查找
            threshold: 相似度阈值（0-1）

        Returns:
            重复内容对列表，每项包含 atom1、atom2、similarity
        """
        atoms = self._load_all_atoms()
        if atom_id:
            # 仅查找与指定原子相似的内容
            target = next((a for a in atoms if a['id'] == atom_id), None)
            if not target:
                return []
            duplicates = []
            for a in atoms:
                if a['id'] == target['id']:
                    continue
                sim = self._compute_similarity(target, a)
                if sim >= threshold:
                    duplicates.append({
                        'atom1': target['id'],
                        'atom1_title': target['title'],
                        'atom2': a['id'],
                        'atom2_title': a['title'],
                        'similarity': round(sim, 3),
                    })
            return sorted(duplicates, key=lambda x: x['similarity'], reverse=True)

        # 全局查找
        duplicates = []
        for i, a1 in enumerate(atoms):
            for a2 in atoms[i + 1:]:
                sim = self._compute_similarity(a1, a2)
                if sim >= threshold:
                    duplicates.append({
                        'atom1': a1['id'],
                        'atom1_title': a1['title'],
                        'atom2': a2['id'],
                        'atom2_title': a2['title'],
                        'similarity': round(sim, 3),
                    })
        return sorted(duplicates, key=lambda x: x['similarity'], reverse=True)

    def merge_atoms(self, primary_id: str, secondary_id: str,
                    merge_strategy: str = 'append') -> Dict[str, Any]:
        """合并两个原子.

        Args:
            primary_id: 主原子 ID（保留）
            secondary_id: 副原子 ID（被合并）
            merge_strategy: 合并策略（append/replace/ignore）

        Returns:
            合并结果
        """
        primary_path = self._resolve_atom_path(primary_id)
        secondary_path = self._resolve_atom_path(secondary_id)
        if not primary_path or not primary_path.exists():
            return {'success': False, 'error': f'主原子不存在: {primary_id}'}
        if not secondary_path or not secondary_path.exists():
            return {'success': False, 'error': f'副原子不存在: {secondary_id}'}

        primary_content = primary_path.read_text(encoding='utf-8')
        secondary_content = secondary_path.read_text(encoding='utf-8')

        # 解析 frontmatter 和正文
        p_fm, p_body = self._split_content(primary_content)
        s_fm, s_body = self._split_content(secondary_content)

        # 合并正文
        if merge_strategy == 'append':
            merged_body = f"{p_body}\n\n---\n\n> 合并自: {secondary_id}\n\n{s_body}"
        elif merge_strategy == 'replace':
            merged_body = s_body
        else:  # ignore
            merged_body = p_body

        # 合并标签
        p_tags = p_fm.get('tags', []) if p_fm else []
        s_tags = s_fm.get('tags', []) if s_fm else []
        merged_tags = list(set(p_tags + s_tags))

        # 重建 frontmatter
        fm_str = self._build_frontmatter(p_fm or {}, merged_tags, primary_id)

        # 写入主原子
        new_content = f"{fm_str}\n\n{merged_body}\n"
        primary_path.write_text(new_content, encoding='utf-8')

        # 归档副原子（重命名为 .merged.md）
        archive_path = secondary_path.with_suffix('.merged.md')
        secondary_path.rename(archive_path)

        return {
            'success': True,
            'primary': primary_id,
            'secondary': secondary_id,
            'archived_to': str(archive_path.relative_to(self.kb_dir)),
            'message': f'已将 {secondary_id} 合并到 {primary_id}',
        }

    def _compute_similarity(self, atom1: Dict, atom2: Dict) -> float:
        """计算两个原子的相似度.

        Args:
            atom1: 原子1
            atom2: 原子2

        Returns:
            相似度（0-1）
        """
        # 1. 标题相似度（Jaccard）
        title1 = set(atom1.get('title', '').lower().split())
        title2 = set(atom2.get('title', '').lower().split())
        title_sim = self._jaccard(title1, title2)

        # 2. 内容哈希完全匹配
        if atom1.get('content_hash') and atom2.get('content_hash'):
            if atom1['content_hash'] == atom2['content_hash']:
                return 1.0

        # 3. 正文相似度（基于关键词重叠）
        body1 = set(atom1.get('body', '').lower().split())
        body2 = set(atom2.get('body', '').lower().split())
        body_sim = self._jaccard(body1, body2)

        # 4. 标签相似度
        tags1 = set(atom1.get('tags', []))
        tags2 = set(atom2.get('tags', []))
        tags_sim = self._jaccard(tags1, tags2)

        # 加权综合
        return 0.3 * title_sim + 0.5 * body_sim + 0.2 * tags_sim

    def _jaccard(self, set1: set, set2: set) -> float:
        """计算 Jaccard 相似度.

        Args:
            set1: 集合1
            set2: 集合2

        Returns:
            Jaccard 相似度（0-1）
        """
        if not set1 and not set2:
            return 0.0
        union = set1 | set2
        if not union:
            return 0.0
        intersection = set1 & set2
        return len(intersection) / len(union)

    def _load_all_atoms(self) -> List[Dict]:
        """加载所有原子.

        Returns:
            原子列表
        """
        atoms = []
        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                if not content.startswith('---'):
                    continue
                parts = content.split('---', 2)
                if len(parts) < 3:
                    continue
                fm = self.yaml_parser.parse(parts[1]) or {}
                body = parts[2]
                atoms.append({
                    'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
                    'path': str(md_file.relative_to(self.kb_dir)),
                    'title': fm.get('title', md_file.stem),
                    'type': fm.get('type', 'Unknown'),
                    'tags': fm.get('tags', []) or [],
                    'status': fm.get('status', 'draft'),
                    'body': body,
                    'content_hash': hashlib.md5(body.encode('utf-8')).hexdigest(),
                })
            except Exception:
                continue
        return atoms

    def _resolve_atom_path(self, atom_id: str) -> Optional[Path]:
        """解析原子 ID 为文件路径.

        Args:
            atom_id: 原子 ID

        Returns:
            原子文件路径，找不到返回 None
        """
        candidates = [
            self.kb_dir / f"{atom_id}.md",
            self.kb_dir / atom_id,
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c
        return None

    def _split_content(self, content: str) -> Tuple[Dict, str]:
        """分离 frontmatter 和正文.

        Args:
            content: 原始内容

        Returns:
            (frontmatter, body) 元组
        """
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                return self.yaml_parser.parse(parts[1]) or {}, parts[2]
        return {}, content

    def _build_frontmatter(self, fm: Dict, tags: List[str], atom_id: str) -> str:
        """构建 frontmatter 字符串.

        Args:
            fm: 原 frontmatter
            tags: 合并后的标签
            atom_id: 原子 ID

        Returns:
            frontmatter 字符串
        """
        fm['tags'] = tags
        fm['updated'] = datetime.now().strftime('%Y-%m-%d')
        fm['merged_at'] = datetime.now().isoformat()

        lines = ['---']
        for k, v in fm.items():
            if isinstance(v, list):
                lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
            elif isinstance(v, str):
                lines.append(f"{k}: \"{v}\"" if '"' in v else f"{k}: {v}")
            else:
                lines.append(f"{k}: {v}")
        lines.append('---')
        return '\n'.join(lines)


class QualityChecker:
    """知识质检器，识别过期/空白/低质量内容."""

    def __init__(self, kb_dir: Path):
        """初始化质检器.

        Args:
            kb_dir: 知识库目录路径
        """
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()

    def check_all(self) -> Dict[str, Any]:
        """执行全面质检.

        Returns:
            质检结果，包含问题列表和统计
        """
        atoms = self._load_all_atoms()
        issues = []

        for atom in atoms:
            # 1. 空白内容检测
            if not atom['body'].strip() or len(atom['body'].strip()) < 20:
                issues.append({
                    'atom_id': atom['id'],
                    'title': atom['title'],
                    'issue_type': 'empty',
                    'severity': 'high',
                    'message': '内容为空或过短（少于 20 字）',
                })

            # 2. 过期内容检测（created 超过 1 年且未更新）
            created = atom.get('created', '')
            updated = atom.get('updated', '')
            if created:
                try:
                    created_date = datetime.fromisoformat(created.split('T')[0])
                    days_since = (datetime.now() - created_date).days
                    if days_since > 365 and not updated:
                        issues.append({
                            'atom_id': atom['id'],
                            'title': atom['title'],
                            'issue_type': 'outdated',
                            'severity': 'medium',
                            'message': f'创建于 {created}，已 {days_since} 天未更新',
                        })
                except (ValueError, TypeError):
                    pass

            # 3. 低质量内容检测（无标签、无描述）
            if not atom.get('tags') and not atom.get('description'):
                issues.append({
                    'atom_id': atom['id'],
                    'title': atom['title'],
                    'issue_type': 'low_quality',
                    'severity': 'low',
                    'message': '缺少标签和描述，可发现性差',
                })

            # 4. 草稿状态长期未发布
            if atom.get('status') == 'draft':
                created = atom.get('created', '')
                if created:
                    try:
                        created_date = datetime.fromisoformat(created.split('T')[0])
                        days_since = (datetime.now() - created_date).days
                        if days_since > 30:
                            issues.append({
                                'atom_id': atom['id'],
                                'title': atom['title'],
                                'issue_type': 'stale_draft',
                                'severity': 'medium',
                                'message': f'草稿状态已 {days_since} 天，建议提交审核或归档',
                            })
                    except (ValueError, TypeError):
                        pass

        # 按严重程度统计
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        type_counts = {}
        for issue in issues:
            severity_counts[issue['severity']] = severity_counts.get(issue['severity'], 0) + 1
            type_counts[issue['issue_type']] = type_counts.get(issue['issue_type'], 0) + 1

        return {
            'total_atoms': len(atoms),
            'total_issues': len(issues),
            'issues': issues,
            'severity_counts': severity_counts,
            'type_counts': type_counts,
            'checked_at': datetime.now().isoformat(),
        }

    def _load_all_atoms(self) -> List[Dict]:
        """加载所有原子."""
        atoms = []
        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                if not content.startswith('---'):
                    continue
                parts = content.split('---', 2)
                if len(parts) < 3:
                    continue
                fm = self.yaml_parser.parse(parts[1]) or {}
                atoms.append({
                    'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
                    'title': fm.get('title', md_file.stem),
                    'type': fm.get('type', 'Unknown'),
                    'tags': fm.get('tags', []) or [],
                    'status': fm.get('status', 'draft'),
                    'created': fm.get('created', ''),
                    'updated': fm.get('updated', ''),
                    'description': fm.get('description', ''),
                    'body': parts[2],
                })
            except Exception:
                continue
        return atoms


class ShareLinkManager:
    """分享外链管理器，支持加密外链、有效期、访问次数限制."""

    def __init__(self, kb_dir: Path):
        """初始化分享外链管理器.

        Args:
            kb_dir: 知识库目录路径
        """
        self.kb_dir = kb_dir
        self.share_path = kb_dir / '.llm-wiki' / 'share-links.json'
        self.share_path.parent.mkdir(parents=True, exist_ok=True)
        self.yaml_parser = SimpleYAMLParser()

    def create_link(self, atom_id: str, expires_in_days: int = 7,
                    password: Optional[str] = None, max_views: int = 0) -> Dict[str, Any]:
        """创建分享外链.

        Args:
            atom_id: 原子 ID
            expires_in_days: 有效期（天），0 表示永久
            password: 访问密码（可选）
            max_views: 最大访问次数，0 表示不限

        Returns:
            分享链接信息
        """
        import secrets as _secrets
        token = _secrets.token_urlsafe(16)
        now = datetime.now()
        expires_at = None
        if expires_in_days > 0:
            from datetime import timedelta
            expires_at = (now + timedelta(days=expires_in_days)).isoformat()

        link_info = {
            'token': token,
            'atom_id': atom_id,
            'created_at': now.isoformat(),
            'expires_at': expires_at,
            'password': password,
            'max_views': max_views,
            'views': 0,
            'active': True,
        }

        data = self._load()
        data[token] = link_info
        self._save(data)
        return link_info

    def access_link(self, token: str, password: Optional[str] = None) -> Dict[str, Any]:
        """访问分享链接.

        Args:
            token: 分享 token
            password: 访问密码

        Returns:
            访问结果，包含原子内容或错误信息
        """
        data = self._load()
        link = data.get(token)
        if not link:
            return {'success': False, 'error': '链接不存在'}

        if not link.get('active', True):
            return {'success': False, 'error': '链接已被回收'}

        # 检查有效期
        expires_at = link.get('expires_at')
        if expires_at:
            try:
                exp_date = datetime.fromisoformat(expires_at)
                if datetime.now() > exp_date:
                    return {'success': False, 'error': '链接已过期'}
            except ValueError:
                pass

        # 检查访问次数
        max_views = link.get('max_views', 0)
        if max_views > 0 and link.get('views', 0) >= max_views:
            return {'success': False, 'error': '访问次数已用完'}

        # 检查密码
        if link.get('password'):
            if not password or password != link['password']:
                return {'success': False, 'error': '密码错误'}

        # 增加访问计数
        link['views'] = link.get('views', 0) + 1
        data[token] = link
        self._save(data)

        # 读取原子内容
        atom_id = link['atom_id']
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path or not atom_path.exists():
            return {'success': False, 'error': '原子内容不存在'}

        content = atom_path.read_text(encoding='utf-8')
        body = content
        fm = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                fm = self.yaml_parser.parse(parts[1]) or {}
                body = parts[2]

        return {
            'success': True,
            'atom_id': atom_id,
            'title': fm.get('title', atom_id),
            'type': fm.get('type', ''),
            'tags': fm.get('tags', []),
            'content': body,
            'views': link['views'],
            'expires_at': link.get('expires_at'),
        }

    def list_links(self) -> List[Dict]:
        """列出所有分享链接.

        Returns:
            分享链接列表
        """
        data = self._load()
        return list(data.values())

    def revoke_link(self, token: str) -> bool:
        """回收分享链接.

        Args:
            token: 分享 token

        Returns:
            是否成功
        """
        data = self._load()
        if token not in data:
            return False
        data[token]['active'] = False
        self._save(data)
        return True

    def delete_link(self, token: str) -> bool:
        """删除分享链接.

        Args:
            token: 分享 token

        Returns:
            是否成功
        """
        data = self._load()
        if token not in data:
            return False
        del data[token]
        self._save(data)
        return True

    def _resolve_atom_path(self, atom_id: str) -> Optional[Path]:
        """解析原子 ID 为文件路径."""
        candidates = [
            self.kb_dir / f"{atom_id}.md",
            self.kb_dir / atom_id,
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c
        return None

    def _load(self) -> Dict:
        """加载分享链接数据."""
        try:
            if self.share_path.exists():
                return json.loads(self.share_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return {}

    def _save(self, data: Dict) -> None:
        """保存分享链接数据."""
        self.share_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


class SensitiveInfoMasker:
    """敏感信息脱敏器，自动识别并脱敏手机号/身份证/邮箱等."""

    # 敏感信息正则模式
    PATTERNS = {
        'phone': re.compile(r'1[3-9]\d{9}'),
        'id_card': re.compile(r'\d{17}[\dXx]'),
        'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        'bank_card': re.compile(r'\d{16,19}'),
        'ip': re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
    }

    @classmethod
    def mask(cls, text: str) -> str:
        """脱敏文本中的敏感信息.

        Args:
            text: 原始文本

        Returns:
            脱敏后的文本
        """
        if not text:
            return text

        # 手机号：保留前 3 后 4
        text = cls.PATTERNS['phone'].sub(
            lambda m: m.group()[:3] + '****' + m.group()[-4:], text)

        # 身份证：保留前 4 后 4
        text = cls.PATTERNS['id_card'].sub(
            lambda m: m.group()[:4] + '**********' + m.group()[-4:], text)

        # 邮箱：保留首字符和域名
        def mask_email(m):
            email = m.group()
            at_idx = email.index('@')
            if at_idx <= 1:
                return '*' + email[at_idx:]
            return email[0] + '*' * (at_idx - 1) + email[at_idx:]
        text = cls.PATTERNS['email'].sub(mask_email, text)

        # 银行卡：保留前 4 后 4
        text = cls.PATTERNS['bank_card'].sub(
            lambda m: m.group()[:4] + '****' + m.group()[-4:] if len(m.group()) >= 16 else m.group(),
            text)

        return text

    @classmethod
    def detect(cls, text: str) -> List[Dict[str, Any]]:
        """检测文本中的敏感信息（不脱敏）.

        Args:
            text: 原始文本

        Returns:
            检测到的敏感信息列表
        """
        results = []
        for info_type, pattern in cls.PATTERNS.items():
            for match in pattern.finditer(text):
                results.append({
                    'type': info_type,
                    'value': match.group(),
                    'position': match.span(),
                })
        return results


class WebhookNotifier:
    """多渠道消息通知器，支持企业微信/钉钉/飞书 Webhook."""

    def __init__(self, kb_dir: Path):
        """初始化通知器.

        Args:
            kb_dir: 知识库目录路径
        """
        self.kb_dir = kb_dir
        self.config_path = kb_dir / '.llm-wiki' / 'webhooks.json'
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def add_webhook(self, name: str, platform: str, url: str,
                    events: List[str] = None, secret: str = '') -> Dict[str, Any]:
        """添加 Webhook 配置.

        Args:
            name: 配置名称
            platform: 平台（wechat/dingtalk/feishu/custom）
            url: Webhook URL
            events: 订阅事件列表
            secret: 签名密钥（可选）

        Returns:
            添加结果
        """
        import secrets as _secrets
        data = self._load()
        webhook_id = _secrets.token_hex(8)
        data[webhook_id] = {
            'id': webhook_id,
            'name': name,
            'platform': platform,
            'url': url,
            'events': events or ['all'],
            'secret': secret,
            'active': True,
            'created_at': datetime.now().isoformat(),
        }
        self._save(data)
        return {'success': True, 'id': webhook_id, 'webhook': data[webhook_id]}

    def list_webhooks(self) -> List[Dict]:
        """列出所有 Webhook 配置."""
        return list(self._load().values())

    def remove_webhook(self, webhook_id: str) -> bool:
        """删除 Webhook 配置."""
        data = self._load()
        if webhook_id not in data:
            return False
        del data[webhook_id]
        self._save(data)
        return True

    def notify(self, event: str, title: str, message: str,
               extra: Optional[Dict] = None) -> Dict[str, Any]:
        """发送通知到所有订阅了该事件的 Webhook.

        Args:
            event: 事件类型
            title: 通知标题
            message: 通知内容
            extra: 额外信息

        Returns:
            发送结果
        """
        data = self._load()
        results = []
        for webhook_id, webhook in data.items():
            if not webhook.get('active', True):
                continue
            events = webhook.get('events', ['all'])
            if 'all' not in events and event not in events:
                continue

            try:
                success = self._send_to_webhook(webhook, event, title, message, extra)
                results.append({
                    'webhook_id': webhook_id,
                    'name': webhook.get('name', ''),
                    'platform': webhook.get('platform', ''),
                    'success': success,
                })
            except Exception as e:
                results.append({
                    'webhook_id': webhook_id,
                    'name': webhook.get('name', ''),
                    'platform': webhook.get('platform', ''),
                    'success': False,
                    'error': str(e),
                })
        return {'event': event, 'sent_count': len(results), 'results': results}

    def _send_to_webhook(self, webhook: Dict, event: str, title: str,
                         message: str, extra: Optional[Dict]) -> bool:
        """发送消息到单个 Webhook.

        Args:
            webhook: Webhook 配置
            event: 事件类型
            title: 通知标题
            message: 通知内容
            extra: 额外信息

        Returns:
            是否发送成功
        """
        import urllib.request
        platform = webhook.get('platform', 'custom')
        url = webhook.get('url', '')
        if not url:
            return False

        # 根据平台构建不同的消息体
        if platform == 'wechat':
            # 企业微信
            payload = {
                'msgtype': 'markdown',
                'markdown': {
                    'content': f'**{title}**\n\n{message}\n\n事件: {event}'
                }
            }
        elif platform == 'dingtalk':
            # 钉钉
            payload = {
                'msgtype': 'markdown',
                'markdown': {
                    'title': title,
                    'text': f'## {title}\n\n{message}\n\n**事件**: {event}'
                }
            }
        elif platform == 'feishu':
            # 飞书
            payload = {
                'msg_type': 'text',
                'content': {
                    'text': f'{title}\n{message}\n事件: {event}'
                }
            }
        else:
            # 自定义
            payload = {
                'event': event,
                'title': title,
                'message': message,
                'extra': extra or {},
                'timestamp': datetime.now().isoformat(),
            }

        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200

    def _load(self) -> Dict:
        """加载 Webhook 配置."""
        try:
            if self.config_path.exists():
                return json.loads(self.config_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return {}

    def _save(self, data: Dict) -> None:
        """保存 Webhook 配置."""
        self.config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
