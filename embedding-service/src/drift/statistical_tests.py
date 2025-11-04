"""Statistical tests for drift detection."""

import logging
from typing import Tuple
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class StatisticalTests:
    """Statistical tests for detecting distribution drift."""

    @staticmethod
    def kolmogorov_smirnov_test(
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Kolmogorov-Smirnov test for distribution difference.

        Args:
            baseline: Baseline distribution samples
            current: Current distribution samples

        Returns:
            Tuple of (statistic, p_value)
        """
        statistic, p_value = stats.ks_2samp(baseline, current)
        return statistic, p_value

    @staticmethod
    def anderson_darling_test(
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Anderson-Darling test for distribution difference.

        Args:
            baseline: Baseline distribution samples
            current: Current distribution samples

        Returns:
            Tuple of (statistic, p_value)
        """
        # Anderson-Darling test
        result = stats.anderson_ksamp([baseline, current])
        return result.statistic, result.pvalue

    @staticmethod
    def wasserstein_distance(
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> float:
        """
        Wasserstein distance between distributions.

        Args:
            baseline: Baseline distribution samples
            current: Current distribution samples

        Returns:
            Wasserstein distance
        """
        distance = stats.wasserstein_distance(baseline, current)
        return distance

    @staticmethod
    def energy_distance(
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> float:
        """
        Energy distance between distributions.

        Args:
            baseline: Baseline distribution samples
            current: Current distribution samples

        Returns:
            Energy distance
        """
        distance = stats.energy_distance(baseline, current)
        return distance

    @staticmethod
    def mann_whitney_u_test(
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Mann-Whitney U test for distribution difference.

        Args:
            baseline: Baseline distribution samples
            current: Current distribution samples

        Returns:
            Tuple of (statistic, p_value)
        """
        statistic, p_value = stats.mannwhitneyu(baseline, current)
        return statistic, p_value

    @staticmethod
    def kruskal_wallis_test(
        *samples,
    ) -> Tuple[float, float]:
        """
        Kruskal-Wallis test for multiple distributions.

        Args:
            *samples: Variable number of sample arrays

        Returns:
            Tuple of (statistic, p_value)
        """
        statistic, p_value = stats.kruskal(*samples)
        return statistic, p_value

    @staticmethod
    def chi_square_test(
        baseline_hist: np.ndarray,
        current_hist: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Chi-square test for histogram difference.

        Args:
            baseline_hist: Baseline histogram
            current_hist: Current histogram

        Returns:
            Tuple of (statistic, p_value)
        """
        # Add small constant to avoid division by zero
        baseline_hist = baseline_hist + 1e-10
        current_hist = current_hist + 1e-10

        statistic, p_value = stats.chisquare(current_hist, baseline_hist)
        return statistic, p_value

    @staticmethod
    def hellinger_distance(
        baseline_hist: np.ndarray,
        current_hist: np.ndarray,
    ) -> float:
        """
        Hellinger distance between histograms.

        Args:
            baseline_hist: Baseline histogram
            current_hist: Current histogram

        Returns:
            Hellinger distance
        """
        # Normalize histograms
        baseline_norm = baseline_hist / np.sum(baseline_hist)
        current_norm = current_hist / np.sum(current_hist)

        # Calculate Hellinger distance
        distance = np.sqrt(0.5 * np.sum((np.sqrt(baseline_norm) - np.sqrt(current_norm)) ** 2))
        return distance

    @staticmethod
    def jensen_shannon_divergence(
        baseline_hist: np.ndarray,
        current_hist: np.ndarray,
    ) -> float:
        """
        Jensen-Shannon divergence between histograms.

        Args:
            baseline_hist: Baseline histogram
            current_hist: Current histogram

        Returns:
            Jensen-Shannon divergence
        """
        # Normalize histograms
        baseline_norm = baseline_hist / np.sum(baseline_hist)
        current_norm = current_hist / np.sum(current_hist)

        # Calculate Jensen-Shannon divergence
        divergence = stats.entropy(baseline_norm, current_norm)
        return divergence

    @staticmethod
    def mean_shift_test(
        baseline: np.ndarray,
        current: np.ndarray,
        alpha: float = 0.05,
    ) -> Tuple[bool, float]:
        """
        Test for significant mean shift.

        Args:
            baseline: Baseline samples
            current: Current samples
            alpha: Significance level

        Returns:
            Tuple of (is_significant, p_value)
        """
        # T-test for mean difference
        statistic, p_value = stats.ttest_ind(baseline, current)
        is_significant = p_value < alpha

        return is_significant, p_value

    @staticmethod
    def variance_shift_test(
        baseline: np.ndarray,
        current: np.ndarray,
        alpha: float = 0.05,
    ) -> Tuple[bool, float]:
        """
        Test for significant variance shift.

        Args:
            baseline: Baseline samples
            current: Current samples
            alpha: Significance level

        Returns:
            Tuple of (is_significant, p_value)
        """
        # Levene's test for variance difference
        statistic, p_value = stats.levene(baseline, current)
        is_significant = p_value < alpha

        return is_significant, p_value

    @staticmethod
    def distribution_shift_test(
        baseline: np.ndarray,
        current: np.ndarray,
        alpha: float = 0.05,
    ) -> Tuple[bool, float]:
        """
        Comprehensive test for distribution shift.

        Args:
            baseline: Baseline samples
            current: Current samples
            alpha: Significance level

        Returns:
            Tuple of (is_significant, p_value)
        """
        # Use KS test as primary test
        statistic, p_value = stats.ks_2samp(baseline, current)
        is_significant = p_value < alpha

        return is_significant, p_value

