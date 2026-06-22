"""RBAC 权限缓存管理器，支持 TTL 和主动失效.

提供细粒度的权限缓存控制，确保权限变更时缓存及时清除。
特性：
- TTL 自动过期
- 标签索引（按知识库等维度批量失效）
- 按键/前缀/标签/全量多种失效策略
- LRU 淘汰 + 过期清理
- 缓存命中统计
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

# 默认缓存 TTL（5 分钟）
DEFAULT_CACHE_TTL = 300  # 秒
# 最大缓存条目数
DEFAULT_MAX_CACHE_SIZE = 10000


@dataclass
class CacheEntry:
    """缓存条目."""

    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default=0.0)
    tags: Set[str] = field(default_factory=set)

    @property
    def is_expired(self) -> bool:
        """检查是否过期."""
        if self.expires_at == 0:
            return False
        return time.time() > self.expires_at


class CacheManager:
    """缓存管理器，支持 TTL、标签和主动失效."""

    def __init__(
        self,
        ttl: int = DEFAULT_CACHE_TTL,
        max_size: int = DEFAULT_MAX_CACHE_SIZE,
    ):
        """初始化缓存管理器.

        Args:
            ttl: 默认缓存 TTL（秒）
            max_size: 最大缓存条目数
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> set of keys
        self._ttl = ttl
        self._max_size = max_size
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'invalidations': 0,
        }

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值."""
        entry = self._cache.get(key)
        if entry is None:
            self._stats['misses'] += 1
            return None

        if entry.is_expired:
            self._remove_entry(key)
            self._stats['misses'] += 1
            return None

        self._stats['hits'] += 1
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
    ) -> None:
        """设置缓存值.

        Args:
            key: 缓存键
            value: 缓存值
            ttl: TTL（秒），None 使用默认值
            tags: 标签集合（用于按标签失效）
        """
        # 检查缓存大小，淘汰过期或最旧条目
        if len(self._cache) >= self._max_size:
            self._evict_expired()
            if len(self._cache) >= self._max_size:
                oldest_key = min(
                    self._cache,
                    key=lambda k: self._cache[k].created_at
                )
                self._remove_entry(oldest_key)
                self._stats['evictions'] += 1

        # 计算过期时间
        effective_ttl = ttl if ttl is not None else self._ttl
        expires_at = time.time() + effective_ttl if effective_ttl > 0 else 0.0

        # 移除旧条目（如果存在，确保标签索引一致）
        if key in self._cache:
            self._remove_entry(key)

        # 创建新条目
        entry = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at,
            tags=tags or set(),
        )
        self._cache[key] = entry

        # 更新标签索引
        for tag in entry.tags:
            self._tag_index.setdefault(tag, set()).add(key)

    def invalidate(self, key: str) -> bool:
        """失效指定缓存条目."""
        if key in self._cache:
            self._remove_entry(key)
            self._stats['invalidations'] += 1
            logger.debug(f"Cache invalidated: {key}")
            return True
        return False

    def invalidate_by_tag(self, tag: str) -> int:
        """按标签失效所有缓存条目.

        Args:
            tag: 标签名称

        Returns:
            失效的条目数
        """
        keys = self._tag_index.get(tag, set()).copy()
        count = 0
        for key in keys:
            if self.invalidate(key):
                count += 1
        if count > 0:
            logger.info(f"Cache invalidated by tag '{tag}': {count} entries")
        return count

    def invalidate_by_prefix(self, prefix: str) -> int:
        """按前缀失效所有缓存条目.

        Args:
            prefix: 键前缀

        Returns:
            失效的条目数
        """
        keys = [k for k in self._cache if k.startswith(prefix)]
        count = 0
        for key in keys:
            if self.invalidate(key):
                count += 1
        if count > 0:
            logger.info(
                f"Cache invalidated by prefix '{prefix}': {count} entries"
            )
        return count

    def invalidate_all(self) -> int:
        """失效所有缓存条目."""
        count = len(self._cache)
        self._cache.clear()
        self._tag_index.clear()
        self._stats['invalidations'] += count
        if count > 0:
            logger.info(f"All cache invalidated: {count} entries")
        return count

    def _remove_entry(self, key: str) -> None:
        """移除缓存条目并更新标签索引."""
        entry = self._cache.pop(key, None)
        if entry:
            for tag in entry.tags:
                tag_set = self._tag_index.get(tag)
                if tag_set:
                    tag_set.discard(key)
                    if not tag_set:
                        del self._tag_index[tag]

    def _evict_expired(self) -> int:
        """清理过期条目."""
        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired
        ]
        for key in expired_keys:
            self._remove_entry(key)
            self._stats['evictions'] += 1
        return len(expired_keys)

    @property
    def stats(self) -> Dict[str, Any]:
        """缓存统计信息."""
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total if total > 0 else 0.0
        return {
            **self._stats,
            'size': len(self._cache),
            'hit_rate': f"{hit_rate:.2%}",
        }

    @property
    def size(self) -> int:
        """当前缓存大小."""
        return len(self._cache)


# 全局缓存管理器实例（用于 RBAC 权限缓存）
_permission_cache = CacheManager(ttl=DEFAULT_CACHE_TTL)


def get_permission_cache() -> CacheManager:
    """获取权限缓存管理器实例."""
    return _permission_cache


def invalidate_user_permissions(user_id: str) -> int:
    """失效指定用户的所有权限缓存.

    当用户角色变更时调用（如分配/撤销角色）。

    Args:
        user_id: 用户 ID

    Returns:
        失效的条目数
    """
    cache = get_permission_cache()
    return cache.invalidate_by_prefix(f"perm:{user_id}:")


def invalidate_kb_permissions(kb_id: str) -> int:
    """失效指定知识库的所有权限缓存.

    当知识库权限策略变更时调用（如角色权限调整）。

    Args:
        kb_id: 知识库 ID

    Returns:
        失效的条目数
    """
    cache = get_permission_cache()
    # 按标签失效（set 时已标记 kb:{kb_id} 标签的条目）
    count = cache.invalidate_by_tag(f"kb:{kb_id}")
    # 也按前缀失效（覆盖 perm:*:{kb_id} 模式的条目）
    count += cache.invalidate_by_prefix(f"perm:*:{kb_id}")
    return count


def invalidate_all_permissions() -> int:
    """失效所有权限缓存.

    当系统级权限变更时调用（如角色定义修改）。
    """
    cache = get_permission_cache()
    return cache.invalidate_all()
