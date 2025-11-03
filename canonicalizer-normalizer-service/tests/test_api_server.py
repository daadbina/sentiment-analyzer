"""Tests for REST API server."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.api.api_server import (
    CanonicalizeEndpoint,
    BatchCanonicalizeEndpoint,
    PublisherLookupEndpoint,
    DeduplicationCheckEndpoint,
    HealthCheckEndpoint,
    APIRequest,
    APIResponse,
)


class TestAPIRequest:
    """Test API request model."""

    def test_request_creation(self):
        """Test creating API request."""
        request = APIRequest(url="https://example.com")
        assert request.url == "https://example.com"
        assert request.content is None
        assert request.title is None

    def test_request_with_all_fields(self):
        """Test request with all fields."""
        request = APIRequest(
            url="https://example.com",
            content="Article content",
            title="Article title",
            publisher="BBC",
            domain="politics",
        )
        assert request.url == "https://example.com"
        assert request.content == "Article content"
        assert request.title == "Article title"
        assert request.publisher == "BBC"
        assert request.domain == "politics"


class TestAPIResponse:
    """Test API response model."""

    def test_response_success(self):
        """Test successful response."""
        response = APIResponse(
            success=True,
            message="Success",
            data={"key": "value"},
        )
        assert response.success is True
        assert response.message == "Success"
        assert response.data == {"key": "value"}
        assert response.error is None

    def test_response_error(self):
        """Test error response."""
        response = APIResponse(
            success=False,
            message="Error",
            error="Something went wrong",
        )
        assert response.success is False
        assert response.message == "Error"
        assert response.error == "Something went wrong"


class TestCanonicalizeEndpoint:
    """Test canonicalize endpoint."""

    @pytest.mark.asyncio
    async def test_canonicalize_success(self):
        """Test successful canonicalization."""
        canonicalizer = AsyncMock()
        canonicalizer.canonicalize = AsyncMock(return_value={"url": "https://example.com"})

        endpoint = CanonicalizeEndpoint(canonicalizer)
        request = APIRequest(url="https://example.com")
        response = await endpoint.handle(request)

        assert response.success is True
        assert response.message == "Article canonicalized successfully"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_canonicalize_missing_url(self):
        """Test canonicalization with missing URL."""
        canonicalizer = AsyncMock()
        endpoint = CanonicalizeEndpoint(canonicalizer)
        request = APIRequest(url="")
        response = await endpoint.handle(request)

        assert response.success is False
        assert "URL is required" in response.message

    @pytest.mark.asyncio
    async def test_canonicalize_error(self):
        """Test canonicalization error."""
        canonicalizer = AsyncMock()
        canonicalizer.canonicalize = AsyncMock(side_effect=Exception("Test error"))

        endpoint = CanonicalizeEndpoint(canonicalizer)
        request = APIRequest(url="https://example.com")
        response = await endpoint.handle(request)

        assert response.success is False
        assert response.error is not None


class TestBatchCanonicalizeEndpoint:
    """Test batch canonicalize endpoint."""

    @pytest.mark.asyncio
    async def test_batch_canonicalize_success(self):
        """Test successful batch canonicalization."""
        canonicalizer = AsyncMock()
        canonicalizer.canonicalize = AsyncMock(return_value={"url": "https://example.com"})

        endpoint = BatchCanonicalizeEndpoint(canonicalizer, batch_size=100)
        requests = [
            APIRequest(url="https://example1.com"),
            APIRequest(url="https://example2.com"),
        ]
        response = await endpoint.handle(requests)

        assert response.success is True
        assert "Batch canonicalization completed" in response.message

    @pytest.mark.asyncio
    async def test_batch_canonicalize_empty(self):
        """Test batch canonicalization with empty list."""
        canonicalizer = AsyncMock()
        endpoint = BatchCanonicalizeEndpoint(canonicalizer)
        response = await endpoint.handle([])

        assert response.success is False
        assert "At least one request is required" in response.message

    @pytest.mark.asyncio
    async def test_batch_canonicalize_too_large(self):
        """Test batch canonicalization with too many requests."""
        canonicalizer = AsyncMock()
        endpoint = BatchCanonicalizeEndpoint(canonicalizer, batch_size=10)
        requests = [APIRequest(url=f"https://example{i}.com") for i in range(20)]
        response = await endpoint.handle(requests)

        assert response.success is False
        assert "exceeds maximum" in response.message

    @pytest.mark.asyncio
    async def test_batch_canonicalize_error(self):
        """Test batch canonicalization error."""
        canonicalizer = AsyncMock()
        canonicalizer.canonicalize = AsyncMock(side_effect=Exception("Test error"))

        endpoint = BatchCanonicalizeEndpoint(canonicalizer)
        requests = [APIRequest(url="https://example.com")]
        response = await endpoint.handle(requests)

        assert response.success is False
        assert response.error is not None


class TestPublisherLookupEndpoint:
    """Test publisher lookup endpoint."""

    @pytest.mark.asyncio
    async def test_publisher_lookup_success(self):
        """Test successful publisher lookup."""
        registry = AsyncMock()
        registry.get_publisher = AsyncMock(return_value={"domain": "bbc.com", "credibility": 0.95})

        endpoint = PublisherLookupEndpoint(registry)
        response = await endpoint.handle("bbc.com")

        assert response.success is True
        assert response.message == "Publisher found"

    @pytest.mark.asyncio
    async def test_publisher_lookup_missing_domain(self):
        """Test publisher lookup with missing domain."""
        registry = AsyncMock()
        endpoint = PublisherLookupEndpoint(registry)
        response = await endpoint.handle("")

        assert response.success is False
        assert "Domain is required" in response.message

    @pytest.mark.asyncio
    async def test_publisher_lookup_not_found(self):
        """Test publisher lookup not found."""
        registry = AsyncMock()
        registry.get_publisher = AsyncMock(return_value=None)

        endpoint = PublisherLookupEndpoint(registry)
        response = await endpoint.handle("unknown.com")

        assert response.success is False
        assert "Publisher not found" in response.message

    @pytest.mark.asyncio
    async def test_publisher_lookup_error(self):
        """Test publisher lookup error."""
        registry = AsyncMock()
        registry.get_publisher = AsyncMock(side_effect=Exception("Test error"))

        endpoint = PublisherLookupEndpoint(registry)
        response = await endpoint.handle("bbc.com")

        assert response.success is False
        assert response.error is not None


class TestDeduplicationCheckEndpoint:
    """Test deduplication check endpoint."""

    @pytest.mark.asyncio
    async def test_dedup_check_duplicate_found(self):
        """Test deduplication check with duplicate found."""
        deduplicator = MagicMock()
        deduplicator.check_duplicate = MagicMock(
            return_value={"id": "dup-123", "similarity_score": 0.95}
        )

        endpoint = DeduplicationCheckEndpoint(deduplicator)
        response = await endpoint.handle("article-1", "Article content")

        assert response.success is True
        assert response.data["is_duplicate"] is True

    @pytest.mark.asyncio
    async def test_dedup_check_no_duplicate(self):
        """Test deduplication check with no duplicate."""
        deduplicator = MagicMock()
        deduplicator.check_duplicate = MagicMock(return_value=None)

        endpoint = DeduplicationCheckEndpoint(deduplicator)
        response = await endpoint.handle("article-1", "Article content")

        assert response.success is True
        assert response.data["is_duplicate"] is False

    @pytest.mark.asyncio
    async def test_dedup_check_missing_fields(self):
        """Test deduplication check with missing fields."""
        deduplicator = MagicMock()
        endpoint = DeduplicationCheckEndpoint(deduplicator)
        response = await endpoint.handle("", "")

        assert response.success is False
        assert "required" in response.message.lower()

    @pytest.mark.asyncio
    async def test_dedup_check_error(self):
        """Test deduplication check error."""
        deduplicator = MagicMock()
        deduplicator.check_duplicate = MagicMock(side_effect=Exception("Test error"))

        endpoint = DeduplicationCheckEndpoint(deduplicator)
        response = await endpoint.handle("article-1", "Article content")

        assert response.success is False
        assert response.error is not None


class TestHealthCheckEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when service is healthy."""
        service = AsyncMock()
        service.is_healthy = AsyncMock(return_value=True)

        endpoint = HealthCheckEndpoint(service)
        response = await endpoint.handle()

        assert response.success is True
        assert response.data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check when service is unhealthy."""
        service = AsyncMock()
        service.is_healthy = AsyncMock(return_value=False)

        endpoint = HealthCheckEndpoint(service)
        response = await endpoint.handle()

        assert response.success is False
        assert response.data["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_error(self):
        """Test health check error."""
        service = AsyncMock()
        service.is_healthy = AsyncMock(side_effect=Exception("Test error"))

        endpoint = HealthCheckEndpoint(service)
        response = await endpoint.handle()

        assert response.success is False
        assert response.error is not None

