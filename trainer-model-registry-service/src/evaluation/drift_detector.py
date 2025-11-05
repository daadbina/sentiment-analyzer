"""
Data and model drift detection.

Detects feature drift and target drift using statistical tests.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset

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

                # Create report
                report = Report(metrics=[DataDriftPreset()])
                report.run(
                    reference_data=X_reference,
                    current_data=X_current,
                )

                # Extract results
                drift_results = report.as_dict()

                # Check for drift
                drifted_features = []
                if "metrics" in drift_results:
                    for metric in drift_results["metrics"]:
                        if "result" in metric and "drift_detected" in metric["result"]:
                            if metric["result"]["drift_detected"]:
                                drifted_features.append(metric.get("metric", "unknown"))

                result = {
                    "drift_detected": len(drifted_features) > 0,
                    "drifted_features": drifted_features,
                    "num_drifted": len(drifted_features),
                    "num_total_features": X_current.shape[1],
                    "drift_percentage": (
                        len(drifted_features) / X_current.shape[1] * 100
                    ),
                }

                # Store history
                self.drift_history["feature_drift"] = result

                # Record metric
                if result["drift_detected"]:
                    metrics.record_drift_detected()

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

                # Create dataframes for Evidently
                ref_df = pd.DataFrame({"target": y_reference})
                curr_df = pd.DataFrame({"target": y_current})

                # Create report
                report = Report(metrics=[TargetDriftPreset()])
                report.run(
                    reference_data=ref_df,
                    current_data=curr_df,
                )

                # Extract results
                drift_results = report.as_dict()

                # Calculate distribution statistics
                ref_dist = y_reference.value_counts(normalize=True).to_dict()
                curr_dist = y_current.value_counts(normalize=True).to_dict()

                # Check for significant change
                drift_detected = False
                for label in set(list(ref_dist.keys()) + list(curr_dist.keys())):
                    ref_prop = ref_dist.get(label, 0)
                    curr_prop = curr_dist.get(label, 0)
                    if abs(ref_prop - curr_prop) > threshold:
                        drift_detected = True
                        break

                result = {
                    "drift_detected": drift_detected,
                    "reference_distribution": ref_dist,
                    "current_distribution": curr_dist,
                    "threshold": threshold,
                }

                # Store history
                self.drift_history["target_drift"] = result

                # Record metric
                if result["drift_detected"]:
                    metrics.record_drift_detected()

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
                    metrics.record_drift_detected()

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

