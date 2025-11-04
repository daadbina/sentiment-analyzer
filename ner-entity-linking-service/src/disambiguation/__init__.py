"""Entity disambiguation for NER Entity Linking Service."""

from src.disambiguation.entity_disambiguator import (
    DisambiguationCandidate,
    EntityDisambiguator,
    AmbiguityDetector,
    ContextualDisambiguator,
)

__all__ = [
    "DisambiguationCandidate",
    "EntityDisambiguator",
    "AmbiguityDetector",
    "ContextualDisambiguator",
]

