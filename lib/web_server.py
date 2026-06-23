"""统一 Web 服务，同时提供静态前端文件和 REST API.

架构：
    ThreadingHTTPServer（多线程并发）
        ↓
    UnifiedRequestHandler
        ├── /api/*  → API 路由分发（含认证中间件）
        └── 其他    → 静态文件服务（views/ 目录）

特性：
    - 多线程并发（ThreadingHTTPServer）
    - 统一服务入口（前端 + API）
    - Token/Session 认证中间件
    - 35+ REST API 端点
    - 静态文件服务（HTML/JS/CSS/图片）
    - CORS 支持
    - 双模式存储（file_mode / db_mode）通过 StorageInterface 切换
"""

import json
import logging
import os
import re
import time
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse, unquote

from .querier import KnowledgeQuerier
from .ingestor import KnowledgeIngestor
from .constants import RESERVED_FILES
from .yaml_parser import SimpleYAMLParser
from .core.storage_interface import StorageInterface

logger = logging.getLogger(__name__)


def _run_async(coro):
    """在同步上下文中安全运行异步协程

    在 ThreadingHTTPServer 的多线程环境中使用。
    每次调用创建新的事件循环（线程安全但非高性能）。

    Args:
        coro: 异步协程对象

    Returns:
        协程的返回值
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 已在异步上下文中（不应出现在 ThreadingHTTPServer）
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


# 不需要认证的公开端点
PUBLIC_ENDPOINTS = {
    '/api/health',
    '/api/auth/login',
    '/api/auth/sso/providers',
    '/api/auth/sso/callback',
}

# 通过正则匹配的公开端点（用于带路径参数的公开端点）
PUBLIC_ENDPOINT_PATTERNS = [
    re.compile(r'^GET:/api/share/.+/access$'),  # 分享外链访问
]

# 只读端点（reader 权限即可）
READONLY_ACTIONS = {
    'GET:/api/atoms',
    'GET:/api/atoms/',
    'GET:/api/query',
    'GET:/api/stats',
    'GET:/api/suggest',
    'GET:/api/search',
    'GET:/api/search/suggest',
    'GET:/api/health',
    'GET:/api/auth/whoami',
    'GET:/api/audit',
    'GET:/api/analytics',
}


class UnifiedWebServer:
    """统一 Web 服务器，提供前端静态文件和 REST API.

    支持双模式存储：
    - file_mode: 文件系统存储（默认，保留 Skill 特性）
    - db_mode: PostgreSQL 数据库存储（企业模式）

    通过 StorageInterface 实现透明切换。
    """

    def __init__(self, kb_dir: Path, host: str = '127.0.0.1', port: int = 8000,
                 storage: Optional[StorageInterface] = None):
        """初始化统一 Web 服务器.

        Args:
            kb_dir: 知识库目录路径
            host: 监听地址
            port: 监听端口
            storage: 存储接口实例（可选，默认自动创建 FileSystemStorage）
        """
        self.kb_dir = kb_dir
        self.host = host
        self.port = port
        # 存储接口：支持双模式切换
        self._storage = storage
        # 静态文件目录：知识库 views/ 和项目根 views/ 都可用
        self.kb_views_dir = kb_dir / 'views'
        self.project_views_dir = Path(__file__).parent.parent / 'views'
        # 主静态文件目录（优先项目根，确保有 index.html 等模板）
        self.static_dir = self.project_views_dir

    @property
    def storage(self) -> StorageInterface:
        """获取存储接口（懒初始化）"""
        if self._storage is None:
            from .core.file_storage import FileSystemStorage
            self._storage = FileSystemStorage(kb_dir=self.kb_dir)
        return self._storage

    @property
    def storage_mode(self) -> str:
        """获取当前存储模式（'file' 或 'db'）"""
        return self.storage.mode

    def run(self) -> None:
        """启动统一 Web 服务器."""
        handler_cls = self._create_handler()
        server = ThreadingHTTPServer((self.host, self.port), handler_cls)
        # 解决端口占用后无法立即重用的问题
        server.daemon_threads = True

        print(f"\n{'='*60}")
        print(f"🚀 LLM Wiki 统一 Web 服务")
        print(f"{'='*60}")
        print(f"   知识库: {self.kb_dir}")
        print(f"   存储模式: {self.storage_mode}")
        print(f"   静态文件: {self.static_dir}")
        print(f"   访问地址: http://{self.host}:{self.port}")
        print(f"\n📡 API 端点（35+）:")
        print(f"   认证:  POST /api/auth/login, POST /api/auth/logout, GET /api/auth/whoami")
        print(f"   用户:  GET/POST /api/users, DELETE /api/users/{{name}}, PUT /api/users/{{name}}/role")
        print(f"   Token: POST /api/tokens, GET /api/tokens, DELETE /api/tokens/{{token}}")
        print(f"   原子:  GET /api/atoms, GET /api/atoms/{{id}}, POST /api/atoms")
        print(f"   反馈:  POST /api/atoms/{{id}}/comments, /favorite, /rate")
        print(f"   审批:  POST /api/atoms/{{id}}/submit, /approve, /reject")
        print(f"   生命周期: POST /api/atoms/{{id}}/publish, /archive, /deprecate")
        print(f"   审计:  GET /api/audit")
        print(f"   统计:  GET /api/stats, GET /api/analytics/behavior")
        print(f"   备份:  POST /api/backup, POST /api/restore")
        print(f"   批量:  POST /api/batch/tag, /move, /delete")
        print(f"   摄入:  POST /api/ingest, POST /api/ingest/upload")
        print(f"   搜索:  GET /api/search, GET /api/search/suggest")
        print(f"   通知:  GET /api/notifications")
        print(f"\n🌐 前端页面:")
        print(f"   首页: http://{self.host}:{self.port}/")
        print(f"   登录: http://{self.host}:{self.port}/login.html")
        print(f"\n   按 Ctrl+C 停止\n")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 服务器已停止")
            server.server_close()

    def _create_handler(self):
        """创建请求处理器类."""
        kb_dir = self.kb_dir
        static_dir = self.static_dir
        kb_views_dir = self.kb_views_dir
        storage = self.storage

        class Handler(UnifiedRequestHandler):
            pass

        Handler.kb_dir = kb_dir
        Handler.static_dir = static_dir
        Handler.kb_views_dir = kb_views_dir
        Handler.storage = storage
        return Handler


class UnifiedRequestHandler(BaseHTTPRequestHandler):
    """统一请求处理器，处理 API 和静态文件."""

    kb_dir: Path = Path('.')
    static_dir: Path = Path('.')
    kb_views_dir: Path = Path('.')
    # StorageInterface 实例（支持双模式切换）
    storage: StorageInterface = None  # 由 _create_handler 设置
    # 线程锁，保护写操作
    _write_lock = threading.Lock()

    # ========================================================================
    # 请求入口
    # ========================================================================

    def do_GET(self) -> None:
        """处理 GET 请求."""
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path.startswith('/api/'):
            self._route_api('GET', path, parsed.query)
        else:
            self._serve_static(path)

    def do_POST(self) -> None:
        """处理 POST 请求."""
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith('/api/'):
            self._route_api('POST', path, parsed.query)
        else:
            self._json_response({'error': 'Not found'}, 404)

    def do_PUT(self) -> None:
        """处理 PUT 请求."""
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith('/api/'):
            self._route_api('PUT', path, parsed.query)
        else:
            self._json_response({'error': 'Not found'}, 404)

    def do_DELETE(self) -> None:
        """处理 DELETE 请求."""
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith('/api/'):
            self._route_api('DELETE', path, parsed.query)
        else:
            self._json_response({'error': 'Not found'}, 404)

    def do_OPTIONS(self) -> None:
        """处理 CORS 预检请求."""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    # ========================================================================
    # API 路由分发
    # ========================================================================

    def _route_api(self, method: str, path: str, query: str) -> None:
        """API 路由分发.

        Args:
            method: HTTP 方法（GET/POST/PUT/DELETE）
            path: 请求路径
            query: 查询字符串
        """
        # 认证中间件
        if not self._authenticate(path):
            self._json_response({'error': '未登录或认证失效', 'need_login': True}, 401)
            return

        # 如果是 db_mode 且有 storage，设置 RLS 用户上下文
        if hasattr(self, 'storage') and self.storage and hasattr(self.storage, 'set_current_user'):
            current_user = getattr(self, '_current_user', None)
            if current_user and current_user.get('username', 'anonymous') != 'anonymous':
                try:
                    _run_async(self.storage.set_current_user(
                        current_user['username'],
                        [current_user.get('role', 'user')]
                    ))
                except Exception:
                    pass

        # 权限检查（公开端点跳过）
        route_key_for_public = f"{self.command}:{path}"
        is_public = path in PUBLIC_ENDPOINTS or any(p.match(route_key_for_public) for p in PUBLIC_ENDPOINT_PATTERNS)
        if not is_public and not self._check_permission(method, path):
            username = self._get_current_username()
            self._json_response({'error': f"权限不足：用户 '{username}' 无权执行此操作"}, 403)
            return

        # 路由分发
        params = parse_qs(query)
        route_key = f"{method}:{path}"

        try:
            # 认证相关
            if route_key == 'POST:/api/auth/login':
                self._api_login()
            elif route_key == 'POST:/api/auth/logout':
                self._api_logout()
            elif route_key == 'GET:/api/auth/whoami':
                self._api_whoami()

            # SSO 认证相关
            elif route_key == 'GET:/api/auth/sso/providers':
                self._api_sso_providers()
            elif route_key == 'GET:/api/auth/sso/login':
                self._api_sso_login()
            elif method == 'GET' and path.startswith('/api/auth/sso/callback'):
                self._api_sso_callback()
            elif route_key == 'POST:/api/auth/sso/logout':
                self._api_sso_logout()

            # 用户管理
            elif route_key == 'GET:/api/users':
                self._api_user_list()
            elif route_key == 'POST:/api/users':
                self._api_user_add()
            elif re.match(r'DELETE:/api/users/[^/]+$', route_key):
                username = path.split('/')[-1]
                self._api_user_remove(username)
            elif re.match(r'PUT:/api/users/[^/]+/role$', route_key):
                username = path.split('/')[-2]
                self._api_user_role(username)
            elif re.match(r'PUT:/api/users/[^/]+/password$', route_key):
                username = path.split('/')[-2]
                self._api_user_password(username)

            # Token 管理
            elif route_key == 'POST:/api/tokens':
                self._api_token_generate()
            elif route_key == 'GET:/api/tokens':
                self._api_token_list()
            elif re.match(r'DELETE:/api/tokens/.+$', route_key):
                token = path.split('/')[-1]
                self._api_token_revoke(token)

            # 原子管理
            elif route_key == 'GET:/api/atoms':
                self._api_atom_list(params)
            elif route_key == 'POST:/api/atoms':
                self._api_atom_create()

            # 反馈相关（atom_id 可能包含 /，如 atoms/facts/xxx）
            # 注意：这些更具体的路由必须放在 GET:/api/atoms/.+$ 之前
            elif re.match(r'GET:/api/atoms/.+/comments$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/comments')]
                self._api_comment_list(atom_id)
            elif re.match(r'POST:/api/atoms/.+/comments$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/comments')]
                self._api_comment_add(atom_id)
            elif re.match(r'POST:/api/atoms/.+/favorite$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/favorite')]
                self._api_favorite_add(atom_id)
            elif re.match(r'DELETE:/api/atoms/.+/favorite$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/favorite')]
                self._api_favorite_remove(atom_id)
            elif re.match(r'POST:/api/atoms/.+/rate$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/rate')]
                self._api_rate(atom_id)

            # 审批流
            elif re.match(r'POST:/api/atoms/.+/submit$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/submit')]
                self._api_submit(atom_id)
            elif re.match(r'POST:/api/atoms/.+/approve$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/approve')]
                self._api_approve(atom_id)
            elif re.match(r'POST:/api/atoms/.+/reject$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/reject')]
                self._api_reject(atom_id)

            # 生命周期
            elif re.match(r'POST:/api/atoms/.+/publish$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/publish')]
                self._api_change_status(atom_id, 'published')
            elif re.match(r'POST:/api/atoms/.+/archive$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/archive')]
                self._api_change_status(atom_id, 'archived')
            elif re.match(r'POST:/api/atoms/.+/deprecate$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/deprecate')]
                self._api_change_status(atom_id, 'deprecated')

            # 阶段六：内容去重（必须在通配路由之前）
            elif re.match(r'GET:/api/atoms/.+/duplicates$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/duplicates')]
                self._api_atom_duplicates(atom_id, params)

            # 阶段六：协同编辑锁（必须在通配路由之前）
            elif re.match(r'POST:/api/atoms/.+/lock$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/lock')]
                self._api_atom_lock(atom_id)
            elif re.match(r'DELETE:/api/atoms/.+/lock$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/lock')]
                self._api_atom_unlock(atom_id)

            # 原子详情/更新（通配路由，放在最后）
            elif re.match(r'GET:/api/atoms/.+/summary$', route_key):
                atom_id = path[len('/api/atoms/'):-len('/summary')]
                self._api_atom_summary(atom_id)
            elif re.match(r'GET:/api/atoms/.+$', route_key):
                atom_id = path.replace('/api/atoms/', '')
                self._api_atom_get(atom_id)
            elif re.match(r'PUT:/api/atoms/.+$', route_key):
                atom_id = path.replace('/api/atoms/', '')
                self._api_atom_update(atom_id)

            # 审批列表
            elif route_key == 'GET:/api/approvals/pending':
                self._api_approvals_pending()
            elif route_key == 'GET:/api/approvals/history':
                self._api_approvals_history()

            # 审计日志
            elif route_key == 'GET:/api/audit':
                self._api_audit(params)

            # 统计分析
            elif route_key == 'GET:/api/stats':
                self._api_stats()
            elif route_key == 'GET:/api/analytics/behavior':
                self._api_analytics_behavior(params)

            # 备份恢复
            elif route_key == 'POST:/api/backup':
                self._api_backup()
            elif route_key == 'POST:/api/restore':
                self._api_restore()

            # 批量操作
            elif route_key == 'POST:/api/batch/tag':
                self._api_batch_tag()
            elif route_key == 'POST:/api/batch/move':
                self._api_batch_move()
            elif route_key == 'POST:/api/batch/delete':
                self._api_batch_delete()

            # 摄入
            elif route_key == 'POST:/api/ingest':
                self._api_ingest()
            elif route_key == 'POST:/api/ingest/upload':
                self._api_ingest_upload()

            # 搜索
            elif route_key == 'GET:/api/search':
                self._api_search(params)
            elif route_key == 'GET:/api/search/suggest':
                self._api_search_suggest(params)
            elif route_key == 'GET:/api/query':
                self._api_query(params)
            elif route_key == 'GET:/api/suggest':
                self._api_search_suggest(params)

            # 通知
            elif route_key == 'GET:/api/notifications':
                self._api_notifications()
            elif route_key == 'POST:/api/notifications/read':
                self._api_notifications_read()
            elif route_key == 'POST:/api/notifications/read-all':
                self._api_notifications_read_all()

            # 向量化
            elif route_key == 'POST:/api/embed':
                self._api_embed()

            # 健康
            elif route_key == 'GET:/api/health':
                self._api_health()

            # ============ 阶段六：AI 深化 / 协同完善 / 安全合规 / 分享外链 ============

            # AI 问答（多轮对话）
            elif route_key == 'POST:/api/qa/ask':
                self._api_qa_ask()
            elif route_key == 'GET:/api/qa/history':
                self._api_qa_history(params)
            elif route_key == 'POST:/api/qa/clear':
                self._api_qa_clear()

            # 内容去重（全局）
            elif route_key == 'GET:/api/duplicates':
                self._api_duplicates_list(params)
            elif route_key == 'POST:/api/duplicates/merge':
                self._api_duplicates_merge()

            # 知识质检
            elif route_key == 'GET:/api/quality/check':
                self._api_quality_check()

            # 敏感信息脱敏
            elif route_key == 'POST:/api/sensitive/detect':
                self._api_sensitive_detect()
            elif route_key == 'POST:/api/sensitive/mask':
                self._api_sensitive_mask()

            # 分享外链
            elif route_key == 'POST:/api/share':
                self._api_share_create()
            elif route_key == 'GET:/api/share':
                self._api_share_list()
            elif re.match(r'DELETE:/api/share/.+$', route_key):
                token = path.split('/')[-1]
                self._api_share_revoke(token)
            elif re.match(r'GET:/api/share/.+/access$', route_key):
                token = path[len('/api/share/'):-len('/access')]
                self._api_share_access(token, params)

            # Webhook 通知配置
            elif route_key == 'GET:/api/webhooks':
                self._api_webhook_list()
            elif route_key == 'POST:/api/webhooks':
                self._api_webhook_add()
            elif re.match(r'DELETE:/api/webhooks/.+$', route_key):
                webhook_id = path.split('/')[-1]
                self._api_webhook_remove(webhook_id)
            elif route_key == 'POST:/api/webhooks/test':
                self._api_webhook_test()

            # ============ OCR API（PLAN-004 Phase 3） ============
            elif route_key == 'POST:/api/ocr/submit':
                self._api_ocr_submit()
            elif re.match(r'GET:/api/ocr/tasks/.+$', route_key):
                task_id = path.split('/')[-1]
                self._api_ocr_get_task(task_id)
            elif re.match(r'GET:/api/ocr/assets/.+$', route_key):
                asset_id = path.split('/')[-1]
                self._api_ocr_get_by_asset(asset_id)

            # ============ Preview API（PLAN-004 Phase 3） ============
            elif re.match(r'GET:/api/preview/.+/cache$', route_key):
                atom_id = path[len('/api/preview/'):-len('/cache')]
                self._api_preview_cache(atom_id)
            elif re.match(r'GET:/api/preview/.+$', route_key):
                atom_id = path[len('/api/preview/'):]
                self._api_preview_get(atom_id)

            # ============ 配置 API（PLAN-004 Phase 3） ============
            elif route_key == 'GET:/api/config/mode':
                self._api_config_mode()
            elif route_key == 'GET:/api/config/status':
                self._api_config_status()
            elif route_key == 'GET:/api/config/sso':
                self._api_config_sso()

            else:
                self._json_response({'error': f'未知的 API 端点: {method} {path}'}, 404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._json_response({'error': f'服务器内部错误: {str(e)}'}, 500)

    # ========================================================================
    # 认证中间件
    # ========================================================================

    def _get_cookie(self, name: str) -> Optional[str]:
        """从请求中获取指定 cookie 的值.

        Args:
            name: Cookie 名称

        Returns:
            Cookie 值，不存在返回 None
        """
        cookie_header = self.headers.get('Cookie', '')
        if not cookie_header:
            return None
        for part in cookie_header.split(';'):
            part = part.strip()
            if part.startswith(f'{name}='):
                return part[len(name) + 1:]
        return None

    def _authenticate(self, path: str) -> bool:
        """认证中间件，检查请求是否已登录.

        Args:
            path: 请求路径

        Returns:
            是否通过认证
        """
        # 公开端点无需认证
        if path in PUBLIC_ENDPOINTS:
            return True
        # 检查公开端点正则
        route_key = f"{self.command}:{path}"
        for pattern in PUBLIC_ENDPOINT_PATTERNS:
            if pattern.match(route_key):
                return True
        # 通过 Token 或 Session 认证
        auth = self._get_auth_manager()
        # 1. 检查 Authorization Header（Token）
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            role = auth.validate_token(token)
            if role:
                # Token 有效，注入用户信息
                token_info = auth.config.get('tokens', {}).get(token, {})
                self._current_user = {
                    'username': token_info.get('username', 'token_user'),
                    'role': role,
                }
                return True
        # 2. 检查 Session（已登录）
        if auth.is_logged_in():
            self._current_user = auth.get_current_user()
            return True
        # 3. 检查 SSO 会话 cookie
        if auth.is_sso_enabled():
            sso_session_id = self._get_cookie('sso_session_id')
            if sso_session_id:
                try:
                    session_info = _run_async(auth.validate_sso_session(sso_session_id))
                    if session_info:
                        self._current_user = {
                            'username': session_info.get('user_id', 'anonymous'),
                            'role': session_info.get('roles', ['user'])[0] if session_info.get('roles') else 'user',
                        }
                        return True
                except Exception as exc:
                    logger.warning("SSO session validation failed: %s", exc)
        # 4. 未启用权限控制时，允许匿名访问
        if not auth.is_enabled():
            self._current_user = {'username': 'anonymous', 'role': 'guest'}
            return True
        return False

    def _check_permission(self, method: str, path: str) -> bool:
        """权限检查.

        Args:
            method: HTTP 方法
            path: 请求路径

        Returns:
            是否有权限
        """
        user = getattr(self, '_current_user', {'username': 'anonymous', 'role': 'guest'})
        role = user.get('role', 'guest')

        # guest 角色仅允许只读操作
        if role == 'guest':
            route_key = f"{method}:{path}"
            # 允许只读端点
            for readonly in READONLY_ACTIONS:
                if route_key.startswith(readonly):
                    return True
            return False

        # reader 角色：允许只读 + 评论/收藏/评分
        if role == 'reader':
            route_key = f"{method}:{path}"
            for readonly in READONLY_ACTIONS:
                if route_key.startswith(readonly):
                    return True
            # 允许评论、收藏、评分
            if any(x in path for x in ['/comments', '/favorite', '/rate']):
                return method in ('POST', 'DELETE')
            return False

        # editor 角色：允许 reader + 摄入/编辑/发布/归档/提交
        if role == 'editor':
            if any(x in path for x in ['/approve', '/reject', '/users', '/tokens', '/audit', '/backup', '/restore', '/batch/delete']):
                return False
            return True

        # admin 角色：允许所有操作
        if role == 'admin':
            return True

        return False

    def _get_current_username(self) -> str:
        """获取当前用户名."""
        user = getattr(self, '_current_user', None)
        return user.get('username', 'anonymous') if user else 'anonymous'

    def _get_current_role(self) -> str:
        """获取当前用户角色."""
        user = getattr(self, '_current_user', None)
        return user.get('role', 'guest') if user else 'guest'

    def _is_mobile_request(self) -> bool:
        """检测是否为移动端请求.

        通过 User-Agent 或 Sec-CH-UA-Mobile 请求头判断。
        用于移动端 API 优化（返回精简数据）。
        """
        # 优先使用 Client Hints（现代浏览器）
        mobile_hint = self.headers.get('Sec-CH-UA-Mobile', '')
        if mobile_hint == '?1':
            return True
        # 回退到 User-Agent 检测
        user_agent = self.headers.get('User-Agent', '')
        mobile_patterns = [
            'Android', 'iPhone', 'iPad', 'iPod',
            'Windows Phone', 'BlackBerry', 'Mobile',
        ]
        return any(p in user_agent for p in mobile_patterns)

    # ========================================================================
    # 认证 API
    # ========================================================================

    def _api_login(self) -> None:
        """用户登录."""
        data = self._read_json_body()
        username = data.get('username', '')
        password = data.get('password', '')
        if not username or not password:
            self._json_response({'error': '用户名和密码不能为空'}, 400)
            return
        auth = self._get_auth_manager()
        if auth.login(username, password):
            user = auth.get_current_user()
            self._json_response({
                'status': 'ok',
                'user': user,
                'message': f'登录成功: {username}',
            })
        else:
            self._json_response({'error': '用户名或密码错误'}, 401)

    def _api_logout(self) -> None:
        """退出登录."""
        auth = self._get_auth_manager()
        username = auth.get_current_username()
        auth.logout()
        self._json_response({'status': 'ok', 'message': f'已退出登录: {username}'})

    def _api_whoami(self) -> None:
        """获取当前用户信息."""
        auth = self._get_auth_manager()
        user = auth.get_current_user()
        if user:
            self._json_response({'user': user})
        else:
            self._json_response({'user': None, 'message': '未登录'})

    # ========================================================================
    # SSO 认证 API
    # ========================================================================

    def _api_sso_providers(self) -> None:
        """返回可用 SSO 提供商列表."""
        auth = self._get_auth_manager()
        if not auth.is_sso_enabled():
            self._json_response({'providers': []})
            return
        self._json_response({
            'providers': [
                {
                    'name': 'casdoor',
                    'display_name': '企业 SSO',
                    'login_url': '/api/auth/sso/login',
                }
            ]
        })

    def _api_sso_login(self) -> None:
        """发起 SSO 登录（302 重定向到 IdP）."""
        auth = self._get_auth_manager()
        if not auth.is_sso_enabled():
            self._json_response({'error': 'SSO is not enabled'}, 501)
            return
        try:
            result = _run_async(auth.sso_login())
            if hasattr(result, 'redirect_url') and result.redirect_url:
                self.send_response(302)
                self.send_header('Location', result.redirect_url)
                self._send_cors_headers()
                self.end_headers()
            else:
                error_msg = getattr(result, 'error', 'Unknown SSO login error')
                self._json_response({'error': error_msg}, 500)
        except Exception as exc:
            logger.error("SSO login failed: %s", exc)
            self._json_response({'error': str(exc)}, 500)

    def _api_sso_callback(self) -> None:
        """OAuth2 回调处理."""
        # 从 URL query 参数获取 code 和 state
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = params.get('code', [''])[0]
        state = params.get('state', [''])[0]

        if not code or not state:
            self.send_response(302)
            self.send_header('Location', '/login.html?error=missing_params')
            self._send_cors_headers()
            self.end_headers()
            return

        auth = self._get_auth_manager()
        try:
            result = _run_async(auth.sso_callback(code, state))
            if hasattr(result, 'success') and result.success:
                # 获取会话 ID 并设置 cookie
                session_id = getattr(result, 'session_id', None)
                user_id = getattr(result, 'user_id', 'anonymous')
                self.send_response(302)
                self.send_header('Location', '/')
                if session_id:
                    self.send_header(
                        'Set-Cookie',
                        f'sso_session_id={session_id}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400'
                    )
                self._send_cors_headers()
                self.end_headers()
            else:
                error_msg = getattr(result, 'error', 'SSO callback failed')
                self.send_response(302)
                self.send_header('Location', f'/login.html?error={error_msg}')
                self._send_cors_headers()
                self.end_headers()
        except Exception as exc:
            logger.error("SSO callback failed: %s", exc)
            self.send_response(302)
            self.send_header('Location', f'/login.html?error={exc}')
            self._send_cors_headers()
            self.end_headers()

    def _api_sso_logout(self) -> None:
        """SSO 登出."""
        auth = self._get_auth_manager()
        if not auth.is_sso_enabled():
            self._json_response({'error': 'SSO is not enabled'}, 501)
            return

        # 获取当前 SSO 会话 ID
        session_id = self._get_cookie('sso_session_id')
        if not session_id:
            # 也尝试从 header 获取
            session_id = self.headers.get('X-SSO-Session-Id', '')

        try:
            result = _run_async(auth.sso_logout(session_id or ''))
            redirect_url = getattr(result, 'redirect_url', None)
            # 清除 SSO 会话 cookie
            self.send_response(200)
            self.send_header(
                'Set-Cookie',
                'sso_session_id=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0'
            )
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            body = json.dumps(
                {'logout_url': redirect_url, 'status': 'ok'},
                ensure_ascii=False, indent=2
            ).encode('utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            logger.error("SSO logout failed: %s", exc)
            self._json_response({'error': str(exc)}, 500)

    # ========================================================================
    # 用户管理 API
    # ========================================================================

    def _api_user_list(self) -> None:
        """用户列表."""
        auth = self._get_auth_manager()
        users = auth.list_users()
        self._json_response({'users': users, 'count': len(users)})

    def _api_user_add(self) -> None:
        """添加用户."""
        data = self._read_json_body()
        username = data.get('username', '')
        password = data.get('password', '')
        role = data.get('role', 'reader')
        if not username or not password:
            self._json_response({'error': '用户名和密码不能为空'}, 400)
            return
        auth = self._get_auth_manager()
        if auth.add_user(username, role, password):
            self._json_response({'status': 'ok', 'message': f'用户已添加: {username}'})
        else:
            self._json_response({'error': '添加失败（角色无效或用户已存在）'}, 400)

    def _api_user_remove(self, username: str) -> None:
        """移除用户."""
        auth = self._get_auth_manager()
        if auth.remove_user(username):
            self._json_response({'status': 'ok', 'message': f'用户已移除: {username}'})
        else:
            self._json_response({'error': f'用户不存在: {username}'}, 404)

    def _api_user_role(self, username: str) -> None:
        """更新用户角色."""
        data = self._read_json_body()
        role = data.get('role', '')
        auth = self._get_auth_manager()
        if auth.update_user_role(username, role):
            self._json_response({'status': 'ok', 'message': f'{username} 角色已更新为: {role}'})
        else:
            self._json_response({'error': '更新失败'}, 400)

    def _api_user_password(self, username: str) -> None:
        """修改用户密码."""
        data = self._read_json_body()
        new_password = data.get('password', '')
        if not new_password:
            self._json_response({'error': '新密码不能为空'}, 400)
            return
        auth = self._get_auth_manager()
        if auth.change_password(username, new_password):
            self._json_response({'status': 'ok', 'message': f'{username} 密码已修改'})
        else:
            self._json_response({'error': '修改失败'}, 400)

    # ========================================================================
    # Token 管理 API
    # ========================================================================

    def _api_token_generate(self) -> None:
        """生成 Token."""
        data = self._read_json_body()
        username = data.get('username', '')
        role = data.get('role')
        auth = self._get_auth_manager()
        token = auth.generate_token(username, role)
        if token:
            self._json_response({'status': 'ok', 'token': token, 'username': username})
        else:
            self._json_response({'error': '生成失败（用户不存在）'}, 400)

    def _api_token_list(self) -> None:
        """Token 列表."""
        auth = self._get_auth_manager()
        tokens = auth.list_tokens()
        self._json_response({'tokens': tokens, 'count': len(tokens)})

    def _api_token_revoke(self, token: str) -> None:
        """吊销 Token."""
        auth = self._get_auth_manager()
        if auth.revoke_token(token):
            self._json_response({'status': 'ok', 'message': 'Token 已吊销'})
        else:
            self._json_response({'error': 'Token 不存在'}, 404)

    # ========================================================================
    # 原子管理 API
    # ========================================================================

    def _api_atom_list(self, params: Dict) -> None:
        """原子列表（支持双模式 + 移动端精简）."""
        atom_type = params.get('type', [None])[0]
        limit = int(params.get('limit', ['100'])[0])
        is_mobile = self._is_mobile_request()

        if self.storage and self.storage.mode == 'db':
            # db_mode: 通过 StorageInterface 查询
            try:
                atoms = _run_async(self.storage.list_atoms(kb_id=1, by_type=atom_type, limit=limit, offset=0))
                # 统一响应格式
                result = []
                for a in atoms:
                    if is_mobile:
                        # 移动端精简：只返回核心字段
                        result.append({
                            'id': str(a.get('id', '')),
                            'path': a.get('slug', ''),
                            'type': a.get('type', 'Unknown'),
                            'title': a.get('title', ''),
                            'description': a.get('description', '')[:80],  # 截断描述
                        })
                    else:
                        result.append({
                            'id': str(a.get('id', '')),
                            'path': a.get('slug', ''),
                            'type': a.get('type', 'Unknown'),
                            'title': a.get('title', ''),
                            'description': a.get('description', ''),
                            'tags': a.get('tags', []),
                            'status': a.get('status', 'active'),
                            'author': a.get('author_id', ''),
                            'created': a.get('created_at', ''),
                            'updated': a.get('updated_at', ''),
                        })
                self._json_response({'atoms': result, 'count': len(result)})
                return
            except Exception as e:
                logger.error("db_mode atom list failed, falling back to file scan: %s", e)

        # file_mode（或 db_mode 降级）：文件扫描
        atoms = self._load_atoms(by_type=atom_type, limit=limit)
        if is_mobile:
            # 移动端精简：只保留核心字段
            slim_atoms = []
            for a in atoms:
                slim_atoms.append({
                    'id': a.get('id', ''),
                    'path': a.get('path', ''),
                    'type': a.get('type', 'Unknown'),
                    'title': a.get('title', ''),
                    'description': (a.get('description', '') or '')[:80],
                })
            self._json_response({'atoms': slim_atoms, 'count': len(slim_atoms)})
        else:
            self._json_response({'atoms': atoms, 'count': len(atoms)})

    def _api_atom_get(self, atom_id: str) -> None:
        """获取原子详情（支持双模式）."""
        if self.storage and self.storage.mode == 'db':
            # db_mode: 尝试数字 ID 解析
            try:
                numeric_id = int(atom_id)
                atom = _run_async(self.storage.get_atom(numeric_id))
                if atom:
                    # 统一响应格式（兼容前端期望的字段名）
                    self._json_response({
                        'id': atom_id,
                        'path': atom.get('slug', ''),
                        'frontmatter': atom.get('metadata', {}),
                        'content': atom.get('content', ''),
                        'body': atom.get('content', ''),
                        'tags': atom.get('tags', []),
                        'comments': [],
                    })
                    return
            except (ValueError, Exception) as e:
                if not isinstance(e, ValueError):
                    logger.error("db_mode atom get failed: %s", e)

        # file_mode（或 db_mode 降级）：文件读取
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path or not atom_path.exists():
            self._json_response({'error': 'Atom not found'}, 404)
            return
        content = atom_path.read_text(encoding='utf-8')
        # 解析 frontmatter
        yaml_parser = SimpleYAMLParser()
        fm = {}
        body = content
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                fm = yaml_parser.parse(parts[1]) or {}
                body = parts[2]
        # 获取评论
        comments = []
        try:
            from .feedback import FeedbackManager
            fm_mgr = FeedbackManager(self.kb_dir)
            comments = fm_mgr.get_comments(atom_path)
        except Exception:
            pass
        self._json_response({
            'id': atom_id,
            'path': str(atom_path.relative_to(self.kb_dir)),
            'frontmatter': fm,
            'content': content,
            'body': body,
            'comments': comments,
        })

    def _api_atom_summary(self, atom_id: str) -> None:
        """生成原子摘要（简化版：提取关键段落）."""
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path or not atom_path.exists():
            self._json_response({'error': 'Atom not found'}, 404)
            return
        content = atom_path.read_text(encoding='utf-8')
        # 去掉 frontmatter
        body = content
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                body = parts[2]
        # 提取摘要：第一段非空文本 + 关键句子
        lines = [l.strip() for l in body.split('\n') if l.strip() and not l.startswith('#')]
        if not lines:
            self._json_response({'summary': '（无内容）', 'method': 'empty'})
            return
        # 第一段作为摘要
        first_para = lines[0]
        # 如果内容较长，拼接前 3 行
        if len(first_para) < 100 and len(lines) > 1:
            first_para = ' '.join(lines[:3])
        # 截断到 300 字
        if len(first_para) > 300:
            first_para = first_para[:300] + '...'
        # 统计关键信息
        word_count = len(body.replace(' ', '').replace('\n', ''))
        line_count = len([l for l in body.split('\n') if l.strip()])
        summary = f"**摘要**：{first_para}\n\n**统计**：{word_count} 字，{line_count} 行。"
        self._json_response({'summary': summary, 'word_count': word_count, 'line_count': line_count})

    def _api_atom_create(self) -> None:
        """创建新原子（支持双模式）."""
        data = self._read_json_body()
        atom_type = data.get('type', 'fact')
        title = data.get('title', '')
        body = data.get('body', '')
        tags = data.get('tags', [])
        if not title:
            self._json_response({'error': '标题不能为空'}, 400)
            return

        if self.storage and self.storage.mode == 'db':
            # db_mode: 通过 StorageInterface 创建
            try:
                atom_data = {
                    'kb_id': 1,  # 默认知识库
                    'title': title,
                    'content': body,
                    'type': atom_type,
                    'tags': tags,
                    'status': 'draft',
                }
                atom_id = _run_async(self.storage.create_atom(atom_data))
                self._json_response({
                    'status': 'ok',
                    'id': str(atom_id),
                    'path': f"atoms/{atom_type}s/{title.lower().replace(' ', '-')}",
                })
                return
            except Exception as e:
                logger.error("db_mode atom create failed, falling back to file: %s", e)

        # file_mode（或 db_mode 降级）：写 Markdown 文件
        slug = re.sub(r'[^\w\-]', '-', title.lower()).strip('-')[:50]
        atom_path = self.kb_dir / 'atoms' / f"{atom_type}s" / f"{slug}.md"
        atom_path.parent.mkdir(parents=True, exist_ok=True)
        # 生成 frontmatter
        from datetime import datetime
        tags_str = ', '.join(tags) if tags else ''
        content = f"""---
okf_version: "0.1"
id: {atom_type}-{slug}
title: {title}
type: {atom_type}
status: draft
created: {datetime.now().strftime('%Y-%m-%d')}
tags: [{tags_str}]
---

# {title}

{body}
"""
        with self._write_lock:
            atom_path.write_text(content, encoding='utf-8')
        self._json_response({
            'status': 'ok',
            'id': f"atoms/{atom_type}s/{slug}",
            'path': str(atom_path.relative_to(self.kb_dir)),
        })

    def _api_atom_update(self, atom_id: str) -> None:
        """更新原子内容（支持双模式）."""
        data = self._read_json_body()
        body = data.get('body', '')

        if self.storage and self.storage.mode == 'db':
            # db_mode: 通过 StorageInterface 更新
            try:
                numeric_id = int(atom_id)
                update_data = {'content': body}
                success = _run_async(self.storage.update_atom(numeric_id, update_data))
                if success:
                    self._json_response({'status': 'ok', 'message': '原子已更新'})
                    return
                else:
                    self._json_response({'error': 'Atom not found'}, 404)
                    return
            except (ValueError, Exception) as e:
                if not isinstance(e, ValueError):
                    logger.error("db_mode atom update failed: %s", e)

        # file_mode（或 db_mode 降级）：读-改-写 Markdown 文件
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path or not atom_path.exists():
            self._json_response({'error': 'Atom not found'}, 404)
            return
        # 读取原内容，保留 frontmatter
        content = atom_path.read_text(encoding='utf-8')
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                new_content = f"{parts[0]}---{parts[1]}---\n\n{body}\n"
            else:
                new_content = body
        else:
            new_content = body
        with self._write_lock:
            atom_path.write_text(new_content, encoding='utf-8')
        self._json_response({'status': 'ok', 'message': '原子已更新'})

    # ========================================================================
    # 反馈 API
    # ========================================================================

    def _api_comment_list(self, atom_id: str) -> None:
        """评论列表."""
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path:
            self._json_response({'error': 'Atom not found'}, 404)
            return
        from .feedback import FeedbackManager
        fm = FeedbackManager(self.kb_dir)
        comments = fm.get_comments(atom_path)
        self._json_response({'comments': comments, 'count': len(comments)})

    def _api_comment_add(self, atom_id: str) -> None:
        """添加评论."""
        data = self._read_json_body()
        text = data.get('text', '')
        if not text:
            self._json_response({'error': '评论内容不能为空'}, 400)
            return
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path:
            self._json_response({'error': 'Atom not found'}, 404)
            return
        username = self._get_current_username()
        from .feedback import FeedbackManager
        from .audit import AuditLogger
        with self._write_lock:
            fm = FeedbackManager(self.kb_dir)
            if fm.add_comment(atom_path, text, author=username):
                AuditLogger(self.kb_dir).log('comment', str(atom_path), user=username, detail=text[:100])
                self._json_response({'status': 'ok', 'message': '评论已添加'})
            else:
                self._json_response({'error': '评论失败'}, 500)

    def _api_favorite_add(self, atom_id: str) -> None:
        """收藏."""
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path:
            self._json_response({'error': 'Atom not found'}, 404)
            return
        username = self._get_current_username()
        from .feedback import FeedbackManager
        from .audit import AuditLogger
        with self._write_lock:
            fm = FeedbackManager(self.kb_dir)
            fm.add_favorite(atom_path, user=username)
            AuditLogger(self.kb_dir).log('favorite', str(atom_path), user=username)
        self._json_response({'status': 'ok', 'message': '已收藏'})

    def _api_favorite_remove(self, atom_id: str) -> None:
        """取消收藏."""
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path:
            self._json_response({'error': 'Atom not found'}, 404)
            return
        username = self._get_current_username()
        from .feedback import FeedbackManager
        with self._write_lock:
            fm = FeedbackManager(self.kb_dir)
            fm.remove_favorite(atom_path, user=username)
        self._json_response({'status': 'ok', 'message': '已取消收藏'})

    def _api_rate(self, atom_id: str) -> None:
        """评分."""
        data = self._read_json_body()
        score = int(data.get('score', 0))
        if score < 1 or score > 5:
            self._json_response({'error': '评分必须在 1-5 之间'}, 400)
            return
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path:
            self._json_response({'error': 'Atom not found'}, 404)
            return
        username = self._get_current_username()
        from .feedback import FeedbackManager
        from .audit import AuditLogger
        with self._write_lock:
            fm = FeedbackManager(self.kb_dir)
            if fm.rate(atom_path, score, user=username):
                AuditLogger(self.kb_dir).log('rate', str(atom_path), user=username, detail=f'score={score}')
                self._json_response({'status': 'ok', 'message': f'评分 {score} 已记录'})
            else:
                self._json_response({'error': '评分失败'}, 500)

    # ========================================================================
    # 审批流 API
    # ========================================================================

    def _api_submit(self, atom_id: str) -> None:
        """提交审核."""
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path:
            self._json_response({'error': 'Atom not found'}, 404)
            return
        username = self._get_current_username()
        from .workflow import WorkflowManager
        from .audit import AuditLogger
        with self._write_lock:
            wf = WorkflowManager(self.kb_dir)
            if wf.submit(atom_path, submitter=username):
                AuditLogger(self.kb_dir).log('submit', str(atom_path), user=username)
                self._json_response({'status': 'ok', 'message': '已提交审核'})
            else:
                self._json_response({'error': '提交失败'}, 500)

    def _api_approve(self, atom_id: str) -> None:
        """审核通过."""
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path:
            self._json_response({'error': 'Atom not found'}, 404)
            return
        username = self._get_current_username()
        from .workflow import WorkflowManager
        from .audit import AuditLogger
        with self._write_lock:
            wf = WorkflowManager(self.kb_dir)
            if wf.approve(atom_path, reviewer=username):
                AuditLogger(self.kb_dir).log('approve', str(atom_path), user=username)
                self._json_response({'status': 'ok', 'message': '审核通过'})
            else:
                self._json_response({'error': '审核失败'}, 500)

    def _api_reject(self, atom_id: str) -> None:
        """审核驳回."""
        data = self._read_json_body()
        reason = data.get('reason', '')
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path:
            self._json_response({'error': 'Atom not found'}, 404)
            return
        username = self._get_current_username()
        from .workflow import WorkflowManager
        from .audit import AuditLogger
        with self._write_lock:
            wf = WorkflowManager(self.kb_dir)
            if wf.reject(atom_path, reason=reason, reviewer=username):
                AuditLogger(self.kb_dir).log('reject', str(atom_path), user=username, detail=reason)
                self._json_response({'status': 'ok', 'message': '已驳回'})
            else:
                self._json_response({'error': '驳回失败'}, 500)

    def _api_approvals_pending(self) -> None:
        """待审批列表."""
        from .workflow import WorkflowManager
        wf = WorkflowManager(self.kb_dir)
        pending = wf.get_pending_reviews()
        self._json_response({'pending': pending, 'count': len(pending)})

    def _api_approvals_history(self) -> None:
        """审批历史."""
        from .workflow import WorkflowManager
        wf = WorkflowManager(self.kb_dir)
        history = wf.get_review_history()
        self._json_response({'history': history, 'count': len(history)})

    # ========================================================================
    # 生命周期 API
    # ========================================================================

    def _api_change_status(self, atom_id: str, new_status: str) -> None:
        """修改原子状态."""
        atom_path = self._resolve_atom_path(atom_id)
        if not atom_path:
            self._json_response({'error': 'Atom not found'}, 404)
            return
        username = self._get_current_username()
        from .lifecycle import LifecycleManager
        from .audit import AuditLogger
        with self._write_lock:
            manager = LifecycleManager(self.kb_dir)
            if manager.change_status(atom_path, new_status):
                AuditLogger(self.kb_dir).log(f'status:{new_status}', str(atom_path), user=username)
                self._json_response({'status': 'ok', 'message': f'状态已改为: {new_status}'})
            else:
                self._json_response({'error': '状态修改失败'}, 500)

    # ========================================================================
    # 审计日志 API
    # ========================================================================

    def _api_audit(self, params: Dict) -> None:
        """查询审计日志（支持双模式）."""
        if self.storage and self.storage.mode == 'db':
            # db_mode: 通过 StorageInterface 查询
            try:
                entries = _run_async(self.storage.query_audit(
                    event_type=params.get('action', [None])[0],
                    start_time=params.get('since', [None])[0],
                    limit=int(params.get('limit', ['50'])[0]),
                ))
                self._json_response({'entries': entries, 'count': len(entries)})
                return
            except Exception as e:
                logger.error("db_mode audit query failed, falling back to file: %s", e)

        # file_mode（或降级）：文件审计日志
        from .audit import AuditLogger
        audit_logger = AuditLogger(self.kb_dir)
        entries = audit_logger.query(
            since=params.get('since', [None])[0],
            action=params.get('action', [None])[0],
            limit=int(params.get('limit', ['50'])[0]),
        )
        self._json_response({'entries': entries, 'count': len(entries)})

    # ========================================================================
    # 统计分析 API
    # ========================================================================

    def _api_stats(self) -> None:
        """统计数据（支持双模式）."""
        if self.storage and self.storage.mode == 'db':
            # db_mode: 通过 StorageInterface 获取统计
            try:
                stats = _run_async(self.storage.get_stats())
                self._json_response(stats)
                return
            except Exception as e:
                logger.error("db_mode stats failed, falling back to file: %s", e)

        # file_mode（或降级）：文件系统统计
        from .analytics import AnalyticsEngine
        engine = AnalyticsEngine(self.kb_dir)
        stats = engine.get_stats()
        self._json_response(stats)

    def _api_analytics_behavior(self, params: Dict) -> None:
        """行为分析."""
        from .analytics import AnalyticsEngine
        engine = AnalyticsEngine(self.kb_dir)
        stats = engine.get_stats()
        # 补充行为数据
        from .audit import AuditLogger
        logger = AuditLogger(self.kb_dir)
        entries = logger.query(limit=500)
        action_counts = {}
        user_counts = {}
        for e in entries:
            action = e.get('action', 'unknown')
            action_counts[action] = action_counts.get(action, 0) + 1
            user = e.get('user', 'anonymous')
            user_counts[user] = user_counts.get(user, 0) + 1
        self._json_response({
            'total_atoms': stats.get('total_atoms', 0),
            'by_type': stats.get('by_type', {}),
            'by_status': stats.get('by_status', {}),
            'action_counts': action_counts,
            'user_activity': user_counts,
            'recent_activity': stats.get('recent_activity', []),
        })

    # ========================================================================
    # 备份恢复 API
    # ========================================================================

    def _api_backup(self) -> None:
        """备份."""
        data = self._read_json_body()
        output = data.get('output', '')
        from .backup import BackupManager
        mgr = BackupManager(self.kb_dir)
        if not output:
            output = str(self.kb_dir / f"backup-{int(time.time())}.tar.gz")
        result = mgr.backup(Path(output))
        self._json_response({'status': 'ok', 'output': output, 'result': result})

    def _api_restore(self) -> None:
        """恢复."""
        data = self._read_json_body()
        backup_path = data.get('path', '')
        if not backup_path:
            self._json_response({'error': '缺少备份路径'}, 400)
            return
        from .backup import BackupManager
        mgr = BackupManager(self.kb_dir)
        result = mgr.restore(Path(backup_path))
        self._json_response({'status': 'ok' if result else 'failed', 'result': result})

    # ========================================================================
    # 批量操作 API
    # ========================================================================

    def _api_batch_tag(self) -> None:
        """批量打标签（支持双模式）."""
        data = self._read_json_body()
        atom_ids = data.get('atoms', [])
        tags = data.get('tags', [])

        if self.storage and self.storage.mode == 'db':
            # db_mode: 通过 StorageInterface 操作标签
            try:
                results = {'success': 0, 'failed': 0}
                for atom_id_str in atom_ids:
                    try:
                        numeric_id = int(atom_id_str)
                        for tag_name in tags:
                            _run_async(self.storage.add_atom_tag(numeric_id, tag_name))
                        results['success'] += 1
                    except Exception:
                        results['failed'] += 1
                self._json_response({'status': 'ok', 'result': results})
                return
            except Exception as e:
                logger.error("db_mode batch_tag failed, falling back to file: %s", e)

        # file_mode（或降级）：批量文件操作
        from .batch_ops import BatchOperations
        ops = BatchOperations(self.kb_dir)
        result = ops.batch_tag(atom_ids, tags)
        self._json_response({'status': 'ok', 'result': result})

    def _api_batch_move(self) -> None:
        """批量移动."""
        data = self._read_json_body()
        atom_ids = data.get('atoms', [])
        target = data.get('target', '')
        from .batch_ops import BatchOperations
        ops = BatchOperations(self.kb_dir)
        result = ops.batch_move(atom_ids, target)
        self._json_response({'status': 'ok', 'result': result})

    def _api_batch_delete(self) -> None:
        """批量删除."""
        data = self._read_json_body()
        atom_ids = data.get('atoms', [])
        from .batch_ops import BatchOperations
        ops = BatchOperations(self.kb_dir)
        result = ops.batch_delete(atom_ids)
        self._json_response({'status': 'ok', 'result': result})

    # ========================================================================
    # 摄入 API
    # ========================================================================

    def _api_ingest(self) -> None:
        """摄入资料."""
        data = self._read_json_body()
        source = data.get('source', '')
        if not source:
            self._json_response({'error': '缺少 source 路径'}, 400)
            return
        ingestor = KnowledgeIngestor(self.kb_dir)
        success = ingestor.ingest(Path(source))
        if success:
            self._json_response({'status': 'ok', 'source': source})
        else:
            self._json_response({'error': '摄入失败'}, 500)

    def _api_ingest_upload(self) -> None:
        """文件上传摄入."""
        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            self._json_response({'error': '仅支持 multipart/form-data'}, 400)
            return
        # 简化处理：读取整个 body 作为文件内容
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        # 解析 multipart 数据（简化版）
        # 提取文件名和内容
        filename = 'upload.md'
        file_content = body
        # 尝试从 Content-Type 提取 boundary
        boundary = None
        for part in content_type.split(';'):
            part = part.strip()
            if part.startswith('boundary='):
                boundary = part[len('boundary='):].strip('"')
                break
        if boundary:
            boundary_bytes = boundary.encode()
            parts = body.split(b'--' + boundary_bytes)
            for part in parts:
                if b'Content-Disposition' in part and b'filename=' in part:
                    # 提取文件名
                    disp_match = re.search(rb'filename="([^"]+)"', part)
                    if disp_match:
                        filename = disp_match.group(1).decode('utf-8')
                    # 提取文件内容（在空行之后）
                    content_start = part.find(b'\r\n\r\n')
                    if content_start > 0:
                        file_content = part[content_start + 4:].rstrip(b'\r\n')
                    break
        # 保存到 raw/ 目录
        raw_dir = self.kb_dir / 'raw' / 'reference'
        raw_dir.mkdir(parents=True, exist_ok=True)
        upload_path = raw_dir / filename
        with self._write_lock:
            upload_path.write_bytes(file_content)
        # 摄入
        ingestor = KnowledgeIngestor(self.kb_dir)
        success = ingestor.ingest(upload_path)
        if success:
            self._json_response({'status': 'ok', 'filename': filename, 'ingested': True})
        else:
            self._json_response({'status': 'ok', 'filename': filename, 'ingested': False, 'message': '文件已保存但摄入失败'})

    # ========================================================================
    # 搜索 API
    # ========================================================================

    def _api_search(self, params: Dict) -> None:
        """搜索（支持双模式）."""
        q = params.get('q', [''])[0]
        if not q:
            self._json_response({'error': '缺少查询参数 q'}, 400)
            return
        semantic = params.get('semantic', ['0'])[0] in ('1', 'true', 'yes')
        limit = int(params.get('limit', ['20'])[0])
        by_type = params.get('type', [None])[0]
        sort_by = params.get('sort', ['relevance'])[0]

        if self.storage and self.storage.mode == 'db':
            # db_mode: 通过 StorageInterface 全文搜索
            try:
                results = _run_async(self.storage.search_atoms(
                    q, kb_id=None, by_type=by_type, limit=limit, offset=0
                ))
                # 统一响应格式
                formatted = []
                for r in results:
                    formatted.append({
                        'id': str(r.get('id', '')),
                        'path': r.get('slug', ''),
                        'type': r.get('type', ''),
                        'title': r.get('title', ''),
                        'description': r.get('description', ''),
                        'tags': r.get('tags', []),
                        'score': r.get('rank', 0),
                    })
                self._json_response({'query': q, 'results': formatted, 'count': len(formatted)})
                return
            except Exception as e:
                logger.error("db_mode search failed, falling back to file search: %s", e)

        # file_mode（或 db_mode 降级）：使用 KnowledgeQuerier
        querier = KnowledgeQuerier(self.kb_dir)
        results = querier.query(q, limit=limit, by_type=by_type, semantic=semantic, sort_by=sort_by)
        for r in results:
            r.pop('body', None)
            r.pop('frontmatter', None)
        self._json_response({'query': q, 'results': results, 'count': len(results)})

    def _api_search_suggest(self, params: Dict) -> None:
        """搜索联想."""
        prefix = params.get('q', [''])[0]
        querier = KnowledgeQuerier(self.kb_dir)
        suggestions = querier.get_suggestions(prefix)
        self._json_response({'suggestions': suggestions})

    def _api_query(self, params: Dict) -> None:
        """查询知识（兼容旧接口）."""
        self._api_search(params)

    # ========================================================================
    # 通知 API
    # ========================================================================

    def _api_notifications(self) -> None:
        """通知列表."""
        from .audit import AuditLogger
        from .workflow import WorkflowManager
        notifications = []
        # 待审核通知
        try:
            wf = WorkflowManager(self.kb_dir)
            pending = wf.get_pending_reviews()
            for p in pending:
                notifications.append({
                    'id': f"pending-{p.get('atom_id', '')}",
                    'event': 'review_requested',
                    'title': f"待审核: {p.get('atom_id', p.get('title', ''))}",
                    'message': f"提交者: {p.get('submitter', '-')}",
                    'timestamp': p.get('submitted_at', p.get('timestamp', '')),
                    'read': False,
                })
        except Exception:
            pass
        # 最近操作通知
        try:
            logger = AuditLogger(self.kb_dir)
            entries = logger.query(limit=10)
            for i, e in enumerate(entries):
                action = e.get('action', '')
                notifications.append({
                    'id': f"audit-{i}-{e.get('timestamp', '')}",
                    'event': action,
                    'title': f"{action}: {e.get('target', '')}",
                    'message': f"用户: {e.get('user', '-')}" + (f"，详情: {e.get('detail', '')}" if e.get('detail') else ''),
                    'timestamp': e.get('timestamp', ''),
                    'read': True,  # 审计日志默认视为已读
                })
        except Exception:
            pass
        self._json_response({'notifications': notifications, 'count': len(notifications)})

    def _api_notifications_read(self) -> None:
        """标记通知为已读（简化实现：直接返回成功）."""
        self._json_response({'status': 'ok', 'message': '已标记为已读'})

    def _api_notifications_read_all(self) -> None:
        """标记所有通知为已读."""
        self._json_response({'status': 'ok', 'message': '已全部标记为已读'})

    # ========================================================================
    # 向量化 API
    # ========================================================================

    def _api_embed(self) -> None:
        """触发向量化."""
        try:
            from .semantic import SemanticSearchEngine
            engine = SemanticSearchEngine(self.kb_dir)
            count = engine.embed_all()
            self._json_response({'status': 'ok', 'embedded': count})
        except (ImportError, RuntimeError, OSError) as e:
            self._json_response({'error': str(e)}, 500)

    # ========================================================================
    # 健康 API
    # ========================================================================

    def _api_health(self) -> None:
        """健康检查."""
        auth = self._get_auth_manager()
        self._json_response({
            'status': 'ok',
            'kb': str(self.kb_dir),
            'auth_enabled': auth.is_enabled(),
            'current_user': self._get_current_username(),
        })

    # ========================================================================
    # 阶段六：AI 问答 API（多轮对话）
    # ========================================================================

    def _api_qa_ask(self) -> None:
        """AI 问答（多轮对话）."""
        data = self._read_json_body()
        question = data.get('question', '').strip()
        if not question:
            self._json_response({'error': '问题不能为空'}, 400)
            return
        session_id = data.get('session_id', f"user-{self._get_current_username()}")
        llm_config = data.get('llm_config')  # 可选
        try:
            from .ai_helper import QAEngine
            engine = QAEngine(self.kb_dir)
            result = engine.ask(question, session_id=session_id, llm_config=llm_config)
            # 记录审计
            from .audit import AuditLogger
            AuditLogger(self.kb_dir).log('qa_ask', question, user=self._get_current_username(),
                                          detail=f"mode={result.get('mode')}")
            self._json_response(result)
        except Exception as e:
            self._json_response({'error': f'问答失败: {str(e)}'}, 500)

    def _api_qa_history(self, params: Dict) -> None:
        """获取对话历史."""
        session_id = params.get('session_id', [f"user-{self._get_current_username()}"])[0]
        from .ai_helper import QAEngine
        engine = QAEngine(self.kb_dir)
        history = engine._load_history(session_id)
        self._json_response({'session_id': session_id, 'history': history, 'count': len(history)})

    def _api_qa_clear(self) -> None:
        """清空对话历史."""
        data = self._read_json_body()
        session_id = data.get('session_id', f"user-{self._get_current_username()}")
        from .ai_helper import QAEngine
        engine = QAEngine(self.kb_dir)
        if engine.clear_history(session_id):
            self._json_response({'status': 'ok', 'message': '对话历史已清空'})
        else:
            self._json_response({'error': '清空失败'}, 500)

    # ========================================================================
    # 阶段六：内容去重 API
    # ========================================================================

    def _api_duplicates_list(self, params: Dict) -> None:
        """全局重复内容列表."""
        threshold = float(params.get('threshold', ['0.7'])[0])
        from .ai_helper import DuplicateDetector
        detector = DuplicateDetector(self.kb_dir)
        duplicates = detector.find_duplicates(threshold=threshold)
        self._json_response({
            'duplicates': duplicates,
            'count': len(duplicates),
            'threshold': threshold,
        })

    def _api_atom_duplicates(self, atom_id: str, params: Dict) -> None:
        """查找与指定原子相似的内容."""
        threshold = float(params.get('threshold', ['0.7'])[0])
        from .ai_helper import DuplicateDetector
        detector = DuplicateDetector(self.kb_dir)
        duplicates = detector.find_duplicates(atom_id=atom_id, threshold=threshold)
        self._json_response({
            'atom_id': atom_id,
            'duplicates': duplicates,
            'count': len(duplicates),
        })

    def _api_duplicates_merge(self) -> None:
        """合并重复原子."""
        data = self._read_json_body()
        primary_id = data.get('primary', '')
        secondary_id = data.get('secondary', '')
        strategy = data.get('strategy', 'append')
        if not primary_id or not secondary_id:
            self._json_response({'error': '必须指定 primary 和 secondary'}, 400)
            return
        from .ai_helper import DuplicateDetector
        from .audit import AuditLogger
        detector = DuplicateDetector(self.kb_dir)
        with self._write_lock:
            result = detector.merge_atoms(primary_id, secondary_id, strategy)
            if result.get('success'):
                AuditLogger(self.kb_dir).log('merge', f"{secondary_id} -> {primary_id}",
                                              user=self._get_current_username())
        self._json_response(result)

    # ========================================================================
    # 阶段六：知识质检 API
    # ========================================================================

    def _api_quality_check(self) -> None:
        """执行知识质检."""
        from .ai_helper import QualityChecker
        checker = QualityChecker(self.kb_dir)
        result = checker.check_all()
        self._json_response(result)

    # ========================================================================
    # 阶段六：敏感信息脱敏 API
    # ========================================================================

    def _api_sensitive_detect(self) -> None:
        """检测文本中的敏感信息."""
        data = self._read_json_body()
        text = data.get('text', '')
        if not text:
            self._json_response({'error': '文本不能为空'}, 400)
            return
        from .ai_helper import SensitiveInfoMasker
        detections = SensitiveInfoMasker.detect(text)
        self._json_response({'detections': detections, 'count': len(detections)})

    def _api_sensitive_mask(self) -> None:
        """脱敏文本中的敏感信息."""
        data = self._read_json_body()
        text = data.get('text', '')
        if not text:
            self._json_response({'error': '文本不能为空'}, 400)
            return
        from .ai_helper import SensitiveInfoMasker
        masked = SensitiveInfoMasker.mask(text)
        self._json_response({'original_length': len(text), 'masked': masked})

    # ========================================================================
    # 阶段六：分享外链 API
    # ========================================================================

    def _api_share_create(self) -> None:
        """创建分享外链."""
        data = self._read_json_body()
        atom_id = data.get('atom_id', '')
        if not atom_id:
            self._json_response({'error': 'atom_id 不能为空'}, 400)
            return
        expires_in_days = int(data.get('expires_in_days', 7))
        password = data.get('password') or None
        max_views = int(data.get('max_views', 0))
        from .ai_helper import ShareLinkManager
        from .audit import AuditLogger
        with self._write_lock:
            mgr = ShareLinkManager(self.kb_dir)
            link = mgr.create_link(atom_id, expires_in_days=expires_in_days,
                                    password=password, max_views=max_views)
            AuditLogger(self.kb_dir).log('share_create', atom_id,
                                          user=self._get_current_username(),
                                          detail=f"token={link['token']}")
        # 返回完整访问 URL
        link['url'] = f"/share.html?token={link['token']}"
        self._json_response({'status': 'ok', 'link': link})

    def _api_share_list(self) -> None:
        """分享外链列表."""
        from .ai_helper import ShareLinkManager
        mgr = ShareLinkManager(self.kb_dir)
        links = mgr.list_links()
        # 补充完整 URL
        for link in links:
            link['url'] = f"/share.html?token={link.get('token', '')}"
        self._json_response({'links': links, 'count': len(links)})

    def _api_share_revoke(self, token: str) -> None:
        """回收分享外链."""
        from .ai_helper import ShareLinkManager
        from .audit import AuditLogger
        with self._write_lock:
            mgr = ShareLinkManager(self.kb_dir)
            if mgr.revoke_link(token):
                AuditLogger(self.kb_dir).log('share_revoke', token,
                                              user=self._get_current_username())
                self._json_response({'status': 'ok', 'message': '链接已回收'})
            else:
                self._json_response({'error': '链接不存在'}, 404)

    def _api_share_access(self, token: str, params: Dict) -> None:
        """访问分享外链（公开端点，无需登录）."""
        password = params.get('password', [''])[0]
        from .ai_helper import ShareLinkManager
        mgr = ShareLinkManager(self.kb_dir)
        result = mgr.access_link(token, password=password or None)
        if result.get('success'):
            self._json_response(result)
        else:
            self._json_response({'error': result.get('error', '访问失败')}, 403)

    # ========================================================================
    # 阶段六：Webhook 通知 API
    # ========================================================================

    def _api_webhook_list(self) -> None:
        """Webhook 列表."""
        from .ai_helper import WebhookNotifier
        notifier = WebhookNotifier(self.kb_dir)
        webhooks = notifier.list_webhooks()
        self._json_response({'webhooks': webhooks, 'count': len(webhooks)})

    def _api_webhook_add(self) -> None:
        """添加 Webhook."""
        data = self._read_json_body()
        name = data.get('name', '')
        platform = data.get('platform', 'custom')
        url = data.get('url', '')
        events = data.get('events', ['all'])
        secret = data.get('secret', '')
        if not name or not url:
            self._json_response({'error': '名称和 URL 不能为空'}, 400)
            return
        if platform not in ('wechat', 'dingtalk', 'feishu', 'custom'):
            self._json_response({'error': '不支持的平台'}, 400)
            return
        from .ai_helper import WebhookNotifier
        from .audit import AuditLogger
        with self._write_lock:
            notifier = WebhookNotifier(self.kb_dir)
            result = notifier.add_webhook(name, platform, url, events, secret)
            AuditLogger(self.kb_dir).log('webhook_add', name,
                                          user=self._get_current_username(),
                                          detail=f"platform={platform}")
        self._json_response(result)

    def _api_webhook_remove(self, webhook_id: str) -> None:
        """删除 Webhook."""
        from .ai_helper import WebhookNotifier
        with self._write_lock:
            notifier = WebhookNotifier(self.kb_dir)
            if notifier.remove_webhook(webhook_id):
                self._json_response({'status': 'ok', 'message': 'Webhook 已删除'})
            else:
                self._json_response({'error': 'Webhook 不存在'}, 404)

    def _api_webhook_test(self) -> None:
        """测试 Webhook 发送."""
        from .ai_helper import WebhookNotifier
        notifier = WebhookNotifier(self.kb_dir)
        result = notifier.notify(
            event='test',
            title='测试通知',
            message=f'这是一条来自 LLM-Wiki 的测试通知，发送时间: {time.strftime("%Y-%m-%d %H:%M:%S")}',
        )
        self._json_response(result)

    # ========================================================================
    # 阶段六：协同编辑锁 API
    # ========================================================================

    def _api_atom_lock(self, atom_id: str) -> None:
        """获取编辑锁（标记当前用户正在编辑）."""
        username = self._get_current_username()
        lock_path = self.kb_dir / '.llm-wiki' / 'edit-locks.json'
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            try:
                locks = json.loads(lock_path.read_text(encoding='utf-8')) if lock_path.exists() else {}
            except json.JSONDecodeError:
                locks = {}
            # 检查是否被其他用户锁定
            existing = locks.get(atom_id)
            if existing and existing.get('user') != username:
                # 检查锁是否过期（30 分钟）
                lock_time = existing.get('timestamp', '')
                try:
                    from datetime import datetime, timedelta
                    lock_dt = datetime.fromisoformat(lock_time)
                    if datetime.now() - lock_dt < timedelta(minutes=30):
                        self._json_response({
                            'error': f'原子正被 {existing.get("user")} 编辑中',
                            'locked_by': existing.get('user'),
                            'locked_at': lock_time,
                        }, 409)
                        return
                except (ValueError, TypeError):
                    pass
            # 设置锁
            from datetime import datetime
            locks[atom_id] = {
                'user': username,
                'timestamp': datetime.now().isoformat(),
            }
            lock_path.write_text(json.dumps(locks, ensure_ascii=False, indent=2), encoding='utf-8')
        self._json_response({'status': 'ok', 'message': f'已锁定原子: {atom_id}', 'user': username})

    def _api_atom_unlock(self, atom_id: str) -> None:
        """释放编辑锁."""
        username = self._get_current_username()
        lock_path = self.kb_dir / '.llm-wiki' / 'edit-locks.json'
        with self._write_lock:
            try:
                locks = json.loads(lock_path.read_text(encoding='utf-8')) if lock_path.exists() else {}
            except json.JSONDecodeError:
                locks = {}
            if atom_id in locks:
                # 只允许锁定者或 admin 释放
                if locks[atom_id].get('user') == username or self._get_current_role() == 'admin':
                    del locks[atom_id]
                    lock_path.write_text(json.dumps(locks, ensure_ascii=False, indent=2), encoding='utf-8')
                    self._json_response({'status': 'ok', 'message': f'已释放锁: {atom_id}'})
                else:
                    self._json_response({'error': '只能释放自己持有的锁'}, 403)
            else:
                self._json_response({'status': 'ok', 'message': '锁不存在，无需释放'})

    # ========================================================================
    # 静态文件服务
    # ========================================================================

    def _serve_static(self, path: str) -> None:
        """提供静态文件服务.

        Args:
            path: 请求路径
        """
        # 根路径返回 index.html
        if path == '/' or path == '':
            path = '/index.html'
        # 防止路径遍历攻击
        path = path.lstrip('/')
        # 安全检查：禁止 .. 路径
        if '..' in path:
            self._json_response({'error': 'Forbidden'}, 403)
            return
        # 先查知识库 views/，再查项目根 views/
        file_path = self.kb_views_dir / path
        if not file_path.exists() or not file_path.is_file():
            file_path = self.static_dir / path
        # 如果是目录，尝试 index.html
        if file_path.is_dir():
            file_path = file_path / 'index.html'
        if not file_path.exists() or not file_path.is_file():
            # SPA 路由回退：返回 index.html
            if not path.startswith('api/'):
                index_path = self.static_dir / 'index.html'
                if index_path.exists():
                    self._serve_file(index_path)
                    return
            self._json_response({'error': 'Not found'}, 404)
            return
        self._serve_file(file_path)

    def _serve_file(self, file_path: Path) -> None:
        """发送静态文件."""
        content_type = self._get_content_type(file_path.suffix)
        # PWA manifest.json 应使用 manifest+json MIME 类型
        if file_path.name == 'manifest.json':
            content_type = 'application/manifest+json; charset=utf-8'
        try:
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except (FileNotFoundError, PermissionError):
            self._json_response({'error': 'File not found'}, 404)

    def _get_content_type(self, suffix: str) -> str:
        """根据扩展名获取 Content-Type."""
        types = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.webmanifest': 'application/manifest+json; charset=utf-8',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.pdf': 'application/pdf',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.map': 'application/json',
        }
        return types.get(suffix.lower(), 'application/octet-stream')

    # ========================================================================
    # OCR API（PLAN-004 Phase 3）
    # ========================================================================

    def _api_ocr_submit(self) -> None:
        """提交 OCR 任务."""
        from .api.ocr_api import OCRAPIHandler
        data = self._read_json_body()
        username = self._get_current_username()
        handler = OCRAPIHandler(self.storage)
        result, status = handler.submit(data, user_id=username)
        self._json_response(result, status)

    def _api_ocr_get_task(self, task_id: str) -> None:
        """查询 OCR 任务状态."""
        from .api.ocr_api import OCRAPIHandler
        handler = OCRAPIHandler(self.storage)
        try:
            numeric_id = int(task_id)
            result, status = handler.get_task(numeric_id)
        except ValueError:
            result, status = {'error': '无效的 task_id'}, 400
        self._json_response(result, status)

    def _api_ocr_get_by_asset(self, asset_id: str) -> None:
        """查询资产的 OCR 结果."""
        from .api.ocr_api import OCRAPIHandler
        handler = OCRAPIHandler(self.storage)
        try:
            numeric_id = int(asset_id)
            result, status = handler.get_by_asset(numeric_id)
        except ValueError:
            result, status = {'error': '无效的 asset_id'}, 400
        self._json_response(result, status)

    # ========================================================================
    # Preview API（PLAN-004 Phase 3）
    # ========================================================================

    def _api_preview_get(self, atom_id: str) -> None:
        """获取原子预览 URL."""
        from .api.preview_api import PreviewAPIHandler
        handler = PreviewAPIHandler(self.storage)
        params = parse_qs(urlparse(self.path).query)
        fmt = params.get('format', ['html'])[0]
        mime_type = params.get('mime_type', [None])[0]
        result, status = handler.get_preview(atom_id, format=fmt, source_mime_type=mime_type)
        self._json_response(result, status)

    def _api_preview_cache(self, atom_id: str) -> None:
        """获取预览缓存状态."""
        from .api.preview_api import PreviewAPIHandler
        handler = PreviewAPIHandler(self.storage)
        params = parse_qs(urlparse(self.path).query)
        fmt = params.get('format', ['html'])[0]
        result, status = handler.get_cache(atom_id, format=fmt)
        self._json_response(result, status)

    # ========================================================================
    # 配置 API（PLAN-004 Phase 3）
    # ========================================================================

    def _api_config_mode(self) -> None:
        """获取当前存储模式."""
        mode = self.storage.mode if self.storage else 'file'
        self._json_response({
            'mode': mode,
            'supports_rls': self.storage.supports_rls if self.storage else False,
            'description': '数据库模式 (PostgreSQL)' if mode == 'db' else '文件模式 (Markdown)',
        })

    def _api_config_status(self) -> None:
        """获取数据库连接状态."""
        if not self.storage or self.storage.mode != 'db':
            self._json_response({
                'mode': 'file',
                'connected': False,
                'message': '当前为文件模式，无数据库连接',
            })
            return
        # db_mode: 检查连接状态
        try:
            if hasattr(self.storage, 'db_manager') and hasattr(self.storage.db_manager, 'is_connected'):
                connected = _run_async(self.storage.db_manager.is_connected())
            else:
                connected = False
            self._json_response({
                'mode': 'db',
                'connected': connected,
                'type': 'postgresql',
            })
        except Exception as e:
            self._json_response({
                'mode': 'db',
                'connected': False,
                'error': str(e),
            })

    def _api_config_sso(self) -> None:
        """获取 SSO 配置信息（仅 admin 可访问）."""
        user = getattr(self, '_current_user', None)
        if not user or user.get('role', 'guest') != 'admin':
            self._json_response({'error': '仅 admin 可访问此端点'}, 403)
            return

        auth = self._get_auth_manager()
        if not auth.is_sso_enabled():
            self._json_response({
                'enabled': False,
                'endpoint': '',
                'providers': [],
            })
            return

        # 获取 SSO 提供商信息
        provider = auth._sso_provider
        endpoint = ''
        if hasattr(provider, 'config') and hasattr(provider.config, 'endpoint'):
            endpoint = provider.config.endpoint or ''
        elif hasattr(provider, 'endpoint'):
            endpoint = provider.endpoint or ''

        self._json_response({
            'enabled': True,
            'endpoint': endpoint,
            'providers': [
                {
                    'name': 'casdoor',
                    'display_name': '企业 SSO',
                    'login_url': '/api/auth/sso/login',
                }
            ],
        })

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _get_auth_manager(self):
        """获取 AuthManager 实例."""
        from .auth import AuthManager
        return AuthManager(self.kb_dir)

    def _resolve_atom_path(self, atom_id: str) -> Optional[Path]:
        """解析原子 ID 为文件路径.

        Args:
            atom_id: 原子 ID（可能是路径、文件名等）

        Returns:
            原子文件路径，找不到返回 None
        """
        # 尝试多种路径格式
        candidates = [
            self.kb_dir / f"{atom_id}.md",
            self.kb_dir / atom_id,
            self.kb_dir / f"{atom_id}",
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c
        return None

    def _load_atoms(self, by_type: Optional[str] = None, limit: int = 100) -> list:
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
                'author': fm.get('author', ''),
                'created': fm.get('created', ''),
                'updated': fm.get('updated', ''),
            })
            if len(atoms) >= limit:
                break
        return atoms

    def _read_json_body(self) -> Dict:
        """读取 JSON 请求体."""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            return json.loads(body) if body else {}
        except json.JSONDecodeError:
            return {}

    def _json_response(self, data: Any, status: int = 200) -> None:
        """发送 JSON 响应."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self._send_cors_headers()
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self) -> None:
        """发送 CORS 头."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def log_message(self, format: str, *args) -> None:
        """简化日志输出."""
        pass  # 静默日志，避免污染输出
