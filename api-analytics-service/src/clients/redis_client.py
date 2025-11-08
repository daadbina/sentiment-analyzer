"""Redis cache client."""

import redis.asyncio as redis
from typing import Optional, Any
import json
import logging

from src.config import config
from src.exceptions import CacheError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis cache client with async support."""

    def __init__(self):
        """Initialize Redis client."""
        self.client: Optional[redis.Redis] = None
        self.config = config.redis

    async def connect(self) -> None:
        """Create Redis connection pool.

        Raises:
            CacheError: If connection fails
        """
        try:
            logger.info("Connecting to Redis...")

            self.client = await redis.from_url(
                f"redis://{self.config.host}:{self.config.port}/{self.config.db}",
                password=self.config.password,
                max_connections=self.config.pool_size,
                decode_responses=False,
            )

            # Test connection
            await self.client.ping()

            logger.info(
                "Redis connection established",
                extra={
                    "extra_fields": {
                        "host": self.config.host,
                        "port": self.config.port,
                        "db": self.config.db,
                    }
                },
            )

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise CacheError(
                message="Failed to connect to Redis",
                details={"error": str(e)},
            )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def health_check(self) -> bool:
        """Check Redis health.

        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            if not self.client:
                return False

            await self.client.ping()
            logger.info("Redis health check passed")
            return True

        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None

        Raises:
            CacheError: If operation fails
        """
        if not self.client:
            raise CacheError(message="Not connected to Redis")

        try:
            value = await self.client.get(key)

            if value:
                return json.loads(value.decode("utf-8"))

            return None

        except json.JSONDecodeError:
            logger.warning(f"Failed to decode cached value for key: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get failed: {str(e)}")
            raise CacheError(
                message="Cache get failed",
                details={"error": str(e), "key": key},
            )

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Raises:
            CacheError: If operation fails
        """
        if not self.client:
            raise CacheError(message="Not connected to Redis")

        try:
            serialized = json.dumps(value).encode("utf-8")
            ttl = ttl or config.cache.ttl_seconds

            await self.client.setex(key, ttl, serialized)

        except Exception as e:
            logger.error(f"Cache set failed: {str(e)}")
            raise CacheError(
                message="Cache set failed",
                details={"error": str(e), "key": key},
            )

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key

        Raises:
            CacheError: If operation fails
        """
        if not self.client:
            raise CacheError(message="Not connected to Redis")

        try:
            await self.client.delete(key)

        except Exception as e:
            logger.error(f"Cache delete failed: {str(e)}")
            raise CacheError(
                message="Cache delete failed",
                details={"error": str(e), "key": key},
            )

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise

        Raises:
            CacheError: If operation fails
        """
        if not self.client:
            raise CacheError(message="Not connected to Redis")

        try:
            return await self.client.exists(key) > 0

        except Exception as e:
            logger.error(f"Cache exists check failed: {str(e)}")
            raise CacheError(
                message="Cache exists check failed",
                details={"error": str(e), "key": key},
            )

    async def clear(self) -> None:
        """Clear all cache.

        Raises:
            CacheError: If operation fails
        """
        if not self.client:
            raise CacheError(message="Not connected to Redis")

        try:
            await self.client.flushdb()
            logger.info("Redis cache cleared")

        except Exception as e:
            logger.error(f"Cache clear failed: {str(e)}")
            raise CacheError(
                message="Cache clear failed",
                details={"error": str(e)},
            )

    async def get_ttl(self, key: str) -> int:
        """Get remaining TTL for key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist

        Raises:
            CacheError: If operation fails
        """
        if not self.client:
            raise CacheError(message="Not connected to Redis")

        try:
            return await self.client.ttl(key)

        except Exception as e:
            logger.error(f"Cache TTL check failed: {str(e)}")
            raise CacheError(
                message="Cache TTL check failed",
                details={"error": str(e), "key": key},
            )


# Global Redis client instance
redis_client = RedisClient()

