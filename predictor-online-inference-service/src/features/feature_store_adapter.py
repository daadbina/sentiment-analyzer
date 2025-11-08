"""
Feature Store Adapter for Predictor Online Inference Service.

Provides unified interface to Feast offline and online stores with
feature reconciliation, version tracking, and schema validation.
"""

import logging
from datetime import datetime
from typing import Any

from feast import FeatureStore

from ..config import FeastConfig
from ..exceptions import FeatureError
from ..metrics import MetricsCollector
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class FeatureStoreAdapter:
    """
    Unified adapter for Feast offline and online feature stores.

    Provides abstraction over Feast with feature reconciliation,
    version tracking, and schema validation.
    """

    def __init__(self, config: FeastConfig, metrics: MetricsCollector):
        """
        Initialize feature store adapter.

        Args:
            config: Feast configuration
            metrics: Metrics collector
        """
        self.config = config
        self.metrics = metrics
        self._store: FeatureStore | None = None
        self._feature_versions: dict[str, str] = {}

        logger.info("Initializing FeatureStoreAdapter", extra={"repo_path": config.repo_path})

    async def connect(self) -> None:
        """
        Connect to Feast feature store.

        Raises:
            FeatureError: If connection fails
        """
        try:
            logger.info("Connecting to Feast feature store")

            self._store = FeatureStore(repo_path=self.config.repo_path)

            # Verify connection by listing feature views
            feature_views = self._store.list_feature_views()

            logger.info(
                "Connected to Feast feature store",
                extra={
                    "feature_views_count": len(feature_views),
                    "feature_views": [fv.name for fv in feature_views],
                },
            )

        except Exception as e:
            logger.error(
                "Failed to connect to Feast feature store", extra={"error": str(e)}, exc_info=True
            )
            raise FeatureError(
                message=f"Failed to connect to Feast: {str(e)}",
                details={"repo_path": self.config.repo_path},
            ) from e

    @trace_span("feature_store_adapter.get_online_features")
    async def get_online_features(
        self,
        entity_rows: list[dict[str, Any]],
        feature_refs: list[str],
        trace_id: str | None = None,
    ) -> dict[str, list[Any]]:
        """
        Fetch features from online store.

        Args:
            entity_rows: List of entity dictionaries
            feature_refs: List of feature references (e.g., "feature_view:feature_name")
            trace_id: Trace ID for correlation

        Returns:
            Dictionary mapping feature names to lists of values

        Raises:
            FeatureError: If feature fetch fails
        """
        if not self._store:
            raise FeatureError(
                message="Feature store not connected", details={"operation": "get_online_features"}
            )

        try:
            start_time = datetime.now()

            logger.debug(
                "Fetching online features",
                extra={
                    "entity_count": len(entity_rows),
                    "feature_refs": feature_refs,
                    "trace_id": trace_id,
                },
            )

            # Fetch features from online store
            feature_vector = self._store.get_online_features(
                features=feature_refs, entity_rows=entity_rows
            )

            # Convert to dictionary
            result = feature_vector.to_dict()

            # Calculate latency
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Record metrics
            self.metrics.record_feature_fetch_latency(latency_ms, "online")

            logger.info(
                "Fetched online features",
                extra={
                    "entity_count": len(entity_rows),
                    "feature_count": len(feature_refs),
                    "latency_ms": latency_ms,
                    "trace_id": trace_id,
                },
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to fetch online features",
                extra={
                    "entity_count": len(entity_rows),
                    "feature_refs": feature_refs,
                    "error": str(e),
                    "trace_id": trace_id,
                },
                exc_info=True,
            )

            self.metrics.increment_feature_fetch_failures("online")

            raise FeatureError(
                message=f"Failed to fetch online features: {str(e)}",
                details={"entity_count": len(entity_rows), "feature_refs": feature_refs},
            ) from e

    @trace_span("feature_store_adapter.get_offline_features")
    async def get_offline_features(
        self,
        entity_df: Any,  # pandas DataFrame
        feature_refs: list[str],
        trace_id: str | None = None,
    ) -> Any:  # pandas DataFrame
        """
        Fetch features from offline store.

        Args:
            entity_df: Pandas DataFrame with entity keys and timestamps
            feature_refs: List of feature references
            trace_id: Trace ID for correlation

        Returns:
            Pandas DataFrame with features

        Raises:
            FeatureError: If feature fetch fails
        """
        if not self._store:
            raise FeatureError(
                message="Feature store not connected", details={"operation": "get_offline_features"}
            )

        try:
            start_time = datetime.now()

            logger.debug(
                "Fetching offline features",
                extra={
                    "entity_count": len(entity_df),
                    "feature_refs": feature_refs,
                    "trace_id": trace_id,
                },
            )

            # Fetch features from offline store
            training_df = self._store.get_historical_features(
                entity_df=entity_df, features=feature_refs
            ).to_df()

            # Calculate latency
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Record metrics
            self.metrics.record_feature_fetch_latency(latency_ms, "offline")

            logger.info(
                "Fetched offline features",
                extra={
                    "entity_count": len(entity_df),
                    "feature_count": len(feature_refs),
                    "result_count": len(training_df),
                    "latency_ms": latency_ms,
                    "trace_id": trace_id,
                },
            )

            return training_df

        except Exception as e:
            logger.error(
                "Failed to fetch offline features",
                extra={
                    "entity_count": len(entity_df),
                    "feature_refs": feature_refs,
                    "error": str(e),
                    "trace_id": trace_id,
                },
                exc_info=True,
            )

            self.metrics.increment_feature_fetch_failures("offline")

            raise FeatureError(
                message=f"Failed to fetch offline features: {str(e)}",
                details={"entity_count": len(entity_df), "feature_refs": feature_refs},
            ) from e

    def track_feature_version(self, feature_name: str, version: str) -> None:
        """
        Track feature version for audit trail.

        Args:
            feature_name: Name of the feature
            version: Version identifier
        """
        self._feature_versions[feature_name] = version

        logger.debug(
            "Tracked feature version", extra={"feature_name": feature_name, "version": version}
        )

    def get_feature_version(self, feature_name: str) -> str | None:
        """
        Get tracked version for a feature.

        Args:
            feature_name: Name of the feature

        Returns:
            Version identifier or None if not tracked
        """
        return self._feature_versions.get(feature_name)

    async def close(self) -> None:
        """Close feature store connection."""
        logger.info("Closing FeatureStoreAdapter")
        self._store = None
        self._feature_versions.clear()
