"""Tests for text preprocessing."""

import pytest
from src.preprocessing.text_preprocessor import TextPreprocessor


class TestTextPreprocessor:
    """Test text preprocessing."""

    def setup_method(self):
        """Setup test fixtures."""
        self.preprocessor = TextPreprocessor()

    def test_normalize_unicode(self):
        """Test Unicode normalization."""
        text = "café"  # é as single character
        result = self.preprocessor.normalize_unicode(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_remove_html_tags(self):
        """Test HTML tag removal."""
        text = "<p>Hello <b>world</b></p>"
        result = self.preprocessor.remove_html_tags(text)
        assert "<" not in result
        assert ">" not in result
        assert "Hello" in result
        assert "world" in result

    def test_remove_urls(self):
        """Test URL removal."""
        text = "Check this https://example.com for more info"
        result = self.preprocessor.remove_urls(text)
        assert "https://" not in result
        assert "example.com" not in result
        assert "Check this" in result
        assert "for more info" in result

    def test_remove_extra_whitespace(self):
        """Test extra whitespace removal."""
        text = "Hello    world  \n  test"
        result = self.preprocessor.remove_extra_whitespace(text)
        assert "    " not in result
        assert result.count(" ") <= 2

    def test_preprocess_chain(self):
        """Test full preprocessing chain."""
        text = "<p>Visit https://example.com for café info</p>"
        result = self.preprocessor.preprocess(text)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "<" not in result
        assert "https://" not in result

    def test_empty_text(self):
        """Test preprocessing empty text."""
        result = self.preprocessor.preprocess("")
        assert isinstance(result, str)

    def test_special_characters(self):
        """Test handling of special characters."""
        text = "Hello!!! @#$% world???"
        result = self.preprocessor.preprocess(text)
        assert isinstance(result, str)
        assert len(result) > 0

