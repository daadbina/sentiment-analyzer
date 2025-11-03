"""Source verification stage."""

import logging
from src.pipeline.stage import ValidationStage
from src.models import ValidationContext
from src.repositories.source_registry import SourceRegistryRepository

logger = logging.getLogger(__name__)


class SourceVerificationStage(ValidationStage):
    """Verifies source reliability (R6)."""

    def __init__(self, source_registry: SourceRegistryRepository):
        """Initialize source verification stage.

        Args:
            source_registry: Source registry repository
        """
        super().__init__("SourceVerification")
        self.source_registry = source_registry

    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute source verification.

        Args:
            context: Validation context

        Returns:
            Updated validation context
        """
        try:
            source_id = context.raw_message.source

            # Verify source
            is_verified = await self.source_registry.verify_source(source_id)

            if not is_verified:
                self._add_warning(context, f"Source {source_id} not verified")
                context.validation_details.source_verified = False
                return context

            # Get publisher ID
            publisher_id = await self.source_registry.get_publisher_id(source_id)
            context.publisher_id = publisher_id

            context.validation_details.source_verified = True
            logger.debug(f"[{self.name}] Source {source_id} verified")

            return context

        except Exception as e:
            logger.error(f"[{self.name}] Verification error: {e}")
            self._add_warning(context, f"Source verification error: {e}")
            context.validation_details.source_verified = False
            return context
