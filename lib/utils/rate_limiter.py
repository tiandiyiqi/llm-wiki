"""速率限制中间件.

实现 API 请求速率限制，防止滥用和 DDoS 攻击。
"""

import time
import logging
from collections import defaultdict
from threading import Lock
from typing import Callable, Dict, Optional, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器.

    使用滑动窗口算法实现速率限制。
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        cleanup_interval: int = 1000
    ):
        """初始化速率限制器.

        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口大小（秒）
            cleanup_interval: 清理间隔（请求数）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.cleanup_interval = cleanup_interval

        # 请求记录：{client_id: [timestamp1, timestamp2, ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()
        self._request_count = 0

    def is_allowed(self, client_id: str) -> Tuple[bool, Dict]:
        """检查客户端是否被允许访问.

        Args:
            client_id: 客户端标识（IP 地址或用户 ID）

        Returns:
            (是否允许, 元数据字典)
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds

        with self._lock:
            # 清理过期记录
            self._requests[client_id] = [
                ts for ts in self._requests[client_id]
                if ts > window_start
            ]

            # 检查请求数
            request_count = len(self._requests[client_id])
            is_allowed = request_count < self.max_requests

            if is_allowed:
                # 记录本次请求
                self._requests[client_id].append(current_time)
                request_count += 1

            # 定期清理所有客户端记录
            self._request_count += 1
            if self._request_count >= self.cleanup_interval:
                self._cleanup_all(window_start)
                self._request_count = 0

        # 计算元数据
        retry_after = 0
        if not is_allowed:
            # 计算最早请求的过期时间
            oldest_request = min(self._requests[client_id]) if self._requests[client_id] else current_time
            retry_after = int(oldest_request + self.window_seconds - current_time) + 1

        metadata = {
            'limit': self.max_requests,
            'remaining': max(0, self.max_requests - request_count),
            'reset': int(current_time + self.window_seconds),
            'retry_after': retry_after if not is_allowed else 0,
        }

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for client {client_id}: "
                f"{request_count} requests in {self.window_seconds}s"
            )

        return is_allowed, metadata

    def _cleanup_all(self, window_start: float) -> None:
        """清理所有客户端的过期记录.

        Args:
            window_start: 时间窗口起始时间
        """
        expired_clients = []

        for client_id, timestamps in self._requests.items():
            # 清理过期时间戳
            self._requests[client_id] = [
                ts for ts in timestamps if ts > window_start
            ]

            # 标记空记录的客户端
            if not self._requests[client_id]:
                expired_clients.append(client_id)

        # 删除空记录
        for client_id in expired_clients:
            del self._requests[client_id]

        logger.debug(f"Cleaned up {len(expired_clients)} expired client records")

    def reset(self, client_id: Optional[str] = None) -> None:
        """重置速率限制.

        Args:
            client_id: 客户端 ID，None 表示重置所有
        """
        with self._lock:
            if client_id:
                self._requests.pop(client_id, None)
                logger.info(f"Rate limit reset for client {client_id}")
            else:
                self._requests.clear()
                logger.info("Rate limit reset for all clients")


# 全局速率限制器实例
_global_limiters: Dict[str, RateLimiter] = {}
_global_lock = Lock()


def get_rate_limiter(
    name: str = 'default',
    max_requests: int = 100,
    window_seconds: int = 60
) -> RateLimiter:
    """获取或创建速率限制器实例.

    Args:
        name: 限制器名称
        max_requests: 最大请求数
        window_seconds: 时间窗口

    Returns:
        速率限制器实例
    """
    with _global_lock:
        if name not in _global_limiters:
            _global_limiters[name] = RateLimiter(
                max_requests=max_requests,
                window_seconds=window_seconds
            )
            logger.info(f"Created rate limiter '{name}': {max_requests} requests per {window_seconds}s")
        return _global_limiters[name]


def rate_limit(
    max_requests: int = 100,
    window_seconds: int = 60,
    key_func: Optional[Callable] = None,
    limiter_name: str = 'default'
) -> Callable:
    """速率限制装饰器.

    使用方式：
        @rate_limit(max_requests=100, window_seconds=60)
        def handle_api_request(self, *args, **kwargs):
            pass

    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口大小（秒）
        key_func: 客户端标识函数，默认使用 IP 地址
        limiter_name: 限制器名称

    Returns:
        装饰器函数
    """
    limiter = get_rate_limiter(limiter_name, max_requests, window_seconds)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self: any, *args, **kwargs) -> any:
            # 获取客户端标识
            if key_func:
                client_id = key_func(self, *args, **kwargs)
            else:
                # 默认使用 IP 地址
                client_id = getattr(self, 'client_address', ('unknown',))[0]
                if hasattr(self, 'headers'):
                    # 尝试从 X-Forwarded-For 获取真实 IP
                    forwarded = self.headers.get('X-Forwarded-For', '')
                    if forwarded:
                        client_id = forwarded.split(',')[0].strip()

            # 检查速率限制
            is_allowed, metadata = limiter.is_allowed(client_id)

            # 设置响应头
            if hasattr(self, 'send_header'):
                self.send_header('X-RateLimit-Limit', str(metadata['limit']))
                self.send_header('X-RateLimit-Remaining', str(metadata['remaining']))
                self.send_header('X-RateLimit-Reset', str(metadata['reset']))

            if not is_allowed:
                # 返回 429 错误
                logger.warning(f"Rate limit exceeded for {client_id}")

                if hasattr(self, 'send_response'):
                    self.send_response(429)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Retry-After', str(metadata['retry_after']))
                    self.end_headers()

                    error_response = {
                        'error': 'Too Many Requests',
                        'message': f"Rate limit exceeded. Retry after {metadata['retry_after']} seconds.",
                        'retry_after': metadata['retry_after']
                    }

                    import json
                    self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return None

            # 执行原函数
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


class IPWhitelist:
    """IP 白名单管理.

    白名单中的 IP 不受速率限制。
    """

    def __init__(self):
        """初始化 IP 白名单."""
        self._whitelist: set = set()
        self._lock = Lock()

    def add(self, ip: str) -> None:
        """添加 IP 到白名单.

        Args:
            ip: IP 地址
        """
        with self._lock:
            self._whitelist.add(ip)
            logger.info(f"Added IP to whitelist: {ip}")

    def remove(self, ip: str) -> None:
        """从白名单移除 IP.

        Args:
            ip: IP 地址
        """
        with self._lock:
            self._whitelist.discard(ip)
            logger.info(f"Removed IP from whitelist: {ip}")

    def is_whitelisted(self, ip: str) -> bool:
        """检查 IP 是否在白名单中.

        Args:
            ip: IP 地址

        Returns:
            是否在白名单中
        """
        with self._lock:
            return ip in self._whitelist

    def clear(self) -> None:
        """清空白名单."""
        with self._lock:
            self._whitelist.clear()
            logger.info("Cleared IP whitelist")


# 全局 IP 白名单
_global_whitelist = IPWhitelist()


def get_ip_whitelist() -> IPWhitelist:
    """获取全局 IP 白名单.

    Returns:
        IP 白名单实例
    """
    return _global_whitelist
