"""Cluster validation with quality checks and temporal coherence."""

import logging
from datetime import datetime, timezone
from typing import List, Tuple, Dict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class ClusterValidator:
    """Validates cluster quality and temporal coherence."""

    def __init__(
        self,
        min_cluster_purity: float = 0.85,
        min_cluster_size: int = 3,
        max_cluster_size: int = 1000,
        max_time_span_hours: int = 168,
        min_sources: int = 2,
        language_consistency_threshold: float = 0.70,
        domain_consistency_threshold: float = 0.60,
    ):
        """
        Initialize cluster validator.

        Args:
            min_cluster_purity: Minimum average cosine similarity
            min_cluster_size: Minimum articles per cluster
            max_cluster_size: Maximum articles per cluster
            max_time_span_hours: Maximum time span from earliest to latest article
            min_sources: Minimum unique sources
            language_consistency_threshold: Minimum language consistency ratio
            domain_consistency_threshold: Minimum domain consistency ratio
        """
        self.min_cluster_purity = min_cluster_purity
        self.min_cluster_size = min_cluster_size
        self.max_cluster_size = max_cluster_size
        self.max_time_span_hours = max_time_span_hours
        self.min_sources = min_sources
        self.language_consistency_threshold = language_consistency_threshold
        self.domain_consistency_threshold = domain_consistency_threshold
        logger.info(
            f"Initialized ClusterValidator: purity={min_cluster_purity}, "
            f"size=[{min_cluster_size}, {max_cluster_size}]"
        )

    def validate_cluster(
        self,
        cluster_embeddings: np.ndarray,
        cluster_articles: List[dict],
        cluster_created_at: datetime,
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Validate a single cluster.

        Args:
            cluster_embeddings: Embeddings for cluster articles
            cluster_articles: Article metadata for cluster
            cluster_created_at: Cluster creation timestamp

        Returns:
            Tuple of (is_valid, validation_report)
        """
        report = {
            "valid": True,
            "issues": [],
            "metrics": {},
        }

        # Check size
        cluster_size = len(cluster_articles)
        if cluster_size < self.min_cluster_size:
            report["valid"] = False
            report["issues"].append(f"Too small: {cluster_size} articles")
        elif cluster_size > self.max_cluster_size:
            report["valid"] = False
            report["issues"].append(f"Mega-cluster: {cluster_size} articles")

        # Check purity (R7 + cluster purity)
        purity, avg_similarity, std_similarity, min_similarity = self._validate_purity(cluster_embeddings)
        report["metrics"]["similarity_avg"] = avg_similarity
        report["metrics"]["similarity_std"] = std_similarity
        report["metrics"]["similarity_min"] = min_similarity

        # Debug log to verify values
        logger.info(
            f"Similarity metrics computed: avg={avg_similarity:.4f}, "
            f"std={std_similarity:.4f}, min={min_similarity:.4f}"
        )

        if not purity:
            report["valid"] = False
            report["issues"].append(f"Low purity: {avg_similarity:.3f} < {self.min_cluster_purity}")

        # Check temporal coherence (R7)
        temporal_valid = self._validate_temporal_coherence(cluster_articles, cluster_created_at)
        if not temporal_valid:
            report["valid"] = False
            report["issues"].append("Temporal coherence violation (R7)")

        # Check time span
        time_span_valid, time_span_hours = self._validate_time_span(cluster_articles)
        report["metrics"]["time_span_hours"] = time_span_hours
        if not time_span_valid:
            report["valid"] = False
            report["issues"].append(f"Time span too large: {time_span_hours:.1f}h")

        # Check source diversity
        sources = set(a.get("source") for a in cluster_articles if a.get("source"))
        logger.info(f"Cluster articles: {len(cluster_articles)}")
        if cluster_articles:
            logger.info(f"First article fields: {list(cluster_articles[0].keys())}")
            logger.info(f"First article: {cluster_articles[0]}")
        logger.debug(f"Cluster sources: {sources}, min_sources: {self.min_sources}")
        if len(sources) < self.min_sources:
            report["valid"] = False
            report["issues"].append(f"Insufficient sources: {len(sources)} < {self.min_sources}")

        # Check language consistency
        languages = [a.get("language") for a in cluster_articles if a.get("language")]
        if languages:
            lang_consistency = max(languages.count(l) for l in set(languages)) / len(languages)
            report["metrics"]["language_consistency"] = lang_consistency
            if lang_consistency < self.language_consistency_threshold:
                report["issues"].append(
                    f"Low language consistency: {lang_consistency:.2f}"
                )

        # Check domain consistency
        domains = [a.get("domain") for a in cluster_articles if a.get("domain")]
        if domains:
            domain_consistency = max(domains.count(d) for d in set(domains)) / len(domains)
            report["metrics"]["domain_consistency"] = domain_consistency
            if domain_consistency < self.domain_consistency_threshold:
                report["issues"].append(
                    f"Low domain consistency: {domain_consistency:.2f}"
                )

        logger.info(
            f"Cluster validation: valid={report['valid']}, "
            f"size={cluster_size}, purity={avg_similarity:.3f}, "
            f"issues={len(report['issues'])}"
        )

        return report["valid"], report

    def _validate_purity(self, embeddings: np.ndarray) -> Tuple[bool, float, float, float]:
        """Validate cluster purity using cosine similarity.

        Returns:
            Tuple of (passed, avg_similarity, std_similarity, min_similarity)
        """
        if len(embeddings) < 2:
            return True, 1.0, 0.0, 1.0

        similarities = cosine_similarity(embeddings)
        np.fill_diagonal(similarities, np.nan)
        avg_similarity = np.nanmean(similarities)
        std_similarity = np.nanstd(similarities)
        min_similarity = np.nanmin(similarities)

        passed = avg_similarity >= self.min_cluster_purity
        return passed, avg_similarity, std_similarity, min_similarity

    def _validate_temporal_coherence(
        self, articles: List[dict], cluster_created_at: datetime
    ) -> bool:
        """Validate R7: cluster timestamp >= min(article timestamps)."""
        if not articles:
            return True

        published_times = []
        for a in articles:
            pub_at = a.get("published_at")
            if pub_at:
                # Parse ISO format string to datetime if needed
                if isinstance(pub_at, str):
                    try:
                        # Handle ISO format with or without timezone
                        if pub_at.endswith('Z'):
                            pub_at = pub_at[:-1] + '+00:00'
                        pub_at = datetime.fromisoformat(pub_at.replace('Z', '+00:00'))
                        # Ensure timezone-aware for comparison
                        if pub_at.tzinfo is None:
                            pub_at = pub_at.replace(tzinfo=timezone.utc)
                    except (ValueError, AttributeError):
                        logger.warning(f"Could not parse published_at: {pub_at}")
                        continue
                published_times.append(pub_at)

        if not published_times:
            return True

        earliest = min(published_times)
        # Ensure cluster_created_at is timezone-aware for comparison
        cluster_created_at_aware = cluster_created_at
        if cluster_created_at_aware.tzinfo is None:
            cluster_created_at_aware = cluster_created_at_aware.replace(tzinfo=timezone.utc)

        if cluster_created_at_aware < earliest:
            logger.error(
                f"R7 violation: cluster_created_at={cluster_created_at_aware} "
                f"< earliest_published_at={earliest}"
            )
            return False

        return True

    def _validate_time_span(self, articles: List[dict]) -> Tuple[bool, float]:
        """Validate time span from earliest to latest article."""
        published_times = []
        for a in articles:
            pub_at = a.get("published_at")
            if pub_at:
                # Parse ISO format string to datetime if needed
                if isinstance(pub_at, str):
                    try:
                        # Handle ISO format with or without timezone
                        if pub_at.endswith('Z'):
                            pub_at = pub_at[:-1] + '+00:00'
                        pub_at = datetime.fromisoformat(pub_at.replace('Z', '+00:00'))
                        # Ensure timezone-aware for comparison
                        if pub_at.tzinfo is None:
                            pub_at = pub_at.replace(tzinfo=timezone.utc)
                    except (ValueError, AttributeError):
                        logger.warning(f"Could not parse published_at: {pub_at}")
                        continue
                published_times.append(pub_at)

        if len(published_times) < 2:
            return True, 0.0

        time_span = (max(published_times) - min(published_times)).total_seconds() / 3600
        passed = time_span <= self.max_time_span_hours

        return passed, time_span

