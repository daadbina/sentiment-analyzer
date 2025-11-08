"""
Feature retrieval from Feast offline store.

Retrieves training features for model training.
"""

import logging
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd

from src.clients.feast_client import FeastClient
from src.config import config
from src.exceptions import DataPreparationError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class FeatureRetriever:
    """Retrieves features from Feast offline store."""

    def __init__(self, feast_client: FeastClient):
        """
        Initialize feature retriever.

        Args:
            feast_client: Feast client instance
        """
        self.feast_client = feast_client
        logger.info("Feature retriever initialized")

    def retrieve_features(
        self,
        entity_ids: List[str],
        start_date: datetime,
        end_date: datetime,
        features: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Retrieve features for entities in time range.

        Args:
            entity_ids: List of entity IDs (group IDs from semantic groups)
            start_date: Start date for feature retrieval
            end_date: End date for feature retrieval
            features: Optional list of specific features to retrieve

        Returns:
            DataFrame with features

        Raises:
            DataPreparationError: If retrieval fails
        """
        with tracer.start_as_current_span("retrieve_features") as span:
            span.set_attribute("num_entities", len(entity_ids))
            span.set_attribute("start_date", start_date.isoformat())
            span.set_attribute("end_date", end_date.isoformat())

            try:
                logger.info(
                    f"Retrieving features for {len(entity_ids)} entities "
                    f"from {start_date} to {end_date}"
                )
                logger.debug(f"Entity IDs (first 5): {entity_ids[:5]}")

                # Create entity dataframe with timestamps
                # Use group_id as entity (semantic groups from feature-engineering-service)
                # Ensure timestamps are datetime objects for Feast
                # Convert end_date to pandas Timestamp with UTC timezone to match Feast expectations
                if isinstance(end_date, str):
                    end_date_ts = pd.Timestamp(end_date, tz='UTC')
                else:
                    end_date_ts = pd.Timestamp(end_date, tz='UTC')

                entity_df = pd.DataFrame(
                    {
                        "group_id": entity_ids,
                        "timestamp": [end_date_ts] * len(entity_ids),
                    }
                )

                logger.debug(f"Entity dataframe shape: {entity_df.shape}")
                logger.debug(f"Entity dataframe dtypes:\n{entity_df.dtypes}")
                logger.debug(f"Entity dataframe sample:\n{entity_df.head()}")
                logger.debug(f"Timestamp column type: {type(entity_df['timestamp'].iloc[0])}")
                logger.debug(f"Timestamp value: {entity_df['timestamp'].iloc[0]}")
                logger.debug(f"Timestamp tzinfo: {entity_df['timestamp'].iloc[0].tzinfo}")

                # Get features from Feast
                feature_list = features or self._get_default_features()
                # Format features with feature view prefix for Feast
                formatted_features = [
                    f"semantic_group_features:{feature}" for feature in feature_list
                ]

                logger.info(f"Requesting {len(formatted_features)} features from Feast")
                logger.debug(f"Formatted features: {formatted_features}")

                feature_df = self.feast_client.get_features(
                    entity_df=entity_df,
                    features=formatted_features,
                    timestamp_column="timestamp",
                )

                logger.info(
                    f"Retrieved {feature_df.shape[0]} rows with "
                    f"{feature_df.shape[1]} features"
                )
                logger.debug(f"Feature columns: {list(feature_df.columns)}")
                logger.debug(f"Feature dataframe dtypes:\n{feature_df.dtypes}")

                # Check for null values
                null_counts = feature_df.isnull().sum()
                if null_counts.sum() > 0:
                    logger.warning(f"Found null values in features:\n{null_counts[null_counts > 0]}")
                else:
                    logger.info("No null values found in features")

                # Log data statistics
                numeric_cols = feature_df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    logger.debug(f"Feature statistics:\n{feature_df[numeric_cols].describe()}")

                return feature_df

            except Exception as e:
                logger.error(f"Feature retrieval failed: {e}", exc_info=True)
                raise DataPreparationError(
                    f"Feature retrieval failed: {e}",
                    stage="feature_retrieval",
                    details={
                        "num_entities": len(entity_ids),
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                )

    def _get_default_features(self) -> List[str]:
        """
        Get default feature list.

        Returns:
            List of feature names from feature-engineering-service
        """
        # These features are computed by feature-engineering-service
        # and stored in Feast offline store
        return [
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

    def validate_features(self, feature_df: pd.DataFrame) -> bool:
        """
        Validate feature dataframe.

        Args:
            feature_df: Feature dataframe

        Returns:
            True if valid, False otherwise

        Raises:
            DataPreparationError: If validation fails
        """
        with tracer.start_as_current_span("validate_features"):
            try:
                # Check for required columns
                # group_id is the entity from semantic groups
                required_cols = ["group_id", "timestamp"]
                missing_cols = [c for c in required_cols if c not in feature_df.columns]

                if missing_cols:
                    raise DataPreparationError(
                        f"Missing required columns: {missing_cols}",
                        stage="feature_validation",
                    )

                # Check for null values
                null_counts = feature_df.isnull().sum()
                if null_counts.sum() > 0:
                    logger.warning(f"Found null values: {null_counts[null_counts > 0]}")

                # Check data types
                numeric_cols = feature_df.select_dtypes(include=["number"]).columns
                logger.debug(f"Numeric columns: {list(numeric_cols)}")

                logger.info("Feature validation passed")
                return True

            except Exception as e:
                logger.error(f"Feature validation failed: {e}")
                raise DataPreparationError(
                    f"Feature validation failed: {e}",
                    stage="feature_validation",
                )

    def get_feature_statistics(self, feature_df: pd.DataFrame) -> dict:
        """
        Get statistics for features.

        Args:
            feature_df: Feature dataframe

        Returns:
            Dictionary with feature statistics
        """
        with tracer.start_as_current_span("get_feature_statistics"):
            try:
                numeric_cols = feature_df.select_dtypes(include=["number"]).columns

                stats = {
                    "num_rows": len(feature_df),
                    "num_features": len(feature_df.columns),
                    "numeric_features": len(numeric_cols),
                    "null_counts": feature_df.isnull().sum().to_dict(),
                    "mean_values": feature_df[numeric_cols].mean().to_dict(),
                    "std_values": feature_df[numeric_cols].std().to_dict(),
                    "min_values": feature_df[numeric_cols].min().to_dict(),
                    "max_values": feature_df[numeric_cols].max().to_dict(),
                }

                logger.debug(f"Feature statistics: {stats}")
                return stats

            except Exception as e:
                logger.error(f"Failed to compute feature statistics: {e}")
                raise DataPreparationError(
                    f"Failed to compute feature statistics: {e}",
                    stage="feature_statistics",
                )
