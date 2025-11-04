"""
Pytest configuration and shared fixtures for integration tests.
"""
import os
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from testcontainers.postgres import PostgresContainer
from testcontainers.kafka import KafkaContainer
from testcontainers.redis import RedisContainer
import psycopg2
from psycopg2.extensions import connection as psycopg2_connection
import redis
from confluent_kafka import Producer, Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer, AvroDeserializer


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Start PostgreSQL container for integration tests."""
    container = PostgresContainer("postgres:15-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def kafka_container() -> Generator[KafkaContainer, None, None]:
    """Start Kafka container for integration tests."""
    container = KafkaContainer()
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    """Start Redis container for integration tests."""
    container = RedisContainer()
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def postgres_connection(postgres_container: PostgresContainer) -> Generator[psycopg2_connection, None, None]:
    """Create PostgreSQL connection to test container."""
    conn = psycopg2.connect(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        user=postgres_container.POSTGRES_USER,
        password=postgres_container.POSTGRES_PASSWORD,
        database=postgres_container.POSTGRES_DB,
    )
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def redis_connection(redis_container: RedisContainer) -> Generator[redis.Redis, None, None]:
    """Create Redis connection to test container."""
    client = redis.Redis(
        host=redis_container.get_container_host_ip(),
        port=redis_container.get_exposed_port(6379),
        decode_responses=True,
    )
    yield client
    client.close()


@pytest.fixture(scope="session")
def kafka_brokers(kafka_container: KafkaContainer) -> str:
    """Get Kafka brokers address."""
    return kafka_container.get_bootstrap_server()


@pytest.fixture(scope="session")
def schema_registry_url(kafka_container: KafkaContainer) -> str:
    """Get Schema Registry URL."""
    # For testcontainers, we need to use a mock schema registry
    # In production, this would be the actual schema registry
    return "http://localhost:8081"


@pytest.fixture
def kafka_producer(kafka_brokers: str) -> Generator[Producer, None, None]:
    """Create Kafka producer for tests."""
    producer = Producer({"bootstrap.servers": kafka_brokers})
    yield producer
    producer.flush()


@pytest.fixture
def kafka_consumer(kafka_brokers: str) -> Generator[Consumer, None, None]:
    """Create Kafka consumer for tests."""
    consumer = Consumer({
        "bootstrap.servers": kafka_brokers,
        "group.id": "test-group",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    yield consumer
    consumer.close()


@pytest.fixture
def postgres_cursor(postgres_connection: psycopg2_connection):
    """Create PostgreSQL cursor for tests."""
    cursor = postgres_connection.cursor()
    yield cursor
    cursor.close()
    postgres_connection.rollback()


@pytest.fixture
def redis_client(redis_connection: redis.Redis) -> Generator[redis.Redis, None, None]:
    """Get Redis client and flush before test."""
    redis_connection.flushdb()
    yield redis_connection
    redis_connection.flushdb()


@pytest.fixture
def test_env_vars(monkeypatch, postgres_container, kafka_container, redis_container):
    """Set environment variables for tests."""
    monkeypatch.setenv("POSTGRES_HOST", postgres_container.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(postgres_container.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_USER", postgres_container.POSTGRES_USER)
    monkeypatch.setenv("POSTGRES_PASSWORD", postgres_container.POSTGRES_PASSWORD)
    monkeypatch.setenv("POSTGRES_DATABASE", postgres_container.POSTGRES_DB)
    
    monkeypatch.setenv("KAFKA_BROKERS", kafka_container.get_bootstrap_server())
    monkeypatch.setenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
    
    monkeypatch.setenv("REDIS_HOST", redis_container.get_container_host_ip())
    monkeypatch.setenv("REDIS_PORT", str(redis_container.get_exposed_port(6379)))
    
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "false")

