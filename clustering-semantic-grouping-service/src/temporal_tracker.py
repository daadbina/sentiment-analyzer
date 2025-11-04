"""Temporal tracking of cluster evolution and lineage."""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class TemporalTracker:
    """Tracks cluster evolution and lineage over time."""

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize temporal tracker.

        Args:
            similarity_threshold: Threshold for cluster matching
        """
        self.similarity_threshold = similarity_threshold
        self.cluster_history = {}
        logger.info(f"Initialized TemporalTracker: threshold={similarity_threshold}")

    def match_clusters(
        self,
        current_centroids: np.ndarray,
        previous_centroids: np.ndarray,
        current_cluster_ids: List[str],
        previous_cluster_ids: List[str],
    ) -> Dict[str, str]:
        """
        Match current clusters to previous clusters.

        Args:
            current_centroids: Current cluster centroids
            previous_centroids: Previous cluster centroids
            current_cluster_ids: Current cluster IDs
            previous_cluster_ids: Previous cluster IDs

        Returns:
            Mapping of current cluster ID to previous cluster ID
        """
        if len(previous_centroids) == 0:
            logger.info("No previous clusters, all current clusters are new")
            return {}

        # Compute similarity matrix
        similarities = cosine_similarity(current_centroids, previous_centroids)

        # Match clusters
        matches = {}
        matched_previous = set()

        for i, current_id in enumerate(current_cluster_ids):
            # Find best match
            best_j = np.argmax(similarities[i])
            best_similarity = similarities[i, best_j]

            if best_similarity >= self.similarity_threshold and best_j not in matched_previous:
                previous_id = previous_cluster_ids[best_j]
                matches[current_id] = previous_id
                matched_previous.add(best_j)
                logger.debug(
                    f"Matched cluster {current_id} to {previous_id} "
                    f"(similarity: {best_similarity:.3f})"
                )

        logger.info(
            f"Matched {len(matches)} current clusters to previous clusters "
            f"({len(current_cluster_ids) - len(matches)} new)"
        )

        return matches

    def track_cluster_evolution(
        self,
        cluster_id: str,
        articles: List[dict],
        centroid: np.ndarray,
        timestamp: datetime,
        parent_cluster_id: Optional[str] = None,
    ) -> dict:
        """
        Track evolution of a cluster.

        Args:
            cluster_id: Current cluster ID
            articles: Articles in cluster
            centroid: Cluster centroid
            timestamp: Cluster creation timestamp
            parent_cluster_id: Parent cluster ID if matched

        Returns:
            Evolution record
        """
        evolution = {
            "cluster_id": cluster_id,
            "parent_cluster_id": parent_cluster_id,
            "timestamp": timestamp.isoformat(),
            "article_count": len(articles),
            "article_ids": [a.get("article_id") for a in articles],
            "centroid_vector": centroid.tolist(),
        }

        # Store in history
        if cluster_id not in self.cluster_history:
            self.cluster_history[cluster_id] = []

        self.cluster_history[cluster_id].append(evolution)

        logger.debug(
            f"Tracked evolution for cluster {cluster_id}: "
            f"parent={parent_cluster_id}, articles={len(articles)}"
        )

        return evolution

    def get_cluster_lineage(self, cluster_id: str) -> List[dict]:
        """
        Get complete lineage for a cluster.

        Args:
            cluster_id: Cluster ID

        Returns:
            List of evolution records
        """
        return self.cluster_history.get(cluster_id, [])

    def compute_cluster_stability(
        self,
        cluster_id: str,
        window_size: int = 3,
    ) -> float:
        """
        Compute stability score for cluster.

        Args:
            cluster_id: Cluster ID
            window_size: Number of recent snapshots to consider

        Returns:
            Stability score (0-1)
        """
        history = self.get_cluster_lineage(cluster_id)

        if len(history) < 2:
            return 1.0  # New clusters are considered stable

        # Get recent snapshots
        recent = history[-window_size:]

        # Compute centroid similarity
        centroids = np.array([h["centroid_vector"] for h in recent])
        similarities = cosine_similarity(centroids)

        # Average pairwise similarity
        mask = np.triu(np.ones_like(similarities), k=1).astype(bool)
        avg_similarity = np.mean(similarities[mask])

        logger.debug(
            f"Cluster {cluster_id} stability: {avg_similarity:.3f} "
            f"(based on {len(recent)} snapshots)"
        )

        return float(avg_similarity)

    def detect_cluster_merges(
        self,
        current_clusters: Dict[str, dict],
        previous_clusters: Dict[str, dict],
    ) -> List[Tuple[List[str], str]]:
        """
        Detect cluster merges (multiple previous clusters → one current).

        Args:
            current_clusters: Current cluster data
            previous_clusters: Previous cluster data

        Returns:
            List of (source_cluster_ids, target_cluster_id) tuples
        """
        merges = []

        # For each current cluster, find all previous clusters that contributed
        for current_id, current_data in current_clusters.items():
            current_articles = set(current_data.get("article_ids", []))

            contributing_previous = []
            for previous_id, previous_data in previous_clusters.items():
                previous_articles = set(previous_data.get("article_ids", []))
                overlap = len(current_articles & previous_articles)

                if overlap > 0:
                    contributing_previous.append(previous_id)

            if len(contributing_previous) > 1:
                merges.append((contributing_previous, current_id))
                logger.info(
                    f"Detected merge: {contributing_previous} → {current_id}"
                )

        return merges

    def detect_cluster_splits(
        self,
        current_clusters: Dict[str, dict],
        previous_clusters: Dict[str, dict],
    ) -> List[Tuple[str, List[str]]]:
        """
        Detect cluster splits (one previous cluster → multiple current).

        Args:
            current_clusters: Current cluster data
            previous_clusters: Previous cluster data

        Returns:
            List of (source_cluster_id, target_cluster_ids) tuples
        """
        splits = []

        # For each previous cluster, find all current clusters it contributed to
        for previous_id, previous_data in previous_clusters.items():
            previous_articles = set(previous_data.get("article_ids", []))

            contributing_current = []
            for current_id, current_data in current_clusters.items():
                current_articles = set(current_data.get("article_ids", []))
                overlap = len(current_articles & previous_articles)

                if overlap > 0:
                    contributing_current.append(current_id)

            if len(contributing_current) > 1:
                splits.append((previous_id, contributing_current))
                logger.info(
                    f"Detected split: {previous_id} → {contributing_current}"
                )

        return splits

