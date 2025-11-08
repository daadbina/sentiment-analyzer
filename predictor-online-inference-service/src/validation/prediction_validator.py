"""
Prediction Validator for Predictor Online Inference Service.

Compares predictions with ground-truth labels and calculates
label consistency metrics weighted by label confidence.
"""

import logging
from datetime import datetime, timedelta

from ..exceptions import LabelValidationError
from ..metrics import MetricsCollector
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class PredictionValidator:
    """
    Validator for comparing predictions with ground-truth labels.

    Calculates label consistency metric (target ≥0.85) weighted by
    label confidence and tracks accuracy over time.
    """

    def __init__(self, metrics: MetricsCollector, consistency_threshold: float = 0.85):
        """
        Initialize prediction validator.

        Args:
            metrics: Metrics collector
            consistency_threshold: Target consistency threshold (default: 0.85)
        """
        self.metrics = metrics
        self.consistency_threshold = consistency_threshold
        self._validation_history: list[dict] = []

        logger.info(
            "Initialized PredictionValidator",
            extra={"consistency_threshold": consistency_threshold},
        )

    @trace_span("prediction_validator.compare_prediction_with_label")
    def compare_prediction_with_label(
        self,
        group_id: str,
        predicted_realized: bool,
        predicted_confidence: float,
        label_realized: bool,
        label_confidence: float,
        trace_id: str | None = None,
    ) -> dict[str, any]:
        """
        Compare a prediction with its ground-truth label.

        Args:
            group_id: Semantic group ID
            predicted_realized: Predicted realization (True/False)
            predicted_confidence: Prediction confidence [0, 1]
            label_realized: Ground-truth label (True/False)
            label_confidence: Label confidence [0, 1]
            trace_id: Trace ID for correlation

        Returns:
            Dictionary with comparison results:
                - is_correct: Whether prediction matches label
                - weighted_score: Score weighted by label confidence
                - prediction_confidence: Original prediction confidence
                - label_confidence: Original label confidence

        Raises:
            LabelValidationError: If validation fails
        """
        try:
            # Validate inputs
            if not (0 <= predicted_confidence <= 1):
                raise LabelValidationError(
                    message=f"Invalid predicted_confidence: {predicted_confidence}",
                    details={"group_id": group_id, "predicted_confidence": predicted_confidence},
                )

            if not (0 <= label_confidence <= 1):
                raise LabelValidationError(
                    message=f"Invalid label_confidence: {label_confidence}",
                    details={"group_id": group_id, "label_confidence": label_confidence},
                )

            # Check if prediction matches label
            is_correct = predicted_realized == label_realized

            # Calculate weighted score
            # Weight by label confidence: high-confidence labels matter more
            weighted_score = float(is_correct) * label_confidence

            # Store validation result
            validation_result = {
                "group_id": group_id,
                "is_correct": is_correct,
                "weighted_score": weighted_score,
                "predicted_realized": predicted_realized,
                "predicted_confidence": predicted_confidence,
                "label_realized": label_realized,
                "label_confidence": label_confidence,
                "timestamp": datetime.now().isoformat(),
                "trace_id": trace_id,
            }

            self._validation_history.append(validation_result)

            # Update metrics
            if is_correct:
                self.metrics.increment_prediction_correct()
            else:
                self.metrics.increment_prediction_incorrect()

            logger.info(
                "Compared prediction with label",
                extra={
                    "group_id": group_id,
                    "is_correct": is_correct,
                    "weighted_score": weighted_score,
                    "predicted_realized": predicted_realized,
                    "label_realized": label_realized,
                    "label_confidence": label_confidence,
                    "trace_id": trace_id,
                },
            )

            return validation_result

        except Exception as e:
            logger.error(
                "Failed to compare prediction with label",
                extra={"group_id": group_id, "error": str(e), "trace_id": trace_id},
                exc_info=True,
            )
            raise LabelValidationError(
                message=f"Failed to validate prediction: {str(e)}", details={"group_id": group_id}
            ) from e

    def calculate_label_consistency(
        self, time_window_hours: int | None = None, trace_id: str | None = None
    ) -> float:
        """
        Calculate label consistency metric over time window.

        Args:
            time_window_hours: Time window in hours (None = all history)
            trace_id: Trace ID for correlation

        Returns:
            Label consistency score [0, 1]
        """
        try:
            # Filter validation history by time window
            if time_window_hours:
                cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
                relevant_validations = [
                    v
                    for v in self._validation_history
                    if datetime.fromisoformat(v["timestamp"]) >= cutoff_time
                ]
            else:
                relevant_validations = self._validation_history

            if not relevant_validations:
                logger.warning(
                    "No validation history available",
                    extra={"time_window_hours": time_window_hours, "trace_id": trace_id},
                )
                return 0.0

            # Calculate weighted consistency
            total_weighted_score = sum(v["weighted_score"] for v in relevant_validations)
            total_weight = sum(v["label_confidence"] for v in relevant_validations)

            if total_weight == 0:
                logger.warning(
                    "Total weight is zero",
                    extra={"validation_count": len(relevant_validations), "trace_id": trace_id},
                )
                return 0.0

            consistency_score = total_weighted_score / total_weight

            # Update metrics
            self.metrics.set_label_consistency_score(consistency_score)

            logger.info(
                "Calculated label consistency",
                extra={
                    "consistency_score": consistency_score,
                    "validation_count": len(relevant_validations),
                    "time_window_hours": time_window_hours,
                    "meets_threshold": consistency_score >= self.consistency_threshold,
                    "trace_id": trace_id,
                },
            )

            return consistency_score

        except Exception as e:
            logger.error(
                "Failed to calculate label consistency",
                extra={
                    "time_window_hours": time_window_hours,
                    "error": str(e),
                    "trace_id": trace_id,
                },
                exc_info=True,
            )
            return 0.0

    def get_accuracy_over_time(
        self, time_window_hours: int = 24, trace_id: str | None = None
    ) -> dict[str, any]:
        """
        Get accuracy metrics over time window.

        Args:
            time_window_hours: Time window in hours
            trace_id: Trace ID for correlation

        Returns:
            Dictionary with accuracy metrics
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            relevant_validations = [
                v
                for v in self._validation_history
                if datetime.fromisoformat(v["timestamp"]) >= cutoff_time
            ]

            if not relevant_validations:
                return {
                    "total_predictions": 0,
                    "correct_predictions": 0,
                    "accuracy": 0.0,
                    "weighted_consistency": 0.0,
                    "time_window_hours": time_window_hours,
                }

            total_predictions = len(relevant_validations)
            correct_predictions = sum(1 for v in relevant_validations if v["is_correct"])
            accuracy = correct_predictions / total_predictions

            # Calculate weighted consistency
            total_weighted_score = sum(v["weighted_score"] for v in relevant_validations)
            total_weight = sum(v["label_confidence"] for v in relevant_validations)
            weighted_consistency = total_weighted_score / total_weight if total_weight > 0 else 0.0

            metrics = {
                "total_predictions": total_predictions,
                "correct_predictions": correct_predictions,
                "incorrect_predictions": total_predictions - correct_predictions,
                "accuracy": accuracy,
                "weighted_consistency": weighted_consistency,
                "time_window_hours": time_window_hours,
                "meets_threshold": weighted_consistency >= self.consistency_threshold,
            }

            logger.info("Calculated accuracy over time", extra={**metrics, "trace_id": trace_id})

            return metrics

        except Exception as e:
            logger.error(
                "Failed to calculate accuracy over time",
                extra={
                    "time_window_hours": time_window_hours,
                    "error": str(e),
                    "trace_id": trace_id,
                },
                exc_info=True,
            )
            return {
                "total_predictions": 0,
                "correct_predictions": 0,
                "accuracy": 0.0,
                "weighted_consistency": 0.0,
                "time_window_hours": time_window_hours,
                "error": str(e),
            }

    def clear_history(self, older_than_hours: int | None = None) -> int:
        """
        Clear validation history.

        Args:
            older_than_hours: Clear entries older than this (None = clear all)

        Returns:
            Number of entries cleared
        """
        if older_than_hours is None:
            count = len(self._validation_history)
            self._validation_history.clear()
            logger.info(f"Cleared all validation history: {count} entries")
            return count

        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        original_count = len(self._validation_history)

        self._validation_history = [
            v
            for v in self._validation_history
            if datetime.fromisoformat(v["timestamp"]) >= cutoff_time
        ]

        cleared_count = original_count - len(self._validation_history)

        logger.info(
            "Cleared old validation history",
            extra={
                "cleared_count": cleared_count,
                "remaining_count": len(self._validation_history),
                "older_than_hours": older_than_hours,
            },
        )

        return cleared_count
