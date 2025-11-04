"""Centroid computation and representative article selection."""

import logging
from typing import List, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class CentroidCalculator:
    """Computes cluster centroids and selects representative articles."""

    @staticmethod
    def compute_weighted_centroid(
        embeddings: np.ndarray,
        weights: np.ndarray,
    ) -> np.ndarray:
        """
        Compute weighted centroid of embeddings.

        Args:
            embeddings: Array of shape (n_samples, n_features)
            weights: Weight array of shape (n_samples,)

        Returns:
            Centroid vector of shape (n_features,)
        """
        if len(embeddings) == 0:
            raise ValueError("Empty embeddings array")

        # Normalize weights
        weights = weights / np.sum(weights)

        # Weighted sum
        centroid = np.sum(embeddings * weights[:, np.newaxis], axis=0)

        # L2 normalize
        centroid = centroid / np.linalg.norm(centroid)

        logger.debug(f"Computed weighted centroid (shape: {centroid.shape})")
        return centroid

    @staticmethod
    def compute_unweighted_centroid(embeddings: np.ndarray) -> np.ndarray:
        """
        Compute unweighted centroid (mean).

        Args:
            embeddings: Array of shape (n_samples, n_features)

        Returns:
            Centroid vector of shape (n_features,)
        """
        if len(embeddings) == 0:
            raise ValueError("Empty embeddings array")

        centroid = np.mean(embeddings, axis=0)
        centroid = centroid / np.linalg.norm(centroid)

        logger.debug(f"Computed unweighted centroid (shape: {centroid.shape})")
        return centroid

    @staticmethod
    def select_representative_article(
        embeddings: np.ndarray,
        centroid: np.ndarray,
        article_ids: List[str],
    ) -> str:
        """
        Select article closest to centroid.

        Args:
            embeddings: Array of shape (n_samples, n_features)
            centroid: Centroid vector of shape (n_features,)
            article_ids: List of article IDs

        Returns:
            ID of representative article
        """
        if len(embeddings) == 0:
            raise ValueError("Empty embeddings array")

        # Compute cosine similarity to centroid
        similarities = cosine_similarity(embeddings, centroid.reshape(1, -1)).flatten()

        # Return article with highest similarity
        best_idx = np.argmax(similarities)
        representative_id = article_ids[best_idx]

        logger.debug(
            f"Selected representative article: {representative_id} "
            f"(similarity: {similarities[best_idx]:.3f})"
        )

        return representative_id

    @staticmethod
    def select_medoid(
        embeddings: np.ndarray,
        article_ids: List[str],
    ) -> str:
        """
        Select medoid (article minimizing sum of distances to all others).

        Args:
            embeddings: Array of shape (n_samples, n_features)
            article_ids: List of article IDs

        Returns:
            ID of medoid article
        """
        if len(embeddings) == 0:
            raise ValueError("Empty embeddings array")

        # Compute pairwise distances
        distances = 1 - cosine_similarity(embeddings)

        # Sum distances for each point
        sum_distances = np.sum(distances, axis=1)

        # Return article with minimum sum
        medoid_idx = np.argmin(sum_distances)
        medoid_id = article_ids[medoid_idx]

        logger.debug(
            f"Selected medoid article: {medoid_id} "
            f"(sum_distance: {sum_distances[medoid_idx]:.3f})"
        )

        return medoid_id

    @staticmethod
    def compute_cluster_statistics(
        embeddings: np.ndarray,
        similarities: np.ndarray,
    ) -> dict:
        """
        Compute statistical metrics for cluster.

        Args:
            embeddings: Array of shape (n_samples, n_features)
            similarities: Pairwise similarity matrix

        Returns:
            Dictionary of statistics
        """
        return {
            "similarity_avg": float(np.mean(similarities)),
            "similarity_min": float(np.min(similarities)),
            "similarity_max": float(np.max(similarities)),
            "similarity_std": float(np.std(similarities)),
            "similarity_median": float(np.median(similarities)),
            "embedding_dimension": embeddings.shape[1],
        }

