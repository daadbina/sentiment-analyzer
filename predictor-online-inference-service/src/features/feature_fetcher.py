"""
Feature fetcher for retrieving features from Feast online store via HTTP.

Provides high-level interface for fetching features with caching and validation.
Uses Feast HTTP client to retrieve features from remote Feast server.
"""

import logging
from datetime import datetime
from typing import Any

from ..clients.feast_http_client import FeastHTTPClient
from ..exceptions import FeatureFetchError
from ..metrics import feature_freshness_seconds
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


# Expected feature names from feature engineering service
# These match the feature names defined in feature-engineering-service/features.py
# Note: When reading from Redis, these are stored without the "semantic_group_features:" prefix
# All 28 features are required for model inference (24 base + 4 BTC)
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
    # BTC price features (4)
    "btc_change_pct_10h",
    "btc_volatility_score",
    "btc_volume",
    "btc_label_spike",
]


class FeatureFetcher:
    """
    High-level interface for fetching features from Feast online store via HTTP.

    Provides methods for retrieving features with proper error handling
    and metric collection. Uses Feast HTTP client to retrieve features from
    remote Feast server at 154.53.166.231:6566.
    """

    def __init__(
        self,
        feast_http_client: FeastHTTPClient,
        feature_view_name: str = "semantic_group_features",
    ):
        """
        Initialize feature fetcher.

        Args:
            feast_http_client: Feast HTTP client instance
            feature_view_name: Name of the feature view to query
        """
        self.feast_http_client = feast_http_client
        self.feature_view_name = feature_view_name

        logger.info(
            f"Initialized feature fetcher with Feast HTTP client: "
            f"feature_view={feature_view_name}"
        )

    async def fetch_online_features(
        self,
        group_id: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch features from Feast online store for a semantic group.

        Args:
            group_id: Semantic group ID
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Dictionary of feature values with semantic_group_features: prefix

        Raises:
            FeatureFetchError: If feature fetch fails

        Example:
            features = await fetcher.fetch_online_features("group_123")
            # Returns: {
            #     "semantic_group_features:num_sources": 5,
            #     "semantic_group_features:sentiment_mean": 0.75,
            #     "semantic_group_features:source_credibility_avg": 0.85,
            #     ...
            # }
        """
        with trace_span(
            "fetch_online_features",
            attributes={"group_id": group_id, "trace_id": trace_id},
        ):
            try:
                logger.info(
                    f"=== PREDICTOR: Fetching features from Feast HTTP ===",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

                # Prepare entity rows for Feast query
                entity_rows = [{"group_id": group_id}]

                # Fetch features from Feast via HTTP
                result = await self.feast_http_client.get_online_features(
                    feature_view_name=self.feature_view_name,
                    entity_rows=entity_rows,
                    features=None,  # Get all features
                )

                if not result or "features" not in result:
                    logger.error(f"No features returned from Feast for group_id={group_id}")
                    raise FeatureFetchError(
                        f"No features returned from Feast for group_id={group_id}",
                        group_id=group_id,
                        store_type="online",
                        trace_id=trace_id,
                    )

                # Extract features from result
                # Feast returns features in format: {"features": [{feature_name: value, ...}]}
                feature_data = result["features"][0] if result["features"] else {}

                logger.info(f"Raw feature data from Feast: {len(feature_data)} keys")
                logger.info(f"Raw feature keys: {list(feature_data.keys())[:20]}")  # First 20

                # Add the semantic_group_features: prefix to match training data format
                features = {}
                for feature_name in REQUIRED_FEATURES:
                    # Check both with and without prefix
                    if feature_name in feature_data:
                        prefixed_name = f"semantic_group_features:{feature_name}"
                        features[prefixed_name] = feature_data[feature_name]
                    elif f"semantic_group_features:{feature_name}" in feature_data:
                        # Already has prefix
                        prefixed_name = f"semantic_group_features:{feature_name}"
                        features[prefixed_name] = feature_data[prefixed_name]
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

                    logger.info(
                        f"Feature freshness: age_seconds={age_seconds:.2f}",
                        extra={"trace_id": trace_id, "group_id": group_id},
                    )

                # Log sample features for debugging
                logger.info(
                    f"=== PREDICTOR: Fetched {len(features)} features from Feast ===",
                    extra={
                        "trace_id": trace_id,
                        "group_id": group_id,
                        "feature_sample": {k: features[k] for k in list(features.keys())[:10]},
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
