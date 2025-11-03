"""Tests for audit log repository."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from src.repositories.audit_log import AuditLogRepository


class TestAuditLogRepository:
    """Test audit log repository."""

    @pytest.fixture
    def repo(self):
        """Create audit log repository."""
        return AuditLogRepository()

    @pytest.mark.asyncio
    async def test_initialization(self, repo):
        """Test repository initialization."""
        assert repo.pool is None
        assert repo.config is not None

    @pytest.mark.asyncio
    async def test_initialize_success(self, repo):
        """Test successful database initialization."""
        mock_pool = MagicMock()

        mock_create_pool = AsyncMock(return_value=mock_pool)
        with patch("src.repositories.audit_log.asyncpg.create_pool", mock_create_pool):
            await repo.initialize()

            assert repo.pool is not None
            assert repo.pool == mock_pool

    @pytest.mark.asyncio
    async def test_initialize_failure(self, repo):
        """Test database initialization failure."""
        with patch("src.repositories.audit_log.asyncpg.create_pool", side_effect=Exception("Connection failed")):
            await repo.initialize()

            assert repo.pool is None

    @pytest.mark.asyncio
    async def test_log_validation_no_pool(self, repo):
        """Test logging validation without database pool."""
        repo.pool = None

        result = await repo.log_validation(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.9,
            is_valid=True,
            errors=[],
            warnings=[],
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_validation_success(self, repo):
        """Test successful validation logging."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.log_validation(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.9,
            is_valid=True,
            errors=[],
            warnings=[],
        )

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_validation_with_metadata(self, repo):
        """Test logging validation with metadata."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        metadata = {"language": "en", "source": "bbc"}
        result = await repo.log_validation(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.9,
            is_valid=True,
            errors=[],
            warnings=[],
            metadata=metadata,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_validation_with_errors(self, repo):
        """Test logging validation with errors."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.log_validation(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.5,
            is_valid=False,
            errors=["R1_TIMESTAMP_INVALID", "R2_LANGUAGE_DETECTION_FAILED"],
            warnings=["R1_FUTURE_DATE"],
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_validation_failure(self, repo):
        """Test validation logging failure."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Database error"))

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.log_validation(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            validation_score=0.9,
            is_valid=True,
            errors=[],
            warnings=[],
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_log_rejection_no_pool(self, repo):
        """Test logging rejection without database pool."""
        repo.pool = None

        result = await repo.log_rejection(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            rejection_reason="Low quality",
            error_codes=["CONTENT_QUALITY_LOW"],
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_rejection_success(self, repo):
        """Test successful rejection logging."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.log_rejection(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            rejection_reason="Low quality",
            error_codes=["CONTENT_QUALITY_LOW"],
            retry_count=0,
        )

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_rejection_with_retry_count(self, repo):
        """Test logging rejection with retry count."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.log_rejection(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            rejection_reason="Duplicate",
            error_codes=["R3_DUPLICATE_DETECTED"],
            retry_count=3,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_rejection_failure(self, repo):
        """Test rejection logging failure."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Database error"))

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.log_rejection(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            rejection_reason="Error",
            error_codes=["ERROR"],
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_article_history_no_pool(self, repo):
        """Test getting article history without database pool."""
        repo.pool = None

        result = await repo.get_article_history("art_123")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_article_history_success(self, repo):
        """Test successful article history retrieval."""
        mock_row1 = {"article_id": "art_123", "validation_score": 0.9}
        mock_row2 = {"article_id": "art_123", "validation_score": 0.85}

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row1, mock_row2])

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.get_article_history("art_123")

        assert len(result) == 2
        assert result[0]["article_id"] == "art_123"
        assert result[1]["validation_score"] == 0.85

    @pytest.mark.asyncio
    async def test_get_article_history_empty(self, repo):
        """Test getting article history with no records."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.get_article_history("art_nonexistent")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_article_history_failure(self, repo):
        """Test article history retrieval failure."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("Database error"))

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.get_article_history("art_123")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_stats_no_pool(self, repo):
        """Test getting stats without database pool."""
        repo.pool = None

        result = await repo.get_stats()

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_stats_success(self, repo):
        """Test successful stats retrieval."""
        mock_row = {
            "total": 100,
            "valid_count": 85,
            "invalid_count": 15,
            "avg_score": 0.87,
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.get_stats(hours=24)

        assert result["total"] == 100
        assert result["valid_count"] == 85
        assert result["invalid_count"] == 15
        assert result["avg_score"] == 0.87

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, repo):
        """Test getting stats with no records."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.get_stats()

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_stats_failure(self, repo):
        """Test stats retrieval failure."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("Database error"))

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        repo.pool = mock_pool

        result = await repo.get_stats()

        assert result == {}

    @pytest.mark.asyncio
    async def test_close_with_pool(self, repo):
        """Test closing database connection pool."""
        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock(return_value=None)

        repo.pool = mock_pool

        await repo.close()

        mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_pool(self, repo):
        """Test closing without pool."""
        repo.pool = None

        await repo.close()

        # Should not raise any exception

    @pytest.mark.asyncio
    async def test_close_failure(self, repo):
        """Test close failure."""
        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock(side_effect=Exception("Close error"))

        repo.pool = mock_pool

        await repo.close()

        # Should not raise any exception

