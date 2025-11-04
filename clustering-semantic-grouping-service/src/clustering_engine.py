"""Clustering engine with HDBSCAN and DBSCAN support."""

import logging
from typing import Tuple, Optional
import numpy as np
from hdbscan import HDBSCAN
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.model_selection import ParameterGrid

logger = logging.getLogger(__name__)


class ClusteringEngine:
    """Performs density-based clustering on embeddings."""

    def __init__(
        self,
        algorithm: str = "hdbscan",
        min_cluster_size: int = 3,
        min_samples: int = 2,
        cluster_selection_epsilon: float = 0.15,
        metric: str = "cosine",
    ):
        """
        Initialize clustering engine.

        Args:
            algorithm: "hdbscan" or "dbscan"
            min_cluster_size: Minimum cluster size
            min_samples: Minimum samples for core points
            cluster_selection_epsilon: Similarity threshold
            metric: Distance metric (cosine, euclidean, etc.)
        """
        self.algorithm = algorithm
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.cluster_selection_epsilon = cluster_selection_epsilon
        self.metric = metric
        logger.info(
            f"Initialized ClusteringEngine: algorithm={algorithm}, "
            f"min_cluster_size={min_cluster_size}, metric={metric}"
        )

    def cluster(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Perform clustering on embeddings.

        Args:
            embeddings: Array of shape (n_samples, n_features)

        Returns:
            Cluster labels array (shape: n_samples,)
        """
        if len(embeddings) == 0:
            logger.warning("Empty embeddings array")
            return np.array([])

        logger.info(f"Clustering {len(embeddings)} embeddings with {self.algorithm}")

        try:
            if self.algorithm == "hdbscan":
                labels = self._cluster_hdbscan(embeddings)
            elif self.algorithm == "dbscan":
                labels = self._cluster_dbscan(embeddings)
            else:
                raise ValueError(f"Unknown algorithm: {self.algorithm}")

            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = np.sum(labels == -1)
            logger.info(
                f"Clustering complete: {n_clusters} clusters, {n_noise} noise points"
            )

            return labels

        except Exception as e:
            logger.error(f"Clustering failed: {e}", exc_info=True)
            raise

    def _cluster_hdbscan(self, embeddings: np.ndarray) -> np.ndarray:
        """Perform HDBSCAN clustering."""
        # HDBSCAN supports: euclidean, manhattan, chebyshev, minkowski
        # For cosine distance, we need to precompute distance matrix or use euclidean on normalized vectors
        # Using euclidean on normalized vectors approximates cosine distance
        metric = "euclidean" if self.metric == "cosine" else self.metric

        clusterer = HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric=metric,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            cluster_selection_method="eom",
            prediction_data=True,
            core_dist_n_jobs=-1,
        )
        labels = clusterer.fit_predict(embeddings)
        return labels

    def _cluster_dbscan(self, embeddings: np.ndarray) -> np.ndarray:
        """Perform DBSCAN clustering."""
        # Convert similarity threshold to distance
        eps = 1.0 - self.cluster_selection_epsilon
        # DBSCAN supports: euclidean, manhattan, chebyshev, minkowski, cosine, etc.
        # Use cosine directly for DBSCAN
        metric = self.metric

        clusterer = DBSCAN(
            eps=eps,
            min_samples=self.min_samples,
            metric=metric,
            n_jobs=-1,
        )
        labels = clusterer.fit_predict(embeddings)
        return labels

    def tune_parameters(
        self,
        embeddings: np.ndarray,
        sample_size: int = 1000,
    ) -> dict:
        """
        Auto-tune clustering parameters using grid search.

        Args:
            embeddings: Array of embeddings
            sample_size: Sample size for tuning

        Returns:
            Best parameters dictionary
        """
        logger.info(f"Tuning parameters on sample of {sample_size} embeddings")

        # Sample for efficiency
        if len(embeddings) > sample_size:
            indices = np.random.choice(len(embeddings), sample_size, replace=False)
            sample = embeddings[indices]
        else:
            sample = embeddings

        # Grid search
        param_grid = {
            "min_cluster_size": [3, 5, 7, 10],
            "min_samples": [2, 3, 5],
            "cluster_selection_epsilon": [0.10, 0.15, 0.20],
        }

        best_score = -1
        best_params = None

        for params in ParameterGrid(param_grid):
            try:
                clusterer = HDBSCAN(
                    **params,
                    metric=self.metric,
                    cluster_selection_method="eom",
                    prediction_data=True,
                )
                labels = clusterer.fit_predict(sample)

                # Skip if too few clusters or too many noise points
                n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                noise_ratio = np.sum(labels == -1) / len(labels)

                if n_clusters < 2 or noise_ratio > 0.5:
                    continue

                # Compute silhouette score
                if n_clusters > 1:
                    mask = labels != -1
                    if np.sum(mask) > 10:
                        score = silhouette_score(sample[mask], labels[mask], metric=self.metric)

                        if score > best_score:
                            best_score = score
                            best_params = params

            except Exception as e:
                logger.debug(f"Parameter set failed: {params}, error: {e}")
                continue

        if best_params is None:
            best_params = {
                "min_cluster_size": 5,
                "min_samples": 2,
                "cluster_selection_epsilon": 0.15,
            }
            logger.warning(f"No valid parameters found, using defaults: {best_params}")
        else:
            logger.info(f"Best parameters found: {best_params} (score: {best_score:.3f})")

        return best_params

