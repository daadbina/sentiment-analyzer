"""Base extractor class for feature extraction."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class SemanticGroup:
    """Semantic group data structure."""

    group_id: str
    article_ids: List[str]
    centroid_vector: List[float]
    similarity_avg: float
    topic_label: str
    metadata: Dict[str, Any]
    created_at: str


@dataclass
class Article:
    """Article data structure."""

    article_id: str
    title: str
    body: str
    language: str
    domain: str
    source: str
    published_at: str
    sentiment_score: float
    entities: List[Dict[str, Any]]
    publisher_credibility: float = None


@dataclass
class Actor:
    """Actor (entity) data structure."""

    actor_id: str
    name: str
    type: str
    country: str
    sentiment_avg: float
    occurrences: int
    wikidata_id: str


class FeatureExtractor(ABC):
    """Abstract base class for feature extractors."""

    def __init__(self, name: str):
        """Initialize extractor.

        Args:
            name: Extractor name
        """
        self.name = name
        self.features_extracted: List[str] = []

    @abstractmethod
    def extract(
        self,
        group: SemanticGroup,
        articles: List[Article],
        actors: List[Actor],
    ) -> Dict[str, Any]:
        """Extract features from semantic group.

        Args:
            group: Semantic group
            articles: Articles in group
            actors: Actors mentioned in articles

        Returns:
            Dictionary of feature_name -> value
        """
        pass

    def validate_inputs(
        self,
        group: SemanticGroup,
        articles: List[Article],
        actors: List[Actor],
    ) -> bool:
        """Validate input data.

        Args:
            group: Semantic group
            articles: Articles in group
            actors: Actors mentioned in articles

        Returns:
            True if inputs are valid
        """
        # Handle both dict and object types
        if not group:
            return False

        group_id = group.get("group_id") if isinstance(group, dict) else getattr(group, "group_id", None)
        if not group_id:
            return False

        if not articles or len(articles) == 0:
            return False
        return True

    def get_group_id(self, group: Any) -> str:
        """Safely get group_id from dict or object.

        Args:
            group: Semantic group (dict or object)

        Returns:
            Group ID string
        """
        if isinstance(group, dict):
            return group.get("group_id", "")
        return getattr(group, "group_id", "")

    def get_feature_names(self) -> List[str]:
        """Get list of feature names produced by this extractor.

        Returns:
            List of feature names
        """
        return self.features_extracted

