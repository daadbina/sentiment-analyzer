"""Client modules for external services."""

from src.clients.kafka_consumer import KafkaConsumer
from src.clients.kafka_producer import KafkaProducer
from src.clients.postgres_client import PostgresClient

__all__ = [
    "KafkaConsumer",
    "KafkaProducer",
    "PostgresClient",
]

