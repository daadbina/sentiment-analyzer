"""Tests for URL canonicalizer."""

import pytest
from src.canonicalization import URLCanonicalizer


class TestURLCanonicalizer:
    """Test URL canonicalization."""

    @pytest.fixture
    def canonicalizer(self):
        """Create canonicalizer instance."""
        return URLCanonicalizer()

    def test_canonicalize_basic_url(self, canonicalizer):
        """Test basic URL canonicalization."""
        url = "http://www.example.com/path"
        result = canonicalizer.canonicalize(url)

        assert result.canonicalized
        assert result.normalized_url.startswith("https://")
        assert "www." not in result.normalized_url
        assert result.url_hash

    def test_canonicalize_removes_tracking_params(self, canonicalizer):
        """Test removal of tracking parameters."""
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=123"
        result = canonicalizer.canonicalize(url)

        assert result.canonicalized
        assert "utm_source" not in result.normalized_url
        assert "utm_medium" not in result.normalized_url
        assert "id=123" in result.normalized_url

    def test_canonicalize_removes_fragment(self, canonicalizer):
        """Test removal of URL fragments."""
        url = "https://example.com/article#section1"
        result = canonicalizer.canonicalize(url)

        assert result.canonicalized
        assert "#" not in result.normalized_url

    def test_canonicalize_sorts_parameters(self, canonicalizer):
        """Test parameter sorting."""
        url1 = "https://example.com/article?z=1&a=2&m=3"
        url2 = "https://example.com/article?a=2&m=3&z=1"

        result1 = canonicalizer.canonicalize(url1)
        result2 = canonicalizer.canonicalize(url2)

        assert result1.normalized_url == result2.normalized_url

    def test_canonicalize_http_to_https(self, canonicalizer):
        """Test HTTP to HTTPS conversion."""
        url = "http://example.com/article"
        result = canonicalizer.canonicalize(url)

        assert result.canonicalized
        assert result.normalized_url.startswith("https://")

    def test_canonicalize_removes_www(self, canonicalizer):
        """Test www removal."""
        url = "https://www.example.com/article"
        result = canonicalizer.canonicalize(url)

        assert result.canonicalized
        assert "www." not in result.normalized_url

    def test_canonicalize_extracts_domain(self, canonicalizer):
        """Test domain extraction."""
        url = "https://www.example.com/article"
        result = canonicalizer.canonicalize(url)

        assert result.domain == "example"

    def test_canonicalize_invalid_url(self, canonicalizer):
        """Test handling of invalid URL."""
        url = "not a valid url"
        result = canonicalizer.canonicalize(url)

        # Should still return a result, but not canonicalized
        assert result.original_url == url
        assert result.url_hash

    def test_canonicalize_url_hash_consistency(self, canonicalizer):
        """Test URL hash consistency."""
        url = "https://example.com/article"
        result1 = canonicalizer.canonicalize(url)
        result2 = canonicalizer.canonicalize(url)

        assert result1.url_hash == result2.url_hash

    def test_canonicalize_removes_default_ports(self, canonicalizer):
        """Test removal of default ports."""
        url_http = "http://example.com:80/article"
        url_https = "https://example.com:443/article"

        result_http = canonicalizer.canonicalize(url_http)
        result_https = canonicalizer.canonicalize(url_https)

        assert ":80" not in result_http.normalized_url
        assert ":443" not in result_https.normalized_url

