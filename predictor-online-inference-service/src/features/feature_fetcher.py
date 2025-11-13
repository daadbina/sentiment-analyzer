"""
Feature fetcher for retrieving features from parquet files.

Provides high-level interface for fetching features with caching and validation.
Reads features directly from parquet files instead of Feast online store.
"""

import logging
from datetime import datetime
from typing import Any

from ..data.parquet_loader import ParquetFeatureLoader
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
    High-level interface for fetching features from parquet files.

    Provides methods for retrieving features with proper error handling
    and metric collection. Reads features directly from parquet files.
    """

    def __init__(
        self,
        parquet_loader: ParquetFeatureLoader,
        feature_view_name: str = "semantic_group_features",
    ):
        """
        Initialize feature fetcher.

        Args:
            parquet_loader: Parquet feature loader instance
            feature_view_name: Name of the feature view (for compatibility)
        """
        self.parquet_loader = parquet_loader
        self.feature_view_name = feature_view_name

        logger.info(
            f"Initialized feature fetcher with parquet loader: "
            f"feature_view={feature_view_name}"
        )

    async def fetch_online_features(
        self,
        group_id: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch features from parquet file for a semantic group.

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
                    f"=== PREDICTOR: Fetching features from parquet file ===",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

                # Fetch features from parquet file
                feature_data = self.parquet_loader.get_semantic_group_features(group_id)

                logger.info(f"Raw feature data from parquet: {len(feature_data)} keys")
                logger.debug(f"Raw feature keys: {list(feature_data.keys())[:20]}")  # First 20

                # Add the semantic_group_features: prefix to match training data format
                features = {}
                for feature_name in REQUIRED_FEATURES:
                    if feature_name in feature_data:
                        prefixed_name = f"semantic_group_features:{feature_name}"
                        features[prefixed_name] = feature_data[feature_name]
                    else:
                        logger.warning(
                            f"Missing feature: {feature_name} for group_id={group_id}",
                            extra={"trace_id": trace_id, "group_id": group_id},
                        )

                # Also include metadata fields (countries, has_conflict) without prefix
                for metadata_field in ["countries", "has_conflict"]:
                    if metadata_field in feature_data:
                        features[metadata_field] = feature_data[metadata_field]

                # Log sample features for debugging
                logger.info(
                    f"=== PREDICTOR: Fetched {len(features)} features from parquet ===",
                    extra={
                        "trace_id": trace_id,
                        "group_id": group_id,
                        "feature_sample": {k: features[k] for k in list(features.keys())[:10]},
                    },
                )

                return features

            except FeatureFetchError:
                raise
            except ValueError as e:
                # Group ID not found in parquet
                logger.error(
                    f"Group ID not found in parquet: group_id={group_id}, error={e}",
                    extra={"trace_id": trace_id},
                )
                raise FeatureFetchError(
                    f"Group ID not found: {e}",
                    group_id=group_id,
                    store_type="parquet",
                    trace_id=trace_id,
                )
            except Exception as e:
                logger.error(
                    f"Failed to fetch features from parquet: group_id={group_id}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise FeatureFetchError(
                    f"Failed to fetch features from parquet: {e}",
                    group_id=group_id,
                    store_type="parquet",
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
        Fetch features from parquet file for multiple semantic groups.

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
                    f"Fetching batch features from parquet: group_count={len(group_ids)}",
                    extra={"trace_id": trace_id},
                )

                # Fetch features for each group from parquet
                feature_rows = []
                for group_id in group_ids:
                    features = await self.fetch_online_features(group_id, trace_id=trace_id)
                    feature_rows.append(features)

                logger.debug(
                    f"Fetched batch features: group_count={len(group_ids)}, "
                    f"row_count={len(feature_rows)}",
                    extra={"trace_id": trace_id},
                )

                return feature_rows

            except FeatureFetchError:
                raise
            except Exception as e:
                logger.error(
                    f"Failed to fetch batch features: error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise FeatureFetchError(
                    f"Failed to fetch batch features: {e}",
                    store_type="parquet",
                    trace_id=trace_id,
                )

    def get_required_features(self) -> list[str]:
        """
        Get list of required feature names.

        Returns:
            List of required feature names
        """
        return REQUIRED_FEATURES.copy()
