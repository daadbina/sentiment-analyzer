"""NER orchestrator for coordinating extraction pipeline."""

import logging
import time
import uuid
from typing import List
from src.ner.model_registry import NERModelRegistry
from src.models import Entity, EntityType, NERResult
from src.exceptions import UnsupportedLanguageError, NERExtractionError
from src.metrics import MetricsCollector

logger = logging.getLogger(__name__)


class NEROrchestrator:
    """Orchestrates NER extraction pipeline."""

    def __init__(self, model_registry: NERModelRegistry):
        """
        Initialize NER orchestrator.

        Args:
            model_registry: Registry of NER models
        """
        self.model_registry = model_registry

    def extract_entities(
        self, text: str, language: str, article_id: str
    ) -> NERResult:
        """
        Extract entities from text.

        Args:
            text: Article text
            language: Language code
            article_id: Article identifier for tracing

        Returns:
            NERResult with extracted entities

        Raises:
            UnsupportedLanguageError: If language not supported
            NERExtractionError: If extraction fails
        """
        start_time = time.time()

        try:
            # Validate language
            if not self.model_registry.is_language_supported(language):
                raise UnsupportedLanguageError(language)

            # Get appropriate NER model
            strategy = self.model_registry.get_model(language)

            # Extract raw entities
            raw_entities = strategy.extract_entities(text)

            # Convert to Entity objects
            entities = []
            for entity_text, entity_type, start_char, end_char, confidence in raw_entities:
                entity = Entity(
                    entity_id=str(uuid.uuid4()),
                    text=entity_text,
                    normalized_text=entity_text.lower(),
                    entity_type=EntityType(entity_type),
                    start_char=start_char,
                    end_char=end_char,
                    confidence=confidence,
                    context_snippet=self._extract_context(text, start_char, end_char),
                )
                entities.append(entity)

            # Calculate coverage score
            coverage_score = self._calculate_coverage(len(entities), len(text), language)

            # Record metrics
            duration_seconds = time.time() - start_time
            MetricsCollector.record_extraction_latency(duration_seconds)
            MetricsCollector.set_coverage_score(coverage_score)
            MetricsCollector.record_entities_extracted(len(entities))

            logger.info(
                f"Extracted {len(entities)} entities from article {article_id} "
                f"in {duration_seconds:.2f}s (language={language})"
            )

            return NERResult(
                entities=entities,
                coverage_score=coverage_score,
                linking_success_rate=0.0,  # Will be updated after linking
                extraction_duration_ms=duration_seconds * 1000,
                model_used=strategy.get_model_name(),
                language=language,
            )

        except UnsupportedLanguageError:
            raise
        except Exception as e:
            logger.error(f"Error extracting entities from article {article_id}: {e}")
            raise NERExtractionError(f"Entity extraction failed: {e}", language)

    def _extract_context(self, text: str, start_char: int, end_char: int, window: int = 50) -> str:
        """
        Extract context window around entity.

        Args:
            text: Full text
            start_char: Entity start position
            end_char: Entity end position
            window: Context window size

        Returns:
            Context snippet
        """
        context_start = max(0, start_char - window)
        context_end = min(len(text), end_char + window)
        return text[context_start:context_end].strip()

    def _calculate_coverage(self, entity_count: int, text_length: int, language: str) -> float:
        """
        Calculate entity coverage score.

        Args:
            entity_count: Number of entities extracted
            text_length: Length of text in characters
            language: Language code

        Returns:
            Coverage score (0.0-1.0)
        """
        if text_length == 0:
            return 0.0

        # Expected entity density: 2-5 entities per 100 words
        # Approximate: 5 characters per word
        expected_words = text_length / 5
        expected_entities = expected_words * 0.035  # 3.5% entity density

        if expected_entities == 0:
            return 1.0 if entity_count == 0 else 0.5

        coverage = min(1.0, entity_count / expected_entities)
        return coverage

    def shutdown(self) -> None:
        """Shutdown orchestrator and unload models."""
        logger.info("Shutting down NER orchestrator")
        self.model_registry.unload_all()

