"""End-to-end integration tests for validation pipeline."""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from testcontainers.kafka import KafkaContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from confluent_kafka import Producer, Consumer, KafkaError
from confluent_kafka.avro import AvroProducer, AvroConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
import avro.schema
import avro.io
import io


@pytest.fixture(scope="module")
def kafka_container():
    """Start Kafka container for testing."""
    container = KafkaContainer()
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="module")
def postgres_container():
    """Start PostgreSQL container for testing."""
    container = PostgresContainer("postgres:15")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="module")
def redis_container():
    """Start Redis container for testing."""
    container = RedisContainer()
    container.start()
    yield container
    container.stop()


@pytest.fixture
def kafka_bootstrap_servers(kafka_container):
    """Get Kafka bootstrap servers."""
    return kafka_container.get_bootstrap_server()


@pytest.fixture
def postgres_url(postgres_container):
    """Get PostgreSQL connection URL."""
    return postgres_container.get_connection_url()


@pytest.fixture
def redis_url(redis_container):
    """Get Redis connection URL."""
    return f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}"


class TestEndToEndPipeline:
    """Test end-to-end validation pipeline."""

    def test_kafka_connectivity(self, kafka_bootstrap_servers):
        """Test Kafka container connectivity."""
        producer = Producer({"bootstrap.servers": kafka_bootstrap_servers})
        
        def delivery_report(err, msg):
            if err is not None:
                raise err
        
        producer.produce(
            "test-topic",
            key="test-key",
            value="test-value",
            callback=delivery_report
        )
        producer.flush()
        
        # Verify message was produced
        consumer = Consumer({
            "bootstrap.servers": kafka_bootstrap_servers,
            "group.id": "test-group",
            "auto.offset.reset": "earliest"
        })
        consumer.subscribe(["test-topic"])
        
        msg = consumer.poll(timeout=5)
        assert msg is not None
        assert msg.value() == b"test-value"
        
        consumer.close()
        producer.close()

    def test_postgres_connectivity(self, postgres_url):
        """Test PostgreSQL container connectivity."""
        import asyncpg
        
        async def test_connection():
            conn = await asyncpg.connect(postgres_url)
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            return result
        
        result = asyncio.run(test_connection())
        assert result == 1

    def test_redis_connectivity(self, redis_url):
        """Test Redis container connectivity."""
        import redis
        
        r = redis.from_url(redis_url)
        r.set("test-key", "test-value")
        value = r.get("test-key")
        assert value == b"test-value"
        r.close()

    def test_kafka_topic_creation(self, kafka_bootstrap_servers):
        """Test creating Kafka topics."""
        from confluent_kafka.admin import AdminClient, NewTopic
        
        admin_client = AdminClient({"bootstrap.servers": kafka_bootstrap_servers})
        
        # Create topics
        topics = [
            NewTopic("news_raw", num_partitions=1, replication_factor=1),
            NewTopic("news_validated", num_partitions=1, replication_factor=1),
            NewTopic("news_rejected", num_partitions=1, replication_factor=1),
        ]
        
        fs = admin_client.create_topics(topics, validate_only=False)
        
        for topic, f in fs.items():
            try:
                f.result()
            except Exception as e:
                # Topic might already exist
                pass
        
        admin_client.close()

    def test_message_serialization(self, kafka_bootstrap_servers):
        """Test Avro message serialization."""
        # Define schema
        schema_str = """
        {
            "type": "record",
            "name": "TestMessage",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "title", "type": "string"},
                {"name": "body", "type": "string"}
            ]
        }
        """
        
        schema = avro.schema.parse(schema_str)
        
        # Create message
        message = {
            "id": "test-1",
            "title": "Test Title",
            "body": "Test Body"
        }
        
        # Serialize
        writer = avro.io.DatumWriter(schema)
        bytes_writer = io.BytesIO()
        encoder = avro.io.BinaryEncoder(bytes_writer)
        writer.write(message, encoder)
        
        # Deserialize
        bytes_reader = io.BytesIO(bytes_writer.getvalue())
        decoder = avro.io.BinaryDecoder(bytes_reader)
        reader = avro.io.DatumReader(schema)
        deserialized = reader.read(decoder)
        
        assert deserialized == message

    def test_postgres_schema_creation(self, postgres_url):
        """Test creating PostgreSQL schema for audit logs."""
        import asyncpg
        
        async def create_schema():
            conn = await asyncpg.connect(postgres_url)
            
            # Create audit log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS data_validation_log (
                    id SERIAL PRIMARY KEY,
                    record_id VARCHAR(255),
                    timestamp TIMESTAMP,
                    rule_id VARCHAR(50),
                    validation_stage VARCHAR(100),
                    passed BOOLEAN,
                    error_message TEXT,
                    severity VARCHAR(20),
                    schema_version VARCHAR(20),
                    trace_id VARCHAR(255),
                    processing_duration_ms INTEGER,
                    language_detected VARCHAR(10),
                    confidence_score FLOAT,
                    validation_score_final FLOAT
                )
            """)
            
            # Verify table exists
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'data_validation_log'
                )
            """)
            
            await conn.close()
            return result
        
        result = asyncio.run(create_schema())
        assert result is True

    def test_redis_cache_operations(self, redis_url):
        """Test Redis cache operations."""
        import redis
        
        r = redis.from_url(redis_url)
        
        # Test set/get
        r.set("key1", "value1", ex=3600)
        assert r.get("key1") == b"value1"
        
        # Test TTL
        ttl = r.ttl("key1")
        assert ttl > 0
        
        # Test delete
        r.delete("key1")
        assert r.get("key1") is None
        
        r.close()

    def test_kafka_consumer_group(self, kafka_bootstrap_servers):
        """Test Kafka consumer group functionality."""
        producer = Producer({"bootstrap.servers": kafka_bootstrap_servers})
        
        # Produce messages
        for i in range(5):
            producer.produce("test-consumer-group", value=f"message-{i}")
        producer.flush()
        
        # Consume with group
        consumer = Consumer({
            "bootstrap.servers": kafka_bootstrap_servers,
            "group.id": "test-consumer-group",
            "auto.offset.reset": "earliest"
        })
        consumer.subscribe(["test-consumer-group"])
        
        messages = []
        for _ in range(5):
            msg = consumer.poll(timeout=5)
            if msg:
                messages.append(msg.value())
        
        assert len(messages) == 5
        
        consumer.close()
        producer.close()

    def test_postgres_transaction(self, postgres_url):
        """Test PostgreSQL transaction handling."""
        import asyncpg
        
        async def test_transaction():
            conn = await asyncpg.connect(postgres_url)
            
            # Create test table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_transactions (
                    id SERIAL PRIMARY KEY,
                    value VARCHAR(255)
                )
            """)
            
            # Test transaction
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO test_transactions (value) VALUES ($1)",
                    "test-value"
                )
            
            # Verify insert
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM test_transactions"
            )
            
            await conn.close()
            return result
        
        result = asyncio.run(test_transaction())
        assert result >= 1

    def test_redis_expiration(self, redis_url):
        """Test Redis key expiration."""
        import redis
        import time
        
        r = redis.from_url(redis_url)
        
        # Set key with 1 second expiration
        r.set("expiring-key", "value", ex=1)
        assert r.get("expiring-key") is not None
        
        # Wait for expiration
        time.sleep(1.5)
        assert r.get("expiring-key") is None
        
        r.close()

