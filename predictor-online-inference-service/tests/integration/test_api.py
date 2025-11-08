"""
Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.app import create_app
from src.api.routes import set_dependencies


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for testing."""
    return {
        "feast_client": MagicMock(),
        "mlflow_client": MagicMock(),
        "redis_client": MagicMock(),
        "postgres_client": MagicMock(),
        "kafka_producer": MagicMock(),
        "feature_fetcher": MagicMock(),
        "feature_validator": MagicMock(),
        "model_manager": MagicMock(),
        "batch_predictor": MagicMock(),
    }


@pytest.fixture
def client(mock_dependencies):
    """Create test client with mocked dependencies."""
    app = create_app()
    set_dependencies(**mock_dependencies)
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    def test_health_check_success(self, client, mock_dependencies):
        """Test health check returns healthy status."""
        # Mock health checks
        mock_dependencies["mlflow_client"].health_check = AsyncMock(return_value=True)
        mock_dependencies["feast_client"].health_check = AsyncMock(return_value=True)
        mock_dependencies["redis_client"].health_check = AsyncMock(return_value=True)
        mock_dependencies["postgres_client"].health_check = AsyncMock(return_value=True)
        mock_dependencies["kafka_producer"].health_check = AsyncMock(return_value=True)
        
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert "dependencies" in data
    
    def test_health_check_unhealthy_dependency(self, client, mock_dependencies):
        """Test health check with unhealthy dependency."""
        # Mock one unhealthy dependency
        mock_dependencies["mlflow_client"].health_check = AsyncMock(return_value=False)
        mock_dependencies["feast_client"].health_check = AsyncMock(return_value=True)
        mock_dependencies["redis_client"].health_check = AsyncMock(return_value=True)
        mock_dependencies["postgres_client"].health_check = AsyncMock(return_value=True)
        mock_dependencies["kafka_producer"].health_check = AsyncMock(return_value=True)
        
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["mlflow"] == "unhealthy"


class TestPredictEndpoint:
    """Tests for /predict endpoint."""
    
    def test_predict_success(self, client, mock_dependencies):
        """Test successful prediction."""
        # Mock prediction
        mock_dependencies["batch_predictor"].predict_single = AsyncMock(
            return_value={
                "group_id": "group_123",
                "domain": "btc",
                "prediction_probability": 0.85,
                "prediction_confidence": 0.70,
                "model_version": "v1.0.0",
                "predicted_at": "2025-11-07T12:00:00Z",
                "trace_id": "01JCABCDEFGHIJKLMNOPQRSTUV",
            }
        )
        
        response = client.post(
            "/api/v1/predict",
            json={"group_id": "group_123", "domain": "btc"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["group_id"] == "group_123"
        assert data["domain"] == "btc"
        assert data["prediction_probability"] == 0.85
        assert data["model_version"] == "v1.0.0"
    
    def test_predict_missing_group_id(self, client):
        """Test prediction with missing group_id."""
        response = client.post(
            "/api/v1/predict",
            json={"domain": "btc"},
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_predict_missing_domain(self, client):
        """Test prediction with missing domain."""
        response = client.post(
            "/api/v1/predict",
            json={"group_id": "group_123"},
        )
        
        assert response.status_code == 422  # Validation error


class TestBatchPredictEndpoint:
    """Tests for /predict/batch endpoint."""
    
    def test_batch_predict_success(self, client, mock_dependencies):
        """Test successful batch prediction."""
        # Mock batch prediction
        mock_dependencies["batch_predictor"].predict_batch = AsyncMock(
            return_value=[
                {
                    "group_id": "group_123",
                    "domain": "btc",
                    "prediction_probability": 0.85,
                    "prediction_confidence": 0.70,
                    "model_version": "v1.0.0",
                    "predicted_at": "2025-11-07T12:00:00Z",
                    "trace_id": "01JCABCDEFGHIJKLMNOPQRSTUV",
                },
                {
                    "group_id": "group_456",
                    "domain": "btc",
                    "prediction_probability": 0.65,
                    "prediction_confidence": 0.60,
                    "model_version": "v1.0.0",
                    "predicted_at": "2025-11-07T12:00:00Z",
                    "trace_id": "01JCABCDEFGHIJKLMNOPQRSTUV",
                },
            ]
        )
        
        response = client.post(
            "/api/v1/predict/batch",
            json={"group_ids": ["group_123", "group_456"], "domain": "btc"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["predictions"]) == 2
        assert data["predictions"][0]["group_id"] == "group_123"
        assert data["predictions"][1]["group_id"] == "group_456"
    
    def test_batch_predict_empty_list(self, client):
        """Test batch prediction with empty group_ids list."""
        response = client.post(
            "/api/v1/predict/batch",
            json={"group_ids": [], "domain": "btc"},
        )
        
        assert response.status_code == 422  # Validation error


class TestModelMetadataEndpoint:
    """Tests for /model/metadata endpoint."""
    
    def test_get_model_metadata_success(self, client, mock_dependencies):
        """Test getting model metadata."""
        # Mock model metadata
        mock_dependencies["model_manager"].get_model_metadata = AsyncMock(
            return_value={
                "model_name": "predictor_model",
                "model_version": "v1.0.0",
                "stage": "Production",
                "created_at": "2025-11-01T00:00:00Z",
                "description": "Event realization prediction model",
                "tags": {
                    "framework": "xgboost",
                    "accuracy": "0.85",
                },
            }
        )
        
        response = client.get("/api/v1/model/metadata")
        
        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "predictor_model"
        assert data["model_version"] == "v1.0.0"
        assert data["stage"] == "Production"

