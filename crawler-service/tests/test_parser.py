"""Tests for parser module."""

import pytest
from datetime import datetime

from src.parser import ParserFactory, RSSParser, HTMLParser, ParsedArticle


@pytest.fixture
def parser_factory():
    """Create parser factory."""
    return ParserFactory()


@pytest.fixture
def rss_content():
    """Create sample RSS feed content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example News</title>
    <link>https://example.com</link>
    <description>Example News Feed</description>
    <item>
      <title>Breaking News</title>
      <link>https://example.com/article1</link>
      <description>This is breaking news content</description>
      <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
      <author>John Doe</author>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def html_content():
    """Create sample HTML content."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Article Title</title>
</head>
<body>
    <h1>Article Title</h1>
    <p>This is the article content with substantial text.</p>
    <p>More content here to make it substantial enough for parsing.</p>
    <p>Even more content to ensure we have enough text.</p>
</body>
</html>"""


class TestParserFactory:
    """Tests for ParserFactory class."""

    def test_create_rss_parser(self, parser_factory):
        """Test creating RSS parser."""
        parser = parser_factory.create_parser("Test Source", "rss")

        assert isinstance(parser, RSSParser)

    def test_create_html_parser(self, parser_factory):
        """Test creating HTML parser."""
        parser = parser_factory.create_parser("Test Source", "html")

        assert isinstance(parser, HTMLParser)

    def test_detect_rss_parser(self, parser_factory, rss_content):
        """Test detecting RSS parser from content."""
        parser = parser_factory.detect_parser("Test Source", "application/rss+xml")

        assert isinstance(parser, RSSParser)

    def test_detect_html_parser(self, parser_factory, html_content):
        """Test detecting HTML parser from content."""
        parser = parser_factory.detect_parser("Test Source", "text/html")

        assert isinstance(parser, HTMLParser)

    def test_register_custom_parser(self, parser_factory):
        """Test registering custom parser."""
        from src.parser.base import BaseParser

        class CustomParser(BaseParser):
            def supports_format(self, content_type: str) -> bool:
                return False

            async def parse(self, content: str, url: str):
                return []

        parser_factory.register_parser("custom", CustomParser)
        assert "custom" in parser_factory._parsers


class TestRSSParser:
    """Tests for RSSParser class."""

    @pytest.mark.asyncio
    async def test_parse_rss_feed(self, rss_content):
        """Test parsing RSS feed."""
        parser = RSSParser("Test Source")
        article = await parser.parse(rss_content, "https://example.com/feed")

        assert isinstance(article, ParsedArticle)
        assert article.title is not None

    @pytest.mark.asyncio
    async def test_parse_rss_article_fields(self, rss_content):
        """Test RSS article field extraction."""
        parser = RSSParser("Test Source")
        article = await parser.parse(rss_content, "https://example.com/feed")

        assert article.title == "Breaking News"
        assert article.url == "https://example.com/article1"
        assert article.author == "John Doe"

    def test_parse_rss_supports_format(self, rss_content):
        """Test RSS parser format detection."""
        parser = RSSParser("Test Source")

        assert parser.supports_format("application/rss+xml") is True

    @pytest.mark.asyncio
    async def test_parse_rss_invalid_content(self):
        """Test parsing invalid RSS content."""
        parser = RSSParser("Test Source")

        with pytest.raises(Exception):
            await parser.parse("invalid content", "https://example.com/feed")


class TestHTMLParser:
    """Tests for HTMLParser class."""

    @pytest.mark.asyncio
    async def test_parse_html_content(self, html_content):
        """Test parsing HTML content."""
        parser = HTMLParser("Test Source")
        article = await parser.parse(html_content, "https://example.com/article")

        assert isinstance(article, ParsedArticle)
        assert article.title is not None

    @pytest.mark.asyncio
    async def test_parse_html_article_fields(self, html_content):
        """Test HTML article field extraction."""
        parser = HTMLParser("Test Source")
        article = await parser.parse(html_content, "https://example.com/article")

        assert article.title is not None
        assert article.body is not None
        assert article.url == "https://example.com/article"

    def test_parse_html_supports_format(self, html_content):
        """Test HTML parser format detection."""
        parser = HTMLParser("Test Source")

        assert parser.supports_format("text/html") is True

    @pytest.mark.asyncio
    async def test_parse_html_invalid_content(self):
        """Test parsing invalid HTML content."""
        parser = HTMLParser("Test Source")

        with pytest.raises(Exception):
            await parser.parse("", "https://example.com/article")


class TestParsedArticle:
    """Tests for ParsedArticle dataclass."""

    def test_create_parsed_article(self):
        """Test creating ParsedArticle."""
        article = ParsedArticle(
            title="Test Article",
            body="Test content",
            url="https://example.com/article",
            canonical_url="https://example.com/article",
            source="Test Source",
            published_at=datetime.utcnow(),
            extraction_method="html",
        )

        assert article.title == "Test Article"
        assert article.body == "Test content"

    def test_parsed_article_validation(self):
        """Test ParsedArticle validation."""
        # Should validate required fields
        with pytest.raises(Exception):
            ParsedArticle(
                title="",  # Empty title
                body="Test content",
                url="https://example.com/article",
                canonical_url="https://example.com/article",
                source="Test Source",
                published_at=datetime.utcnow(),
                extraction_method="html",
            )
