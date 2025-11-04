"""Temporal feature extractor."""

from typing import Dict, Any, List
from datetime import datetime
import math
from .base import FeatureExtractor, SemanticGroup, Article, Actor
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


class TemporalExtractor(FeatureExtractor):
    """Extract temporal-related features."""

    def __init__(self):
        """Initialize temporal extractor."""
        super().__init__("temporal_extractor")
        self.features_extracted = [
            "time_span_hours",
            "publication_velocity",
            "temporal_concentration",
            "days_since_first_article",
        ]

    def extract(
        self,
        group: SemanticGroup,
        articles: List[Article],
        actors: List[Actor],
    ) -> Dict[str, Any]:
        """Extract temporal features.

        Args:
            group: Semantic group
            articles: Articles in group
            actors: Actors (unused for temporal features)

        Returns:
            Dictionary of temporal features
        """
        if not self.validate_inputs(group, articles, actors):
            logger.warning("Invalid inputs for temporal extraction", group_id=self.get_group_id(group))
            return {}

        try:
            features = {}

            # Parse publication timestamps
            timestamps = []
            for article in articles:
                try:
                    ts = datetime.fromisoformat(article.published_at.replace("Z", "+00:00"))
                    timestamps.append(ts)
                except (ValueError, AttributeError):
                    continue

            if not timestamps:
                logger.warning(
                    "No valid timestamps found", group_id=self.get_group_id(group)
                )
                return {
                    "time_span_hours": 0.0,
                    "publication_velocity": 0.0,
                    "temporal_concentration": 0.0,
                    "days_since_first_article": 0.0,
                }

            timestamps.sort()
            earliest = timestamps[0]
            latest = timestamps[-1]

            # time_span_hours: Duration from earliest to latest article
            time_span = (latest - earliest).total_seconds() / 3600
            features["time_span_hours"] = max(0.0, time_span)

            # publication_velocity: Articles per hour
            if features["time_span_hours"] > 0:
                features["publication_velocity"] = len(articles) / features["time_span_hours"]
            else:
                features["publication_velocity"] = float(len(articles))

            # temporal_concentration: Ratio of articles in peak hour
            if len(articles) > 0:
                # Count articles per hour
                hour_counts = {}
                for ts in timestamps:
                    hour_key = ts.replace(minute=0, second=0, microsecond=0)
                    hour_counts[hour_key] = hour_counts.get(hour_key, 0) + 1

                max_hour_count = max(hour_counts.values()) if hour_counts else 0
                features["temporal_concentration"] = max_hour_count / len(articles)
            else:
                features["temporal_concentration"] = 0.0

            # days_since_first_article: Days elapsed since first publication
            now = datetime.utcnow()
            days_elapsed = (now - earliest).total_seconds() / (24 * 3600)
            features["days_since_first_article"] = max(0.0, days_elapsed)

            logger.info(
                "Temporal features extracted",
                group_id=self.get_group_id(group),
                time_span_hours=features["time_span_hours"],
            )
            return features

        except Exception as e:
            logger.error(
                "Error extracting temporal features",
                group_id=self.get_group_id(group),
                error=str(e),
            )
            return {}

