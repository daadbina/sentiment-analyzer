"""Encoding validation stage."""

import logging
from src.pipeline.stage import ValidationStage
from src.models import ValidationContext
from src.validation.encoding import EncodingValidator

logger = logging.getLogger(__name__)


class EncodingValidationStage(ValidationStage):
    """Validates text encoding (R9)."""

    def __init__(self):
        """Initialize encoding validation stage."""
        super().__init__("EncodingValidation")

    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute encoding validation.

        Args:
            context: Validation context

        Returns:
            Updated validation context
        """
        try:
            logger.debug(f"[{self.name}] Starting encoding validation for {context.article_id}")
            logger.debug(f"[{self.name}] context.title={context.title}, context.body={context.body}")

            # Validate title encoding
            if context.title:
                title_bytes = context.title.encode("utf-8", errors="replace")
                is_valid, sanitized, encoding, error = (
                    EncodingValidator.validate_and_sanitize(
                        title_bytes,
                        None,
                    )
                )

                if not is_valid:
                    self._add_error(context, f"Title encoding error: {error}")
                    context.validation_details.encoding_valid = False
                    return context

                context.title = sanitized

            # Validate body encoding
            if context.body:
                body_bytes = context.body.encode("utf-8", errors="replace")
                is_valid, sanitized, encoding, error = (
                    EncodingValidator.validate_and_sanitize(
                        body_bytes,
                        context.checksum,
                    )
                )

                if not is_valid:
                    self._add_error(context, f"Body encoding error: {error}")
                    context.validation_details.encoding_valid = False
                    return context

                context.body = sanitized

            # Recalculate checksum after sanitization
            combined_text = f"{context.title}|{context.body}"
            context.checksum = EncodingValidator.calculate_checksum(combined_text)

            context.validation_details.encoding_valid = True
            logger.debug(
                f"[{self.name}] Encoding validation passed for {context.article_id}"
            )

            return context

        except Exception as e:
            logger.error(f"[{self.name}] Validation error: {e}")
            self._add_error(context, f"Encoding validation error: {e}")
            context.validation_details.encoding_valid = False
            return context
