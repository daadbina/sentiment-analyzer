"""Outlier handling for noise points in clustering."""

import numpy as np
import logging
from typing import Tuple, List, Dict, Any
from sklearn.neighbors import NearestNeighbors

logger = logging.getLogger(__name__)


class OutlierHandler:
    """Handle noise points and outliers in clustering results."""

    def __init__(
        self,
        k_neighbors: int = 5,
        distance_threshold: float = 0.5,
        reassignment_threshold: float = 0.75,
    ):
        """Initialize outlier handler.

        Args:
            k_neighbors: Number of neighbors for outlier detection
            distance_threshold: Distance threshold for outlier detection
            reassignment_threshold: Similarity threshold for reassignment
        """
        self.k_neighbors = k_neighbors
        self.distance_threshold = distance_threshold
        self.reassignment_threshold = reassignment_threshold
        logger.info(
            f"OutlierHandler initialized with k={k_neighbors}, "
            f"threshold={distance_threshold}"
        )

    def detect_outliers(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Detect outliers using k-NN distance.

        Args:
            embeddings: Article embeddings (n_samples, n_features)
            labels: Cluster labels (-1 for noise)

        Returns:
            Tuple of (outlier_mask, outlier_distances)
        """
        if len(embeddings) == 0:
            return np.array([], dtype=bool), np.array([])

        # Compute k-NN distances
        nbrs = NearestNeighbors(n_neighbors=self.k_neighbors + 1).fit(embeddings)
        distances, indices = nbrs.kneighbors(embeddings)

        # Use mean distance to k-th neighbor
        k_distances = distances[:, self.k_neighbors]

        # Detect outliers
        outlier_mask = k_distances > self.distance_threshold

        logger.debug(
            f"Detected {outlier_mask.sum()} outliers out of {len(embeddings)} points"
        )

        return outlier_mask, k_distances

    def reassign_outliers(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
        cluster_centroids: Dict[int, np.ndarray],
    ) -> np.ndarray:
        """Reassign outliers to nearest clusters.

        Args:
            embeddings: Article embeddings
            labels: Current cluster labels
            cluster_centroids: Centroids of clusters

        Returns:
            Updated labels with reassigned outliers
        """
        updated_labels = labels.copy()
        outlier_mask, _ = self.detect_outliers(embeddings, labels)

        if not outlier_mask.any():
            return updated_labels

        outlier_indices = np.where(outlier_mask)[0]
        logger.info(f"Reassigning {len(outlier_indices)} outliers")

        for idx in outlier_indices:
            embedding = embeddings[idx]

            # Find nearest cluster centroid
            min_distance = float("inf")
            nearest_cluster = -1

            for cluster_id, centroid in cluster_centroids.items():
                distance = 1 - np.dot(embedding, centroid) / (
                    np.linalg.norm(embedding) * np.linalg.norm(centroid) + 1e-8
                )

                if distance < min_distance:
                    min_distance = distance
                    nearest_cluster = cluster_id

            # Reassign if similarity is above threshold
            if min_distance < (1 - self.reassignment_threshold):
                updated_labels[idx] = nearest_cluster
                logger.debug(
                    f"Reassigned outlier {idx} to cluster {nearest_cluster} "
                    f"(distance={min_distance:.4f})"
                )

        return updated_labels

    def filter_noise_points(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
        metadata: List[Dict[str, Any]],
    ) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
        """Filter out noise points from clustering results.

        Args:
            embeddings: Article embeddings
            labels: Cluster labels
            metadata: Article metadata

        Returns:
            Tuple of (filtered_embeddings, filtered_labels, filtered_metadata)
        """
        # Keep only non-noise points
        noise_mask = labels == -1
        keep_mask = ~noise_mask

        filtered_embeddings = embeddings[keep_mask]
        filtered_labels = labels[keep_mask]
        filtered_metadata = [m for i, m in enumerate(metadata) if keep_mask[i]]

        logger.info(
            f"Filtered {noise_mask.sum()} noise points, "
            f"kept {keep_mask.sum()} points"
        )

        return filtered_embeddings, filtered_labels, filtered_metadata

    def compute_outlier_score(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
    ) -> np.ndarray:
        """Compute outlier score for each point.

        Args:
            embeddings: Article embeddings
            labels: Cluster labels

        Returns:
            Outlier scores (0-1, higher = more outlier-like)
        """
        if len(embeddings) == 0:
            return np.array([])

        outlier_mask, k_distances = self.detect_outliers(embeddings, labels)

        # Normalize distances to 0-1 range
        max_distance = np.max(k_distances) if len(k_distances) > 0 else 1.0
        scores = k_distances / (max_distance + 1e-8)

        return scores

    def handle_mixed_clusters(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
        purity_threshold: float = 0.85,
    ) -> np.ndarray:
        """Handle clusters with mixed content by removing low-purity points.

        Args:
            embeddings: Article embeddings
            labels: Cluster labels
            purity_threshold: Minimum purity threshold

        Returns:
            Updated labels with low-purity points marked as noise
        """
        updated_labels = labels.copy()
        unique_clusters = np.unique(labels[labels != -1])

        for cluster_id in unique_clusters:
            cluster_mask = labels == cluster_id
            cluster_embeddings = embeddings[cluster_mask]

            if len(cluster_embeddings) < 2:
                continue

            # Compute intra-cluster similarity
            similarities = []
            for i, emb in enumerate(cluster_embeddings):
                for j in range(i + 1, len(cluster_embeddings)):
                    sim = np.dot(emb, cluster_embeddings[j]) / (
                        np.linalg.norm(emb) * np.linalg.norm(cluster_embeddings[j])
                        + 1e-8
                    )
                    similarities.append(sim)

            if not similarities:
                continue

            avg_similarity = np.mean(similarities)

            # If cluster purity is low, mark outliers
            if avg_similarity < purity_threshold:
                logger.debug(
                    f"Cluster {cluster_id} has low purity ({avg_similarity:.4f}), "
                    "marking outliers"
                )

                # Mark points with low similarity to cluster as noise
                cluster_indices = np.where(cluster_mask)[0]
                for idx in cluster_indices:
                    point_similarities = []
                    for other_idx in cluster_indices:
                        if idx != other_idx:
                            sim = np.dot(
                                embeddings[idx], embeddings[other_idx]
                            ) / (
                                np.linalg.norm(embeddings[idx])
                                * np.linalg.norm(embeddings[other_idx])
                                + 1e-8
                            )
                            point_similarities.append(sim)

                    if point_similarities:
                        point_avg_sim = np.mean(point_similarities)
                        if point_avg_sim < purity_threshold:
                            updated_labels[idx] = -1

        return updated_labels

