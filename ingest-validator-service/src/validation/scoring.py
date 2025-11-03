"""Validation score calculation."""

import logging
from typing import Tuple, Optional
from src.models import ValidationContext

logger = logging.getLogger(__name__)


class ValidationScorer:
    """Calculates validation scores using weighted formula."""

    # Weights for VS formula: VS = 0.15*L + 0.15*S + 0.15*E + 0.15*T + 0.15*G + 0.25*C
    WEIGHTS = {
        "language": 0.15,  # L - Language detection
        "source": 0.15,  # S - Source reliability
        "encoding": 0.15,  # E - Encoding integrity
        "timestamp": 0.15,  # T - Timestamp accuracy
        "geographic": 0.15,  # G - Geographic relevance
        "content": 0.25,  # C - Content quality
    }

    # Decision thresholds
    ACCEPT_THRESHOLD = 0.85
    REPROCESS_THRESHOLD = 0.70

    @staticmethod
    def calculate_language_score(
        language_detected: bool,
        language_confidence: float = 0.0,
    ) -> float:
        """Calculate language component score.

        Args:
            language_detected: Whether language was detected
            language_confidence: Detection confidence (0.0-1.0)

        Returns:
            Language score (0.0-1.0)
        """
        if not language_detected:
            return 0.0

        # Use confidence as score if detected
        return min(1.0, language_confidence)

    @staticmethod
    def calculate_source_score(
        source_verified: bool, credibility: float = 1.0
    ) -> float:
        """Calculate source component score.

        Args:
            source_verified: Whether source is verified
            credibility: Source credibility score (0.0-1.0)

        Returns:
            Source score (0.0-1.0)
        """
        if not source_verified:
            return 0.0

        return min(1.0, credibility)

    @staticmethod
    def calculate_encoding_score(encoding_valid: bool) -> float:
        """Calculate encoding component score.

        Args:
            encoding_valid: Whether encoding is valid

        Returns:
            Encoding score (0.0-1.0)
        """
        return 1.0 if encoding_valid else 0.0

    @staticmethod
    def calculate_timestamp_score(timestamp_valid: bool) -> float:
        """Calculate timestamp component score.

        Args:
            timestamp_valid: Whether timestamp is valid

        Returns:
            Timestamp score (0.0-1.0)
        """
        return 1.0 if timestamp_valid else 0.0

    @staticmethod
    def calculate_geographic_score(country: Optional[str] = None) -> float:
        """Calculate geographic component score.

        Args:
            country: Country code if extracted

        Returns:
            Geographic score (0.0-1.0)
        """
        if country:
            return 1.0  # Country extracted
        return 0.5  # Uncertain

    @staticmethod
    def calculate_content_score(quality_score: float = 0.0) -> float:
        """Calculate content component score.

        Args:
            quality_score: Content quality score (0.0-1.0)

        Returns:
            Content score (0.0-1.0)
        """
        return min(1.0, quality_score)

    @staticmethod
    def calculate_validation_score(
        language_score: float,
        source_score: float,
        encoding_score: float,
        timestamp_score: float,
        geographic_score: float,
        content_score: float,
    ) -> float:
        """Calculate overall validation score using weighted formula.

        VS = 0.15*L + 0.15*S + 0.15*E + 0.15*T + 0.15*G + 0.25*C

        Args:
            language_score: Language component (0.0-1.0)
            source_score: Source component (0.0-1.0)
            encoding_score: Encoding component (0.0-1.0)
            timestamp_score: Timestamp component (0.0-1.0)
            geographic_score: Geographic component (0.0-1.0)
            content_score: Content component (0.0-1.0)

        Returns:
            Overall validation score (0.0-1.0)
        """
        vs = (
            ValidationScorer.WEIGHTS["language"] * language_score
            + ValidationScorer.WEIGHTS["source"] * source_score
            + ValidationScorer.WEIGHTS["encoding"] * encoding_score
            + ValidationScorer.WEIGHTS["timestamp"] * timestamp_score
            + ValidationScorer.WEIGHTS["geographic"] * geographic_score
            + ValidationScorer.WEIGHTS["content"] * content_score
        )

        return min(1.0, max(0.0, vs))

    @staticmethod
    def decide_routing(validation_score: float) -> str:
        """Decide where to route article based on score.

        Args:
            validation_score: Overall validation score

        Returns:
            Routing decision: "accept", "reprocess", or "reject"
        """
        if validation_score >= ValidationScorer.ACCEPT_THRESHOLD:
            return "accept"
        elif validation_score >= ValidationScorer.REPROCESS_THRESHOLD:
            return "reprocess"
        else:
            return "reject"

    @staticmethod
    def score_from_context(context: ValidationContext) -> Tuple[float, str]:
        """Calculate validation score from context.

        Args:
            context: Validation context

        Returns:
            Tuple of (validation_score, routing_decision)
        """
        # Calculate component scores
        language_score = ValidationScorer.calculate_language_score(
            context.validation_details.language_detected,
            context.language_confidence or 0.0,
        )

        source_score = ValidationScorer.calculate_source_score(
            context.validation_details.source_verified,
            1.0,  # Default credibility
        )

        encoding_score = ValidationScorer.calculate_encoding_score(
            context.validation_details.encoding_valid,
        )

        timestamp_score = ValidationScorer.calculate_timestamp_score(
            context.validation_details.timestamp_valid,
        )

        geographic_score = ValidationScorer.calculate_geographic_score(context.country)

        # Use actual quality score from context (no hardcoded fallback)
        content_score = ValidationScorer.calculate_content_score(
            context.quality_score or 0.0
        )

        # Calculate overall score
        vs = ValidationScorer.calculate_validation_score(
            language_score,
            source_score,
            encoding_score,
            timestamp_score,
            geographic_score,
            content_score,
        )

        # Decide routing
        routing = ValidationScorer.decide_routing(vs)

        return vs, routing
