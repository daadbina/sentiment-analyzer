"""Entity disambiguation and ambiguity resolution."""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DisambiguationCandidate:
    """Candidate for entity disambiguation."""

    entity_id: str
    label: str
    description: str
    score: float
    source: str  # wikidata, dbpedia, opensanctions
    context_relevance: float = 0.0


class EntityDisambiguator:
    """Resolves ambiguous entity references."""

    # Minimum score for disambiguation
    MIN_DISAMBIGUATION_SCORE = 0.4

    # Context keywords for disambiguation
    CONTEXT_KEYWORDS = {
        "PERSON": ["said", "told", "announced", "declared", "stated", "born", "died"],
        "ORGANIZATION": ["company", "organization", "founded", "headquarters", "ceo"],
        "LOCATION": ["city", "country", "region", "located", "situated", "capital"],
        "GPE": ["government", "president", "minister", "parliament", "congress"],
    }

    @staticmethod
    def disambiguate(
        entity_text: str,
        entity_type: str,
        context: str,
        candidates: List[DisambiguationCandidate],
    ) -> Optional[DisambiguationCandidate]:
        """Disambiguate entity using context.

        Args:
            entity_text: Entity text
            entity_type: Entity type
            context: Context snippet
            candidates: List of disambiguation candidates

        Returns:
            Best matching candidate or None
        """
        if not candidates:
            logger.warning(f"No candidates for disambiguation of {entity_text}")
            return None

        if len(candidates) == 1:
            logger.debug(f"Single candidate for {entity_text}, no disambiguation needed")
            return candidates[0]

        # Score candidates based on context
        scored_candidates = []
        for candidate in candidates:
            score = EntityDisambiguator._score_candidate(
                candidate, entity_type, context
            )
            scored_candidates.append((candidate, score))

        # Sort by score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        best_candidate, best_score = scored_candidates[0]

        if best_score >= EntityDisambiguator.MIN_DISAMBIGUATION_SCORE:
            logger.info(
                f"Disambiguated {entity_text} to {best_candidate.label} "
                f"with score {best_score:.2f}"
            )
            return best_candidate
        else:
            logger.warning(
                f"Could not disambiguate {entity_text} with confidence "
                f"(best score: {best_score:.2f})"
            )
            return None

    @staticmethod
    def _score_candidate(
        candidate: DisambiguationCandidate,
        entity_type: str,
        context: str,
    ) -> float:
        """Score a disambiguation candidate.

        Args:
            candidate: Candidate to score
            entity_type: Entity type
            context: Context snippet

        Returns:
            Score (0-1)
        """
        score = candidate.score  # Base score from linking

        # Add context relevance
        context_score = EntityDisambiguator._calculate_context_relevance(
            candidate, entity_type, context
        )
        score = (score + context_score) / 2

        return min(score, 1.0)

    @staticmethod
    def _calculate_context_relevance(
        candidate: DisambiguationCandidate,
        entity_type: str,
        context: str,
    ) -> float:
        """Calculate context relevance score.

        Args:
            candidate: Candidate
            entity_type: Entity type
            context: Context snippet

        Returns:
            Relevance score (0-1)
        """
        if not context:
            return 0.5  # Default to neutral score

        context_lower = context.lower()
        description_lower = candidate.description.lower()
        keywords = EntityDisambiguator.CONTEXT_KEYWORDS.get(entity_type, [])

        # Count keyword matches in context
        context_matches = sum(1 for keyword in keywords if keyword in context_lower)

        # Check if description keywords appear in context
        description_matches = sum(
            1 for word in description_lower.split() if word in context_lower
        )

        # Combine scores
        keyword_score = (context_matches / len(keywords)) if keywords else 0.0
        description_score = min(description_matches / 3.0, 1.0)  # Normalize to 0-1

        # Average the scores
        return (keyword_score + description_score) / 2.0

    @staticmethod
    def resolve_ambiguity(
        entity_text: str,
        entity_type: str,
        context: str,
        candidates: List[Dict],
    ) -> Optional[Dict]:
        """Resolve entity ambiguity.

        Args:
            entity_text: Entity text
            entity_type: Entity type
            context: Context snippet
            candidates: List of candidate dictionaries

        Returns:
            Best matching candidate or None
        """
        # Convert to DisambiguationCandidate objects
        candidate_objects = [
            DisambiguationCandidate(
                entity_id=c.get("entity_id", ""),
                label=c.get("label", ""),
                description=c.get("description", ""),
                score=c.get("score", 0.0),
                source=c.get("source", "unknown"),
                context_relevance=c.get("context_relevance", 0.0),
            )
            for c in candidates
        ]

        # Disambiguate
        best_candidate = EntityDisambiguator.disambiguate(
            entity_text, entity_type, context, candidate_objects
        )

        if best_candidate:
            return {
                "entity_id": best_candidate.entity_id,
                "label": best_candidate.label,
                "description": best_candidate.description,
                "score": best_candidate.score,
                "source": best_candidate.source,
            }
        return None


class AmbiguityDetector:
    """Detects ambiguous entity references."""

    # Threshold for ambiguity
    AMBIGUITY_THRESHOLD = 0.1  # Score difference between top candidates

    @staticmethod
    def is_ambiguous(candidates: List[DisambiguationCandidate]) -> bool:
        """Check if entity reference is ambiguous.

        Args:
            candidates: List of candidates

        Returns:
            True if ambiguous
        """
        if len(candidates) < 2:
            return False

        # Sort by score
        sorted_candidates = sorted(candidates, key=lambda x: x.score, reverse=True)

        # Check score difference
        score_diff = sorted_candidates[0].score - sorted_candidates[1].score

        return score_diff < AmbiguityDetector.AMBIGUITY_THRESHOLD

    @staticmethod
    def get_ambiguity_score(candidates: List[DisambiguationCandidate]) -> float:
        """Get ambiguity score for candidates.

        Args:
            candidates: List of candidates

        Returns:
            Ambiguity score (0-1, higher = more ambiguous)
        """
        if len(candidates) < 2:
            return 0.0

        # Sort by score
        sorted_candidates = sorted(candidates, key=lambda x: x.score, reverse=True)

        # Calculate score difference between top candidates
        score_diff = sorted_candidates[0].score - sorted_candidates[1].score

        # Ambiguity is inverse of score difference
        # If scores are close (small diff), ambiguity is high
        # If scores are far apart (large diff), ambiguity is low
        ambiguity = 1.0 - min(score_diff, 1.0)

        return max(0.0, min(ambiguity, 1.0))

    @staticmethod
    def get_top_candidates(
        candidates: List[DisambiguationCandidate],
        top_k: int = 3,
    ) -> List[DisambiguationCandidate]:
        """Get top candidates by score.

        Args:
            candidates: List of candidates
            top_k: Number of top candidates to return

        Returns:
            Top candidates
        """
        sorted_candidates = sorted(candidates, key=lambda x: x.score, reverse=True)
        return sorted_candidates[:top_k]


class ContextualDisambiguator:
    """Uses contextual information for disambiguation."""

    @staticmethod
    def extract_context_features(context: str) -> Dict[str, int]:
        """Extract features from context.

        Args:
            context: Context snippet

        Returns:
            Dictionary of context features
        """
        features = {
            "length": len(context),
            "word_count": len(context.split()),
            "sentence_count": context.count(".") + context.count("!") + context.count("?"),
        }
        return features

    @staticmethod
    def calculate_context_similarity(
        context1: str,
        context2: str,
    ) -> float:
        """Calculate similarity between two contexts.

        Args:
            context1: First context
            context2: Second context

        Returns:
            Similarity score (0-1)
        """
        words1 = set(context1.lower().split())
        words2 = set(context2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def rank_candidates_by_context(
        candidates: List[DisambiguationCandidate],
        context: str,
    ) -> List[Tuple[DisambiguationCandidate, float]]:
        """Rank candidates by context similarity.

        Args:
            candidates: List of candidates
            context: Context snippet

        Returns:
            List of (candidate, score) tuples
        """
        ranked = []
        for candidate in candidates:
            # Use description as candidate context
            similarity = ContextualDisambiguator.calculate_context_similarity(
                context, candidate.description
            )
            ranked.append((candidate, similarity))

        # Sort by similarity
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

