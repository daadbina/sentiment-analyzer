"""Tests for metadata enricher."""

import pytest
from src.enrichment import MetadataEnricher


class TestMetadataEnricher:
    """Test metadata enrichment."""

    @pytest.fixture
    def enricher(self):
        """Create enricher instance."""
        return MetadataEnricher()

    def test_enrich_basic_metadata(self, enricher):
        """Test basic metadata enrichment."""
        title = "Article Title"
        body = "Article body content"
        url = "https://example.com/article"

        result = enricher.enrich(title, body, url)

        assert result.content_type
        assert result.readability_score >= 0.0

    def test_extract_country_us(self, enricher):
        """Test US country extraction."""
        title = "News from United States"
        body = "This happened in America"
        url = "https://example.com"

        result = enricher.enrich(title, body, url)

        assert result.country == "US"

    def test_extract_country_uk(self, enricher):
        """Test UK country extraction."""
        title = "News from Britain"
        body = "This happened in the United Kingdom"
        url = "https://example.com"

        result = enricher.enrich(title, body, url)

        assert result.country == "GB"

    def test_extract_country_china(self, enricher):
        """Test China country extraction."""
        title = "Chinese News"
        body = "This happened in China"
        url = "https://example.com"

        result = enricher.enrich(title, body, url)

        assert result.country == "CN"

    def test_classify_opinion_content(self, enricher):
        """Test opinion content classification."""
        title = "Opinion: Why This Matters"
        body = "This is my editorial on the topic"
        url = "https://example.com"

        result = enricher.enrich(title, body, url)

        assert result.content_type == "opinion"

    def test_classify_analysis_content(self, enricher):
        """Test analysis content classification."""
        title = "Deep Dive Analysis"
        body = "This is an in-depth analysis of the situation"
        url = "https://example.com"

        result = enricher.enrich(title, body, url)

        assert result.content_type == "analysis"

    def test_extract_region_eu(self, enricher):
        """Test EU region extraction."""
        title = "European News"
        body = "News from Europe"
        url = "https://example.de/article"

        result = enricher.enrich(title, body, url)

        assert result.region == "EU"

    def test_extract_region_apac(self, enricher):
        """Test APAC region extraction."""
        title = "Asian News"
        body = "News from Asia"
        url = "https://example.cn/article"

        result = enricher.enrich(title, body, url)

        assert result.region == "APAC"

    def test_readability_score_range(self, enricher):
        """Test readability score is in valid range."""
        title = "Title"
        body = "This is a simple sentence. This is another sentence. And one more."
        url = "https://example.com"

        result = enricher.enrich(title, body, url)

        assert 0.0 <= result.readability_score <= 1.0

    def test_enrich_empty_content(self, enricher):
        """Test enrichment with empty content."""
        result = enricher.enrich("", "", "https://example.com")

        assert result.content_type == "article"
        assert result.readability_score == 0.0

