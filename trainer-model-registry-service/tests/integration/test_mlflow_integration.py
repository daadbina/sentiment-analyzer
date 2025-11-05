"""
Integration tests for MLflow integration.

Tests MLflow model registry operations.
"""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from src.clients.mlflow_client import MLflowClient
from src.registry.model_promoter import ModelPromoter
from src.registry.artifact_manager import ArtifactManager


class TestMLflowIntegration:
    """Test MLflow integration."""

    @pytest.fixture
    def mock_mlflow(self):
        """Create mock MLflow."""
        with patch('src.clients.mlflow_client.mlflow') as mock:
            yield mock

    def test_mlflow_client_initialization(self, mock_mlflow):
        """Test MLflow client initialization."""
        mock_mlflow.set_tracking_uri = MagicMock()
        
        client = MLflowClient()
        
        assert client is not None

    def test_mlflow_create_experiment(self, mock_mlflow):
        """Test creating MLflow experiment."""
        mock_mlflow.create_experiment.return_value = 'exp_123'
        
        client = MLflowClient()
        
        exp_id = client.create_experiment('test_experiment')
        
        assert exp_id == 'exp_123'

    def test_mlflow_start_run(self, mock_mlflow):
        """Test starting MLflow run."""
        mock_run = MagicMock()
        mock_run.info.run_id = 'run_123'
        mock_mlflow.start_run.return_value = mock_run
        
        client = MLflowClient()
        
        run = client.start_run('exp_123')
        
        assert run is not None

    def test_mlflow_log_metrics(self, mock_mlflow):
        """Test logging metrics to MLflow."""
        mock_mlflow.log_metrics = MagicMock()
        
        client = MLflowClient()
        
        metrics = {
            'auc': 0.85,
            'precision': 0.80,
            'recall': 0.80,
            'f1': 0.80,
        }
        
        client.log_metrics(metrics)
        
        mock_mlflow.log_metrics.assert_called_once()

    def test_mlflow_log_params(self, mock_mlflow):
        """Test logging parameters to MLflow."""
        mock_mlflow.log_params = MagicMock()
        
        client = MLflowClient()
        
        params = {
            'max_depth': 8,
            'learning_rate': 0.1,
            'n_estimators': 200,
        }
        
        client.log_params(params)
        
        mock_mlflow.log_params.assert_called_once()

    def test_mlflow_log_model(self, mock_mlflow):
        """Test logging model to MLflow."""
        mock_mlflow.log_model = MagicMock()
        
        client = MLflowClient()
        
        model = MagicMock()
        client.log_model(model, 'test_model')
        
        mock_mlflow.log_model.assert_called_once()

    def test_mlflow_register_model(self, mock_mlflow):
        """Test registering model in MLflow."""
        mock_version = MagicMock()
        mock_version.version = 1
        mock_mlflow.register_model.return_value = mock_version
        
        client = MLflowClient()
        
        result = client.register_model('runs:/abc123/model', 'test_model')
        
        assert result is not None
        assert result.version == 1

    def test_mlflow_transition_stage(self, mock_mlflow):
        """Test transitioning model stage."""
        mock_mlflow.transition_model_version_stage = MagicMock()
        
        client = MLflowClient()
        
        client.transition_model_stage('test_model', 1, 'Production')
        
        mock_mlflow.transition_model_version_stage.assert_called_once()

    def test_mlflow_get_model_version(self, mock_mlflow):
        """Test getting model version."""
        mock_version = MagicMock()
        mock_version.version = 1
        mock_version.stage = 'Production'
        mock_mlflow.get_model_version.return_value = mock_version
        
        client = MLflowClient()
        
        version = client.get_model_version('test_model', 1)
        
        assert version is not None
        assert version.stage == 'Production'

    def test_mlflow_list_models(self, mock_mlflow):
        """Test listing models."""
        mock_mlflow.search_registered_models.return_value = [
            MagicMock(name='model_1'),
            MagicMock(name='model_2'),
        ]
        
        client = MLflowClient()
        
        models = client.list_models()
        
        assert models is not None
        assert len(models) == 2

    def test_mlflow_model_promoter_integration(self, mock_mlflow):
        """Test model promoter with MLflow."""
        mock_mlflow.transition_model_version_stage = MagicMock()
        
        promoter = ModelPromoter()
        
        metrics = {
            'auc': 0.85,
            'precision': 0.80,
            'recall': 0.80,
            'f1': 0.80,
        }
        
        result = promoter.promote_model(
            'test_model',
            'v1',
            metrics,
            stage='Production'
        )
        
        assert result is not None

    def test_mlflow_artifact_logging(self, mock_mlflow):
        """Test artifact logging to MLflow."""
        mock_mlflow.log_artifact = MagicMock()
        
        client = MLflowClient()
        
        client.log_artifact('/path/to/artifact', 'artifacts')
        
        mock_mlflow.log_artifact.assert_called_once()

    def test_mlflow_end_run(self, mock_mlflow):
        """Test ending MLflow run."""
        mock_mlflow.end_run = MagicMock()
        
        client = MLflowClient()
        
        client.end_run()
        
        mock_mlflow.end_run.assert_called_once()

    def test_mlflow_get_run_metrics(self, mock_mlflow):
        """Test getting run metrics."""
        mock_mlflow.get_run.return_value = MagicMock(
            data=MagicMock(metrics={'auc': 0.85, 'precision': 0.80})
        )
        
        client = MLflowClient()
        
        metrics = client.get_run_metrics('run_123')
        
        assert metrics is not None

    def test_mlflow_search_runs(self, mock_mlflow):
        """Test searching runs."""
        mock_mlflow.search_runs.return_value = [
            MagicMock(run_id='run_1'),
            MagicMock(run_id='run_2'),
        ]
        
        client = MLflowClient()
        
        runs = client.search_runs('exp_123')
        
        assert runs is not None
        assert len(runs) == 2

    def test_mlflow_model_versioning(self, mock_mlflow):
        """Test model versioning in MLflow."""
        mock_v1 = MagicMock(version=1, stage='Staging')
        mock_v2 = MagicMock(version=2, stage='Production')
        mock_mlflow.search_model_versions.return_value = [mock_v1, mock_v2]
        
        client = MLflowClient()
        
        versions = client.search_model_versions('test_model')
        
        assert versions is not None
        assert len(versions) == 2

    def test_mlflow_artifact_manager_integration(self, mock_mlflow):
        """Test artifact manager with MLflow."""
        with patch('src.registry.artifact_manager.S3Client') as mock_s3:
            mock_s3_client = MagicMock()
            mock_s3.return_value = mock_s3_client
            
            manager = ArtifactManager()
            
            artifact_data = b'model_data'
            result = manager.upload_artifact(artifact_data, 's3://bucket/model.pkl')
            
            assert result is not None

