"""Tests for audit logging performance."""

import pytest
import time
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.repositories.audit_log import AuditLogRepository


class AsyncContextManagerMock:
    """Mock for async context manager."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class TestAuditLoggingPerformance:
    """Test audit logging performance under load."""

    def setup_method(self):
        """Setup test fixtures."""
        self.repo = AuditLogRepository()

    def _setup_mock_pool(self):
        """Setup mock database pool with proper async context manager."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        mock_pool = Mock()
        mock_pool.acquire = Mock(return_value=AsyncContextManagerMock(mock_conn))

        self.repo.pool = mock_pool
        return mock_pool

    @pytest.mark.asyncio
    async def test_audit_log_write_performance(self):
        """Test that single audit log write completes within acceptable time."""
        self._setup_mock_pool()

        start_time = time.time()
        result = await self.repo.log_validation(
            article_id="test_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.85,
            is_valid=True,
            errors=[],
            warnings=[],
        )
        elapsed_time = time.time() - start_time

        assert result is True
        assert elapsed_time < 0.1, f"Write took {elapsed_time}s, expected < 0.1s"

    @pytest.mark.asyncio
    async def test_audit_log_batch_writes(self):
        """Test batch audit log writes performance."""
        self._setup_mock_pool()

        start_time = time.time()

        # Write 100 logs
        tasks = []
        for i in range(100):
            task = self.repo.log_validation(
                article_id=f"test_{i}",
                trace_id=f"trace_{i}",
                job_id="job_123",
                validation_score=0.85,
                is_valid=True,
                errors=[],
                warnings=[],
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        elapsed_time = time.time() - start_time

        assert all(results), "All writes should succeed"
        assert elapsed_time < 5.0, f"Batch write took {elapsed_time}s, expected < 5.0s"

    @pytest.mark.asyncio
    async def test_audit_log_rejection_write_performance(self):
        """Test that rejection log write completes within acceptable time."""
        self._setup_mock_pool()

        start_time = time.time()
        result = await self.repo.log_rejection(
            article_id="test_123",
            trace_id="trace_123",
            job_id="job_123",
            rejection_reason="Duplicate detected",
            error_codes=["DUPLICATE"],
            retry_count=0,
        )
        elapsed_time = time.time() - start_time

        assert result is True
        assert elapsed_time < 0.1, f"Write took {elapsed_time}s, expected < 0.1s"

    @pytest.mark.asyncio
    async def test_audit_log_handles_no_database(self):
        """Test that audit logging gracefully handles missing database."""
        # No pool initialized
        self.repo.pool = None

        start_time = time.time()
        result = await self.repo.log_validation(
            article_id="test_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.85,
            is_valid=True,
            errors=[],
            warnings=[],
        )
        elapsed_time = time.time() - start_time

        # Should return True (graceful degradation)
        assert result is True
        # Should be very fast (no database call)
        assert elapsed_time < 0.01, f"No-op took {elapsed_time}s, expected < 0.01s"

    @pytest.mark.asyncio
    async def test_audit_log_with_metadata(self):
        """Test audit logging with metadata."""
        self._setup_mock_pool()

        metadata = {
            "language": "en",
            "source": "test_source",
            "country": "US",
            "quality_score": 0.85,
        }

        result = await self.repo.log_validation(
            article_id="test_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.85,
            is_valid=True,
            errors=[],
            warnings=[],
            metadata=metadata,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_audit_log_with_errors_and_warnings(self):
        """Test audit logging with errors and warnings."""
        self._setup_mock_pool()

        errors = ["Error 1", "Error 2"]
        warnings = ["Warning 1"]

        result = await self.repo.log_validation(
            article_id="test_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.65,
            is_valid=False,
            errors=errors,
            warnings=warnings,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_audit_log_concurrent_writes(self):
        """Test concurrent audit log writes."""
        self._setup_mock_pool()

        start_time = time.time()

        # Create 50 concurrent writes
        tasks = []
        for i in range(50):
            task = self.repo.log_validation(
                article_id=f"test_{i}",
                trace_id=f"trace_{i}",
                job_id="job_123",
                validation_score=0.85,
                is_valid=True,
                errors=[],
                warnings=[],
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        elapsed_time = time.time() - start_time

        assert all(results), "All concurrent writes should succeed"
        assert elapsed_time < 3.0, f"Concurrent writes took {elapsed_time}s, expected < 3.0s"

    @pytest.mark.asyncio
    async def test_audit_log_error_handling(self):
        """Test audit logging error handling."""
        # Mock the database pool to raise error
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Database error"))

        mock_pool = Mock()
        mock_pool.acquire = Mock(return_value=AsyncContextManagerMock(mock_conn))

        self.repo.pool = mock_pool

        result = await self.repo.log_validation(
            article_id="test_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.85,
            is_valid=True,
            errors=[],
            warnings=[],
        )

        # Should return False on error
        assert result is False

    @pytest.mark.asyncio
    async def test_audit_log_rejection_error_handling(self):
        """Test rejection log error handling."""
        # Mock the database pool to raise error
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Database error"))

        mock_pool = Mock()
        mock_pool.acquire = Mock(return_value=AsyncContextManagerMock(mock_conn))

        self.repo.pool = mock_pool

        result = await self.repo.log_rejection(
            article_id="test_123",
            trace_id="trace_123",
            job_id="job_123",
            rejection_reason="Duplicate",
            error_codes=["DUPLICATE"],
        )

        # Should return False on error
        assert result is False

    @pytest.mark.asyncio
    async def test_audit_log_large_error_list(self):
        """Test audit logging with large error list."""
        self._setup_mock_pool()

        # Create large error list
        errors = [f"Error {i}" for i in range(100)]

        start_time = time.time()
        result = await self.repo.log_validation(
            article_id="test_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.0,
            is_valid=False,
            errors=errors,
            warnings=[],
        )
        elapsed_time = time.time() - start_time

        assert result is True
        assert elapsed_time < 0.1, f"Write with large error list took {elapsed_time}s"

    @pytest.mark.asyncio
    async def test_audit_log_large_metadata(self):
        """Test audit logging with large metadata."""
        self._setup_mock_pool()

        # Create large metadata
        metadata = {f"key_{i}": f"value_{i}" for i in range(100)}

        start_time = time.time()
        result = await self.repo.log_validation(
            article_id="test_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.85,
            is_valid=True,
            errors=[],
            warnings=[],
            metadata=metadata,
        )
        elapsed_time = time.time() - start_time

        assert result is True
        assert elapsed_time < 0.1, f"Write with large metadata took {elapsed_time}s"

