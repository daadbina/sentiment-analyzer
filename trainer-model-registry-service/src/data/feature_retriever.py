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
            entity_ids: List of entity IDs (article IDs)
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

                # Create entity dataframe with timestamps
                entity_df = pd.DataFrame(
                    {
                        "article_id": entity_ids,
                        "timestamp": [end_date] * len(entity_ids),
                    }
                )

                # Get features from Feast
                feature_df = self.feast_client.get_features(
                    entity_df=entity_df,
                    features=features or self._get_default_features(),
                    timestamp_column="timestamp",
                )

                logger.info(
                    f"Retrieved {feature_df.shape[0]} rows with "
                    f"{feature_df.shape[1]} features"
                )
                logger.debug(f"Feature columns: {list(feature_df.columns)}")

                return feature_df

            except Exception as e:
                logger.error(f"Feature retrieval failed: {e}")
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
            List of feature names
        """
        # These should match features defined in Feast registry
        return [
            "article_features__word_count",
            "article_features__sentence_count",
            "article_features__avg_word_length",
            "article_features__language_confidence",
            "article_features__source_credibility",
            "article_features__publication_frequency",
            "temporal_features__hour_of_day",
            "temporal_features__day_of_week",
            "temporal_features__month_of_year",
            "temporal_features__days_since_publication",
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
                required_cols = ["article_id", "timestamp"]
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
