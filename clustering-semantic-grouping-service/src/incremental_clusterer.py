"""Incremental clustering for online updates."""

import numpy as np
import logging
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class IncrementalClusterer:
    """Handle incremental clustering for online updates."""

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_cluster_age_hours: int = 168,
        merge_threshold: float = 0.90,
    ):
        """Initialize incremental clusterer.

        Args:
            similarity_threshold: Minimum similarity for cluster assignment
            max_cluster_age_hours: Maximum age of clusters before expiration
            merge_threshold: Similarity threshold for cluster merging
        """
        self.similarity_threshold = similarity_threshold
        self.max_cluster_age_hours = max_cluster_age_hours
        self.merge_threshold = merge_threshold
        self.cluster_registry: Dict[str, Dict[str, Any]] = {}
        logger.info(
            f"IncrementalClusterer initialized with "
            f"similarity_threshold={similarity_threshold}"
        )

    def assign_to_existing_clusters(
        self,
        new_embeddings: np.ndarray,
        new_metadata: List[Dict[str, Any]],
        existing_clusters: Dict[str, Dict[str, Any]],
    ) -> Tuple[np.ndarray, List[Dict[str, Any]], List[str]]:
        """Assign new embeddings to existing clusters.

        Args:
            new_embeddings: New article embeddings
            new_metadata: New article metadata
            existing_clusters: Dictionary of existing clusters

        Returns:
            Tuple of (assigned_labels, assigned_metadata, unassigned_indices)
        """
        assigned_labels = np.full(len(new_embeddings), -1, dtype=int)
        unassigned_indices = []

        for i, embedding in enumerate(new_embeddings):
            best_cluster_id = None
            best_similarity = 0

            # Find best matching cluster
            for cluster_id, cluster_data in existing_clusters.items():
                centroid = cluster_data.get("centroid")
                if centroid is None:
                    continue

                # Compute cosine similarity
                similarity = np.dot(embedding, centroid) / (
                    np.linalg.norm(embedding) * np.linalg.norm(centroid) + 1e-8
                )

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_cluster_id = cluster_id

            # Assign if similarity exceeds threshold
            if best_similarity >= self.similarity_threshold:
                assigned_labels[i] = int(best_cluster_id.split("_")[-1])
                logger.debug(
                    f"Assigned article {new_metadata[i]['article_id']} "
                    f"to cluster {best_cluster_id} (similarity={best_similarity:.4f})"
                )
            else:
                unassigned_indices.append(i)

        return assigned_labels, new_metadata, unassigned_indices

    def merge_similar_clusters(
        self,
        clusters: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """Merge similar clusters.

        Args:
            clusters: Dictionary of clusters

        Returns:
            Merged clusters dictionary
        """
        merged_clusters = {}
        merged_pairs = set()

        cluster_ids = list(clusters.keys())

        for i, cluster_id_1 in enumerate(cluster_ids):
            if cluster_id_1 in merged_pairs:
                continue

            centroid_1 = clusters[cluster_id_1].get("centroid")
            if centroid_1 is None:
                merged_clusters[cluster_id_1] = clusters[cluster_id_1]
                continue

            for cluster_id_2 in cluster_ids[i + 1 :]:
                if cluster_id_2 in merged_pairs:
                    continue

                centroid_2 = clusters[cluster_id_2].get("centroid")
                if centroid_2 is None:
                    continue

                # Compute similarity between centroids
                similarity = np.dot(centroid_1, centroid_2) / (
                    np.linalg.norm(centroid_1) * np.linalg.norm(centroid_2) + 1e-8
                )

                if similarity >= self.merge_threshold:
                    logger.info(
                        f"Merging clusters {cluster_id_1} and {cluster_id_2} "
                        f"(similarity={similarity:.4f})"
                    )

                    # Merge cluster_id_2 into cluster_id_1
                    merged_clusters[cluster_id_1] = self._merge_cluster_data(
                        clusters[cluster_id_1], clusters[cluster_id_2]
                    )
                    merged_pairs.add(cluster_id_2)
                    break

            if cluster_id_1 not in merged_pairs:
                merged_clusters[cluster_id_1] = clusters[cluster_id_1]

        return merged_clusters

    def _merge_cluster_data(
        self,
        cluster_1: Dict[str, Any],
        cluster_2: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge two cluster data dictionaries.

        Args:
            cluster_1: First cluster data
            cluster_2: Second cluster data

        Returns:
            Merged cluster data
        """
        merged = cluster_1.copy()

        # Merge article IDs
        articles_1 = set(cluster_1.get("article_ids", []))
        articles_2 = set(cluster_2.get("article_ids", []))
        merged["article_ids"] = list(articles_1 | articles_2)

        # Update centroid (weighted average)
        centroid_1 = cluster_1.get("centroid")
        centroid_2 = cluster_2.get("centroid")
        if centroid_1 is not None and centroid_2 is not None:
            n1 = len(articles_1)
            n2 = len(articles_2)
            merged["centroid"] = (
                centroid_1 * n1 + centroid_2 * n2
            ) / (n1 + n2 + 1e-8)

        # Update metadata
        merged["article_count"] = len(merged["article_ids"])
        merged["merged_at"] = datetime.now(timezone.utc).isoformat()

        return merged

    def expire_old_clusters(
        self,
        clusters: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """Remove clusters older than max_cluster_age_hours.

        Args:
            clusters: Dictionary of clusters

        Returns:
            Filtered clusters dictionary
        """
        now = datetime.now(timezone.utc)
        active_clusters = {}

        for cluster_id, cluster_data in clusters.items():
            created_at_str = cluster_data.get("created_at")
            if created_at_str is None:
                active_clusters[cluster_id] = cluster_data
                continue

            try:
                created_at = datetime.fromisoformat(created_at_str)
                age_hours = (now - created_at).total_seconds() / 3600

                if age_hours <= self.max_cluster_age_hours:
                    active_clusters[cluster_id] = cluster_data
                else:
                    logger.info(
                        f"Expiring cluster {cluster_id} (age={age_hours:.1f} hours)"
                    )
            except (ValueError, TypeError):
                active_clusters[cluster_id] = cluster_data

        return active_clusters

    def update_cluster_statistics(
        self,
        cluster_id: str,
        new_articles: List[Dict[str, Any]],
        cluster_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update cluster statistics with new articles.

        Args:
            cluster_id: Cluster identifier
            new_articles: New articles to add
            cluster_data: Current cluster data

        Returns:
            Updated cluster data
        """
        updated = cluster_data.copy()

        # Update article count
        existing_ids = set(cluster_data.get("article_ids", []))
        new_ids = {a["article_id"] for a in new_articles}
        all_ids = existing_ids | new_ids

        updated["article_ids"] = list(all_ids)
        updated["article_count"] = len(all_ids)
        updated["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Update similarity metrics
        if len(new_articles) > 0:
            updated["last_update_size"] = len(new_articles)

        return updated

    def get_cluster_statistics(
        self,
        clusters: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Get statistics about current clusters.

        Args:
            clusters: Dictionary of clusters

        Returns:
            Statistics dictionary
        """
        if not clusters:
            return {
                "total_clusters": 0,
                "total_articles": 0,
                "avg_cluster_size": 0,
                "max_cluster_size": 0,
                "min_cluster_size": 0,
            }

        sizes = [c.get("article_count", 0) for c in clusters.values()]

        return {
            "total_clusters": len(clusters),
            "total_articles": sum(sizes),
            "avg_cluster_size": np.mean(sizes) if sizes else 0,
            "max_cluster_size": max(sizes) if sizes else 0,
            "min_cluster_size": min(sizes) if sizes else 0,
        }

