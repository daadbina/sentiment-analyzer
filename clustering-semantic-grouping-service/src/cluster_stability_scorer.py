"""Cluster stability scoring and quality metrics."""

import numpy as np
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ClusterStabilityScorer:
    """Score cluster stability and quality metrics."""

    def __init__(
        self,
        min_stability_score: float = 0.70,
        history_window_size: int = 10,
    ):
        """Initialize stability scorer.

        Args:
            min_stability_score: Minimum stability score threshold
            history_window_size: Number of historical snapshots to maintain
        """
        self.min_stability_score = min_stability_score
        self.history_window_size = history_window_size
        self.cluster_history: Dict[str, List[Dict[str, Any]]] = {}
        logger.info(
            f"ClusterStabilityScorer initialized with "
            f"min_stability_score={min_stability_score}"
        )

    def compute_stability_score(
        self,
        cluster_id: str,
        current_cluster: Dict[str, Any],
    ) -> float:
        """Compute stability score for a cluster.

        Args:
            cluster_id: Cluster identifier
            current_cluster: Current cluster data

        Returns:
            Stability score (0-1)
        """
        if cluster_id not in self.cluster_history:
            # New cluster gets baseline score
            return 0.5

        history = self.cluster_history[cluster_id]
        if len(history) < 2:
            return 0.5

        # Compute stability based on:
        # 1. Membership stability (how many articles remain)
        # 2. Centroid stability (how much centroid moves)
        # 3. Size stability (how much size changes)

        membership_stability = self._compute_membership_stability(
            history, current_cluster
        )
        centroid_stability = self._compute_centroid_stability(history, current_cluster)
        size_stability = self._compute_size_stability(history, current_cluster)

        # Weighted average
        stability_score = (
            0.4 * membership_stability
            + 0.3 * centroid_stability
            + 0.3 * size_stability
        )

        logger.debug(
            f"Cluster {cluster_id} stability: "
            f"membership={membership_stability:.3f}, "
            f"centroid={centroid_stability:.3f}, "
            f"size={size_stability:.3f}, "
            f"overall={stability_score:.3f}"
        )

        return stability_score

    def _compute_membership_stability(
        self,
        history: List[Dict[str, Any]],
        current_cluster: Dict[str, Any],
    ) -> float:
        """Compute membership stability."""
        if len(history) == 0:
            return 0.5

        prev_cluster = history[-1]
        prev_articles = set(prev_cluster.get("article_ids", []))
        current_articles = set(current_cluster.get("article_ids", []))

        if len(prev_articles) == 0:
            return 0.5

        # Jaccard similarity
        intersection = len(prev_articles & current_articles)
        union = len(prev_articles | current_articles)

        if union == 0:
            return 0.0

        return intersection / union

    def _compute_centroid_stability(
        self,
        history: List[Dict[str, Any]],
        current_cluster: Dict[str, Any],
    ) -> float:
        """Compute centroid stability."""
        if len(history) == 0:
            return 0.5

        prev_cluster = history[-1]
        prev_centroid = prev_cluster.get("centroid")
        current_centroid = current_cluster.get("centroid")

        if prev_centroid is None or current_centroid is None:
            return 0.5

        # Cosine similarity between centroids
        prev_centroid = np.array(prev_centroid)
        current_centroid = np.array(current_centroid)

        similarity = np.dot(prev_centroid, current_centroid) / (
            np.linalg.norm(prev_centroid) * np.linalg.norm(current_centroid) + 1e-8
        )

        return max(0.0, similarity)

    def _compute_size_stability(
        self,
        history: List[Dict[str, Any]],
        current_cluster: Dict[str, Any],
    ) -> float:
        """Compute size stability."""
        if len(history) == 0:
            return 0.5

        prev_cluster = history[-1]
        prev_size = prev_cluster.get("article_count", 0)
        current_size = current_cluster.get("article_count", 0)

        if prev_size == 0:
            return 0.5

        # Compute relative change
        relative_change = abs(current_size - prev_size) / prev_size

        # Convert to stability score (lower change = higher stability)
        stability = max(0.0, 1.0 - relative_change)

        return stability

    def update_cluster_history(
        self,
        cluster_id: str,
        cluster_data: Dict[str, Any],
    ) -> None:
        """Update cluster history.

        Args:
            cluster_id: Cluster identifier
            cluster_data: Current cluster data
        """
        if cluster_id not in self.cluster_history:
            self.cluster_history[cluster_id] = []

        # Add current snapshot
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "article_ids": cluster_data.get("article_ids", []),
            "article_count": cluster_data.get("article_count", 0),
            "centroid": cluster_data.get("centroid"),
            "similarity_avg": cluster_data.get("similarity_avg", 0),
        }

        self.cluster_history[cluster_id].append(snapshot)

        # Maintain window size
        if len(self.cluster_history[cluster_id]) > self.history_window_size:
            self.cluster_history[cluster_id] = self.cluster_history[cluster_id][
                -self.history_window_size :
            ]

    def compute_cluster_quality_metrics(
        self,
        cluster_id: str,
        cluster_data: Dict[str, Any],
    ) -> Dict[str, float]:
        """Compute comprehensive quality metrics for a cluster.

        Args:
            cluster_id: Cluster identifier
            cluster_data: Cluster data

        Returns:
            Dictionary of quality metrics
        """
        stability_score = self.compute_stability_score(cluster_id, cluster_data)

        metrics = {
            "stability_score": stability_score,
            "article_count": cluster_data.get("article_count", 0),
            "similarity_avg": cluster_data.get("similarity_avg", 0),
            "purity": cluster_data.get("purity", 0),
            "is_stable": stability_score >= self.min_stability_score,
        }

        return metrics

    def get_cluster_quality_report(
        self,
        clusters: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Get quality report for all clusters.

        Args:
            clusters: Dictionary of clusters

        Returns:
            Quality report
        """
        if not clusters:
            return {
                "total_clusters": 0,
                "stable_clusters": 0,
                "unstable_clusters": 0,
                "avg_stability": 0,
                "quality_metrics": {},
            }

        metrics_list = []
        stable_count = 0

        for cluster_id, cluster_data in clusters.items():
            metrics = self.compute_cluster_quality_metrics(cluster_id, cluster_data)
            metrics_list.append(metrics)

            if metrics["is_stable"]:
                stable_count += 1

        stability_scores = [m["stability_score"] for m in metrics_list]

        return {
            "total_clusters": len(clusters),
            "stable_clusters": stable_count,
            "unstable_clusters": len(clusters) - stable_count,
            "avg_stability": np.mean(stability_scores) if stability_scores else 0,
            "min_stability": np.min(stability_scores) if stability_scores else 0,
            "max_stability": np.max(stability_scores) if stability_scores else 0,
            "quality_metrics": metrics_list,
        }

    def identify_degrading_clusters(
        self,
        clusters: Dict[str, Dict[str, Any]],
    ) -> List[Tuple[str, float]]:
        """Identify clusters with degrading quality.

        Args:
            clusters: Dictionary of clusters

        Returns:
            List of (cluster_id, degradation_score) tuples
        """
        degrading = []

        for cluster_id, cluster_data in clusters.items():
            if cluster_id not in self.cluster_history:
                continue

            history = self.cluster_history[cluster_id]
            if len(history) < 2:
                continue

            # Compute trend in stability
            recent_stability = self.compute_stability_score(cluster_id, cluster_data)
            prev_stability = self._compute_centroid_stability(history, cluster_data)

            degradation = prev_stability - recent_stability

            if degradation > 0.1:  # Significant degradation
                degrading.append((cluster_id, degradation))
                logger.warning(
                    f"Cluster {cluster_id} showing degradation "
                    f"(score change: {degradation:.3f})"
                )

        return sorted(degrading, key=lambda x: x[1], reverse=True)

