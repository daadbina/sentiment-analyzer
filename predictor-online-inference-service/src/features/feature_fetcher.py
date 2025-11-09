"""
Feature fetcher for retrieving features from Redis online store.

Provides high-level interface for fetching features with caching and validation.
Reads features directly from Redis using the same format as feature-engineering-service.
"""

import logging
from datetime import datetime
from typing import Any

from ..clients import FeastClient, RedisClient
from ..exceptions import FeatureFetchError
from ..metrics import feature_freshness_seconds
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


# Expected feature names from feature engineering service
# These match the feature names defined in feature-engineering-service/features.py
# Note: When reading from Redis, these are stored without the "semantic_group_features:" prefix
# All 24 features are required for model inference
REQUIRED_FEATURES = [
    # Source features (4)
    "num_sources",
    "source_credibility_avg",
    "source_credibility_std",
    "source_diversity_score",
    # Temporal features (4)
    "time_span_hours",
    "publication_velocity",
    "temporal_concentration",
    "days_since_first_article",
    # Sentiment features (4)
    "sentiment_mean",
    "sentiment_std",
    "sentiment_polarity_ratio",
    "sentiment_volatility",
    # Entity features (4)
    "entity_count",
    "entity_diversity",
    "entity_prominence",
    "entity_concentration",
    # Content features (4)
    "avg_word_count",
    "avg_title_length",
    "language_diversity",
    "domain_diversity",
    # Embedding features (4)
    "centroid_magnitude",
    "intra_cluster_similarity_mean",
    "intra_cluster_similarity_std",
    "embedding_drift_score",
]


class FeatureFetcher:
    """
    High-level interface for fetching features from Redis online store.

    Provides methods for retrieving features with proper error handling
    and metric collection. Reads features directly from Redis using the
    key format: features:{group_id}
    """

    def __init__(self, feast_client: FeastClient, redis_client: RedisClient):
        """
        Initialize feature fetcher.

        Args:
            feast_client: Feast client instance (for historical features)
            redis_client: Redis client instance (for online features)
        """
        self.feast_client = feast_client
        self.redis_client = redis_client

        logger.info("Initialized feature fetcher with Redis online store")

    async def fetch_online_features(
        self,
        group_id: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch features from Redis online store for a semantic group.

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
            #     "num_sources": 5,
            #     "sentiment_mean": 0.75,
            #     "source_credibility_avg": 0.85,
            #     "entity_count": 10,
            #     "temporal_concentration": 0.5,
            #     "feature_timestamp": "2025-11-07T12:00:00Z",
            # }
        """
        with trace_span(
            "fetch_online_features",
            attributes={"group_id": group_id, "trace_id": trace_id},
        ):
            try:
                logger.debug(
                    f"Fetching online features from Redis: group_id={group_id}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

                # Fetch features directly from Redis using the same key format
                # as feature-engineering-service: features:{group_id}
                redis_key = f"features:{group_id}"
                feature_data = await self.redis_client.get(redis_key, trace_id=trace_id)

                if not feature_data:
                    raise FeatureFetchError(
                        f"No features found in Redis for group_id={group_id}",
                        group_id=group_id,
                        store_type="online",
                        trace_id=trace_id,
                    )

                # Extract only the required features
                # Add the semantic_group_features: prefix to match training data format
                features = {}
                for feature_name in REQUIRED_FEATURES:
                    if feature_name in feature_data:
                        # Add prefix to match the format used during training
                        prefixed_name = f"semantic_group_features:{feature_name}"
                        features[prefixed_name] = feature_data[feature_name]
                    else:
                        logger.warning(
                            f"Missing feature: {feature_name} for group_id={group_id}",
                            extra={"trace_id": trace_id, "group_id": group_id},
                        )

                # Check for feature freshness
                if "timestamp" in feature_data:
                    feature_timestamp = datetime.fromisoformat(feature_data["timestamp"])
                    age_seconds = (datetime.utcnow() - feature_timestamp).total_seconds()
                    feature_freshness_seconds.labels(group_id=group_id).set(age_seconds)

                    logger.debug(
                        f"Feature freshness: group_id={group_id}, age_seconds={age_seconds:.2f}",
                        extra={"trace_id": trace_id, "group_id": group_id},
                    )

                # Log sample features for debugging
                logger.info(
                    f"Fetched {len(features)} raw features from Redis: group_id={group_id}",
                    extra={
                        "trace_id": trace_id,
                        "group_id": group_id,
                        "feature_sample": {k: features[k] for k in list(features.keys())[:5]},
                        "all_features": features,
                    },
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
        Fetch features from Redis online store for multiple semantic groups.

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
                    f"Fetching batch online features from Redis: group_count={len(group_ids)}",
                    extra={"trace_id": trace_id},
                )

                # Fetch features for each group from Redis
                feature_rows = []
                for group_id in group_ids:
                    features = await self.fetch_online_features(group_id, trace_id=trace_id)
                    feature_rows.append(features)

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
