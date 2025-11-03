"""Redis cache manager."""

import logging
import json
from typing import Optional, Any
import redis
from src.config import get_config
from src.exceptions import CacheError

logger = logging.getLogger(__name__)


class RedisCacheManager:
    """Manages caching with Redis."""

    def __init__(self):
        """Initialize Redis cache manager."""
        self.config = get_config()
        self.redis_client: Optional[redis.Redis] = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis.host,
                port=self.config.redis.port,
                db=self.config.redis.db,
                decode_responses=True,
                socket_connect_timeout=self.config.redis.socket_timeout,
                socket_keepalive=True,
            )

            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")

        except Exception as e:
            logger.warning(f"Redis connection failed (optional): {e}")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                return json.loads(str(value))  # type: ignore
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds

        Returns:
            True if successful
        """
        if not self.redis_client:
            return False

        try:
            self.redis_client.setex(
                key,
                ttl_seconds,
                json.dumps(value),
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        if not self.redis_client:
            return False

        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists
        """
        if not self.redis_client:
            return False

        try:
            exists_count = self.redis_client.exists(key)
            return bool(exists_count > 0)  # type: ignore
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    def get_checksum_cache_key(self, checksum: str) -> str:
        """Get cache key for checksum.

        Args:
            checksum: Article checksum

        Returns:
            Cache key
        """
        return f"checksum:{checksum}"

    def get_url_cache_key(self, url: str) -> str:
        """Get cache key for URL.

        Args:
            url: Article URL

        Returns:
            Cache key
        """
        return f"url:{url}"

    def cache_article(
        self, article_id: str, data: dict, ttl_seconds: int = 86400
    ) -> bool:
        """Cache article data.

        Args:
            article_id: Article ID
            data: Article data
            ttl_seconds: Time to live

        Returns:
            True if successful
        """
        key = f"article:{article_id}"
        return self.set(key, data, ttl_seconds)

    def get_cached_article(self, article_id: str) -> Optional[dict]:
        """Get cached article.

        Args:
            article_id: Article ID

        Returns:
            Cached article or None
        """
        key = f"article:{article_id}"
        return self.get(key)

    def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis: {e}")
