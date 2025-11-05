"""Label drift detection engine."""

import statistics
from typing import Dict, List, Any, Tuple, Optional
from collections import deque
from src.config import config
from src.utils.trace import get_logger


logger = get_logger(__name__, config.logging.log_level)


class DriftDetector:
    """Monitor label distribution shifts and anomalies."""

    def __init__(self, window_size: int = 100):
        """
        Initialize drift detector.
        
        Args:
            window_size: Number of labels to keep in history for drift detection
        """
        self.window_size = window_size
        self.confidence_history: Dict[str, deque] = {}
        self.label_count_history: Dict[str, deque] = {}
        
        logger.info(
            "Drift detector initialized",
            operation="init",
            window_size=window_size
        )

    def _add_to_history(
        self,
        history: Dict[str, deque],
        source: str,
        value: float
    ) -> None:
        """Add value to history for source."""
        if source not in history:
            history[source] = deque(maxlen=self.window_size)
        
        history[source].append(value)

    def compute_confidence_stats(
        self,
        source: str
    ) -> Dict[str, float]:
        """
        Compute confidence statistics for source.
        
        Returns:
            Dict with mean, stdev, min, max
        """
        try:
            if source not in self.confidence_history or len(self.confidence_history[source]) == 0:
                return {
                    "mean": 0.0,
                    "stdev": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "count": 0
                }
            
            values = list(self.confidence_history[source])
            
            if len(values) == 1:
                return {
                    "mean": values[0],
                    "stdev": 0.0,
                    "min": values[0],
                    "max": values[0],
                    "count": 1
                }
            
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            
            return {
                "mean": mean,
                "stdev": stdev,
                "min": min(values),
                "max": max(values),
                "count": len(values)
            }
        except Exception as e:
            logger.error(
                f"Failed to compute confidence stats: {str(e)}",
                operation="compute_confidence_stats",
                source=source,
                error_type=type(e).__name__
            )
            return {
                "mean": 0.0,
                "stdev": 0.0,
                "min": 0.0,
                "max": 0.0,
                "count": 0
            }

    def detect_confidence_drift(
        self,
        source: str,
        labels: List[Dict[str, Any]]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect drift in label confidence scores.
        
        Returns:
            Tuple of (drift_detected: bool, drift_info: Dict)
        """
        try:
            if not labels:
                return False, {}
            
            # Extract confidence scores
            confidences = [label.get("confidence", 0.0) for label in labels]
            
            # Add to history
            for conf in confidences:
                self._add_to_history(self.confidence_history, source, conf)
            
            # Compute current batch stats
            batch_mean = statistics.mean(confidences)
            batch_stdev = statistics.stdev(confidences) if len(confidences) > 1 else 0.0
            
            # Get historical stats
            hist_stats = self.compute_confidence_stats(source)
            
            # Detect drift: if batch mean deviates >2 stdev from historical mean
            if hist_stats["count"] >= self.window_size:
                hist_mean = hist_stats["mean"]
                hist_stdev = hist_stats["stdev"]
                
                if hist_stdev > 0:
                    z_score = abs(batch_mean - hist_mean) / hist_stdev
                    
                    if z_score > 2.0:  # 2-sigma threshold
                        logger.warning(
                            f"Confidence drift detected",
                            operation="detect_confidence_drift",
                            source=source,
                            z_score=z_score,
                            batch_mean=batch_mean,
                            hist_mean=hist_mean,
                            hist_stdev=hist_stdev
                        )
                        
                        return True, {
                            "source": source,
                            "z_score": z_score,
                            "batch_mean": batch_mean,
                            "batch_stdev": batch_stdev,
                            "hist_mean": hist_mean,
                            "hist_stdev": hist_stdev,
                            "drift_type": "confidence"
                        }
            
            return False, {}
        
        except Exception as e:
            logger.error(
                f"Drift detection failed: {str(e)}",
                operation="detect_confidence_drift",
                source=source,
                error_type=type(e).__name__
            )
            return False, {}

    def detect_volume_drift(
        self,
        source: str,
        label_count: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect drift in label volume.
        
        Returns:
            Tuple of (drift_detected: bool, drift_info: Dict)
        """
        try:
            # Add to history
            self._add_to_history(self.label_count_history, source, float(label_count))
            
            if source not in self.label_count_history or len(self.label_count_history[source]) < 5:
                return False, {}
            
            counts = list(self.label_count_history[source])
            mean_count = statistics.mean(counts)
            stdev_count = statistics.stdev(counts) if len(counts) > 1 else 0.0
            
            # Detect drift: if current count deviates >2 stdev from mean
            if stdev_count > 0:
                z_score = abs(label_count - mean_count) / stdev_count
                
                if z_score > 2.0:
                    logger.warning(
                        f"Volume drift detected",
                        operation="detect_volume_drift",
                        source=source,
                        z_score=z_score,
                        current_count=label_count,
                        mean_count=mean_count,
                        stdev_count=stdev_count
                    )
                    
                    return True, {
                        "source": source,
                        "z_score": z_score,
                        "current_count": label_count,
                        "mean_count": mean_count,
                        "stdev_count": stdev_count,
                        "drift_type": "volume"
                    }
            
            return False, {}
        
        except Exception as e:
            logger.error(
                f"Volume drift detection failed: {str(e)}",
                operation="detect_volume_drift",
                source=source,
                error_type=type(e).__name__
            )
            return False, {}

    def clear_history(self) -> None:
        """Clear drift detection history."""
        try:
            self.confidence_history.clear()
            self.label_count_history.clear()
            logger.info(
                "Drift detection history cleared",
                operation="clear_history"
            )
        except Exception as e:
            logger.error(
                f"Failed to clear history: {str(e)}",
                operation="clear_history",
                error_type=type(e).__name__
            )

