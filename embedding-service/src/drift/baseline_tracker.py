"""Baseline tracking for drift detection."""

import logging
from typing import Dict, Optional
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class BaselineTracker:
    """Tracks baseline statistics for drift detection."""

    def __init__(self, window_size: int = 1000):
        """
        Initialize baseline tracker.

        Args:
            window_size: Size of sliding window for baseline
        """
        self.window_size = window_size
        self.baseline_samples = []
        self.baseline_stats = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.sample_count = 0

    def add_samples(self, samples: np.ndarray) -> None:
        """
        Add samples to baseline.

        Args:
            samples: Array of samples to add
        """
        if len(samples.shape) == 1:
            samples = samples.reshape(-1, 1)

        self.baseline_samples.extend(samples.tolist())

        # Keep only recent samples (sliding window)
        if len(self.baseline_samples) > self.window_size:
            self.baseline_samples = self.baseline_samples[-self.window_size :]

        self.sample_count += len(samples)
        self.updated_at = datetime.now()

        # Update statistics
        self._update_statistics()

    def _update_statistics(self) -> None:
        """Update baseline statistics."""
        if not self.baseline_samples:
            return

        samples_array = np.array(self.baseline_samples)

        self.baseline_stats = {
            "mean": np.mean(samples_array, axis=0),
            "std": np.std(samples_array, axis=0),
            "min": np.min(samples_array, axis=0),
            "max": np.max(samples_array, axis=0),
            "median": np.median(samples_array, axis=0),
            "q25": np.percentile(samples_array, 25, axis=0),
            "q75": np.percentile(samples_array, 75, axis=0),
            "count": len(samples_array),
        }

    def get_baseline_stats(self) -> Optional[Dict]:
        """
        Get baseline statistics.

        Returns:
            Dictionary with baseline statistics
        """
        return self.baseline_stats

    def get_baseline_samples(self) -> np.ndarray:
        """
        Get baseline samples.

        Returns:
            Array of baseline samples
        """
        return np.array(self.baseline_samples)

    def reset(self) -> None:
        """Reset baseline tracker."""
        self.baseline_samples = []
        self.baseline_stats = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.sample_count = 0
        logger.info("Baseline tracker reset")

    def get_age_seconds(self) -> float:
        """
        Get age of baseline in seconds.

        Returns:
            Age in seconds
        """
        return (datetime.now() - self.created_at).total_seconds()

    def get_update_age_seconds(self) -> float:
        """
        Get time since last update in seconds.

        Returns:
            Time since last update in seconds
        """
        return (datetime.now() - self.updated_at).total_seconds()

    def is_stale(self, max_age_seconds: float = 86400) -> bool:
        """
        Check if baseline is stale.

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            True if baseline is stale
        """
        return self.get_age_seconds() > max_age_seconds

    def get_statistics_summary(self) -> str:
        """
        Get summary of baseline statistics.

        Returns:
            String summary
        """
        if not self.baseline_stats:
            return "No baseline statistics available"

        stats = self.baseline_stats
        return (
            f"Baseline Statistics:\n"
            f"  Samples: {stats['count']}\n"
            f"  Mean: {stats['mean']}\n"
            f"  Std: {stats['std']}\n"
            f"  Min: {stats['min']}\n"
            f"  Max: {stats['max']}\n"
            f"  Median: {stats['median']}\n"
            f"  Q25: {stats['q25']}\n"
            f"  Q75: {stats['q75']}"
        )

    def compare_with_current(
        self,
        current_samples: np.ndarray,
    ) -> Dict:
        """
        Compare current samples with baseline.

        Args:
            current_samples: Current samples to compare

        Returns:
            Dictionary with comparison results
        """
        if not self.baseline_stats:
            return {"error": "No baseline statistics available"}

        if len(current_samples.shape) == 1:
            current_samples = current_samples.reshape(-1, 1)

        current_mean = np.mean(current_samples, axis=0)
        current_std = np.std(current_samples, axis=0)

        baseline_mean = self.baseline_stats["mean"]
        baseline_std = self.baseline_stats["std"]

        # Calculate differences
        mean_diff = current_mean - baseline_mean
        std_diff = current_std - baseline_std

        # Calculate relative differences
        mean_rel_diff = mean_diff / (np.abs(baseline_mean) + 1e-9)
        std_rel_diff = std_diff / (np.abs(baseline_std) + 1e-9)

        return {
            "current_mean": current_mean,
            "current_std": current_std,
            "baseline_mean": baseline_mean,
            "baseline_std": baseline_std,
            "mean_diff": mean_diff,
            "std_diff": std_diff,
            "mean_rel_diff": mean_rel_diff,
            "std_rel_diff": std_rel_diff,
            "current_count": len(current_samples),
        }

    def export_baseline(self) -> Dict:
        """
        Export baseline for persistence.

        Returns:
            Dictionary with baseline data
        """
        return {
            "baseline_samples": self.baseline_samples,
            "baseline_stats": self.baseline_stats,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sample_count": self.sample_count,
            "window_size": self.window_size,
        }

    def import_baseline(self, data: Dict) -> None:
        """
        Import baseline from persistence.

        Args:
            data: Dictionary with baseline data
        """
        self.baseline_samples = data.get("baseline_samples", [])
        self.baseline_stats = data.get("baseline_stats")
        self.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        self.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        self.sample_count = data.get("sample_count", 0)
        self.window_size = data.get("window_size", self.window_size)

        logger.info(f"Imported baseline with {self.sample_count} samples")

