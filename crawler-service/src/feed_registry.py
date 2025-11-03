"""
Feed registry for managing news feed sources.

Maintains registry of feeds to crawl with metadata and configuration.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import FeedSource
from .exceptions import ConfigError

logger = logging.getLogger(__name__)


class FeedRegistry:
    """
    Registry for managing news feed sources.

    Stores feed configurations and provides query/management operations.
    """

    def __init__(self) -> None:
        """Initialize feed registry."""
        self.feeds: Dict[str, FeedSource] = {}
        self.last_updated: Optional[datetime] = None

    def add_feed(self, feed: FeedSource) -> None:
        """
        Add feed to registry.

        Args:
            feed: Feed source to add.

        Raises:
            ConfigError: If feed_id already exists.
        """
        if feed.feed_id in self.feeds:
            raise ConfigError(
                f"Feed {feed.feed_id} already exists",
                config_key=feed.feed_id,
                error_code="FEED_ALREADY_EXISTS",
            )

        self.feeds[feed.feed_id] = feed
        self.last_updated = datetime.utcnow()
        logger.info(f"Added feed to registry: {feed.feed_id} ({feed.name})")

    def remove_feed(self, feed_id: str) -> None:
        """
        Remove feed from registry.

        Args:
            feed_id: Feed identifier.

        Raises:
            ConfigError: If feed not found.
        """
        if feed_id not in self.feeds:
            raise ConfigError(
                f"Feed {feed_id} not found",
                config_key=feed_id,
                error_code="FEED_NOT_FOUND",
            )

        del self.feeds[feed_id]
        self.last_updated = datetime.utcnow()
        logger.info(f"Removed feed from registry: {feed_id}")

    def get_feed(self, feed_id: str) -> Optional[FeedSource]:
        """
        Get feed by ID.

        Args:
            feed_id: Feed identifier.

        Returns:
            FeedSource or None if not found.
        """
        return self.feeds.get(feed_id)

    def get_all_feeds(self) -> List[FeedSource]:
        """
        Get all feeds in registry.

        Returns:
            list[FeedSource]: All feeds.
        """
        return list(self.feeds.values())

    def get_enabled_feeds(self) -> List[FeedSource]:
        """
        Get all enabled feeds.

        Returns:
            list[FeedSource]: Enabled feeds only.
        """
        return [feed for feed in self.feeds.values() if feed.enabled]

    def get_feeds_by_country(self, country: str) -> List[FeedSource]:
        """
        Get feeds by country code.

        Args:
            country: ISO 3166-1 alpha-2 country code.

        Returns:
            list[FeedSource]: Feeds for country.
        """
        return [
            feed
            for feed in self.feeds.values()
            if feed.country and feed.country.upper() == country.upper()
        ]

    def get_feeds_by_language(self, language: str) -> List[FeedSource]:
        """
        Get feeds by language code.

        Args:
            language: ISO 639-1 language code.

        Returns:
            list[FeedSource]: Feeds for language.
        """
        return [
            feed
            for feed in self.feeds.values()
            if feed.language and feed.language.lower() == language.lower()
        ]

    def get_feeds_by_type(self, feed_type: str) -> List[FeedSource]:
        """
        Get feeds by type.

        Args:
            feed_type: Feed type (rss, html, etc.).

        Returns:
            list[FeedSource]: Feeds of type.
        """
        return [
            feed for feed in self.feeds.values()
            if feed.feed_type.lower() == feed_type.lower()
        ]

    def update_feed(self, feed_id: str, **kwargs) -> FeedSource:
        """
        Update feed configuration.

        Args:
            feed_id: Feed identifier.
            **kwargs: Fields to update.

        Returns:
            FeedSource: Updated feed.

        Raises:
            ConfigError: If feed not found.
        """
        if feed_id not in self.feeds:
            raise ConfigError(
                f"Feed {feed_id} not found",
                config_key=feed_id,
                error_code="FEED_NOT_FOUND",
            )

        feed = self.feeds[feed_id]

        # Update allowed fields
        for key, value in kwargs.items():
            if hasattr(feed, key):
                setattr(feed, key, value)

        self.last_updated = datetime.utcnow()
        logger.info(f"Updated feed: {feed_id}")
        return feed

    def enable_feed(self, feed_id: str) -> None:
        """
        Enable feed.

        Args:
            feed_id: Feed identifier.
        """
        self.update_feed(feed_id, enabled=True)
        logger.info(f"Enabled feed: {feed_id}")

    def disable_feed(self, feed_id: str) -> None:
        """
        Disable feed.

        Args:
            feed_id: Feed identifier.
        """
        self.update_feed(feed_id, enabled=False)
        logger.info(f"Disabled feed: {feed_id}")

    def load_from_json(self, json_data: str) -> None:
        """
        Load feeds from JSON.

        Args:
            json_data: JSON string with feed configurations.

        Raises:
            ConfigError: If JSON is invalid.
        """
        try:
            data = json.loads(json_data)

            if not isinstance(data, list):
                raise ConfigError(
                    "JSON must be array of feed objects",
                    error_code="INVALID_JSON_FORMAT",
                )

            for feed_data in data:
                feed = FeedSource(**feed_data)
                self.add_feed(feed)

            logger.info(f"Loaded {len(data)} feeds from JSON")

        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Invalid JSON: {str(e)}",
                error_code="JSON_PARSE_ERROR",
            )
        except Exception as e:
            raise ConfigError(
                f"Failed to load feeds: {str(e)}",
                error_code="LOAD_FAILED",
            )

    def export_to_json(self) -> str:
        """
        Export feeds to JSON.

        Returns:
            str: JSON string with all feeds.
        """
        feeds_data = [feed.model_dump() for feed in self.feeds.values()]
        return json.dumps(feeds_data, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            dict: Registry statistics.
        """
        all_feeds = self.get_all_feeds()
        enabled_feeds = self.get_enabled_feeds()

        return {
            "total_feeds": len(all_feeds),
            "enabled_feeds": len(enabled_feeds),
            "disabled_feeds": len(all_feeds) - len(enabled_feeds),
            "last_updated": (
                self.last_updated.isoformat()
                if self.last_updated else None
            ),
            "feeds_by_type": self._count_by_field("feed_type"),
            "feeds_by_country": self._count_by_field("country"),
            "feeds_by_language": self._count_by_field("language"),
        }

    def _count_by_field(self, field: str) -> Dict[str, int]:
        """
        Count feeds by field value.

        Args:
            field: Field name to count by.

        Returns:
            dict: Counts by field value.
        """
        counts: Dict[str, int] = {}

        for feed in self.feeds.values():
            value = getattr(feed, field, None)
            if value:
                counts[value] = counts.get(value, 0) + 1

        return counts
