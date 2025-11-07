"""Client abstractions for external services."""

from .feast_client import FeastClient
from .mlflow_client import MLflowModelClient
from .redis_client import RedisClient
from .postgres_client import PostgresClient
from .kafka_consumer import KafkaConsumerClient
from .kafka_producer import KafkaProducerClient, PREDICTION_SCHEMA


__all__ = [
    "FeastClient",
    "MLflowModelClient",
    "RedisClient",
    "PostgresClient",
    "KafkaConsumerClient",
    "KafkaProducerClient",
    "PREDICTION_SCHEMA",
]

