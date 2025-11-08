"""
Label validator for validating ground-truth labels.

Validates label schema, freshness, and confidence.
Implements Rule R8 (Ground-Truth Sync) and Rule R10 (Truth Freshness).
"""

import logging
from datetime import datetime
from typing import Any

from ..exceptions import LabelValidationError
from ..utils.trace import trace_span
from .label_retriever import LABEL_FRESHNESS_THRESHOLDS

logger = logging.getLogger(__name__)


class LabelValidator:
    """
    Validator for ground-truth labels.

    Validates label schema, freshness, and confidence.
    """

    def __init__(self, min_confidence: float = 0.5):
        """
        Initialize label validator.

        Args:
            min_confidence: Minimum label confidence threshold
        """
        self.min_confidence = min_confidence

        logger.info(f"Initialized label validator: min_confidence={min_confidence}")

    async def validate_label(
        self,
        label: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Validate label schema and quality.

        Args:
            label: Label dictionary to validate
            trace_id: Optional trace ID for distributed tracing

        Raises:
            LabelValidationError: If validation fails
        """
        with trace_span(
            "validate_label",
            attributes={"group_id": label.get("group_id"), "trace_id": trace_id},
        ):
            # Check required fields
            required_fields = [
                "group_id",
                "domain",
                "label_value",
                "label_confidence",
                "label_source",
                "labeled_at",
            ]

            missing_fields = [field for field in required_fields if field not in label]
            if missing_fields:
                logger.error(
                    f"Missing required label fields: {missing_fields}",
                    extra={"trace_id": trace_id},
                )
                raise LabelValidationError(
                    f"Missing required label fields: {missing_fields}",
                    group_id=label.get("group_id"),
                    trace_id=trace_id,
                )

            # Validate label value
            label_value = label["label_value"]
            if label_value not in [0.0, 1.0]:
                logger.error(
                    f"Invalid label value: {label_value}, must be 0.0 or 1.0",
                    extra={"trace_id": trace_id},
                )
                raise LabelValidationError(
                    f"Invalid label value: {label_value}, must be 0.0 or 1.0",
                    group_id=label["group_id"],
                    trace_id=trace_id,
                )

            # Validate label confidence
            label_confidence = label["label_confidence"]
            if not 0.0 <= label_confidence <= 1.0:
                logger.error(
                    f"Invalid label confidence: {label_confidence}, must be in [0.0, 1.0]",
                    extra={"trace_id": trace_id},
                )
                raise LabelValidationError(
                    f"Invalid label confidence: {label_confidence}, must be in [0.0, 1.0]",
                    group_id=label["group_id"],
                    trace_id=trace_id,
                )

            # Check minimum confidence
            if label_confidence < self.min_confidence:
                logger.warning(
                    f"Label confidence below threshold: {label_confidence} < {self.min_confidence}",
                    extra={"trace_id": trace_id, "group_id": label["group_id"]},
                )
                raise LabelValidationError(
                    f"Label confidence {label_confidence} below threshold {self.min_confidence}",
                    group_id=label["group_id"],
                    trace_id=trace_id,
                )

            # Validate label source
            valid_sources = ["ACLED", "GDELT", "CoinGecko"]
            label_source = label["label_source"]
            if label_source not in valid_sources:
                logger.error(
                    f"Invalid label source: {label_source}, must be one of {valid_sources}",
                    extra={"trace_id": trace_id},
                )
                raise LabelValidationError(
                    f"Invalid label source: {label_source}, must be one of {valid_sources}",
                    group_id=label["group_id"],
                    trace_id=trace_id,
                )

            # Validate label freshness
            self._validate_freshness(label, trace_id)

            logger.debug(
                f"Label validated successfully: group_id={label['group_id']}",
                extra={"trace_id": trace_id, "group_id": label["group_id"]},
            )

    def _validate_freshness(
        self,
        label: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Validate label freshness against Rule R10 thresholds.

        Args:
            label: Label dictionary
            trace_id: Optional trace ID for distributed tracing

        Raises:
            LabelValidationError: If label is too stale
        """
        label_source = label["label_source"]
        labeled_at = label["labeled_at"]

        # Get freshness threshold for source
        threshold = LABEL_FRESHNESS_THRESHOLDS.get(label_source)
        if not threshold:
            logger.warning(
                f"Unknown label source: {label_source}",
                extra={"trace_id": trace_id},
            )
            return

        # Calculate label age
        if isinstance(labeled_at, str):
            labeled_at = datetime.fromisoformat(labeled_at)

        age = datetime.utcnow() - labeled_at

        # Check if label is stale
        if age > threshold:
            logger.error(
                f"Label is stale: group_id={label['group_id']}, "
                f"source={label_source}, age={age}, threshold={threshold}",
                extra={"trace_id": trace_id, "group_id": label["group_id"]},
            )
            raise LabelValidationError(
                f"Label is stale: age={age}, threshold={threshold}",
                group_id=label["group_id"],
                trace_id=trace_id,
            )
