"""spaCy-based NER strategy (placeholder - uses HuggingFace)."""

import logging
from typing import List, Tuple, Optional

from src.ner.base_strategy import NERStrategy
from src.exceptions import NERExtractionError

logger = logging.getLogger(__name__)


class SpacyNERStrategy(NERStrategy):
    """NER strategy using spaCy models (placeholder for HuggingFace)."""

    # Mapping of entity labels to canonical types
    ENTITY_TYPE_MAPPING = {
        "PERSON": "PERSON",
        "PER": "PERSON",
        "ORG": "ORGANIZATION",
        "ORGANIZATION": "ORGANIZATION",
        "GPE": "GPE",
        "LOC": "LOCATION",
        "LOCATION": "LOCATION",
        "MONEY": "CURRENCY",
        "CURRENCY": "CURRENCY",
        "DATE": "DATE",
        "EVENT": "EVENT",
    }

    def __init__(self, language: str, model_name: str):
        """
        Initialize spaCy NER strategy.

        Args:
            language: Language code (e.g., 'en', 'de', 'fr')
            model_name: Model name (not used, for compatibility)
        """
        self.language = language
        self.model_name = model_name
        self.nlp: Optional[object] = None

    def load_model(self) -> None:
        """Load the model (placeholder)."""
        logger.info(f"SpacyNERStrategy is a placeholder. Use HuggingFaceNERStrategy instead.")

    def unload_model(self) -> None:
        """Unload the model."""
        if self.nlp is not None:
            self.nlp = None
            logger.info(f"Unloaded model: {self.model_name}")

    def is_available(self) -> bool:
        """Check if model is loaded."""
        return False

    def get_language(self) -> str:
        """Get language code."""
        return self.language

    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_name

    def extract_entities(self, text: str) -> List[Tuple[str, str, int, int, float]]:
        """
        Extract entities (placeholder).

        Args:
            text: Input text

        Returns:
            Empty list (use HuggingFaceNERStrategy instead)
        """
        logger.warning("SpacyNERStrategy is a placeholder. Use HuggingFaceNERStrategy instead.")
        return []

