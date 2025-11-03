"""Redis client for caching."""

import logging
import json
from typing import Optional, Any
import redis

from src.config import get_settings
from src.exceptions import CacheError

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for URL and publisher caching."""

    def __init__(self):
        """Initialize Redis client."""
        self.settings = get_settings()
        self.client: Optional[redis.Redis] = None

    def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.client = redis.Redis(
                host=self.settings.redis.host,
                port=self.settings.redis.port,
                db=self.settings.redis.db,
                password=self.settings.redis.password,
                decode_responses=True,
            )
            # Test connection
            self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise CacheError(f"Redis connection failed: {e}")

    def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.client:
            try:
                self.client.close()
                logger.info("Disconnected from Redis")
            except Exception as e:
                logger.error(f"Error disconnecting from Redis: {e}")

    def get_url_redirect(self, url: str) -> Optional[str]:
        """Get cached URL redirect.

        Args:
            url: Original URL

        Returns:
            Redirected URL or None if not cached
        """
        if not self.client:
            return None

        try:
            key = f"url_redirect:{url}"
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Failed to get URL redirect from cache: {e}")
            return None

    def set_url_redirect(self, url: str, redirected_url: str) -> None:
        """Cache URL redirect.

        Args:
            url: Original URL
            redirected_url: Redirected URL
        """
        if not self.client:
            return

        try:
            key = f"url_redirect:{url}"
            self.client.setex(
                key,
                self.settings.redis.url_cache_ttl_seconds,
                redirected_url,
            )
        except Exception as e:
            logger.error(f"Failed to cache URL redirect: {e}")

    def get_publisher(self, domain: str) -> Optional[dict]:
        """Get cached publisher.

        Args:
            domain: Domain name

        Returns:
            Publisher dict or None if not cached
        """
        if not self.client:
            return None

        try:
            key = f"publisher:{domain}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get publisher from cache: {e}")
            return None

    def set_publisher(self, domain: str, publisher: dict) -> None:
        """Cache publisher.

        Args:
            domain: Domain name
            publisher: Publisher data
        """
        if not self.client:
            return

        try:
            key = f"publisher:{domain}"
            self.client.setex(
                key,
                self.settings.redis.publisher_cache_ttl_seconds,
                json.dumps(publisher),
            )
        except Exception as e:
            logger.error(f"Failed to cache publisher: {e}")

    def get_lsh_bucket(self, bucket_id: str) -> Optional[list]:
        """Get cached LSH bucket for fuzzy deduplication.

        Args:
            bucket_id: LSH bucket ID

        Returns:
            List of article IDs or None if not cached
        """
        if not self.client:
            return None

        try:
            key = f"lsh_bucket:{bucket_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get LSH bucket from cache: {e}")
            return None

    def set_lsh_bucket(self, bucket_id: str, article_ids: list) -> None:
        """Cache LSH bucket.

        Args:
            bucket_id: LSH bucket ID
            article_ids: List of article IDs
        """
        if not self.client:
            return

        try:
            key = f"lsh_bucket:{bucket_id}"
            self.client.setex(
                key,
                self.settings.redis.url_cache_ttl_seconds,  # 7 days
                json.dumps(article_ids),
            )
        except Exception as e:
            logger.error(f"Failed to cache LSH bucket: {e}")

    def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        if not self.client:
            return {}

        try:
            info = self.client.info()
            return {
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

