"""REST API server for manual canonicalization."""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class APIRequest:
    """API request model."""

    url: str
    content: Optional[str] = None
    title: Optional[str] = None
    publisher: Optional[str] = None
    domain: Optional[str] = None


@dataclass
class APIResponse:
    """API response model."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CanonicalizeEndpoint:
    """Endpoint for single article canonicalization."""

    def __init__(self, canonicalizer):
        """Initialize endpoint.

        Args:
            canonicalizer: Canonicalizer service instance
        """
        self.canonicalizer = canonicalizer

    async def handle(self, request: APIRequest) -> APIResponse:
        """Handle canonicalization request.

        Args:
            request: API request

        Returns:
            API response
        """
        try:
            if not request.url:
                return APIResponse(
                    success=False,
                    message="URL is required",
                    error="Missing required field: url",
                )

            # Canonicalize article
            result = await self.canonicalizer.canonicalize(
                url=request.url,
                content=request.content,
                title=request.title,
                publisher=request.publisher,
                domain=request.domain,
            )

            return APIResponse(
                success=True,
                message="Article canonicalized successfully",
                data=result,
            )
        except Exception as e:
            logger.error(f"Error canonicalizing article: {e}")
            return APIResponse(
                success=False,
                message="Error canonicalizing article",
                error=str(e),
            )


class BatchCanonicalizeEndpoint:
    """Endpoint for batch canonicalization."""

    def __init__(self, canonicalizer, batch_size: int = 100):
        """Initialize endpoint.

        Args:
            canonicalizer: Canonicalizer service instance
            batch_size: Batch size for processing
        """
        self.canonicalizer = canonicalizer
        self.batch_size = batch_size

    async def handle(self, requests: List[APIRequest]) -> APIResponse:
        """Handle batch canonicalization request.

        Args:
            requests: List of API requests

        Returns:
            API response
        """
        try:
            if not requests:
                return APIResponse(
                    success=False,
                    message="At least one request is required",
                    error="Empty request list",
                )

            if len(requests) > self.batch_size:
                return APIResponse(
                    success=False,
                    message=f"Batch size exceeds maximum of {self.batch_size}",
                    error="Batch too large",
                )

            results = []
            for request in requests:
                result = await self.canonicalizer.canonicalize(
                    url=request.url,
                    content=request.content,
                    title=request.title,
                    publisher=request.publisher,
                    domain=request.domain,
                )
                results.append(result)

            return APIResponse(
                success=True,
                message=f"Batch canonicalization completed: {len(results)} articles",
                data={"results": results, "count": len(results)},
            )
        except Exception as e:
            logger.error(f"Error in batch canonicalization: {e}")
            return APIResponse(
                success=False,
                message="Error in batch canonicalization",
                error=str(e),
            )


class PublisherLookupEndpoint:
    """Endpoint for publisher lookup."""

    def __init__(self, publisher_registry):
        """Initialize endpoint.

        Args:
            publisher_registry: Publisher registry instance
        """
        self.publisher_registry = publisher_registry

    async def handle(self, domain: str) -> APIResponse:
        """Handle publisher lookup request.

        Args:
            domain: Publisher domain

        Returns:
            API response
        """
        try:
            if not domain:
                return APIResponse(
                    success=False,
                    message="Domain is required",
                    error="Missing required field: domain",
                )

            publisher = await self.publisher_registry.get_publisher(domain)

            if not publisher:
                return APIResponse(
                    success=False,
                    message=f"Publisher not found for domain: {domain}",
                    error="Publisher not found",
                )

            return APIResponse(
                success=True,
                message="Publisher found",
                data=publisher,
            )
        except Exception as e:
            logger.error(f"Error looking up publisher: {e}")
            return APIResponse(
                success=False,
                message="Error looking up publisher",
                error=str(e),
            )


class DeduplicationCheckEndpoint:
    """Endpoint for deduplication check."""

    def __init__(self, deduplicator):
        """Initialize endpoint.

        Args:
            deduplicator: Deduplicator instance
        """
        self.deduplicator = deduplicator

    async def handle(self, article_id: str, content: str) -> APIResponse:
        """Handle deduplication check request.

        Args:
            article_id: Article ID
            content: Article content

        Returns:
            API response
        """
        try:
            if not article_id or not content:
                return APIResponse(
                    success=False,
                    message="Article ID and content are required",
                    error="Missing required fields",
                )

            duplicate = self.deduplicator.check_duplicate(article_id, content)

            if duplicate:
                return APIResponse(
                    success=True,
                    message="Duplicate found",
                    data={
                        "is_duplicate": True,
                        "duplicate_id": duplicate.get("id"),
                        "similarity_score": duplicate.get("similarity_score"),
                    },
                )
            else:
                return APIResponse(
                    success=True,
                    message="No duplicate found",
                    data={"is_duplicate": False},
                )
        except Exception as e:
            logger.error(f"Error checking deduplication: {e}")
            return APIResponse(
                success=False,
                message="Error checking deduplication",
                error=str(e),
            )


class HealthCheckEndpoint:
    """Endpoint for health checks."""

    def __init__(self, service):
        """Initialize endpoint.

        Args:
            service: Service instance
        """
        self.service = service

    async def handle(self) -> APIResponse:
        """Handle health check request.

        Returns:
            API response
        """
        try:
            # Check service health
            is_healthy = await self.service.is_healthy()

            if is_healthy:
                return APIResponse(
                    success=True,
                    message="Service is healthy",
                    data={"status": "healthy"},
                )
            else:
                return APIResponse(
                    success=False,
                    message="Service is unhealthy",
                    data={"status": "unhealthy"},
                )
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            return APIResponse(
                success=False,
                message="Error checking health",
                error=str(e),
            )

