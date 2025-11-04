"""Redis cache manager for incremental clustering state."""

import logging
import json
from typing import Optional, Dict, List
import redis

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis cache for incremental clustering state."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        socket_timeout: int = 5,
        cache_ttl_seconds: int = 86400,
    ):
        """
        Initialize cache manager.

        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            db: Redis database number
            socket_timeout: Socket timeout in seconds
            cache_ttl_seconds: Cache TTL in seconds
        """
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            socket_timeout=socket_timeout,
            decode_responses=True,
        )
        self.cache_ttl = cache_ttl_seconds

        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"Initialized CacheManager: {host}:{port}/{db}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            raise

    def set_cluster_state(
        self,
        cluster_id: str,
        state: Dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store cluster state in cache.

        Args:
            cluster_id: Cluster ID
            state: State dictionary
            ttl: Optional TTL override

        Returns:
            True if successful
        """
        try:
            key = f"cluster:{cluster_id}"
            value = json.dumps(state)
            ttl = ttl or self.cache_ttl

            self.redis_client.setex(key, ttl, value)
            logger.debug(f"Cached cluster state: {cluster_id}")
            return True

        except Exception as e:
            logger.error(f"Error caching cluster state: {e}", exc_info=True)
            return False

    def get_cluster_state(self, cluster_id: str) -> Optional[Dict]:
        """
        Retrieve cluster state from cache.

        Args:
            cluster_id: Cluster ID

        Returns:
            State dictionary or None
        """
        try:
            key = f"cluster:{cluster_id}"
            value = self.redis_client.get(key)

            if value:
                return json.loads(value)

            return None

        except Exception as e:
            logger.error(f"Error retrieving cluster state: {e}", exc_info=True)
            return None

    def set_window_checkpoint(
        self,
        window_id: str,
        checkpoint: Dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store time window checkpoint.

        Args:
            window_id: Window identifier
            checkpoint: Checkpoint data
            ttl: Optional TTL override

        Returns:
            True if successful
        """
        try:
            key = f"window:{window_id}"
            value = json.dumps(checkpoint)
            ttl = ttl or self.cache_ttl

            self.redis_client.setex(key, ttl, value)
            logger.debug(f"Cached window checkpoint: {window_id}")
            return True

        except Exception as e:
            logger.error(f"Error caching window checkpoint: {e}", exc_info=True)
            return False

    def get_window_checkpoint(self, window_id: str) -> Optional[Dict]:
        """
        Retrieve time window checkpoint.

        Args:
            window_id: Window identifier

        Returns:
            Checkpoint data or None
        """
        try:
            key = f"window:{window_id}"
            value = self.redis_client.get(key)

            if value:
                return json.loads(value)

            return None

        except Exception as e:
            logger.error(f"Error retrieving window checkpoint: {e}", exc_info=True)
            return None

    def set_deduplication_set(
        self,
        set_id: str,
        items: List[str],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store deduplication set.

        Args:
            set_id: Set identifier
            items: List of items
            ttl: Optional TTL override

        Returns:
            True if successful
        """
        try:
            key = f"dedup:{set_id}"
            ttl = ttl or self.cache_ttl

            # Use Redis set for efficient membership testing
            self.redis_client.delete(key)
            if items:
                self.redis_client.sadd(key, *items)
                self.redis_client.expire(key, ttl)

            logger.debug(f"Cached deduplication set: {set_id} ({len(items)} items)")
            return True

        except Exception as e:
            logger.error(f"Error caching deduplication set: {e}", exc_info=True)
            return False

    def is_duplicate(self, set_id: str, item: str) -> bool:
        """
        Check if item is in deduplication set.

        Args:
            set_id: Set identifier
            item: Item to check

        Returns:
            True if item is in set
        """
        try:
            key = f"dedup:{set_id}"
            return self.redis_client.sismember(key, item)

        except Exception as e:
            logger.error(f"Error checking deduplication: {e}", exc_info=True)
            return False

    def clear_cache(self, pattern: str = "*") -> int:
        """
        Clear cache entries matching pattern.

        Args:
            pattern: Key pattern (e.g., "cluster:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries matching {pattern}")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)
            return 0

