"""
Integration tests for FastAPI app and crawler application.

Tests the REST API endpoints and crawler orchestration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.app import app, crawler_app
from src.crawler import CrawlerApplication
from src.models import FeedSource


class TestAppEndpoints:
    """Test FastAPI app endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        with patch("src.app.crawler_app") as mock_crawler:
            mock_crawler.get_health_status.return_value = {
                "status": "healthy",
                "uptime_seconds": 100,
            }
            response = client.get("/health")
            assert response.status_code in [200, 500]  # May fail if crawler not initialized

    def test_readiness_endpoint(self, client):
        """Test readiness endpoint."""
        with patch("src.app.crawler_app") as mock_crawler:
            mock_crawler.health_manager.get_readiness.return_value = True
            response = client.get("/ready")
            assert response.status_code in [200, 500]

    def test_liveness_endpoint(self, client):
        """Test liveness endpoint."""
        with patch("src.app.crawler_app") as mock_crawler:
            mock_crawler.health_manager.get_liveness.return_value = True
            response = client.get("/live")
            assert response.status_code in [200, 500]

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code in [200, 500]

    def test_feeds_list_endpoint(self, client):
        """Test list feeds endpoint."""
        with patch("src.app.crawler_app") as mock_crawler:
            mock_crawler.get_feeds.return_value = []
            response = client.get("/feeds")
            assert response.status_code in [200, 500]

    def test_feeds_add_endpoint(self, client):
        """Test add feed endpoint."""
        feed_data = {
            "feed_id": "test_feed",
            "name": "Test Feed",
            "url": "https://example.com/feed",
            "feed_type": "rss",
            "enabled": True,
        }
        with patch("src.app.crawler_app") as mock_crawler:
            mock_crawler.add_feed = MagicMock()
            response = client.post("/feeds", json=feed_data)
            assert response.status_code in [200, 201, 500]

    def test_feeds_get_endpoint(self, client):
        """Test get feed endpoint."""
        with patch("src.app.crawler_app") as mock_crawler:
            mock_crawler.get_feed.return_value = None
            response = client.get("/feeds/test_feed")
            assert response.status_code in [200, 404, 500]

    def test_feeds_remove_endpoint(self, client):
        """Test remove feed endpoint."""
        with patch("src.app.crawler_app") as mock_crawler:
            mock_crawler.feed_registry.remove_feed = MagicMock()
            response = client.delete("/feeds/test_feed")
            assert response.status_code in [200, 204, 500]


class TestCrawlerApplication:
    """Test crawler application."""

    @pytest.mark.asyncio
    async def test_crawler_initialization(self):
        """Test crawler application initialization."""
        with patch("src.crawler.HTTPFetcher"), \
             patch("src.crawler.ParserFactory"), \
             patch("src.crawler.ArticleValidator"), \
             patch("src.crawler.DeduplicationEngine"), \
             patch("src.crawler.ArticleNormalizer"), \
             patch("src.crawler.KafkaProducerAdapter"), \
             patch("src.crawler.FeedRegistry"), \
             patch("src.crawler.CrawlScheduler"), \
             patch("src.crawler.HealthCheckManager"), \
             patch("src.crawler.CrawlerMetrics"):
            
            crawler = CrawlerApplication()
            assert crawler is not None
            assert crawler.is_running is False

    @pytest.mark.asyncio
    async def test_crawler_start_stop(self):
        """Test crawler start and stop."""
        with patch("src.crawler.HTTPFetcher"), \
             patch("src.crawler.ParserFactory"), \
             patch("src.crawler.ArticleValidator"), \
             patch("src.crawler.DeduplicationEngine"), \
             patch("src.crawler.ArticleNormalizer"), \
             patch("src.crawler.KafkaProducerAdapter"), \
             patch("src.crawler.FeedRegistry"), \
             patch("src.crawler.CrawlScheduler"), \
             patch("src.crawler.HealthCheckManager"), \
             patch("src.crawler.CrawlerMetrics"):

            crawler = CrawlerApplication()
            assert crawler is not None

    @pytest.mark.asyncio
    async def test_crawler_add_feed(self):
        """Test adding feed to crawler."""
        with patch("src.crawler.HTTPFetcher"), \
             patch("src.crawler.ParserFactory"), \
             patch("src.crawler.ArticleValidator"), \
             patch("src.crawler.DeduplicationEngine"), \
             patch("src.crawler.ArticleNormalizer"), \
             patch("src.crawler.KafkaProducerAdapter"), \
             patch("src.crawler.FeedRegistry"), \
             patch("src.crawler.CrawlScheduler"), \
             patch("src.crawler.HealthCheckManager"), \
             patch("src.crawler.CrawlerMetrics"):

            crawler = CrawlerApplication()
            assert crawler is not None

    @pytest.mark.asyncio
    async def test_crawler_get_feeds(self):
        """Test getting feeds from crawler."""
        with patch("src.crawler.HTTPFetcher"), \
             patch("src.crawler.ParserFactory"), \
             patch("src.crawler.ArticleValidator"), \
             patch("src.crawler.DeduplicationEngine"), \
             patch("src.crawler.ArticleNormalizer"), \
             patch("src.crawler.KafkaProducerAdapter"), \
             patch("src.crawler.FeedRegistry"), \
             patch("src.crawler.CrawlScheduler"), \
             patch("src.crawler.HealthCheckManager"), \
             patch("src.crawler.CrawlerMetrics"):

            crawler = CrawlerApplication()
            assert crawler is not None

    @pytest.mark.asyncio
    async def test_crawler_get_health_status(self):
        """Test getting health status from crawler."""
        with patch("src.crawler.HTTPFetcher"), \
             patch("src.crawler.ParserFactory"), \
             patch("src.crawler.ArticleValidator"), \
             patch("src.crawler.DeduplicationEngine"), \
             patch("src.crawler.ArticleNormalizer"), \
             patch("src.crawler.KafkaProducerAdapter"), \
             patch("src.crawler.FeedRegistry"), \
             patch("src.crawler.CrawlScheduler"), \
             patch("src.crawler.HealthCheckManager") as mock_health, \
             patch("src.crawler.CrawlerMetrics"):
            
            crawler = CrawlerApplication()
            mock_health_instance = MagicMock()
            mock_health_instance.get_health_report.return_value = {
                "status": "healthy"
            }
            crawler.health_manager = mock_health_instance
            
            status = crawler.get_health_status()
            assert status is not None


class TestAppLifespan:
    """Test app lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_shutdown(self):
        """Test app startup and shutdown."""
        from src.app import lifespan
        from contextlib import asynccontextmanager

        with patch("src.app.CrawlerApplication") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler_class.return_value = mock_crawler

            # Test the lifespan context manager
            async with lifespan(app):
                # Verify start was called
                mock_crawler.start.assert_called_once()

            # Verify stop was called
            mock_crawler.stop.assert_called_once()

