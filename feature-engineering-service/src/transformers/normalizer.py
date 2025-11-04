"""Feature normalizer transformer."""

from typing import Dict, Any
import math
from .base import FeatureTransformer
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


class FeatureNormalizer(FeatureTransformer):
    """Normalize features to standard ranges."""

    def __init__(self):
        """Initialize normalizer."""
        super().__init__("feature_normalizer")
        # Define normalization ranges for known features
        self.feature_ranges = {
            "sentiment_mean": (-1.0, 1.0),
            "sentiment_std": (0.0, 1.0),
            "sentiment_polarity_ratio": (0.0, float("inf")),
            "sentiment_volatility": (0.0, 1.0),
            "source_credibility_avg": (0.0, 1.0),
            "source_credibility_std": (0.0, 1.0),
            "source_diversity_score": (0.0, 1.0),
            "entity_concentration": (0.0, 1.0),
            "intra_cluster_similarity_mean": (0.0, 1.0),
            "intra_cluster_similarity_std": (0.0, 1.0),
        }

    def transform(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize features.

        Args:
            features: Dictionary of feature_name -> value

        Returns:
            Dictionary with normalized features
        """
        if not self.validate_inputs(features):
            logger.warning("Invalid inputs for normalization")
            return {}

        try:
            normalized = {}

            for key, value in features.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    # Normalize to [0, 1] range if possible
                    if key in self.feature_ranges:
                        min_val, max_val = self.feature_ranges[key]
                        if max_val != float("inf"):
                            # Min-max normalization
                            if max_val > min_val:
                                normalized[key] = (value - min_val) / (max_val - min_val)
                                # Clamp to [0, 1]
                                normalized[key] = max(0.0, min(1.0, normalized[key]))
                            else:
                                normalized[key] = 0.0
                        else:
                            # For unbounded features, use log normalization
                            if value > 0:
                                normalized[key] = math.log1p(value) / 10.0
                                normalized[key] = min(1.0, normalized[key])
                            else:
                                normalized[key] = 0.0
                    else:
                        # For unknown features, use z-score normalization (assume mean=0, std=1)
                        normalized[key] = value
                else:
                    # Keep non-numeric features as-is
                    normalized[key] = value

            logger.info(
                "Features normalized",
                feature_count=len(normalized),
            )
            return normalized

        except Exception as e:
            logger.error("Error normalizing features", error=str(e))
            return features

