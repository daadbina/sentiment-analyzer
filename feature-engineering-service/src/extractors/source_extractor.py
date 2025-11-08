"""Source feature extractor."""

from typing import Dict, Any, List
from collections import Counter
import math
from .base import FeatureExtractor, SemanticGroup, Article, Actor
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


class SourceExtractor(FeatureExtractor):
    """Extract source-related features."""

    def __init__(self):
        """Initialize source extractor."""
        super().__init__("source_extractor")
        self.features_extracted = [
            "num_sources",
            "source_credibility_avg",
            "source_credibility_std",
            "source_diversity_score",
        ]

    def extract(
        self,
        group: SemanticGroup,
        articles: List[Article],
        actors: List[Actor],
    ) -> Dict[str, Any]:
        """Extract source features.

        Args:
            group: Semantic group
            articles: Articles in group
            actors: Actors (unused for source features)

        Returns:
            Dictionary of source features
        """
        if not self.validate_inputs(group, articles, actors):
            logger.warning("Invalid inputs for source extraction", group_id=self.get_group_id(group))
            return {}

        try:
            features = {}

            # Extract unique sources
            sources = [article.source for article in articles if article.source]
            unique_sources = list(set(sources))

            # num_sources: Count of unique news sources
            features["num_sources"] = len(unique_sources)

            # source_credibility_avg: Average publisher credibility
            # Extract credibility scores from articles (if available)
            # If not available, use a default credibility value
            credibility_scores = []
            for article in articles:
                # Try to get credibility from article metadata
                if hasattr(article, 'credibility_score') and article.credibility_score is not None:
                    credibility_scores.append(article.credibility_score)
                elif hasattr(article, 'publisher_credibility') and article.publisher_credibility is not None:
                    credibility_scores.append(article.publisher_credibility)
                else:
                    # Default credibility value if not available
                    # This ensures we have a value for all articles
                    credibility_scores.append(0.5)

            if credibility_scores:
                features["source_credibility_avg"] = sum(credibility_scores) / len(
                    credibility_scores
                )
            else:
                features["source_credibility_avg"] = 0.5

            # source_credibility_std: Standard deviation of credibility
            if len(credibility_scores) > 1:
                mean = features["source_credibility_avg"]
                variance = sum((x - mean) ** 2 for x in credibility_scores) / len(
                    credibility_scores
                )
                features["source_credibility_std"] = math.sqrt(variance)
            else:
                features["source_credibility_std"] = 0.0

            # source_diversity_score: Entropy of source distribution
            if unique_sources and len(unique_sources) > 1:
                source_counts = Counter(sources)
                total = len(sources)
                entropy = 0.0
                for count in source_counts.values():
                    if count > 0:
                        p = count / total
                        entropy -= p * math.log2(p)
                features["source_diversity_score"] = entropy / math.log2(
                    len(unique_sources)
                )
            else:
                features["source_diversity_score"] = 0.0

            logger.info(
                "Source features extracted",
                group_id=self.get_group_id(group),
                num_sources=features["num_sources"],
            )
            return features

        except Exception as e:
            logger.error(
                "Error extracting source features",
                group_id=self.get_group_id(group),
                error=str(e),
            )
            return {}

