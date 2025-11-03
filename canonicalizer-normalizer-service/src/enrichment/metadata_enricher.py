"""Metadata enrichment module."""

import logging
import re
import textstat
from typing import Optional, Tuple

from src.exceptions import MetadataEnrichmentError
from src.models import MetadataEnrichmentResult

logger = logging.getLogger(__name__)

# Country code patterns
COUNTRY_PATTERNS = {
    "US": r"\b(United States|USA|America|U\.S\.)\b",
    "GB": r"\b(United Kingdom|UK|Britain|England)\b",
    "CN": r"\b(China|Chinese)\b",
    "RU": r"\b(Russia|Russian)\b",
    "IN": r"\b(India|Indian)\b",
    "BR": r"\b(Brazil|Brazilian)\b",
    "DE": r"\b(Germany|German)\b",
    "FR": r"\b(France|French)\b",
    "JP": r"\b(Japan|Japanese)\b",
    "KR": r"\b(Korea|Korean)\b",
}

# Content type patterns
CONTENT_TYPE_PATTERNS = {
    "opinion": r"\b(opinion|editorial|column|commentary)\b",
    "analysis": r"\b(analysis|analysis|explainer|deep dive)\b",
    "press_release": r"\b(press release|statement|announcement)\b",
    "interview": r"\b(interview|q&a|qa)\b",
    "breaking": r"\b(breaking|breaking news|just in)\b",
}


class MetadataEnricher:
    """Enriches article metadata."""

    def __init__(self):
        """Initialize metadata enricher."""
        pass

    def enrich(self, title: str, body: str, url: str) -> MetadataEnrichmentResult:
        """Enrich article metadata.

        Args:
            title: Article title
            body: Article body
            url: Article URL

        Returns:
            MetadataEnrichmentResult with enriched metadata
        """
        try:
            # Extract country
            country = self._extract_country(title, body)

            # Extract region (simplified)
            region = self._extract_region(url)

            # Classify content type
            content_type = self._classify_content_type(title, body)

            # Calculate readability score
            readability_score = self._calculate_readability(body)

            return MetadataEnrichmentResult(
                country=country,
                region=region,
                content_type=content_type,
                readability_score=readability_score,
            )

        except Exception as e:
            logger.error(f"Metadata enrichment failed: {e}")
            return MetadataEnrichmentResult(error=str(e))

    def _extract_country(self, title: str, body: str) -> Optional[str]:
        """Extract country from content.

        Args:
            title: Article title
            body: Article body

        Returns:
            Country code or None
        """
        try:
            combined_text = f"{title} {body}".lower()

            for country_code, pattern in COUNTRY_PATTERNS.items():
                if re.search(pattern, combined_text, re.IGNORECASE):
                    return country_code

            return None

        except Exception as e:
            logger.error(f"Country extraction failed: {e}")
            return None

    def _extract_region(self, url: str) -> Optional[str]:
        """Extract region from URL.

        Args:
            url: Article URL

        Returns:
            Region code or None
        """
        try:
            # Extract TLD and domain patterns
            if ".uk" in url or ".co.uk" in url:
                return "EU"
            elif ".de" in url or ".fr" in url or ".it" in url:
                return "EU"
            elif ".cn" in url or ".hk" in url:
                return "APAC"
            elif ".in" in url or ".jp" in url or ".kr" in url:
                return "APAC"
            elif ".br" in url or ".mx" in url:
                return "LATAM"
            elif ".ru" in url or ".ua" in url:
                return "EMEA"

            return None

        except Exception as e:
            logger.error(f"Region extraction failed: {e}")
            return None

    def _classify_content_type(self, title: str, body: str) -> str:
        """Classify content type.

        Args:
            title: Article title
            body: Article body

        Returns:
            Content type classification
        """
        try:
            combined_text = f"{title} {body}".lower()

            for content_type, pattern in CONTENT_TYPE_PATTERNS.items():
                if re.search(pattern, combined_text, re.IGNORECASE):
                    return content_type

            return "article"

        except Exception as e:
            logger.error(f"Content type classification failed: {e}")
            return "article"

    def _calculate_readability(self, body: str) -> float:
        """Calculate readability score.

        Args:
            body: Article body

        Returns:
            Flesch reading ease score (0-100)
        """
        try:
            if not body or len(body) < 100:
                return 0.0

            # Calculate Flesch reading ease
            score = textstat.flesch_reading_ease(body)

            # Normalize to 0-1 range
            normalized_score = max(0.0, min(1.0, score / 100.0))

            return normalized_score

        except Exception as e:
            logger.error(f"Readability calculation failed: {e}")
            return 0.0

