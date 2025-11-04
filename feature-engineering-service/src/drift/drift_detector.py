"""Drift detection for feature distributions."""

from typing import Dict, Any, List, Tuple
import numpy as np
from scipy import stats
from ..utils import StructuredLogger
from ..exceptions import DriftDetectionError

logger = StructuredLogger(__name__)


class DriftDetector:
    """Detect distribution drift in features."""

    def __init__(self, baseline_stats: Dict[str, Dict[str, float]] = None):
        """Initialize drift detector.

        Args:
            baseline_stats: Baseline statistics for comparison
        """
        self.baseline_stats = baseline_stats or {}

    def detect_drift(
        self,
        feature_name: str,
        current_values: List[float],
        method: str = "ks",
    ) -> Tuple[bool, Dict[str, Any]]:
        """Detect drift in feature distribution.

        Args:
            feature_name: Name of feature
            current_values: Current feature values
            method: "ks" (Kolmogorov-Smirnov) or "js" (Jensen-Shannon)

        Returns:
            Tuple of (has_drift, drift_report)
        """
        try:
            if not current_values or len(current_values) < 2:
                return False, {
                    "feature": feature_name,
                    "result": "insufficient_data",
                }

            if feature_name not in self.baseline_stats:
                # No baseline, compute current as baseline
                self._update_baseline(feature_name, current_values)
                return False, {
                    "feature": feature_name,
                    "result": "baseline_created",
                }

            baseline = self.baseline_stats[feature_name]

            if method == "ks":
                has_drift, statistic, p_value = self._ks_test(
                    current_values,
                    baseline,
                )
            else:  # js
                has_drift, statistic, p_value = self._js_test(
                    current_values,
                    baseline,
                )

            report = {
                "feature": feature_name,
                "method": method,
                "has_drift": has_drift,
                "statistic": statistic,
                "p_value": p_value,
                "baseline_mean": baseline.get("mean", 0),
                "baseline_std": baseline.get("std", 0),
                "current_mean": np.mean(current_values),
                "current_std": np.std(current_values),
            }

            if has_drift:
                logger.warning(
                    "Drift detected",
                    feature_name=feature_name,
                    method=method,
                    statistic=statistic,
                )
            else:
                logger.info(
                    "No drift detected",
                    feature_name=feature_name,
                    method=method,
                )

            return has_drift, report

        except Exception as e:
            logger.error(
                "Error detecting drift",
                feature_name=feature_name,
                error=str(e),
            )
            raise DriftDetectionError(f"Error detecting drift: {str(e)}")

    def _ks_test(
        self,
        current_values: List[float],
        baseline: Dict[str, float],
    ) -> Tuple[bool, float, float]:
        """Kolmogorov-Smirnov test.

        Returns:
            Tuple of (has_drift, statistic, p_value)
        """
        # Normalize current values using baseline mean and std
        baseline_mean = baseline.get("mean", 0)
        baseline_std = baseline.get("std", 1)

        if baseline_std > 0:
            normalized = [(v - baseline_mean) / baseline_std for v in current_values]
        else:
            normalized = current_values

        # Compare against standard normal distribution
        statistic, p_value = stats.kstest(normalized, "norm")

        # Drift detected if p-value < 0.05
        has_drift = p_value < 0.05

        return has_drift, statistic, p_value

    def _js_test(
        self,
        current_values: List[float],
        baseline: Dict[str, float],
    ) -> Tuple[bool, float, float]:
        """Jensen-Shannon divergence test.

        Returns:
            Tuple of (has_drift, divergence, threshold_exceeded)
        """
        # Compute histograms
        baseline_values = baseline.get("values", [])
        if not baseline_values:
            return False, 0.0, 1.0

        # Compute Jensen-Shannon divergence
        hist_current, _ = np.histogram(current_values, bins=10)
        hist_baseline, _ = np.histogram(baseline_values, bins=10)

        # Normalize
        hist_current = hist_current / np.sum(hist_current)
        hist_baseline = hist_baseline / np.sum(hist_baseline)

        # Compute divergence
        divergence = stats.entropy(hist_current, hist_baseline)

        # Drift detected if divergence > threshold
        threshold = 0.1
        has_drift = divergence > threshold

        return has_drift, divergence, float(has_drift)

    def _update_baseline(
        self,
        feature_name: str,
        values: List[float],
    ):
        """Update baseline statistics.

        Args:
            feature_name: Name of feature
            values: Feature values
        """
        self.baseline_stats[feature_name] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "values": values,
        }

        logger.info(
            "Baseline updated",
            feature_name=feature_name,
            mean=self.baseline_stats[feature_name]["mean"],
        )

