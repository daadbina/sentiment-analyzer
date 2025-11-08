"""
Feast feature store client for Predictor Online Inference Service.

Provides abstraction over Feast online and offline stores for feature retrieval.
Supports both real-time and batch feature fetching with proper error handling.
"""

import logging
from datetime import datetime
from typing import Any

from feast import FeatureStore

from ..config import FeastConfig
from ..exceptions import FeatureFetchError
from ..metrics import MetricsCollector
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class FeastClient:
    """
    Client for interacting with Feast feature store.

    Provides methods for fetching features from online and offline stores.
    Handles connection management and error recovery.
    """

    def __init__(self, config: FeastConfig):
        """
        Initialize Feast client.

        Args:
            config: Feast configuration
        """
        self.config = config
        self._store: FeatureStore | None = None

        logger.info(f"Initializing Feast client: repo_path={config.repo_path}")

    async def connect(self) -> None:
        """
        Connect to Feast feature store.

        Raises:
            FeatureFetchError: If connection fails
        """
        try:
            logger.info("Connecting to Feast feature store")

            # Initialize feature store
            self._store = FeatureStore(repo_path=self.config.repo_path)

            logger.info(
                f"Connected to Feast feature store: "
                f"online_store={self.config.online_store_type}, "
                f"offline_store={self.config.offline_store_type}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Feast feature store: {e}", exc_info=True)
            raise FeatureFetchError(
                f"Failed to connect to Feast feature store: {e}",
                store_type="feast",
            )

    async def disconnect(self) -> None:
        """Disconnect from Feast feature store."""
        logger.info("Disconnecting from Feast feature store")
        self._store = None

    def _ensure_connected(self) -> FeatureStore:
        """
        Ensure client is connected.

        Returns:
            FeatureStore instance

        Raises:
            FeatureFetchError: If not connected
        """
        if self._store is None:
            raise FeatureFetchError(
                "Feast client not connected. Call connect() first.",
                store_type="feast",
            )
        return self._store

    async def get_online_features(
        self,
        feature_names: list[str],
        entity_rows: list[dict[str, Any]],
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch features from online store.

        Args:
            feature_names: List of feature names to fetch
            entity_rows: List of entity dictionaries (e.g., [{"group_id": "123"}])
            trace_id: Optional trace ID for distributed tracing

        Returns:
            List of feature dictionaries, one per entity row

        Raises:
            FeatureFetchError: If feature fetch fails

        Example:
            features = await client.get_online_features(
                feature_names=["feature_num_sources", "feature_sentiment_mean"],
                entity_rows=[{"group_id": "123"}],
            )
        """
        store = self._ensure_connected()

        with trace_span(
            "feast_get_online_features",
            attributes={
                "feature_count": len(feature_names),
                "entity_count": len(entity_rows),
                "trace_id": trace_id,
            },
        ):
            try:
                start_time = datetime.now()

                # Fetch features from online store
                feature_vector = store.get_online_features(
                    features=feature_names,
                    entity_rows=entity_rows,
                ).to_dict()

                # Calculate latency
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Record metrics
                MetricsCollector.record_feature_fetch_latency("online", latency_ms)

                # Convert to list of dictionaries
                result = []
                num_rows = len(entity_rows)

                for i in range(num_rows):
                    row = {}
                    for feature_name in feature_names:
                        if feature_name in feature_vector:
                            values = feature_vector[feature_name]
                            row[feature_name] = values[i] if i < len(values) else None
                    result.append(row)

                logger.debug(
                    f"Fetched online features: count={len(feature_names)}, "
                    f"entities={len(entity_rows)}, latency_ms={latency_ms:.2f}",
                    extra={"trace_id": trace_id, "latency_ms": latency_ms},
                )

                return result

            except Exception as e:
                logger.error(
                    f"Failed to fetch online features: {e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )

                # Record failure metrics
                for feature_name in feature_names:
                    MetricsCollector.record_feature_fetch_failure("online", feature_name)

                raise FeatureFetchError(
                    f"Failed to fetch online features: {e}",
                    feature_names=feature_names,
                    store_type="online",
                    trace_id=trace_id,
                )

    async def get_historical_features(
        self,
        feature_names: list[str],
        entity_df_dict: dict[str, list[Any]],
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch features from offline store.

        Args:
            feature_names: List of feature names to fetch
            entity_df_dict: Dictionary representing entity dataframe
                Example: {"group_id": ["123", "456"], "event_timestamp": [ts1, ts2]}
            trace_id: Optional trace ID for distributed tracing

        Returns:
            List of feature dictionaries

        Raises:
            FeatureFetchError: If feature fetch fails
        """
        store = self._ensure_connected()

        with trace_span(
            "feast_get_historical_features",
            attributes={
                "feature_count": len(feature_names),
                "entity_count": len(entity_df_dict.get("group_id", [])),
                "trace_id": trace_id,
            },
        ):
            try:
                import pandas as pd

                start_time = datetime.now()

                # Convert dict to pandas DataFrame
                entity_df = pd.DataFrame(entity_df_dict)

                # Fetch features from offline store
                training_df = store.get_historical_features(
                    features=feature_names,
                    entity_df=entity_df,
                ).to_df()

                # Calculate latency
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Record metrics
                MetricsCollector.record_feature_fetch_latency("offline", latency_ms)

                # Convert to list of dictionaries
                result = training_df.to_dict(orient="records")

                logger.debug(
                    f"Fetched historical features: count={len(feature_names)}, "
                    f"entities={len(entity_df)}, latency_ms={latency_ms:.2f}",
                    extra={"trace_id": trace_id, "latency_ms": latency_ms},
                )

                return result

            except Exception as e:
                logger.error(
                    f"Failed to fetch historical features: {e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )

                # Record failure metrics
                for feature_name in feature_names:
                    MetricsCollector.record_feature_fetch_failure("offline", feature_name)

                raise FeatureFetchError(
                    f"Failed to fetch historical features: {e}",
                    feature_names=feature_names,
                    store_type="offline",
                    trace_id=trace_id,
                )

    async def get_feature_view_names(self) -> list[str]:
        """
        Get list of available feature view names.

        Returns:
            List of feature view names
        """
        store = self._ensure_connected()

        try:
            feature_views = store.list_feature_views()
            return [fv.name for fv in feature_views]
        except Exception as e:
            logger.error(f"Failed to list feature views: {e}", exc_info=True)
            raise FeatureFetchError(
                f"Failed to list feature views: {e}",
                store_type="feast",
            )

    async def health_check(self) -> bool:
        """
        Check if Feast feature store is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            store = self._ensure_connected()
            # Try to list feature views as a health check
            store.list_feature_views()
            return True
        except Exception as e:
            logger.warning(f"Feast health check failed: {e}")
            return False
