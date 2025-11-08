"""Client abstractions for external services."""

from .feast_client import FeastClient
from .kafka_consumer import KafkaConsumerClient
from .kafka_producer import PREDICTION_SCHEMA, KafkaProducerClient
from .mlflow_client import MLflowModelClient
from .postgres_client import PostgresClient
from .redis_client import RedisClient
from .s3_client import S3Client

__all__ = [
    "FeastClient",
    "MLflowModelClient",
    "RedisClient",
    "PostgresClient",
    "KafkaConsumerClient",
    "KafkaProducerClient",
    "S3Client",
    "PREDICTION_SCHEMA",
]
