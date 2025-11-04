"""
Integration tests for Redis caching.
"""
import json
import pytest
import redis
from datetime import datetime, timedelta


@pytest.mark.integration
class TestRedisCache:
    """Integration tests for Redis caching."""

    def test_redis_connection(self, redis_client: redis.Redis):
        """Test Redis connection."""
        assert redis_client is not None
        assert redis_client.ping()

    def test_redis_set_and_get(self, redis_client: redis.Redis):
        """Test setting and getting values in Redis."""
        redis_client.set("test-key", "test-value")
        value = redis_client.get("test-key")
        assert value == "test-value"

    def test_redis_set_with_expiry(self, redis_client: redis.Redis):
        """Test setting values with expiry."""
        redis_client.setex("expiring-key", 1, "expiring-value")
        value = redis_client.get("expiring-key")
        assert value == "expiring-value"

    def test_redis_delete(self, redis_client: redis.Redis):
        """Test deleting values from Redis."""
        redis_client.set("delete-key", "delete-value")
        redis_client.delete("delete-key")
        value = redis_client.get("delete-key")
        assert value is None

    def test_redis_hash_operations(self, redis_client: redis.Redis):
        """Test Redis hash operations."""
        redis_client.hset("test-hash", mapping={
            "field1": "value1",
            "field2": "value2",
        })
        
        value = redis_client.hget("test-hash", "field1")
        assert value == "value1"
        
        all_values = redis_client.hgetall("test-hash")
        assert all_values["field1"] == "value1"
        assert all_values["field2"] == "value2"

    def test_redis_list_operations(self, redis_client: redis.Redis):
        """Test Redis list operations."""
        redis_client.rpush("test-list", "item1", "item2", "item3")
        
        length = redis_client.llen("test-list")
        assert length == 3
        
        items = redis_client.lrange("test-list", 0, -1)
        assert items == ["item1", "item2", "item3"]

    def test_redis_set_operations(self, redis_client: redis.Redis):
        """Test Redis set operations."""
        redis_client.sadd("test-set", "member1", "member2", "member3")
        
        is_member = redis_client.sismember("test-set", "member1")
        assert is_member
        
        members = redis_client.smembers("test-set")
        assert "member1" in members
        assert "member2" in members
        assert "member3" in members

    def test_redis_json_storage(self, redis_client: redis.Redis):
        """Test storing JSON in Redis."""
        data = {
            "entity_id": "test-entity-1",
            "text": "John Doe",
            "type": "PERSON",
            "confidence": 0.95,
        }
        
        redis_client.set("entity:test-entity-1", json.dumps(data))
        stored_data = json.loads(redis_client.get("entity:test-entity-1"))
        
        assert stored_data["entity_id"] == "test-entity-1"
        assert stored_data["text"] == "John Doe"
        assert stored_data["confidence"] == 0.95

    def test_redis_cache_hit_miss(self, redis_client: redis.Redis):
        """Test cache hit and miss scenarios."""
        # Cache miss
        value = redis_client.get("nonexistent-key")
        assert value is None
        
        # Cache hit
        redis_client.set("existing-key", "existing-value")
        value = redis_client.get("existing-key")
        assert value == "existing-value"

    def test_redis_key_pattern_matching(self, redis_client: redis.Redis):
        """Test Redis key pattern matching."""
        redis_client.set("entity:1", "value1")
        redis_client.set("entity:2", "value2")
        redis_client.set("actor:1", "value3")
        
        entity_keys = redis_client.keys("entity:*")
        assert len(entity_keys) == 2
        assert "entity:1" in entity_keys
        assert "entity:2" in entity_keys

    def test_redis_increment_operations(self, redis_client: redis.Redis):
        """Test Redis increment operations."""
        redis_client.set("counter", 0)
        redis_client.incr("counter")
        redis_client.incr("counter")
        
        value = int(redis_client.get("counter"))
        assert value == 2

    def test_redis_flush_database(self, redis_client: redis.Redis):
        """Test flushing Redis database."""
        redis_client.set("key1", "value1")
        redis_client.set("key2", "value2")
        
        redis_client.flushdb()
        
        value1 = redis_client.get("key1")
        value2 = redis_client.get("key2")
        
        assert value1 is None
        assert value2 is None

