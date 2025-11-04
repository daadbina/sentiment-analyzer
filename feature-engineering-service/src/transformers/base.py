"""Base transformer class for feature transformation."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class FeatureTransformer(ABC):
    """Abstract base class for feature transformers."""

    def __init__(self, name: str):
        """Initialize transformer.

        Args:
            name: Transformer name
        """
        self.name = name

    @abstractmethod
    def transform(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Transform features.

        Args:
            features: Dictionary of feature_name -> value

        Returns:
            Dictionary of transformed features
        """
        pass

    def validate_inputs(self, features: Dict[str, Any]) -> bool:
        """Validate input features.

        Args:
            features: Dictionary of features

        Returns:
            True if inputs are valid
        """
        return features is not None and isinstance(features, dict)

