"""Content feature extractor."""

from typing import Dict, Any, List
from .base import FeatureExtractor, SemanticGroup, Article, Actor
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


class ContentExtractor(FeatureExtractor):
    """Extract content-related features."""

    def __init__(self):
        """Initialize content extractor."""
        super().__init__("content_extractor")
        self.features_extracted = [
            "avg_word_count",
            "avg_title_length",
            "language_diversity",
            "domain_diversity",
        ]

    async def extract(
        self,
        group: SemanticGroup,
        articles: List[Article],
        actors: List[Actor],
    ) -> Dict[str, Any]:
        """Extract content features.

        Args:
            group: Semantic group
            articles: Articles in group
            actors: Actors (unused for content features)

        Returns:
            Dictionary of content features
        """
        if not self.validate_inputs(group, articles, actors):
            logger.warning("Invalid inputs for content extraction", group_id=self.get_group_id(group))
            return {}

        try:
            features = {}

            # avg_word_count: Average article length
            word_counts = []
            for article in articles:
                if article.body:
                    word_count = len(article.body.split())
                    word_counts.append(word_count)

            if word_counts:
                features["avg_word_count"] = sum(word_counts) / len(word_counts)
            else:
                features["avg_word_count"] = 0.0

            # avg_title_length: Average title length
            title_lengths = []
            for article in articles:
                if article.title:
                    title_length = len(article.title.split())
                    title_lengths.append(title_length)

            if title_lengths:
                features["avg_title_length"] = sum(title_lengths) / len(title_lengths)
            else:
                features["avg_title_length"] = 0.0

            # language_diversity: Number of languages in group
            languages = set()
            for article in articles:
                if article.language:
                    languages.add(article.language)

            features["language_diversity"] = len(languages)

            # domain_diversity: Number of content domains
            domains = set()
            for article in articles:
                if article.domain:
                    domains.add(article.domain)

            features["domain_diversity"] = len(domains)

            logger.info(
                "Content features extracted",
                group_id=self.get_group_id(group),
                avg_word_count=features["avg_word_count"],
            )
            return features

        except Exception as e:
            logger.error(
                "Error extracting content features",
                group_id=self.get_group_id(group),
                error=str(e),
            )
            return {}

