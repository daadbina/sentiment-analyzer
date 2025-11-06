"""HuggingFace-based NER strategy using transformers library."""

import logging
from typing import List, Tuple, Optional

from transformers import pipeline
from src.ner.base_strategy import NERStrategy
from src.exceptions import NERExtractionError

logger = logging.getLogger(__name__)


class HuggingFaceNERStrategy(NERStrategy):
    """NER strategy using HuggingFace transformers for real entity extraction."""

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
        "B-PER": "PERSON",
        "I-PER": "PERSON",
        "B-ORG": "ORGANIZATION",
        "I-ORG": "ORGANIZATION",
        "B-LOC": "LOCATION",
        "I-LOC": "LOCATION",
        "B-GPE": "GPE",
        "I-GPE": "GPE",
        "B-DATE": "DATE",
        "I-DATE": "DATE",
        "B-MONEY": "CURRENCY",
        "I-MONEY": "CURRENCY",
    }

    def __init__(self, language: str, model_name: str):
        """
        Initialize HuggingFace NER strategy.

        Args:
            language: Language code (e.g., 'en', 'fa', 'ru', 'zh')
            model_name: HuggingFace model name (e.g., 'dslim/bert-base-uncased-finetuned-ner')
        """
        self.language = language
        self.model_name = model_name
        self.nlp: Optional[object] = None

    def load_model(self) -> None:
        """Load the HuggingFace NER model using transformers pipeline."""
        try:
            logger.info(f"Loading HuggingFace model: {self.model_name}")
            # Load real NER pipeline from transformers using PyTorch backend
            self.nlp = pipeline(
                "ner",
                model=self.model_name,
                aggregation_strategy="simple",
                framework="pt"  # Use PyTorch backend to avoid TensorFlow/Keras issues
            )
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
        Extract entities using HuggingFace transformers NER pipeline.

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

            # Use transformers pipeline for real NER
            ner_results = self.nlp(text)

            logger.debug(f"HuggingFace pipeline returned {len(ner_results)} raw entities")

            # Process results and convert to canonical format
            for result in ner_results:
                entity_text = result.get("word", "").strip()
                if not entity_text:
                    continue

                entity_label = result.get("entity_group", result.get("entity", ""))
                start_char = result.get("start", 0)
                end_char = result.get("end", len(entity_text))
                confidence = result.get("score", 0.0)

                # Map to canonical entity type
                canonical_type = self.ENTITY_TYPE_MAPPING.get(entity_label, "PERSON")

                # Skip unknown entity types that don't map to canonical types
                if canonical_type not in ["PERSON", "ORGANIZATION", "LOCATION", "GPE", "DATE", "CURRENCY", "EVENT"]:
                    logger.debug(f"Skipping unknown entity type: {entity_label} -> {canonical_type}")
                    continue

                entities.append(
                    (entity_text, canonical_type, start_char, end_char, confidence)
                )

            logger.debug(f"Extracted {len(entities)} entities from text using {self.model_name}")
            return entities

        except Exception as e:
            logger.error(f"Error extracting entities with HuggingFace: {e}")
            raise NERExtractionError(f"HuggingFace extraction failed: {e}", self.language)

