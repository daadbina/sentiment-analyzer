"""Entity linking orchestrator."""

import logging
import time
from typing import Optional, Dict
from src.linking.wikidata_client import WikidataClient
from src.models import Entity
from src.metrics import MetricsCollector

logger = logging.getLogger(__name__)

# Common words that are unlikely to be real entities
COMMON_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
    "from", "up", "about", "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "can",
    "just", "should", "now", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "ought", "i", "you", "he", "she",
    "it", "we", "they", "what", "which", "who", "whom", "this", "that", "these", "those",
}


class EntityLinker:
    """Orchestrates entity linking to knowledge bases."""

    def __init__(
        self,
        wikidata_client: WikidataClient,
        confidence_threshold: float = 0.75,
    ):
        """
        Initialize entity linker.

        Args:
            wikidata_client: Wikidata client instance
            confidence_threshold: Minimum confidence for linking
        """
        self.wikidata_client = wikidata_client
        self.confidence_threshold = confidence_threshold

    def _should_skip_entity(self, entity: Entity) -> bool:
        """
        Check if entity should be skipped from linking.

        Args:
            entity: Entity to check

        Returns:
            True if entity should be skipped, False otherwise
        """
        # Skip common words
        if entity.text.lower() in COMMON_WORDS:
            logger.debug(f"Skipping common word: '{entity.text}'")
            return True

        # Skip very short entities (likely noise)
        if len(entity.text) < 2:
            logger.debug(f"Skipping short entity: '{entity.text}'")
            return True

        return False

    def link_entity(self, entity: Entity) -> Entity:
        """
        Link entity to knowledge bases.

        Args:
            entity: Entity to link

        Returns:
            Entity with linking information
        """
        start_time = time.time()

        try:
            logger.debug(f"Linking entity: text='{entity.text}', normalized='{entity.normalized_text}', type='{entity.entity_type}'")

            # Skip common words and short entities
            if self._should_skip_entity(entity):
                logger.debug(f"Skipped entity: '{entity.text}'")
                return entity

            # Try Wikidata linking using original entity text (not normalized)
            # Normalized text (lowercase, no diacritics) won't match Wikidata labels
            wikidata_result = self.wikidata_client.search_entity(
                entity.text, entity.entity_type
            )

            if wikidata_result:
                entity.wikidata_id = wikidata_result.get("wikidata_id")
                entity.country = wikidata_result.get("country")
                MetricsCollector.record_entities_linked(1)
                logger.info(f"✓ Linked entity '{entity.text}' → Wikidata: {entity.wikidata_id} (label: {wikidata_result.get('label')})")
            else:
                logger.debug(f"✗ Could not link entity '{entity.text}' (normalized: '{entity.normalized_text}') to Wikidata")

            # Record linking duration
            duration_seconds = time.time() - start_time
            MetricsCollector.record_linking_latency(duration_seconds)

            return entity

        except Exception as e:
            logger.error(f"Error linking entity {entity.text}: {e}")
            MetricsCollector.record_linking_error("linking_error")
            return entity

    def link_entities(self, entities: list) -> tuple:
        """
        Link multiple entities.

        Args:
            entities: List of entities to link

        Returns:
            Tuple of (linked_entities, linking_success_rate)
        """
        linked_entities = []
        linked_count = 0

        for entity in entities:
            linked_entity = self.link_entity(entity)
            linked_entities.append(linked_entity)

            if linked_entity.wikidata_id:
                linked_count += 1

        success_rate = linked_count / len(entities) if entities else 0.0
        MetricsCollector.set_linking_success_rate(success_rate)

        logger.info(
            f"Linked {linked_count}/{len(entities)} entities "
            f"(success rate: {success_rate:.2%})"
        )

        return linked_entities, success_rate

