"""
Integration tests for MLflow integration.

Tests model loading, version management, and end-to-end workflows.
Requires MLflow server to be running for full integration tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.clients.mlflow_client import MLflowClient
from src.config import MLflowConfig
from src.exceptions import ModelLoadError


@pytest.fixture
def mlflow_config():
    """Create MLflow configuration for testing."""
    return MLflowConfig(
        tracking_uri="http://localhost:5000",
        btc_model_name="btc_prediction_xgboost_regressor",
        btc_model_version="14",
        conflict_model_name="conflict_prediction_random_forest",
        conflict_model_version="18",
        model_version="1",
        model_stage="Production",
        fallback_model_version=None,
        model_load_timeout_seconds=30,
        auto_select_best_model=False,
        model_selection_metric="f1",
    )


@pytest.fixture
def mlflow_client(mlflow_config):
    """Create MLflowClient instance."""
    return MLflowClient(config=mlflow_config)


class TestMLflowConnection:
    """Test MLflow connection and health checks."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_success(self, mlflow_client):
        """Test successful connection to MLflow."""
        with patch("mlflow.tracking.MlflowClient") as mock_client:
            mock_client.return_value = MagicMock()
            await mlflow_client.connect()
            assert mlflow_client._client is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_failure(self, mlflow_client):
        """Test connection failure handling."""
        with patch("mlflow.tracking.MlflowClient", side_effect=Exception("Connection failed")):
            with pytest.raises(ModelLoadError):
                await mlflow_client.connect()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_connected(self, mlflow_client):
        """Test health check when connected."""
        mock_client = MagicMock()
        mock_client.search_registered_models.return_value = []
        mlflow_client._client = mock_client
        
        result = await mlflow_client.health_check()
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_not_connected(self, mlflow_client):
        """Test health check when not connected."""
        result = await mlflow_client.health_check()
        assert result is False


class TestModelLoading:
    """Test model loading from MLflow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_load_model_by_stage(self, mlflow_client):
        """Test loading model by stage."""
        mock_client = MagicMock()
        mock_model = MagicMock()

        mlflow_client._client = mock_client

        with patch("mlflow.pyfunc.load_model", return_value=mock_model):
            model, version = await mlflow_client.load_model(stage="Production")
            assert model is not None
            assert version is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_load_model_by_version(self, mlflow_client):
        """Test loading model by version."""
        mock_client = MagicMock()
        mock_model = MagicMock()

        mlflow_client._client = mock_client

        with patch("mlflow.pyfunc.load_model", return_value=mock_model):
            model, version = await mlflow_client.load_model(model_version="5")
            assert model is not None
            assert version == "5"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_load_model_not_found(self, mlflow_client):
        """Test loading non-existent model."""
        mock_client = MagicMock()
        mlflow_client._client = mock_client
        
        with patch("mlflow.pyfunc.load_model", side_effect=Exception("Model not found")):
            with pytest.raises(ModelLoadError):
                await mlflow_client.load_model(stage="Production")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_load_model_not_connected(self, mlflow_client):
        """Test loading model when not connected."""
        with pytest.raises(ModelLoadError):
            await mlflow_client.load_model(stage="Production")


class TestModelMetadata:
    """Test model metadata retrieval."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_model_metadata_success(self, mlflow_client):
        """Test successful metadata retrieval."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.name = "sentiment_predictor"
        mock_version.version = "5"
        mock_version.current_stage = "Production"
        mock_version.creation_timestamp = 1234567890000
        mock_version.description = "Test model"
        mock_version.tags = {"accuracy": "0.95"}
        
        mock_client.get_latest_versions.return_value = [mock_version]
        mlflow_client._client = mock_client
        
        metadata = await mlflow_client.get_model_metadata(stage="Production")
        
        assert metadata["name"] == "sentiment_predictor"
        assert metadata["version"] == "5"
        assert metadata["stage"] == "Production"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_model_metadata_not_found(self, mlflow_client):
        """Test metadata retrieval for non-existent model."""
        mock_client = MagicMock()
        mock_client.get_latest_versions.return_value = []
        mlflow_client._client = mock_client
        
        with pytest.raises(ModelLoadError):
            await mlflow_client.get_model_metadata(stage="Production")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_model_metadata_not_connected(self, mlflow_client):
        """Test metadata retrieval when not connected."""
        with pytest.raises(ModelLoadError):
            await mlflow_client.get_model_metadata(stage="Production")


class TestModelVersionManagement:
    """Test model version management."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_model_versions(self, mlflow_client):
        """Test listing all model versions."""
        mock_client = MagicMock()
        mock_versions = [
            MagicMock(version="1", current_stage="Archived"),
            MagicMock(version="2", current_stage="Staging"),
            MagicMock(version="3", current_stage="Production"),
        ]
        
        mock_client.search_model_versions.return_value = mock_versions
        mlflow_client._client = mock_client
        
        versions = await mlflow_client.list_model_versions()
        
        assert len(versions) == 3
        assert versions[0].version == "1"
        assert versions[2].current_stage == "Production"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_latest_version_by_stage(self, mlflow_client):
        """Test getting latest version for a stage."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.version = "5"
        mock_version.current_stage = "Production"
        
        mock_client.get_latest_versions.return_value = [mock_version]
        mlflow_client._client = mock_client
        
        version = await mlflow_client.get_latest_version(stage="Production")
        
        assert version.version == "5"
        assert version.current_stage == "Production"


class TestEndToEndWorkflow:
    """Test end-to-end MLflow workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_load_predict_workflow(self, mlflow_client):
        """Test complete workflow: connect -> load -> predict."""
        mock_client = MagicMock()
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.75, 0.85]
        
        with patch("mlflow.tracking.MlflowClient", return_value=mock_client):
            await mlflow_client.connect()
        
        with patch("mlflow.pyfunc.load_model", return_value=mock_model):
            model, version = await mlflow_client.load_model(stage="Production")

        # Make prediction
        predictions = model.predict([[0.5, 0.8], [0.6, 0.7]])

        assert len(predictions) == 2
        assert predictions[0] == 0.75
        assert predictions[1] == 0.85

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_model_version_switching(self, mlflow_client):
        """Test switching between model versions."""
        mock_client = MagicMock()
        mlflow_client._client = mock_client
        
        # Load version 1
        mock_model_v1 = MagicMock()
        mock_model_v1.predict.return_value = [0.70]
        
        with patch("mlflow.pyfunc.load_model", return_value=mock_model_v1):
            model_v1, version_v1 = await mlflow_client.load_model(model_version="1")
            pred_v1 = model_v1.predict([[0.5, 0.8]])

        # Load version 2
        mock_model_v2 = MagicMock()
        mock_model_v2.predict.return_value = [0.85]

        with patch("mlflow.pyfunc.load_model", return_value=mock_model_v2):
            model_v2, version_v2 = await mlflow_client.load_model(model_version="2")
            pred_v2 = model_v2.predict([[0.5, 0.8]])

        # Verify different predictions
        assert pred_v1[0] != pred_v2[0]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_model_reload_on_version_change(self, mlflow_client):
        """Test model reload when version changes."""
        mock_client = MagicMock()
        mlflow_client._client = mock_client
        
        # Load initial model
        mock_model_1 = MagicMock()
        with patch("mlflow.pyfunc.load_model", return_value=mock_model_1):
            model_1 = await mlflow_client.load_model(stage="Production")
        
        # Simulate version change
        mock_model_2 = MagicMock()
        with patch("mlflow.pyfunc.load_model", return_value=mock_model_2):
            model_2 = await mlflow_client.load_model(stage="Production")
        
        # Models should be different instances
        assert model_1 is not model_2


class TestErrorHandling:
    """Test error handling in MLflow integration."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_network_timeout(self, mlflow_client):
        """Test handling of network timeout."""
        with patch("mlflow.tracking.MlflowClient", side_effect=TimeoutError("Timeout")):
            with pytest.raises(ModelLoadError):
                await mlflow_client.connect()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_model_format(self, mlflow_client):
        """Test handling of invalid model format."""
        mock_client = MagicMock()
        mlflow_client._client = mock_client
        
        with patch("mlflow.pyfunc.load_model", side_effect=Exception("Invalid format")):
            with pytest.raises(ModelLoadError):
                await mlflow_client.load_model(stage="Production")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_model_loads(self, mlflow_client):
        """Test concurrent model loading."""
        mock_client = MagicMock()
        mlflow_client._client = mock_client
        
        mock_model = MagicMock()
        
        with patch("mlflow.pyfunc.load_model", return_value=mock_model):
            # Load same model concurrently
            import asyncio
            results = await asyncio.gather(
                mlflow_client.load_model(stage="Production"),
                mlflow_client.load_model(stage="Production"),
                mlflow_client.load_model(stage="Production"),
            )
        
        assert len(results) == 3
        assert all(r is not None for r in results)

