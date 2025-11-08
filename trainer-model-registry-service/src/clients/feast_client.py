"""
Feast client for Trainer & Model Registry Service.

Provides integration with Feast offline feature store.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd
from feast import FeatureStore

from src.config import FeastConfig
from src.exceptions import ExternalServiceError, DataPreparationError

logger = logging.getLogger(__name__)


class FeastClient:
    """Feast feature store client."""

    def __init__(self, config: FeastConfig):
        """
        Initialize Feast client.

        Args:
            config: Feast configuration
        """
        self.config = config
        self.store: Optional[FeatureStore] = None
        logger.info(f"Feast client initialized with registry: {config.registry_path}")

    def connect(self) -> None:
        """
        Initialize Feast feature store.

        Raises:
            ExternalServiceError: If connection fails
        """
        try:
            self.store = FeatureStore(repo_path=self.config.repo_path)
            logger.info("Feast feature store connected")
        except Exception as e:
            logger.error(f"Failed to connect to Feast: {e}")
            raise ExternalServiceError(
                f"Failed to connect to Feast: {e}",
                service_name="Feast",
                details={"repo_path": self.config.repo_path, "registry_path": self.config.registry_path},
            )

    def health_check(self) -> bool:
        """
        Check Feast connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.store:
            logger.warning("Feast store not initialized")
            return False

        try:
            # Try to list feature views
            _ = self.store.list_feature_views()
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
        Retrieve features from offline store.

        Args:
            entity_df: DataFrame with entity IDs and timestamps
            features: List of feature names to retrieve
            timestamp_column: Name of timestamp column

        Returns:
            DataFrame with features

        Raises:
            DataPreparationError: If feature retrieval fails
        """
        if not self.store:
            raise ExternalServiceError(
                "Feast store not initialized",
                service_name="Feast",
            )

        try:
            logger.info(
                f"Retrieving {len(features)} features for {len(entity_df)} entities"
            )

            # Try to retrieve from online store first (faster, more reliable)
            # If that fails, fall back to offline store
            print(f"[FEAST_CLIENT] get_features called with {len(features)} features and {len(entity_df)} entities")
            try:
                print("[FEAST_CLIENT] Attempting to retrieve features from online store")
                logger.info("Attempting to retrieve features from online store")
                feature_df = self._get_features_from_online_store(entity_df, features)
                print(f"[FEAST_CLIENT] Retrieved {len(feature_df)} rows from online store")
                logger.info(f"Retrieved {len(feature_df)} rows from online store")
                logger.info(f"Feature columns: {list(feature_df.columns)}")
                logger.info(f"Feature dtypes:\n{feature_df.dtypes}")
                logger.info(f"Feature sample:\n{feature_df.head()}")
                return feature_df
            except Exception as e:
                print(f"[FEAST_CLIENT] Exception in online store retrieval: {e}")
                logger.warning(f"Failed to retrieve from online store: {e}, falling back to offline store")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")

                # Fall back to offline store
                logger.debug("Attempting to retrieve features from offline store")
                entity_df_copy = entity_df.copy()
                if timestamp_column in entity_df_copy.columns and timestamp_column != "event_timestamp":
                    entity_df_copy = entity_df_copy.rename(columns={timestamp_column: "event_timestamp"})
                    logger.debug(f"Renamed {timestamp_column} to event_timestamp")

                logger.debug(f"Entity dataframe columns: {list(entity_df_copy.columns)}")
                logger.debug(f"Entity dataframe dtypes:\n{entity_df_copy.dtypes}")

                # Get historical features
                feature_df = self.store.get_historical_features(
                    entity_df=entity_df_copy,
                    features=features,
                    full_feature_names=True,
                ).to_df()

                logger.info(f"Retrieved features with shape: {feature_df.shape}")
                logger.debug(f"Feature columns: {list(feature_df.columns)}")

                return feature_df

        except Exception as e:
            logger.error(f"Failed to retrieve features from Feast: {e}")
            raise DataPreparationError(
                f"Failed to retrieve features from Feast: {e}",
                stage="feature_retrieval",
                details={"num_features": len(features), "num_entities": len(entity_df)},
            )

    def _get_features_from_online_store(
        self,
        entity_df: pd.DataFrame,
        features: List[str],
    ) -> pd.DataFrame:
        """
        Retrieve features from online store (Redis).

        Args:
            entity_df: DataFrame with entity IDs
            features: List of feature names to retrieve

        Returns:
            DataFrame with features

        Raises:
            Exception: If retrieval fails
        """
        import redis
        import json

        print(f"[ONLINE_STORE] _get_features_from_online_store called")
        # Connect to Redis
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Extract entity IDs
        entity_ids = entity_df['group_id'].tolist()
        print(f"[ONLINE_STORE] Retrieving features for {len(entity_ids)} entities from Redis")
        logger.info(f"Retrieving features for {len(entity_ids)} entities from Redis")
        logger.info(f"Requested features: {features}")

        # Retrieve features from Redis
        feature_data = []
        found_count = 0
        for i, entity_id in enumerate(entity_ids):
            row_data = {"group_id": entity_id}

            # Feature key format: features:{entity_id}
            # The value is a JSON object with all features
            feature_key = f"features:{entity_id}"

            try:
                value = redis_client.get(feature_key)
                if i == 0:
                    print(f"[ONLINE_STORE] First entity: {entity_id}, key: {feature_key}, value exists: {value is not None}")
                if value is not None:
                    found_count += 1
                    try:
                        features_dict = json.loads(value)
                        if i == 0:
                            print(f"[ONLINE_STORE] First entity features: {list(features_dict.keys())}")
                        logger.info(f"Found features for {entity_id}: {list(features_dict.keys())[:5]}...")
                        # Extract requested features
                        for feature in features:
                            # Feature name format: semantic_group_features:feature_name
                            feature_name = feature.split(':')[-1]
                            if feature_name in features_dict:
                                row_data[feature] = features_dict[feature_name]
                            else:
                                logger.warning(f"Feature {feature_name} not found in Redis for {entity_id}")
                                row_data[feature] = None
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON for {feature_key}: {e}")
                        for feature in features:
                            row_data[feature] = None
                else:
                    if i == 0:
                        print(f"[ONLINE_STORE] First entity: {entity_id}, key: {feature_key}, NO VALUE FOUND")
                    logger.info(f"No features found for entity {entity_id} (key: {feature_key})")
                    for feature in features:
                        row_data[feature] = None
            except Exception as e:
                logger.warning(f"Failed to retrieve {feature_key}: {e}")
                for feature in features:
                    row_data[feature] = None

            feature_data.append(row_data)

        logger.info(f"Found features for {found_count} out of {len(entity_ids)} entities")

        # Create DataFrame
        feature_df = pd.DataFrame(feature_data)
        logger.info(f"Retrieved {len(feature_df)} rows from online store")
        logger.info(f"Feature columns: {list(feature_df.columns)}")
        logger.info(f"Feature dtypes:\n{feature_df.dtypes}")

        return feature_df

    def get_feature_view(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get feature view metadata.

        Args:
            name: Feature view name

        Returns:
            Feature view metadata or None if not found

        Raises:
            ExternalServiceError: If retrieval fails
        """
        if not self.store:
            raise ExternalServiceError(
                "Feast store not initialized",
                service_name="Feast",
            )

        try:
            feature_view = self.store.get_feature_view(name)
            logger.debug(f"Retrieved feature view: {name}")
            return {
                "name": feature_view.name,
                "entities": feature_view.entities,
                "features": [f.name for f in feature_view.features],
                "ttl": feature_view.ttl,
            }
        except Exception as e:
            logger.error(f"Failed to get feature view {name}: {e}")
            raise ExternalServiceError(
                f"Failed to get feature view {name}: {e}",
                service_name="Feast",
                details={"feature_view": name},
            )

    def list_feature_views(self) -> List[str]:
        """
        List all feature views.

        Returns:
            List of feature view names

        Raises:
            ExternalServiceError: If listing fails
        """
        if not self.store:
            raise ExternalServiceError(
                "Feast store not initialized",
                service_name="Feast",
            )

        try:
            feature_views = self.store.list_feature_views()
            names = [fv.name for fv in feature_views]
            logger.debug(f"Listed {len(names)} feature views")
            return names
        except Exception as e:
            logger.error(f"Failed to list feature views: {e}")
            raise ExternalServiceError(
                f"Failed to list feature views: {e}",
                service_name="Feast",
            )

    def validate_features(self, features: List[str]) -> bool:
        """
        Validate that features exist in feature store.

        Args:
            features: List of feature names

        Returns:
            True if all features exist, False otherwise

        Raises:
            ExternalServiceError: If validation fails
        """
        if not self.store:
            raise ExternalServiceError(
                "Feast store not initialized",
                service_name="Feast",
            )

        try:
            # Get all available features
            all_features = []
            for fv in self.store.list_feature_views():
                for feature in fv.features:
                    all_features.append(f"{fv.name}__{feature.name}")

            missing_features = [f for f in features if f not in all_features]

            if missing_features:
                logger.warning(f"Missing features: {missing_features}")
                return False

            logger.debug(f"All {len(features)} features validated")
            return True

        except Exception as e:
            logger.error(f"Feature validation failed: {e}")
            raise ExternalServiceError(
                f"Feature validation failed: {e}",
                service_name="Feast",
                details={"num_features": len(features)},
            )

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
        if not self.store:
            raise ExternalServiceError(
                "Feast store not initialized",
                service_name="Feast",
            )

        try:
            feature_view = self.store.get_feature_view(feature_view_name)
            schema = {f.name: str(f.dtype) for f in feature_view.features}
            logger.debug(f"Retrieved schema for {feature_view_name}: {schema}")
            return schema
        except Exception as e:
            logger.error(f"Failed to get feature schema: {e}")
            raise ExternalServiceError(
                f"Failed to get feature schema: {e}",
                service_name="Feast",
                details={"feature_view": feature_view_name},
            )
