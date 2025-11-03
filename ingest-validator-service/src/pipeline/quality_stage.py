"""Content quality scoring stage."""

import logging
from src.pipeline.stage import ValidationStage
from src.models import ValidationContext
from src.validation.quality import QualityScorer

logger = logging.getLogger(__name__)


class QualityScoringStage(ValidationStage):
    """Scores content quality."""

    def __init__(self):
        """Initialize quality scoring stage."""
        super().__init__("QualityScoring")

    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute quality scoring.

        Args:
            context: Validation context

        Returns:
            Updated validation context
        """
        try:
            # Score content
            quality_score, issues = QualityScorer.score_content(
                context.title or "",
                context.body or "",
                context.url or "",
                context.language or "en",
            )

            # Add issues as warnings
            for issue in issues:
                self._add_warning(context, issue)

            # Store actual quality score (no fallback)
            context.quality_score = quality_score

            # Determine if content quality is acceptable
            # Quality score >= 0.7 is acceptable
            context.validation_details.content_quality_ok = quality_score >= 0.7

            # Log detailed quality scoring info
            logger.info(
                f"[{self.name}] Quality score {quality_score:.2f} "
                f"for {context.article_id} - Issues: {issues}"
            )
            logger.info(
                f"[{self.name}] Content: title_len={len(context.title or '')}, "
                f"body_len={len(context.body or '')}, "
                f"word_count={QualityScorer.count_words(context.body or '')}, "
                f"language={context.language}"
            )

            return context

        except Exception as e:
            logger.error(f"[{self.name}] Scoring error: {e}")
            self._add_error(context, f"Quality scoring error: {e}")
            # Set quality score to 0.0 on error (no fallback to True)
            context.quality_score = 0.0
            context.validation_details.content_quality_ok = False
            return context
