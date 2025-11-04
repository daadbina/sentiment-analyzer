"""Redis writer for online features."""

from typing import Dict, Any
from ..clients import RedisClient
from ..utils import StructuredLogger
from ..exceptions import RedisWriteError

logger = StructuredLogger(__name__)


class RedisWriter:
    """Write features to Redis online store."""

    def __init__(self, ttl_seconds: int = 86400):
        """Initialize writer.

        Args:
            ttl_seconds: Time to live for features in Redis
        """
        self.client = RedisClient()
        self.client.connect()
        self.ttl_seconds = ttl_seconds

    def write_features(
        self,
        group_id: str,
        features: Dict[str, Any],
    ) -> bool:
        """Write features to Redis.

        Args:
            group_id: Semantic group ID
            features: Feature dictionary

        Returns:
            True if successful
        """
        try:
            # Prepare feature data with metadata
            feature_data = {
                "group_id": group_id,
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                **features,
            }

            # Write to Redis
            success = self.client.set_features(
                group_id=group_id,
                features=feature_data,
                ttl_seconds=self.ttl_seconds,
            )

            if success:
                logger.info(
                    "Features written to Redis online store",
                    group_id=group_id,
                    feature_count=len(features),
                    ttl_seconds=self.ttl_seconds,
                )
            else:
                logger.warning(
                    "Failed to write features to Redis",
                    group_id=group_id,
                )

            return success

        except Exception as e:
            logger.error(
                "Error writing features to Redis",
                group_id=group_id,
                error=str(e),
            )
            raise RedisWriteError(f"Error writing features to Redis: {str(e)}")

    def close(self):
        """Close connection."""
        self.client.close()

