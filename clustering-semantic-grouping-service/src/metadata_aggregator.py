"""Metadata aggregation for clusters."""

import logging
from typing import List, Dict
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class MetadataAggregator:
    """Aggregates article metadata for clusters."""

    @staticmethod
    def aggregate_cluster_metadata(articles: List[dict]) -> dict:
        """
        Aggregate article metadata for cluster.

        Args:
            articles: List of article metadata dictionaries

        Returns:
            Aggregated metadata dictionary
        """
        if not articles:
            raise ValueError("Empty articles list")

        logger.debug(f"Aggregating metadata for {len(articles)} articles")

        # Extract fields
        article_ids = [a.get("article_id") for a in articles]
        languages = list(set(a.get("language") for a in articles if a.get("language")))
        domains = list(set(a.get("domain") for a in articles if a.get("domain")))
        sources = list(set(a.get("source") for a in articles if a.get("source")))
        countries = list(
            set(a.get("country") for a in articles if a.get("country"))
        )

        # Compute credibility average
        credibilities = [
            a.get("publisher_credibility", 0.5)
            for a in articles
            if a.get("publisher_credibility")
        ]
        credibility_avg = np.mean(credibilities) if credibilities else 0.5

        # Get time span
        published_times = [
            a.get("published_at") for a in articles if a.get("published_at")
        ]
        if published_times:
            earliest = min(published_times)
            latest = max(published_times)
            time_span_hours = (latest - earliest).total_seconds() / 3600
        else:
            earliest = None
            latest = None
            time_span_hours = 0.0

        metadata = {
            "article_ids": article_ids,
            "article_count": len(articles),
            "languages": languages,
            "domains": domains,
            "sources": sources,
            "countries": countries,
            "publisher_credibility_avg": float(credibility_avg),
            "earliest_published_at": earliest.isoformat() if earliest else "",
            "latest_published_at": latest.isoformat() if latest else "",
            "time_span_hours": float(time_span_hours),
        }

        logger.debug(
            f"Aggregated metadata: {len(article_ids)} articles, "
            f"{len(languages)} languages, {len(sources)} sources"
        )

        return metadata

    @staticmethod
    def compute_cluster_statistics(
        articles: List[dict],
        similarities: np.ndarray,
    ) -> dict:
        """
        Compute statistical metrics for cluster.

        Args:
            articles: List of article metadata
            similarities: Pairwise similarity matrix

        Returns:
            Dictionary of statistics
        """
        stats = {
            "article_count": len(articles),
            "similarity_avg": float(np.mean(similarities)),
            "similarity_min": float(np.min(similarities)),
            "similarity_max": float(np.max(similarities)),
            "similarity_std": float(np.std(similarities)),
            "similarity_median": float(np.median(similarities)),
        }

        # Language distribution
        languages = [a.get("language") for a in articles if a.get("language")]
        if languages:
            lang_counts = {}
            for lang in languages:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            stats["language_distribution"] = lang_counts

        # Domain distribution
        domains = [a.get("domain") for a in articles if a.get("domain")]
        if domains:
            domain_counts = {}
            for domain in domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            stats["domain_distribution"] = domain_counts

        # Source distribution
        sources = [a.get("source") for a in articles if a.get("source")]
        if sources:
            stats["source_count"] = len(set(sources))
            stats["sources"] = list(set(sources))

        return stats

    @staticmethod
    def get_cluster_summary(
        cluster_id: str,
        articles: List[dict],
        centroid: np.ndarray,
        similarities: np.ndarray,
        topic_label: str,
    ) -> dict:
        """
        Get comprehensive cluster summary.

        Args:
            cluster_id: Cluster identifier
            articles: List of article metadata
            centroid: Centroid vector
            similarities: Pairwise similarity matrix
            topic_label: Topic label for cluster

        Returns:
            Comprehensive cluster summary
        """
        metadata = MetadataAggregator.aggregate_cluster_metadata(articles)
        stats = MetadataAggregator.compute_cluster_statistics(articles, similarities)

        summary = {
            "group_id": cluster_id,
            **metadata,
            **stats,
            "topic_label": topic_label,
            "centroid_vector": centroid.tolist(),
            "created_at": datetime.utcnow().isoformat(),
        }

        return summary

