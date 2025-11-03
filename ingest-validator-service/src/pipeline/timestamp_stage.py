"""Timestamp validation stage."""

import logging
from src.pipeline.stage import ValidationStage
from src.models import ValidationContext
from src.validation.timestamp import TimestampValidator

logger = logging.getLogger(__name__)


class TimestampValidationStage(ValidationStage):
    """Validates and normalizes timestamps (R1)."""

    def __init__(self):
        """Initialize timestamp validation stage."""
        super().__init__("TimestampValidation")

    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute timestamp validation.

        Args:
            context: Validation context

        Returns:
            Updated validation context
        """
        try:
            # Validate and normalize published_at
            is_valid, normalized_utc, error = TimestampValidator.validate_and_normalize(
                context.raw_message.published_at,
                context.raw_message.crawled_at,
            )

            if not is_valid:
                self._add_error(context, f"Timestamp validation failed: {error}")
                context.validation_details.timestamp_valid = False
                return context

            if error:  # Warning message
                self._add_warning(context, error)

            context.source_published_at_utc = normalized_utc
            context.validation_details.timestamp_valid = True

            logger.debug(
                f"[{self.name}] Timestamp validation passed for {context.article_id}"
            )

            return context

        except Exception as e:
            logger.error(f"[{self.name}] Validation error: {e}")
            self._add_error(context, f"Timestamp validation error: {e}")
            context.validation_details.timestamp_valid = False
            return context
