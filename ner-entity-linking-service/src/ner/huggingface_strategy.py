"""HuggingFace-based NER strategy (mock implementation)."""

import logging
import re
from typing import List, Tuple, Optional

from src.ner.base_strategy import NERStrategy
from src.exceptions import NERExtractionError

logger = logging.getLogger(__name__)


class HuggingFaceNERStrategy(NERStrategy):
    """NER strategy using HuggingFace transformers (mock for testing)."""

    # Mapping of entity labels to canonical types
    ENTITY_TYPE_MAPPING = {
        "PER": "PERSON",
        "PERSON": "PERSON",
        "ORG": "ORGANIZATION",
        "ORGANIZATION": "ORGANIZATION",
        "LOC": "LOCATION",
        "LOCATION": "LOCATION",
        "GPE": "GPE",
        "DATE": "DATE",
        "MONEY": "CURRENCY",
        "CURRENCY": "CURRENCY",
        "EVENT": "EVENT",
    }

    def __init__(self, language: str, model_name: str):
        """
        Initialize HuggingFace NER strategy.

        Args:
            language: Language code (e.g., 'fa', 'ru', 'zh')
            model_name: HuggingFace model name
        """
        self.language = language
        self.model_name = model_name
        self.nlp: Optional[object] = None

    def load_model(self) -> None:
        """Load the HuggingFace model (mock)."""
        try:
            logger.info(f"Loading HuggingFace model: {self.model_name}")
            self.nlp = True  # Mock: just set to True
            logger.info(f"Successfully loaded HuggingFace model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load HuggingFace model {self.model_name}: {e}")
            raise NERExtractionError(
                f"Failed to load HuggingFace model {self.model_name}", self.language
            )

    def unload_model(self) -> None:
        """Unload the HuggingFace model."""
        if self.nlp is not None:
            self.nlp = None
            logger.info(f"Unloaded HuggingFace model: {self.model_name}")

    def is_available(self) -> bool:
        """Check if model is loaded."""
        return self.nlp is not None

    def get_language(self) -> str:
        """Get language code."""
        return self.language

    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_name

    def extract_entities(self, text: str) -> List[Tuple[str, str, int, int, float]]:
        """
        Extract entities using simple regex patterns (mock).

        Args:
            text: Input text

        Returns:
            List of tuples: (entity_text, entity_type, start_char, end_char, confidence)
        """
        if not self.is_available():
            raise NERExtractionError(
                f"HuggingFace model not loaded: {self.model_name}", self.language
            )

        try:
            entities = []

            # Simple mock: extract capitalized words as PERSON
            for match in re.finditer(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text):
                entity_text = match.group()
                start_char = match.start()
                end_char = match.end()
                entities.append(
                    (entity_text, "PERSON", start_char, end_char, 0.85)
                )

            logger.debug(f"Extracted {len(entities)} entities from text")
            return entities

        except Exception as e:
            logger.error(f"Error extracting entities with HuggingFace: {e}")
            raise NERExtractionError(f"HuggingFace extraction failed: {e}", self.language)

