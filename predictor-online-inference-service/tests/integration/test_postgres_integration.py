"""
Integration tests for PostgreSQL integration.

Tests database operations, label queries, and end-to-end workflows.
Requires PostgreSQL database to be running for full integration tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import asyncpg

from src.clients.postgres_client import PostgresClient
from src.config import PostgresConfig
from src.exceptions import DatabaseError


@pytest.fixture
def postgres_config():
    """Create PostgreSQL configuration for testing."""
    return PostgresConfig(
        host="localhost",
        port=5432,
        database="sentiment_db",
        user="postgres",
        password="postgres",
        min_pool_size=2,
        max_pool_size=10,
        command_timeout=30,
    )


@pytest.fixture
def postgres_client(postgres_config):
    """Create PostgresClient instance."""
    return PostgresClient(config=postgres_config)


class TestPostgresConnection:
    """Test PostgreSQL connection and health checks."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_success(self, postgres_client):
        """Test successful connection to PostgreSQL."""
        with patch("asyncpg.create_pool") as mock_pool:
            mock_pool.return_value = AsyncMock()
            await postgres_client.connect()
            assert postgres_client._pool is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_failure(self, postgres_client):
        """Test connection failure handling."""
        with patch("asyncpg.create_pool", side_effect=Exception("Connection failed")):
            with pytest.raises(DatabaseError):
                await postgres_client.connect()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_disconnect(self, postgres_client):
        """Test disconnection from PostgreSQL."""
        mock_pool = AsyncMock()
        postgres_client._pool = mock_pool
        
        await postgres_client.disconnect()
        
        mock_pool.close.assert_called_once()
        mock_pool.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_connected(self, postgres_client):
        """Test health check when connected."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        result = await postgres_client.health_check()
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_not_connected(self, postgres_client):
        """Test health check when not connected."""
        result = await postgres_client.health_check()
        assert result is False


class TestLabelQueries:
    """Test label query operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_label_for_group(self, postgres_client):
        """Test getting label for a semantic group."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "group_id": "group123",
            "label": 1,
            "label_timestamp": datetime.utcnow(),
        }
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        label = await postgres_client.get_label("group123")
        
        assert label["group_id"] == "group123"
        assert label["label"] == 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_label_not_found(self, postgres_client):
        """Test getting label for non-existent group."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        label = await postgres_client.get_label("nonexistent")
        
        assert label is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_labels_batch(self, postgres_client):
        """Test getting labels for multiple groups."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"group_id": "group1", "label": 1, "label_timestamp": datetime.utcnow()},
            {"group_id": "group2", "label": 0, "label_timestamp": datetime.utcnow()},
            {"group_id": "group3", "label": 1, "label_timestamp": datetime.utcnow()},
        ]
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        labels = await postgres_client.get_labels_batch(["group1", "group2", "group3"])
        
        assert len(labels) == 3
        assert labels[0]["group_id"] == "group1"
        assert labels[1]["label"] == 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_labels_with_time_window(self, postgres_client):
        """Test getting labels within a time window."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        
        now = datetime.utcnow()
        mock_conn.fetch.return_value = [
            {"group_id": "group1", "label": 1, "label_timestamp": now - timedelta(hours=1)},
            {"group_id": "group2", "label": 0, "label_timestamp": now - timedelta(hours=2)},
        ]
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        start_time = now - timedelta(hours=24)
        end_time = now
        
        labels = await postgres_client.get_labels_in_time_window(start_time, end_time)
        
        assert len(labels) == 2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_recent_labels(self, postgres_client):
        """Test getting recent labels."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        
        now = datetime.utcnow()
        mock_conn.fetch.return_value = [
            {"group_id": f"group{i}", "label": i % 2, "label_timestamp": now - timedelta(hours=i)}
            for i in range(10)
        ]
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        labels = await postgres_client.get_recent_labels(hours=24, limit=10)
        
        assert len(labels) == 10


class TestPredictionLogging:
    """Test prediction logging operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_log_prediction(self, postgres_client):
        """Test logging a prediction."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "INSERT 0 1"
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        prediction = {
            "group_id": "group123",
            "prediction": 0.75,
            "confidence": 0.9,
            "model_version": "v1.0",
        }
        
        await postgres_client.log_prediction(prediction)
        
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_log_predictions_batch(self, postgres_client):
        """Test logging multiple predictions."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.executemany.return_value = None
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        predictions = [
            {"group_id": f"group{i}", "prediction": 0.7 + i * 0.05, "confidence": 0.9}
            for i in range(5)
        ]
        
        await postgres_client.log_predictions_batch(predictions)
        
        mock_conn.executemany.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_prediction_history(self, postgres_client):
        """Test getting prediction history for a group."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        
        now = datetime.utcnow()
        mock_conn.fetch.return_value = [
            {
                "group_id": "group123",
                "prediction": 0.75,
                "confidence": 0.9,
                "timestamp": now - timedelta(hours=i),
            }
            for i in range(5)
        ]
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        history = await postgres_client.get_prediction_history("group123", limit=5)
        
        assert len(history) == 5
        assert history[0]["group_id"] == "group123"


class TestLabelReconciliation:
    """Test label reconciliation operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_predictions_for_reconciliation(self, postgres_client):
        """Test getting predictions that need label reconciliation."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        
        now = datetime.utcnow()
        mock_conn.fetch.return_value = [
            {
                "group_id": f"group{i}",
                "prediction": 0.7 + i * 0.05,
                "confidence": 0.9,
                "timestamp": now - timedelta(hours=i),
                "label": None,
            }
            for i in range(10)
        ]
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        predictions = await postgres_client.get_predictions_for_reconciliation(hours=48)
        
        assert len(predictions) == 10

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_prediction_with_label(self, postgres_client):
        """Test updating prediction with actual label."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "UPDATE 1"
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        await postgres_client.update_prediction_with_label("group123", label=1)
        
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_calculate_accuracy_metrics(self, postgres_client):
        """Test calculating accuracy metrics."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "total": 100,
            "correct": 85,
            "accuracy": 0.85,
        }
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        metrics = await postgres_client.calculate_accuracy_metrics(hours=48)
        
        assert metrics["total"] == 100
        assert metrics["correct"] == 85
        assert metrics["accuracy"] == 0.85


class TestTransactions:
    """Test transaction operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_transaction_commit(self, postgres_client):
        """Test transaction commit."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_tx = AsyncMock()
        mock_conn.transaction.return_value = mock_tx
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        async with postgres_client.transaction() as tx:
            await postgres_client.log_prediction({"group_id": "group123", "prediction": 0.75})
        
        mock_tx.__aenter__.assert_called_once()
        mock_tx.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_transaction_rollback(self, postgres_client):
        """Test transaction rollback on error."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_tx = AsyncMock()
        mock_conn.transaction.return_value = mock_tx
        mock_conn.execute.side_effect = Exception("Query failed")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        with pytest.raises(Exception):
            async with postgres_client.transaction() as tx:
                await postgres_client.log_prediction({"group_id": "group123", "prediction": 0.75})
        
        # Transaction should be rolled back
        mock_tx.__aexit__.assert_called_once()


class TestEndToEndWorkflow:
    """Test end-to-end PostgreSQL workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_prediction_label_reconciliation_workflow(self, postgres_client):
        """Test complete workflow: log prediction -> get label -> reconcile."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        # Log prediction
        mock_conn.execute.return_value = "INSERT 0 1"
        await postgres_client.log_prediction({
            "group_id": "group123",
            "prediction": 0.75,
            "confidence": 0.9,
        })
        
        # Get label (simulate label arriving later)
        mock_conn.fetchrow.return_value = {
            "group_id": "group123",
            "label": 1,
            "label_timestamp": datetime.utcnow(),
        }
        label = await postgres_client.get_label("group123")
        
        # Update prediction with label
        mock_conn.execute.return_value = "UPDATE 1"
        await postgres_client.update_prediction_with_label("group123", label=label["label"])
        
        assert label["label"] == 1


class TestErrorHandling:
    """Test error handling in PostgreSQL integration."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_timeout(self, postgres_client):
        """Test handling of query timeout."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = asyncpg.QueryCanceledError("Timeout")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        with pytest.raises(DatabaseError):
            await postgres_client.get_label("group123")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connection_pool_exhausted(self, postgres_client):
        """Test handling of connection pool exhaustion."""
        mock_pool = AsyncMock()
        mock_pool.acquire.side_effect = asyncpg.TooManyConnectionsError("Pool exhausted")
        postgres_client._pool = mock_pool
        
        with pytest.raises(DatabaseError):
            await postgres_client.get_label("group123")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_query(self, postgres_client):
        """Test handling of invalid query."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = asyncpg.PostgresSyntaxError("Invalid query")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        postgres_client._pool = mock_pool
        
        with pytest.raises(DatabaseError):
            await postgres_client.get_label("group123")

