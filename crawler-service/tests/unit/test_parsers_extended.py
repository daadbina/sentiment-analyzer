"""
Extended unit tests for parser modules.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from src.parser.rss_parser import RSSParser
from src.parser.html_parser import HTMLParser
from src.parser.base import ParsedArticle
from src.exceptions import ParseError


@pytest.fixture
def rss_parser():
    """Create RSS parser."""
    return RSSParser("Test Source")


@pytest.fixture
def html_parser():
    """Create HTML parser."""
    return HTMLParser("Test Source")


@pytest.fixture
def sample_rss_content():
    """Create sample RSS content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>Test Description</description>
    <item>
      <title>Test Article</title>
      <link>https://example.com/article</link>
      <description>Test article description</description>
      <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
      <author>Test Author</author>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def sample_html_content():
    """Create sample HTML content."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Test Article</title>
    <meta property="og:url" content="https://example.com/article">
    <meta property="og:title" content="Test Article Title">
    <meta property="og:description" content="Test article description">
    <meta property="article:published_time" content="2024-01-15T10:30:00Z">
    <meta property="article:author" content="Test Author">
</head>
<body>
    <h1>Test Article Title</h1>
    <article>
        <p>This is the first paragraph of the article.</p>
        <p>This is the second paragraph of the article.</p>
    </article>
</body>
</html>"""


class TestRSSParser:
    """Test RSSParser class."""

    @pytest.mark.asyncio
    async def test_parse_valid_rss(self, rss_parser, sample_rss_content):
        """Test parsing valid RSS content."""
        article = await rss_parser.parse(sample_rss_content, "https://example.com/feed.xml")
        
        assert article is not None
        assert isinstance(article, ParsedArticle)
        assert article.title == "Test Article"
        assert article.url == "https://example.com/article"
        assert article.source == "Test Source"

    @pytest.mark.asyncio
    async def test_parse_empty_feed(self, rss_parser):
        """Test parsing empty RSS feed."""
        empty_rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
  </channel>
</rss>"""
        
        with pytest.raises(ParseError):
            await rss_parser.parse(empty_rss, "https://example.com/feed.xml")

    @pytest.mark.asyncio
    async def test_parse_malformed_rss(self, rss_parser):
        """Test parsing malformed RSS."""
        malformed_rss = "<invalid>xml</invalid>"
        
        with pytest.raises(ParseError):
            await rss_parser.parse(malformed_rss, "https://example.com/feed.xml")

    @pytest.mark.asyncio
    async def test_parse_rss_missing_title(self, rss_parser):
        """Test parsing RSS with missing title."""
        rss_no_title = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <link>https://example.com/article</link>
      <description>Test description</description>
    </item>
  </channel>
</rss>"""
        
        with pytest.raises(ParseError):
            await rss_parser.parse(rss_no_title, "https://example.com/feed.xml")

    @pytest.mark.asyncio
    async def test_parse_rss_missing_link(self, rss_parser):
        """Test parsing RSS with missing link."""
        rss_no_link = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Test Article</title>
      <description>Test description</description>
    </item>
  </channel>
</rss>"""
        
        with pytest.raises(ParseError):
            await rss_parser.parse(rss_no_link, "https://example.com/feed.xml")

    @pytest.mark.asyncio
    async def test_parse_rss_missing_description(self, rss_parser):
        """Test parsing RSS with missing description."""
        rss_no_desc = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Test Article</title>
      <link>https://example.com/article</link>
    </item>
  </channel>
</rss>"""
        
        with pytest.raises(ParseError):
            await rss_parser.parse(rss_no_desc, "https://example.com/feed.xml")

    @pytest.mark.asyncio
    async def test_parse_rss_with_cdata(self, rss_parser):
        """Test parsing RSS with CDATA sections."""
        rss_cdata = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title><![CDATA[Test Article with <HTML>]]></title>
      <link>https://example.com/article</link>
      <description><![CDATA[<p>Test description</p>]]></description>
    </item>
  </channel>
</rss>"""
        
        article = await rss_parser.parse(rss_cdata, "https://example.com/feed.xml")
        
        assert article is not None
        assert "Test Article" in article.title

    @pytest.mark.asyncio
    async def test_parse_atom_feed(self, rss_parser):
        """Test parsing Atom feed."""
        atom_content = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <entry>
    <title>Test Article</title>
    <link href="https://example.com/article"/>
    <summary>Test summary</summary>
    <published>2024-01-15T10:30:00Z</published>
    <author><name>Test Author</name></author>
  </entry>
</feed>"""
        
        article = await rss_parser.parse(atom_content, "https://example.com/feed.xml")
        
        assert article is not None
        assert article.title == "Test Article"


class TestHTMLParser:
    """Test HTMLParser class."""

    @pytest.mark.asyncio
    async def test_parse_valid_html(self, html_parser, sample_html_content):
        """Test parsing valid HTML content."""
        article = await html_parser.parse(sample_html_content, "https://example.com/article")
        
        assert article is not None
        assert isinstance(article, ParsedArticle)
        assert article.title is not None
        assert article.body is not None
        assert article.url == "https://example.com/article"

    @pytest.mark.asyncio
    async def test_parse_empty_html(self, html_parser):
        """Test parsing empty HTML."""
        empty_html = "<html><body></body></html>"
        
        with pytest.raises(ParseError):
            await html_parser.parse(empty_html, "https://example.com/article")

    @pytest.mark.asyncio
    async def test_parse_html_no_title(self, html_parser):
        """Test parsing HTML without title."""
        html_no_title = """<!DOCTYPE html>
<html>
<body>
    <article>
        <p>Article content here</p>
    </article>
</body>
</html>"""
        
        with pytest.raises(ParseError):
            await html_parser.parse(html_no_title, "https://example.com/article")

    @pytest.mark.asyncio
    async def test_parse_html_no_content(self, html_parser):
        """Test parsing HTML without content."""
        html_no_content = """<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body></body>
</html>"""
        
        with pytest.raises(ParseError):
            await html_parser.parse(html_no_content, "https://example.com/article")

    @pytest.mark.asyncio
    async def test_parse_html_with_scripts(self, html_parser):
        """Test parsing HTML with script tags."""
        html_with_scripts = """<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
    <script>alert('test');</script>
    <article>
        <p>Article content</p>
    </article>
</body>
</html>"""
        
        article = await html_parser.parse(html_with_scripts, "https://example.com/article")
        
        assert article is not None
        assert "alert" not in article.body

    @pytest.mark.asyncio
    async def test_parse_html_with_styles(self, html_parser):
        """Test parsing HTML with style tags."""
        html_with_styles = """<!DOCTYPE html>
<html>
<head>
    <title>Test Article</title>
    <style>body { color: red; }</style>
</head>
<body>
    <article>
        <p>Article content</p>
    </article>
</body>
</html>"""

        article = await html_parser.parse(html_with_styles, "https://example.com/article")

        assert article is not None
        assert "color: red" not in article.body

    @pytest.mark.asyncio
    async def test_parse_rss_with_string_date(self, rss_parser):
        """Test parsing RSS with string date."""
        rss_with_string_date = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>Test Description</description>
    <item>
      <title>Test Article</title>
      <link>https://example.com/article</link>
      <description>Test article description</description>
      <published>2024-01-15T10:30:00Z</published>
      <author>Test Author</author>
    </item>
  </channel>
</rss>"""

        article = await rss_parser.parse(rss_with_string_date, "https://example.com/feed")

        assert article is not None
        assert article.title == "Test Article"

    @pytest.mark.asyncio
    async def test_parse_rss_with_datetime_object(self, rss_parser):
        """Test parsing RSS with datetime object."""
        with patch('src.parser.rss_parser.feedparser.parse') as mock_parse:
            mock_feed = MagicMock()
            mock_feed.entries = [{
                'title': 'Test Article',
                'link': 'https://example.com/article',
                'description': 'Test article description',
                'published': datetime(2024, 1, 15, 10, 30, 0),
                'author': 'Test Author'
            }]
            mock_parse.return_value = mock_feed

            article = await rss_parser.parse("dummy", "https://example.com/feed")

            assert article is not None
            assert article.title == "Test Article"

    @pytest.mark.asyncio
    async def test_parse_rss_with_invalid_date(self, rss_parser):
        """Test parsing RSS with invalid date falls back to current time."""
        with patch('src.parser.rss_parser.feedparser.parse') as mock_parse:
            mock_feed = MagicMock()
            mock_feed.entries = [{
                'title': 'Test Article',
                'link': 'https://example.com/article',
                'description': 'Test article description',
                'published': 'invalid-date-format',
                'author': 'Test Author'
            }]
            mock_parse.return_value = mock_feed

            article = await rss_parser.parse("dummy", "https://example.com/feed")

            assert article is not None
            assert article.published_at is not None

    @pytest.mark.asyncio
    async def test_parse_rss_with_no_date(self, rss_parser):
        """Test parsing RSS with no date field."""
        with patch('src.parser.rss_parser.feedparser.parse') as mock_parse:
            mock_feed = MagicMock()
            mock_feed.entries = [{
                'title': 'Test Article',
                'link': 'https://example.com/article',
                'description': 'Test article description',
                'author': 'Test Author'
            }]
            mock_parse.return_value = mock_feed

            article = await rss_parser.parse("dummy", "https://example.com/feed")

            assert article is not None
            assert article.published_at is not None

    def test_rss_supports_format(self, rss_parser):
        """Test RSS parser format support."""
        assert rss_parser.supports_format("application/rss+xml") is True
        assert rss_parser.supports_format("application/atom+xml") is True
        assert rss_parser.supports_format("text/xml") is True
        assert rss_parser.supports_format("application/xml") is True
        assert rss_parser.supports_format("text/html") is False

    def test_rss_supports_format_case_insensitive(self, rss_parser):
        """Test RSS parser format support is case insensitive."""
        assert rss_parser.supports_format("APPLICATION/RSS+XML") is True
        assert rss_parser.supports_format("Application/Atom+Xml") is True

