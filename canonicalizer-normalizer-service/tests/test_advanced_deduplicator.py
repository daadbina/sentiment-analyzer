"""Tests for advanced deduplication with LSH and semantic similarity."""

import pytest
from src.deduplication.advanced_deduplicator import (
    LSHDeduplicator,
    SemanticDeduplicator,
    AdvancedDeduplicator,
    SemanticSimilarityResult,
)


class TestLSHDeduplicator:
    """Test LSH deduplicator."""

    def test_lsh_initialization(self):
        """Test LSH deduplicator initialization."""
        dedup = LSHDeduplicator()
        assert dedup is not None
        assert dedup.num_perm == 128
        assert dedup.threshold == 0.9

    def test_lsh_custom_parameters(self):
        """Test LSH with custom parameters."""
        dedup = LSHDeduplicator(num_perm=64, threshold=0.85)
        assert dedup.num_perm == 64
        assert dedup.threshold == 0.85

    def test_lsh_add_article(self):
        """Test adding article to LSH."""
        dedup = LSHDeduplicator()
        result = dedup.add_article("article1", "This is a test article")
        assert isinstance(result, bool)

    def test_lsh_add_empty_content(self):
        """Test adding article with empty content."""
        dedup = LSHDeduplicator()
        result = dedup.add_article("article1", "")
        assert result is False

    def test_lsh_find_duplicates_empty(self):
        """Test finding duplicates with empty content."""
        dedup = LSHDeduplicator()
        duplicates = dedup.find_duplicates("article1", "")
        assert isinstance(duplicates, list)
        assert len(duplicates) == 0

    def test_lsh_find_duplicates_no_matches(self):
        """Test finding duplicates with no matches."""
        dedup = LSHDeduplicator()
        dedup.add_article("article1", "This is a test article")
        duplicates = dedup.find_duplicates("article2", "Completely different content")
        assert isinstance(duplicates, list)

    def test_lsh_get_shingles(self):
        """Test shingle generation."""
        shingles = LSHDeduplicator._get_shingles("hello", 2)
        assert isinstance(shingles, list)
        assert len(shingles) > 0

    def test_lsh_get_shingles_empty(self):
        """Test shingle generation with empty text."""
        shingles = LSHDeduplicator._get_shingles("", 2)
        assert isinstance(shingles, list)
        assert len(shingles) == 0


class TestSemanticDeduplicator:
    """Test semantic deduplicator."""

    def test_semantic_initialization(self):
        """Test semantic deduplicator initialization."""
        dedup = SemanticDeduplicator()
        assert dedup is not None
        assert dedup.model_name == 'all-MiniLM-L6-v2'

    def test_semantic_custom_model(self):
        """Test semantic deduplicator with custom model."""
        dedup = SemanticDeduplicator('all-MiniLM-L6-v2')
        assert dedup.model_name == 'all-MiniLM-L6-v2'

    def test_semantic_compute_similarity_empty(self):
        """Test computing similarity with empty text."""
        dedup = SemanticDeduplicator()
        similarity = dedup.compute_similarity("", "")
        assert similarity == 0.0

    def test_semantic_compute_similarity_one_empty(self):
        """Test computing similarity with one empty text."""
        dedup = SemanticDeduplicator()
        similarity = dedup.compute_similarity("hello", "")
        assert similarity == 0.0

    def test_semantic_compute_similarity_returns_float(self):
        """Test that similarity returns float."""
        dedup = SemanticDeduplicator()
        similarity = dedup.compute_similarity("hello world", "hello world")
        if dedup.available:
            assert isinstance(similarity, float)
            assert 0.0 <= similarity <= 1.0
        else:
            assert similarity == 0.0

    def test_semantic_find_duplicates_empty_candidates(self):
        """Test finding duplicates with empty candidates."""
        dedup = SemanticDeduplicator()
        results = dedup.find_semantic_duplicates("article1", "content", [])
        assert isinstance(results, list)
        assert len(results) == 0

    def test_semantic_find_duplicates_empty_content(self):
        """Test finding duplicates with empty content."""
        dedup = SemanticDeduplicator()
        candidates = [("article2", "some content")]
        results = dedup.find_semantic_duplicates("article1", "", candidates)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_semantic_find_duplicates_returns_results(self):
        """Test finding duplicates returns results."""
        dedup = SemanticDeduplicator()
        candidates = [
            ("article2", "similar content"),
            ("article3", "different content"),
        ]
        results = dedup.find_semantic_duplicates(
            "article1",
            "similar content",
            candidates
        )
        assert isinstance(results, list)


class TestAdvancedDeduplicator:
    """Test advanced deduplicator."""

    def test_advanced_initialization(self):
        """Test advanced deduplicator initialization."""
        dedup = AdvancedDeduplicator()
        assert dedup is not None
        assert dedup.lsh_threshold == 0.9
        assert dedup.semantic_threshold == 0.85

    def test_advanced_custom_thresholds(self):
        """Test advanced deduplicator with custom thresholds."""
        dedup = AdvancedDeduplicator(lsh_threshold=0.8, semantic_threshold=0.75)
        assert dedup.lsh_threshold == 0.8
        assert dedup.semantic_threshold == 0.75

    def test_advanced_add_article(self):
        """Test adding article."""
        dedup = AdvancedDeduplicator()
        result = dedup.add_article("article1", "This is a test article")
        assert result is True

    def test_advanced_add_multiple_articles(self):
        """Test adding multiple articles."""
        dedup = AdvancedDeduplicator()
        dedup.add_article("article1", "First article")
        dedup.add_article("article2", "Second article")
        dedup.add_article("article3", "Third article")
        assert len(dedup.articles) == 3

    def test_advanced_check_duplicate_no_articles(self):
        """Test checking duplicate with no articles."""
        dedup = AdvancedDeduplicator()
        result = dedup.check_duplicate("article1", "content")
        assert result is None

    def test_advanced_check_duplicate_empty_content(self):
        """Test checking duplicate with empty content."""
        dedup = AdvancedDeduplicator()
        dedup.add_article("article1", "content")
        result = dedup.check_duplicate("article2", "")
        assert result is None

    def test_advanced_clear(self):
        """Test clearing deduplicator."""
        dedup = AdvancedDeduplicator()
        dedup.add_article("article1", "content")
        dedup.add_article("article2", "content")
        assert len(dedup.articles) == 2
        dedup.clear()
        assert len(dedup.articles) == 0

    def test_advanced_check_duplicate_returns_result_or_none(self):
        """Test check_duplicate returns correct type."""
        dedup = AdvancedDeduplicator()
        dedup.add_article("article1", "This is a test article")
        result = dedup.check_duplicate("article2", "This is a test article")
        assert result is None or isinstance(result, SemanticSimilarityResult)


class TestSemanticSimilarityResult:
    """Test SemanticSimilarityResult dataclass."""

    def test_result_creation(self):
        """Test creating semantic similarity result."""
        result = SemanticSimilarityResult(
            article_id="article1",
            similarity_score=0.95,
            is_duplicate=True
        )
        assert result.article_id == "article1"
        assert result.similarity_score == 0.95
        assert result.is_duplicate is True

    def test_result_fields(self):
        """Test result has required fields."""
        result = SemanticSimilarityResult(
            article_id="article2",
            similarity_score=0.5,
            is_duplicate=False
        )
        assert hasattr(result, 'article_id')
        assert hasattr(result, 'similarity_score')
        assert hasattr(result, 'is_duplicate')

    def test_result_similarity_range(self):
        """Test similarity score is in valid range."""
        result = SemanticSimilarityResult(
            article_id="article1",
            similarity_score=0.75,
            is_duplicate=False
        )
        assert 0.0 <= result.similarity_score <= 1.0

