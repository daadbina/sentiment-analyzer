"""
Integration tests for FastAPI app endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from src.app import app
from src.models import FeedSource


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_feed():
    """Create sample feed."""
    return FeedSource(
        feed_id="test-feed-1",
        name="Test Feed",
        url="https://example.com/feed.xml",
        feed_type="rss",
        timeout_seconds=30,
        enabled=True,
    )


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check_success(self, client):
        """Test health check endpoint."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.get_health_status.return_value = {
                "status": "healthy",
                "components": {}
            }
            response = client.get("/health")
            assert response.status_code == 200

    def test_health_check_not_initialized(self, client):
        """Test health check when service not initialized."""
        with patch('src.app.crawler_app', None):
            response = client.get("/health")
            assert response.status_code == 503

    def test_readiness_check_ready(self, client):
        """Test readiness check endpoint."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.health_manager.get_readiness.return_value = True
            response = client.get("/ready")
            assert response.status_code == 200
            assert response.json()["ready"] is True

    def test_readiness_check_not_ready(self, client):
        """Test readiness check when not ready."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.health_manager.get_readiness.return_value = False
            response = client.get("/ready")
            assert response.status_code == 503

    def test_readiness_check_not_initialized(self, client):
        """Test readiness check when service not initialized."""
        with patch('src.app.crawler_app', None):
            response = client.get("/ready")
            assert response.status_code == 503

    def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = client.get("/live")
        assert response.status_code == 200
        assert response.json()["alive"] is True


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert b"HELP" in response.content or b"TYPE" in response.content


class TestFeedEndpoints:
    """Test feed management endpoints."""

    def test_add_feed_success(self, client, sample_feed):
        """Test adding a feed."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.feed_registry.add_feed = MagicMock()
            response = client.post("/feeds", json=sample_feed.model_dump())
            assert response.status_code == 200
            assert response.json()["status"] == "success"

    def test_add_feed_not_initialized(self, client, sample_feed):
        """Test adding feed when service not initialized."""
        with patch('src.app.crawler_app', None):
            response = client.post("/feeds", json=sample_feed.model_dump())
            assert response.status_code == 503

    def test_add_feed_error(self, client, sample_feed):
        """Test adding feed with error."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.feed_registry.add_feed.side_effect = Exception("Add failed")
            response = client.post("/feeds", json=sample_feed.model_dump())
            assert response.status_code == 400

    def test_list_feeds_success(self, client, sample_feed):
        """Test listing feeds."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.feed_registry.get_all_feeds.return_value = [sample_feed]
            response = client.get("/feeds")
            assert response.status_code == 200
            assert response.json()["total"] == 1

    def test_list_feeds_not_initialized(self, client):
        """Test listing feeds when service not initialized."""
        with patch('src.app.crawler_app', None):
            response = client.get("/feeds")
            assert response.status_code == 503

    def test_get_feed_success(self, client, sample_feed):
        """Test getting a feed."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.feed_registry.get_feed.return_value = sample_feed
            response = client.get(f"/feeds/{sample_feed.feed_id}")
            assert response.status_code == 200

    def test_get_feed_not_found(self, client):
        """Test getting non-existent feed."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.feed_registry.get_feed.return_value = None
            response = client.get("/feeds/nonexistent")
            assert response.status_code == 404

    def test_get_feed_not_initialized(self, client):
        """Test getting feed when service not initialized."""
        with patch('src.app.crawler_app', None):
            response = client.get("/feeds/test-feed")
            assert response.status_code == 503

    def test_delete_feed_success(self, client):
        """Test deleting a feed."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.feed_registry.remove_feed = MagicMock()
            response = client.delete("/feeds/test-feed")
            assert response.status_code == 200

    def test_delete_feed_not_found(self, client):
        """Test deleting non-existent feed."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.feed_registry.remove_feed.side_effect = ValueError("Not found")
            response = client.delete("/feeds/nonexistent")
            assert response.status_code == 404


class TestCrawlEndpoints:
    """Test crawl management endpoints."""

    def test_crawl_feed_success(self, client, sample_feed):
        """Test crawling a feed."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.feed_registry.get_feed.return_value = sample_feed
            mock_crawler.crawl_feed = AsyncMock(return_value=MagicMock())
            response = client.post("/crawl/test-feed")
            assert response.status_code == 200

    def test_crawl_feed_not_found(self, client):
        """Test crawling non-existent feed."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.feed_registry.get_feed.return_value = None
            response = client.post("/crawl/nonexistent")
            assert response.status_code == 404

    def test_crawl_feed_not_initialized(self, client):
        """Test crawling when service not initialized."""
        with patch('src.app.crawler_app', None):
            response = client.post("/crawl/test-feed")
            assert response.status_code == 503

    def test_crawl_all_success(self, client):
        """Test crawling all feeds."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.crawl_all_feeds = AsyncMock(return_value=[])
            response = client.post("/crawl")
            assert response.status_code == 200

    def test_crawl_all_not_initialized(self, client):
        """Test crawling all when service not initialized."""
        with patch('src.app.crawler_app', None):
            response = client.post("/crawl")
            assert response.status_code == 503

    def test_crawl_feed_error(self, client, sample_feed):
        """Test crawling a feed with error."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.feed_registry.get_feed.return_value = sample_feed
            mock_crawler.crawl_feed = AsyncMock(side_effect=Exception("Crawl failed"))
            response = client.post("/crawl/test-feed")
            assert response.status_code == 500

    def test_crawl_all_error(self, client):
        """Test crawling all feeds with error."""
        with patch('src.app.crawler_app') as mock_crawler:
            mock_crawler.crawl_all_feeds = AsyncMock(side_effect=Exception("Crawl failed"))
            response = client.post("/crawl")
            assert response.status_code == 500


class TestInfoEndpoint:
    """Test info endpoint."""

    def test_info_endpoint(self, client):
        """Test info endpoint."""
        response = client.get("/info")
        assert response.status_code == 200
        assert "name" in response.json()
        assert "version" in response.json()

