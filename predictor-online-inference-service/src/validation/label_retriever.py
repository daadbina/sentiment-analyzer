"""
Label retriever for fetching ground-truth labels from Labeler Service.

Retrieves labels from PostgreSQL database with proper error handling.
Implements Rule R8 (Ground-Truth Sync) and Rule R10 (Truth Freshness).
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from ..clients import PostgresClient
from ..exceptions import LabelFetchError
from ..metrics import MetricsCollector
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


# Label freshness thresholds per Rule R10
LABEL_FRESHNESS_THRESHOLDS = {
    "ACLED": timedelta(days=1),  # ≤1 day
    "GDELT": timedelta(hours=1),  # ≤1 hour
    "CoinGecko": timedelta(minutes=5),  # ≤5 minutes
}


class LabelRetriever:
    """
    Retriever for ground-truth labels from Labeler Service.

    Fetches labels from PostgreSQL with validation and freshness checks.
    """

    def __init__(self, postgres_client: PostgresClient):
        """
        Initialize label retriever.

        Args:
            postgres_client: PostgreSQL client instance
        """
        self.postgres_client = postgres_client

        logger.info("Initialized label retriever")

    async def get_label(
        self,
        group_id: str,
        trace_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Retrieve ground-truth label for a semantic group.

        Args:
            group_id: Semantic group ID
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Label dictionary or None if not found
            Dictionary contains:
                - group_id: str
                - domain: str
                - label_value: float (0.0 or 1.0)
                - label_confidence: float (0.0-1.0)
                - label_source: str (ACLED/GDELT/CoinGecko)
                - labeled_at: datetime
                - event_timestamp: datetime

        Raises:
            LabelFetchError: If retrieval fails
        """
        with trace_span(
            "get_ground_truth_label",
            attributes={"group_id": group_id, "trace_id": trace_id},
        ):
            try:
                logger.debug(
                    f"Retrieving label: group_id={group_id}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

                # Fetch label from PostgreSQL
                label = await self.postgres_client.get_ground_truth_label(
                    group_id=group_id,
                    trace_id=trace_id,
                )

                if label is None:
                    logger.debug(
                        f"No label found: group_id={group_id}",
                        extra={"trace_id": trace_id, "group_id": group_id},
                    )
                    return None

                # Check label freshness
                self._check_label_freshness(label, trace_id)

                logger.debug(
                    f"Retrieved label: group_id={group_id}, "
                    f"source={label['label_source']}, value={label['label_value']}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

                return label

            except LabelFetchError:
                # Record failure metric
                MetricsCollector.record_feature_fetch_failure("postgres", "ground_truth")
                raise
            except Exception as e:
                logger.error(
                    f"Failed to retrieve label: group_id={group_id}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                MetricsCollector.record_feature_fetch_failure("postgres", "ground_truth")
                raise LabelFetchError(
                    f"Failed to retrieve label: {e}",
                    group_id=group_id,
                    source="postgres",
                    trace_id=trace_id,
                )

    def _check_label_freshness(
        self,
        label: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Check label freshness against Rule R10 thresholds.

        Args:
            label: Label dictionary
            trace_id: Optional trace ID for distributed tracing

        Logs warning if label is stale but does not raise exception.
        """
        label_source = label.get("label_source")
        labeled_at = label.get("labeled_at")

        if not label_source or not labeled_at:
            return

        # Get freshness threshold for source
        threshold = LABEL_FRESHNESS_THRESHOLDS.get(label_source)
        if not threshold:
            logger.warning(
                f"Unknown label source: {label_source}",
                extra={"trace_id": trace_id},
            )
            return

        # Calculate label age
        age = datetime.utcnow() - labeled_at

        # Check if label is stale
        if age > threshold:
            logger.warning(
                f"Stale label: group_id={label['group_id']}, "
                f"source={label_source}, age={age}, threshold={threshold}",
                extra={"trace_id": trace_id, "group_id": label["group_id"]},
            )

    async def get_labels_batch(
        self,
        group_ids: list[str],
        trace_id: str | None = None,
    ) -> dict[str, dict[str, Any] | None]:
        """
        Retrieve ground-truth labels for multiple semantic groups.

        Args:
            group_ids: List of semantic group IDs
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Dictionary mapping group_id to label (or None if not found)

        Raises:
            LabelFetchError: If retrieval fails
        """
        with trace_span(
            "get_ground_truth_labels_batch",
            attributes={"batch_size": len(group_ids), "trace_id": trace_id},
        ):
            logger.debug(
                f"Retrieving labels batch: count={len(group_ids)}",
                extra={"trace_id": trace_id},
            )

            labels = {}

            # Fetch labels for each group
            for group_id in group_ids:
                try:
                    label = await self.get_label(group_id, trace_id)
                    labels[group_id] = label
                except LabelFetchError as e:
                    logger.warning(
                        f"Failed to retrieve label for group: group_id={group_id}, error={e}",
                        extra={"trace_id": trace_id},
                    )
                    labels[group_id] = None

            logger.debug(
                f"Retrieved labels batch: count={len(group_ids)}, "
                f"found={sum(1 for l in labels.values() if l is not None)}",
                extra={"trace_id": trace_id},
            )

            return labels

    async def get_recent_labels(
        self,
        hours: int = 24,
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve recent labels for validation.

        Args:
            hours: Number of hours to look back
            trace_id: Optional trace ID for distributed tracing

        Returns:
            List of label dictionaries

        Raises:
            LabelFetchError: If retrieval fails
        """
        with trace_span(
            "get_recent_labels",
            attributes={"hours": hours, "trace_id": trace_id},
        ):
            try:
                logger.debug(
                    f"Retrieving recent labels: hours={hours}",
                    extra={"trace_id": trace_id},
                )

                # Get predictions with labels from PostgreSQL
                predictions = await self.postgres_client.get_predictions_for_validation(
                    limit=1000,
                    trace_id=trace_id,
                )

                # Filter to only those with labels
                labels = [
                    {
                        "group_id": p["group_id"],
                        "domain": p["domain"],
                        "label_value": p["label_value"],
                        "label_confidence": p["label_confidence"],
                        "label_source": p["label_source"],
                        "prediction_probability": p["prediction_probability"],
                        "prediction_confidence": p["prediction_confidence"],
                        "model_version": p["model_version"],
                        "predicted_at": p["predicted_at"],
                    }
                    for p in predictions
                    if p.get("label_value") is not None
                ]

                logger.debug(
                    f"Retrieved recent labels: count={len(labels)}",
                    extra={"trace_id": trace_id},
                )

                return labels

            except Exception as e:
                logger.error(
                    f"Failed to retrieve recent labels: error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise LabelFetchError(
                    f"Failed to retrieve recent labels: {e}",
                    source="postgres",
                    trace_id=trace_id,
                )
