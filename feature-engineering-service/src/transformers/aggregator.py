"""Feature aggregator transformer."""

from typing import Dict, Any, List
from .base import FeatureTransformer
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


class FeatureAggregator(FeatureTransformer):
    """Aggregate features from multiple extractors."""

    def __init__(self):
        """Initialize aggregator."""
        super().__init__("feature_aggregator")

    def transform(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate features.

        Args:
            features: Dictionary of feature_name -> value

        Returns:
            Dictionary with aggregated features
        """
        if not self.validate_inputs(features):
            logger.warning("Invalid inputs for aggregation")
            return {}

        try:
            aggregated = {}

            # Copy all features
            aggregated.update(features)

            # Compute aggregate statistics
            numeric_features = {
                k: v for k, v in features.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            }

            if numeric_features:
                values = list(numeric_features.values())

                # Add aggregate statistics
                aggregated["feature_count"] = len(numeric_features)
                aggregated["feature_sum"] = sum(values)
                aggregated["feature_mean"] = sum(values) / len(values)
                aggregated["feature_min"] = min(values)
                aggregated["feature_max"] = max(values)

                # Compute range
                aggregated["feature_range"] = aggregated["feature_max"] - aggregated["feature_min"]

            logger.info(
                "Features aggregated",
                feature_count=len(aggregated),
            )
            return aggregated

        except Exception as e:
            logger.error("Error aggregating features", error=str(e))
            return features

