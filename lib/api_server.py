"""HTTP API 服务，基于 Python 标准库 http.server 实现 REST API."""

import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from .querier import KnowledgeQuerier, AggregatedQuerier
from .ingestor import KnowledgeIngestor
from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser
from .auth.auth_middleware import require_auth, public_endpoint
from .utils.path_validator import PathValidator


def get_allowed_origins() -> List[str]:
    """
    从环境变量获取允许的 CORS 来源白名单.

    环境变量格式：
    - ALLOWED_ORIGINS=https://example.com,https://app.example.com
    - 为空时使用开发环境默认值

    Returns:
        允许的来源列表
    """
    origins_str = os.getenv('ALLOWED_ORIGINS', '').strip()
    if not origins_str:
        # 开发环境默认值
        return ['http://localhost:3000', 'http://localhost:8080', 'http://127.0.0.1:3000']

    origins = [origin.strip() for origin in origins_str.split(',') if origin.strip()]

    # 生产环境检查：不允许使用通配符
    if '*' in origins:
        print("⚠️  WARNING: Using wildcard '*' in ALLOWED_ORIGINS is not recommended for production!")
        if os.getenv('ENV', 'development') == 'production':
            raise ValueError("Wildcard '*' is not allowed in production environment. Set specific origins in ALLOWED_ORIGINS.")

    return origins


def validate_origin(origin: Optional[str], allowed_origins: List[str]) -> bool:
    """
    验证请求来源是否在白名单中.

    Args:
        origin: 请求的 Origin 标头
        allowed_origins: 允许的来源列表

    Returns:
        是否允许该来源
    """
    if not origin:
        return False

    # 完全匹配
    if origin in allowed_origins:
        return True

    # 支持通配符匹配（仅用于开发环境）
    if '*' in allowed_origins:
        return True

    return False


class APIServer:
    """HTTP API 服务器，提供 REST 接口."""

    def __init__(self, kb_dir: Path, host: str = '127.0.0.1', port: int = 8000):
        self.kb_dir = kb_dir
        self.host = host
        self.port = port
        self.allowed_origins = get_allowed_origins()

    def run(self) -> None:
        """启动 HTTP 服务器."""
        kb_dir = self.kb_dir
        allowed_origins = self.allowed_origins

        class Handler(APIRequestHandler):
            pass

        Handler.kb_dir = kb_dir
        # 初始化路径验证器，防止路径遍历攻击
        Handler.path_validator = PathValidator([str(kb_dir)])
        # 设置 CORS 白名单
        Handler.allowed_origins = allowed_origins
        server = HTTPServer((self.host, self.port), Handler)
        print(f"🚀 LLM Wiki API Server")
        print(f"   Knowledge base: {kb_dir}")
        print(f"   Listening: http://{self.host}:{self.port}")
        print(f"   CORS Origins: {', '.join(allowed_origins)}")
        print(f"   Endpoints:")
        print(f"     GET  /api/health        - 健康检查")
        print(f"     GET  /api/atoms         - 原子列表")
        print(f"     GET  /api/atoms/<id>    - 原子详情")
        print(f"     GET  /api/query?q=      - 查询知识")
        print(f"     POST /api/ingest        - 摄入资料")
        print(f"     GET  /api/stats         - 统计数据")
        print(f"     GET  /api/suggest?q=    - 搜索建议")
        print(f"     OPTIONS *              - CORS 预检请求")
        print(f"\n   按 Ctrl+C 停止\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 服务器已停止")
            server.server_close()


class APIRequestHandler(BaseHTTPRequestHandler):
    """API 请求处理器."""

    kb_dir: Path = Path('.')
    path_validator: Optional[PathValidator] = None
    allowed_origins: List[str] = ['http://localhost:3000']

    def _is_https_request(self) -> bool:
        """
        检查请求是否通过 HTTPS 到达.

        支持反向代理场景（X-Forwarded-Proto）和直连场景.

        Returns:
            是否为 HTTPS 请求
        """
        forwarded_proto = self.headers.get('X-Forwarded-Proto', '')
        if forwarded_proto:
            return forwarded_proto.lower() == 'https'
        return False

    def _enforce_https(self) -> bool:
        """
        生产环境强制 HTTPS.

        如果当前为 HTTP 请求，发送 301 重定向到 HTTPS 并返回 True.
        如果已经是 HTTPS，设置 HSTS 标头并返回 False.
        非生产环境直接返回 False.

        Returns:
            True 表示已发送重定向响应，调用方应立即返回
        """
        env = os.getenv('ENV', 'development')
        if env != 'production':
            return False

        if not self._is_https_request():
            host = self.headers.get(
                'Host',
                f'{self.server.server_address[0]}:{self.server.server_address[1]}'
            )
            https_url = f'https://{host}{self.path}'
            self.send_response(301)
            self.send_header('Location', https_url)
            self.send_header('Connection', 'close')
            self.end_headers()
            return True

        # 已是 HTTPS，设置 HSTS
        self.send_header(
            'Strict-Transport-Security',
            'max-age=31536000; includeSubDomains; preload'
        )
        return False

    def _set_security_headers(self) -> None:
        """设置安全响应标头."""
        # 防止 MIME 类型嗅探
        self.send_header('X-Content-Type-Options', 'nosniff')
        # 防止点击劫持
        self.send_header('X-Frame-Options', 'DENY')
        # 启用浏览器 XSS 过滤
        self.send_header('X-XSS-Protection', '1; mode=block')
        # 内容安全策略
        self.send_header(
            'Content-Security-Policy',
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        )
        # 防止引用来源泄露
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        # 权限策略（替代 Feature-Policy）
        self.send_header(
            'Permissions-Policy',
            'camera=(), microphone=(), geolocation=()'
        )

    def _set_cors_headers(self, origin: Optional[str]) -> None:
        """
        设置 CORS 响应标头.

        Args:
            origin: 请求的 Origin 标头
        """
        if validate_origin(origin, self.allowed_origins):
            # 来源在白名单中，允许访问
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Credentials', 'true')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type, X-API-Key')
            self.send_header('Access-Control-Max-Age', '3600')  # 预检请求缓存 1 小时
        else:
            # 来源不在白名单中，拒绝访问
            # 不设置 Access-Control-Allow-Origin，浏览器会阻止请求
            pass

    @public_endpoint
    def do_OPTIONS(self) -> None:
        """处理 OPTIONS 预检请求."""
        if self._enforce_https():
            return
        origin = self.headers.get('Origin')
        self.send_response(200)
        self._set_security_headers()
        self._set_cors_headers(origin)
        self.send_header('Content-Length', '0')
        self.end_headers()

    @public_endpoint
    def do_GET(self) -> None:
        """处理 GET 请求."""
        if self._enforce_https():
            return
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
        if self._enforce_https():
            return
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
        # 验证路径安全性，防止路径遍历攻击
        if self.path_validator is None:
            self._json_response({'error': 'Path validator not initialized'}, 500)
            return

        # 净化并验证 atom_id
        safe_path = self.path_validator.get_safe_path(atom_id)
        if safe_path is None:
            self._json_response({'error': 'Invalid or unsafe path'}, 400)
            return

        # 尝试添加 .md 扩展名
        atom_path = safe_path if safe_path.suffix == '.md' else safe_path.with_suffix('.md')

        if not atom_path.exists():
            # 尝试直接使用路径（可能是完整路径）
            if not safe_path.exists():
                self._json_response({'error': 'Atom not found'}, 404)
                return
            atom_path = safe_path

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
        origin = self.headers.get('Origin')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self._set_security_headers()
        self._set_cors_headers(origin)
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        """简化日志输出."""
        print(f"  {self.command} {self.path} - {args[1] if len(args) > 1 else ''}")
