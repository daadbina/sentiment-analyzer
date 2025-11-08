"""
Confidence Scorer for Predictor Online Inference Service.

Computes confidence scores for model predictions with
model-specific logic and uncertainty quantification.
"""

import logging
from typing import Any

import numpy as np

from ..exceptions import InferenceError
from ..metrics import MetricsCollector
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Scorer for computing prediction confidence.

    Provides model-specific confidence logic and uncertainty
    quantification for predictions.
    """

    def __init__(self, metrics: MetricsCollector):
        """
        Initialize confidence scorer.

        Args:
            metrics: Metrics collector
        """
        self.metrics = metrics

        logger.info("Initialized ConfidenceScorer")

    @trace_span("confidence_scorer.compute_confidence")
    def compute_confidence(
        self, model_output: Any, model_type: str = "xgboost", trace_id: str | None = None
    ) -> float:
        """
        Compute confidence score for model prediction.

        Args:
            model_output: Raw model output (probabilities or scores)
            model_type: Type of model (xgboost, sklearn, etc.)
            trace_id: Trace ID for correlation

        Returns:
            Confidence score [0, 1]

        Raises:
            InferenceError: If confidence computation fails
        """
        try:
            logger.debug(
                "Computing confidence score", extra={"model_type": model_type, "trace_id": trace_id}
            )

            if model_type == "xgboost":
                confidence = self._compute_xgboost_confidence(model_output)
            elif model_type == "sklearn":
                confidence = self._compute_sklearn_confidence(model_output)
            elif model_type == "baseline":
                confidence = self._compute_baseline_confidence(model_output)
            else:
                # Default: use max probability
                confidence = self._compute_default_confidence(model_output)

            # Ensure confidence is in [0, 1]
            confidence = float(np.clip(confidence, 0.0, 1.0))

            # Update metrics
            self.metrics.record_prediction_confidence(confidence)

            logger.debug(
                "Computed confidence score",
                extra={"confidence": confidence, "model_type": model_type, "trace_id": trace_id},
            )

            return confidence

        except Exception as e:
            logger.error(
                "Failed to compute confidence score",
                extra={"model_type": model_type, "error": str(e), "trace_id": trace_id},
                exc_info=True,
            )
            raise InferenceError(
                message=f"Failed to compute confidence: {str(e)}",
                details={"model_type": model_type},
            ) from e

    def _compute_xgboost_confidence(self, model_output: Any) -> float:
        """
        Compute confidence for XGBoost model.

        Args:
            model_output: XGBoost prediction probabilities

        Returns:
            Confidence score
        """
        try:
            # XGBoost outputs probabilities for each class
            # Confidence is the max probability
            if isinstance(model_output, np.ndarray):
                if model_output.ndim == 2:
                    # Multi-class: shape (n_samples, n_classes)
                    confidence = float(np.max(model_output[0]))
                else:
                    # Binary: shape (n_samples,)
                    # Convert to probability of positive class
                    prob = float(model_output[0])
                    confidence = max(prob, 1 - prob)
            else:
                # Single value
                prob = float(model_output)
                confidence = max(prob, 1 - prob)

            return confidence

        except Exception as e:
            logger.warning(
                "Failed to compute XGBoost confidence, using default", extra={"error": str(e)}
            )
            return 0.5

    def _compute_sklearn_confidence(self, model_output: Any) -> float:
        """
        Compute confidence for scikit-learn model.

        Args:
            model_output: sklearn prediction probabilities

        Returns:
            Confidence score
        """
        try:
            # sklearn outputs probabilities for each class
            if isinstance(model_output, np.ndarray):
                if model_output.ndim == 2:
                    # Multi-class: shape (n_samples, n_classes)
                    confidence = float(np.max(model_output[0]))
                else:
                    # Binary: shape (n_samples,)
                    prob = float(model_output[0])
                    confidence = max(prob, 1 - prob)
            else:
                prob = float(model_output)
                confidence = max(prob, 1 - prob)

            return confidence

        except Exception as e:
            logger.warning(
                "Failed to compute sklearn confidence, using default", extra={"error": str(e)}
            )
            return 0.5

    def _compute_baseline_confidence(self, model_output: Any) -> float:
        """
        Compute confidence for baseline model.

        Args:
            model_output: Baseline model output

        Returns:
            Confidence score (fixed at 0.5 for baseline)
        """
        # Baseline model has low confidence
        return 0.5

    def _compute_default_confidence(self, model_output: Any) -> float:
        """
        Compute confidence using default method.

        Args:
            model_output: Model output

        Returns:
            Confidence score
        """
        try:
            if isinstance(model_output, np.ndarray):
                if model_output.ndim == 2:
                    confidence = float(np.max(model_output[0]))
                else:
                    prob = float(model_output[0])
                    confidence = max(prob, 1 - prob)
            else:
                prob = float(model_output)
                confidence = max(prob, 1 - prob)

            return confidence

        except Exception as e:
            logger.warning("Failed to compute default confidence", extra={"error": str(e)})
            return 0.5

    @trace_span("confidence_scorer.quantify_uncertainty")
    def quantify_uncertainty(
        self,
        model_output: Any,
        feature_quality: dict[str, float] | None = None,
        trace_id: str | None = None,
    ) -> dict[str, float]:
        """
        Quantify prediction uncertainty.

        Args:
            model_output: Raw model output
            feature_quality: Optional feature quality metrics
            trace_id: Trace ID for correlation

        Returns:
            Dictionary with uncertainty metrics:
                - epistemic_uncertainty: Model uncertainty
                - aleatoric_uncertainty: Data uncertainty
                - total_uncertainty: Combined uncertainty
        """
        try:
            logger.debug("Quantifying uncertainty", extra={"trace_id": trace_id})

            # Compute epistemic uncertainty (model uncertainty)
            # Based on prediction entropy
            if isinstance(model_output, np.ndarray):
                if model_output.ndim == 2:
                    probs = model_output[0]
                else:
                    prob = float(model_output[0])
                    probs = np.array([1 - prob, prob])
            else:
                prob = float(model_output)
                probs = np.array([1 - prob, prob])

            # Calculate entropy
            epsilon = 1e-10  # Avoid log(0)
            probs = np.clip(probs, epsilon, 1 - epsilon)
            entropy = -np.sum(probs * np.log(probs))

            # Normalize entropy to [0, 1]
            max_entropy = np.log(len(probs))
            epistemic_uncertainty = float(entropy / max_entropy)

            # Compute aleatoric uncertainty (data uncertainty)
            # Based on feature quality if available
            if feature_quality:
                # Average feature quality as proxy for data certainty
                avg_quality = np.mean(list(feature_quality.values()))
                aleatoric_uncertainty = 1.0 - avg_quality
            else:
                # Default: moderate uncertainty
                aleatoric_uncertainty = 0.3

            # Compute total uncertainty
            # Combine epistemic and aleatoric
            total_uncertainty = np.sqrt(epistemic_uncertainty**2 + aleatoric_uncertainty**2)

            uncertainty_metrics = {
                "epistemic_uncertainty": float(epistemic_uncertainty),
                "aleatoric_uncertainty": float(aleatoric_uncertainty),
                "total_uncertainty": float(total_uncertainty),
            }

            logger.debug(
                "Quantified uncertainty", extra={**uncertainty_metrics, "trace_id": trace_id}
            )

            return uncertainty_metrics

        except Exception as e:
            logger.error(
                "Failed to quantify uncertainty",
                extra={"error": str(e), "trace_id": trace_id},
                exc_info=True,
            )
            return {
                "epistemic_uncertainty": 0.5,
                "aleatoric_uncertainty": 0.5,
                "total_uncertainty": 0.7,
            }

    def adjust_confidence_by_uncertainty(self, confidence: float, uncertainty: float) -> float:
        """
        Adjust confidence score by uncertainty.

        Args:
            confidence: Original confidence score
            uncertainty: Uncertainty score

        Returns:
            Adjusted confidence score
        """
        # Reduce confidence proportionally to uncertainty
        adjusted_confidence = confidence * (1.0 - uncertainty)

        return float(np.clip(adjusted_confidence, 0.0, 1.0))
