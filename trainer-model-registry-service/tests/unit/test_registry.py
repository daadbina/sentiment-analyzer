"""
Unit tests for model registry and promotion.

Tests MLflow client, model promoter, and artifact manager.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.registry.model_promoter import ModelPromoter
from src.registry.artifact_manager import ArtifactManager


class TestModelPromoter:
    """Test model promotion logic."""

    def test_promoter_initialization(self):
        """Test promoter initialization."""
        promoter = ModelPromoter()
        assert promoter is not None

    def test_promoter_validate_metrics_pass(self):
        """Test metric validation with passing metrics."""
        promoter = ModelPromoter()

        metrics = {"auc": 0.80, "precision": 0.75, "recall": 0.75, "f1": 0.75}

        is_valid = promoter._validate_metrics(metrics, stage="Staging")

        assert is_valid is True

    def test_promoter_validate_metrics_fail_auc(self):
        """Test metric validation with low AUC."""
        promoter = ModelPromoter()

        metrics = {
            "auc": 0.70,  # Below threshold
            "precision": 0.75,
            "recall": 0.75,
            "f1": 0.75,
        }

        is_valid = promoter._validate_metrics(metrics, stage="Staging")

        assert is_valid is False

    def test_promoter_validate_metrics_fail_precision(self):
        """Test metric validation with low precision."""
        promoter = ModelPromoter()

        metrics = {
            "auc": 0.80,
            "precision": 0.65,  # Below threshold
            "recall": 0.75,
            "f1": 0.75,
        }

        is_valid = promoter._validate_metrics(metrics, stage="Staging")

        assert is_valid is False

    def test_promoter_validate_metrics_fail_recall(self):
        """Test metric validation with low recall."""
        promoter = ModelPromoter()

        metrics = {
            "auc": 0.80,
            "precision": 0.75,
            "recall": 0.65,  # Below threshold
            "f1": 0.75,
        }

        is_valid = promoter._validate_metrics(metrics, stage="Staging")

        assert is_valid is False

    @patch("src.registry.model_promoter.MLflowClient")
    def test_promoter_promote_model_to_staging(self, mock_mlflow):
        """Test promoting model to Staging."""
        mock_client = MagicMock()
        mock_mlflow.return_value = mock_client

        promoter = ModelPromoter()

        metrics = {"auc": 0.80, "precision": 0.75, "recall": 0.75, "f1": 0.75}

        result = promoter.promote_model("test_model", "v1", metrics, stage="Staging")

        assert result is not None

    @patch("src.registry.model_promoter.MLflowClient")
    def test_promoter_promote_model_to_production(self, mock_mlflow):
        """Test promoting model to Production."""
        mock_client = MagicMock()
        mock_mlflow.return_value = mock_client

        promoter = ModelPromoter()

        metrics = {"auc": 0.85, "precision": 0.80, "recall": 0.80, "f1": 0.80}

        result = promoter.promote_model("test_model", "v2", metrics, stage="Production")

        assert result is not None

    def test_promoter_stage_transitions(self):
        """Test valid stage transitions."""
        promoter = ModelPromoter()

        # None -> Staging is valid
        assert promoter._is_valid_transition(None, "Staging") is True

        # Staging -> Production is valid
        assert promoter._is_valid_transition("Staging", "Production") is True

        # Production -> Staging is valid (rollback)
        assert promoter._is_valid_transition("Production", "Staging") is True

    def test_promoter_invalid_stage_transitions(self):
        """Test invalid stage transitions."""
        promoter = ModelPromoter()

        # Production -> None is invalid
        assert promoter._is_valid_transition("Production", None) is False


class TestArtifactManager:
    """Test artifact management."""

    def test_artifact_manager_initialization(self):
        """Test artifact manager initialization."""
        manager = ArtifactManager()
        assert manager is not None

    @patch("src.registry.artifact_manager.S3Client")
    def test_artifact_manager_upload(self, mock_s3):
        """Test artifact upload."""
        mock_client = MagicMock()
        mock_s3.return_value = mock_client

        manager = ArtifactManager()

        artifact_data = b"model_data"
        artifact_path = "s3://bucket/model.pkl"

        result = manager.upload_artifact(artifact_data, artifact_path)

        assert result is not None

    @patch("src.registry.artifact_manager.S3Client")
    def test_artifact_manager_download(self, mock_s3):
        """Test artifact download."""
        mock_client = MagicMock()
        mock_client.download.return_value = b"model_data"
        mock_s3.return_value = mock_client

        manager = ArtifactManager()

        artifact_path = "s3://bucket/model.pkl"

        result = manager.download_artifact(artifact_path)

        assert result is not None
        assert isinstance(result, bytes)

    def test_artifact_manager_compute_checksum(self):
        """Test checksum computation."""
        manager = ArtifactManager()

        artifact_data = b"model_data"

        checksum = manager.compute_checksum(artifact_data)

        assert checksum is not None
        assert isinstance(checksum, str)
        assert len(checksum) > 0

    def test_artifact_manager_validate_checksum(self):
        """Test checksum validation."""
        manager = ArtifactManager()

        artifact_data = b"model_data"
        checksum = manager.compute_checksum(artifact_data)

        is_valid = manager.validate_checksum(artifact_data, checksum)

        assert is_valid is True

    def test_artifact_manager_validate_checksum_fail(self):
        """Test checksum validation failure."""
        manager = ArtifactManager()

        artifact_data = b"model_data"
        wrong_checksum = "wrong_checksum"

        is_valid = manager.validate_checksum(artifact_data, wrong_checksum)

        assert is_valid is False

    @patch("src.registry.artifact_manager.S3Client")
    def test_artifact_manager_versioning(self, mock_s3):
        """Test artifact versioning."""
        mock_client = MagicMock()
        mock_s3.return_value = mock_client

        manager = ArtifactManager()

        artifact_data = b"model_data"

        # Upload v1
        path_v1 = manager.upload_artifact(artifact_data, "s3://bucket/model_v1.pkl")

        # Upload v2
        path_v2 = manager.upload_artifact(artifact_data, "s3://bucket/model_v2.pkl")

        assert path_v1 is not None
        assert path_v2 is not None
        assert path_v1 != path_v2

    @patch("src.registry.artifact_manager.S3Client")
    def test_artifact_manager_metadata(self, mock_s3):
        """Test artifact metadata tracking."""
        mock_client = MagicMock()
        mock_s3.return_value = mock_client

        manager = ArtifactManager()

        artifact_data = b"model_data"
        metadata = {"model_name": "xgboost", "version": "v1", "auc": 0.85}

        result = manager.upload_artifact_with_metadata(
            artifact_data, "s3://bucket/model.pkl", metadata
        )

        assert result is not None

    def test_artifact_manager_retry_logic(self):
        """Test retry logic for failed uploads."""
        manager = ArtifactManager()

        # Mock S3 client with retry
        with patch("src.registry.artifact_manager.S3Client") as mock_s3:
            mock_client = MagicMock()
            mock_client.upload.side_effect = [
                Exception("Connection error"),
                Exception("Connection error"),
                "success",
            ]
            mock_s3.return_value = mock_client

            artifact_data = b"model_data"

            # Should retry and eventually succeed
            result = manager.upload_artifact_with_retry(
                artifact_data, "s3://bucket/model.pkl", max_retries=3
            )

            assert result is not None
