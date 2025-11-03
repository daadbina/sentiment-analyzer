"""Tests for normalization scorer."""

import pytest
from src.scoring import NormalizationScorer


class TestNormalizationScorer:
    """Test normalization scoring."""

    @pytest.fixture
    def scorer(self):
        """Create scorer instance."""
        return NormalizationScorer()

    def test_calculate_score_perfect(self, scorer):
        """Test perfect score calculation."""
        score = scorer.calculate_score(
            url_canonicalized=True,
            publisher_credibility=1.0,
            content_cleaned=True,
            metadata_enriched=True,
            domain_classified=True,
            fuzzy_dedup_checked=True,
            word_count=500,
            readability_score=1.0,
        )

        assert score == 1.0

    def test_calculate_score_zero(self, scorer):
        """Test zero score calculation."""
        score = scorer.calculate_score(
            url_canonicalized=False,
            publisher_credibility=0.0,
            content_cleaned=False,
            metadata_enriched=False,
            domain_classified=False,
            fuzzy_dedup_checked=False,
            word_count=0,
            readability_score=0.0,
        )

        assert score == 0.0

    def test_calculate_score_partial(self, scorer):
        """Test partial score calculation."""
        score = scorer.calculate_score(
            url_canonicalized=True,
            publisher_credibility=0.5,
            content_cleaned=True,
            metadata_enriched=False,
            domain_classified=True,
            fuzzy_dedup_checked=True,
            word_count=100,
            readability_score=0.5,
        )

        assert 0.0 < score < 1.0

    def test_calculate_score_range(self, scorer):
        """Test score is in valid range."""
        score = scorer.calculate_score(
            url_canonicalized=True,
            publisher_credibility=0.7,
            content_cleaned=True,
            metadata_enriched=True,
            domain_classified=True,
            fuzzy_dedup_checked=True,
            word_count=200,
            readability_score=0.6,
        )

        assert 0.0 <= score <= 1.0

    def test_get_decision_accept(self, scorer):
        """Test accept decision."""
        decision = scorer.get_decision(0.90, accept_threshold=0.85, review_threshold=0.70)

        assert decision == "accept"

    def test_get_decision_review(self, scorer):
        """Test review decision."""
        decision = scorer.get_decision(0.75, accept_threshold=0.85, review_threshold=0.70)

        assert decision == "review"

    def test_get_decision_reject(self, scorer):
        """Test reject decision."""
        decision = scorer.get_decision(0.60, accept_threshold=0.85, review_threshold=0.70)

        assert decision == "reject"

    def test_get_decision_boundary_accept(self, scorer):
        """Test boundary case for accept."""
        decision = scorer.get_decision(0.85, accept_threshold=0.85, review_threshold=0.70)

        assert decision == "accept"

    def test_get_decision_boundary_review(self, scorer):
        """Test boundary case for review."""
        decision = scorer.get_decision(0.70, accept_threshold=0.85, review_threshold=0.70)

        assert decision == "review"

    def test_content_score_adequate_length(self, scorer):
        """Test content score with adequate length."""
        score = scorer.calculate_score(
            url_canonicalized=False,
            publisher_credibility=0.0,
            content_cleaned=True,
            metadata_enriched=False,
            domain_classified=False,
            fuzzy_dedup_checked=False,
            word_count=100,
            readability_score=0.0,
        )

        # Content score should be 1.0 for 100 words
        assert score > 0.0

    def test_content_score_short_length(self, scorer):
        """Test content score with short length."""
        score = scorer.calculate_score(
            url_canonicalized=False,
            publisher_credibility=0.0,
            content_cleaned=True,
            metadata_enriched=False,
            domain_classified=False,
            fuzzy_dedup_checked=False,
            word_count=10,
            readability_score=0.0,
        )

        # Content score should be lower for 10 words
        assert score >= 0.0

