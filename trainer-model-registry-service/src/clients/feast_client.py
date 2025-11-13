"""
Feast HTTP client for Trainer & Model Registry Service.

Provides integration with remote Feast feature server via HTTP API.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd
import requests
import asyncio
from functools import wraps

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
    """Feast HTTP client for remote feature server."""

    def __init__(self, config: FeastConfig, server_url: str = "http://154.53.166.231:6566"):
        """
        Initialize Feast HTTP client.

        Args:
            config: Feast configuration (kept for compatibility)
            server_url: URL of remote Feast feature server
        """
        self.config = config
        self.server_url = server_url.rstrip('/')
        self.timeout = 30
        self.max_retries = 3
        self._connected = False
        logger.info(f"Feast HTTP client initialized: server={self.server_url}")

    def connect(self) -> None:
        """
        Test connection to Feast feature server.

        Raises:
            ExternalServiceError: If connection fails
        """
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                self._connected = True
                logger.info("Feast HTTP feature server connected successfully")
            else:
                raise ExternalServiceError(
                    f"Feast server returned status {response.status_code}",
                    service_name="Feast",
                    details={"server_url": self.server_url, "status_code": response.status_code},
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Feast HTTP server: {e}")
            raise ExternalServiceError(
                f"Failed to connect to Feast HTTP server: {e}",
                service_name="Feast",
                details={"server_url": self.server_url},
            )

    def health_check(self) -> bool:
        """
        Check Feast connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5
            )
            is_healthy = response.status_code == 200
            if is_healthy:
                logger.debug("Feast health check passed")
            else:
                logger.warning(f"Feast health check failed: status {response.status_code}")
            return is_healthy
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
        Retrieve features from remote Feast server via HTTP.

        Args:
            entity_df: DataFrame with entity IDs and timestamps
            features: List of feature names to retrieve (format: "feature_view:feature_name")
            timestamp_column: Name of timestamp column (ignored for HTTP client)

        Returns:
            DataFrame with features

        Raises:
            DataPreparationError: If feature retrieval fails
        """
        if not self._connected:
            raise ExternalServiceError(
                "Feast HTTP client not connected",
                service_name="Feast",
            )

        try:
            logger.info(
                f"Retrieving {len(features)} features for {len(entity_df)} entities via HTTP"
            )

            # Extract entity IDs from DataFrame
            entity_ids = entity_df['group_id'].tolist()

            # Prepare entity rows for HTTP request
            # Convert UUID objects to strings for JSON serialization
            entity_rows = [{"group_id": str(entity_id)} for entity_id in entity_ids]

            # Prepare payload for HTTP request
            payload = {
                "features": features,
                "entities": entity_rows,
                "full_feature_names": True
            }

            logger.debug(f"HTTP request payload: {len(features)} features, {len(entity_rows)} entities")

            # Make HTTP request to Feast server
            response = requests.post(
                f"{self.server_url}/get-online-features",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Parse response
            data = response.json()

            # Convert to DataFrame
            if "results" in data:
                feature_df = pd.DataFrame(data["results"])
            elif isinstance(data, list):
                feature_df = pd.DataFrame(data)
            else:
                feature_df = pd.DataFrame([data])

            logger.info(f"Retrieved {len(feature_df)} rows with {len(feature_df.columns)} features via HTTP")
            logger.debug(f"Feature columns: {list(feature_df.columns)}")
            logger.debug(f"Feature dtypes:\n{feature_df.dtypes}")

            # Log feature statistics
            numeric_cols = feature_df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                logger.info("Feature statistics from Feast HTTP server:")
                for col in numeric_cols:
                    if col != 'group_id':
                        unique_vals = feature_df[col].nunique()
                        min_val = feature_df[col].min()
                        max_val = feature_df[col].max()
                        non_null = feature_df[col].notna().sum()
                        logger.info(f"  {col}: unique={unique_vals}, min={min_val}, max={max_val}, non_null={non_null}/{len(feature_df)}")

            return feature_df

        except requests.exceptions.Timeout:
            logger.error(f"Timeout retrieving features from Feast HTTP server")
            raise DataPreparationError(
                "Timeout retrieving features from Feast HTTP server",
                stage="feature_retrieval",
                details={"num_features": len(features), "num_entities": len(entity_df)},
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error retrieving features from Feast: {e}")
            raise DataPreparationError(
                f"HTTP error retrieving features from Feast: {e}",
                stage="feature_retrieval",
                details={"num_features": len(features), "num_entities": len(entity_df)},
            )
        except Exception as e:
            logger.error(f"Failed to retrieve features from Feast HTTP server: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise DataPreparationError(
                f"Failed to retrieve features from Feast HTTP server: {e}",
                stage="feature_retrieval",
                details={"num_features": len(features), "num_entities": len(entity_df)},
            )

    def get_feature_view(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get feature view metadata from remote server.

        Args:
            name: Feature view name

        Returns:
            Feature view metadata or None if not found

        Raises:
            ExternalServiceError: If retrieval fails
        """
        if not self._connected:
            raise ExternalServiceError(
                "Feast HTTP client not connected",
                service_name="Feast",
            )

        try:
            response = requests.get(
                f"{self.server_url}/feature-views/{name}",
                timeout=self.timeout
            )

            if response.status_code == 404:
                logger.warning(f"Feature view not found: {name}")
                return None

            response.raise_for_status()
            data = response.json()
            logger.debug(f"Retrieved feature view: {name}")
            return data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get feature view {name}: {e}")
            raise ExternalServiceError(
                f"Failed to get feature view {name}: {e}",
                service_name="Feast",
                details={"feature_view": name},
            )
        except Exception as e:
            logger.error(f"Failed to get feature view {name}: {e}")
            raise ExternalServiceError(
                f"Failed to get feature view {name}: {e}",
                service_name="Feast",
                details={"feature_view": name},
            )

    def list_feature_views(self) -> List[str]:
        """
        List all feature views from remote server.

        Returns:
            List of feature view names

        Raises:
            ExternalServiceError: If listing fails
        """
        if not self._connected:
            raise ExternalServiceError(
                "Feast HTTP client not connected",
                service_name="Feast",
            )

        try:
            response = requests.get(
                f"{self.server_url}/feature-views",
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            names = data.get("feature_views", [])
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
            True if all features exist (always returns True for HTTP client)
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
