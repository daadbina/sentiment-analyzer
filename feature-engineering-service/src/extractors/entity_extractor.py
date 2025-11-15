"""Entity feature extractor."""

from typing import Dict, Any, List
from collections import Counter
import math
from .base import FeatureExtractor, SemanticGroup, Article, Actor
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


class EntityExtractor(FeatureExtractor):
    """Extract entity-related features."""

    def __init__(self):
        """Initialize entity extractor."""
        super().__init__("entity_extractor")
        self.features_extracted = [
            "entity_count",
            "entity_diversity",
            "entity_prominence",
            "entity_concentration",
        ]

    async def extract(
        self,
        group: SemanticGroup,
        articles: List[Article],
        actors: List[Actor],
    ) -> Dict[str, Any]:
        """Extract entity features.

        Args:
            group: Semantic group
            articles: Articles in group
            actors: Actors mentioned in articles

        Returns:
            Dictionary of entity features
        """
        if not self.validate_inputs(group, articles, actors):
            logger.warning("Invalid inputs for entity extraction", group_id=self.get_group_id(group))
            return {}

        try:
            features = {}

            # Collect all entities from articles
            all_entities = []
            entity_types = set()
            articles_with_entities = 0

            for article in articles:
                if article.entities:
                    articles_with_entities += 1
                    for entity in article.entities:
                        all_entities.append(entity)
                        if isinstance(entity, dict):
                            # Try different field names for entity type
                            entity_type = entity.get("entity_type") or entity.get("type")
                            if entity_type:
                                entity_types.add(entity_type)

            logger.info(
                f"Entity extraction analysis: group_id={self.get_group_id(group)}, "
                f"article_count={len(articles)}, articles_with_entities={articles_with_entities}, "
                f"total_entities={len(all_entities)}, entity_types={list(entity_types)}"
            )

            if not all_entities:
                logger.info(
                    f"No entities found in {len(articles)} articles for group_id={self.get_group_id(group)} "
                    f"(articles_with_entities={articles_with_entities})"
                )
                return {
                    "entity_count": 0,
                    "entity_diversity": 0,
                    "entity_prominence": 0.0,
                    "entity_concentration": 0.0,
                }

            # entity_count: Total unique entities mentioned
            unique_entities = set()
            for entity in all_entities:
                if isinstance(entity, dict):
                    # Try different field names for entity text
                    entity_text = entity.get("name") or entity.get("text") or entity.get("normalized_text")
                    if entity_text:
                        unique_entities.add(entity_text)
                elif isinstance(entity, str):
                    unique_entities.add(entity)

            features["entity_count"] = len(unique_entities)

            # entity_diversity: Unique entity types
            features["entity_diversity"] = len(entity_types)

            # entity_prominence: Frequency of top entity
            entity_names = []
            for entity in all_entities:
                if isinstance(entity, dict):
                    # Try different field names for entity text
                    entity_text = entity.get("name") or entity.get("text") or entity.get("normalized_text")
                    if entity_text:
                        entity_names.append(entity_text)
                elif isinstance(entity, str):
                    entity_names.append(entity)

            if entity_names:
                entity_counts = Counter(entity_names)
                max_count = max(entity_counts.values())
                features["entity_prominence"] = max_count / len(entity_names)
            else:
                features["entity_prominence"] = 0.0

            # entity_concentration: Entropy of entity distribution
            if entity_names:
                entity_counts = Counter(entity_names)
                total = len(entity_names)
                entropy = 0.0
                for count in entity_counts.values():
                    if count > 0:
                        p = count / total
                        entropy -= p * math.log2(p)

                max_entropy = math.log2(len(entity_counts))
                if max_entropy > 0:
                    features["entity_concentration"] = entropy / max_entropy
                else:
                    features["entity_concentration"] = 0.0
            else:
                features["entity_concentration"] = 0.0

            logger.info(
                "Entity features extracted",
                group_id=self.get_group_id(group),
                entity_count=features["entity_count"],
            )
            return features

        except Exception as e:
            logger.error(
                "Error extracting entity features",
                group_id=self.get_group_id(group),
                error=str(e),
            )
            return {}

