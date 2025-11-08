"""
Unit tests for ModelLoader.

Tests lazy loading, validation, fallback logic, and warmup functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pickle
import os
import tempfile

from src.models.model_loader import ModelLoader
from src.exceptions import ModelLoadError
from src.config import MLflowConfig


@pytest.fixture
def mlflow_config():
    """Create MLflow configuration for testing."""
    return MLflowConfig(
        tracking_uri="http://localhost:5000",
        model_name="test_model",
        model_version="1",
        model_stage="Production",
        baseline_model_path="/tmp/baseline_model.pkl"
    )


@pytest.fixture
def metrics_mock():
    """Create metrics collector mock."""
    metrics = Mock()
    metrics.record_model_load_time = Mock()
    metrics.increment_model_load_failures = Mock()
    return metrics


@pytest.fixture
def model_loader(mlflow_config, metrics_mock):
    """Create ModelLoader instance for testing."""
    return ModelLoader(config=mlflow_config, metrics=metrics_mock)


@pytest.fixture
def mock_model():
    """Create a mock model with predict method."""
    model = Mock()
    model.predict = Mock(return_value=[0.8])
    return model


class TestModelLoader:
    """Test suite for ModelLoader."""
    
    @pytest.mark.asyncio
    async def test_lazy_load_model_first_load(self, model_loader, mock_model, metrics_mock):
        """Test lazy loading model for the first time."""
        with patch('mlflow.pyfunc.load_model', return_value=mock_model):
            loaded_model = await model_loader.lazy_load_model()
            
            assert loaded_model is not None
            assert loaded_model == mock_model
            assert model_loader._current_model == mock_model
            assert model_loader._current_version == "1"
            metrics_mock.record_model_load_time.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lazy_load_model_already_loaded(self, model_loader, mock_model):
        """Test lazy loading when model is already loaded."""
        model_loader._current_model = mock_model
        model_loader._current_version = "1"
        
        loaded_model = await model_loader.lazy_load_model()
        
        assert loaded_model == mock_model
        # Should not load again
    
    @pytest.mark.asyncio
    async def test_lazy_load_model_version_changed(self, model_loader, mock_model, metrics_mock):
        """Test lazy loading when model version changes."""
        old_model = Mock()
        model_loader._current_model = old_model
        model_loader._current_version = "0"
        
        with patch('mlflow.pyfunc.load_model', return_value=mock_model):
            loaded_model = await model_loader.lazy_load_model(version="1")
            
            assert loaded_model == mock_model
            assert model_loader._current_version == "1"
            metrics_mock.record_model_load_time.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lazy_load_model_failure(self, model_loader, metrics_mock):
        """Test lazy loading when model load fails."""
        with patch('mlflow.pyfunc.load_model', side_effect=Exception("Load failed")):
            with pytest.raises(ModelLoadError) as exc_info:
                await model_loader.lazy_load_model()
            
            assert "Failed to load model" in str(exc_info.value)
            metrics_mock.increment_model_load_failures.assert_called_once()
    
    def test_validate_model_success(self, model_loader, mock_model):
        """Test model validation with valid model."""
        is_valid = model_loader.validate_model(mock_model)
        assert is_valid is True
    
    def test_validate_model_no_predict_method(self, model_loader):
        """Test model validation with model missing predict method."""
        invalid_model = Mock(spec=[])  # No predict method
        
        is_valid = model_loader.validate_model(invalid_model)
        assert is_valid is False
    
    def test_validate_model_none(self, model_loader):
        """Test model validation with None."""
        is_valid = model_loader.validate_model(None)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_warmup_model_success(self, model_loader, mock_model):
        """Test model warmup with successful prediction."""
        model_loader._current_model = mock_model
        
        await model_loader.warmup_model()
        
        mock_model.predict.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_warmup_model_no_model(self, model_loader):
        """Test model warmup when no model is loaded."""
        # Should not raise exception
        await model_loader.warmup_model()
    
    @pytest.mark.asyncio
    async def test_warmup_model_failure(self, model_loader, mock_model):
        """Test model warmup when prediction fails."""
        model_loader._current_model = mock_model
        mock_model.predict.side_effect = Exception("Prediction failed")
        
        # Should not raise exception, just log warning
        await model_loader.warmup_model()
    
    @pytest.mark.asyncio
    async def test_fallback_to_baseline_model_success(self, model_loader, mock_model):
        """Test fallback to baseline model."""
        # Create temporary baseline model file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
            pickle.dump(mock_model, f)
            baseline_path = f.name
        
        try:
            model_loader.config.baseline_model_path = baseline_path
            
            baseline_model = await model_loader.fallback_to_baseline_model()
            
            assert baseline_model is not None
            assert model_loader._current_model == baseline_model
            assert model_loader._current_version == "baseline"
        finally:
            os.unlink(baseline_path)
    
    @pytest.mark.asyncio
    async def test_fallback_to_baseline_model_file_not_found(self, model_loader):
        """Test fallback when baseline model file doesn't exist."""
        model_loader.config.baseline_model_path = "/nonexistent/path.pkl"
        
        with pytest.raises(ModelLoadError) as exc_info:
            await model_loader.fallback_to_baseline_model()
        
        assert "Baseline model not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_fallback_to_baseline_model_invalid_pickle(self, model_loader):
        """Test fallback when baseline model file is invalid."""
        # Create temporary invalid pickle file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pkl') as f:
            f.write("invalid pickle data")
            invalid_path = f.name
        
        try:
            model_loader.config.baseline_model_path = invalid_path
            
            with pytest.raises(ModelLoadError) as exc_info:
                await model_loader.fallback_to_baseline_model()
            
            assert "Failed to load baseline model" in str(exc_info.value)
        finally:
            os.unlink(invalid_path)
    
    def test_get_current_model(self, model_loader, mock_model):
        """Test getting current model."""
        model_loader._current_model = mock_model
        
        current = model_loader.get_current_model()
        assert current == mock_model
    
    def test_get_current_version(self, model_loader):
        """Test getting current version."""
        model_loader._current_version = "2"
        
        version = model_loader.get_current_version()
        assert version == "2"
    
    @pytest.mark.asyncio
    async def test_lazy_load_with_fallback_on_failure(self, model_loader, mock_model, metrics_mock):
        """Test lazy loading with automatic fallback on failure."""
        # Create temporary baseline model file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
            pickle.dump(mock_model, f)
            baseline_path = f.name
        
        try:
            model_loader.config.baseline_model_path = baseline_path
            
            # Mock MLflow load to fail
            with patch('mlflow.pyfunc.load_model', side_effect=Exception("MLflow unavailable")):
                # Should fall back to baseline
                with pytest.raises(ModelLoadError):
                    await model_loader.lazy_load_model()
                
                metrics_mock.increment_model_load_failures.assert_called()
        finally:
            os.unlink(baseline_path)
    
    @pytest.mark.asyncio
    async def test_concurrent_loads(self, model_loader, mock_model):
        """Test that concurrent loads don't cause issues."""
        import asyncio
        
        with patch('mlflow.pyfunc.load_model', return_value=mock_model):
            # Simulate concurrent loads
            tasks = [model_loader.lazy_load_model() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed and return the same model
            for result in results:
                assert result == mock_model
            
            # Model should only be loaded once
            assert model_loader._current_model == mock_model

