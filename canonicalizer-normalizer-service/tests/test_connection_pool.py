"""Tests for database connection pooling."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.database.connection_pool import (
    ConnectionPoolManager,
    IndexManager,
    PoolStats,
)


class TestPoolStats:
    """Test pool statistics."""

    def test_pool_stats_creation(self):
        """Test creating pool stats."""
        stats = PoolStats(
            total_connections=10,
            available_connections=8,
            in_use_connections=2,
            total_created=100,
            total_closed=90,
        )
        assert stats.total_connections == 10
        assert stats.available_connections == 8
        assert stats.in_use_connections == 2
        assert stats.total_created == 100
        assert stats.total_closed == 90

    def test_pool_stats_default_values(self):
        """Test pool stats default values."""
        stats = PoolStats(
            total_connections=0,
            available_connections=0,
            in_use_connections=0,
            total_created=0,
            total_closed=0,
        )
        assert stats.last_health_check is None
        assert stats.health_check_failures == 0


class TestConnectionPoolManager:
    """Test connection pool manager."""

    def test_pool_manager_initialization(self):
        """Test pool manager initialization."""
        manager = ConnectionPoolManager(
            dsn="postgresql://user:pass@localhost/db",
            min_size=5,
            max_size=15,
        )
        assert manager.dsn == "postgresql://user:pass@localhost/db"
        assert manager.min_size == 5
        assert manager.max_size == 15
        assert manager.pool is None

    def test_pool_manager_default_parameters(self):
        """Test pool manager default parameters."""
        manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        assert manager.min_size == 10
        assert manager.max_size == 20
        assert manager.max_queries == 50000
        assert manager.health_check_interval == 30
        assert manager.health_check_timeout == 5

    def test_pool_manager_stats_initialization(self):
        """Test pool manager stats initialization."""
        manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        stats = manager.get_stats()
        assert isinstance(stats, PoolStats)
        assert stats.total_connections == 0
        assert stats.available_connections == 0
        assert stats.in_use_connections == 0

    @pytest.mark.asyncio
    async def test_pool_manager_initialize_error(self):
        """Test pool manager initialization error."""
        manager = ConnectionPoolManager(dsn="postgresql://invalid/db")
        with patch('asyncpg.create_pool', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception):
                await manager.initialize()

    @pytest.mark.asyncio
    async def test_pool_manager_close_without_pool(self):
        """Test closing pool manager without pool."""
        manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        # Should not raise error
        await manager.close()

    @pytest.mark.asyncio
    async def test_pool_manager_acquire_without_pool(self):
        """Test acquiring connection without pool."""
        manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        with pytest.raises(RuntimeError):
            await manager.acquire()

    @pytest.mark.asyncio
    async def test_pool_manager_execute_without_pool(self):
        """Test executing query without pool."""
        manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        with pytest.raises(RuntimeError):
            await manager.execute("SELECT 1")

    @pytest.mark.asyncio
    async def test_pool_manager_execute_one_without_pool(self):
        """Test executing single query without pool."""
        manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        with pytest.raises(RuntimeError):
            await manager.execute_one("SELECT 1")

    @pytest.mark.asyncio
    async def test_pool_manager_execute_scalar_without_pool(self):
        """Test executing scalar query without pool."""
        manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        with pytest.raises(RuntimeError):
            await manager.execute_scalar("SELECT 1")

    @pytest.mark.asyncio
    async def test_pool_manager_health_check_without_pool(self):
        """Test health check without pool."""
        manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        # Should not raise error
        await manager._perform_health_check()

    @pytest.mark.asyncio
    async def test_pool_manager_create_indexes_without_pool(self):
        """Test creating indexes without pool."""
        manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        with pytest.raises(RuntimeError):
            await manager.create_indexes()


class TestIndexManager:
    """Test index manager."""

    def test_index_manager_initialization(self):
        """Test index manager initialization."""
        pool_manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        manager = IndexManager(pool_manager)
        assert manager.pool_manager is pool_manager

    @pytest.mark.asyncio
    async def test_index_manager_create_all_indexes_without_pool(self):
        """Test creating indexes without pool."""
        pool_manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        manager = IndexManager(pool_manager)
        with pytest.raises(RuntimeError):
            await manager.create_all_indexes()

    @pytest.mark.asyncio
    async def test_index_manager_get_index_stats_without_pool(self):
        """Test getting index stats without pool."""
        pool_manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        manager = IndexManager(pool_manager)
        stats = await manager.get_index_stats()
        assert isinstance(stats, dict)
        assert stats == {}

    @pytest.mark.asyncio
    async def test_index_manager_get_index_stats_with_error(self):
        """Test getting index stats with error."""
        pool_manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        pool_manager.pool = AsyncMock()
        pool_manager.pool.fetch = AsyncMock(side_effect=Exception("Query failed"))

        manager = IndexManager(pool_manager)
        stats = await manager.get_index_stats()
        assert isinstance(stats, dict)
        assert stats == {}


class TestConnectionPoolIntegration:
    """Integration tests for connection pool."""

    def test_pool_manager_configuration(self):
        """Test pool manager configuration."""
        manager = ConnectionPoolManager(
            dsn="postgresql://user:pass@localhost:5432/testdb",
            min_size=5,
            max_size=25,
            max_queries=100000,
            health_check_interval=60,
            health_check_timeout=10,
        )
        assert manager.dsn == "postgresql://user:pass@localhost:5432/testdb"
        assert manager.min_size == 5
        assert manager.max_size == 25
        assert manager.max_queries == 100000
        assert manager.health_check_interval == 60
        assert manager.health_check_timeout == 10

    def test_pool_stats_tracking(self):
        """Test pool stats tracking."""
        manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        stats = manager.get_stats()

        assert stats.total_connections == 0
        assert stats.available_connections == 0
        assert stats.in_use_connections == 0
        assert stats.health_check_failures == 0

    @pytest.mark.asyncio
    async def test_index_manager_with_pool_manager(self):
        """Test index manager with pool manager."""
        pool_manager = ConnectionPoolManager(dsn="postgresql://localhost/db")
        index_manager = IndexManager(pool_manager)

        assert index_manager.pool_manager is pool_manager

