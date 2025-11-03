"""Tests for deduplication module."""

import pytest
from datetime import datetime

from src.deduplication import DeduplicationEngine
from src.parser import ParsedArticle
from src.exceptions import DuplicateArticleError


@pytest.fixture
def dedup_engine():
    """Create deduplication engine."""
    return DeduplicationEngine(num_perm=128)


@pytest.fixture
def article1():
    """Create first test article."""
    return ParsedArticle(
        title="Breaking News: Major Discovery",
        body="This is a comprehensive article about an important discovery. " * 10,
        url="https://example.com/article1",
        canonical_url="https://example.com/article1",
        source="Example News",
        published_at=datetime.utcnow(),
        extraction_method="html",
    )


@pytest.fixture
def article2():
    """Create second test article (similar to article1)."""
    return ParsedArticle(
        title="Breaking News: Major Discovery",
        body="This is a comprehensive article about an important discovery. " * 10,
        url="https://example.com/article1?utm_source=twitter",
        canonical_url="https://example.com/article1",
        source="Example News",
        published_at=datetime.utcnow(),
        extraction_method="html",
    )


@pytest.fixture
def article3():
    """Create third test article (different)."""
    return ParsedArticle(
        title="Different Article Title",
        body="Completely different content about a different topic. " * 10,
        url="https://example.com/article2",
        canonical_url="https://example.com/article2",
        source="Other News",
        published_at=datetime.utcnow(),
        extraction_method="html",
    )


class TestDeduplicationEngine:
    """Tests for DeduplicationEngine class."""

    def test_add_article(self, dedup_engine, article1):
        """Test adding article to cache."""
        article_id = dedup_engine.add_article(article1)

        assert article_id == article1.canonical_url
        assert article_id in dedup_engine.cache

    def test_duplicate_detection(self, dedup_engine, article1, article2):
        """Test duplicate detection."""
        dedup_engine.add_article(article1)

        # Similar article should be detected as duplicate
        with pytest.raises(DuplicateArticleError):
            dedup_engine.add_article(article2)

    def test_different_articles(self, dedup_engine, article1, article3):
        """Test that different articles are not marked as duplicates."""
        dedup_engine.add_article(article1)

        # Different article should not raise error
        article_id = dedup_engine.add_article(article3)
        assert article_id == article3.canonical_url

    def test_is_duplicate(self, dedup_engine, article1, article2):
        """Test is_duplicate method."""
        dedup_engine.add_article(article1)

        assert dedup_engine.is_duplicate(article2) is True
        assert dedup_engine.is_duplicate(article1) is True

    def test_is_not_duplicate(self, dedup_engine, article1, article3):
        """Test is_duplicate returns False for different articles."""
        dedup_engine.add_article(article1)

        assert dedup_engine.is_duplicate(article3) is False

    def test_get_similar_articles(self, dedup_engine, article1, article2):
        """Test finding similar articles."""
        dedup_engine.add_article(article1)

        similar = dedup_engine.get_similar_articles(article2)
        assert len(similar) > 0

    def test_cache_stats(self, dedup_engine, article1):
        """Test cache statistics."""
        dedup_engine.add_article(article1)

        stats = dedup_engine.get_cache_stats()
        assert stats["cache_size"] == 1
        assert stats["num_perm"] == 128

    def test_clear_cache(self, dedup_engine, article1):
        """Test clearing cache."""
        dedup_engine.add_article(article1)
        assert len(dedup_engine.cache) == 1

        dedup_engine.clear_cache()
        assert len(dedup_engine.cache) == 0

    def test_cache_eviction(self, dedup_engine):
        """Test cache eviction when size limit reached."""
        # Create many articles
        articles = []
        for i in range(150):
            article = ParsedArticle(
                title=f"Article {i}",
                body=f"Content for article {i}. " * 10,
                url=f"https://example.com/article{i}",
                canonical_url=f"https://example.com/article{i}",
                source="Example News",
                published_at=datetime.utcnow(),
                extraction_method="html",
            )
            articles.append(article)

        # Add articles
        for article in articles:
            try:
                dedup_engine.add_article(article)
            except Exception:
                pass

        # Cache should not exceed max size
        stats = dedup_engine.get_cache_stats()
        assert stats["cache_size"] <= dedup_engine.max_cache_size

    def test_shingle_generation(self, dedup_engine):
        """Test shingle generation."""
        text = "This is a test article with multiple words"
        shingles = dedup_engine._generate_shingles(text, n=4)

        assert len(shingles) > 0
        assert all(isinstance(s, str) for s in shingles)

    def test_signature_generation(self, dedup_engine, article1):
        """Test MinHash signature generation."""
        signature = dedup_engine._generate_signature(article1)

        assert signature is not None
        assert hasattr(signature, "update")
