"""
Simple unit tests for deduplication module.
"""

import pytest
from datetime import datetime, timezone

from src.deduplication import DeduplicationEngine
from src.parser.base import ParsedArticle
from src.exceptions import DuplicateArticleError


@pytest.fixture
def engine():
    """Create deduplication engine."""
    return DeduplicationEngine()


@pytest.fixture
def article_a():
    """Create article A."""
    return ParsedArticle(
        title="Breaking News",
        body="This is the main content of the article. " * 10,
        url="https://example.com/a",
        canonical_url="https://example.com/a",
        published_at=datetime.now(timezone.utc),
        source="Source A",
        language="en",
        extraction_method="html"
    )


@pytest.fixture
def article_b():
    """Create article B with different content."""
    return ParsedArticle(
        title="Different Story",
        body="This is completely different content about a different topic. " * 10,
        url="https://example.com/b",
        canonical_url="https://example.com/b",
        published_at=datetime.now(timezone.utc),
        source="Source B",
        language="en",
        extraction_method="html"
    )


class TestDeduplicationEngine:
    """Test DeduplicationEngine."""

    def test_init(self, engine):
        """Test initialization."""
        assert engine.num_perm == 128
        assert engine.cache is not None
        assert len(engine.cache) == 0

    def test_add_article(self, engine, article_a):
        """Test adding article."""
        article_id = engine.add_article(article_a)
        
        assert article_id == article_a.canonical_url
        assert len(engine.cache) == 1

    def test_is_duplicate_same_article(self, engine, article_a):
        """Test duplicate detection for same article."""
        engine.add_article(article_a)
        
        is_dup = engine.is_duplicate(article_a)
        
        assert is_dup is True

    def test_is_duplicate_different_article(self, engine, article_a, article_b):
        """Test duplicate detection for different articles."""
        engine.add_article(article_a)
        
        is_dup = engine.is_duplicate(article_b)
        
        assert is_dup is False

    def test_add_duplicate_raises_error(self, engine, article_a):
        """Test adding duplicate raises error."""
        engine.add_article(article_a)
        
        with pytest.raises(DuplicateArticleError):
            engine.add_article(article_a)

    def test_get_similar_articles(self, engine, article_a, article_b):
        """Test getting similar articles."""
        engine.add_article(article_a)

        similar = engine.get_similar_articles(article_b)

        assert isinstance(similar, list)

    def test_clear_cache(self, engine, article_a):
        """Test clearing cache."""
        engine.add_article(article_a)
        
        engine.clear_cache()
        
        assert len(engine.cache) == 0
        assert engine.is_duplicate(article_a) is False

    def test_get_cache_stats(self, engine, article_a, article_b):
        """Test getting cache statistics."""
        engine.add_article(article_a)
        engine.add_article(article_b)

        stats = engine.get_cache_stats()

        assert stats is not None
        assert "cache_size" in stats
        assert stats["cache_size"] == 2

    def test_multiple_articles(self, engine, article_a, article_b):
        """Test adding multiple articles."""
        id_a = engine.add_article(article_a)
        id_b = engine.add_article(article_b)
        
        assert id_a != id_b
        assert len(engine.cache) == 2

    def test_article_with_unicode(self, engine):
        """Test with unicode content."""
        article = ParsedArticle(
            title="文章标题",
            body="这是文章内容。" * 10,
            url="https://example.com/unicode",
            canonical_url="https://example.com/unicode",
            published_at=datetime.now(timezone.utc),
            source="Test",
            language="zh",
            extraction_method="html"
        )
        
        article_id = engine.add_article(article)
        
        assert article_id is not None
        assert engine.is_duplicate(article) is True

    def test_article_with_special_chars(self, engine):
        """Test with special characters."""
        article = ParsedArticle(
            title="Article © ® ™",
            body="Content with special chars: é à ñ " * 10,
            url="https://example.com/special",
            canonical_url="https://example.com/special",
            published_at=datetime.now(timezone.utc),
            source="Test",
            language="en",
            extraction_method="html"
        )
        
        article_id = engine.add_article(article)
        
        assert article_id is not None

    def test_article_with_urls(self, engine):
        """Test with URLs in content."""
        article = ParsedArticle(
            title="Article with Links",
            body="Check https://example.com and https://test.com for info. " * 10,
            url="https://example.com/links",
            canonical_url="https://example.com/links",
            published_at=datetime.now(timezone.utc),
            source="Test",
            language="en",
            extraction_method="html"
        )
        
        article_id = engine.add_article(article)
        
        assert article_id is not None

    def test_article_with_numbers(self, engine):
        """Test with numbers."""
        article = ParsedArticle(
            title="Article with Numbers: 123, 456",
            body="Price is $99.99 and quantity is 100 units. " * 10,
            url="https://example.com/numbers",
            canonical_url="https://example.com/numbers",
            published_at=datetime.now(timezone.utc),
            source="Test",
            language="en",
            extraction_method="html"
        )
        
        article_id = engine.add_article(article)
        
        assert article_id is not None

    def test_num_perm_parameter(self):
        """Test num_perm parameter."""
        engine_128 = DeduplicationEngine(num_perm=128)
        engine_256 = DeduplicationEngine(num_perm=256)
        
        assert engine_128.num_perm == 128
        assert engine_256.num_perm == 256

