"""Tests for source registry repository."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.repositories.source_registry import SourceRegistryRepository
from src.exceptions import DatabaseError


class TestSourceRegistryRepository:
    """Test source registry repository."""

    @patch('src.repositories.source_registry.get_config')
    def test_initialization(self, mock_get_config):
        """Test repository initialization."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        assert repo.config is not None
        assert repo.pool is None

    @patch('src.repositories.source_registry.get_config')
    @patch('src.repositories.source_registry.asyncpg')
    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_asyncpg, mock_get_config):
        """Test successful database initialization."""
        mock_config = MagicMock()
        mock_config.database.host = "localhost"
        mock_config.database.port = 5432
        mock_config.database.user = "user"
        mock_config.database.password = "pass"
        mock_config.database.name = "db"
        mock_config.database.min_pool_size = 5
        mock_config.database.max_pool_size = 20
        mock_get_config.return_value = mock_config

        mock_pool = AsyncMock()
        mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

        repo = SourceRegistryRepository()
        await repo.initialize()

        assert repo.pool is not None
        mock_asyncpg.create_pool.assert_called_once()

    @patch('src.repositories.source_registry.get_config')
    @patch('src.repositories.source_registry.asyncpg.create_pool')
    @pytest.mark.asyncio
    async def test_initialize_failure(self, mock_create_pool, mock_get_config):
        """Test database initialization failure."""
        mock_config = MagicMock()
        mock_config.database.host = "localhost"
        mock_config.database.port = 5432
        mock_config.database.user = "user"
        mock_config.database.password = "pass"
        mock_config.database.name = "db"
        mock_config.database.min_pool_size = 5
        mock_config.database.max_pool_size = 20
        mock_get_config.return_value = mock_config

        mock_create_pool.side_effect = Exception("Connection failed")

        repo = SourceRegistryRepository()
        await repo.initialize()

        # Pool should be None on failure
        assert repo.pool is None

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_get_source_no_pool(self, mock_get_config):
        """Test getting source when pool is not available."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()
        result = await repo.get_source("source_123")

        assert result is None

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_get_source_success(self, mock_get_config):
        """Test getting source successfully."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_row = {"id": "source_123", "name": "Test Source", "credibility_score": 0.8}
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.get_source("source_123")

        assert result is not None
        assert result["id"] == "source_123"
        assert result["name"] == "Test Source"

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_get_source_not_found(self, mock_get_config):
        """Test getting source that doesn't exist."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.get_source("nonexistent")

        assert result is None

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_verify_source_no_pool(self, mock_get_config):
        """Test verifying source when pool is not available."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()
        result = await repo.verify_source("source_123")

        # Should return True in lenient mode
        assert result is True

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_verify_source_active(self, mock_get_config):
        """Test verifying active source."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_row = {"id": "source_123", "is_active": True}
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.verify_source("source_123")

        assert result is True

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_verify_source_inactive(self, mock_get_config):
        """Test verifying inactive source."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_row = {"id": "source_123", "is_active": False}
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.verify_source("source_123")

        assert result is False

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_get_source_credibility_no_pool(self, mock_get_config):
        """Test getting credibility when pool is not available."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()
        result = await repo.get_source_credibility("source_123")

        assert result == 0.0

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_get_source_credibility_success(self, mock_get_config):
        """Test getting source credibility successfully."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_row = {"id": "source_123", "credibility_score": 0.85}
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.get_source_credibility("source_123")

        assert result == 0.85

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_get_publisher_id_success(self, mock_get_config):
        """Test getting publisher ID successfully."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_row = {"id": "source_123", "publisher_id": "pub_456"}
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.get_publisher_id("source_123")

        assert result == "pub_456"

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_get_publisher_id_not_found(self, mock_get_config):
        """Test getting publisher ID when source not found."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.get_publisher_id("nonexistent")

        assert result is None

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_create_source_no_pool(self, mock_get_config):
        """Test creating source when pool is not available."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        with pytest.raises(DatabaseError):
            await repo.create_source("source_123", "Test Source")

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_create_source_success(self, mock_get_config):
        """Test creating source successfully."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.create_source(
            "source_123",
            "Test Source",
            credibility_score=0.8,
            is_active=True,
            publisher_id="pub_456",
        )

        assert result is True
        mock_conn.execute.assert_called_once()

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_create_source_failure(self, mock_get_config):
        """Test creating source with failure."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Insert failed"))

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.create_source("source_123", "Test Source")

        assert result is False

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_close_success(self, mock_get_config):
        """Test closing database connection."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool
        mock_pool = AsyncMock()
        repo.pool = mock_pool

        await repo.close()

        mock_pool.close.assert_called_once()

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_close_no_pool(self, mock_get_config):
        """Test closing when pool is not available."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Should not raise error
        await repo.close()

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_close_failure(self, mock_get_config):
        """Test closing with failure."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool with error
        mock_pool = AsyncMock()
        mock_pool.close.side_effect = Exception("Close failed")
        repo.pool = mock_pool

        # Should not raise error
        await repo.close()

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_get_source_credibility_default(self, mock_get_config):
        """Test getting credibility with default value."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_row = {"id": "source_123"}  # No credibility_score
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.get_source_credibility("source_123")

        assert result == 0.5  # Default value

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_verify_source_exception(self, mock_get_config):
        """Test verifying source with exception."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection with error
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("Query failed"))

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.verify_source("source_123")

        # Should return False on error
        assert result is False

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_verify_source_exception_with_no_pool(self, mock_get_config):
        """Test verifying source with exception and no pool."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()
        repo.pool = None

        # Mock pool and connection with error
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("Query failed"))

        result = await repo.verify_source("source_123")

        # Should return True on error when pool is None (lenient mode)
        assert result is True

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_get_source_credibility_exception(self, mock_get_config):
        """Test getting source credibility with exception."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection with error
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("Query failed"))

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.get_source_credibility("source_123")

        # Should return 0.0 on error
        assert result == 0.0

    @patch('src.repositories.source_registry.get_config')
    @pytest.mark.asyncio
    async def test_get_publisher_id_exception(self, mock_get_config):
        """Test getting publisher ID with exception."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        repo = SourceRegistryRepository()

        # Mock pool and connection with error
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("Query failed"))

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        repo.pool = mock_pool

        result = await repo.get_publisher_id("source_123")

        # Should return None on error
        assert result is None

