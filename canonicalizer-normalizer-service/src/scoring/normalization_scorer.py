"""Normalization scoring module."""

import logging
from typing import Optional

from src.models import NormalizationDetails

logger = logging.getLogger(__name__)


class NormalizationScorer:
    """Calculates normalization quality score."""

    # Scoring weights
    WEIGHTS = {
        "url": 0.20,
        "publisher": 0.20,
        "content": 0.25,
        "metadata": 0.15,
        "domain": 0.10,
        "fuzzy": 0.10,
    }

    def __init__(self):
        """Initialize normalization scorer."""
        pass

    def calculate_score(
        self,
        url_canonicalized: bool,
        publisher_credibility: float,
        content_cleaned: bool,
        metadata_enriched: bool,
        domain_classified: bool,
        fuzzy_dedup_checked: bool,
        word_count: int = 0,
        readability_score: float = 0.0,
    ) -> float:
        """Calculate normalization quality score.

        Args:
            url_canonicalized: Whether URL was canonicalized
            publisher_credibility: Publisher credibility score (0-1)
            content_cleaned: Whether content was cleaned
            metadata_enriched: Whether metadata was enriched
            domain_classified: Whether domain was classified
            fuzzy_dedup_checked: Whether fuzzy dedup was checked
            word_count: Word count of content
            readability_score: Readability score (0-1)

        Returns:
            Normalization score (0-1)
        """
        try:
            # Component scores
            url_score = 1.0 if url_canonicalized else 0.0
            publisher_score = publisher_credibility
            content_score = self._calculate_content_score(content_cleaned, word_count)
            metadata_score = self._calculate_metadata_score(metadata_enriched, readability_score)
            domain_score = 1.0 if domain_classified else 0.0
            fuzzy_score = 1.0 if fuzzy_dedup_checked else 0.0

            # Weighted sum
            total_score = (
                self.WEIGHTS["url"] * url_score
                + self.WEIGHTS["publisher"] * publisher_score
                + self.WEIGHTS["content"] * content_score
                + self.WEIGHTS["metadata"] * metadata_score
                + self.WEIGHTS["domain"] * domain_score
                + self.WEIGHTS["fuzzy"] * fuzzy_score
            )

            # Normalize to 0-1 range
            return min(1.0, max(0.0, total_score))

        except Exception as e:
            logger.error(f"Score calculation failed: {e}")
            return 0.0

    def _calculate_content_score(self, content_cleaned: bool, word_count: int) -> float:
        """Calculate content quality score.

        Args:
            content_cleaned: Whether content was cleaned
            word_count: Word count

        Returns:
            Content score (0-1)
        """
        if not content_cleaned:
            return 0.0

        # Bonus for adequate content length
        if word_count >= 100:
            return 1.0
        elif word_count >= 50:
            return 0.8
        elif word_count >= 20:
            return 0.5
        else:
            return 0.2

    def _calculate_metadata_score(self, metadata_enriched: bool, readability_score: float) -> float:
        """Calculate metadata quality score.

        Args:
            metadata_enriched: Whether metadata was enriched
            readability_score: Readability score (0-1)

        Returns:
            Metadata score (0-1)
        """
        if not metadata_enriched:
            return 0.0

        # Combine enrichment and readability
        return (readability_score + 1.0) / 2.0

    def get_decision(self, score: float, accept_threshold: float = 0.85, review_threshold: float = 0.70) -> str:
        """Get publishing decision based on score.

        Args:
            score: Normalization score
            accept_threshold: Score threshold for acceptance
            review_threshold: Score threshold for review

        Returns:
            Decision: "accept", "review", or "reject"
        """
        if score >= accept_threshold:
            return "accept"
        elif score >= review_threshold:
            return "review"
        else:
            return "reject"

