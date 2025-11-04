"""Drift detection for embedding distributions."""

import logging
import numpy as np
from collections import deque
from typing import Optional, Dict
from scipy import stats

from src.config import config
from src.metrics import embedding_drift_score
from src.exceptions import DriftDetectionError

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detects distribution drift in embeddings."""

    def __init__(
        self,
        sample_size: int = 1000,
        drift_threshold: float = 0.05,
    ):
        """
        Initialize drift detector.

        Args:
            sample_size: Number of samples to maintain for baseline
            drift_threshold: KS statistic threshold for drift detection
        """
        self.sample_size = sample_size
        self.drift_threshold = drift_threshold
        self.baseline_samples: deque = deque(maxlen=sample_size)
        self.baseline_stats: Optional[Dict] = None
        self._is_initialized = False

    def add_samples(self, embeddings: np.ndarray) -> None:
        """
        Add embedding samples to the detector.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)
        """
        if embeddings.size == 0:
            return

        # Flatten embeddings to 1D for distribution analysis
        flattened = embeddings.flatten()

        for value in flattened:
            self.baseline_samples.append(value)

        # Update baseline stats when we have enough samples
        if len(self.baseline_samples) >= self.sample_size and not self._is_initialized:
            self._compute_baseline_stats()
            self._is_initialized = True

    def _compute_baseline_stats(self) -> None:
        """Compute baseline statistics from samples."""
        samples = np.array(list(self.baseline_samples))

        self.baseline_stats = {
            "mean": float(np.mean(samples)),
            "std": float(np.std(samples)),
            "min": float(np.min(samples)),
            "max": float(np.max(samples)),
            "median": float(np.median(samples)),
        }

        logger.info(
            f"Baseline stats computed: mean={self.baseline_stats['mean']:.4f}, "
            f"std={self.baseline_stats['std']:.4f}"
        )

    def detect_drift(self, embeddings: np.ndarray) -> Dict:
        """
        Detect drift in new embeddings.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)

        Returns:
            Dictionary with drift detection results
        """
        if not self._is_initialized or self.baseline_stats is None:
            logger.warning("Drift detector not initialized, skipping drift detection")
            return {
                "drift_detected": False,
                "ks_statistic": 0.0,
                "p_value": 1.0,
                "reason": "detector_not_initialized",
            }

        try:
            # Flatten embeddings
            flattened = embeddings.flatten()

            # Perform Kolmogorov-Smirnov test
            baseline_samples = np.array(list(self.baseline_samples))
            ks_statistic, p_value = stats.ks_2samp(baseline_samples, flattened)

            # Determine if drift detected
            drift_detected = ks_statistic > self.drift_threshold

            # Update metrics
            embedding_drift_score.set(ks_statistic)

            logger.info(
                f"Drift detection: KS={ks_statistic:.4f}, p={p_value:.4f}, "
                f"drift={'YES' if drift_detected else 'NO'}"
            )

            return {
                "drift_detected": drift_detected,
                "ks_statistic": float(ks_statistic),
                "p_value": float(p_value),
                "threshold": self.drift_threshold,
                "reason": "ks_test",
            }

        except Exception as e:
            logger.error(f"Drift detection failed: {e}")
            raise DriftDetectionError(f"Drift detection failed: {e}")

    def get_baseline_stats(self) -> Optional[Dict]:
        """Get baseline statistics."""
        return self.baseline_stats

    def reset(self) -> None:
        """Reset detector."""
        self.baseline_samples.clear()
        self.baseline_stats = None
        self._is_initialized = False
        logger.info("Drift detector reset")

