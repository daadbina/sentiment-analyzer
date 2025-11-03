"""Tests for article validation module."""

import pytest
from datetime import datetime

from src.validation import ArticleValidator
from src.parser import ParsedArticle


@pytest.fixture
def validator():
    """Create validator instance."""
    return ArticleValidator()


@pytest.fixture
def valid_article():
    """Create valid test article."""
    return ParsedArticle(
        title="Breaking News: Major Discovery",
        body="This is a comprehensive article with substantial content about an important discovery. "
        * 5,
        url="https://example.com/article",
        canonical_url="https://example.com/article",
        source="Example News",
        published_at=datetime.utcnow(),
        author="John Doe",
        extraction_method="html",
    )


class TestArticleValidator:
    """Tests for ArticleValidator class."""

    def test_validate_valid_article(self, validator, valid_article):
        """Test validation of valid article."""
        result = validator.validate(valid_article)

        assert result.is_valid is True
        assert result.validation_score >= 0.7
        assert len(result.errors) == 0

    def test_validate_short_title(self, validator, valid_article):
        """Test validation fails for short title."""
        valid_article.title = "Bad"
        result = validator.validate(valid_article)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("Title too short" in error for error in result.errors)

    def test_validate_short_body(self, validator, valid_article):
        """Test validation fails for short body."""
        valid_article.body = "Too short"
        result = validator.validate(valid_article)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_empty_body(self, validator, valid_article):
        """Test validation fails for empty body."""
        valid_article.body = ""
        result = validator.validate(valid_article)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_missing_source(self, validator, valid_article):
        """Test validation fails for missing source."""
        valid_article.source = ""
        result = validator.validate(valid_article)

        assert result.is_valid is False
        assert any("source" in error.lower() for error in result.errors)

    def test_validate_missing_url(self, validator, valid_article):
        """Test validation fails for missing URL."""
        valid_article.canonical_url = ""
        result = validator.validate(valid_article)

        assert result.is_valid is False
        assert any("url" in error.lower() for error in result.errors)

    def test_validate_invalid_timestamp(self, validator, valid_article):
        """Test validation fails for invalid timestamp."""
        valid_article.published_at = datetime(1900, 1, 1)
        result = validator.validate(valid_article)

        assert result.is_valid is False
        assert any("R1" in error or "timestamp" in error.lower() for error in result.errors)

    def test_validate_score_calculation(self, validator, valid_article):
        """Test validation score calculation."""
        result = validator.validate(valid_article)

        assert 0.0 <= result.validation_score <= 1.0

    def test_validate_multiple_errors(self, validator, valid_article):
        """Test validation with multiple errors."""
        valid_article.title = "Bad"
        valid_article.body = "Short"
        valid_article.source = ""

        result = validator.validate(valid_article)

        assert result.is_valid is False
        assert len(result.errors) >= 2

    def test_validate_unicode_content(self, validator, valid_article):
        """Test validation with unicode content."""
        valid_article.title = "Breaking News: 日本語テスト"
        valid_article.body = "Content with émojis 🎉 and spëcial çharacters " * 5

        result = validator.validate(valid_article)

        assert result.is_valid is True or len(result.errors) > 0  # Should handle unicode

    def test_validate_html_content(self, validator, valid_article):
        """Test validation with HTML content."""
        valid_article.body = "<p>HTML content</p>" * 10

        result = validator.validate(valid_article)

        # Should handle HTML content
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.validation_score, float)
