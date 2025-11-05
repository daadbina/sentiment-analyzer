"""
Integration tests for PostgreSQL integration.

Tests PostgreSQL client and label retrieval.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from src.clients.postgres_client import PostgreSQLClient
from src.data.label_retriever import LabelRetriever


class TestPostgreSQLIntegration:
    """Test PostgreSQL integration."""

    @pytest.fixture
    def mock_asyncpg(self):
        """Create mock asyncpg."""
        with patch('src.clients.postgres_client.asyncpg.create_pool') as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_postgres_client_connect(self, mock_asyncpg):
        """Test PostgreSQL connection."""
        mock_pool = AsyncMock()
        mock_asyncpg.return_value = mock_pool
        
        client = PostgreSQLClient()
        await client.connect()
        
        assert client.pool is not None

    @pytest.mark.asyncio
    async def test_postgres_client_query(self, mock_asyncpg):
        """Test PostgreSQL query execution."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'id': 1, 'value': 'test1'},
            {'id': 2, 'value': 'test2'},
        ]
        mock_asyncpg.return_value = mock_pool
        
        client = PostgreSQLClient()
        await client.connect()
        
        result = await client.query("SELECT * FROM test")
        
        assert result is not None
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_postgres_client_execute(self, mock_asyncpg):
        """Test PostgreSQL execute."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.execute.return_value = None
        mock_asyncpg.return_value = mock_pool
        
        client = PostgreSQLClient()
        await client.connect()
        
        await client.execute("INSERT INTO test VALUES (1, 'test')")
        
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_client_health_check(self, mock_asyncpg):
        """Test PostgreSQL health check."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = 1
        mock_asyncpg.return_value = mock_pool
        
        client = PostgreSQLClient()
        await client.connect()
        
        is_healthy = await client.health_check()
        
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_postgres_client_disconnect(self, mock_asyncpg):
        """Test PostgreSQL disconnection."""
        mock_pool = AsyncMock()
        mock_asyncpg.return_value = mock_pool
        
        client = PostgreSQLClient()
        await client.connect()
        await client.disconnect()
        
        mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_label_retriever_retrieve_labels(self, mock_asyncpg):
        """Test label retrieval."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'entity_id': 1, 'label': 1, 'timestamp': '2024-01-01'},
            {'entity_id': 2, 'label': 0, 'timestamp': '2024-01-02'},
            {'entity_id': 3, 'label': 1, 'timestamp': '2024-01-03'},
        ]
        mock_asyncpg.return_value = mock_pool
        
        retriever = LabelRetriever()
        
        labels = await retriever.retrieve_labels(
            start_date='2024-01-01',
            end_date='2024-12-31'
        )
        
        assert labels is not None

    @pytest.mark.asyncio
    async def test_label_retriever_temporal_filtering(self, mock_asyncpg):
        """Test temporal filtering of labels."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'entity_id': 1, 'label': 1, 'timestamp': '2024-06-01'},
            {'entity_id': 2, 'label': 0, 'timestamp': '2024-06-02'},
        ]
        mock_asyncpg.return_value = mock_pool
        
        retriever = LabelRetriever()
        
        labels = await retriever.retrieve_labels(
            start_date='2024-01-01',
            end_date='2024-12-31'
        )
        
        assert labels is not None

    @pytest.mark.asyncio
    async def test_label_retriever_validation(self, mock_asyncpg):
        """Test label validation."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'entity_id': 1, 'label': 1},
            {'entity_id': 2, 'label': 0},
            {'entity_id': 3, 'label': 1},
        ]
        mock_asyncpg.return_value = mock_pool
        
        retriever = LabelRetriever()
        
        labels = await retriever.retrieve_labels()
        
        # Validate labels are binary
        assert all(label in [0, 1] for label in labels)

    @pytest.mark.asyncio
    async def test_postgres_connection_pooling(self, mock_asyncpg):
        """Test connection pooling."""
        mock_pool = AsyncMock()
        mock_asyncpg.return_value = mock_pool
        
        client = PostgreSQLClient()
        await client.connect()
        
        # Pool should be created
        assert client.pool is not None

    @pytest.mark.asyncio
    async def test_postgres_transaction_handling(self, mock_asyncpg):
        """Test transaction handling."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_asyncpg.return_value = mock_pool
        
        client = PostgreSQLClient()
        await client.connect()
        
        # Execute should work
        await client.execute("BEGIN")
        await client.execute("INSERT INTO test VALUES (1, 'test')")
        await client.execute("COMMIT")
        
        assert mock_conn.execute.call_count >= 3

    @pytest.mark.asyncio
    async def test_postgres_error_handling(self, mock_asyncpg):
        """Test error handling."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.side_effect = Exception("Connection error")
        mock_asyncpg.return_value = mock_pool
        
        client = PostgreSQLClient()
        await client.connect()
        
        with pytest.raises(Exception):
            await client.query("SELECT * FROM test")

    @pytest.mark.asyncio
    async def test_label_retriever_statistics(self, mock_asyncpg):
        """Test label statistics."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'entity_id': i, 'label': i % 2} for i in range(100)
        ]
        mock_asyncpg.return_value = mock_pool
        
        retriever = LabelRetriever()
        
        labels = await retriever.retrieve_labels()
        stats = retriever.get_statistics(labels)
        
        assert stats is not None
        assert 'class_distribution' in stats

    @pytest.mark.asyncio
    async def test_postgres_batch_operations(self, mock_asyncpg):
        """Test batch operations."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'id': i, 'value': f'test_{i}'} for i in range(1000)
        ]
        mock_asyncpg.return_value = mock_pool
        
        client = PostgreSQLClient()
        await client.connect()
        
        result = await client.query("SELECT * FROM test LIMIT 1000")
        
        assert result is not None
        assert len(result) == 1000

