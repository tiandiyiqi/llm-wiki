#!/usr/bin/env python3
"""独立测试速率限制功能."""

import time
from threading import Lock
from collections import defaultdict
from typing import Dict, Tuple, Optional


class RateLimiter:
    """速率限制器（独立版本用于测试）."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, client_id: str) -> Tuple[bool, Dict]:
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
                self._requests[client_id].append(current_time)
                request_count += 1

        metadata = {
            'limit': self.max_requests,
            'remaining': max(0, self.max_requests - request_count),
        }

        return is_allowed, metadata


def test_rate_limit_basic():
    print("\n=== 测试基本速率限制 ===")
    limiter = RateLimiter(max_requests=5, window_seconds=10)

    # 前 5 次应该被允许
    for i in range(5):
        is_allowed, metadata = limiter.is_allowed('client_1')
        assert is_allowed, f"请求 {i+1} 应该被允许"
        print(f"✅ 请求 {i+1} 通过，剩余 {metadata['remaining']}")

    # 第 6 次应该被拒绝
    is_allowed, metadata = limiter.is_allowed('client_1')
    assert not is_allowed, "第 6 次应该被拒绝"
    print(f"✅ 速率限制生效，被拒绝")


def test_rate_limit_different_clients():
    print("\n=== 测试不同客户端 ===")
    limiter = RateLimiter(max_requests=3, window_seconds=5)

    # 客户端 A 的请求
    for i in range(3):
        is_allowed, _ = limiter.is_allowed('client_A')
        assert is_allowed

    # 客户端 A 应该被拒绝
    is_allowed, _ = limiter.is_allowed('client_A')
    assert not is_allowed
    print("✅ 客户端 A 速率限制生效")

    # 客户端 B 应该仍然可以访问
    is_allowed, _ = limiter.is_allowed('client_B')
    assert is_allowed
    print("✅ 客户端 B 不受影响")


def test_rate_limit_window():
    print("\n=== 测试时间窗口 ===")
    limiter = RateLimiter(max_requests=2, window_seconds=2)

    # 2 次请求
    limiter.is_allowed('client_1')
    limiter.is_allowed('client_1')

    # 应该被拒绝
    is_allowed, _ = limiter.is_allowed('client_1')
    assert not is_allowed
    print("✅ 速率限制生效")

    # 等待窗口过期
    print("等待 2.5 秒...")
    time.sleep(2.5)

    # 应该可以再次访问
    is_allowed, _ = limiter.is_allowed('client_1')
    assert is_allowed
    print("✅ 时间窗口过期后恢复访问")


def test_rate_limit_remaining():
    print("\n=== 测试剩余请求数 ===")
    limiter = RateLimiter(max_requests=10, window_seconds=60)

    # 第一次请求
    _, metadata = limiter.is_allowed('client_1')
    assert metadata['remaining'] == 9

    # 第二次请求
    _, metadata = limiter.is_allowed('client_1')
    assert metadata['remaining'] == 8
    print("✅ 剩余请求数正确更新")


def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("速率限制功能测试（独立版本）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        test_rate_limit_basic()
        test_rate_limit_different_clients()
        test_rate_limit_window()
        test_rate_limit_remaining()

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("✅ 所有测试通过！")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())