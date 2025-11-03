"""Tests for article normalizer module."""

import pytest
from datetime import datetime

from src.normalizer import ArticleNormalizer
from src.parser import ParsedArticle
from src.models import NewsRawMessage


@pytest.fixture
def normalizer():
    """Create normalizer instance."""
    return ArticleNormalizer()


@pytest.fixture
def article():
    """Create test article."""
    return ParsedArticle(
        title="Breaking News: Major Discovery",
        body="This is a comprehensive article about an important discovery. " * 10,
        url="https://example.com/article?utm_source=twitter&utm_medium=social",
        canonical_url="https://example.com/article",
        source="Example News",
        published_at=datetime.utcnow(),
        author="John Doe",
        extraction_method="html",
        metadata={"country": "US", "category": "tech"},
    )


class TestArticleNormalizer:
    """Tests for ArticleNormalizer class."""

    def test_normalize_article(self, normalizer, article):
        """Test normalizing article."""
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
            validation_score=0.95,
        )

        assert isinstance(message, NewsRawMessage)
        assert message.title == article.title
        assert message.source == article.source
        assert message.validation_score == 0.95

    def test_normalize_removes_tracking_params(self, normalizer, article):
        """Test that tracking parameters are removed from URL."""
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert "utm_source" not in message.canonical_url
        assert "utm_medium" not in message.canonical_url

    def test_normalize_text_whitespace(self, normalizer, article):
        """Test text normalization removes extra whitespace."""
        article.title = "Title  with   extra    spaces"
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert "   " not in message.title

    def test_normalize_extracts_country(self, normalizer, article):
        """Test country extraction from metadata."""
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert message.country == "US"

    def test_normalize_generates_checksum(self, normalizer, article):
        """Test checksum generation."""
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert message.checksum is not None
        assert len(message.checksum) == 64  # SHA-256 hex length

    def test_normalize_detects_language(self, normalizer, article):
        """Test language detection."""
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert message.language is not None
        assert len(message.language) == 2  # ISO 639-1 code

    def test_normalize_sets_timestamps(self, normalizer, article):
        """Test timestamp normalization."""
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert message.published_at is not None
        assert message.crawled_at is not None
        assert "T" in message.published_at  # ISO-8601 format
        assert "Z" in message.crawled_at

    def test_normalize_preserves_metadata(self, normalizer, article):
        """Test metadata preservation."""
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert message.metadata is not None

    def test_normalize_unicode_content(self, normalizer, article):
        """Test normalization with unicode content."""
        article.title = "Breaking News: 日本語テスト"
        article.body = "Content with émojis 🎉 and spëcial çharacters " * 5

        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert message.title is not None
        assert message.body is not None

    def test_normalize_html_content(self, normalizer, article):
        """Test normalization with HTML content."""
        article.body = "<p>HTML content</p>" * 10

        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert message.body is not None

    def test_normalize_url_with_fragment(self, normalizer, article):
        """Test URL normalization removes fragments."""
        article.url = "https://example.com/article#section"
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert "#" not in message.canonical_url

    def test_normalize_sets_feed_id(self, normalizer, article):
        """Test feed ID is set correctly."""
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert message.publisher_id == "feed_001"

    def test_normalize_sets_job_id(self, normalizer, article):
        """Test job ID is set correctly."""
        message = normalizer.normalize(
            article,
            feed_id="feed_001",
            job_id="job_001",
        )

        assert message.ingest_job_id == "job_001"
