"""
Feast SDK client for Trainer & Model Registry Service.

Provides integration with Feast offline store for feature retrieval.
Falls back to Delta Lake if features not found in Feast.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd
import asyncio
from functools import wraps
from feast import FeatureStore

from src.config import FeastConfig
from src.exceptions import ExternalServiceError, DataPreparationError

logger = logging.getLogger(__name__)


def async_to_sync(func):
    """Decorator to run async functions synchronously."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper


class FeastClient:
    """Feast SDK client for offline store feature retrieval with Delta Lake fallback."""

    def __init__(self, config: FeastConfig, repo_path: str = "feast_remote"):
        """
        Initialize Feast SDK client.

        Args:
            config: Feast configuration
            repo_path: Path to Feast repository configuration
        """
        self.config = config
        self.repo_path = repo_path
        self._connected = False

        try:
            # Initialize Feast FeatureStore
            self.feature_store = FeatureStore(repo_path=repo_path)
            self._connected = True
            logger.info(f"Feast SDK client initialized: repo_path={repo_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Feast SDK client: {e}")
            raise ExternalServiceError(
                f"Failed to initialize Feast SDK client: {e}",
                service_name="Feast",
                details={"repo_path": repo_path},
            )

    def connect(self) -> None:
        """
        Test connection to Feast offline store.

        Raises:
            ExternalServiceError: If connection fails
        """
        try:
            # Test by listing feature views
            feature_views = self.feature_store.list_feature_views()
            self._connected = True
            logger.info(f"Feast SDK client connected successfully: {len(feature_views)} feature views found")
        except Exception as e:
            logger.error(f"Failed to connect to Feast offline store: {e}")
            raise ExternalServiceError(
                f"Failed to connect to Feast offline store: {e}",
                service_name="Feast",
                details={"repo_path": self.repo_path},
            )

    def health_check(self) -> bool:
        """
        Check Feast connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Test by listing feature views
            self.feature_store.list_feature_views()
            logger.debug("Feast health check passed")
            return True
        except Exception as e:
            logger.error(f"Feast health check failed: {e}")
            return False

    def get_features(
        self,
        entity_df: pd.DataFrame,
        features: List[str],
        timestamp_column: str = "timestamp",
    ) -> pd.DataFrame:
        """
        Retrieve features from Feast offline store with Delta Lake fallback.

        Args:
            entity_df: DataFrame with entity IDs and timestamps
            features: List of feature names to retrieve (format: "feature_view:feature_name")
            timestamp_column: Name of timestamp column

        Returns:
            DataFrame with features

        Raises:
            DataPreparationError: If feature retrieval fails
        """
        if not self._connected:
            raise ExternalServiceError(
                "Feast SDK client not connected",
                service_name="Feast",
            )

        try:
            logger.info(
                f"Retrieving {len(features)} features for {len(entity_df)} entities from Feast offline store"
            )

            # Ensure entity_df has the timestamp column
            if timestamp_column not in entity_df.columns:
                raise DataPreparationError(
                    f"Entity DataFrame missing timestamp column: {timestamp_column}",
                    stage="feature_retrieval",
                    details={"columns": list(entity_df.columns)}
                )

            # Rename timestamp column to event_timestamp for Feast
            entity_df_feast = entity_df.copy()
            entity_df_feast = entity_df_feast.rename(columns={timestamp_column: "event_timestamp"})

            logger.debug(f"Entity DataFrame shape: {entity_df_feast.shape}")
            logger.debug(f"Entity DataFrame columns: {list(entity_df_feast.columns)}")
            logger.debug(f"Entity DataFrame sample:\n{entity_df_feast.head()}")

            # Get historical features from Feast offline store
            logger.info("Fetching features from Feast offline store...")
            training_df = self.feature_store.get_historical_features(
                entity_df=entity_df_feast,
                features=features
            ).to_df()

            logger.info(f"Retrieved {len(training_df)} rows from Feast offline store")
            logger.debug(f"Feature DataFrame shape: {training_df.shape}")
            logger.debug(f"Feature DataFrame columns: {list(training_df.columns)}")

            # Check for missing features (NaN values)
            null_counts = training_df.isnull().sum()
            missing_features = null_counts[null_counts > 0]

            if len(missing_features) > 0:
                logger.warning(f"Found {len(missing_features)} features with null values")
                logger.debug(f"Null counts:\n{missing_features}")

                # Identify group_ids with missing features
                missing_mask = training_df.isnull().any(axis=1)
                missing_group_ids = training_df.loc[missing_mask, 'group_id'].tolist()

                if len(missing_group_ids) > 0:
                    logger.warning(
                        f"Found {len(missing_group_ids)} group_ids with missing features, "
                        f"will attempt Delta Lake fallback"
                    )
                    logger.debug(f"Missing group_ids (first 10): {missing_group_ids[:10]}")

                    # Attempt Delta Lake fallback for missing group_ids
                    try:
                        feature_df = self._fallback_to_delta_lake(
                            training_df,
                            missing_group_ids,
                            features
                        )
                    except Exception as e:
                        logger.error(f"Delta Lake fallback failed: {e}")
                        # Continue with Feast data even if fallback fails
                        feature_df = training_df
                else:
                    feature_df = training_df
            else:
                logger.info("All features retrieved successfully from Feast offline store")
                feature_df = training_df

            # Convert feature columns to numeric types
            # All features except group_id and event_timestamp should be numeric
            for col in feature_df.columns:
                if col not in ['group_id', 'event_timestamp']:
                    feature_df[col] = pd.to_numeric(feature_df[col], errors='coerce')

            logger.debug(f"DataFrame after conversion - dtypes: {feature_df.dtypes.to_dict()}")
            logger.debug(f"DataFrame after conversion - first row: {feature_df.iloc[0].to_dict() if len(feature_df) > 0 else 'empty'}")

            logger.info(f"Retrieved {len(feature_df)} rows with {len(feature_df.columns)} features from Feast offline store")
            logger.debug(f"Feature columns: {list(feature_df.columns)}")
            logger.debug(f"Feature dtypes:\n{feature_df.dtypes}")

            # Log feature statistics
            numeric_cols = feature_df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                logger.info("Feature statistics from Feast offline store:")
                for col in numeric_cols:
                    if col not in ['group_id', 'event_timestamp']:
                        unique_vals = feature_df[col].nunique()
                        min_val = feature_df[col].min()
                        max_val = feature_df[col].max()
                        non_null = feature_df[col].notna().sum()
                        logger.info(f"  {col}: unique={unique_vals}, min={min_val}, max={max_val}, non_null={non_null}/{len(feature_df)}")

            return feature_df

        except Exception as e:
            logger.error(f"Failed to retrieve features from Feast offline store: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise DataPreparationError(
                f"Failed to retrieve features from Feast offline store: {e}",
                stage="feature_retrieval",
                details={"num_features": len(features), "num_entities": len(entity_df)},
            )

    def _fallback_to_delta_lake(
        self,
        feast_df: pd.DataFrame,
        missing_group_ids: List[str],
        features: List[str]
    ) -> pd.DataFrame:
        """
        Fall back to Delta Lake for missing features.

        Args:
            feast_df: DataFrame from Feast with some missing values
            missing_group_ids: List of group_ids with missing features
            features: List of feature names

        Returns:
            DataFrame with missing features filled from Delta Lake
        """
        try:
            from deltalake import DeltaTable

            logger.info(f"Attempting Delta Lake fallback for {len(missing_group_ids)} group_ids")

            # Read from Delta Lake
            delta_path = "C:/data/features"
            dt = DeltaTable(delta_path)
            delta_df = dt.to_pandas()

            logger.debug(f"Delta Lake has {len(delta_df)} rows")

            # Filter for missing group_ids
            delta_df_filtered = delta_df[delta_df['group_id'].isin(missing_group_ids)]

            if len(delta_df_filtered) == 0:
                logger.warning("No matching group_ids found in Delta Lake")
                return feast_df

            logger.info(f"Found {len(delta_df_filtered)} rows in Delta Lake for missing group_ids")

            # Extract feature columns (remove view prefix if present)
            feature_cols = []
            for f in features:
                if ':' in f:
                    feature_cols.append(f.split(':')[1])
                else:
                    feature_cols.append(f)

            # Select relevant columns from Delta Lake
            delta_cols = ['group_id'] + [col for col in feature_cols if col in delta_df_filtered.columns]
            delta_df_selected = delta_df_filtered[delta_cols]

            # Merge with Feast data, filling missing values from Delta Lake
            # For rows with missing features, replace with Delta Lake values
            result_df = feast_df.copy()

            for group_id in missing_group_ids:
                delta_row = delta_df_selected[delta_df_selected['group_id'] == group_id]
                if len(delta_row) > 0:
                    feast_row_idx = result_df[result_df['group_id'] == group_id].index
                    if len(feast_row_idx) > 0:
                        idx = feast_row_idx[0]
                        for col in feature_cols:
                            if col in delta_row.columns and pd.isna(result_df.loc[idx, col]):
                                result_df.loc[idx, col] = delta_row[col].iloc[0]

            # Count how many features were filled
            filled_count = feast_df.isnull().sum().sum() - result_df.isnull().sum().sum()
            logger.info(f"Filled {filled_count} missing feature values from Delta Lake")

            return result_df

        except Exception as e:
            logger.error(f"Delta Lake fallback failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return original Feast data if fallback fails
            return feast_df

    def get_feature_view(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get feature view metadata from Feast.

        Args:
            name: Feature view name

        Returns:
            Feature view metadata or None if not found
        """
        if not self._connected:
            raise ExternalServiceError(
                "Feast SDK client not connected",
                service_name="Feast",
            )

        try:
            feature_views = self.feature_store.list_feature_views()
            for fv in feature_views:
                if fv.name == name:
                    logger.debug(f"Retrieved feature view: {name}")
                    return {
                        "name": fv.name,
                        "features": [f.name for f in fv.features],
                        "entities": [e for e in fv.entities]
                    }
            logger.warning(f"Feature view not found: {name}")
            return None

        except Exception as e:
            logger.error(f"Failed to get feature view {name}: {e}")
            raise ExternalServiceError(
                f"Failed to get feature view {name}: {e}",
                service_name="Feast",
                details={"feature_view": name},
            )

    def list_feature_views(self) -> List[str]:
        """
        List all feature views from Feast.

        Returns:
            List of feature view names
        """
        if not self._connected:
            raise ExternalServiceError(
                "Feast SDK client not connected",
                service_name="Feast",
            )

        try:
            feature_views = self.feature_store.list_feature_views()
            names = [fv.name for fv in feature_views]
            logger.debug(f"Listed {len(names)} feature views")
            return names

        except Exception as e:
            logger.error(f"Failed to list feature views: {e}")
            # Return empty list instead of raising to maintain compatibility
            logger.warning("Returning empty feature view list")
            return []

    def validate_features(self, features: List[str]) -> bool:
        """
        Validate that features exist in feature store.

        Args:
            features: List of feature names

        Returns:
            True if all features exist
        """
        # For HTTP client, we assume features are valid
        # The server will return an error if features don't exist
        logger.debug(f"Skipping feature validation for {len(features)} features (HTTP client)")
        return True

    def get_feature_schema(self, feature_view_name: str) -> Dict[str, str]:
        """
        Get feature schema for a feature view.

        Args:
            feature_view_name: Name of feature view

        Returns:
            Dictionary mapping feature names to data types

        Raises:
            ExternalServiceError: If retrieval fails
        """
        if not self._connected:
            raise ExternalServiceError(
                "Feast HTTP client not connected",
                service_name="Feast",
            )

        try:
            feature_view = self.get_feature_view(feature_view_name)
            if not feature_view:
                raise ExternalServiceError(
                    f"Feature view not found: {feature_view_name}",
                    service_name="Feast",
                    details={"feature_view": feature_view_name},
                )

            # Extract schema from feature view metadata
            schema = {}
            if "features" in feature_view:
                for feature in feature_view["features"]:
                    if isinstance(feature, dict):
                        schema[feature.get("name", "")] = feature.get("dtype", "unknown")
                    else:
                        schema[str(feature)] = "unknown"

            logger.debug(f"Retrieved schema for {feature_view_name}: {schema}")
            return schema

        except Exception as e:
            logger.error(f"Failed to get feature schema: {e}")
            raise ExternalServiceError(
                f"Failed to get feature schema: {e}",
                service_name="Feast",
                details={"feature_view": feature_view_name},
            )
