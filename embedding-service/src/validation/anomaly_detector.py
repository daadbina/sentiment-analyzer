"""Anomaly detection for embeddings."""

import logging
from typing import List, Tuple
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalous embeddings using statistical methods."""

    def __init__(
        self,
        z_score_threshold: float = 3.0,
        isolation_forest_contamination: float = 0.1,
    ):
        """
        Initialize anomaly detector.

        Args:
            z_score_threshold: Z-score threshold for outliers
            isolation_forest_contamination: Contamination parameter for Isolation Forest
        """
        self.z_score_threshold = z_score_threshold
        self.isolation_forest_contamination = isolation_forest_contamination
        self.baseline_mean = None
        self.baseline_std = None

    def fit_baseline(self, embeddings: np.ndarray) -> None:
        """
        Fit baseline statistics from embeddings.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)
        """
        self.baseline_mean = np.mean(embeddings, axis=0)
        self.baseline_std = np.std(embeddings, axis=0)

        logger.info(
            f"Fitted baseline: mean_norm={np.linalg.norm(self.baseline_mean):.4f}, "
            f"std_norm={np.linalg.norm(self.baseline_std):.4f}"
        )

    def detect_z_score_anomalies(
        self,
        embeddings: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies using Z-score method.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)

        Returns:
            Tuple of (anomaly_flags, z_scores)
        """
        if self.baseline_mean is None:
            self.fit_baseline(embeddings)

        # Calculate Z-scores
        z_scores = np.abs(
            (embeddings - self.baseline_mean) / (self.baseline_std + 1e-9)
        )

        # Max Z-score per sample
        max_z_scores = np.max(z_scores, axis=1)

        # Detect anomalies
        anomalies = max_z_scores > self.z_score_threshold

        logger.debug(
            f"Z-score anomalies: {np.sum(anomalies)}/{len(embeddings)} "
            f"(threshold={self.z_score_threshold})"
        )

        return anomalies, max_z_scores

    def detect_magnitude_anomalies(
        self,
        embeddings: np.ndarray,
        threshold_std: float = 3.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies based on embedding magnitude.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)
            threshold_std: Number of standard deviations for threshold

        Returns:
            Tuple of (anomaly_flags, magnitudes)
        """
        # Calculate magnitudes
        magnitudes = np.linalg.norm(embeddings, axis=1)

        # Calculate statistics
        mean_mag = np.mean(magnitudes)
        std_mag = np.std(magnitudes)

        # Detect anomalies
        threshold = mean_mag + threshold_std * std_mag
        anomalies = magnitudes > threshold

        logger.debug(
            f"Magnitude anomalies: {np.sum(anomalies)}/{len(embeddings)} "
            f"(threshold={threshold:.4f})"
        )

        return anomalies, magnitudes

    def detect_cosine_distance_anomalies(
        self,
        embeddings: np.ndarray,
        reference_embedding: np.ndarray = None,
        threshold_percentile: float = 95.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies based on cosine distance from reference.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)
            reference_embedding: Reference embedding (uses mean if None)
            threshold_percentile: Percentile for threshold

        Returns:
            Tuple of (anomaly_flags, distances)
        """
        if reference_embedding is None:
            reference_embedding = np.mean(embeddings, axis=0)

        # Normalize
        ref_norm = reference_embedding / (np.linalg.norm(reference_embedding) + 1e-9)
        emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9)

        # Calculate cosine distances
        distances = 1 - np.dot(emb_norm, ref_norm)

        # Calculate threshold
        threshold = np.percentile(distances, threshold_percentile)

        # Detect anomalies
        anomalies = distances > threshold

        logger.debug(
            f"Cosine distance anomalies: {np.sum(anomalies)}/{len(embeddings)} "
            f"(threshold={threshold:.4f})"
        )

        return anomalies, distances

    def detect_isolation_forest_anomalies(
        self,
        embeddings: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies using Isolation Forest.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)

        Returns:
            Tuple of (anomaly_flags, anomaly_scores)
        """
        try:
            from sklearn.ensemble import IsolationForest

            # Fit Isolation Forest
            iso_forest = IsolationForest(
                contamination=self.isolation_forest_contamination,
                random_state=42,
            )

            # Predict anomalies (-1 for anomalies, 1 for normal)
            predictions = iso_forest.fit_predict(embeddings)
            anomalies = predictions == -1

            # Get anomaly scores
            scores = -iso_forest.score_samples(embeddings)

            logger.debug(
                f"Isolation Forest anomalies: {np.sum(anomalies)}/{len(embeddings)}"
            )

            return anomalies, scores

        except ImportError:
            logger.warning("scikit-learn not available, skipping Isolation Forest")
            return np.zeros(len(embeddings), dtype=bool), np.zeros(len(embeddings))

    def detect_local_outlier_factor_anomalies(
        self,
        embeddings: np.ndarray,
        n_neighbors: int = 20,
        threshold_percentile: float = 95.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies using Local Outlier Factor.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)
            n_neighbors: Number of neighbors for LOF
            threshold_percentile: Percentile for threshold

        Returns:
            Tuple of (anomaly_flags, lof_scores)
        """
        try:
            from sklearn.neighbors import LocalOutlierFactor

            # Fit LOF
            lof = LocalOutlierFactor(n_neighbors=n_neighbors)
            predictions = lof.fit_predict(embeddings)
            anomalies = predictions == -1

            # Get LOF scores
            scores = -lof.negative_outlier_factor_

            logger.debug(
                f"LOF anomalies: {np.sum(anomalies)}/{len(embeddings)}"
            )

            return anomalies, scores

        except ImportError:
            logger.warning("scikit-learn not available, skipping LOF")
            return np.zeros(len(embeddings), dtype=bool), np.zeros(len(embeddings))

    def detect_ensemble_anomalies(
        self,
        embeddings: np.ndarray,
        methods: List[str] = None,
        voting_threshold: float = 0.5,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies using ensemble of methods.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)
            methods: List of methods to use
            voting_threshold: Fraction of methods that must vote anomaly

        Returns:
            Tuple of (anomaly_flags, ensemble_scores)
        """
        if methods is None:
            methods = ["z_score", "magnitude", "cosine_distance"]

        votes = np.zeros(len(embeddings))

        if "z_score" in methods:
            anomalies, _ = self.detect_z_score_anomalies(embeddings)
            votes += anomalies.astype(int)

        if "magnitude" in methods:
            anomalies, _ = self.detect_magnitude_anomalies(embeddings)
            votes += anomalies.astype(int)

        if "cosine_distance" in methods:
            anomalies, _ = self.detect_cosine_distance_anomalies(embeddings)
            votes += anomalies.astype(int)

        # Ensemble decision
        ensemble_anomalies = votes >= (len(methods) * voting_threshold)

        logger.debug(
            f"Ensemble anomalies: {np.sum(ensemble_anomalies)}/{len(embeddings)} "
            f"(methods={methods}, threshold={voting_threshold})"
        )

        return ensemble_anomalies, votes / len(methods)

