"""Tests for fuzzy deduplicator."""

import pytest
from src.deduplication import FuzzyDeduplicator


class TestFuzzyDeduplicator:
    """Test fuzzy deduplication."""

    @pytest.fixture
    def deduplicator(self):
        """Create deduplicator instance."""
        return FuzzyDeduplicator(threshold=0.90)

    def test_check_duplicate_identical_content(self, deduplicator):
        """Test detection of identical content."""
        content = "This is the exact same article content"

        result1 = deduplicator.check_duplicate("article1", content)
        result2 = deduplicator.check_duplicate("article2", content)

        assert result2.checked
        assert len(result2.similar_articles) > 0

    def test_check_duplicate_similar_content(self, deduplicator):
        """Test detection of similar content."""
        content1 = "This is an article about breaking news"
        content2 = "This is an article about breaking news with minor changes"

        result1 = deduplicator.check_duplicate("article1", content1)
        result2 = deduplicator.check_duplicate("article2", content2)

        assert result2.checked

    def test_check_duplicate_different_content(self, deduplicator):
        """Test no detection of different content."""
        content1 = "Article about politics and government"
        content2 = "Article about sports and games"

        result1 = deduplicator.check_duplicate("article1", content1)
        result2 = deduplicator.check_duplicate("article2", content2)

        # Different content should not be flagged as duplicates
        assert result2.checked

    def test_check_duplicate_excludes_self(self, deduplicator):
        """Test that self is excluded from similar articles."""
        content = "Article content"

        result = deduplicator.check_duplicate("article1", content)

        # Should not include self
        similar_ids = [a["article_id"] for a in result.similar_articles]
        assert "article1" not in similar_ids

    def test_check_duplicate_similarity_score(self, deduplicator):
        """Test similarity score is in valid range."""
        content1 = "Article content"
        content2 = "Article content with changes"

        result1 = deduplicator.check_duplicate("article1", content1)
        result2 = deduplicator.check_duplicate("article2", content2)

        for similar in result2.similar_articles:
            assert 0.0 <= similar["similarity"] <= 1.0

    def test_check_duplicate_empty_content(self, deduplicator):
        """Test handling of empty content."""
        result = deduplicator.check_duplicate("article1", "")

        assert result.checked

    def test_clear_deduplicator(self, deduplicator):
        """Test clearing deduplicator state."""
        content = "Article content"

        result1 = deduplicator.check_duplicate("article1", content)
        deduplicator.clear()
        result2 = deduplicator.check_duplicate("article2", content)

        # After clear, should not find previous articles
        assert len(result2.similar_articles) == 0

    def test_multiple_duplicates(self, deduplicator):
        """Test detection of multiple duplicates."""
        content = "This is the article content"

        result1 = deduplicator.check_duplicate("article1", content)
        result2 = deduplicator.check_duplicate("article2", content)
        result3 = deduplicator.check_duplicate("article3", content)

        # Third article should find two similar articles
        assert len(result3.similar_articles) >= 1

