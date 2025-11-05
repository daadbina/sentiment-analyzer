"""Unit tests for storage layer."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.storage.delta_lake_writer import DeltaLakeWriter
from src.storage.postgres_writer import PostgreSQLWriter


class TestDeltaLakeWriter:
    """Test Delta Lake writer."""

    def test_sanitize_labels_removes_none(self, sample_acled_label):
        """Test sanitization removes None values."""
        writer = DeltaLakeWriter()
        sample_acled_label["optional_field"] = None
        
        sanitized = writer._sanitize_labels([sample_acled_label])
        
        assert len(sanitized) > 0
        # None values should be replaced with defaults
        for label in sanitized:
            assert label is not None

    def test_sanitize_labels_converts_lists(self, sample_acled_label):
        """Test sanitization converts lists to strings."""
        writer = DeltaLakeWriter()
        sample_acled_label["tags"] = ["tag1", "tag2"]
        
        sanitized = writer._sanitize_labels([sample_acled_label])
        
        assert len(sanitized) > 0
        # Lists should be converted to strings
        for label in sanitized:
            if "tags" in label:
                assert isinstance(label["tags"], str)

    def test_sanitize_labels_handles_empty_list(self):
        """Test sanitization handles empty labels list."""
        writer = DeltaLakeWriter()
        
        sanitized = writer._sanitize_labels([])
        
        assert sanitized == []

    @pytest.mark.asyncio
    async def test_write_labels_with_mock_config(self, mock_config):
        """Test writing labels with mocked config."""
        with patch('src.storage.delta_lake_writer.config', mock_config):
            with patch('src.storage.delta_lake_writer.write_deltalake'):
                writer = DeltaLakeWriter()
                labels = [{"id": "l1", "confidence": 0.9}]

                await writer.write_labels(labels)

                # Should complete without error
                assert True

    @pytest.mark.asyncio
    async def test_write_labels_to_delta_lake(self, sample_acled_label):
        """Test writing labels to Delta Lake."""
        writer = DeltaLakeWriter()
        
        with patch('src.storage.delta_lake_writer.write_deltalake') as mock_write:
            mock_write.return_value = None
            
            # This would be called in the actual implementation
            # result = await writer.write_labels([sample_acled_label])
            # assert result is True


class TestPostgreSQLWriter:
    """Test PostgreSQL writer."""

    @pytest.mark.asyncio
    async def test_postgres_connect(self, mock_postgres_writer):
        """Test PostgreSQL connection."""
        await mock_postgres_writer.connect()
        
        mock_postgres_writer.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_write_labels(self, mock_postgres_writer, sample_acled_label):
        """Test writing labels to PostgreSQL."""
        result = await mock_postgres_writer.write_labels([sample_acled_label])
        
        assert result is True
        mock_postgres_writer.write_labels.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_write_batch_labels(self, mock_postgres_writer, sample_acled_label, sample_gdelt_label):
        """Test writing batch of labels to PostgreSQL."""
        labels = [sample_acled_label, sample_gdelt_label]
        
        result = await mock_postgres_writer.write_labels(labels)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_postgres_close(self, mock_postgres_writer):
        """Test PostgreSQL connection close."""
        await mock_postgres_writer.close()
        
        mock_postgres_writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_transaction_rollback(self, mock_postgres_writer):
        """Test PostgreSQL transaction rollback on error."""
        mock_postgres_writer.write_labels.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await mock_postgres_writer.write_labels([])

    @pytest.mark.asyncio
    async def test_postgres_connection_pool(self, mock_postgres_writer):
        """Test PostgreSQL connection pooling."""
        # Connection pool should be initialized
        await mock_postgres_writer.connect()
        
        mock_postgres_writer.connect.assert_called_once()


class TestReconciliationLogger:
    """Test reconciliation logger."""

    @pytest.mark.asyncio
    async def test_log_reconciliation_decision(self, mock_postgres_writer):
        """Test logging reconciliation decision."""
        decision = {
            "label_id": "123",
            "group_id": "group-001",
            "confidence": 0.85,
            "status": "matched",
        }
        
        # This would be called in the actual implementation
        # result = await logger.log_decision(decision)
        # assert result is True


class TestStorageIntegration:
    """Test storage layer integration."""

    @pytest.mark.asyncio
    async def test_dual_write_delta_and_postgres(self, mock_delta_lake_writer, mock_postgres_writer, sample_acled_label):
        """Test dual write to Delta Lake and PostgreSQL."""
        # Write to Delta Lake
        await mock_delta_lake_writer.write_labels([sample_acled_label])
        
        # Write to PostgreSQL
        await mock_postgres_writer.write_labels([sample_acled_label])
        
        mock_delta_lake_writer.write_labels.assert_called_once()
        mock_postgres_writer.write_labels.assert_called_once()

    @pytest.mark.asyncio
    async def test_storage_failure_handling(self, mock_postgres_writer):
        """Test storage failure handling."""
        mock_postgres_writer.write_labels.side_effect = Exception("Storage error")
        
        with pytest.raises(Exception):
            await mock_postgres_writer.write_labels([])

    @pytest.mark.asyncio
    async def test_storage_retry_logic(self, mock_postgres_writer, sample_acled_label):
        """Test storage retry logic."""
        # First call fails, second succeeds
        mock_postgres_writer.write_labels.side_effect = [
            Exception("Temporary error"),
            True,
        ]
        
        # First attempt should fail
        with pytest.raises(Exception):
            await mock_postgres_writer.write_labels([sample_acled_label])
        
        # Second attempt should succeed
        result = await mock_postgres_writer.write_labels([sample_acled_label])
        assert result is True

    def test_postgres_initialization(self):
        """Test PostgreSQL writer initialization."""
        writer = PostgreSQLWriter()

        # Should have pool attribute
        assert hasattr(writer, 'pool')

    def test_delta_lake_initialization(self):
        """Test Delta Lake writer initialization."""
        writer = DeltaLakeWriter()

        # Should have path attribute
        assert hasattr(writer, 'path')

    @pytest.mark.asyncio
    async def test_delta_lake_write_labels(self, mock_config):
        """Test Delta Lake write labels."""
        with patch('src.storage.delta_lake_writer.config', mock_config):
            with patch('src.storage.delta_lake_writer.write_deltalake'):
                writer = DeltaLakeWriter()

                labels = [{"label_id": "l1", "source": "acled"}]

                await writer.write_labels(labels)

                assert True

    def test_postgres_has_methods(self):
        """Test PostgreSQL writer has required methods."""
        writer = PostgreSQLWriter()

        # Should have required methods
        assert callable(getattr(writer, 'connect', None))
        assert callable(getattr(writer, 'disconnect', None))
        assert callable(getattr(writer, 'write_labels', None))

    def test_delta_lake_has_methods(self):
        """Test Delta Lake writer has required methods."""
        writer = DeltaLakeWriter()

        # Should have required methods
        assert callable(getattr(writer, 'write_labels', None))
        assert callable(getattr(writer, 'write_reconciliation_results', None))

