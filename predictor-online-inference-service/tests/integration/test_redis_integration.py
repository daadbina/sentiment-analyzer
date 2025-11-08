"""
Integration tests for Redis integration.

Tests cache operations, connection management, and end-to-end workflows.
Requires Redis server to be running for full integration tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime

from src.clients.redis_client import RedisClient
from src.config import RedisConfig
from src.exceptions import CacheError


@pytest.fixture
def redis_config():
    """Create Redis configuration for testing."""
    return RedisConfig(
        host="localhost",
        port=6379,
        db=0,
        password=None,
        max_connections=10,
        socket_timeout=5,
        socket_connect_timeout=5,
    )


@pytest.fixture
def redis_client(redis_config):
    """Create RedisClient instance."""
    return RedisClient(config=redis_config)


class TestRedisConnection:
    """Test Redis connection and health checks."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_success(self, redis_client):
        """Test successful connection to Redis."""
        with patch("redis.asyncio.Redis") as mock_redis:
            mock_redis.return_value = MagicMock()
            await redis_client.connect()
            assert redis_client._client is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_failure(self, redis_client):
        """Test connection failure handling."""
        with patch("redis.asyncio.Redis", side_effect=Exception("Connection failed")):
            with pytest.raises(CacheError):
                await redis_client.connect()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_disconnect(self, redis_client):
        """Test disconnection from Redis."""
        mock_client = AsyncMock()
        redis_client._client = mock_client
        
        await redis_client.disconnect()
        
        mock_client.close.assert_called_once()
        mock_client.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_connected(self, redis_client):
        """Test health check when connected."""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        redis_client._client = mock_client
        
        result = await redis_client.health_check()
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_not_connected(self, redis_client):
        """Test health check when not connected."""
        result = await redis_client.health_check()
        assert result is False


class TestCacheOperations:
    """Test basic cache operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_set_get_success(self, redis_client):
        """Test setting and getting a value."""
        mock_client = AsyncMock()
        mock_client.set.return_value = True
        mock_client.get.return_value = json.dumps({"key": "value"})
        redis_client._client = mock_client
        
        # Set value
        await redis_client.set("test_key", {"key": "value"}, ttl=3600)
        
        # Get value
        result = await redis_client.get("test_key")
        
        assert result == {"key": "value"}
        mock_client.set.assert_called_once()
        mock_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_nonexistent_key(self, redis_client):
        """Test getting a non-existent key."""
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        redis_client._client = mock_client
        
        result = await redis_client.get("nonexistent_key")
        
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_success(self, redis_client):
        """Test deleting a key."""
        mock_client = AsyncMock()
        mock_client.delete.return_value = 1
        redis_client._client = mock_client
        
        result = await redis_client.delete("test_key")
        
        assert result is True
        mock_client.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_nonexistent_key(self, redis_client):
        """Test deleting a non-existent key."""
        mock_client = AsyncMock()
        mock_client.delete.return_value = 0
        redis_client._client = mock_client
        
        result = await redis_client.delete("nonexistent_key")
        
        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_exists_key(self, redis_client):
        """Test checking if key exists."""
        mock_client = AsyncMock()
        mock_client.exists.return_value = 1
        redis_client._client = mock_client
        
        result = await redis_client.exists("test_key")
        
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_exists_nonexistent_key(self, redis_client):
        """Test checking if non-existent key exists."""
        mock_client = AsyncMock()
        mock_client.exists.return_value = 0
        redis_client._client = mock_client
        
        result = await redis_client.exists("nonexistent_key")
        
        assert result is False


class TestBatchOperations:
    """Test batch cache operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mget_success(self, redis_client):
        """Test getting multiple values."""
        mock_client = AsyncMock()
        mock_client.mget.return_value = [
            json.dumps({"id": "1"}),
            json.dumps({"id": "2"}),
            None,
        ]
        redis_client._client = mock_client
        
        results = await redis_client.mget(["key1", "key2", "key3"])
        
        assert len(results) == 3
        assert results[0] == {"id": "1"}
        assert results[1] == {"id": "2"}
        assert results[2] is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mset_success(self, redis_client):
        """Test setting multiple values."""
        mock_client = AsyncMock()
        mock_client.mset.return_value = True
        redis_client._client = mock_client
        
        data = {
            "key1": {"id": "1"},
            "key2": {"id": "2"},
            "key3": {"id": "3"},
        }
        
        await redis_client.mset(data, ttl=3600)
        
        mock_client.mset.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_batch_success(self, redis_client):
        """Test deleting multiple keys."""
        mock_client = AsyncMock()
        mock_client.delete.return_value = 3
        redis_client._client = mock_client
        
        result = await redis_client.delete_batch(["key1", "key2", "key3"])
        
        assert result == 3
        mock_client.delete.assert_called_once_with("key1", "key2", "key3")


class TestTTLManagement:
    """Test TTL (Time To Live) management."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_set_with_ttl(self, redis_client):
        """Test setting value with TTL."""
        mock_client = AsyncMock()
        mock_client.set.return_value = True
        redis_client._client = mock_client
        
        await redis_client.set("test_key", {"data": "value"}, ttl=3600)
        
        # Verify set was called with ex parameter
        call_args = mock_client.set.call_args
        assert call_args[1]["ex"] == 3600

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_ttl(self, redis_client):
        """Test getting TTL of a key."""
        mock_client = AsyncMock()
        mock_client.ttl.return_value = 3600
        redis_client._client = mock_client
        
        ttl = await redis_client.get_ttl("test_key")
        
        assert ttl == 3600

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_ttl_nonexistent_key(self, redis_client):
        """Test getting TTL of non-existent key."""
        mock_client = AsyncMock()
        mock_client.ttl.return_value = -2
        redis_client._client = mock_client
        
        ttl = await redis_client.get_ttl("nonexistent_key")
        
        assert ttl == -2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_expire_key(self, redis_client):
        """Test setting expiration on existing key."""
        mock_client = AsyncMock()
        mock_client.expire.return_value = True
        redis_client._client = mock_client
        
        result = await redis_client.expire("test_key", 7200)
        
        assert result is True
        mock_client.expire.assert_called_once_with("test_key", 7200)


class TestPredictionCache:
    """Test prediction-specific cache operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cache_prediction(self, redis_client):
        """Test caching a prediction."""
        mock_client = AsyncMock()
        mock_client.set.return_value = True
        redis_client._client = mock_client
        
        prediction = {
            "group_id": "group123",
            "prediction": 0.75,
            "confidence": 0.9,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await redis_client.set(f"prediction:group123", prediction, ttl=3600)
        
        mock_client.set.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_cached_prediction(self, redis_client):
        """Test retrieving a cached prediction."""
        mock_client = AsyncMock()
        prediction = {
            "group_id": "group123",
            "prediction": 0.75,
            "confidence": 0.9,
        }
        mock_client.get.return_value = json.dumps(prediction)
        redis_client._client = mock_client
        
        result = await redis_client.get("prediction:group123")
        
        assert result["group_id"] == "group123"
        assert result["prediction"] == 0.75

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cache_batch_predictions(self, redis_client):
        """Test caching multiple predictions."""
        mock_client = AsyncMock()
        mock_client.mset.return_value = True
        redis_client._client = mock_client
        
        predictions = {
            "prediction:group1": {"group_id": "group1", "prediction": 0.75},
            "prediction:group2": {"group_id": "group2", "prediction": 0.85},
            "prediction:group3": {"group_id": "group3", "prediction": 0.65},
        }
        
        await redis_client.mset(predictions, ttl=3600)
        
        mock_client.mset.assert_called_once()


class TestEndToEndWorkflow:
    """Test end-to-end Redis workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_cache_retrieve_workflow(self, redis_client):
        """Test complete workflow: connect -> cache -> retrieve."""
        mock_client = AsyncMock()
        
        with patch("redis.asyncio.Redis", return_value=mock_client):
            await redis_client.connect()
        
        # Cache prediction
        prediction = {"group_id": "group123", "prediction": 0.75}
        mock_client.set.return_value = True
        await redis_client.set("prediction:group123", prediction, ttl=3600)
        
        # Retrieve prediction
        mock_client.get.return_value = json.dumps(prediction)
        result = await redis_client.get("prediction:group123")
        
        assert result["group_id"] == "group123"
        assert result["prediction"] == 0.75


class TestErrorHandling:
    """Test error handling in Redis integration."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_network_timeout(self, redis_client):
        """Test handling of network timeout."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = TimeoutError("Timeout")
        redis_client._client = mock_client
        
        with pytest.raises(CacheError):
            await redis_client.get("test_key")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connection_error(self, redis_client):
        """Test handling of connection error."""
        mock_client = AsyncMock()
        mock_client.set.side_effect = ConnectionError("Connection lost")
        redis_client._client = mock_client
        
        with pytest.raises(CacheError):
            await redis_client.set("test_key", {"data": "value"})

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_json_data(self, redis_client):
        """Test handling of invalid JSON data."""
        mock_client = AsyncMock()
        mock_client.get.return_value = "invalid json"
        redis_client._client = mock_client
        
        with pytest.raises(CacheError):
            await redis_client.get("test_key")

