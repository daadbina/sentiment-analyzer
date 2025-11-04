"""Tests for entity disambiguation."""

import pytest
from src.disambiguation.entity_disambiguator import (
    DisambiguationCandidate,
    EntityDisambiguator,
    AmbiguityDetector,
    ContextualDisambiguator,
)


class TestDisambiguationCandidate:
    """Tests for DisambiguationCandidate."""

    def test_create_candidate(self):
        """Test creating a disambiguation candidate."""
        candidate = DisambiguationCandidate(
            entity_id="Q123",
            label="John Smith",
            description="American actor",
            score=0.95,
            source="wikidata",
        )
        assert candidate.entity_id == "Q123"
        assert candidate.label == "John Smith"
        assert candidate.score == 0.95


class TestEntityDisambiguator:
    """Tests for entity disambiguator."""

    def test_disambiguate_single_candidate(self):
        """Test disambiguation with single candidate."""
        candidates = [
            DisambiguationCandidate(
                entity_id="Q123",
                label="John Smith",
                description="American actor",
                score=0.95,
                source="wikidata",
            )
        ]
        result = EntityDisambiguator.disambiguate(
            "John Smith", "PERSON", "John Smith is an actor", candidates
        )
        assert result is not None
        assert result.entity_id == "Q123"

    def test_disambiguate_multiple_candidates(self):
        """Test disambiguation with multiple candidates."""
        candidates = [
            DisambiguationCandidate(
                entity_id="Q123",
                label="John Smith",
                description="American actor",
                score=0.95,
                source="wikidata",
            ),
            DisambiguationCandidate(
                entity_id="Q456",
                label="John Smith",
                description="British politician",
                score=0.70,
                source="wikidata",
            ),
        ]
        result = EntityDisambiguator.disambiguate(
            "John Smith", "PERSON", "John Smith is an actor", candidates
        )
        assert result is not None
        assert result.entity_id == "Q123"  # Higher score

    def test_disambiguate_with_context(self):
        """Test disambiguation using context."""
        candidates = [
            DisambiguationCandidate(
                entity_id="Q123",
                label="John Smith",
                description="American actor",
                score=0.80,
                source="wikidata",
            ),
            DisambiguationCandidate(
                entity_id="Q456",
                label="John Smith",
                description="British politician",
                score=0.75,
                source="wikidata",
            ),
        ]
        # Context mentions "actor"
        result = EntityDisambiguator.disambiguate(
            "John Smith", "PERSON", "John Smith is an actor", candidates
        )
        assert result is not None

    def test_disambiguate_no_candidates(self):
        """Test disambiguation with no candidates."""
        result = EntityDisambiguator.disambiguate(
            "Unknown Entity", "PERSON", "context", []
        )
        assert result is None

    def test_resolve_ambiguity(self):
        """Test resolving ambiguity."""
        candidates = [
            {
                "entity_id": "Q123",
                "label": "John Smith",
                "description": "American actor",
                "score": 0.95,
                "source": "wikidata",
            }
        ]
        result = EntityDisambiguator.resolve_ambiguity(
            "John Smith", "PERSON", "John Smith is an actor", candidates
        )
        assert result is not None
        assert result["entity_id"] == "Q123"


class TestAmbiguityDetector:
    """Tests for ambiguity detector."""

    def test_is_ambiguous_single_candidate(self):
        """Test ambiguity detection with single candidate."""
        candidates = [
            DisambiguationCandidate(
                entity_id="Q123",
                label="John Smith",
                description="American actor",
                score=0.95,
                source="wikidata",
            )
        ]
        assert not AmbiguityDetector.is_ambiguous(candidates)

    def test_is_ambiguous_clear_winner(self):
        """Test ambiguity detection with clear winner."""
        candidates = [
            DisambiguationCandidate(
                entity_id="Q123",
                label="John Smith",
                description="American actor",
                score=0.95,
                source="wikidata",
            ),
            DisambiguationCandidate(
                entity_id="Q456",
                label="John Smith",
                description="British politician",
                score=0.50,
                source="wikidata",
            ),
        ]
        assert not AmbiguityDetector.is_ambiguous(candidates)

    def test_is_ambiguous_close_scores(self):
        """Test ambiguity detection with close scores."""
        candidates = [
            DisambiguationCandidate(
                entity_id="Q123",
                label="John Smith",
                description="American actor",
                score=0.85,
                source="wikidata",
            ),
            DisambiguationCandidate(
                entity_id="Q456",
                label="John Smith",
                description="British politician",
                score=0.80,
                source="wikidata",
            ),
        ]
        assert AmbiguityDetector.is_ambiguous(candidates)

    def test_get_ambiguity_score(self):
        """Test getting ambiguity score."""
        candidates = [
            DisambiguationCandidate(
                entity_id="Q123",
                label="John Smith",
                description="American actor",
                score=0.95,
                source="wikidata",
            ),
            DisambiguationCandidate(
                entity_id="Q456",
                label="John Smith",
                description="British politician",
                score=0.50,
                source="wikidata",
            ),
        ]
        score = AmbiguityDetector.get_ambiguity_score(candidates)
        assert 0.0 <= score <= 1.0

    def test_get_top_candidates(self):
        """Test getting top candidates."""
        candidates = [
            DisambiguationCandidate(
                entity_id="Q1",
                label="Entity 1",
                description="Description 1",
                score=0.95,
                source="wikidata",
            ),
            DisambiguationCandidate(
                entity_id="Q2",
                label="Entity 2",
                description="Description 2",
                score=0.85,
                source="wikidata",
            ),
            DisambiguationCandidate(
                entity_id="Q3",
                label="Entity 3",
                description="Description 3",
                score=0.75,
                source="wikidata",
            ),
            DisambiguationCandidate(
                entity_id="Q4",
                label="Entity 4",
                description="Description 4",
                score=0.65,
                source="wikidata",
            ),
        ]
        top = AmbiguityDetector.get_top_candidates(candidates, top_k=2)
        assert len(top) == 2
        assert top[0].entity_id == "Q1"
        assert top[1].entity_id == "Q2"


class TestContextualDisambiguator:
    """Tests for contextual disambiguator."""

    def test_extract_context_features(self):
        """Test extracting context features."""
        context = "John Smith is an American actor. He was born in 1980."
        features = ContextualDisambiguator.extract_context_features(context)
        assert features["length"] > 0
        assert features["word_count"] > 0
        assert features["sentence_count"] == 2

    def test_calculate_context_similarity_identical(self):
        """Test context similarity for identical contexts."""
        context = "John Smith is an actor"
        similarity = ContextualDisambiguator.calculate_context_similarity(context, context)
        assert similarity == 1.0

    def test_calculate_context_similarity_different(self):
        """Test context similarity for different contexts."""
        context1 = "John Smith is an actor"
        context2 = "Jane Doe is a politician"
        similarity = ContextualDisambiguator.calculate_context_similarity(context1, context2)
        assert 0.0 <= similarity < 1.0

    def test_calculate_context_similarity_empty(self):
        """Test context similarity with empty context."""
        similarity = ContextualDisambiguator.calculate_context_similarity("", "test")
        assert similarity == 0.0

    def test_rank_candidates_by_context(self):
        """Test ranking candidates by context."""
        candidates = [
            DisambiguationCandidate(
                entity_id="Q123",
                label="John Smith",
                description="American actor",
                score=0.95,
                source="wikidata",
            ),
            DisambiguationCandidate(
                entity_id="Q456",
                label="John Smith",
                description="British politician",
                score=0.85,
                source="wikidata",
            ),
        ]
        context = "John Smith is an actor"
        ranked = ContextualDisambiguator.rank_candidates_by_context(candidates, context)
        assert len(ranked) == 2
        # First candidate should have higher similarity (contains "actor")
        assert ranked[0][1] >= ranked[1][1]


class TestDisambiguationIntegration:
    """Integration tests for disambiguation."""

    def test_full_disambiguation_workflow(self):
        """Test full disambiguation workflow."""
        candidates = [
            DisambiguationCandidate(
                entity_id="Q123",
                label="John Smith",
                description="American actor",
                score=0.85,
                source="wikidata",
            ),
            DisambiguationCandidate(
                entity_id="Q456",
                label="John Smith",
                description="British politician",
                score=0.80,
                source="wikidata",
            ),
        ]

        # Check ambiguity
        is_ambiguous = AmbiguityDetector.is_ambiguous(candidates)
        assert is_ambiguous

        # Get ambiguity score
        ambiguity_score = AmbiguityDetector.get_ambiguity_score(candidates)
        assert 0.0 <= ambiguity_score <= 1.0

        # Disambiguate
        context = "John Smith is an actor"
        result = EntityDisambiguator.disambiguate(
            "John Smith", "PERSON", context, candidates
        )
        assert result is not None
        assert result.entity_id == "Q123"

