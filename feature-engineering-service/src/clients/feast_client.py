"""Feast client for feature store operations."""

from feast import FeatureStore
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime
from pathlib import Path
import pytz
from ..config import config
from ..utils import StructuredLogger
from ..exceptions import FeastWriteError

logger = StructuredLogger(__name__)


class FeastClient:
    """Feast client for offline feature store."""

    def __init__(self):
        """Initialize client."""
        self.config = config
        self.fs: Optional[FeatureStore] = None

    def connect(self) -> bool:
        """Connect to Feast.

        Returns:
            True if connection successful
        """
        try:
            # Initialize Feast feature store
            self.fs = FeatureStore(repo_path=self.config.feast.repo_path)

            logger.info(
                "Feast connected",
                repo_path=self.config.feast.repo_path,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to Feast", error=str(e))
            raise FeastWriteError(f"Failed to connect to Feast: {str(e)}")

    def write_features(
        self,
        group_id: str,
        features: Dict[str, Any],
        push_source_name: str = "semantic_group_features_push",
    ) -> bool:
        """Write features to Feast offline store (Delta Lake).

        Args:
            group_id: Semantic group ID
            features: Feature dictionary
            push_source_name: Name of push source (not feature view name)

        Returns:
            True if successful
        """
        if not self.fs:
            raise FeastWriteError("Not connected to Feast")

        try:
            # Prepare feature data with timestamp
            # Use datetime object with UTC timezone, not ISO string
            timestamp = pd.Timestamp(datetime.now(pytz.UTC))
            feature_data = {
                "group_id": group_id,
                "timestamp": timestamp,
                **features,
            }

            # Create DataFrame for Feast write
            df = pd.DataFrame([feature_data])

            # Ensure timestamp column has UTC timezone
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

            logger.debug(
                "Prepared feature DataFrame for Feast write",
                group_id=group_id,
                feature_count=len(features),
                columns=list(df.columns),
                dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
                push_source_name=push_source_name,
            )

            # Write to Feast offline store using push method
            # This writes to the configured offline store (Delta Lake)
            # NOTE: Must use push_source_name, not feature_view_name
            self.fs.push(
                push_source_name=push_source_name,
                df=df,
            )

            # Also manually write to parquet file for file offline store
            # This ensures the data is available for historical feature retrieval
            try:
                from pathlib import Path
                import os

                # Get the absolute path to the repo
                repo_path = Path(self.config.feast.repo_path).resolve()
                offline_store_dir = repo_path.parent / "feast" / "data"
                offline_store_dir.mkdir(parents=True, exist_ok=True)
                parquet_path = offline_store_dir / "semantic_groups.parquet"

                logger.debug(
                    "Parquet write details",
                    repo_path=str(repo_path),
                    offline_store_dir=str(offline_store_dir),
                    parquet_path=str(parquet_path),
                    dir_exists=offline_store_dir.exists(),
                )

                # Read existing parquet file if it exists, otherwise create new
                if parquet_path.exists():
                    existing_df = pd.read_parquet(str(parquet_path))
                    # Append new data
                    df_combined = pd.concat([existing_df, df], ignore_index=True)
                    # Remove duplicates based on group_id and timestamp, keeping the latest
                    df_combined = df_combined.sort_values('timestamp').drop_duplicates(
                        subset=['group_id'], keep='last'
                    )
                else:
                    df_combined = df

                # Write to parquet with proper schema
                df_combined.to_parquet(str(parquet_path), index=False, engine='pyarrow')
                logger.debug(
                    "Features written to parquet file",
                    parquet_path=str(parquet_path),
                    rows=len(df_combined),
                )
            except Exception as e:
                logger.warning(
                    "Failed to write to parquet file",
                    error=str(e),
                    group_id=group_id,
                )

            logger.info(
                "Features written to Feast offline store",
                group_id=group_id,
                feature_count=len(features),
                timestamp=timestamp,
            )
            return True

        except Exception as e:
            logger.error(
                "Error writing features to Feast",
                error=str(e),
                group_id=group_id,
                error_type=type(e).__name__,
            )
            raise FeastWriteError(f"Error writing features to Feast: {str(e)}")

    def get_features(
        self,
        group_id: str,
        feature_names: list,
    ) -> Optional[Dict[str, Any]]:
        """Get features from Feast offline store.

        Args:
            group_id: Semantic group ID
            feature_names: List of feature names

        Returns:
            Feature dictionary or None
        """
        if not self.fs:
            raise FeastWriteError("Not connected to Feast")

        try:
            # Create entity DataFrame for feature retrieval
            entity_df = pd.DataFrame({
                "group_id": [group_id],
            })

            # Build feature list with feature view prefix
            features = [f"semantic_group_features:{name}" for name in feature_names]

            logger.debug(
                "Retrieving features from Feast",
                group_id=group_id,
                feature_count=len(features),
                features=features,
            )

            # Get historical features from Feast
            feature_df = self.fs.get_historical_features(
                entity_df=entity_df,
                features=features,
                full_feature_names=True,
            ).to_df()

            logger.info(
                "Features retrieved from Feast",
                group_id=group_id,
                feature_count=len(feature_names),
                result_shape=feature_df.shape,
            )

            # Convert to dictionary
            if len(feature_df) > 0:
                return feature_df.iloc[0].to_dict()
            return None

        except Exception as e:
            logger.error(
                "Error retrieving features from Feast",
                error=str(e),
                group_id=group_id,
                error_type=type(e).__name__,
            )
            raise FeastWriteError(f"Error retrieving features from Feast: {str(e)}")

    def health_check(self) -> bool:
        """Check Feast connection health.

        Returns:
            True if connection is healthy
        """
        try:
            if not self.fs:
                return False

            # Try to list feature views as health check
            _ = self.fs.list_feature_views()
            logger.debug("Feast health check passed")
            return True
        except Exception as e:
            logger.warning("Feast health check failed", error=str(e))
            return False

    def validate_feature_view(self, feature_view_name: str = "semantic_group_features") -> bool:
        """Validate that feature view exists in registry.

        Args:
            feature_view_name: Name of feature view to validate

        Returns:
            True if feature view exists
        """
        if not self.fs:
            raise FeastWriteError("Not connected to Feast")

        try:
            fv = self.fs.get_feature_view(feature_view_name)
            if fv:
                logger.info(
                    "Feature view validated",
                    feature_view_name=feature_view_name,
                    num_features=len(fv.features),
                )
                return True
            return False
        except Exception as e:
            logger.warning(
                "Feature view validation failed",
                feature_view_name=feature_view_name,
                error=str(e),
            )
            return False

    def close(self):
        """Close connection."""
        if self.fs:
            self.fs = None
            logger.info("Feast connection closed")

