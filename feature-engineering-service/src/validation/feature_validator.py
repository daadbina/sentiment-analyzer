"""Feature validator for quality checks."""

from typing import Dict, Any, List, Tuple
import math
from ..utils import StructuredLogger
from ..exceptions import ValidationError

logger = StructuredLogger(__name__)


class FeatureValidator:
    """Validate feature quality and correctness."""

    def __init__(self):
        """Initialize validator."""
        self.validation_rules: List[str] = []
        self.failed_validations: List[str] = []

    def validate(self, features: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate features.

        Args:
            features: Dictionary of feature_name -> value

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        self.failed_validations = []

        if not features:
            self.failed_validations.append("Features dictionary is empty")
            return False, self.failed_validations

        # Check for NaN and Inf values
        for key, value in features.items():
            if isinstance(value, float):
                if math.isnan(value):
                    self.failed_validations.append(f"Feature {key} is NaN")
                elif math.isinf(value):
                    self.failed_validations.append(f"Feature {key} is Inf")

        # Check for negative counts
        count_features = [k for k in features.keys() if "count" in k.lower()]
        for key in count_features:
            if isinstance(features[key], (int, float)) and features[key] < 0:
                self.failed_validations.append(f"Count feature {key} is negative: {features[key]}")

        # Check for out-of-range values
        range_checks = {
            "sentiment_mean": (-1.0, 1.0),
            "sentiment_std": (0.0, 1.0),
            "sentiment_polarity_ratio": (0.0, float("inf")),
            "source_credibility_avg": (0.0, 1.0),
            "source_credibility_std": (0.0, 1.0),
            "source_diversity_score": (0.0, 1.0),
            "entity_concentration": (0.0, 1.0),
            "intra_cluster_similarity_mean": (0.0, 1.0),
            "intra_cluster_similarity_std": (0.0, 1.0),
        }

        for key, (min_val, max_val) in range_checks.items():
            if key in features:
                value = features[key]
                if isinstance(value, (int, float)):
                    if value < min_val or (max_val != float("inf") and value > max_val):
                        self.failed_validations.append(
                            f"Feature {key} out of range [{min_val}, {max_val}]: {value}"
                        )

        is_valid = len(self.failed_validations) == 0
        logger.info(
            "Feature validation completed",
            is_valid=is_valid,
            error_count=len(self.failed_validations),
        )
        return is_valid, self.failed_validations

    def get_failed_validations(self) -> List[str]:
        """Get list of failed validations.

        Returns:
            List of validation error messages
        """
        return self.failed_validations

