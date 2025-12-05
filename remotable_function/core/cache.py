"""
Response Cache for Remotable

A high-performance LRU cache with TTL support for caching RPC responses.

Features:
- LRU eviction policy
- TTL (Time-To-Live) expiration
- Thread-safe operations
- Cache statistics
- Automatic cleanup of expired entries
"""

import asyncio
import time
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with value and metadata"""

    value: Any
    created_at: float
    ttl: float
    hits: int = 0
    size: int = 0  # Approximate size in bytes

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() - self.created_at > self.ttl

    def touch(self) -> None:
        """Increment hit counter"""
        self.hits += 1


@dataclass
class CacheStats:
    """Cache statistics"""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    total_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class LRUCache:
    """
    LRU Cache with TTL support.

    Thread-safe cache implementation using OrderedDict for LRU eviction
    and TTL for automatic expiration.

    Example:
        cache = LRUCache(max_size=1000, default_ttl=60.0)

        # Set value with default TTL
        cache.set("key", "value")

        # Set value with custom TTL
        cache.set("key", "value", ttl=300.0)

        # Get value
        value = cache.get("key")

        # Check stats
        stats = cache.get_stats()
        print(f"Hit rate: {stats.hit_rate:.2%}")
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float = 60.0,
        cleanup_interval: float = 60.0,
    ):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
            cleanup_interval: Interval for cleanup task in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info(f"Cache cleanup task started (interval={self.cleanup_interval}s)")

    async def stop(self) -> None:
        """Stop background cleanup task"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Cache cleanup task stopped")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                self._stats.expirations += 1
                self._stats.misses += 1
                self._stats.total_size -= entry.size
                logger.debug(f"Cache expired: {key}")
                return None

            # Update LRU order
            self._cache.move_to_end(key)
            entry.touch()
            self._stats.hits += 1

            logger.debug(f"Cache hit: {key} (hits={entry.hits})")
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default_ttl if None)
        """
        async with self._lock:
            # Calculate approximate size
            try:
                size = len(json.dumps(value))
            except (TypeError, ValueError):
                size = 0

            # Check if key already exists
            if key in self._cache:
                old_entry = self._cache[key]
                self._stats.total_size -= old_entry.size

            # Create new entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl if ttl is not None else self.default_ttl,
                size=size,
            )

            # Evict oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest_key, oldest_entry = self._cache.popitem(last=False)
                self._stats.evictions += 1
                self._stats.total_size -= oldest_entry.size
                logger.debug(f"Cache evicted (LRU): {oldest_key}")

            # Add to cache
            self._cache[key] = entry
            self._stats.total_size += size
            logger.debug(f"Cache set: {key} (ttl={entry.ttl}s, size={size})")

    async def delete(self, key: str) -> bool:
        """
        Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._stats.total_size -= entry.size
                logger.debug(f"Cache deleted: {key}")
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries from cache"""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats = CacheStats()
            logger.info(f"Cache cleared ({count} entries)")

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        return self._stats

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired entries"""
        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

            for key in expired_keys:
                entry = self._cache.pop(key)
                self._stats.expirations += 1
                self._stats.total_size -= entry.size

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")


class ResponseCache:
    """
    Response cache for RPC calls.

    Caches RPC responses based on tool name and arguments.

    Example:
        cache = ResponseCache(max_size=500, default_ttl=300.0)
        await cache.start()

        # Cache response
        await cache.cache_response(
            client_id="client-1",
            tool="read_file",
            args={"path": "/etc/hosts"},
            response={"content": "..."},
            ttl=60.0
        )

        # Get cached response
        cached = await cache.get_response(
            client_id="client-1",
            tool="read_file",
            args={"path": "/etc/hosts"}
        )
    """

    def __init__(
        self,
        max_size: int = 500,
        default_ttl: float = 300.0,
        cleanup_interval: float = 60.0,
    ):
        """
        Initialize response cache.

        Args:
            max_size: Maximum number of cached responses
            default_ttl: Default TTL in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        self._cache = LRUCache(
            max_size=max_size,
            default_ttl=default_ttl,
            cleanup_interval=cleanup_interval,
        )
        # Maintain client_id -> set of cache keys mapping for efficient invalidation
        self._client_keys: Dict[str, set] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start cache"""
        await self._cache.start()

    async def stop(self) -> None:
        """Stop cache"""
        await self._cache.stop()

    def _make_key(self, client_id: str, tool: str, args: Dict[str, Any]) -> str:
        """
        Generate cache key from request parameters.

        Args:
            client_id: Client ID
            tool: Tool name
            args: Tool arguments

        Returns:
            Cache key (hash)
        """
        # Sort args for consistent hashing
        sorted_args = json.dumps(args, sort_keys=True)
        key_str = f"{client_id}:{tool}:{sorted_args}"

        # Use SHA256 hash for key
        return hashlib.sha256(key_str.encode()).hexdigest()

    async def get_response(self, client_id: str, tool: str, args: Dict[str, Any]) -> Optional[Any]:
        """
        Get cached response.

        Args:
            client_id: Client ID
            tool: Tool name
            args: Tool arguments

        Returns:
            Cached response or None
        """
        key = self._make_key(client_id, tool, args)
        return await self._cache.get(key)

    async def cache_response(
        self,
        client_id: str,
        tool: str,
        args: Dict[str, Any],
        response: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """
        Cache response.

        Args:
            client_id: Client ID
            tool: Tool name
            args: Tool arguments
            response: Response to cache
            ttl: TTL in seconds (uses default if None)
        """
        key = self._make_key(client_id, tool, args)
        await self._cache.set(key, response, ttl=ttl)

        # Update client key index
        async with self._lock:
            if client_id not in self._client_keys:
                self._client_keys[client_id] = set()
            self._client_keys[client_id].add(key)

    async def invalidate(self, client_id: str, tool: str, args: Dict[str, Any]) -> bool:
        """
        Invalidate cached response.

        Args:
            client_id: Client ID
            tool: Tool name
            args: Tool arguments

        Returns:
            True if invalidated, False if not found
        """
        key = self._make_key(client_id, tool, args)
        deleted = await self._cache.delete(key)

        # Update client key index if deleted
        if deleted:
            async with self._lock:
                if client_id in self._client_keys:
                    self._client_keys[client_id].discard(key)
                    # Clean up empty sets
                    if not self._client_keys[client_id]:
                        del self._client_keys[client_id]

        return deleted

    async def invalidate_client(self, client_id: str) -> int:
        """
        Invalidate all cached responses for a client.

        Args:
            client_id: Client ID

        Returns:
            Number of entries invalidated
        """
        async with self._lock:
            # Get all keys for this client
            if client_id not in self._client_keys:
                return 0

            keys_to_delete = list(self._client_keys[client_id])
            count = 0

            # Delete each key from cache
            for key in keys_to_delete:
                deleted = await self._cache.delete(key)
                if deleted:
                    count += 1

            # Clear the client's key set
            del self._client_keys[client_id]

            logger.info(f"Invalidated {count} cache entries for client {client_id}")
            return count

    async def clear(self) -> None:
        """Clear all cached responses"""
        await self._cache.clear()
        async with self._lock:
            self._client_keys.clear()

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        return self._cache.get_stats()
