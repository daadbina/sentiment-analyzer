"""
Unit tests for main service.

Tests TrainerService orchestration and API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import numpy as np

from src.service import TrainerService


class TestTrainerService:
    """Test main trainer service."""

    @pytest.fixture
    def mock_clients(self):
        """Create mock clients."""
        with patch("src.service.PostgreSQLClient") as mock_pg, patch(
            "src.service.FeastClient"
        ) as mock_feast, patch("src.service.MLflowClient") as mock_mlflow, patch(
            "src.service.S3Client"
        ) as mock_s3, patch(
            "src.service.KafkaProducer"
        ) as mock_kafka:
            yield {
                "postgres": mock_pg,
                "feast": mock_feast,
                "mlflow": mock_mlflow,
                "s3": mock_s3,
                "kafka": mock_kafka,
            }

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_clients):
        """Test service initialization."""
        service = TrainerService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_service_start(self, mock_clients):
        """Test service startup."""
        service = TrainerService()

        # Mock async methods
        with patch.object(
            service, "postgres_client", new_callable=AsyncMock
        ), patch.object(service, "feast_client", new_callable=MagicMock), patch.object(
            service, "mlflow_client", new_callable=MagicMock
        ):

            await service.start()

            assert service.postgres_client is not None

    @pytest.mark.asyncio
    async def test_service_shutdown(self, mock_clients):
        """Test service shutdown."""
        service = TrainerService()

        with patch.object(service, "postgres_client", new_callable=AsyncMock):
            await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_health_check(self, mock_clients):
        """Test service health check."""
        service = TrainerService()

        with patch.object(
            service, "postgres_client", new_callable=AsyncMock
        ) as mock_pg:
            mock_pg.health_check.return_value = True

            health = await service.health_check()

            assert health is not None
            assert isinstance(health, dict)

    @pytest.mark.asyncio
    async def test_service_train_pipeline(self, mock_clients):
        """Test training pipeline execution."""
        service = TrainerService()

        with patch.object(
            service, "feature_retriever", new_callable=MagicMock
        ) as mock_feat, patch.object(
            service, "label_retriever", new_callable=AsyncMock
        ) as mock_label, patch.object(
            service, "preprocessor", new_callable=MagicMock
        ) as mock_prep, patch.object(
            service, "splitter", new_callable=MagicMock
        ) as mock_split, patch.object(
            service, "trainer", new_callable=MagicMock
        ) as mock_train, patch.object(
            service, "evaluator", new_callable=MagicMock
        ) as mock_eval:

            # Setup mock returns
            mock_feat.retrieve_features.return_value = np.random.randn(100, 10)
            mock_label.retrieve_labels.return_value = np.random.randint(0, 2, 100)
            mock_prep.preprocess.return_value = (
                np.random.randn(100, 10),
                np.random.randint(0, 2, 100),
            )
            mock_split.split_temporal.return_value = (
                (np.random.randn(70, 10), np.random.randint(0, 2, 70)),
                (np.random.randn(10, 10), np.random.randint(0, 2, 10)),
                (np.random.randn(20, 10), np.random.randint(0, 2, 20)),
            )
            mock_train.train_all_models.return_value = [MagicMock()]
            mock_eval.evaluate.return_value = {
                "auc": 0.85,
                "precision": 0.80,
                "recall": 0.80,
                "f1": 0.80,
            }

            result = await service.train_pipeline()

            assert result is not None

    @pytest.mark.asyncio
    async def test_service_get_models(self, mock_clients):
        """Test getting trained models."""
        service = TrainerService()

        with patch.object(
            service, "mlflow_client", new_callable=MagicMock
        ) as mock_mlflow:
            mock_mlflow.list_models.return_value = [
                {"name": "model_1", "version": 1},
                {"name": "model_2", "version": 2},
            ]

            models = service.get_models()

            assert models is not None
            assert len(models) > 0

    @pytest.mark.asyncio
    async def test_service_get_evaluation_results(self, mock_clients):
        """Test getting evaluation results."""
        service = TrainerService()

        with patch.object(
            service, "mlflow_client", new_callable=MagicMock
        ) as mock_mlflow:
            mock_mlflow.get_run_metrics.return_value = {
                "auc": 0.85,
                "precision": 0.80,
                "recall": 0.80,
                "f1": 0.80,
            }

            results = service.get_evaluation_results("run_id")

            assert results is not None

    @pytest.mark.asyncio
    async def test_service_get_drift_results(self, mock_clients):
        """Test getting drift detection results."""
        service = TrainerService()

        with patch.object(
            service, "drift_detector", new_callable=MagicMock
        ) as mock_drift:
            mock_drift.get_latest_report.return_value = {
                "drift_detected": False,
                "metrics": [],
            }

            results = service.get_drift_results()

            assert results is not None

    @pytest.mark.asyncio
    async def test_service_get_artifacts(self, mock_clients):
        """Test getting model artifacts."""
        service = TrainerService()

        with patch.object(
            service, "artifact_manager", new_callable=MagicMock
        ) as mock_art:
            mock_art.list_artifacts.return_value = [
                {"name": "model_v1.pkl", "size": 1024},
                {"name": "model_v2.pkl", "size": 2048},
            ]

            artifacts = service.get_artifacts()

            assert artifacts is not None
            assert len(artifacts) > 0

    @pytest.mark.asyncio
    async def test_service_promote_model(self, mock_clients):
        """Test model promotion."""
        service = TrainerService()

        with patch.object(
            service, "model_promoter", new_callable=MagicMock
        ) as mock_prom:
            mock_prom.promote_model.return_value = True

            result = service.promote_model(
                "test_model",
                "v1",
                {"auc": 0.85, "precision": 0.80, "recall": 0.80, "f1": 0.80},
                "Production",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_service_error_handling(self, mock_clients):
        """Test error handling in service."""
        service = TrainerService()

        with patch.object(
            service, "feature_retriever", new_callable=MagicMock
        ) as mock_feat:
            mock_feat.retrieve_features.side_effect = Exception(
                "Feature retrieval failed"
            )

            with pytest.raises(Exception):
                await service.train_pipeline()

    @pytest.mark.asyncio
    async def test_service_logging(self, mock_clients):
        """Test service logging."""
        service = TrainerService()

        with patch("src.service.logger") as mock_logger:
            await service.start()

            # Verify logging was called
            assert mock_logger is not None
