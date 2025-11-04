"""Knowledge base management for NER Entity Linking Service."""

from src.knowledge_base.freshness_manager import (
    FreshnessMetadata,
    FreshnessManager,
    CacheInvalidationStrategy,
)

__all__ = [
    "FreshnessMetadata",
    "FreshnessManager",
    "CacheInvalidationStrategy",
]

