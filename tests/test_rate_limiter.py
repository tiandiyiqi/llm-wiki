#!/usr/bin/env python3
"""速率限制功能测试.

测试覆盖：
- 基本速率限制功能
- 不同客户端的独立计数
- 时间窗口过期恢复
- 剩余请求数跟踪
- 重试时间计算
- IP 白名单管理
- 全局限制器单例模式
- 重置功能
"""

import time
import pytest

from lib.utils.rate_limiter import (
    RateLimiter,
    get_rate_limiter,
    rate_limit,
    IPWhitelist,
    get_ip_whitelist,
)


class TestRateLimiterBasic:
    """测试基本速率限制功能."""

    def test_basic_rate_limiting(self):
        """测试基本速率限制."""
        limiter = RateLimiter(max_requests=5, window_seconds=10)

        # 前 5 次应该被允许
        for i in range(5):
            is_allowed, metadata = limiter.is_allowed('client_1')
            assert is_allowed, f"请求 {i+1} 应该被允许"
            assert metadata['remaining'] == 5 - i - 1

        # 第 6 次应该被拒绝
        is_allowed, metadata = limiter.is_allowed('client_1')
        assert not is_allowed, "第 6 次应该被拒绝"
        assert metadata['remaining'] == 0

    def test_different_clients_independent(self):
        """测试不同客户端独立计数."""
        limiter = RateLimiter(max_requests=3, window_seconds=5)

        # 客户端 A 用完配额
        for _ in range(3):
            is_allowed, _ = limiter.is_allowed('client_A')
            assert is_allowed

        # 客户端 A 应该被拒绝
        is_allowed, _ = limiter.is_allowed('client_A')
        assert not is_allowed

        # 客户端 B 应该仍然可以访问
        is_allowed, _ = limiter.is_allowed('client_B')
        assert is_allowed

    def test_window_expiration(self):
        """测试时间窗口过期后恢复访问."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # 用完配额
        limiter.is_allowed('client_1')
        limiter.is_allowed('client_1')

        # 应该被拒绝
        is_allowed, _ = limiter.is_allowed('client_1')
        assert not is_allowed

        # 等待窗口过期
        time.sleep(1.5)

        # 应该可以再次访问
        is_allowed, _ = limiter.is_allowed('client_1')
        assert is_allowed

    def test_remaining_requests_tracking(self):
        """测试剩余请求数正确跟踪."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        # 第一次请求
        _, metadata = limiter.is_allowed('client_1')
        assert metadata['remaining'] == 9

        # 第二次请求
        _, metadata = limiter.is_allowed('client_1')
        assert metadata['remaining'] == 8

    def test_retry_after_calculation(self):
        """测试重试时间计算."""
        limiter = RateLimiter(max_requests=2, window_seconds=5)

        # 用完配额
        limiter.is_allowed('client_1')
        limiter.is_allowed('client_1')

        # 被拒绝时应该有 retry_after
        is_allowed, metadata = limiter.is_allowed('client_1')
        assert not is_allowed
        assert 'retry_after' in metadata
        assert metadata['retry_after'] > 0
        assert metadata['retry_after'] <= 5


class TestIPWhitelist:
    """测试 IP 白名单功能."""

    def test_whitelist_add_and_check(self):
        """测试添加和检查白名单."""
        whitelist = IPWhitelist()

        # 添加 IP
        whitelist.add('192.168.1.1')
        whitelist.add('10.0.0.1')

        # 检查白名单
        assert whitelist.is_whitelisted('192.168.1.1')
        assert whitelist.is_whitelisted('10.0.0.1')
        assert not whitelist.is_whitelisted('192.168.1.2')

    def test_whitelist_remove(self):
        """测试移除白名单."""
        whitelist = IPWhitelist()
        whitelist.add('192.168.1.1')

        # 移除 IP
        whitelist.remove('192.168.1.1')
        assert not whitelist.is_whitelisted('192.168.1.1')

    def test_whitelist_clear(self):
        """测试清空白名单."""
        whitelist = IPWhitelist()
        whitelist.add('192.168.1.1')
        whitelist.add('10.0.0.1')

        # 清空
        whitelist.clear()
        assert not whitelist.is_whitelisted('192.168.1.1')
        assert not whitelist.is_whitelisted('10.0.0.1')

    def test_global_whitelist_singleton(self):
        """测试全局白名单单例."""
        whitelist1 = get_ip_whitelist()
        whitelist2 = get_ip_whitelist()

        assert whitelist1 is whitelist2


class TestGlobalRateLimiter:
    """测试全局速率限制器."""

    def test_singleton_pattern(self):
        """测试单例模式."""
        limiter1 = get_rate_limiter('test_singleton', max_requests=50, window_seconds=30)
        limiter2 = get_rate_limiter('test_singleton', max_requests=100, window_seconds=60)

        # 应该是同一个实例
        assert limiter1 is limiter2
        # 使用第一次创建的参数
        assert limiter1.max_requests == 50

    def test_different_names_create_different_limiters(self):
        """测试不同名称创建不同限制器."""
        limiter1 = get_rate_limiter('test_name_1', max_requests=100, window_seconds=60)
        limiter2 = get_rate_limiter('test_name_2', max_requests=100, window_seconds=60)

        assert limiter1 is not limiter2


class TestRateLimiterReset:
    """测试速率限制器重置功能."""

    def test_reset_single_client(self):
        """测试重置单个客户端."""
        limiter = RateLimiter(max_requests=3, window_seconds=10)

        # 用完配额
        for _ in range(3):
            limiter.is_allowed('client_1')

        # 应该被拒绝
        is_allowed, _ = limiter.is_allowed('client_1')
        assert not is_allowed

        # 重置特定客户端
        limiter.reset('client_1')

        # 应该可以访问
        is_allowed, _ = limiter.is_allowed('client_1')
        assert is_allowed

    def test_reset_all_clients(self):
        """测试重置所有客户端."""
        limiter = RateLimiter(max_requests=3, window_seconds=10)

        # 两个客户端都用完配额
        for _ in range(3):
            limiter.is_allowed('client_1')
            limiter.is_allowed('client_2')

        # 都应该被拒绝
        is_allowed, _ = limiter.is_allowed('client_1')
        assert not is_allowed
        is_allowed, _ = limiter.is_allowed('client_2')
        assert not is_allowed

        # 重置所有
        limiter.reset()

        # 都应该可以访问
        is_allowed, _ = limiter.is_allowed('client_1')
        assert is_allowed
        is_allowed, _ = limiter.is_allowed('client_2')
        assert is_allowed


class TestRateLimitDecorator:
    """测试速率限制装饰器."""

    def test_decorator_basic(self):
        """测试装饰器基本功能."""
        # 创建模拟请求处理器
        class MockHandler:
            def __init__(self):
                self.client_address = ('192.168.1.1', 8080)
                self.headers = {}
                self.response_code = None
                self.response_headers = {}
                self.response_body = None
                # 模拟 wfile 对象
                self.wfile = self

            def write(self, data):
                self.response_body = data

            def send_response(self, code):
                self.response_code = code

            def send_header(self, key, value):
                self.response_headers[key] = value

            def end_headers(self):
                pass

        # 使用装饰器
        @rate_limit(max_requests=2, window_seconds=5, limiter_name='test_decorator')
        def handle_request(self):
            return "success"

        handler = MockHandler()

        # 前 2 次应该成功
        result1 = handle_request(handler)
        assert result1 == "success"

        result2 = handle_request(handler)
        assert result2 == "success"

        # 第 3 次应该返回 429
        result3 = handle_request(handler)
        assert result3 is None
        assert handler.response_code == 429