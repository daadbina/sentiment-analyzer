"""Validation scoring stage."""

import logging
from src.pipeline.stage import ValidationStage
from src.models import ValidationContext
from src.validation.scoring import ValidationScorer

logger = logging.getLogger(__name__)


class ValidationScoringStage(ValidationStage):
    """Calculates overall validation score."""

    def __init__(self):
        """Initialize validation scoring stage."""
        super().__init__("ValidationScoring")

    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute validation scoring.

        Args:
            context: Validation context

        Returns:
            Updated validation context
        """
        try:
            # Calculate component scores
            language_score = ValidationScorer.calculate_language_score(
                context.validation_details.language_detected,
                context.language_confidence or 0.0,
            )

            source_score = ValidationScorer.calculate_source_score(
                context.validation_details.source_verified,
                1.0,
            )

            encoding_score = ValidationScorer.calculate_encoding_score(
                context.validation_details.encoding_valid,
            )

            timestamp_score = ValidationScorer.calculate_timestamp_score(
                context.validation_details.timestamp_valid,
            )

            geographic_score = ValidationScorer.calculate_geographic_score(
                context.country,
            )

            # Use actual quality score from quality stage (no hardcoded fallback)
            content_score = ValidationScorer.calculate_content_score(
                context.quality_score or 0.0,
            )

            # Calculate overall score
            validation_score = ValidationScorer.calculate_validation_score(
                language_score,
                source_score,
                encoding_score,
                timestamp_score,
                geographic_score,
                content_score,
            )

            context.validation_score = validation_score

            # Log detailed scoring breakdown
            logger.info(
                f"[{self.name}] Validation score {validation_score:.2f} "
                f"for {context.article_id} - "
                f"L={language_score:.2f}, S={source_score:.2f}, E={encoding_score:.2f}, "
                f"T={timestamp_score:.2f}, G={geographic_score:.2f}, C={content_score:.2f}"
            )

            return context

        except Exception as e:
            logger.error(f"[{self.name}] Scoring error: {e}")
            self._add_error(context, f"Validation scoring error: {e}")
            context.validation_score = 0.0
            return context
