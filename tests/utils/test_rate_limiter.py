"""rate_limiter 模块单元测试

测试范围：
1. RateLimiter 类的滑动窗口逻辑
2. IPWhitelist 类
3. get_rate_limiter 全局实例管理
4. rate_limit 装饰器
5. get_ip_whitelist 全局实例
6. 并发请求处理
"""

import time
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# 导入被测模块
# ---------------------------------------------------------------------------
try:
    from lib.utils.rate_limiter import (
        RateLimiter,
        IPWhitelist,
        get_rate_limiter,
        rate_limit,
        get_ip_whitelist,
    )
except ImportError as exc:
    pytest.skip(f"Cannot import rate_limiter: {exc}", allow_module_level=True)


# ============================================================================
# RateLimiter 测试
# ============================================================================


class TestRateLimiter:
    """RateLimiter 类测试"""

    def test_initial_state(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 60

    def test_first_request_allowed(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        allowed, meta = limiter.is_allowed('client1')
        assert allowed is True
        assert meta['remaining'] == 4
        assert meta['limit'] == 5
        assert meta['retry_after'] == 0

    def test_multiple_requests_within_limit(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for i in range(5):
            allowed, meta = limiter.is_allowed('client1')
            assert allowed is True
        assert meta['remaining'] == 0

    def test_exceeds_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for i in range(3):
            limiter.is_allowed('client1')
        allowed, meta = limiter.is_allowed('client1')
        assert allowed is False
        assert meta['remaining'] == 0
        assert meta['retry_after'] > 0

    def test_different_clients_independent(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed('client1')
        limiter.is_allowed('client1')
        # client1 已达上限
        allowed1, _ = limiter.is_allowed('client1')
        assert allowed1 is False
        # client2 仍可请求
        allowed2, _ = limiter.is_allowed('client2')
        assert allowed2 is True

    def test_metadata_structure(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        allowed, meta = limiter.is_allowed('client1')
        assert 'limit' in meta
        assert 'remaining' in meta
        assert 'reset' in meta
        assert 'retry_after' in meta

    def test_remaining_decrements(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for i in range(5):
            _, meta = limiter.is_allowed('client1')
            assert meta['remaining'] == 4 - i

    def test_reset_specific_client(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed('client1')
        limiter.is_allowed('client1')
        allowed, _ = limiter.is_allowed('client1')
        assert allowed is False
        limiter.reset('client1')
        allowed, _ = limiter.is_allowed('client1')
        assert allowed is True

    def test_reset_all_clients(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed('client1')
        limiter.is_allowed('client1')
        limiter.is_allowed('client2')
        limiter.is_allowed('client2')
        limiter.reset()
        allowed1, _ = limiter.is_allowed('client1')
        allowed2, _ = limiter.is_allowed('client2')
        assert allowed1 is True
        assert allowed2 is True

    def test_window_expiry(self):
        """测试时间窗口过期后请求重新允许"""
        limiter = RateLimiter(max_requests=1, window_seconds=1)
        limiter.is_allowed('client1')
        allowed, _ = limiter.is_allowed('client1')
        assert allowed is False
        # 等待窗口过期
        time.sleep(1.1)
        allowed, _ = limiter.is_allowed('client1')
        assert allowed is True

    def test_cleanup_interval(self):
        """测试定期清理机制"""
        limiter = RateLimiter(max_requests=100, window_seconds=60, cleanup_interval=2)
        # 触发两次请求，第二次会触发清理
        limiter.is_allowed('client1')
        limiter.is_allowed('client1')
        # 清理后应仍能正常工作
        allowed, _ = limiter.is_allowed('client1')
        assert allowed is True

    def test_retry_after_calculation(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        limiter.is_allowed('client1')
        allowed, meta = limiter.is_allowed('client1')
        assert allowed is False
        assert meta['retry_after'] > 0
        assert meta['retry_after'] <= 60

    def test_reset_time_calculation(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        _, meta = limiter.is_allowed('client1')
        assert meta['reset'] > int(time.time())


# ============================================================================
# IPWhitelist 测试
# ============================================================================


class TestIPWhitelist:
    """IPWhitelist 类测试"""

    def test_add_and_check(self):
        wl = IPWhitelist()
        wl.add('192.168.1.1')
        assert wl.is_whitelisted('192.168.1.1') is True
        assert wl.is_whitelisted('10.0.0.1') is False

    def test_remove(self):
        wl = IPWhitelist()
        wl.add('192.168.1.1')
        wl.remove('192.168.1.1')
        assert wl.is_whitelisted('192.168.1.1') is False

    def test_remove_nonexistent(self):
        wl = IPWhitelist()
        wl.remove('10.0.0.1')  # 不应报错

    def test_clear(self):
        wl = IPWhitelist()
        wl.add('192.168.1.1')
        wl.add('10.0.0.1')
        wl.clear()
        assert wl.is_whitelisted('192.168.1.1') is False
        assert wl.is_whitelisted('10.0.0.1') is False

    def test_empty_whitelist(self):
        wl = IPWhitelist()
        assert wl.is_whitelisted('any_ip') is False

    def test_add_duplicate(self):
        wl = IPWhitelist()
        wl.add('192.168.1.1')
        wl.add('192.168.1.1')  # 重复添加
        assert wl.is_whitelisted('192.168.1.1') is True
        wl.remove('192.168.1.1')
        assert wl.is_whitelisted('192.168.1.1') is False


# ============================================================================
# get_rate_limiter 测试
# ============================================================================


class TestGetRateLimiter:
    """get_rate_limiter 全局实例管理测试"""

    def test_creates_new_limiter(self):
        limiter = get_rate_limiter('test_new', max_requests=50, window_seconds=30)
        assert limiter.max_requests == 50
        assert limiter.window_seconds == 30

    def test_returns_same_limiter(self):
        limiter1 = get_rate_limiter('test_same')
        limiter2 = get_rate_limiter('test_same')
        assert limiter1 is limiter2

    def test_different_names_different_limiters(self):
        limiter1 = get_rate_limiter('test_diff1')
        limiter2 = get_rate_limiter('test_diff2')
        assert limiter1 is not limiter2


# ============================================================================
# rate_limit 装饰器测试
# ============================================================================


class TestRateLimitDecorator:
    """rate_limit 装饰器测试"""

    def test_allowed_request(self):
        """请求在限制内时正常执行"""

        @rate_limit(max_requests=10, window_seconds=60, limiter_name='test_decorator_ok')
        def handle_request(self):
            return "ok"

        handler = MagicMock()
        handler.client_address = ('127.0.0.1',)
        result = handle_request(handler)
        assert result == "ok"

    def test_rate_limited_request(self):
        """超过限制时返回 None"""

        @rate_limit(max_requests=1, window_seconds=60, limiter_name='test_decorator_limited')
        def handle_request(self):
            return "ok"

        handler = MagicMock()
        handler.client_address = ('127.0.0.1',)
        # 第一次请求通过
        result1 = handle_request(handler)
        assert result1 == "ok"
        # 第二次请求被限流
        result2 = handle_request(handler)
        assert result2 is None

    def test_custom_key_func(self):
        """自定义客户端标识函数"""

        @rate_limit(
            max_requests=1,
            window_seconds=60,
            key_func=lambda self, *args, **kwargs: self.user_id,
            limiter_name='test_decorator_custom_key'
        )
        def handle_request(self):
            return "ok"

        handler = MagicMock()
        handler.user_id = 'user123'
        result = handle_request(handler)
        assert result == "ok"

    def test_x_forwarded_for(self):
        """使用 X-Forwarded-For 获取真实 IP"""

        @rate_limit(max_requests=10, window_seconds=60, limiter_name='test_decorator_xff')
        def handle_request(self):
            return "ok"

        handler = MagicMock()
        handler.client_address = ('10.0.0.1',)
        handler.headers = {'X-Forwarded-For': '203.0.113.1, 70.41.3.18'}
        result = handle_request(handler)
        assert result == "ok"

    def test_rate_limited_with_send_response(self):
        """被限流时调用 send_response 返回 429"""

        @rate_limit(max_requests=1, window_seconds=60, limiter_name='test_decorator_429')
        def handle_request(self):
            return "ok"

        handler = MagicMock()
        handler.client_address = ('127.0.0.1',)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()

        handle_request(handler)  # 第一次通过
        result = handle_request(handler)  # 第二次被限流
        assert result is None
        handler.send_response.assert_called_with(429)


# ============================================================================
# get_ip_whitelist 测试
# ============================================================================


class TestGetIpWhitelist:
    """get_ip_whitelist 全局实例测试"""

    def test_returns_whitelist_instance(self):
        wl = get_ip_whitelist()
        assert isinstance(wl, IPWhitelist)

    def test_returns_same_instance(self):
        wl1 = get_ip_whitelist()
        wl2 = get_ip_whitelist()
        assert wl1 is wl2
