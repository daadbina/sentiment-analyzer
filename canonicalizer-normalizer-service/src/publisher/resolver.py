"""Publisher resolution module."""

import logging
from typing import Optional
import tldextract

from src.clients.postgres_client import PostgresClient
from src.clients.redis_client import RedisClient
from src.exceptions import PublisherResolutionError
from src.models import PublisherEntity

logger = logging.getLogger(__name__)


class PublisherResolver:
    """Resolves publishers from URLs and manages publisher registry."""

    def __init__(self, postgres_client: PostgresClient, redis_client: RedisClient):
        """Initialize publisher resolver.

        Args:
            postgres_client: PostgreSQL client for registry
            redis_client: Redis client for caching
        """
        self.postgres_client = postgres_client
        self.redis_client = redis_client

    async def resolve_publisher(self, url: str) -> Optional[PublisherEntity]:
        """Resolve publisher from URL.

        Args:
            url: Article URL

        Returns:
            PublisherEntity or None if not found
        """
        try:
            # Extract domain from URL
            domain = self._extract_domain(url)
            if not domain:
                logger.warning(f"Failed to extract domain from URL: {url}")
                return None

            # Check cache first
            cached_publisher = self.redis_client.get_publisher(domain)
            if cached_publisher:
                logger.debug(f"Publisher found in cache: {domain}")
                return PublisherEntity(**cached_publisher)

            # Query database
            publisher = await self.postgres_client.get_publisher_by_domain(domain)

            if publisher:
                # Cache the result
                self.redis_client.set_publisher(domain, publisher.model_dump())
                logger.debug(f"Publisher resolved from database: {domain}")
                return publisher

            logger.warning(f"Publisher not found for domain: {domain}")
            return None

        except Exception as e:
            logger.error(f"Publisher resolution failed for {url}: {e}")
            raise PublisherResolutionError(f"Publisher resolution failed: {e}", url=url)

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL.

        Args:
            url: URL to extract domain from

        Returns:
            Domain name or None if extraction fails
        """
        try:
            extracted = tldextract.extract(url)
            if extracted.domain and extracted.suffix:
                # Return full domain with TLD (e.g., "cnn.com")
                return f"{extracted.domain}.{extracted.suffix}"
            return None
        except Exception as e:
            logger.error(f"Failed to extract domain from {url}: {e}")
            return None

    async def get_publisher_by_id(self, publisher_id: str) -> Optional[PublisherEntity]:
        """Get publisher by ID.

        Args:
            publisher_id: Publisher ID

        Returns:
            PublisherEntity or None if not found
        """
        try:
            # This would require a separate database query
            # For now, we rely on domain-based resolution
            logger.debug(f"Publisher lookup by ID: {publisher_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get publisher by ID {publisher_id}: {e}")
            return None

    async def verify_publisher_credibility(self, publisher_id: str) -> float:
        """Verify publisher credibility score.

        Args:
            publisher_id: Publisher ID

        Returns:
            Credibility score (0.0-1.0)
        """
        try:
            # Query database for credibility score
            # This is a simplified version
            logger.debug(f"Verifying publisher credibility: {publisher_id}")
            return 0.5  # Default credibility
        except Exception as e:
            logger.error(f"Failed to verify publisher credibility: {e}")
            return 0.0

