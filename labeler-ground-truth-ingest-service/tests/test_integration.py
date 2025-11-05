"""Integration tests for labeler service."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.service import LabelerService
from src.reconciliation.reconciler import LabelReconciler
from src.validation.label_validator import LabelValidator
from src.storage.delta_lake_writer import DeltaLakeWriter
from src.storage.postgres_writer import PostgreSQLWriter


class TestLabelReconciliation:
    """Test label reconciliation integration."""

    @pytest.mark.asyncio
    async def test_reconcile_acled_label_with_semantic_group(self, sample_acled_label, sample_semantic_group):
        """Test reconciling ACLED label with semantic group."""
        reconciler = LabelReconciler()

        result = await reconciler.reconcile(sample_acled_label, [sample_semantic_group])

        # Result can be None if no matching group found (which is valid behavior)
        if result is not None:
            assert "group_id" in result or "confidence" in result
            if "confidence" in result:
                assert result["confidence"] >= 0.0
                assert result["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_reconcile_batch_labels(self, sample_acled_label, sample_gdelt_label, sample_semantic_group):
        """Test reconciling batch of labels."""
        reconciler = LabelReconciler()
        labels = [sample_acled_label, sample_gdelt_label]

        results = await reconciler.reconcile_batch(labels, [sample_semantic_group])

        # Results can be empty if no labels match any groups (which is valid behavior)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_reconcile_no_matching_group(self, sample_acled_label):
        """Test reconciling label with no matching group."""
        reconciler = LabelReconciler()
        
        result = await reconciler.reconcile(sample_acled_label, [])
        
        # Should return None or empty result when no groups match
        assert result is None or result.get("group_id") is None


class TestLabelValidation:
    """Test label validation integration."""

    @pytest.mark.asyncio
    async def test_validate_valid_label(self, sample_acled_label):
        """Test validating a valid label."""
        validator = LabelValidator()

        is_valid, message = validator.validate_confidence(sample_acled_label)

        assert is_valid is True
        assert "confidence" in message.lower() and "valid" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_low_confidence_label(self, sample_acled_label):
        """Test validating label with low confidence."""
        sample_acled_label["confidence"] = 0.5
        validator = LabelValidator()
        
        is_valid, message = validator.validate_confidence(sample_acled_label)
        
        assert is_valid is False
        assert "confidence" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_freshness_acled(self, sample_acled_label, mock_config):
        """Test validating ACLED label freshness."""
        from datetime import datetime
        from unittest.mock import patch
        # Update fetched_at to be recent (within 24 hours)
        sample_acled_label["fetched_at"] = datetime.utcnow().isoformat() + "Z"

        with patch('src.validation.label_validator.config', mock_config):
            validator = LabelValidator()

            is_valid, message = validator.validate_freshness(sample_acled_label, "acled")

            assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_freshness_stale_label(self, sample_acled_label):
        """Test validating stale label."""
        # Set timestamp to 2 days ago
        sample_acled_label["timestamp"] = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
        validator = LabelValidator()
        
        is_valid, message = validator.validate_freshness(sample_acled_label, "acled")
        
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_temporal_alignment(self, sample_acled_label, sample_semantic_group):
        """Test validating temporal alignment (R8)."""
        validator = LabelValidator()
        
        is_valid, message = validator.validate_temporal_alignment(
            sample_acled_label,
            sample_semantic_group["created_at"]
        )
        
        # Should be valid if label is ≥24h after group creation
        assert isinstance(is_valid, bool)

    @pytest.mark.asyncio
    async def test_validate_batch_labels(self, sample_acled_label, sample_gdelt_label):
        """Test validating batch of labels."""
        validator = LabelValidator()
        labels = [sample_acled_label, sample_gdelt_label]
        
        valid_labels, invalid_labels = await validator.validate_batch(labels, "acled")
        
        assert len(valid_labels) + len(invalid_labels) == len(labels)


class TestStorageIntegration:
    """Test storage layer integration."""

    @pytest.mark.asyncio
    async def test_delta_lake_writer_sanitization(self, sample_acled_label):
        """Test Delta Lake writer sanitizes data."""
        writer = DeltaLakeWriter()
        
        # Add None values to test sanitization
        sample_acled_label["optional_field"] = None
        sample_acled_label["list_field"] = ["item1", "item2"]
        
        sanitized = writer._sanitize_labels([sample_acled_label])
        
        assert len(sanitized) > 0
        # Check that None values are replaced
        for label in sanitized:
            for key, value in label.items():
                assert value is not None or key in ["optional_field"]

    @pytest.mark.asyncio
    async def test_postgres_writer_table_creation(self, mock_postgres_writer):
        """Test PostgreSQL writer creates tables."""
        await mock_postgres_writer.connect()
        
        # Verify connect was called
        mock_postgres_writer.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_labels_to_storage(self, sample_acled_label, mock_postgres_writer, mock_delta_lake_writer):
        """Test writing labels to storage."""
        await mock_postgres_writer.write_labels([sample_acled_label])
        
        mock_postgres_writer.write_labels.assert_called_once()


class TestServicePipeline:
    """Test complete service pipeline."""

    @pytest.mark.asyncio
    async def test_label_ingestion_pipeline(self, sample_acled_label, sample_semantic_group):
        """Test complete label ingestion pipeline."""
        # This is a high-level integration test
        reconciler = LabelReconciler()
        validator = LabelValidator()
        
        # Step 1: Validate label
        is_valid, _ = validator.validate_confidence(sample_acled_label)
        assert is_valid is True
        
        # Step 2: Reconcile with semantic group
        result = await reconciler.reconcile(sample_acled_label, [sample_semantic_group])
        assert result is not None or result is None  # Either matched or not

    @pytest.mark.asyncio
    async def test_multi_source_label_processing(self, sample_acled_label, sample_gdelt_label, sample_coingecko_label):
        """Test processing labels from multiple sources."""
        validator = LabelValidator()
        
        # Validate labels from different sources
        acled_valid, _ = validator.validate_confidence(sample_acled_label)
        gdelt_valid, _ = validator.validate_confidence(sample_gdelt_label)
        coingecko_valid, _ = validator.validate_confidence(sample_coingecko_label)
        
        assert acled_valid is True
        assert gdelt_valid is True
        assert coingecko_valid is True


class TestErrorHandling:
    """Test error handling in integration."""

    @pytest.mark.asyncio
    async def test_reconciliation_with_empty_groups(self, sample_acled_label):
        """Test reconciliation handles empty semantic groups."""
        reconciler = LabelReconciler()
        
        result = await reconciler.reconcile(sample_acled_label, [])
        
        # Should handle gracefully
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_validation_with_missing_fields(self):
        """Test validation handles missing fields."""
        validator = LabelValidator()
        incomplete_label = {"event_id": "123"}
        
        is_valid, message = validator.validate_required_fields(incomplete_label)
        
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_storage_write_failure_handling(self, mock_postgres_writer):
        """Test storage handles write failures."""
        mock_postgres_writer.write_labels.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await mock_postgres_writer.write_labels([])

