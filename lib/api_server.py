"""HTTP API 服务，基于 Python 标准库 http.server 实现 REST API."""

import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .querier import KnowledgeQuerier, AggregatedQuerier
from .ingestor import KnowledgeIngestor
from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser
from .auth.auth_middleware import require_auth, public_endpoint


class APIServer:
    """HTTP API 服务器，提供 REST 接口."""

    def __init__(self, kb_dir: Path, host: str = '127.0.0.1', port: int = 8000):
        self.kb_dir = kb_dir
        self.host = host
        self.port = port

    def run(self) -> None:
        """启动 HTTP 服务器."""
        kb_dir = self.kb_dir

        class Handler(APIRequestHandler):
            pass

        Handler.kb_dir = kb_dir
        server = HTTPServer((self.host, self.port), Handler)
        print(f"🚀 LLM Wiki API Server")
        print(f"   Knowledge base: {kb_dir}")
        print(f"   Listening: http://{self.host}:{self.port}")
        print(f"   Endpoints:")
        print(f"     GET  /api/health        - 健康检查")
        print(f"     GET  /api/atoms         - 原子列表")
        print(f"     GET  /api/atoms/<id>    - 原子详情")
        print(f"     GET  /api/query?q=      - 查询知识")
        print(f"     POST /api/ingest        - 摄入资料")
        print(f"     GET  /api/stats         - 统计数据")
        print(f"     GET  /api/suggest?q=    - 搜索建议")
        print(f"\n   按 Ctrl+C 停止\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 服务器已停止")
            server.server_close()


class APIRequestHandler(BaseHTTPRequestHandler):
    """API 请求处理器."""

    kb_dir: Path = Path('.')

    @public_endpoint
    def do_GET(self) -> None:
        """处理 GET 请求."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        params = parse_qs(parsed.query)

        if path == '/api/health':
            self._json_response({'status': 'ok', 'kb': str(self.kb_dir)})
        elif path == '/api/atoms':
            self._handle_list_atoms(params)
        elif path.startswith('/api/atoms/'):
            atom_id = path.replace('/api/atoms/', '')
            self._handle_get_atom(atom_id)
        elif path == '/api/query':
            self._handle_query(params)
        elif path == '/api/stats':
            self._handle_stats()
        elif path == '/api/suggest':
            self._handle_suggest(params)
        else:
            self._json_response({'error': 'Not found'}, 404)

    @public_endpoint
    def do_POST(self) -> None:
        """处理 POST 请求."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == '/api/ingest':
            self._handle_ingest()
        elif path == '/api/embed':
            self._handle_embed()
        else:
            self._json_response({'error': 'Not found'}, 404)

    @require_auth
    def _handle_list_atoms(self, params: Dict) -> None:
        """列出原子."""
        atom_type = params.get('type', [None])[0]
        limit = int(params.get('limit', ['50'])[0])
        atoms = self._load_atoms(by_type=atom_type, limit=limit)
        self._json_response({'atoms': atoms, 'count': len(atoms)})

    @require_auth
    def _handle_get_atom(self, atom_id: str) -> None:
        """获取单个原子详情."""
        # atom_id 可能是路径（如 atoms/methods/xxx）
        atom_path = self.kb_dir / f"{atom_id}.md"
        if not atom_path.exists():
            # 尝试直接作为路径
            atom_path = self.kb_dir / atom_id
        if not atom_path.exists():
            self._json_response({'error': 'Atom not found'}, 404)
            return
        content = atom_path.read_text(encoding='utf-8')
        self._json_response({
            'id': atom_id,
            'path': str(atom_path.relative_to(self.kb_dir)),
            'content': content
        })

    @require_auth
    def _handle_query(self, params: Dict) -> None:
        """查询知识."""
        q = params.get('q', [''])[0]
        if not q:
            self._json_response({'error': 'Missing query parameter q'}, 400)
            return
        semantic = params.get('semantic', ['0'])[0] in ('1', 'true', 'yes')
        limit = int(params.get('limit', ['10'])[0])
        by_type = params.get('type', [None])[0]
        sort_by = params.get('sort', ['relevance'])[0]

        querier = KnowledgeQuerier(self.kb_dir)
        results = querier.query(q, limit=limit, by_type=by_type, semantic=semantic, sort_by=sort_by)
        # 移除 body 字段减少响应体积
        for r in results:
            r.pop('body', None)
            r.pop('frontmatter', None)
        self._json_response({'query': q, 'results': results, 'count': len(results)})

    @require_auth
    def _handle_suggest(self, params: Dict) -> None:
        """搜索建议."""
        prefix = params.get('q', [''])[0]
        querier = KnowledgeQuerier(self.kb_dir)
        suggestions = querier.get_suggestions(prefix)
        self._json_response({'suggestions': suggestions})

    @require_auth
    def _handle_stats(self) -> None:
        """统计数据."""
        try:
            from .analytics import AnalyticsEngine
            engine = AnalyticsEngine(self.kb_dir)
            stats = engine.get_stats()
            self._json_response(stats)
        except (ImportError, OSError) as e:
            self._json_response({'error': str(e)}, 500)

    @require_auth
    def _handle_ingest(self) -> None:
        """摄入资料."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length else ''
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json_response({'error': 'Invalid JSON'}, 400)
            return

        source_path = data.get('source')
        if not source_path:
            self._json_response({'error': 'Missing source path'}, 400)
            return

        ingestor = KnowledgeIngestor(self.kb_dir)
        success = ingestor.ingest(Path(source_path))
        if success:
            self._json_response({'status': 'ok', 'source': source_path})
        else:
            self._json_response({'error': 'Ingest failed'}, 500)

    @require_auth
    def _handle_embed(self) -> None:
        """触发向量化."""
        try:
            from .semantic import SemanticSearchEngine
            engine = SemanticSearchEngine(self.kb_dir)
            count = engine.embed_all()
            self._json_response({'status': 'ok', 'embedded': count})
        except (ImportError, RuntimeError, OSError) as e:
            self._json_response({'error': str(e)}, 500)

    def _load_atoms(self, by_type: Optional[str] = None, limit: int = 50) -> list:
        """加载原子列表."""
        yaml_parser = SimpleYAMLParser()
        atoms = []
        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue
            content = md_file.read_text(encoding='utf-8', errors='ignore')
            if not content.startswith('---'):
                continue
            parts = content.split('---', 2)
            if len(parts) < 3:
                continue
            fm = yaml_parser.parse(parts[1])
            if not fm:
                continue
            atom_type = fm.get('type', 'Unknown')
            if by_type and atom_type != by_type:
                continue
            atoms.append({
                'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
                'path': str(md_file.relative_to(self.kb_dir)),
                'type': atom_type,
                'title': fm.get('title', md_file.stem),
                'description': fm.get('description', ''),
                'tags': fm.get('tags', []),
                'status': fm.get('status', 'published'),
            })
            if len(atoms) >= limit:
                break
        return atoms

    def _json_response(self, data: Any, status: int = 200) -> None:
        """发送 JSON 响应."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        """简化日志输出."""
        print(f"  {self.command} {self.path} - {args[1] if len(args) > 1 else ''}")
