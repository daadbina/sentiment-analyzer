"""Feast writer for online and offline features using Feast Python SDK."""

from typing import Dict, Any
import pandas as pd
from datetime import datetime
from feast import FeatureStore

from ..utils import StructuredLogger
from ..exceptions import FeastWriteError
from ..config import FeastConfig

logger = StructuredLogger(__name__)


class FeastWriter:
    """Write features to Feast online and offline stores using Python SDK."""

    def __init__(self):
        """Initialize writer with Feast SDK."""
        config = FeastConfig()

        # Initialize Feast FeatureStore
        # This will read feature_store.yaml from the repo_path
        self.feature_store = FeatureStore(repo_path=config.repo_path)

        logger.info(
            "Feast SDK writer initialized",
            repo_path=config.repo_path,
            registry_path=config.registry_path
        )

    def write_features(
        self,
        group_id: str,
        features: Dict[str, Any],
        to: str = "online_and_offline"
    ) -> bool:
        """Write features to Feast online and/or offline stores.

        Args:
            group_id: Semantic group ID
            features: Feature dictionary
            to: Target store - "online", "offline", or "online_and_offline"

        Returns:
            True if successful
        """
        try:
            # Prepare feature data with required fields
            timestamp = datetime.utcnow()

            # Create DataFrame with all required fields
            # Note: Use "timestamp" field name to match feature definition in features.py
            feature_data = pd.DataFrame([{
                "group_id": group_id,
                "timestamp": timestamp,
                **features,
            }])

            # Write features to Feast using SDK
            # The SDK will handle writing to both online (Redis) and offline (Delta Lake) stores
            if to == "online":
                # Write only to online store (Redis)
                self.feature_store.write_to_online_store(
                    feature_view_name="semantic_group_features",
                    df=feature_data
                )
            elif to == "offline":
                # Write only to offline store (Delta Lake)
                # Note: Feast SDK doesn't have a direct method for this
                # Features are written to offline store during materialization
                logger.warning(
                    "Writing to offline store only is not supported by Feast SDK",
                    group_id=group_id
                )
            else:
                # Write to online store (offline store is updated during materialization)
                self.feature_store.write_to_online_store(
                    feature_view_name="semantic_group_features",
                    df=feature_data
                )

            logger.info(
                "Features written to Feast via SDK",
                group_id=group_id,
                feature_count=len(features),
                target_store=to
            )

            return True

        except Exception as e:
            logger.error(
                "Error writing features to Feast",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise FeastWriteError(f"Error writing features to Feast: {str(e)}")

    def close(self):
        """Close connection (no-op for Feast SDK)."""
        logger.info("Feast SDK writer closed")

