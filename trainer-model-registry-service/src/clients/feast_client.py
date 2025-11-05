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
            self.store = FeatureStore(repo_path=self.config.registry_path)
            logger.info("Feast feature store connected")
        except Exception as e:
            logger.error(f"Failed to connect to Feast: {e}")
            raise ExternalServiceError(
                f"Failed to connect to Feast: {e}",
                service_name="Feast",
                details={"registry_path": self.config.registry_path},
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

            # Get historical features
            feature_df = self.store.get_historical_features(
                entity_df=entity_df,
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
