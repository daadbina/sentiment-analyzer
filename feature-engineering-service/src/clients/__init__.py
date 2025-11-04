"""Clients package for external services."""

from .kafka_consumer import SemanticGroupConsumer
from .kafka_producer import FeaturesProducer
from .postgres_client import PostgresClient
from .redis_client import RedisClient
from .feast_client import FeastClient

__all__ = [
    "SemanticGroupConsumer",
    "FeaturesProducer",
    "PostgresClient",
    "RedisClient",
    "FeastClient",
]

