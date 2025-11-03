"""Geographic extraction stage."""

import logging
from src.pipeline.stage import ValidationStage
from src.models import ValidationContext
from src.validation.geographic import GeographicExtractor

logger = logging.getLogger(__name__)


class GeographicExtractionStage(ValidationStage):
    """Extracts geographic location from article content (R6 - Geographic component)."""

    def __init__(self):
        """Initialize geographic extraction stage."""
        super().__init__("GeographicExtraction")

    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute geographic extraction.

        Args:
            context: Validation context

        Returns:
            Updated validation context
        """
        try:
            # Extract country from content
            country = GeographicExtractor.extract_country(
                title=context.title or "",
                body=context.body or "",
                url=context.url or "",
                existing_country=context.country,
            )

            if country:
                context.country = country
                logger.debug(
                    f"[{self.name}] Extracted country {country} for article {context.article_id}"
                )
            else:
                logger.debug(
                    f"[{self.name}] No country extracted for article {context.article_id}"
                )

            return context

        except Exception as e:
            logger.error(f"[{self.name}] Geographic extraction error: {e}")
            # Geographic extraction is not critical, so we don't add error
            # Just log and continue
            return context

