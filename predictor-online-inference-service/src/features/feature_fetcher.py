"""
Feature fetcher for retrieving features from Feast feature store.

Provides high-level interface for fetching features with caching and validation.
Handles both online and offline feature retrieval.
"""

import logging
from datetime import datetime
from typing import Any

from ..clients import FeastClient
from ..exceptions import FeatureFetchError
from ..metrics import feature_freshness_seconds
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


# Expected feature names from feature engineering service
REQUIRED_FEATURES = [
    "feature_num_sources",
    "feature_sentiment_mean",
    "feature_credibility_mean",
    "feature_entities",
    "feature_time_density",
]


class FeatureFetcher:
    """
    High-level interface for fetching features from Feast.

    Provides methods for retrieving features with proper error handling
    and metric collection.
    """

    def __init__(self, feast_client: FeastClient):
        """
        Initialize feature fetcher.

        Args:
            feast_client: Feast client instance
        """
        self.feast_client = feast_client

        logger.info("Initialized feature fetcher")

    async def fetch_online_features(
        self,
        group_id: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch features from online store for a semantic group.

        Args:
            group_id: Semantic group ID
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Dictionary of feature values

        Raises:
            FeatureFetchError: If feature fetch fails

        Example:
            features = await fetcher.fetch_online_features("group_123")
            # Returns: {
            #     "feature_num_sources": 5,
            #     "feature_sentiment_mean": 0.75,
            #     "feature_credibility_mean": 0.85,
            #     "feature_entities": ["entity1", "entity2"],
            #     "feature_time_density": 0.5,
            #     "feature_timestamp": "2025-11-07T12:00:00Z",
            # }
        """
        with trace_span(
            "fetch_online_features",
            attributes={"group_id": group_id, "trace_id": trace_id},
        ):
            try:
                logger.debug(
                    f"Fetching online features: group_id={group_id}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

                # Prepare entity rows
                entity_rows = [{"group_id": group_id}]

                # Fetch features from Feast online store
                feature_rows = await self.feast_client.get_online_features(
                    feature_names=REQUIRED_FEATURES,
                    entity_rows=entity_rows,
                    trace_id=trace_id,
                )

                if not feature_rows:
                    raise FeatureFetchError(
                        f"No features returned for group_id={group_id}",
                        group_id=group_id,
                        store_type="online",
                        trace_id=trace_id,
                    )

                features = feature_rows[0]

                # Check for feature freshness
                if "feature_timestamp" in features:
                    feature_timestamp = datetime.fromisoformat(features["feature_timestamp"])
                    age_seconds = (datetime.utcnow() - feature_timestamp).total_seconds()
                    feature_freshness_seconds.labels(group_id=group_id).set(age_seconds)

                    logger.debug(
                        f"Feature freshness: group_id={group_id}, age_seconds={age_seconds:.2f}",
                        extra={"trace_id": trace_id, "group_id": group_id},
                    )

                logger.debug(
                    f"Fetched online features: group_id={group_id}, "
                    f"feature_count={len(features)}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

                return features

            except FeatureFetchError:
                raise
            except Exception as e:
                logger.error(
                    f"Failed to fetch online features: group_id={group_id}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise FeatureFetchError(
                    f"Failed to fetch online features: {e}",
                    group_id=group_id,
                    store_type="online",
                    trace_id=trace_id,
                )

    async def fetch_historical_features(
        self,
        group_ids: list[str],
        timestamps: list[datetime],
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch features from offline store for multiple semantic groups.

        Args:
            group_ids: List of semantic group IDs
            timestamps: List of timestamps for point-in-time feature retrieval
            trace_id: Optional trace ID for distributed tracing

        Returns:
            List of feature dictionaries, one per group

        Raises:
            FeatureFetchError: If feature fetch fails
        """
        with trace_span(
            "fetch_historical_features",
            attributes={
                "group_count": len(group_ids),
                "trace_id": trace_id,
            },
        ):
            try:
                logger.debug(
                    f"Fetching historical features: group_count={len(group_ids)}",
                    extra={"trace_id": trace_id},
                )

                # Prepare entity dataframe
                entity_df_dict = {
                    "group_id": group_ids,
                    "event_timestamp": timestamps,
                }

                # Fetch features from Feast offline store
                feature_rows = await self.feast_client.get_historical_features(
                    feature_names=REQUIRED_FEATURES,
                    entity_df_dict=entity_df_dict,
                    trace_id=trace_id,
                )

                logger.debug(
                    f"Fetched historical features: group_count={len(group_ids)}, "
                    f"row_count={len(feature_rows)}",
                    extra={"trace_id": trace_id},
                )

                return feature_rows

            except FeatureFetchError:
                raise
            except Exception as e:
                logger.error(
                    f"Failed to fetch historical features: error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise FeatureFetchError(
                    f"Failed to fetch historical features: {e}",
                    store_type="offline",
                    trace_id=trace_id,
                )

    async def fetch_batch_online_features(
        self,
        group_ids: list[str],
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch features from online store for multiple semantic groups.

        Args:
            group_ids: List of semantic group IDs
            trace_id: Optional trace ID for distributed tracing

        Returns:
            List of feature dictionaries, one per group

        Raises:
            FeatureFetchError: If feature fetch fails
        """
        with trace_span(
            "fetch_batch_online_features",
            attributes={
                "group_count": len(group_ids),
                "trace_id": trace_id,
            },
        ):
            try:
                logger.debug(
                    f"Fetching batch online features: group_count={len(group_ids)}",
                    extra={"trace_id": trace_id},
                )

                # Prepare entity rows
                entity_rows = [{"group_id": gid} for gid in group_ids]

                # Fetch features from Feast online store
                feature_rows = await self.feast_client.get_online_features(
                    feature_names=REQUIRED_FEATURES,
                    entity_rows=entity_rows,
                    trace_id=trace_id,
                )

                logger.debug(
                    f"Fetched batch online features: group_count={len(group_ids)}, "
                    f"row_count={len(feature_rows)}",
                    extra={"trace_id": trace_id},
                )

                return feature_rows

            except FeatureFetchError:
                raise
            except Exception as e:
                logger.error(
                    f"Failed to fetch batch online features: error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise FeatureFetchError(
                    f"Failed to fetch batch online features: {e}",
                    store_type="online",
                    trace_id=trace_id,
                )

    def get_required_features(self) -> list[str]:
        """
        Get list of required feature names.

        Returns:
            List of required feature names
        """
        return REQUIRED_FEATURES.copy()

