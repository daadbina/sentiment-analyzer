"""Redis client for online features."""

import redis
import json
from typing import Dict, Any, Optional
from ..config import config
from ..utils import StructuredLogger
from ..exceptions import RedisWriteError

logger = StructuredLogger(__name__)


class RedisClient:
    """Redis client for online feature store."""

    def __init__(self):
        """Initialize client."""
        self.config = config
        self.client: Optional[redis.Redis] = None

    def connect(self) -> bool:
        """Connect to Redis.

        Returns:
            True if connection successful
        """
        try:
            self.client = redis.Redis(
                host=self.config.redis.host,
                port=self.config.redis.port,
                db=self.config.redis.db,
                decode_responses=True,
            )

            # Test connection
            self.client.ping()

            logger.info(
                "Redis connected",
                host=self.config.redis.host,
                port=self.config.redis.port,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise RedisWriteError(f"Failed to connect to Redis: {str(e)}")

    def set_features(
        self,
        group_id: str,
        features: Dict[str, Any],
        ttl_seconds: int = 86400,
    ) -> bool:
        """Set features in Redis.

        Args:
            group_id: Semantic group ID
            features: Feature dictionary
            ttl_seconds: Time to live in seconds

        Returns:
            True if successful
        """
        if not self.client:
            raise RedisWriteError("Not connected to Redis")

        try:
            key = f"features:{group_id}"
            value = json.dumps(features)

            self.client.setex(key, ttl_seconds, value)

            logger.info(
                "Features set in Redis",
                group_id=group_id,
                ttl_seconds=ttl_seconds,
            )
            return True

        except Exception as e:
            logger.error("Error setting features in Redis", error=str(e), group_id=group_id)
            raise RedisWriteError(f"Error setting features in Redis: {str(e)}")

    def get_features(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get features from Redis.

        Args:
            group_id: Semantic group ID

        Returns:
            Feature dictionary or None
        """
        if not self.client:
            raise RedisWriteError("Not connected to Redis")

        try:
            key = f"features:{group_id}"
            value = self.client.get(key)

            if value:
                features = json.loads(value)
                logger.info("Features retrieved from Redis", group_id=group_id)
                return features

            return None

        except Exception as e:
            logger.error("Error getting features from Redis", error=str(e), group_id=group_id)
            raise RedisWriteError(f"Error getting features from Redis: {str(e)}")

    def delete_features(self, group_id: str) -> bool:
        """Delete features from Redis.

        Args:
            group_id: Semantic group ID

        Returns:
            True if successful
        """
        if not self.client:
            raise RedisWriteError("Not connected to Redis")

        try:
            key = f"features:{group_id}"
            self.client.delete(key)

            logger.info("Features deleted from Redis", group_id=group_id)
            return True

        except Exception as e:
            logger.error("Error deleting features from Redis", error=str(e), group_id=group_id)
            raise RedisWriteError(f"Error deleting features from Redis: {str(e)}")

    def close(self):
        """Close connection."""
        if self.client:
            self.client.close()
            logger.info("Redis connection closed")

