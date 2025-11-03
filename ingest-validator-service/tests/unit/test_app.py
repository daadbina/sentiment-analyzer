"""Tests for FastAPI application."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from src.app import app, validator_service, consumer_task


class TestAppEndpoints:
    """Test FastAPI application endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @patch('src.app.validator_service')
    def test_health_check_healthy(self, mock_service, client):
        """Test health check endpoint when healthy."""
        mock_service.get_health_status.return_value = {
            "status": "healthy",
            "service": "ingest-validator",
            "version": "1.0.0",
            "components": {
                "kafka_consumer": "healthy",
                "kafka_producer": "healthy",
                "pipeline": "healthy",
            },
            "backpressure": {},
        }

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @patch('src.app.validator_service', None)
    def test_health_check_not_initialized(self, client):
        """Test health check when service not initialized."""
        response = client.get("/health")

        assert response.status_code == 503

    @patch('src.app.validator_service')
    def test_readiness_check_ready(self, mock_service, client):
        """Test readiness check endpoint when ready."""
        mock_service.is_ready.return_value = True

        response = client.get("/ready")

        assert response.status_code == 200
        assert response.json()["ready"] is True

    @patch('src.app.validator_service')
    def test_readiness_check_not_ready(self, mock_service, client):
        """Test readiness check endpoint when not ready."""
        mock_service.is_ready.return_value = False

        response = client.get("/ready")

        assert response.status_code == 503
        assert response.json()["ready"] is False

    @patch('src.app.validator_service', None)
    def test_readiness_check_not_initialized(self, client):
        """Test readiness check when service not initialized."""
        response = client.get("/ready")

        assert response.status_code == 503

    def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = client.get("/live")

        assert response.status_code == 200
        assert response.json()["alive"] is True

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert b"# HELP" in response.content or b"# TYPE" in response.content

    @patch('src.app.config')
    def test_service_info(self, mock_config, client):
        """Test service info endpoint."""
        mock_config.environment = "test"
        mock_config.kafka_brokers = "localhost:9092"
        mock_config.schema_registry_url = "http://localhost:8081"

        response = client.get("/info")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Ingest Validator Service"
        assert data["version"] == "1.0.0"

    def test_app_creation(self):
        """Test FastAPI app creation."""
        assert app is not None
        assert app.title == "Ingest Validator Service"
        assert app.version == "1.0.0"

    def test_app_routes(self):
        """Test that all expected routes are registered."""
        routes = [route.path for route in app.routes]

        assert "/health" in routes
        assert "/ready" in routes
        assert "/live" in routes
        assert "/metrics" in routes
        assert "/info" in routes

    def test_app_has_lifespan(self):
        """Test that app has lifespan context manager."""
        assert app.router.lifespan_context is not None

    @patch('src.app.validator_service')
    def test_health_check_degraded(self, mock_service, client):
        """Test health check endpoint when degraded."""
        mock_service.get_health_status.return_value = {
            "status": "degraded",
            "service": "ingest-validator",
            "version": "1.0.0",
            "components": {
                "kafka_consumer": "healthy",
                "kafka_producer": "degraded",
                "pipeline": "healthy",
            },
            "backpressure": {},
        }

        response = client.get("/health")

        assert response.status_code == 503
        assert response.json()["status"] == "degraded"

    def test_app_openapi_schema(self):
        """Test that OpenAPI schema is available."""
        response = TestClient(app).get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_app_docs_available(self):
        """Test that API documentation is available."""
        response = TestClient(app).get("/docs")

        assert response.status_code == 200

    def test_app_redoc_available(self):
        """Test that ReDoc documentation is available."""
        response = TestClient(app).get("/redoc")

        assert response.status_code == 200

    @patch('src.app.validator_service')
    def test_health_check_response_structure(self, mock_service, client):
        """Test health check response structure."""
        mock_service.get_health_status.return_value = {
            "status": "healthy",
            "service": "ingest-validator",
            "version": "1.0.0",
            "components": {
                "kafka_consumer": "healthy",
                "kafka_producer": "healthy",
                "pipeline": "healthy",
            },
            "backpressure": {
                "status": "normal",
                "lag": 100,
            },
        }

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "components" in data
        assert "backpressure" in data

    @patch('src.app.validator_service')
    def test_service_info_response_structure(self, mock_service, client):
        """Test service info response structure."""
        response = client.get("/info")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "environment" in data
        assert "kafka_brokers" in data
        assert "schema_registry_url" in data

    def test_metrics_content_type(self, client):
        """Test metrics endpoint content type."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

    def test_health_check_json_content_type(self, client):
        """Test health check JSON content type."""
        with patch('src.app.validator_service') as mock_service:
            mock_service.get_health_status.return_value = {
                "status": "healthy",
                "service": "ingest-validator",
                "version": "1.0.0",
                "components": {},
                "backpressure": {},
            }

            response = client.get("/health")

            assert response.status_code == 200
            assert "application/json" in response.headers.get("content-type", "")

    def test_readiness_check_json_content_type(self, client):
        """Test readiness check JSON content type."""
        with patch('src.app.validator_service') as mock_service:
            mock_service.is_ready.return_value = True

            response = client.get("/ready")

            assert response.status_code == 200
            assert "application/json" in response.headers.get("content-type", "")

    def test_liveness_check_json_content_type(self, client):
        """Test liveness check JSON content type."""
        response = client.get("/live")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_info_endpoint_json_content_type(self, client):
        """Test info endpoint JSON content type."""
        response = client.get("/info")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    @patch('src.app.validator_service')
    def test_multiple_health_checks(self, mock_service, client):
        """Test multiple health checks in sequence."""
        mock_service.get_health_status.return_value = {
            "status": "healthy",
            "service": "ingest-validator",
            "version": "1.0.0",
            "components": {},
            "backpressure": {},
        }

        for _ in range(3):
            response = client.get("/health")
            assert response.status_code == 200

    @patch('src.app.validator_service')
    def test_multiple_readiness_checks(self, mock_service, client):
        """Test multiple readiness checks in sequence."""
        mock_service.is_ready.return_value = True

        for _ in range(3):
            response = client.get("/ready")
            assert response.status_code == 200

    def test_multiple_liveness_checks(self, client):
        """Test multiple liveness checks in sequence."""
        for _ in range(3):
            response = client.get("/live")
            assert response.status_code == 200

    @patch('src.app.validator_service')
    def test_replay_from_offset_success(self, mock_service, client):
        """Test replay from offset endpoint - success."""
        mock_service.replay_from_offset.return_value = {
            "status": "success",
            "partition": 0,
            "replay_offset": 100,
            "previous_offset": 50,
            "message": "Replay started from offset 100",
        }

        response = client.post("/replay?partition=0&offset=100")

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["replay_offset"] == 100

    @patch('src.app.validator_service')
    def test_replay_from_offset_error(self, mock_service, client):
        """Test replay from offset endpoint - error."""
        mock_service.replay_from_offset.return_value = {
            "status": "error",
            "partition": 0,
            "error": "Invalid offset",
            "message": "Replay failed: Invalid offset",
        }

        response = client.post("/replay?partition=0&offset=-1")

        assert response.status_code == 400
        assert response.json()["status"] == "error"

    @patch('src.app.validator_service', None)
    def test_replay_from_offset_not_initialized(self, client):
        """Test replay endpoint when service not initialized."""
        response = client.post("/replay?partition=0&offset=100")

        assert response.status_code == 503

    @patch('src.app.validator_service')
    def test_get_partition_offsets_success(self, mock_service, client):
        """Test get partition offsets endpoint - success."""
        mock_service.get_partition_offsets.return_value = {
            "status": "success",
            "partition": 0,
            "current_offset": 150,
        }

        response = client.get("/offsets/0")

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["current_offset"] == 150

    @patch('src.app.validator_service')
    def test_get_partition_offsets_error(self, mock_service, client):
        """Test get partition offsets endpoint - error."""
        mock_service.get_partition_offsets.return_value = {
            "status": "error",
            "partition": 0,
            "error": "Partition not found",
        }

        response = client.get("/offsets/0")

        assert response.status_code == 400
        assert response.json()["status"] == "error"

    @patch('src.app.validator_service', None)
    def test_get_partition_offsets_not_initialized(self, client):
        """Test get partition offsets endpoint when service not initialized."""
        response = client.get("/offsets/0")

        assert response.status_code == 503

    @patch('src.app.validator_service')
    def test_batch_validate_success(self, mock_service, client):
        """Test batch validate endpoint - success."""
        mock_service.validate_batch = AsyncMock(
            return_value={
                "status": "success",
                "total_messages": 2,
                "validated_count": 2,
                "rejected_count": 0,
                "results": [
                    {
                        "article_id": "article_1",
                        "status": "validated",
                        "validation_score": 0.9,
                    },
                    {
                        "article_id": "article_2",
                        "status": "validated",
                        "validation_score": 0.85,
                    },
                ],
            }
        )

        messages = {
            "messages": [
                {
                    "article_id": "article_1",
                    "canonical_url": "https://example.com/1",
                    "title": "Test Article 1",
                    "body": "This is a test article body with sufficient content.",
                    "url": "https://example.com/1",
                    "source": "test_source",
                    "published_at": "2025-11-02T10:00:00Z",
                    "language": "en",
                    "crawled_at": "2025-11-02T11:00:00Z",
                    "checksum": "abc123",
                    "validation_score": 0.8,
                    "schema_version": "1.0.0",
                    "ingest_job_id": "job_123",
                    "publisher_id": "pub_123",
                    "extraction_method": "rss",
                },
                {
                    "article_id": "article_2",
                    "canonical_url": "https://example.com/2",
                    "title": "Test Article 2",
                    "body": "This is another test article body with sufficient content.",
                    "url": "https://example.com/2",
                    "source": "test_source",
                    "published_at": "2025-11-02T10:00:00Z",
                    "language": "en",
                    "crawled_at": "2025-11-02T11:00:00Z",
                    "checksum": "def456",
                    "validation_score": 0.8,
                    "schema_version": "1.0.0",
                    "ingest_job_id": "job_123",
                    "publisher_id": "pub_123",
                    "extraction_method": "rss",
                },
            ]
        }

        response = client.post("/batch/validate", json=messages)

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["total_messages"] == 2
        assert response.json()["validated_count"] == 2

    @patch('src.app.validator_service')
    def test_batch_validate_mixed_results(self, mock_service, client):
        """Test batch validate endpoint - mixed results."""
        mock_service.validate_batch = AsyncMock(
            return_value={
                "status": "success",
                "total_messages": 2,
                "validated_count": 1,
                "rejected_count": 1,
                "results": [
                    {
                        "article_id": "article_1",
                        "status": "validated",
                        "validation_score": 0.9,
                    },
                    {
                        "article_id": "article_2",
                        "status": "rejected",
                        "validation_score": 0.6,
                        "reason": "Low validation score",
                    },
                ],
            }
        )

        messages = {
            "messages": [
                {
                    "article_id": "article_1",
                    "canonical_url": "https://example.com/1",
                    "title": "Test Article 1",
                    "body": "This is a test article body with sufficient content.",
                    "url": "https://example.com/1",
                    "source": "test_source",
                    "published_at": "2025-11-02T10:00:00Z",
                    "language": "en",
                    "crawled_at": "2025-11-02T11:00:00Z",
                    "checksum": "abc123",
                    "validation_score": 0.8,
                    "schema_version": "1.0.0",
                    "ingest_job_id": "job_123",
                    "publisher_id": "pub_123",
                    "extraction_method": "rss",
                },
                {
                    "article_id": "article_2",
                    "canonical_url": "https://example.com/2",
                    "title": "Short",
                    "body": "Short",
                    "url": "https://example.com/2",
                    "source": "test_source",
                    "published_at": "2025-11-02T10:00:00Z",
                    "language": "en",
                    "crawled_at": "2025-11-02T11:00:00Z",
                    "checksum": "def456",
                    "validation_score": 0.6,
                    "schema_version": "1.0.0",
                    "ingest_job_id": "job_123",
                    "publisher_id": "pub_123",
                    "extraction_method": "rss",
                },
            ]
        }

        response = client.post("/batch/validate", json=messages)

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["validated_count"] == 1
        assert response.json()["rejected_count"] == 1

    @patch('src.app.validator_service')
    def test_batch_validate_empty_list(self, mock_service, client):
        """Test batch validate endpoint with empty list."""
        messages = {"messages": []}

        response = client.post("/batch/validate", json=messages)

        assert response.status_code == 400
        assert response.json()["status"] == "error"

    @patch('src.app.validator_service')
    def test_batch_validate_error(self, mock_service, client):
        """Test batch validate endpoint - error."""
        mock_service.validate_batch = AsyncMock(
            return_value={
                "status": "error",
                "total_messages": 1,
                "error": "Processing failed",
                "message": "Batch validation failed: Processing failed",
            }
        )

        messages = {
            "messages": [
                {
                    "article_id": "article_1",
                    "canonical_url": "https://example.com/1",
                    "title": "Test Article 1",
                    "body": "This is a test article body with sufficient content.",
                    "url": "https://example.com/1",
                    "source": "test_source",
                    "published_at": "2025-11-02T10:00:00Z",
                    "language": "en",
                    "crawled_at": "2025-11-02T11:00:00Z",
                    "checksum": "abc123",
                    "validation_score": 0.8,
                    "schema_version": "1.0.0",
                    "ingest_job_id": "job_123",
                    "publisher_id": "pub_123",
                    "extraction_method": "rss",
                },
            ]
        }

        response = client.post("/batch/validate", json=messages)

        assert response.status_code == 400
        assert response.json()["status"] == "error"

    @patch('src.app.validator_service', None)
    def test_batch_validate_not_initialized(self, client):
        """Test batch validate endpoint when service not initialized."""
        messages = {
            "messages": [
                {
                    "article_id": "article_1",
                    "canonical_url": "https://example.com/1",
                    "title": "Test Article 1",
                    "body": "This is a test article body with sufficient content.",
                    "url": "https://example.com/1",
                    "source": "test_source",
                    "published_at": "2025-11-02T10:00:00Z",
                    "language": "en",
                    "crawled_at": "2025-11-02T11:00:00Z",
                    "checksum": "abc123",
                    "validation_score": 0.8,
                    "schema_version": "1.0.0",
                    "ingest_job_id": "job_123",
                    "publisher_id": "pub_123",
                    "extraction_method": "rss",
                },
            ]
        }

        response = client.post("/batch/validate", json=messages)

        assert response.status_code == 503

