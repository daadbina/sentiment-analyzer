"""Feature Engineering Service - Phase 3 of sentiment-analyzer-v2."""

__version__ = "0.1.0"
__author__ = "Feature Engineering Service Team"
__description__ = "Compute features for ML models from semantic groups"

from .config import config
from .exceptions import FeatureError

__all__ = ["config", "FeatureError", "__version__"]

