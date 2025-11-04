"""Configuration management for clustering service."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class KafkaConfig(BaseSettings):
    """Kafka configuration."""
    brokers: str = os.getenv("KAFKA_BROKERS", "154.53.166.231:9092")
    schema_registry_url: str = os.getenv("SCHEMA_REGISTRY_URL", "http://154.53.166.231:8081")
    input_topic: str = os.getenv("KAFKA_INPUT_TOPIC", "embeddings")
    output_topic: str = os.getenv("KAFKA_OUTPUT_TOPIC", "semantic_groups")
    consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", "clustering-service-group")
    max_poll_interval_ms: int = int(os.getenv("MAX_POLL_INTERVAL_MS", "300000"))
    processing_timeout_seconds: int = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "30"))


class QdrantConfig(BaseSettings):
    """Qdrant vector database configuration."""
    host: str = os.getenv("QDRANT_HOST", "localhost")
    port: int = int(os.getenv("QDRANT_PORT", "6333"))
    collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "news_embeddings_v1")
    vector_size: int = int(os.getenv("QDRANT_VECTOR_SIZE", "768"))
    timeout: int = int(os.getenv("QDRANT_TIMEOUT", "30"))


class PostgresConfig(BaseSettings):
    """PostgreSQL configuration."""
    host: str = os.getenv("POSTGRES_HOST", "154.53.166.231")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    user: str = os.getenv("POSTGRES_USER", "adminsentiment")
    password: str = os.getenv("POSTGRES_PASSWORD", "wp2400!!!!")
    database: str = os.getenv("POSTGRES_DB", "sentiment")
    min_pool_size: int = int(os.getenv("DB_MIN_POOL_SIZE", "5"))
    max_pool_size: int = int(os.getenv("DB_MAX_POOL_SIZE", "20"))


class RedisConfig(BaseSettings):
    """Redis configuration."""
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    cache_ttl_seconds: int = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "86400"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    socket_timeout: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))


class ClusteringConfig(BaseSettings):
    """Clustering algorithm configuration."""
    algorithm: str = os.getenv("CLUSTERING_ALGORITHM", "hdbscan")
    min_cluster_size: int = int(os.getenv("MIN_CLUSTER_SIZE", "3"))
    min_samples: int = int(os.getenv("MIN_SAMPLES", "2"))
    cluster_selection_epsilon: float = float(os.getenv("CLUSTER_SELECTION_EPSILON", "0.15"))
    metric: str = os.getenv("CLUSTERING_METRIC", "cosine")
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    max_cluster_size: int = int(os.getenv("MAX_CLUSTER_SIZE", "1000"))
    time_window_hours: int = int(os.getenv("TIME_WINDOW_HOURS", "24"))
    overlap_hours: int = int(os.getenv("OVERLAP_HOURS", "6"))
    execution_frequency_hours: int = int(os.getenv("EXECUTION_FREQUENCY_HOURS", "4"))


class ValidationConfig(BaseSettings):
    """Validation configuration."""
    min_cluster_purity: float = float(os.getenv("MIN_CLUSTER_PURITY", "0.85"))
    min_cluster_size: int = int(os.getenv("MIN_CLUSTER_SIZE", "3"))
    max_time_span_hours: int = int(os.getenv("MAX_TIME_SPAN_HOURS", "168"))
    min_sources: int = int(os.getenv("MIN_SOURCES", "2"))
    language_consistency_threshold: float = float(os.getenv("LANGUAGE_CONSISTENCY_THRESHOLD", "0.70"))
    domain_consistency_threshold: float = float(os.getenv("DOMAIN_CONSISTENCY_THRESHOLD", "0.60"))


class ServiceConfig(BaseSettings):
    """Service configuration."""
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8082"))
    prometheus_port: int = int(os.getenv("PROMETHEUS_PORT", "9104"))
    enable_tracing: bool = os.getenv("ENABLE_TRACING", "true").lower() == "true"
    jaeger_host: str = os.getenv("JAEGER_HOST", "localhost")
    jaeger_port: int = int(os.getenv("JAEGER_PORT", "6831"))


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

