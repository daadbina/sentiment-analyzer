"""
Base plugin classes for extensibility.

Defines plugin interfaces and metadata structures.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List
from enum import Enum


class PluginType(str, Enum):
    """Plugin type enumeration."""

    SOURCE = "source"
    FETCHER = "fetcher"
    PROCESSOR = "processor"
    TRANSFORMER = "transformer"


@dataclass
class PluginMetadata:
    """Plugin metadata and configuration."""

    name: str
    version: str
    plugin_type: PluginType
    description: str
    author: str
    dependencies: List[str] = None
    config_schema: Dict[str, Any] = None

    def __post_init__(self) -> None:
        """Validate metadata."""
        if not self.name or not self.version:
            raise ValueError("Plugin name and version are required")
        if self.dependencies is None:
            self.dependencies = []
        if self.config_schema is None:
            self.config_schema = {}


class Plugin(ABC):
    """
    Base plugin class.

    All plugins must inherit from this class and implement required methods.
    """

    def __init__(self, metadata: PluginMetadata) -> None:
        """
        Initialize plugin.

        Args:
            metadata: Plugin metadata.
        """
        self.metadata = metadata
        self._initialized = False

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize plugin with configuration.

        Args:
            config: Plugin configuration.

        Raises:
            ValueError: If configuration is invalid.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown plugin and cleanup resources."""
        pass

    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.

        Args:
            config: Configuration to validate.

        Returns:
            True if configuration is valid.

        Raises:
            ValueError: If configuration is invalid.
        """
        pass

    async def health_check(self) -> bool:
        """
        Check plugin health status.

        Returns:
            True if plugin is healthy.
        """
        return self._initialized


class SourcePlugin(Plugin):
    """
    Base class for source plugins.

    Plugins that provide new feed sources.
    """

    @abstractmethod
    async def get_feeds(self) -> List[Dict[str, Any]]:
        """
        Get list of feeds from this source.

        Returns:
            List of feed configurations.
        """
        pass

    @abstractmethod
    async def validate_feed(self, feed_config: Dict[str, Any]) -> bool:
        """
        Validate feed configuration.

        Args:
            feed_config: Feed configuration to validate.

        Returns:
            True if feed configuration is valid.
        """
        pass


class FetcherPlugin(Plugin):
    """
    Base class for fetcher plugins.

    Plugins that provide custom HTTP fetching strategies.
    """

    @abstractmethod
    async def fetch(
        self, url: str, timeout: int = 10, **kwargs: Any
    ) -> str:
        """
        Fetch content from URL.

        Args:
            url: URL to fetch.
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments.

        Returns:
            Fetched content.

        Raises:
            Exception: If fetch fails.
        """
        pass

    @abstractmethod
    async def supports_url(self, url: str) -> bool:
        """
        Check if plugin supports fetching from URL.

        Args:
            url: URL to check.

        Returns:
            True if plugin can fetch from URL.
        """
        pass


class ProcessorPlugin(Plugin):
    """
    Base class for processor plugins.

    Plugins that process and transform articles.
    """

    @abstractmethod
    async def process(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process article.

        Args:
            article: Article to process.

        Returns:
            Processed article.
        """
        pass

    @abstractmethod
    async def can_process(self, article: Dict[str, Any]) -> bool:
        """
        Check if plugin can process article.

        Args:
            article: Article to check.

        Returns:
            True if plugin can process article.
        """
        pass

