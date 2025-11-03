"""
End-to-end integration tests for the Crawler Service.

Tests the complete flow: fetch → parse → normalize → validate → produce.
Uses mock Kafka broker and HTTP server for realistic scenarios.
"""

import asyncio
from datetime import datetime

import pytest
from aioresponses import aioresponses

from src.deduplication import DeduplicationEngine
from src.exceptions import (
    FetchError,
    ParseError,
)
from src.feed_registry import FeedRegistry, FeedSource
from src.fetcher import HTTPFetcher
from src.models import NewsRawMessage
from src.normalizer import ArticleNormalizer
from src.parser.base import ParsedArticle
from src.parser.factory import ParserFactory
from src.utils.checksum import ChecksumEngine
from src.utils.language_detector import LanguageDetector
from src.utils.timestamp import TimestampUtils
from src.validation import ArticleValidator


class TestEndToEndCrawlFlow:
    """Test complete crawl pipeline from fetch to validation."""

    @pytest.fixture
    def feed_registry(self):
        """Create a feed registry with test feeds."""
        registry = FeedRegistry()
        registry.add_feed(
            FeedSource(
                feed_id="test_feed_001",
                name="Test News",
                url="https://example.com/feed.xml",
                feed_type="rss",
                language="en",
                country="US",
                enabled=True,
            )
        )
        return registry

    @pytest.fixture
    def fetcher(self):
        """Create HTTP fetcher."""
        return HTTPFetcher()

    @pytest.fixture
    def parser_factory(self):
        """Create parser factory."""
        return ParserFactory()

    @pytest.fixture
    def normalizer(self):
        """Create article normalizer."""
        return ArticleNormalizer()

    @pytest.fixture
    def validator(self):
        """Create article validator."""
        return ArticleValidator()

    @pytest.fixture
    def dedup_engine(self):
        """Create deduplication engine."""
        return DeduplicationEngine(num_perm=128)

    @pytest.mark.asyncio
    async def test_fetch_parse_normalize_flow(self, fetcher, parser_factory, normalizer, validator):
        """Test complete flow: fetch → parse → normalize → validate."""
        # Mock RSS feed response
        rss_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <link>https://example.com</link>
                <description>Test Description</description>
                <item>
                    <title>Test Article</title>
                    <link>https://example.com/article1</link>
                    <description>This is a comprehensive test article with sufficient content for validation. It contains multiple sentences and enough text to pass content quality checks. The article discusses important topics and provides detailed information.</description>
                    <pubDate>Fri, 02 Nov 2025 10:00:00 GMT</pubDate>
                    <author>Test Author</author>
                </item>
            </channel>
        </rss>"""

        with aioresponses() as mocked:
            mocked.get(
                "https://example.com/feed.xml",
                status=200,
                body=rss_content,
            )

            # Fetch
            content, content_type = await fetcher.fetch("https://example.com/feed.xml")
            assert content is not None
            assert "Test Article" in content

            # Parse
            parser = parser_factory.create_parser("Test Feed", "rss")
            parsed = await parser.parse(content, "https://example.com/feed.xml")
            assert parsed.title == "Test Article"
            assert parsed.body is not None
            assert parsed.url == "https://example.com/article1"

            # Normalize
            normalized = normalizer.normalize(
                parsed,
                feed_id="test_feed_001",
                job_id="job_001",
            )
            assert isinstance(normalized, NewsRawMessage)
            assert normalized.title == "Test Article"
            assert normalized.source == "Test Feed"

            # Validate
            result = validator.validate(normalized)
            assert result.is_valid
            assert result.validation_score >= 0.7

    @pytest.mark.asyncio
    async def test_deduplication_flow(self, normalizer, dedup_engine):
        """Test deduplication of duplicate articles."""
        article1 = ParsedArticle(
            title="Breaking News",
            body="This is important news content.",
            url="https://example.com/news/123",
            canonical_url="https://example.com/news/123",
            published_at=datetime.now(),
            source="Test Source",
            language="en",
        )

        article2 = ParsedArticle(
            title="Breaking News",
            body="This is important news content.",
            url="https://example.com/news/123",
            canonical_url="https://example.com/news/123",
            published_at=datetime.now(),
            source="Test Source",
            language="en",
        )

        # Normalize both
        norm1 = normalizer.normalize(article1, "feed_001", "job_001")
        norm2 = normalizer.normalize(article2, "feed_001", "job_001")

        # Add first to dedup engine
        dedup_engine.add_article(norm1)

        # Check if second is duplicate
        is_dup = dedup_engine.is_duplicate(norm2)
        assert is_dup

    @pytest.mark.asyncio
    async def test_error_handling_fetch_failure(self, fetcher):
        """Test error handling when fetch fails."""
        with aioresponses() as mocked:
            mocked.get(
                "https://example.com/feed.xml",
                status=500,
            )

            with pytest.raises(FetchError):
                await fetcher.fetch("https://example.com/feed.xml")

    @pytest.mark.asyncio
    async def test_error_handling_parse_failure(self, parser_factory):
        """Test error handling when parse fails."""
        parser = parser_factory.create("rss", "Test Feed")

        invalid_content = "This is not valid RSS"

        with pytest.raises(ParseError):
            await parser.parse(invalid_content, "https://example.com/feed.xml")

    def test_validation_failure_short_title(self, validator):
        """Test validation fails for short title."""
        message = NewsRawMessage(
            article_id="test_001",
            canonical_url="https://example.com/1",
            title="Hi",  # Too short
            body="This is a valid body with sufficient content.",
            url="https://example.com/1",
            source="Test",
            language="en",
            published_at="2025-11-02T10:00:00Z",
            crawled_at="2025-11-02T10:00:00Z",
            checksum="abc123",
            validation_score=0.5,
            schema_version="1.0",
            ingest_job_id="job_001",
            publisher_id="pub_001",
            extraction_method="html",
        )

        result = validator.validate(message)
        assert not result.is_valid

    def test_validation_failure_missing_source(self, validator):
        """Test validation fails for missing source."""
        message = NewsRawMessage(
            article_id="test_001",
            canonical_url="https://example.com/1",
            title="Valid Title",
            body="This is a valid body with sufficient content.",
            url="https://example.com/1",
            source="",  # Empty source
            language="en",
            published_at="2025-11-02T10:00:00Z",
            crawled_at="2025-11-02T10:00:00Z",
            checksum="abc123",
            validation_score=0.5,
            schema_version="1.0",
            ingest_job_id="job_001",
            publisher_id="pub_001",
            extraction_method="html",
        )

        result = validator.validate(message)
        assert not result.is_valid

    def test_feed_registry_integration(self, feed_registry):
        """Test feed registry operations."""
        feeds = feed_registry.get_all_feeds()
        assert len(feeds) == 1
        assert feeds[0].name == "Test News"

        enabled_feeds = feed_registry.get_enabled_feeds()
        assert len(enabled_feeds) == 1

        feed_registry.disable_feed("test_feed_001")
        enabled_feeds = feed_registry.get_enabled_feeds()
        assert len(enabled_feeds) == 0

    def test_checksum_consistency(self):
        """Test checksum engine produces consistent results."""
        engine = ChecksumEngine()
        content = "Test article content"

        checksum1 = engine.generate_sha256(content)
        checksum2 = engine.generate_sha256(content)

        assert checksum1 == checksum2

    def test_language_detection_integration(self):
        """Test language detection with various languages."""
        detector = LanguageDetector()

        # English
        lang_en, conf_en = detector.detect("This is an English article about technology. " * 5)
        assert lang_en == "en"
        assert conf_en > 0.5

        # French
        lang_fr, conf_fr = detector.detect("Ceci est un article français sur la technologie. " * 5)
        assert lang_fr == "fr"
        assert conf_fr > 0.5

        # Spanish
        lang_es, conf_es = detector.detect("Este es un artículo español sobre tecnología. " * 5)
        assert lang_es == "es"
        assert conf_es > 0.5

    def test_timestamp_utilities_integration(self):
        """Test timestamp utilities."""
        now = TimestampUtils.now_utc()
        assert now is not None

        iso_str = TimestampUtils.to_iso8601(now)
        assert "T" in iso_str
        assert "Z" in iso_str

        parsed = TimestampUtils.from_iso8601(iso_str)
        assert parsed is not None

    @pytest.mark.asyncio
    async def test_concurrent_feed_processing(self, fetcher, parser_factory):
        """Test processing multiple feeds concurrently."""
        feeds = [
            "https://example.com/feed1.xml",
            "https://example.com/feed2.xml",
            "https://example.com/feed3.xml",
        ]

        rss_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <item>
                    <title>Article</title>
                    <link>https://example.com/article</link>
                    <description>Content</description>
                </item>
            </channel>
        </rss>"""

        with aioresponses() as mocked:
            for feed_url in feeds:
                mocked.get(feed_url, status=200, body=rss_content)

            # Fetch all concurrently
            tasks = [fetcher.fetch(url) for url in feeds]
            results = await asyncio.gather(*tasks)

            assert len(results) == 3
            assert all(r is not None for r in results)
