"""Domain classification module."""

import logging
import re
from typing import Tuple

from src.exceptions import DomainClassificationError
from src.models import DomainClassificationResult

logger = logging.getLogger(__name__)

# Domain category keywords
DOMAIN_KEYWORDS = {
    "politics": [
        "election", "vote", "parliament", "congress", "senate", "minister",
        "government", "political", "campaign", "candidate", "policy",
    ],
    "economy": [
        "market", "stock", "trade", "economy", "business", "finance",
        "investment", "profit", "revenue", "earnings", "gdp",
    ],
    "technology": [
        "tech", "software", "hardware", "ai", "algorithm", "data",
        "digital", "cyber", "internet", "app", "startup",
    ],
    "conflict": [
        "war", "conflict", "military", "attack", "bomb", "soldier",
        "battle", "combat", "armed", "violence", "terrorist",
    ],
    "health": [
        "health", "medical", "disease", "virus", "vaccine", "hospital",
        "doctor", "patient", "treatment", "pandemic", "covid",
    ],
    "environment": [
        "climate", "environment", "pollution", "carbon", "green",
        "renewable", "energy", "sustainability", "weather", "disaster",
    ],
    "sports": [
        "sport", "game", "team", "player", "match", "championship",
        "league", "coach", "score", "win", "tournament",
    ],
    "entertainment": [
        "movie", "film", "music", "actor", "celebrity", "entertainment",
        "show", "concert", "award", "hollywood", "artist",
    ],
}


class DomainClassifier:
    """Classifies articles into domain categories."""

    def __init__(self):
        """Initialize domain classifier."""
        self.domain_keywords = DOMAIN_KEYWORDS

    def classify(self, title: str, body: str) -> DomainClassificationResult:
        """Classify article domain.

        Args:
            title: Article title
            body: Article body

        Returns:
            DomainClassificationResult with classification
        """
        try:
            # Combine title and body for classification
            combined_text = f"{title} {body}".lower()

            # Score each domain
            domain_scores = {}
            for domain, keywords in self.domain_keywords.items():
                score = self._calculate_domain_score(combined_text, keywords)
                domain_scores[domain] = score

            # Find best match
            best_domain = max(domain_scores, key=domain_scores.get)
            best_score = domain_scores[best_domain]

            # Use general if confidence is too low
            if best_score < 0.1:
                best_domain = "general"
                best_score = 0.0

            return DomainClassificationResult(
                domain_category=best_domain,
                confidence=min(1.0, best_score),
            )

        except Exception as e:
            logger.error(f"Domain classification failed: {e}")
            return DomainClassificationResult(error=str(e))

    def _calculate_domain_score(self, text: str, keywords: list) -> float:
        """Calculate domain score based on keyword matches.

        Args:
            text: Text to analyze
            keywords: List of keywords for domain

        Returns:
            Score between 0 and 1
        """
        if not text or not keywords:
            return 0.0

        matches = 0
        for keyword in keywords:
            # Count keyword occurrences
            pattern = r"\b" + re.escape(keyword) + r"\b"
            matches += len(re.findall(pattern, text, re.IGNORECASE))

        # Normalize score
        max_possible_matches = len(keywords) * 3  # Assume max 3 matches per keyword
        score = min(1.0, matches / max_possible_matches)

        return score

