"""Distributed caching strategy for performance optimization."""

import logging
import json
from typing import Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


class CacheManager:
    """Distributed cache manager for normalization results."""

    def __init__(self, redis_client=None, ttl: int = 3600):
        """Initialize cache manager.

        Args:
            redis_client: Redis client for distributed caching
            ttl: Cache TTL in seconds (default 1 hour)
        """
        self.redis_client = redis_client
        self.ttl = ttl
        self.stats = CacheStats()
        self.local_cache = {}  # Local in-memory cache

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        # Try local cache first
        if key in self.local_cache:
            self.stats.hits += 1
            return self.local_cache[key]

        # Try Redis
        if self.redis_client:
            try:
                value = await self.redis_client.get(key)
                if value:
                    self.stats.hits += 1
                    # Store in local cache
                    self.local_cache[key] = json.loads(value)
                    return self.local_cache[key]
            except Exception as e:
                logger.warning(f"Error getting from Redis cache: {e}")

        self.stats.misses += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override

        Returns:
            True if set successfully
        """
        ttl = ttl or self.ttl

        # Store in local cache
        self.local_cache[key] = value

        # Store in Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps(value, default=str)
                )
                return True
            except Exception as e:
                logger.warning(f"Error setting Redis cache: {e}")
                return False

        return True

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        # Delete from local cache
        if key in self.local_cache:
            del self.local_cache[key]

        # Delete from Redis
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
                self.stats.evictions += 1
                return True
            except Exception as e:
                logger.warning(f"Error deleting from Redis cache: {e}")

        return True

    async def clear(self) -> None:
        """Clear all caches."""
        self.local_cache.clear()
        if self.redis_client:
            try:
                await self.redis_client.flushdb()
            except Exception as e:
                logger.warning(f"Error clearing Redis cache: {e}")

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        return self.stats

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self.stats = CacheStats()


class NormalizationResultCache:
    """Cache for normalization results."""

    def __init__(self, cache_manager: CacheManager):
        """Initialize normalization result cache.

        Args:
            cache_manager: Cache manager instance
        """
        self.cache_manager = cache_manager

    async def get_canonicalization(self, url: str) -> Optional[dict]:
        """Get cached canonicalization result.

        Args:
            url: URL to look up

        Returns:
            Cached canonicalization result or None
        """
        key = f"canonicalization:{url}"
        return await self.cache_manager.get(key)

    async def set_canonicalization(self, url: str, result: dict) -> bool:
        """Cache canonicalization result.

        Args:
            url: URL
            result: Canonicalization result

        Returns:
            True if cached successfully
        """
        key = f"canonicalization:{url}"
        return await self.cache_manager.set(key, result)

    async def get_classification(self, content_hash: str) -> Optional[dict]:
        """Get cached classification result.

        Args:
            content_hash: Content hash

        Returns:
            Cached classification result or None
        """
        key = f"classification:{content_hash}"
        return await self.cache_manager.get(key)

    async def set_classification(self, content_hash: str, result: dict) -> bool:
        """Cache classification result.

        Args:
            content_hash: Content hash
            result: Classification result

        Returns:
            True if cached successfully
        """
        key = f"classification:{content_hash}"
        return await self.cache_manager.set(key, result)

    async def get_publisher(self, domain: str) -> Optional[dict]:
        """Get cached publisher info.

        Args:
            domain: Publisher domain

        Returns:
            Cached publisher info or None
        """
        key = f"publisher:{domain}"
        return await self.cache_manager.get(key)

    async def set_publisher(self, domain: str, info: dict, ttl: int = 86400) -> bool:
        """Cache publisher info.

        Args:
            domain: Publisher domain
            info: Publisher information
            ttl: Cache TTL (default 24 hours)

        Returns:
            True if cached successfully
        """
        key = f"publisher:{domain}"
        return await self.cache_manager.set(key, info, ttl)

    async def invalidate_url(self, url: str) -> None:
        """Invalidate canonicalization cache for URL.

        Args:
            url: URL to invalidate
        """
        key = f"canonicalization:{url}"
        await self.cache_manager.delete(key)

    async def invalidate_content(self, content_hash: str) -> None:
        """Invalidate classification cache for content.

        Args:
            content_hash: Content hash to invalidate
        """
        key = f"classification:{content_hash}"
        await self.cache_manager.delete(key)

    async def invalidate_publisher(self, domain: str) -> None:
        """Invalidate publisher cache.

        Args:
            domain: Publisher domain to invalidate
        """
        key = f"publisher:{domain}"
        await self.cache_manager.delete(key)

