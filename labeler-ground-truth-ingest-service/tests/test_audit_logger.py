"""Tests for audit logger."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.storage.audit_logger import AuditLogger


@pytest.fixture
def audit_logger():
    """Create audit logger."""
    return AuditLogger(db_pool=None)


@pytest.fixture
def audit_logger_with_pool():
    """Create audit logger with mock database pool."""
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()

    # Setup async context manager properly
    async def async_acquire():
        return mock_conn

    mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock(return_value=None)))

    return AuditLogger(db_pool=mock_pool)


class TestAuditLogger:
    """Test audit logger."""

    def test_init_no_pool(self, audit_logger):
        """Test initialization without database pool."""
        assert audit_logger is not None
        assert audit_logger.db_pool is None

    def test_init_with_pool(self, audit_logger_with_pool):
        """Test initialization with database pool."""
        assert audit_logger_with_pool is not None
        assert audit_logger_with_pool.db_pool is not None

    @pytest.mark.asyncio
    async def test_ensure_audit_table_no_pool(self, audit_logger):
        """Test table creation without pool."""
        # Should not raise error
        await audit_logger.ensure_audit_table()

    @pytest.mark.asyncio
    async def test_ensure_audit_table_with_pool(self, audit_logger_with_pool):
        """Test table creation with pool."""
        await audit_logger_with_pool.ensure_audit_table()
        
        # Verify execute was called
        mock_conn = audit_logger_with_pool.db_pool.acquire.return_value.__aenter__.return_value
        assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_log_fetch_success(self, audit_logger):
        """Test logging fetch operation."""
        await audit_logger.log_fetch(
            source="GDELT",
            label_count=100,
            duration_ms=1500.0,
            status="success"
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_log_fetch_error(self, audit_logger):
        """Test logging fetch operation with error."""
        await audit_logger.log_fetch(
            source="GDELT",
            label_count=0,
            duration_ms=500.0,
            status="error",
            error_message="API timeout"
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_log_validation(self, audit_logger):
        """Test logging validation operation."""
        await audit_logger.log_validation(
            source="GDELT",
            total_labels=100,
            valid_labels=95,
            invalid_labels=5,
            duration_ms=2000.0
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_log_validation_all_valid(self, audit_logger):
        """Test logging validation with all valid labels."""
        await audit_logger.log_validation(
            source="GDELT",
            total_labels=100,
            valid_labels=100,
            invalid_labels=0,
            duration_ms=2000.0
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_log_reconciliation(self, audit_logger):
        """Test logging reconciliation operation."""
        await audit_logger.log_reconciliation(
            source="GDELT",
            total_labels=100,
            reconciled_labels=50,
            duration_ms=3000.0
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_log_reconciliation_no_matches(self, audit_logger):
        """Test logging reconciliation with no matches."""
        await audit_logger.log_reconciliation(
            source="GDELT",
            total_labels=100,
            reconciled_labels=0,
            duration_ms=3000.0
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_log_deduplication(self, audit_logger):
        """Test logging deduplication operation."""
        await audit_logger.log_deduplication(
            source="GDELT",
            total_labels=100,
            unique_labels=95,
            duplicate_labels=5,
            duration_ms=1000.0
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_log_storage(self, audit_logger):
        """Test logging storage operation."""
        await audit_logger.log_storage(
            storage_type="delta_lake",
            label_count=100,
            duration_ms=2000.0,
            status="success"
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_log_storage_error(self, audit_logger):
        """Test logging storage operation with error."""
        await audit_logger.log_storage(
            storage_type="delta_lake",
            label_count=0,
            duration_ms=500.0,
            status="error",
            error_message="Write failed"
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_write_audit_log_no_pool(self, audit_logger):
        """Test writing audit log without pool."""
        await audit_logger._write_audit_log(
            operation="test",
            source="TEST",
            status="success",
            message="Test message",
            context={"test": "data"}
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_write_audit_log_with_pool(self, audit_logger_with_pool):
        """Test writing audit log with pool."""
        await audit_logger_with_pool._write_audit_log(
            operation="test",
            source="TEST",
            status="success",
            message="Test message",
            context={"test": "data"},
            trace_id="trace_001",
            duration_ms=100.0
        )
        
        # Verify execute was called
        mock_conn = audit_logger_with_pool.db_pool.acquire.return_value.__aenter__.return_value
        assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_log_with_trace_id(self, audit_logger):
        """Test logging with trace ID."""
        await audit_logger.log_fetch(
            source="GDELT",
            label_count=100,
            duration_ms=1500.0,
            trace_id="trace_12345"
        )
        # Should not raise error

    @pytest.mark.asyncio
    async def test_multiple_operations(self, audit_logger):
        """Test logging multiple operations."""
        await audit_logger.log_fetch("GDELT", 100, 1500.0)
        await audit_logger.log_validation("GDELT", 100, 95, 5, 2000.0)
        await audit_logger.log_reconciliation("GDELT", 95, 50, 3000.0)
        await audit_logger.log_deduplication("GDELT", 50, 48, 2, 1000.0)
        await audit_logger.log_storage("delta_lake", 48, 2000.0)
        # Should not raise error

