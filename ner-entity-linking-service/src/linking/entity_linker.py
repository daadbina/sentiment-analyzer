"""Entity linking orchestrator."""

import logging
import time
from typing import Optional, Dict
from src.linking.wikidata_client import WikidataClient
from src.models import Entity
from src.metrics import MetricsCollector

logger = logging.getLogger(__name__)


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
            # Try Wikidata linking
            wikidata_result = self.wikidata_client.search_entity(
                entity.normalized_text, entity.entity_type
            )

            if wikidata_result:
                entity.wikidata_id = wikidata_result.get("wikidata_id")
                entity.country = wikidata_result.get("country")
                MetricsCollector.record_entities_linked(1)
                logger.debug(f"Linked entity {entity.text} to Wikidata: {entity.wikidata_id}")
            else:
                logger.debug(f"Could not link entity {entity.text} to Wikidata")

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

