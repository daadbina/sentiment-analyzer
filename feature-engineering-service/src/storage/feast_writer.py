"""Feast writer for offline features."""

from typing import Dict, Any
from ..clients import FeastClient
from ..utils import StructuredLogger
from ..exceptions import FeastWriteError

logger = StructuredLogger(__name__)


class FeastWriter:
    """Write features to Feast offline store."""

    def __init__(self):
        """Initialize writer."""
        self.client = FeastClient()
        self.client.connect()

    def write_features(
        self,
        group_id: str,
        features: Dict[str, Any],
    ) -> bool:
        """Write features to Feast.

        Args:
            group_id: Semantic group ID
            features: Feature dictionary

        Returns:
            True if successful
        """
        try:
            # Prepare feature data with metadata
            # Use datetime object with UTC timezone, not ISO string
            import pandas as pd
            from datetime import datetime
            import pytz

            timestamp = pd.Timestamp(datetime.now(pytz.UTC))
            feature_data = {
                "group_id": group_id,
                "timestamp": timestamp,
                **features,
            }

            # Write to Feast
            success = self.client.write_features(
                group_id=group_id,
                features=feature_data,
            )

            if success:
                logger.info(
                    "Features written to Feast offline store",
                    group_id=group_id,
                    feature_count=len(features),
                )
            else:
                logger.warning(
                    "Failed to write features to Feast",
                    group_id=group_id,
                )

            return success

        except Exception as e:
            logger.error(
                "Error writing features to Feast",
                group_id=group_id,
                error=str(e),
            )
            raise FeastWriteError(f"Error writing features to Feast: {str(e)}")

    def close(self):
        """Close connection."""
        self.client.close()

