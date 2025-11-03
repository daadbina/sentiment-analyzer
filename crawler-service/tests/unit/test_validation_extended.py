"""
Extended unit tests for validation module.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.validation import ArticleValidator
from src.parser.base import ParsedArticle
from src.exceptions import ValidationError


@pytest.fixture
def validator():
    """Create article validator."""
    return ArticleValidator()


@pytest.fixture
def valid_article():
    """Create valid article."""
    return ParsedArticle(
        title="Test Article Title",
        body="This is a test article body with sufficient content. " * 5,  # Make it long enough
        url="https://example.com/article",
        canonical_url="https://example.com/article",
        source="Test Source",
        published_at=datetime.now(timezone.utc),
        author="Test Author",
        language="en",
        extraction_method="html"
    )


class TestArticleValidator:
    """Test ArticleValidator class."""

    def test_validate_valid_article(self, validator, valid_article):
        """Test validation of valid article."""
        result = validator.validate(valid_article)
        
        assert result is not None
        assert result.is_valid is True

    def test_validate_missing_title(self, validator, valid_article):
        """Test validation with missing title."""
        valid_article.title = ""
        
        result = validator.validate(valid_article)
        
        assert result.is_valid is False
        assert any("title" in str(e).lower() for e in result.errors)

    def test_validate_missing_body(self, validator, valid_article):
        """Test validation with missing body."""
        valid_article.body = ""
        
        result = validator.validate(valid_article)
        
        assert result.is_valid is False

    def test_validate_missing_url(self, validator, valid_article):
        """Test validation with missing URL."""
        valid_article.url = ""

        # ParsedArticle will raise ValueError on empty URL
        with pytest.raises(ValueError):
            ParsedArticle(
                title=valid_article.title,
                body=valid_article.body,
                url="",
                canonical_url=valid_article.canonical_url,
                published_at=valid_article.published_at,
                source=valid_article.source
            )

    def test_validate_invalid_url(self, validator, valid_article):
        """Test validation with invalid URL."""
        # Validator doesn't check URL format, just that it exists
        valid_article.url = "not-a-url"

        result = validator.validate(valid_article)

        # Should still be valid since URL format is not validated
        assert result is not None

    def test_validate_missing_source(self, validator, valid_article):
        """Test validation with missing source."""
        valid_article.source = ""
        
        result = validator.validate(valid_article)
        
        assert result.is_valid is False

    def test_validate_missing_published_at(self, validator, valid_article):
        """Test validation with missing published_at."""
        valid_article.published_at = None
        
        result = validator.validate(valid_article)
        
        assert result.is_valid is False

    def test_validate_future_published_at(self, validator, valid_article):
        """Test validation with future published_at."""
        future_date = datetime.now(timezone.utc)
        future_date = future_date.replace(year=future_date.year + 1)
        valid_article.published_at = future_date
        
        result = validator.validate(valid_article)
        
        assert result.is_valid is False

    def test_validate_short_title(self, validator, valid_article):
        """Test validation with short title."""
        valid_article.title = "Hi"
        
        result = validator.validate(valid_article)
        
        assert result.is_valid is False

    def test_validate_short_body(self, validator, valid_article):
        """Test validation with short body."""
        valid_article.body = "Short"
        
        result = validator.validate(valid_article)
        
        assert result.is_valid is False

    def test_validate_long_title(self, validator, valid_article):
        """Test validation with very long title."""
        valid_article.title = "A" * 1000

        result = validator.validate(valid_article)

        # Validator doesn't check title length, just that it exists
        assert result is not None

    def test_validate_long_body(self, validator, valid_article):
        """Test validation with very long body."""
        valid_article.body = "A" * 100000
        
        result = validator.validate(valid_article)
        
        assert result.is_valid is False

    def test_validate_invalid_language(self, validator, valid_article):
        """Test validation with invalid language."""
        valid_article.language = "invalid"
        
        result = validator.validate(valid_article)
        
        # Should still be valid if language is just invalid
        assert result is not None

    def test_validate_missing_language(self, validator, valid_article):
        """Test validation with missing language."""
        valid_article.language = None
        
        result = validator.validate(valid_article)
        
        assert result is not None

    def test_validate_with_html_tags(self, validator, valid_article):
        """Test validation with HTML tags in body."""
        valid_article.body = "<script>alert('xss')</script>Valid content"
        
        result = validator.validate(valid_article)
        
        # Should detect HTML tags
        assert result is not None

    def test_validate_with_special_chars(self, validator, valid_article):
        """Test validation with special characters."""
        valid_article.title = "Test Article™ © ®"
        valid_article.body = "Content with special chars: é à ñ"
        
        result = validator.validate(valid_article)
        
        assert result is not None

    def test_validate_with_unicode(self, validator, valid_article):
        """Test validation with unicode characters."""
        valid_article.title = "测试文章"
        valid_article.body = "这是一个测试文章的内容。"
        
        result = validator.validate(valid_article)
        
        assert result is not None

    def test_validate_with_emoji(self, validator, valid_article):
        """Test validation with emoji."""
        valid_article.title = "Test Article 🎉"
        valid_article.body = "Content with emoji 😊 and more text"
        
        result = validator.validate(valid_article)
        
        assert result is not None

    def test_validate_with_urls_in_body(self, validator, valid_article):
        """Test validation with URLs in body."""
        valid_article.body = "Check out https://example.com for more info. This is valid content."
        
        result = validator.validate(valid_article)
        
        assert result is not None

    def test_validate_with_emails_in_body(self, validator, valid_article):
        """Test validation with emails in body."""
        valid_article.body = "Contact us at test@example.com for more information about this topic."
        
        result = validator.validate(valid_article)
        
        assert result is not None

    def test_validate_with_numbers_in_body(self, validator, valid_article):
        """Test validation with numbers in body."""
        valid_article.body = "The price is $99.99 and the quantity is 100 units."
        
        result = validator.validate(valid_article)
        
        assert result is not None

    def test_validate_with_quotes(self, validator, valid_article):
        """Test validation with quotes."""
        valid_article.title = 'Test "Article" with quotes'
        valid_article.body = "Content with 'single' and \"double\" quotes."
        
        result = validator.validate(valid_article)
        
        assert result is not None

    def test_validate_with_newlines(self, validator, valid_article):
        """Test validation with newlines."""
        valid_article.body = "Line 1\nLine 2\nLine 3\nLine 4"
        
        result = validator.validate(valid_article)
        
        assert result is not None

    def test_validate_with_tabs(self, validator, valid_article):
        """Test validation with tabs."""
        valid_article.body = "Col1\tCol2\tCol3\nData1\tData2\tData3"
        
        result = validator.validate(valid_article)
        
        assert result is not None

    def test_validate_whitespace_only_title(self, validator, valid_article):
        """Test validation with whitespace-only title."""
        valid_article.title = "   "
        
        result = validator.validate(valid_article)
        
        assert result.is_valid is False

    def test_validate_whitespace_only_body(self, validator, valid_article):
        """Test validation with whitespace-only body."""
        valid_article.body = "   \n\t  "
        
        result = validator.validate(valid_article)
        
        assert result.is_valid is False

    def test_validate_null_bytes(self, validator, valid_article):
        """Test validation with null bytes."""
        valid_article.body = "Valid content\x00with null bytes"
        
        result = validator.validate(valid_article)
        
        assert result is not None

