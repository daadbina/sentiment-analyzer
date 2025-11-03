"""Schema validation stage."""

import logging
from src.pipeline.stage import ValidationStage
from src.models import ValidationContext

logger = logging.getLogger(__name__)


class SchemaValidationStage(ValidationStage):
    """Validates message schema (R12)."""

    def __init__(self):
        """Initialize schema validation stage."""
        super().__init__("SchemaValidation")

    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute schema validation.

        Args:
            context: Validation context

        Returns:
            Updated validation context
        """
        try:
            # Validate required fields (matching NewsRaw model)
            required_fields = [
                "article_id",
                "title",
                "body",
                "url",
                "published_at",
                "language",
                "source",
                "ingest_job_id",
                "validation_score",
                "crawled_at",
                "checksum",
            ]

            raw_msg = context.raw_message
            missing_fields = []

            for field in required_fields:
                if not hasattr(raw_msg, field) or getattr(raw_msg, field) is None:
                    missing_fields.append(field)

            if missing_fields:
                self._add_error(
                    context, f"Missing required fields: {', '.join(missing_fields)}"
                )
                context.validation_details.schema_valid = False
                return context

            # Validate field types
            if not isinstance(raw_msg.title, str) or not raw_msg.title.strip():
                self._add_error(context, "Title must be non-empty string")
                context.validation_details.schema_valid = False
                return context

            if not isinstance(raw_msg.body, str) or not raw_msg.body.strip():
                self._add_error(context, "Body must be non-empty string")
                context.validation_details.schema_valid = False
                return context

            if not isinstance(raw_msg.url, str) or not raw_msg.url.strip():
                self._add_error(context, "URL must be non-empty string")
                context.validation_details.schema_valid = False
                return context

            if not isinstance(raw_msg.source, str) or not raw_msg.source.strip():
                self._add_error(context, "Source must be non-empty string")
                context.validation_details.schema_valid = False
                return context

            # Extract and store normalized values
            context.title = raw_msg.title.strip()
            context.body = raw_msg.body.strip()
            context.url = raw_msg.url.strip()
            context.source = raw_msg.source.strip()
            context.checksum = raw_msg.checksum

            context.validation_details.schema_valid = True
            logger.debug(
                f"[{self.name}] Schema validation passed for {context.article_id}"
            )

            return context

        except Exception as e:
            logger.error(f"[{self.name}] Validation error: {e}")
            self._add_error(context, f"Schema validation error: {e}")
            context.validation_details.schema_valid = False
            return context
