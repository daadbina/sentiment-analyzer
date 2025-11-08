"""Sentiment feature extractor."""

from typing import Dict, Any, List
import math
from .base import FeatureExtractor, SemanticGroup, Article, Actor
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


class SentimentExtractor(FeatureExtractor):
    """Extract sentiment-related features."""

    def __init__(self):
        """Initialize sentiment extractor."""
        super().__init__("sentiment_extractor")
        self.features_extracted = [
            "sentiment_mean",
            "sentiment_std",
            "sentiment_polarity_ratio",
            "sentiment_volatility",
        ]

    def extract(
        self,
        group: SemanticGroup,
        articles: List[Article],
        actors: List[Actor],
    ) -> Dict[str, Any]:
        """Extract sentiment features.

        Args:
            group: Semantic group
            articles: Articles in group
            actors: Actors (unused for sentiment features)

        Returns:
            Dictionary of sentiment features
        """
        if not self.validate_inputs(group, articles, actors):
            logger.warning("Invalid inputs for sentiment extraction", group_id=self.get_group_id(group))
            return {}

        try:
            features = {}

            # Extract sentiment scores
            sentiment_scores = [
                article.sentiment_score
                for article in articles
                if article.sentiment_score is not None
            ]

            logger.info(
                f"Sentiment scores extracted: group_id={self.get_group_id(group)}, "
                f"article_count={len(articles)}, sentiment_count={len(sentiment_scores)}, "
                f"scores_sample={sentiment_scores[:5] if sentiment_scores else []}"
            )

            if not sentiment_scores:
                logger.warning(
                    f"No sentiment scores found in {len(articles)} articles for group_id={self.get_group_id(group)}"
                )
                return {
                    "sentiment_mean": 0.0,
                    "sentiment_std": 0.0,
                    "sentiment_polarity_ratio": 0.0,
                    "sentiment_volatility": 0.0,
                }

            # sentiment_mean: Average sentiment score
            features["sentiment_mean"] = sum(sentiment_scores) / len(sentiment_scores)

            # sentiment_std: Standard deviation of sentiment
            if len(sentiment_scores) > 1:
                mean = features["sentiment_mean"]
                variance = sum((x - mean) ** 2 for x in sentiment_scores) / len(
                    sentiment_scores
                )
                features["sentiment_std"] = math.sqrt(variance)
            else:
                features["sentiment_std"] = 0.0

            # sentiment_polarity_ratio: Positive vs negative articles ratio
            positive_count = sum(1 for s in sentiment_scores if s > 0)
            negative_count = sum(1 for s in sentiment_scores if s < 0)
            total_count = len(sentiment_scores)

            if negative_count > 0:
                features["sentiment_polarity_ratio"] = positive_count / negative_count
            elif positive_count > 0:
                features["sentiment_polarity_ratio"] = float(positive_count)
            else:
                features["sentiment_polarity_ratio"] = 0.0

            # sentiment_volatility: Change in sentiment over time
            if len(sentiment_scores) > 1:
                # Calculate differences between consecutive scores
                diffs = [
                    abs(sentiment_scores[i] - sentiment_scores[i - 1])
                    for i in range(1, len(sentiment_scores))
                ]
                features["sentiment_volatility"] = sum(diffs) / len(diffs)
            else:
                features["sentiment_volatility"] = 0.0

            logger.info(
                "Sentiment features extracted",
                group_id=self.get_group_id(group),
                sentiment_mean=features["sentiment_mean"],
            )
            return features

        except Exception as e:
            logger.error(
                "Error extracting sentiment features",
                group_id=self.get_group_id(group),
                error=str(e),
            )
            return {}

