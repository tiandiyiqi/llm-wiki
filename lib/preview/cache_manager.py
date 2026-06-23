"""预览缓存管理模块

提供预览文件的缓存管理功能：
- 文件系统缓存管理
- 缓存生命周期（TTL 默认 24h）
- 自动清理过期缓存
- 缓存命中率统计
- Redis 可选（有则用，无则内存缓存）
"""

import json
import logging
import os
import re
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import redis as redis_module
    REDIS_AVAILABLE = True
except ImportError:
    redis_module = None  # type: ignore[assignment, misc]
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

# 默认缓存 TTL（秒）：24 小时
DEFAULT_CACHE_TTL = 24 * 60 * 60

# 默认缓存目录
DEFAULT_CACHE_DIR = '.cache/previews'

# 缓存统计键前缀
STATS_KEY_PREFIX = 'preview_cache_stats'

# 内存缓存最大条目数
MAX_MEMORY_CACHE_ENTRIES = 1000


@dataclass(frozen=True)
class CacheEntry:
    """缓存条目（不可变）"""
    cache_key: str
    cache_path: str
    atom_id: int
    format: str
    source_mime_type: Optional[str]
    file_size: int
    created_at: float
    expires_at: float
    hit_count: int = 0


@dataclass(frozen=True)
class CacheStats:
    """缓存统计（不可变）"""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    expired_count: int = 0
    evicted_count: int = 0

    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return self.hit_count / total


class PreviewCacheManager:
    """预览缓存管理器

    支持文件系统缓存和可选的 Redis 缓存。
    自动清理过期缓存，提供缓存命中率统计。
    """

    def __init__(
        self,
        cache_dir: str = DEFAULT_CACHE_DIR,
        ttl: int = DEFAULT_CACHE_TTL,
        redis_client: Any = None,
        db: Any = None,
    ) -> None:
        """初始化缓存管理器

        Args:
            cache_dir: 文件系统缓存目录
            ttl: 缓存 TTL（秒）
            redis_client: Redis 客户端（可选）
            db: 数据库管理器（可选）
        """
        self._cache_dir = Path(cache_dir)
        self._ttl = ttl
        self._redis = redis_client
        self._db = db
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._stats = _CacheStatsMutable()

    @property
    def is_redis_available(self) -> bool:
        """Redis 是否可用"""
        return REDIS_AVAILABLE and self._redis is not None

    def _ensure_cache_dir(self) -> Path:
        """确保缓存目录存在

        Returns:
            缓存目录路径
        """
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        return self._cache_dir

    def generate_cache_key(self, atom_id: int, format: str) -> str:
        """生成缓存键

        Args:
            atom_id: 知识原子 ID
            format: 预览格式

        Returns:
            缓存键字符串
        """
        return f"preview:{atom_id}:{format}"

    def generate_cache_path(
        self,
        atom_id: int,
        format: str,
        filename: Optional[str] = None,
    ) -> str:
        """生成缓存文件路径

        Args:
            atom_id: 知识原子 ID
            format: 预览格式
            filename: 文件名（可选）

        Returns:
            相对缓存路径
        """
        unique_id = uuid.uuid4().hex[:8]

        if filename:
            safe_name = _sanitize_filename(filename)
            return f"{atom_id}/{format}/{safe_name}"

        ext = _get_extension_for_format(format)
        return f"{atom_id}/{format}/{unique_id}{ext}"

    async def get(
        self,
        atom_id: int,
        format: str,
    ) -> Optional[CacheEntry]:
        """获取缓存条目

        Args:
            atom_id: 知识原子 ID
            format: 预览格式

        Returns:
            缓存条目，不存在返回 None
        """
        cache_key = self.generate_cache_key(atom_id, format)

        # 1. 检查 Redis 缓存
        if self.is_redis_available:
            entry = await self._get_from_redis(cache_key)
            if entry is not None:
                if not self._is_expired(entry):
                    self._stats.hit_count += 1
                    return entry
                self._stats.expired_count += 1

        # 2. 检查内存缓存
        mem_entry = self._memory_cache.get(cache_key)
        if mem_entry is not None:
            if not self._is_expired_dict(mem_entry):
                self._stats.hit_count += 1
                return self._dict_to_entry(mem_entry)
            self._stats.expired_count += 1

        # 3. 检查数据库
        if self._db:
            db_entry = await self._get_from_db(atom_id, format)
            if db_entry is not None:
                if not self._is_expired(db_entry):
                    self._stats.hit_count += 1
                    # 回填到内存缓存
                    self._put_to_memory(cache_key, db_entry)
                    return db_entry
                self._stats.expired_count += 1

        self._stats.miss_count += 1
        return None

    async def put(
        self,
        atom_id: int,
        format: str,
        data: bytes,
        source_mime_type: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> CacheEntry:
        """存入缓存

        Args:
            atom_id: 知识原子 ID
            format: 预览格式
            data: 缓存数据
            source_mime_type: 源 MIME 类型
            ttl: 自定义 TTL（秒）

        Returns:
            缓存条目
        """
        cache_key = self.generate_cache_key(atom_id, format)
        effective_ttl = ttl or self._ttl
        now = time.time()

        # 写入文件系统
        cache_path = self.generate_cache_path(atom_id, format)
        full_path = self._ensure_cache_dir() / cache_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)

        entry = CacheEntry(
            cache_key=cache_key,
            cache_path=cache_path,
            atom_id=atom_id,
            format=format,
            source_mime_type=source_mime_type,
            file_size=len(data),
            created_at=now,
            expires_at=now + effective_ttl,
        )

        # 写入 Redis
        if self.is_redis_available:
            await self._put_to_redis(cache_key, entry, effective_ttl)

        # 写入内存缓存
        self._put_to_memory(cache_key, entry)

        # 写入数据库
        if self._db:
            await self._put_to_db(entry, effective_ttl)

        return entry

    async def read_cache_data(self, cache_path: str) -> Optional[bytes]:
        """读取缓存文件数据

        Args:
            cache_path: 缓存文件相对路径

        Returns:
            文件数据，不存在返回 None
        """
        full_path = self._cache_dir / cache_path

        if not full_path.exists():
            return None

        try:
            return full_path.read_bytes()
        except Exception as e:
            logger.error(f"Failed to read cache file {cache_path}: {e}")
            return None

    async def invalidate(
        self,
        atom_id: int,
        format: str,
    ) -> bool:
        """使缓存失效

        Args:
            atom_id: 知识原子 ID
            format: 预览格式

        Returns:
            是否成功
        """
        cache_key = self.generate_cache_key(atom_id, format)
        success = True

        # 删除 Redis 缓存
        if self.is_redis_available:
            try:
                self._redis.delete(cache_key)
            except Exception as e:
                logger.warning(f"Failed to delete Redis cache: {e}")
                success = False

        # 删除内存缓存
        self._memory_cache.pop(cache_key, None)

        # 删除文件系统缓存
        cache_dir = self._cache_dir / str(atom_id) / format
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
            except Exception as e:
                logger.warning(f"Failed to delete cache directory: {e}")
                success = False

        # 删除数据库记录
        if self._db:
            try:
                await self._db.execute(
                    'DELETE FROM previews WHERE atom_id = $1 AND format = $2',
                    atom_id, format,
                )
            except Exception as e:
                logger.warning(f"Failed to delete DB cache record: {e}")
                success = False

        return success

    async def cleanup_expired(self) -> int:
        """清理过期缓存

        Returns:
            清理的条目数
        """
        cleaned = 0
        now = time.time()

        # 清理文件系统缓存
        if self._cache_dir.exists():
            cleaned += self._cleanup_filesystem(now)

        # 清理内存缓存
        expired_keys = [
            k for k, v in self._memory_cache.items()
            if v.get('expires_at', 0) < now
        ]
        for key in expired_keys:
            del self._memory_cache[key]
            cleaned += 1

        # 清理数据库过期记录
        if self._db:
            cleaned += await self._cleanup_db()

        self._stats.evicted_count += cleaned
        logger.info(f"Cleaned up {cleaned} expired cache entries")

        return cleaned

    def _cleanup_filesystem(self, now: float) -> int:
        """清理文件系统中的过期缓存

        Args:
            now: 当前时间戳

        Returns:
            清理的条目数
        """
        cleaned = 0

        for cache_file in self._cache_dir.rglob('*'):
            if not cache_file.is_file():
                continue

            # 检查文件修改时间 + TTL
            mtime = cache_file.stat().st_mtime
            if now - mtime > self._ttl:
                try:
                    cache_file.unlink()
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to delete cache file: {e}")

        # 清理空目录
        for dir_path in sorted(self._cache_dir.rglob('*'), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                except Exception:
                    pass

        return cleaned

    async def _cleanup_db(self) -> int:
        """清理数据库中的过期缓存

        Returns:
            清理的条目数
        """
        if not self._db:
            return 0

        try:
            result = await self._db.execute(
                '''
                DELETE FROM previews
                WHERE cache_expires_at IS NOT NULL
                AND cache_expires_at < NOW()
                '''
            )
            return len(result) if result else 0

        except Exception as e:
            logger.error(f"Failed to cleanup DB cache: {e}")
            return 0

    def get_stats(self) -> CacheStats:
        """获取缓存统计

        Returns:
            缓存统计对象
        """
        total_size = 0
        total_entries = 0

        if self._cache_dir.exists():
            for f in self._cache_dir.rglob('*'):
                if f.is_file():
                    total_size += f.stat().st_size
                    total_entries += 1

        return CacheStats(
            total_entries=total_entries,
            total_size_bytes=total_size,
            hit_count=self._stats.hit_count,
            miss_count=self._stats.miss_count,
            expired_count=self._stats.expired_count,
            evicted_count=self._stats.evicted_count,
        )

    async def _get_from_redis(self, cache_key: str) -> Optional[CacheEntry]:
        """从 Redis 获取缓存

        Args:
            cache_key: 缓存键

        Returns:
            缓存条目
        """
        if not self._redis:
            return None

        try:
            data = self._redis.get(cache_key)
            if data is None:
                return None

            entry_dict = json.loads(data)
            return self._dict_to_entry(entry_dict)

        except Exception as e:
            logger.warning(f"Failed to get from Redis: {e}")
            return None

    async def _put_to_redis(
        self,
        cache_key: str,
        entry: CacheEntry,
        ttl: int,
    ) -> None:
        """存入 Redis 缓存

        Args:
            cache_key: 缓存键
            entry: 缓存条目
            ttl: TTL（秒）
        """
        if not self._redis:
            return

        try:
            data = json.dumps(self._entry_to_dict(entry))
            self._redis.setex(cache_key, ttl, data)
        except Exception as e:
            logger.warning(f"Failed to put to Redis: {e}")

    async def _get_from_db(
        self,
        atom_id: int,
        format: str,
    ) -> Optional[CacheEntry]:
        """从数据库获取缓存

        Args:
            atom_id: 知识原子 ID
            format: 预览格式

        Returns:
            缓存条目
        """
        if not self._db:
            return None

        try:
            record = await self._db.fetch_one(
                '''
                SELECT * FROM previews
                WHERE atom_id = $1 AND format = $2
                ''',
                atom_id, format,
            )

            if not record:
                return None

            cache_path = record.get('cache_path', '')
            file_size = record.get('file_size', 0) or 0
            created_at = record.get('created_at')
            expires_at = record.get('cache_expires_at')

            created_ts = created_at.timestamp() if created_at else time.time()
            expires_ts = expires_at.timestamp() if expires_at else (created_ts + self._ttl)

            return CacheEntry(
                cache_key=self.generate_cache_key(atom_id, format),
                cache_path=cache_path or '',
                atom_id=atom_id,
                format=format,
                source_mime_type=record.get('source_mime_type'),
                file_size=file_size,
                created_at=created_ts,
                expires_at=expires_ts,
            )

        except Exception as e:
            logger.error(f"Failed to get from DB: {e}")
            return None

    async def _put_to_db(self, entry: CacheEntry, ttl: int) -> None:
        """存入数据库

        Args:
            entry: 缓存条目
            ttl: TTL（秒）
        """
        if not self._db:
            return

        try:
            from datetime import datetime, timedelta, timezone

            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

            await self._db.execute(
                '''
                INSERT INTO previews (
                    atom_id, format, source_mime_type,
                    cache_path, cache_expires_at, file_size
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (atom_id, format) DO UPDATE SET
                    cache_path = EXCLUDED.cache_path,
                    cache_expires_at = EXCLUDED.cache_expires_at,
                    file_size = EXCLUDED.file_size,
                    source_mime_type = EXCLUDED.source_mime_type
                ''',
                entry.atom_id,
                entry.format,
                entry.source_mime_type,
                entry.cache_path,
                expires_at,
                entry.file_size,
            )

        except Exception as e:
            logger.error(f"Failed to put to DB: {e}")

    def _put_to_memory(self, cache_key: str, entry: Any) -> None:
        """存入内存缓存

        Args:
            cache_key: 缓存键
            entry: 缓存条目或字典
        """
        if len(self._memory_cache) >= MAX_MEMORY_CACHE_ENTRIES:
            # 淘汰最早的条目
            oldest_key = min(
                self._memory_cache,
                key=lambda k: self._memory_cache[k].get('created_at', 0),
            )
            del self._memory_cache[oldest_key]

        if isinstance(entry, CacheEntry):
            self._memory_cache[cache_key] = self._entry_to_dict(entry)
        elif isinstance(entry, dict):
            self._memory_cache[cache_key] = entry

    def _is_expired(self, entry: CacheEntry) -> bool:
        """检查缓存条目是否过期

        Args:
            entry: 缓存条目

        Returns:
            是否过期
        """
        return time.time() > entry.expires_at

    def _is_expired_dict(self, entry_dict: Dict[str, Any]) -> bool:
        """检查缓存字典是否过期

        Args:
            entry_dict: 缓存字典

        Returns:
            是否过期
        """
        return time.time() > entry_dict.get('expires_at', 0)

    def _entry_to_dict(self, entry: CacheEntry) -> Dict[str, Any]:
        """将 CacheEntry 转为字典

        Args:
            entry: 缓存条目

        Returns:
            字典
        """
        return {
            'cache_key': entry.cache_key,
            'cache_path': entry.cache_path,
            'atom_id': entry.atom_id,
            'format': entry.format,
            'source_mime_type': entry.source_mime_type,
            'file_size': entry.file_size,
            'created_at': entry.created_at,
            'expires_at': entry.expires_at,
            'hit_count': entry.hit_count,
        }

    def _dict_to_entry(self, data: Dict[str, Any]) -> CacheEntry:
        """将字典转为 CacheEntry

        Args:
            data: 字典数据

        Returns:
            缓存条目
        """
        return CacheEntry(
            cache_key=data.get('cache_key', ''),
            cache_path=data.get('cache_path', ''),
            atom_id=data.get('atom_id', 0),
            format=data.get('format', ''),
            source_mime_type=data.get('source_mime_type'),
            file_size=data.get('file_size', 0),
            created_at=data.get('created_at', 0.0),
            expires_at=data.get('expires_at', 0.0),
            hit_count=data.get('hit_count', 0),
        )


class _CacheStatsMutable:
    """可变的缓存统计（内部使用）"""

    def __init__(self) -> None:
        self.hit_count: int = 0
        self.miss_count: int = 0
        self.expired_count: int = 0
        self.evicted_count: int = 0


def _sanitize_filename(filename: str) -> str:
    """清理文件名

    Args:
        filename: 原始文件名

    Returns:
            安全的文件名
    """
    safe = re.sub(r'[^\w\-.]', '_', filename)
    if len(safe) > 200:
        name, ext = safe.rsplit('.', 1) if '.' in safe else (safe, '')
        safe = f"{name[:190]}.{ext}" if ext else safe[:200]
    return safe


def _get_extension_for_format(format: str) -> str:
    """获取格式对应的文件扩展名

    Args:
        format: 预览格式

    Returns:
        文件扩展名（含点号）
    """
    extensions = {
        'pdf': '.pdf',
        'word': '.docx',
        'excel': '.xlsx',
        'ppt': '.pptx',
        'image': '.png',
        'markdown': '.md',
        'text': '.txt',
        'other': '.bin',
    }
    return extensions.get(format, '.bin')
