"""
Drift Detector for Predictor Online Inference Service.

Monitors feature drift and prediction drift using statistical methods
inspired by EvidentlyAI patterns.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from scipy import stats

from ..exceptions import ValidationError
from ..utils.trace import trace_span
from ..metrics import MetricsCollector

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Detector for monitoring feature and prediction drift.
    
    Uses statistical tests to detect drift and alerts on
    significant changes.
    """
    
    def __init__(
        self,
        metrics: MetricsCollector,
        drift_threshold: float = 0.05  # p-value threshold
    ):
        """
        Initialize drift detector.
        
        Args:
            metrics: Metrics collector
            drift_threshold: Statistical significance threshold
        """
        self.metrics = metrics
        self.drift_threshold = drift_threshold
        self._feature_baseline: Dict[str, List[float]] = defaultdict(list)
        self._feature_current: Dict[str, List[float]] = defaultdict(list)
        self._prediction_baseline: List[float] = []
        self._prediction_current: List[float] = []
        
        logger.info(
            "Initialized DriftDetector",
            extra={"drift_threshold": drift_threshold}
        )
    
    @trace_span("drift_detector.track_features")
    def track_features(
        self,
        features: Dict[str, float],
        is_baseline: bool = False,
        trace_id: Optional[str] = None
    ) -> None:
        """
        Track features for drift detection.
        
        Args:
            features: Feature values
            is_baseline: Whether this is baseline data
            trace_id: Trace ID for correlation
        """
        try:
            target = self._feature_baseline if is_baseline else self._feature_current
            
            for feature_name, value in features.items():
                if isinstance(value, (int, float)) and not np.isnan(value):
                    target[feature_name].append(float(value))
            
            logger.debug(
                "Tracked features",
                extra={
                    "feature_count": len(features),
                    "is_baseline": is_baseline,
                    "trace_id": trace_id
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to track features",
                extra={
                    "is_baseline": is_baseline,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
    
    @trace_span("drift_detector.track_prediction")
    def track_prediction(
        self,
        prediction_value: float,
        is_baseline: bool = False,
        trace_id: Optional[str] = None
    ) -> None:
        """
        Track prediction for drift detection.
        
        Args:
            prediction_value: Prediction value
            is_baseline: Whether this is baseline data
            trace_id: Trace ID for correlation
        """
        try:
            if isinstance(prediction_value, (int, float)) and not np.isnan(prediction_value):
                if is_baseline:
                    self._prediction_baseline.append(float(prediction_value))
                else:
                    self._prediction_current.append(float(prediction_value))
            
            logger.debug(
                "Tracked prediction",
                extra={
                    "prediction_value": prediction_value,
                    "is_baseline": is_baseline,
                    "trace_id": trace_id
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to track prediction",
                extra={
                    "is_baseline": is_baseline,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
    
    @trace_span("drift_detector.detect_feature_drift")
    def detect_feature_drift(
        self,
        feature_name: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect feature drift using Kolmogorov-Smirnov test.
        
        Args:
            feature_name: Specific feature to check (None = all features)
            trace_id: Trace ID for correlation
            
        Returns:
            Dictionary with drift detection results
        """
        try:
            drift_results = {}
            
            # Check specific feature or all features
            features_to_check = (
                [feature_name] if feature_name
                else self._feature_baseline.keys()
            )
            
            for fname in features_to_check:
                baseline_values = self._feature_baseline.get(fname, [])
                current_values = self._feature_current.get(fname, [])
                
                if len(baseline_values) < 30 or len(current_values) < 30:
                    logger.warning(
                        f"Insufficient data for drift detection: {fname}",
                        extra={
                            "baseline_count": len(baseline_values),
                            "current_count": len(current_values),
                            "trace_id": trace_id
                        }
                    )
                    continue
                
                # Perform Kolmogorov-Smirnov test
                ks_statistic, p_value = stats.ks_2samp(
                    baseline_values,
                    current_values
                )
                
                # Check if drift detected
                drift_detected = p_value < self.drift_threshold
                
                # Calculate distribution statistics
                baseline_mean = np.mean(baseline_values)
                current_mean = np.mean(current_values)
                mean_shift = current_mean - baseline_mean
                mean_shift_pct = (mean_shift / baseline_mean * 100) if baseline_mean != 0 else 0
                
                drift_results[fname] = {
                    "drift_detected": drift_detected,
                    "ks_statistic": float(ks_statistic),
                    "p_value": float(p_value),
                    "baseline_mean": float(baseline_mean),
                    "current_mean": float(current_mean),
                    "mean_shift": float(mean_shift),
                    "mean_shift_pct": float(mean_shift_pct),
                    "baseline_count": len(baseline_values),
                    "current_count": len(current_values)
                }
                
                # Alert if drift detected
                if drift_detected:
                    logger.warning(
                        f"Feature drift detected: {fname}",
                        extra={
                            **drift_results[fname],
                            "trace_id": trace_id
                        }
                    )
                    
                    self.metrics.increment_feature_drift_detected(fname)
            
            logger.info(
                "Feature drift detection completed",
                extra={
                    "features_checked": len(drift_results),
                    "drifts_detected": sum(
                        1 for r in drift_results.values()
                        if r["drift_detected"]
                    ),
                    "trace_id": trace_id
                }
            )
            
            return drift_results
            
        except Exception as e:
            logger.error(
                "Failed to detect feature drift",
                extra={
                    "feature_name": feature_name,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            return {}
    
    @trace_span("drift_detector.detect_prediction_drift")
    def detect_prediction_drift(
        self,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect prediction drift using Kolmogorov-Smirnov test.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            Dictionary with drift detection results
        """
        try:
            if len(self._prediction_baseline) < 30 or len(self._prediction_current) < 30:
                logger.warning(
                    "Insufficient data for prediction drift detection",
                    extra={
                        "baseline_count": len(self._prediction_baseline),
                        "current_count": len(self._prediction_current),
                        "trace_id": trace_id
                    }
                )
                return {
                    "drift_detected": False,
                    "error": "Insufficient data"
                }
            
            # Perform Kolmogorov-Smirnov test
            ks_statistic, p_value = stats.ks_2samp(
                self._prediction_baseline,
                self._prediction_current
            )
            
            # Check if drift detected
            drift_detected = p_value < self.drift_threshold
            
            # Calculate distribution statistics
            baseline_mean = np.mean(self._prediction_baseline)
            current_mean = np.mean(self._prediction_current)
            mean_shift = current_mean - baseline_mean
            mean_shift_pct = (mean_shift / baseline_mean * 100) if baseline_mean != 0 else 0
            
            drift_result = {
                "drift_detected": drift_detected,
                "ks_statistic": float(ks_statistic),
                "p_value": float(p_value),
                "baseline_mean": float(baseline_mean),
                "current_mean": float(current_mean),
                "mean_shift": float(mean_shift),
                "mean_shift_pct": float(mean_shift_pct),
                "baseline_count": len(self._prediction_baseline),
                "current_count": len(self._prediction_current)
            }
            
            # Alert if drift detected
            if drift_detected:
                logger.warning(
                    "Prediction drift detected",
                    extra={
                        **drift_result,
                        "trace_id": trace_id
                    }
                )
                
                self.metrics.increment_prediction_drift_detected()
            
            logger.info(
                "Prediction drift detection completed",
                extra={
                    **drift_result,
                    "trace_id": trace_id
                }
            )
            
            return drift_result
            
        except Exception as e:
            logger.error(
                "Failed to detect prediction drift",
                extra={
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            return {
                "drift_detected": False,
                "error": str(e)
            }
    
    def set_baseline(self, trace_id: Optional[str] = None) -> None:
        """
        Set current data as new baseline.
        
        Args:
            trace_id: Trace ID for correlation
        """
        self._feature_baseline = self._feature_current.copy()
        self._prediction_baseline = self._prediction_current.copy()
        
        self._feature_current = defaultdict(list)
        self._prediction_current = []
        
        logger.info(
            "Set new baseline",
            extra={
                "feature_count": len(self._feature_baseline),
                "prediction_count": len(self._prediction_baseline),
                "trace_id": trace_id
            }
        )
    
    def clear_current(self, trace_id: Optional[str] = None) -> None:
        """
        Clear current data.
        
        Args:
            trace_id: Trace ID for correlation
        """
        self._feature_current = defaultdict(list)
        self._prediction_current = []
        
        logger.info(
            "Cleared current data",
            extra={"trace_id": trace_id}
        )
    
    def get_drift_summary(self, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of drift detection status.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            Drift summary dictionary
        """
        feature_drift = self.detect_feature_drift(trace_id=trace_id)
        prediction_drift = self.detect_prediction_drift(trace_id=trace_id)
        
        summary = {
            "feature_drift": feature_drift,
            "prediction_drift": prediction_drift,
            "total_features_checked": len(feature_drift),
            "features_with_drift": sum(
                1 for r in feature_drift.values()
                if r.get("drift_detected", False)
            ),
            "prediction_drift_detected": prediction_drift.get("drift_detected", False),
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(
            "Generated drift summary",
            extra={**summary, "trace_id": trace_id}
        )
        
        return summary

