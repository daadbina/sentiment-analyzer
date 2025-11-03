"""Tests for content normalizer."""

import pytest
from src.normalization import ContentNormalizer


class TestContentNormalizer:
    """Test content normalization."""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance."""
        return ContentNormalizer()

    def test_normalize_basic_content(self, normalizer):
        """Test basic content normalization."""
        title = "Breaking News: Major Event Happens"
        body = "This is the article body with important information."

        result = normalizer.normalize(title, body)

        assert result.normalized_title
        assert result.normalized_body
        assert result.normalized_checksum
        assert result.word_count > 0
        assert result.sentence_count > 0

    def test_normalize_removes_html_tags(self, normalizer):
        """Test HTML tag removal."""
        title = "Article <b>Title</b>"
        body = "<p>Article body</p> with <a href='#'>link</a>"

        result = normalizer.normalize(title, body)

        assert "<" not in result.normalized_title
        assert "<" not in result.normalized_body

    def test_normalize_removes_urls(self, normalizer):
        """Test URL removal."""
        title = "Article Title"
        body = "Check this link https://example.com for more info"

        result = normalizer.normalize(title, body)

        assert "https://" not in result.normalized_body

    def test_normalize_whitespace(self, normalizer):
        """Test whitespace normalization."""
        title = "Article   Title   With   Spaces"
        body = "Body\n\nwith\n\nmultiple\n\nnewlines"

        result = normalizer.normalize(title, body)

        assert "   " not in result.normalized_title
        assert "\n\n\n" not in result.normalized_body

    def test_normalize_empty_content(self, normalizer):
        """Test handling of empty content."""
        result = normalizer.normalize("", "")

        assert result.normalized_title == ""
        assert result.normalized_body == ""

    def test_normalize_word_count(self, normalizer):
        """Test word count calculation."""
        title = "Title"
        body = "One two three four five"

        result = normalizer.normalize(title, body)

        assert result.word_count == 5

    def test_normalize_sentence_count(self, normalizer):
        """Test sentence count calculation."""
        title = "Title"
        body = "First sentence. Second sentence! Third sentence?"

        result = normalizer.normalize(title, body)

        assert result.sentence_count >= 3

    def test_clean_title_removes_suffixes(self, normalizer):
        """Test title suffix removal."""
        title = "Article Title - CNN"
        cleaned = normalizer.clean_title(title)

        assert "- CNN" not in cleaned

    def test_clean_title_length_limit(self, normalizer):
        """Test title length limiting."""
        title = "A" * 600
        cleaned = normalizer.clean_title(title)

        assert len(cleaned) <= 500

    def test_normalize_checksum_consistency(self, normalizer):
        """Test checksum consistency."""
        title = "Title"
        body = "Body"

        result1 = normalizer.normalize(title, body)
        result2 = normalizer.normalize(title, body)

        assert result1.normalized_checksum == result2.normalized_checksum

    def test_normalize_different_checksums(self, normalizer):
        """Test different checksums for different content."""
        result1 = normalizer.normalize("Title 1", "Body 1")
        result2 = normalizer.normalize("Title 2", "Body 2")

        assert result1.normalized_checksum != result2.normalized_checksum

