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

    # Entity cache methods
    def set_entity(
        self,
        article_id: str,
        entities: List[Dict],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store entities for an article in cache.

        Args:
            article_id: Article ID
            entities: List of entity dictionaries
            ttl: Optional TTL override (default: 7 days = 604800 seconds)

        Returns:
            True if successful
        """
        try:
            key = f"entity:{article_id}"
            value = json.dumps(entities)
            # Default to 7 days TTL for entities
            ttl = ttl or 604800

            self.redis_client.setex(key, ttl, value)
            logger.debug(f"Cached entities for article: {article_id}")
            return True

        except Exception as e:
            logger.error(f"Error caching entities for {article_id}: {e}", exc_info=True)
            return False

    def get_entity(self, article_id: str) -> Optional[List[Dict]]:
        """
        Retrieve entities for an article from cache.

        Args:
            article_id: Article ID

        Returns:
            List of entity dictionaries or None
        """
        try:
            key = f"entity:{article_id}"
            value = self.redis_client.get(key)

            if value:
                return json.loads(value)

            return None

        except Exception as e:
            logger.error(f"Error retrieving entities for {article_id}: {e}", exc_info=True)
            return None

    def set_entities_batch(
        self,
        entities_dict: Dict[str, List[Dict]],
        ttl: Optional[int] = None,
    ) -> int:
        """
        Store multiple entities in batch using pipeline for efficiency.

        Args:
            entities_dict: Dictionary mapping article_id to entities list
            ttl: Optional TTL override (default: 7 days = 604800 seconds)

        Returns:
            Number of entities successfully cached
        """
        try:
            # Default to 7 days TTL for entities
            ttl = ttl or 604800

            # Use pipeline for batch operations
            pipe = self.redis_client.pipeline()

            for article_id, entities in entities_dict.items():
                key = f"entity:{article_id}"
                value = json.dumps(entities)
                pipe.setex(key, ttl, value)

            # Execute all commands at once
            pipe.execute()

            logger.info(f"Batch cached {len(entities_dict)} entities")
            return len(entities_dict)

        except Exception as e:
            logger.error(f"Error batch caching entities: {e}", exc_info=True)
            return 0

    def get_entity_cache_size(self) -> int:
        """
        Get the number of cached entities.

        Returns:
            Number of entity keys in cache
        """
        try:
            keys = self.redis_client.keys("entity:*")
            return len(keys)
        except Exception as e:
            logger.error(f"Error getting entity cache size: {e}", exc_info=True)
            return 0

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Generic set method for any key-value pair.

        Args:
            key: Cache key
            value: Value to store
            ttl: Optional TTL in seconds

        Returns:
            True if successful
        """
        try:
            if ttl:
                self.redis_client.setex(key, ttl, value)
            else:
                self.redis_client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Error setting key {key}: {e}", exc_info=True)
            return False

    def get(self, key: str) -> Optional[str]:
        """
        Generic get method for any key.

        Args:
            key: Cache key

        Returns:
            Value or None
        """
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Error getting key {key}: {e}", exc_info=True)
            return None

