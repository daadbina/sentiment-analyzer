"""Tests for feed registry module."""

import pytest
import json

from src.feed_registry import FeedRegistry
from src.models import FeedSource
from src.exceptions import ConfigError


@pytest.fixture
def registry():
    """Create feed registry."""
    return FeedRegistry()


@pytest.fixture
def feed1():
    """Create first test feed."""
    return FeedSource(
        feed_id="feed_001",
        name="TechCrunch",
        url="https://techcrunch.com/feed/",
        feed_type="rss",
        country="US",
        language="en",
    )


@pytest.fixture
def feed2():
    """Create second test feed."""
    return FeedSource(
        feed_id="feed_002",
        name="BBC News",
        url="https://bbc.com/news/feed/",
        feed_type="rss",
        country="GB",
        language="en",
    )


@pytest.fixture
def feed3():
    """Create third test feed."""
    return FeedSource(
        feed_id="feed_003",
        name="Le Monde",
        url="https://lemonde.fr/feed/",
        feed_type="rss",
        country="FR",
        language="fr",
    )


class TestFeedRegistry:
    """Tests for FeedRegistry class."""

    def test_add_feed(self, registry, feed1):
        """Test adding feed to registry."""
        registry.add_feed(feed1)

        assert feed1.feed_id in registry.feeds
        assert registry.feeds[feed1.feed_id] == feed1

    def test_add_duplicate_feed(self, registry, feed1):
        """Test adding duplicate feed raises error."""
        registry.add_feed(feed1)

        with pytest.raises(ConfigError):
            registry.add_feed(feed1)

    def test_remove_feed(self, registry, feed1):
        """Test removing feed from registry."""
        registry.add_feed(feed1)
        registry.remove_feed(feed1.feed_id)

        assert feed1.feed_id not in registry.feeds

    def test_remove_nonexistent_feed(self, registry):
        """Test removing nonexistent feed raises error."""
        with pytest.raises(ConfigError):
            registry.remove_feed("nonexistent")

    def test_get_feed(self, registry, feed1):
        """Test getting feed by ID."""
        registry.add_feed(feed1)

        feed = registry.get_feed(feed1.feed_id)
        assert feed == feed1

    def test_get_nonexistent_feed(self, registry):
        """Test getting nonexistent feed returns None."""
        feed = registry.get_feed("nonexistent")
        assert feed is None

    def test_get_all_feeds(self, registry, feed1, feed2, feed3):
        """Test getting all feeds."""
        registry.add_feed(feed1)
        registry.add_feed(feed2)
        registry.add_feed(feed3)

        feeds = registry.get_all_feeds()
        assert len(feeds) == 3

    def test_get_enabled_feeds(self, registry, feed1, feed2):
        """Test getting enabled feeds."""
        registry.add_feed(feed1)
        registry.add_feed(feed2)
        feed2.enabled = False

        enabled = registry.get_enabled_feeds()
        assert len(enabled) == 1
        assert enabled[0].feed_id == feed1.feed_id

    def test_get_feeds_by_country(self, registry, feed1, feed2, feed3):
        """Test getting feeds by country."""
        registry.add_feed(feed1)
        registry.add_feed(feed2)
        registry.add_feed(feed3)

        us_feeds = registry.get_feeds_by_country("US")
        assert len(us_feeds) == 1
        assert us_feeds[0].feed_id == feed1.feed_id

    def test_get_feeds_by_language(self, registry, feed1, feed2, feed3):
        """Test getting feeds by language."""
        registry.add_feed(feed1)
        registry.add_feed(feed2)
        registry.add_feed(feed3)

        en_feeds = registry.get_feeds_by_language("en")
        assert len(en_feeds) == 2

    def test_get_feeds_by_type(self, registry, feed1, feed2):
        """Test getting feeds by type."""
        registry.add_feed(feed1)
        registry.add_feed(feed2)

        rss_feeds = registry.get_feeds_by_type("rss")
        assert len(rss_feeds) == 2

    def test_update_feed(self, registry, feed1):
        """Test updating feed."""
        registry.add_feed(feed1)
        registry.update_feed(feed1.feed_id, name="Updated Name")

        updated = registry.get_feed(feed1.feed_id)
        assert updated.name == "Updated Name"

    def test_enable_feed(self, registry, feed1):
        """Test enabling feed."""
        feed1.enabled = False
        registry.add_feed(feed1)

        registry.enable_feed(feed1.feed_id)
        assert registry.get_feed(feed1.feed_id).enabled is True

    def test_disable_feed(self, registry, feed1):
        """Test disabling feed."""
        registry.add_feed(feed1)
        registry.disable_feed(feed1.feed_id)

        assert registry.get_feed(feed1.feed_id).enabled is False

    def test_load_from_json(self, registry):
        """Test loading feeds from JSON."""
        json_data = json.dumps(
            [
                {
                    "feed_id": "feed_001",
                    "name": "Test Feed",
                    "url": "https://example.com/feed",
                    "feed_type": "rss",
                }
            ]
        )

        registry.load_from_json(json_data)
        assert len(registry.feeds) == 1

    def test_export_to_json(self, registry, feed1):
        """Test exporting feeds to JSON."""
        registry.add_feed(feed1)

        json_str = registry.export_to_json()
        data = json.loads(json_str)

        assert len(data) == 1
        assert data[0]["feed_id"] == feed1.feed_id

    def test_get_stats(self, registry, feed1, feed2):
        """Test getting registry statistics."""
        registry.add_feed(feed1)
        registry.add_feed(feed2)
        feed2.enabled = False

        stats = registry.get_stats()
        assert stats["total_feeds"] == 2
        assert stats["enabled_feeds"] == 1
        assert stats["disabled_feeds"] == 1
