"""
Data and model drift detection.

Detects feature drift and target drift using statistical tests.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats

from src.config import config
from src.exceptions import DriftDetectionError
from src.utils.trace import get_tracer
from src.metrics import metrics

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class DriftDetector:
    """Detects data and model drift."""

    def __init__(self):
        """Initialize drift detector."""
        self.drift_history: Dict[str, Dict[str, Any]] = {}
        logger.info("Drift detector initialized")

    def detect_feature_drift(
        self,
        X_reference: pd.DataFrame,
        X_current: pd.DataFrame,
        threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Detect feature drift using Evidently.

        Args:
            X_reference: Reference features (training data)
            X_current: Current features (new data)
            threshold: Significance threshold for drift

        Returns:
            Dictionary with drift detection results

        Raises:
            DriftDetectionError: If detection fails
        """
        with tracer.start_as_current_span("detect_feature_drift") as span:
            span.set_attribute("num_reference_samples", len(X_reference))
            span.set_attribute("num_current_samples", len(X_current))

            try:
                logger.info(
                    f"Detecting feature drift: {len(X_reference)} reference vs "
                    f"{len(X_current)} current samples"
                )

                # Detect drift using statistical tests (Kolmogorov-Smirnov test)
                drifted_features = []

                for column in X_reference.columns:
                    if column in X_current.columns:
                        # Skip non-numeric columns
                        if not pd.api.types.is_numeric_dtype(X_reference[column]):
                            continue

                        # Perform KS test
                        try:
                            statistic, p_value = stats.ks_2samp(
                                X_reference[column].dropna(),
                                X_current[column].dropna()
                            )

                            # If p-value < threshold, drift is detected
                            if p_value < threshold:
                                drifted_features.append({
                                    "feature": column,
                                    "statistic": float(statistic),
                                    "p_value": float(p_value)
                                })
                                logger.debug(
                                    f"Drift detected in {column}: "
                                    f"statistic={statistic:.4f}, p_value={p_value:.4f}"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to test drift for {column}: {e}")

                result = {
                    "drift_detected": len(drifted_features) > 0,
                    "drifted_features": drifted_features,
                    "num_drifted": len(drifted_features),
                    "num_total_features": X_current.shape[1],
                    "drift_percentage": (
                        len(drifted_features) / X_current.shape[1] * 100
                        if X_current.shape[1] > 0 else 0
                    ),
                }

                # Store history
                self.drift_history["feature_drift"] = result

                # Record metric
                if result["drift_detected"]:
                    logger.warning(f"Feature drift detected: {len(drifted_features)} features")
                    metrics.record_drift_detection("feature", "sentiment_classifier")

                logger.info(f"Feature drift detection complete: {result}")
                return result

            except Exception as e:
                logger.error(f"Feature drift detection failed: {e}")
                raise DriftDetectionError(
                    f"Feature drift detection failed: {e}",
                    drift_type="feature",
                )

    def detect_target_drift(
        self,
        y_reference: pd.Series,
        y_current: pd.Series,
        threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Detect target drift.

        Args:
            y_reference: Reference labels (training data)
            y_current: Current labels (new data)
            threshold: Significance threshold for drift

        Returns:
            Dictionary with drift detection results

        Raises:
            DriftDetectionError: If detection fails
        """
        with tracer.start_as_current_span("detect_target_drift"):
            try:
                logger.info(
                    f"Detecting target drift: {len(y_reference)} reference vs "
                    f"{len(y_current)} current samples"
                )

                # Calculate distribution statistics
                ref_dist = y_reference.value_counts(normalize=True).to_dict()
                curr_dist = y_current.value_counts(normalize=True).to_dict()

                # Check for significant change in class distribution
                drift_detected = False
                max_diff = 0.0

                for label in set(list(ref_dist.keys()) + list(curr_dist.keys())):
                    ref_prop = ref_dist.get(label, 0)
                    curr_prop = curr_dist.get(label, 0)
                    diff = abs(ref_prop - curr_prop)
                    max_diff = max(max_diff, diff)

                    if diff > threshold:
                        drift_detected = True
                        logger.debug(
                            f"Target drift detected for class {label}: "
                            f"reference={ref_prop:.4f}, current={curr_prop:.4f}, "
                            f"diff={diff:.4f}"
                        )

                result = {
                    "drift_detected": drift_detected,
                    "reference_distribution": {str(k): v for k, v in ref_dist.items()},
                    "current_distribution": {str(k): v for k, v in curr_dist.items()},
                    "max_difference": float(max_diff),
                    "threshold": threshold,
                }

                # Store history
                self.drift_history["target_drift"] = result

                # Record metric
                if result["drift_detected"]:
                    logger.warning(f"Target drift detected: max_diff={max_diff:.4f}")
                    metrics.record_drift_detection("target", "sentiment_classifier")

                logger.info(f"Target drift detection complete: {result}")
                return result

            except Exception as e:
                logger.error(f"Target drift detection failed: {e}")
                raise DriftDetectionError(
                    f"Target drift detection failed: {e}",
                    drift_type="target",
                )

    def detect_model_drift(
        self,
        y_true: pd.Series,
        y_pred_old: np.ndarray,
        y_pred_new: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Detect model drift by comparing predictions.

        Args:
            y_true: True labels
            y_pred_old: Old model predictions
            y_pred_new: New model predictions

        Returns:
            Dictionary with drift detection results

        Raises:
            DriftDetectionError: If detection fails
        """
        with tracer.start_as_current_span("detect_model_drift"):
            try:
                logger.info("Detecting model drift")

                # Calculate prediction differences
                pred_diff = np.abs(y_pred_old - y_pred_new)
                mean_diff = np.mean(pred_diff)
                max_diff = np.max(pred_diff)

                # Check for significant drift
                drift_detected = mean_diff > 0.1 or max_diff > 0.5

                result = {
                    "drift_detected": drift_detected,
                    "mean_prediction_difference": float(mean_diff),
                    "max_prediction_difference": float(max_diff),
                    "num_changed_predictions": int(np.sum(y_pred_old != y_pred_new)),
                }

                # Store history
                self.drift_history["model_drift"] = result

                # Record metric
                if result["drift_detected"]:
                    metrics.record_drift_detection("model", "sentiment_classifier")

                logger.info(f"Model drift detection complete: {result}")
                return result

            except Exception as e:
                logger.error(f"Model drift detection failed: {e}")
                raise DriftDetectionError(
                    f"Model drift detection failed: {e}",
                    drift_type="model",
                )

    def get_drift_history(self) -> Dict[str, Dict[str, Any]]:
        """
        Get drift detection history.

        Returns:
            Dictionary with drift history
        """
        return self.drift_history
