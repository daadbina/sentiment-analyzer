"""Configuration management for clustering service."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class KafkaConfig(BaseSettings):
    """Kafka configuration."""
    brokers: str = os.getenv("KAFKA_BROKERS")
    schema_registry_url: str = os.getenv("SCHEMA_REGISTRY_URL")
    input_topic: str = os.getenv("KAFKA_INPUT_TOPIC")
    output_topic: str = os.getenv("KAFKA_OUTPUT_TOPIC")
    consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP")
    max_poll_interval_ms: int = int(os.getenv("MAX_POLL_INTERVAL_MS", "0"))
    processing_timeout_seconds: int = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "0"))

    def __init__(self, **data):
        super().__init__(**data)
        if not self.brokers:
            raise ValueError("KAFKA_BROKERS environment variable is required")
        if not self.schema_registry_url:
            raise ValueError("SCHEMA_REGISTRY_URL environment variable is required")
        if not self.input_topic:
            raise ValueError("KAFKA_INPUT_TOPIC environment variable is required")
        if not self.output_topic:
            raise ValueError("KAFKA_OUTPUT_TOPIC environment variable is required")
        if not self.consumer_group:
            raise ValueError("KAFKA_CONSUMER_GROUP environment variable is required")
        if self.max_poll_interval_ms == 0:
            raise ValueError("MAX_POLL_INTERVAL_MS environment variable is required")
        if self.processing_timeout_seconds == 0:
            raise ValueError("PROCESSING_TIMEOUT_SECONDS environment variable is required")


class QdrantConfig(BaseSettings):
    """Qdrant vector database configuration."""
    host: str = os.getenv("QDRANT_HOST")
    port: int = int(os.getenv("QDRANT_PORT", "0"))
    collection_name: str = os.getenv("QDRANT_COLLECTION_NAME")
    vector_size: int = int(os.getenv("QDRANT_VECTOR_SIZE", "0"))
    timeout: int = int(os.getenv("QDRANT_TIMEOUT", "0"))

    def __init__(self, **data):
        super().__init__(**data)
        if not self.host:
            raise ValueError("QDRANT_HOST environment variable is required")
        if self.port == 0:
            raise ValueError("QDRANT_PORT environment variable is required")
        if not self.collection_name:
            raise ValueError("QDRANT_COLLECTION_NAME environment variable is required")
        if self.vector_size == 0:
            raise ValueError("QDRANT_VECTOR_SIZE environment variable is required")
        if self.timeout == 0:
            raise ValueError("QDRANT_TIMEOUT environment variable is required")


class PostgresConfig(BaseSettings):
    """PostgreSQL configuration."""
    host: str = os.getenv("POSTGRES_HOST")
    port: int = int(os.getenv("POSTGRES_PORT", "0"))
    user: str = os.getenv("POSTGRES_USER")
    password: str = os.getenv("POSTGRES_PASSWORD")
    database: str = os.getenv("POSTGRES_DB")
    min_pool_size: int = int(os.getenv("DB_MIN_POOL_SIZE", "0"))
    max_pool_size: int = int(os.getenv("DB_MAX_POOL_SIZE", "0"))

    def __init__(self, **data):
        super().__init__(**data)
        if not self.host:
            raise ValueError("POSTGRES_HOST environment variable is required")
        if self.port == 0:
            raise ValueError("POSTGRES_PORT environment variable is required")
        if not self.user:
            raise ValueError("POSTGRES_USER environment variable is required")
        if not self.password:
            raise ValueError("POSTGRES_PASSWORD environment variable is required")
        if not self.database:
            raise ValueError("POSTGRES_DB environment variable is required")
        if self.min_pool_size == 0:
            raise ValueError("DB_MIN_POOL_SIZE environment variable is required")
        if self.max_pool_size == 0:
            raise ValueError("DB_MAX_POOL_SIZE environment variable is required")


class RedisConfig(BaseSettings):
    """Redis configuration."""
    host: str = os.getenv("REDIS_HOST")
    port: int = int(os.getenv("REDIS_PORT", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")
    cache_ttl_seconds: int = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "0"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    socket_timeout: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "0"))

    def __init__(self, **data):
        super().__init__(**data)
        if not self.host:
            raise ValueError("REDIS_HOST environment variable is required")
        if self.port == 0:
            raise ValueError("REDIS_PORT environment variable is required")
        if self.cache_ttl_seconds == 0:
            raise ValueError("REDIS_CACHE_TTL_SECONDS environment variable is required")
        if self.socket_timeout == 0:
            raise ValueError("REDIS_SOCKET_TIMEOUT environment variable is required")


class ClusteringConfig(BaseSettings):
    """Clustering algorithm configuration."""
    algorithm: str = os.getenv("CLUSTERING_ALGORITHM")
    min_cluster_size: int = int(os.getenv("MIN_CLUSTER_SIZE", "0"))
    min_samples: int = int(os.getenv("MIN_SAMPLES", "0"))
    cluster_selection_epsilon: float = float(os.getenv("CLUSTER_SELECTION_EPSILON", "0.0"))
    metric: str = os.getenv("CLUSTERING_METRIC")
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.0"))
    max_cluster_size: int = int(os.getenv("MAX_CLUSTER_SIZE", "0"))
    time_window_hours: int = int(os.getenv("TIME_WINDOW_HOURS", "0"))
    overlap_hours: int = int(os.getenv("OVERLAP_HOURS", "0"))
    execution_frequency_hours: int = int(os.getenv("EXECUTION_FREQUENCY_HOURS", "0"))

    def __init__(self, **data):
        super().__init__(**data)
        if not self.algorithm:
            raise ValueError("CLUSTERING_ALGORITHM environment variable is required")
        if self.min_cluster_size == 0:
            raise ValueError("MIN_CLUSTER_SIZE environment variable is required")
        if self.min_samples == 0:
            raise ValueError("MIN_SAMPLES environment variable is required")
        if self.cluster_selection_epsilon == 0.0:
            raise ValueError("CLUSTER_SELECTION_EPSILON environment variable is required")
        if not self.metric:
            raise ValueError("CLUSTERING_METRIC environment variable is required")
        if self.similarity_threshold == 0.0:
            raise ValueError("SIMILARITY_THRESHOLD environment variable is required")
        if self.max_cluster_size == 0:
            raise ValueError("MAX_CLUSTER_SIZE environment variable is required")
        if self.time_window_hours == 0:
            raise ValueError("TIME_WINDOW_HOURS environment variable is required")
        if self.overlap_hours == 0:
            raise ValueError("OVERLAP_HOURS environment variable is required")
        if self.execution_frequency_hours == 0:
            raise ValueError("EXECUTION_FREQUENCY_HOURS environment variable is required")


class ValidationConfig(BaseSettings):
    """Validation configuration."""
    min_cluster_purity: float = float(os.getenv("MIN_CLUSTER_PURITY", "0.0"))
    min_cluster_size: int = int(os.getenv("MIN_CLUSTER_SIZE", "0"))
    max_time_span_hours: int = int(os.getenv("MAX_TIME_SPAN_HOURS", "0"))
    min_sources: int = int(os.getenv("MIN_SOURCES", "0"))
    language_consistency_threshold: float = float(os.getenv("LANGUAGE_CONSISTENCY_THRESHOLD", "0.0"))
    domain_consistency_threshold: float = float(os.getenv("DOMAIN_CONSISTENCY_THRESHOLD", "0.0"))

    def __init__(self, **data):
        super().__init__(**data)
        if self.min_cluster_purity == 0.0:
            raise ValueError("MIN_CLUSTER_PURITY environment variable is required")
        if self.min_cluster_size == 0:
            raise ValueError("MIN_CLUSTER_SIZE environment variable is required")
        if self.max_time_span_hours == 0:
            raise ValueError("MAX_TIME_SPAN_HOURS environment variable is required")
        if self.min_sources == 0:
            raise ValueError("MIN_SOURCES environment variable is required")
        if self.language_consistency_threshold == 0.0:
            raise ValueError("LANGUAGE_CONSISTENCY_THRESHOLD environment variable is required")
        if self.domain_consistency_threshold == 0.0:
            raise ValueError("DOMAIN_CONSISTENCY_THRESHOLD environment variable is required")


class ServiceConfig(BaseSettings):
    """Service configuration."""
    environment: str = os.getenv("ENVIRONMENT")
    log_level: str = os.getenv("LOG_LEVEL")
    api_host: str = os.getenv("API_HOST")
    api_port: int = int(os.getenv("API_PORT", "0"))
    prometheus_port: int = int(os.getenv("PROMETHEUS_PORT", "0"))
    enable_tracing: str = os.getenv("ENABLE_TRACING")
    jaeger_host: str = os.getenv("JAEGER_HOST")
    jaeger_port: int = int(os.getenv("JAEGER_PORT", "0"))

    def __init__(self, **data):
        super().__init__(**data)
        if not self.environment:
            raise ValueError("ENVIRONMENT environment variable is required")
        if not self.log_level:
            raise ValueError("LOG_LEVEL environment variable is required")
        if not self.api_host:
            raise ValueError("API_HOST environment variable is required")
        if self.api_port == 0:
            raise ValueError("API_PORT environment variable is required")
        if self.prometheus_port == 0:
            raise ValueError("PROMETHEUS_PORT environment variable is required")
        if not self.enable_tracing:
            raise ValueError("ENABLE_TRACING environment variable is required")
        if not self.jaeger_host:
            raise ValueError("JAEGER_HOST environment variable is required")
        if self.jaeger_port == 0:
            raise ValueError("JAEGER_PORT environment variable is required")


class Config(BaseSettings):
    """Main configuration class."""
    kafka: KafkaConfig = KafkaConfig()
    qdrant: QdrantConfig = QdrantConfig()
    postgres: PostgresConfig = PostgresConfig()
    redis: RedisConfig = RedisConfig()
    clustering: ClusteringConfig = ClusteringConfig()
    validation: ValidationConfig = ValidationConfig()
    service: ServiceConfig = ServiceConfig()


# Global config instance
config = Config()

