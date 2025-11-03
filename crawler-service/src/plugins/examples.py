"""
Example plugins for extensibility demonstration.

Includes proxy rotation, LLM summarizer, and WebSocket ingestion plugins.
"""

import logging
from typing import Any, Dict, List
import httpx

from .base import (
    FetcherPlugin,
    ProcessorPlugin,
    SourcePlugin,
    PluginMetadata,
)

logger = logging.getLogger(__name__)


class ProxyRotationFetcher(FetcherPlugin):
    """
    Fetcher plugin with proxy rotation support.

    Rotates through proxy list for each request.
    """

    def __init__(self, metadata: PluginMetadata) -> None:
        """Initialize proxy rotation fetcher."""
        super().__init__(metadata)
        self.proxies: List[str] = []
        self.current_proxy_index = 0

    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize with proxy list.

        Args:
            config: Configuration with 'proxies' list.
        """
        self.proxies = config.get("proxies", [])
        if not self.proxies:
            logger.warning("No proxies configured for ProxyRotationFetcher")
        self._initialized = True
        logger.info(
            f"Initialized ProxyRotationFetcher with {len(self.proxies)} proxies"
        )

    async def shutdown(self) -> None:
        """Shutdown fetcher."""
        self._initialized = False
        logger.info("Shutdown ProxyRotationFetcher")

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration.

        Args:
            config: Configuration to validate.

        Returns:
            True if valid.
        """
        if "proxies" not in config:
            raise ValueError("'proxies' key required in configuration")
        if not isinstance(config["proxies"], list):
            raise ValueError("'proxies' must be a list")
        return True

    async def fetch(
        self, url: str, timeout: int = 10, **kwargs: Any
    ) -> str:
        """
        Fetch with proxy rotation.

        Args:
            url: URL to fetch.
            timeout: Request timeout.
            **kwargs: Additional arguments.

        Returns:
            Fetched content.
        """
        if not self.proxies:
            raise ValueError("No proxies available")

        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(
            self.proxies
        )

        async with httpx.AsyncClient(
            proxies=proxy, timeout=timeout
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def supports_url(self, url: str) -> bool:
        """
        Check if URL is supported.

        Args:
            url: URL to check.

        Returns:
            True if URL starts with http/https.
        """
        return url.startswith(("http://", "https://"))


class LLMSummarizerProcessor(ProcessorPlugin):
    """
    Processor plugin for LLM-based article summarization.

    Adds AI-generated summaries to articles.
    """

    def __init__(self, metadata: PluginMetadata) -> None:
        """Initialize LLM summarizer."""
        super().__init__(metadata)
        self.llm_endpoint: str = ""
        self.model: str = ""

    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize with LLM configuration.

        Args:
            config: Configuration with LLM endpoint and model.
        """
        self.llm_endpoint = config.get("llm_endpoint", "")
        self.model = config.get("model", "gpt-3.5-turbo")
        self._initialized = True
        logger.info(f"Initialized LLMSummarizerProcessor with model {self.model}")

    async def shutdown(self) -> None:
        """Shutdown processor."""
        self._initialized = False
        logger.info("Shutdown LLMSummarizerProcessor")

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration.

        Args:
            config: Configuration to validate.

        Returns:
            True if valid.
        """
        if "llm_endpoint" not in config:
            raise ValueError("'llm_endpoint' required in configuration")
        return True

    async def process(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process article with LLM summarization.

        Args:
            article: Article to process.

        Returns:
            Article with added summary.
        """
        if not self.llm_endpoint:
            logger.warning("LLM endpoint not configured, skipping summarization")
            return article

        # Placeholder for actual LLM call
        article["ai_summary"] = f"Summary of: {article.get('title', 'Unknown')}"
        article["ai_summary_model"] = self.model
        return article

    async def can_process(self, article: Dict[str, Any]) -> bool:
        """
        Check if article can be processed.

        Args:
            article: Article to check.

        Returns:
            True if article has content.
        """
        return bool(article.get("content"))


class WebSocketSourcePlugin(SourcePlugin):
    """
    Source plugin for WebSocket-based feed ingestion.

    Provides feeds from WebSocket connections.
    """

    def __init__(self, metadata: PluginMetadata) -> None:
        """Initialize WebSocket source."""
        super().__init__(metadata)
        self.websocket_urls: List[str] = []

    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize with WebSocket URLs.

        Args:
            config: Configuration with WebSocket URLs.
        """
        self.websocket_urls = config.get("websocket_urls", [])
        self._initialized = True
        logger.info(
            f"Initialized WebSocketSourcePlugin with {len(self.websocket_urls)} URLs"
        )

    async def shutdown(self) -> None:
        """Shutdown source."""
        self._initialized = False
        logger.info("Shutdown WebSocketSourcePlugin")

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration.

        Args:
            config: Configuration to validate.

        Returns:
            True if valid.
        """
        if "websocket_urls" not in config:
            raise ValueError("'websocket_urls' required in configuration")
        return True

    async def get_feeds(self) -> List[Dict[str, Any]]:
        """
        Get feeds from WebSocket sources.

        Returns:
            List of feed configurations.
        """
        feeds = []
        for url in self.websocket_urls:
            feeds.append(
                {
                    "feed_id": f"ws_{url.replace('://', '_').replace('/', '_')}",
                    "name": f"WebSocket Feed: {url}",
                    "url": url,
                    "feed_type": "websocket",
                }
            )
        return feeds

    async def validate_feed(self, feed_config: Dict[str, Any]) -> bool:
        """
        Validate feed configuration.

        Args:
            feed_config: Feed configuration to validate.

        Returns:
            True if valid.
        """
        return feed_config.get("feed_type") == "websocket"

