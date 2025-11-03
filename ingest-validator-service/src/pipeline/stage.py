"""Base validation stage."""

import logging
from abc import ABC, abstractmethod
from src.models import ValidationContext

logger = logging.getLogger(__name__)


class ValidationStage(ABC):
    """Base class for validation stages."""

    def __init__(self, name: str):
        """Initialize stage.

        Args:
            name: Stage name
        """
        self.name = name

    @abstractmethod
    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute validation stage.

        Args:
            context: Validation context

        Returns:
            Updated validation context
        """
        pass

    def _add_error(self, context: ValidationContext, error: str) -> None:
        """Add error to context.

        Args:
            context: Validation context
            error: Error message
        """
        if error not in context.errors:
            context.errors.append(error)
            logger.debug(f"[{self.name}] Error: {error}")

    def _add_warning(self, context: ValidationContext, warning: str) -> None:
        """Add warning to context.

        Args:
            context: Validation context
            warning: Warning message
        """
        if warning not in context.warnings:
            context.warnings.append(warning)
            logger.debug(f"[{self.name}] Warning: {warning}")
