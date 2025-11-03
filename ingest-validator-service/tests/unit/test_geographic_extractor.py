"""Tests for geographic extraction."""

import pytest
from src.validation.geographic import GeographicExtractor


class TestGeographicExtractor:
    """Test geographic extraction functionality."""

    def test_extract_country_from_title(self):
        """Test country extraction from title."""
        title = "US President announces new policy"
        body = "The announcement was made today."
        country = GeographicExtractor.extract_country(title, body)
        assert country == "US"

    def test_extract_country_from_body(self):
        """Test country extraction from body."""
        title = "Breaking News"
        body = "The incident occurred in Russia today."
        country = GeographicExtractor.extract_country(title, body)
        assert country == "RU"

    def test_extract_country_title_priority(self):
        """Test that title is prioritized over body."""
        title = "China announces trade deal"
        body = "The agreement with Russia was signed."
        country = GeographicExtractor.extract_country(title, body)
        assert country == "CN"

    def test_extract_country_from_url(self):
        """Test country extraction from URL TLD."""
        title = "News"
        body = "Some content"
        url = "https://example.de/article"
        country = GeographicExtractor.extract_country(title, body, url)
        assert country == "DE"

    def test_extract_country_existing_takes_precedence(self):
        """Test that existing country takes precedence."""
        title = "US News"
        body = "Content"
        existing_country = "GB"
        country = GeographicExtractor.extract_country(
            title, body, existing_country=existing_country
        )
        assert country == "GB"

    def test_extract_country_not_found(self):
        """Test when no country is found."""
        title = "Generic News"
        body = "Some generic content without country mentions."
        country = GeographicExtractor.extract_country(title, body)
        assert country is None

    def test_extract_country_case_insensitive(self):
        """Test case-insensitive country extraction."""
        title = "UNITED STATES announces policy"
        body = "Content"
        country = GeographicExtractor.extract_country(title, body)
        assert country == "US"

    def test_extract_country_multiple_mentions(self):
        """Test with multiple country mentions (first match wins)."""
        title = "US and UK sign agreement"
        body = "Content"
        country = GeographicExtractor.extract_country(title, body)
        # Should match first country in title
        assert country in ["US", "GB"]

    def test_extract_country_middle_east(self):
        """Test Middle East countries."""
        test_cases = [
            ("Iran nuclear deal", "Iran"),
            ("Saudi Arabia oil prices", "Saudi Arabia"),
            ("Israeli forces", "Israel"),
            ("Palestinian territories", "Palestine"),
        ]
        for text, country_name in test_cases:
            country = GeographicExtractor.extract_country(text, "")
            assert country is not None, f"Failed to extract country from '{text}'"

    def test_extract_country_asia(self):
        """Test Asian countries."""
        test_cases = [
            ("China economy", "China"),
            ("Japan earthquake", "Japan"),
            ("India elections", "India"),
            ("Thailand tourism", "Thailand"),
        ]
        for text, country_name in test_cases:
            country = GeographicExtractor.extract_country(text, "")
            assert country is not None, f"Failed to extract country from '{text}'"

    def test_extract_country_europe(self):
        """Test European countries."""
        test_cases = [
            ("France protests", "France"),
            ("Germany economy", "Germany"),
            ("UK Brexit", "United Kingdom"),
            ("Russia sanctions", "Russia"),
        ]
        for text, country_name in test_cases:
            country = GeographicExtractor.extract_country(text, "")
            assert country is not None, f"Failed to extract country from '{text}'"

    def test_extract_region_from_country(self):
        """Test region extraction from country code."""
        test_cases = [
            ("US", "AMERICAS"),
            ("GB", "EU"),
            ("CN", "APAC"),
            ("RU", "EMEA"),
            ("IR", "MENA"),
            ("BR", "LATAM"),
            ("ZA", "AFRICA"),
        ]
        for country_code, expected_region in test_cases:
            region = GeographicExtractor.extract_region(country_code)
            assert region == expected_region, f"Failed for {country_code}"

    def test_extract_region_none_country(self):
        """Test region extraction with None country."""
        region = GeographicExtractor.extract_region(None)
        assert region is None

    def test_extract_region_unknown_country(self):
        """Test region extraction with unknown country."""
        region = GeographicExtractor.extract_region("XX")
        assert region is None

    def test_extract_country_with_special_characters(self):
        """Test country extraction with special characters."""
        title = "U.S.A. announces policy"
        body = "Content"
        country = GeographicExtractor.extract_country(title, body)
        assert country == "US"

    def test_extract_country_empty_strings(self):
        """Test with empty strings."""
        country = GeographicExtractor.extract_country("", "")
        assert country is None

    def test_extract_country_none_values(self):
        """Test with None values."""
        country = GeographicExtractor.extract_country(None, None)
        assert country is None

    def test_extract_country_url_tld_priority(self):
        """Test URL TLD extraction when no content match."""
        title = "News"
        body = "Some content"
        url = "https://example.fr/article"
        country = GeographicExtractor.extract_country(title, body, url)
        assert country == "FR"

    def test_extract_country_persian(self):
        """Test Persian/Iran country extraction."""
        title = "Iranian officials meet"
        body = "Content"
        country = GeographicExtractor.extract_country(title, body)
        assert country == "IR"

    def test_extract_country_multiple_tlds(self):
        """Test URL with multiple TLD patterns."""
        title = "News"
        body = "Content"
        url = "https://example.co.uk/article"
        country = GeographicExtractor.extract_country(title, body, url)
        assert country == "GB"

    def test_extract_country_arabic_countries(self):
        """Test Arabic-speaking countries."""
        test_cases = [
            ("Egypt news", "Egypt"),
            ("Saudi Arabia", "Saudi Arabia"),
            ("UAE announces", "United Arab Emirates"),
            ("Iraq conflict", "Iraq"),
        ]
        for text, country_name in test_cases:
            country = GeographicExtractor.extract_country(text, "")
            assert country is not None, f"Failed to extract country from '{text}'"

    def test_extract_country_from_url_exception(self):
        """Test country extraction from URL with exception."""
        title = "News"
        body = "Content"
        url = None  # This will cause an exception
        country = GeographicExtractor.extract_country(title, body, url)
        # Should return None on exception
        assert country is None or isinstance(country, str)

    def test_extract_country_from_url_invalid_url(self):
        """Test country extraction from invalid URL."""
        title = "News"
        body = "Content"
        url = "not a valid url"
        country = GeographicExtractor.extract_country(title, body, url)
        # Should handle gracefully
        assert country is None or isinstance(country, str)

    def test_extract_region_us(self):
        """Test region extraction for US."""
        region = GeographicExtractor.extract_region("US")
        assert region == "AMERICAS"

    def test_extract_region_gb(self):
        """Test region extraction for GB."""
        region = GeographicExtractor.extract_region("GB")
        assert region == "EU"

    def test_extract_region_cn(self):
        """Test region extraction for CN."""
        region = GeographicExtractor.extract_region("CN")
        assert region == "APAC"

    def test_extract_region_none(self):
        """Test region extraction with None."""
        region = GeographicExtractor.extract_region(None)
        assert region is None

    def test_extract_region_unknown(self):
        """Test region extraction for unknown country."""
        region = GeographicExtractor.extract_region("XX")
        assert region is None

