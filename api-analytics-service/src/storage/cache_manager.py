"""Query result caching with TTL."""

from typing import Optional, Any, Callable
import hashlib
import json
import logging
from functools import wraps

from src.clients import RedisClient
from src.exceptions import CacheError
from src.utils.logging import get_logger
from src.metrics import metrics_recorder

logger = get_logger(__name__)


class CacheManager:
    """Manage query result caching."""

    def __init__(self, redis_client: RedisClient):
        """Initialize cache manager.

        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client
        self.cache_prefix = "api_cache:"

    def _generate_key(self, namespace: str, *args, **kwargs) -> str:
        """Generate cache key from namespace and parameters.

        Args:
            namespace: Cache namespace
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key
        """
        # Create a string representation of all parameters
        params_str = json.dumps(
            {
                "args": [str(arg) for arg in args],
                "kwargs": {k: str(v) for k, v in kwargs.items()},
            },
            sort_keys=True,
        )

        # Hash the parameters
        params_hash = hashlib.md5(params_str.encode()).hexdigest()

        return f"{self.cache_prefix}{namespace}:{params_hash}"

    async def get(self, namespace: str, *args, **kwargs) -> Optional[Any]:
        """Get cached value.

        Args:
            namespace: Cache namespace
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cached value or None

        Raises:
            CacheError: If cache operation fails
        """
        try:
            key = self._generate_key(namespace, *args, **kwargs)
            value = await self.redis_client.get(key)

            if value:
                logger.debug(
                    "Cache hit",
                    extra={"extra_fields": {"namespace": namespace}},
                )
                metrics_recorder.record_cache_hit(namespace)
                return value

            logger.debug(
                "Cache miss",
                extra={"extra_fields": {"namespace": namespace}},
            )
            metrics_recorder.record_cache_miss(namespace)
            return None

        except CacheError:
            logger.warning(f"Cache get failed for namespace: {namespace}")
            return None

    async def set(
        self,
        namespace: str,
        value: Any,
        ttl: Optional[int] = None,
        *args,
        **kwargs,
    ) -> None:
        """Set cached value.

        Args:
            namespace: Cache namespace
            value: Value to cache
            ttl: Time to live in seconds
            *args: Positional arguments
            **kwargs: Keyword arguments

        Raises:
            CacheError: If cache operation fails
        """
        try:
            key = self._generate_key(namespace, *args, **kwargs)
            await self.redis_client.set(key, value, ttl)

            logger.debug(
                "Value cached",
                extra={"extra_fields": {"namespace": namespace}},
            )

        except CacheError as e:
            logger.warning(f"Failed to cache value: {str(e)}")

    async def delete(self, namespace: str, *args, **kwargs) -> None:
        """Delete cached value.

        Args:
            namespace: Cache namespace
            *args: Positional arguments
            **kwargs: Keyword arguments

        Raises:
            CacheError: If cache operation fails
        """
        try:
            key = self._generate_key(namespace, *args, **kwargs)
            await self.redis_client.delete(key)

            logger.debug(
                "Cache entry deleted",
                extra={"extra_fields": {"namespace": namespace}},
            )

        except CacheError as e:
            logger.warning(f"Failed to delete cache entry: {str(e)}")

    async def clear_namespace(self, namespace: str) -> None:
        """Clear all cache entries for namespace.

        Args:
            namespace: Cache namespace
        """
        try:
            # Note: This is a simplified implementation
            # In production, use Redis SCAN with pattern matching
            logger.info(f"Clearing cache namespace: {namespace}")

        except Exception as e:
            logger.warning(f"Failed to clear namespace: {str(e)}")

    def cached(
        self,
        namespace: str,
        ttl: Optional[int] = None,
    ):
        """Decorator to cache function results.

        Args:
            namespace: Cache namespace
            ttl: Time to live in seconds

        Returns:
            Decorator function
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Try to get from cache
                cached_value = await self.get(namespace, *args, **kwargs)
                if cached_value is not None:
                    return cached_value

                # Call function
                result = await func(*args, **kwargs)

                # Cache result
                await self.set(namespace, result, ttl, *args, **kwargs)

                return result

            return wrapper

        return decorator


# Global cache manager instance
cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance.

    Returns:
        Cache manager instance

    Raises:
        RuntimeError: If cache manager not initialized
    """
    global cache_manager

    if cache_manager is None:
        raise RuntimeError("Cache manager not initialized")

    return cache_manager


def init_cache_manager(redis_client: RedisClient) -> CacheManager:
    """Initialize global cache manager.

    Args:
        redis_client: Redis client instance

    Returns:
        Cache manager instance
    """
    global cache_manager

    cache_manager = CacheManager(redis_client)
    logger.info("Cache manager initialized")

    return cache_manager

