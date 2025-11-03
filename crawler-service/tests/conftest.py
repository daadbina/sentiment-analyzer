"""Pytest configuration and fixtures."""

import pytest
import os
import sys
from pathlib import Path
from prometheus_client import REGISTRY

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment."""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["LOG_FORMAT"] = "json"


@pytest.fixture(autouse=True)
def reset_env(test_env):
    """Reset environment for each test."""
    yield


@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """Clear Prometheus registry before each test."""
    # Store original collectors
    original_collectors = list(REGISTRY._collector_to_names.keys())
    yield
    # Clear metrics after test
    for collector in list(REGISTRY._collector_to_names.keys()):
        if collector not in original_collectors:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass


@pytest.fixture
def sample_article_data():
    """Sample article data for testing."""
    return {
        "title": "Breaking News: Major Discovery",
        "body": "This is a comprehensive article about an important discovery. " * 10,
        "url": "https://example.com/article",
        "canonical_url": "https://example.com/article",
        "source": "Example News",
        "author": "John Doe",
        "extraction_method": "html",
    }


@pytest.fixture
def sample_feed_data():
    """Sample feed data for testing."""
    return {
        "feed_id": "feed_001",
        "name": "Example News",
        "url": "https://example.com/feed",
        "feed_type": "rss",
        "country": "US",
        "language": "en",
    }


@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed for testing."""
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
    <item>
      <title>Another Story</title>
      <link>https://example.com/article2</link>
      <description>Another news story</description>
      <pubDate>Mon, 15 Jan 2024 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def sample_html_page():
    """Sample HTML page for testing."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Article Title</title>
    <meta name="author" content="Jane Doe">
    <meta name="description" content="Article description">
</head>
<body>
    <h1>Article Title</h1>
    <p>This is the article content with substantial text.</p>
    <p>More content here to make it substantial enough for parsing.</p>
    <p>Even more content to ensure we have enough text for proper extraction.</p>
    <p>Additional paragraphs to increase content length and quality.</p>
</body>
</html>"""
