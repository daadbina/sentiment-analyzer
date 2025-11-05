"""
Label retrieval from PostgreSQL ground truth table.

Retrieves ground-truth labels for model training.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd
import asyncio

from src.clients.postgres_client import PostgreSQLClient
from src.config import config
from src.exceptions import DataPreparationError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class LabelRetriever:
    """Retrieves labels from PostgreSQL ground truth table."""

    def __init__(self, postgres_client: PostgreSQLClient):
        """
        Initialize label retriever.

        Args:
            postgres_client: PostgreSQL client instance
        """
        self.postgres_client = postgres_client
        logger.info("Label retriever initialized")

    async def retrieve_labels(
        self,
        start_date: datetime,
        end_date: datetime,
        label_column: str = "sentiment",
    ) -> pd.DataFrame:
        """
        Retrieve labels from PostgreSQL.

        Args:
            start_date: Start date for label retrieval
            end_date: End date for label retrieval
            label_column: Name of label column

        Returns:
            DataFrame with labels

        Raises:
            DataPreparationError: If retrieval fails
        """
        with tracer.start_as_current_span("retrieve_labels") as span:
            span.set_attribute("start_date", start_date.isoformat())
            span.set_attribute("end_date", end_date.isoformat())
            span.set_attribute("label_column", label_column)

            try:
                logger.info(f"Retrieving labels from {start_date} to {end_date}")

                # Query labels from PostgreSQL
                query = """
                    SELECT 
                        article_id,
                        sentiment,
                        confidence,
                        created_at
                    FROM ground_truth
                    WHERE created_at >= $1 AND created_at <= $2
                    ORDER BY created_at DESC
                """

                rows = await self.postgres_client.fetch_all(
                    query,
                    start_date,
                    end_date,
                )

                if not rows:
                    logger.warning(
                        f"No labels found for period {start_date} to {end_date}"
                    )
                    return pd.DataFrame()

                # Convert to DataFrame
                label_df = pd.DataFrame(rows)
                logger.info(f"Retrieved {len(label_df)} labels")
                logger.debug(f"Label columns: {list(label_df.columns)}")

                return label_df

            except Exception as e:
                logger.error(f"Label retrieval failed: {e}")
                raise DataPreparationError(
                    f"Label retrieval failed: {e}",
                    stage="label_retrieval",
                    details={
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                )

    async def retrieve_labels_for_entities(
        self,
        entity_ids: List[str],
    ) -> pd.DataFrame:
        """
        Retrieve labels for specific entities.

        Args:
            entity_ids: List of entity IDs (article IDs)

        Returns:
            DataFrame with labels

        Raises:
            DataPreparationError: If retrieval fails
        """
        with tracer.start_as_current_span("retrieve_labels_for_entities") as span:
            span.set_attribute("num_entities", len(entity_ids))

            try:
                logger.info(f"Retrieving labels for {len(entity_ids)} entities")

                # Create placeholders for SQL IN clause
                placeholders = ", ".join(f"${i+1}" for i in range(len(entity_ids)))
                query = f"""
                    SELECT 
                        article_id,
                        sentiment,
                        confidence,
                        created_at
                    FROM ground_truth
                    WHERE article_id IN ({placeholders})
                    ORDER BY created_at DESC
                """

                rows = await self.postgres_client.fetch_all(query, *entity_ids)

                if not rows:
                    logger.warning(f"No labels found for {len(entity_ids)} entities")
                    return pd.DataFrame()

                label_df = pd.DataFrame(rows)
                logger.info(f"Retrieved {len(label_df)} labels for entities")

                return label_df

            except Exception as e:
                logger.error(f"Label retrieval for entities failed: {e}")
                raise DataPreparationError(
                    f"Label retrieval for entities failed: {e}",
                    stage="label_retrieval",
                    details={"num_entities": len(entity_ids)},
                )

    async def validate_labels(self, label_df: pd.DataFrame) -> bool:
        """
        Validate label dataframe.

        Args:
            label_df: Label dataframe

        Returns:
            True if valid, False otherwise

        Raises:
            DataPreparationError: If validation fails
        """
        with tracer.start_as_current_span("validate_labels"):
            try:
                if label_df.empty:
                    raise DataPreparationError(
                        "Label dataframe is empty",
                        stage="label_validation",
                    )

                # Check for required columns
                required_cols = ["article_id", "sentiment"]
                missing_cols = [c for c in required_cols if c not in label_df.columns]

                if missing_cols:
                    raise DataPreparationError(
                        f"Missing required columns: {missing_cols}",
                        stage="label_validation",
                    )

                # Check for null values in critical columns
                null_counts = label_df[required_cols].isnull().sum()
                if null_counts.sum() > 0:
                    logger.warning(f"Found null values in labels: {null_counts}")

                # Check sentiment values are valid
                valid_sentiments = {"positive", "negative", "neutral"}
                invalid_sentiments = (
                    set(label_df["sentiment"].unique()) - valid_sentiments
                )
                if invalid_sentiments:
                    logger.warning(
                        f"Found invalid sentiment values: {invalid_sentiments}"
                    )

                logger.info("Label validation passed")
                return True

            except Exception as e:
                logger.error(f"Label validation failed: {e}")
                raise DataPreparationError(
                    f"Label validation failed: {e}",
                    stage="label_validation",
                )

    async def get_label_statistics(self, label_df: pd.DataFrame) -> dict:
        """
        Get statistics for labels.

        Args:
            label_df: Label dataframe

        Returns:
            Dictionary with label statistics
        """
        with tracer.start_as_current_span("get_label_statistics"):
            try:
                if label_df.empty:
                    return {"num_labels": 0}

                stats = {
                    "num_labels": len(label_df),
                    "sentiment_distribution": label_df["sentiment"]
                    .value_counts()
                    .to_dict(),
                    "avg_confidence": label_df["confidence"].mean(),
                    "min_confidence": label_df["confidence"].min(),
                    "max_confidence": label_df["confidence"].max(),
                }

                logger.debug(f"Label statistics: {stats}")
                return stats

            except Exception as e:
                logger.error(f"Failed to compute label statistics: {e}")
                raise DataPreparationError(
                    f"Failed to compute label statistics: {e}",
                    stage="label_statistics",
                )
