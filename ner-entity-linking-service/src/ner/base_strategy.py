"""Base NER strategy interface."""

from abc import ABC, abstractmethod
from typing import List, Tuple
from src.models import Entity


class NERStrategy(ABC):
    """Abstract base class for NER strategies."""

    @abstractmethod
    def extract_entities(self, text: str) -> List[Tuple[str, str, int, int, float]]:
        """
        Extract entities from text.

        Args:
            text: Input text to extract entities from

        Returns:
            List of tuples: (entity_text, entity_type, start_char, end_char, confidence)
        """
        pass

    @abstractmethod
    def get_language(self) -> str:
        """Get language code for this strategy."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get model name for this strategy."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if model is available and loaded."""
        pass

    @abstractmethod
    def load_model(self) -> None:
        """Load the NER model."""
        pass

    @abstractmethod
    def unload_model(self) -> None:
        """Unload the NER model to free memory."""
        pass

