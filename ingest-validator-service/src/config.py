"""Configuration management for Ingest Validator Service."""

from dataclasses import dataclass
from typing import Optional
import os
from functools import lru_cache


@dataclass(frozen=True)
class KafkaConfig:
    """Kafka configuration."""

    brokers: str = os.getenv("KAFKA_BROKERS", "localhost:9092")
    consumer_group: str = os.getenv("CONSUMER_GROUP", "validator-service-group")
    schema_registry_url: str = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
    max_poll_interval_ms: int = int(os.getenv("MAX_POLL_INTERVAL_MS", "300000"))
    processing_timeout_seconds: int = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "30"))


@dataclass(frozen=True)
class LanguageConfig:
    """Language detection configuration."""

    confidence_threshold_rss: float = float(
        os.getenv("LANG_CONFIDENCE_THRESHOLD_RSS", "0.80")
    )
    confidence_threshold_full: float = float(
        os.getenv("LANG_CONFIDENCE_THRESHOLD_FULL", "0.90")
    )
    confidence_threshold_default: float = float(
        os.getenv("LANG_CONFIDENCE_THRESHOLD_DEFAULT", "0.85")
    )


@dataclass(frozen=True)
class DuplicationConfig:
    """Deduplication configuration."""

    similarity_threshold: float = float(
        os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.85")
    )
    time_window_hours: int = int(os.getenv("DUPLICATE_TIME_WINDOW_HOURS", "48"))
    service_url: str = os.getenv("DEDUP_SERVICE_URL", "localhost:50051")


@dataclass(frozen=True)
class ValidationConfig:
    """Validation configuration."""

    score_accept: float = float(os.getenv("VALIDATION_SCORE_ACCEPT", "0.85"))
    score_reprocess: float = float(os.getenv("VALIDATION_SCORE_REPROCESS", "0.70"))


@dataclass(frozen=True)
class RedisConfig:
    """Redis configuration."""

    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")
    cache_ttl_seconds: int = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "86400"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    socket_timeout: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))


@dataclass(frozen=True)
class DatabaseConfig:
    """Database configuration."""

    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    user: str = os.getenv("POSTGRES_USER", "postgres")
    password: str = os.getenv("POSTGRES_PASSWORD", "password")
    database: str = os.getenv("POSTGRES_DB", "validator")
    name: str = os.getenv("POSTGRES_DB", "validator")
    min_pool_size: int = int(os.getenv("DB_MIN_POOL_SIZE", "5"))
    max_pool_size: int = int(os.getenv("DB_MAX_POOL_SIZE", "20"))
    timescaledb_dsn: str = os.getenv(
        "TIMESCALEDB_DSN", "postgresql://user:password@localhost:5432/validator"
    )
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "password")
    postgres_db: str = os.getenv("POSTGRES_DB", "validator")


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    timeout_seconds: int = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))


@dataclass(frozen=True)
class MetricsConfig:
    """Metrics configuration."""

    prometheus_port: int = int(os.getenv("PROMETHEUS_PORT", "9102"))
    enabled: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"


@dataclass(frozen=True)
class TracingConfig:
    """Tracing configuration."""

    jaeger_host: str = os.getenv("JAEGER_HOST", "localhost")
    jaeger_port: int = int(os.getenv("JAEGER_PORT", "6831"))
    enabled: bool = os.getenv("TRACING_ENABLED", "true").lower() == "true"


@dataclass(frozen=True)
class ServiceConfig:
    """Main service configuration."""

    api_host: str = os.getenv("API_HOST", "127.0.0.1")  # nosec - intentional for development
    api_port: int = int(os.getenv("API_PORT", "8081"))
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    service_version: str = "1.0.0"

    # Kafka configuration
    kafka_brokers: str = os.getenv("KAFKA_BROKERS", "localhost:9092")
    schema_registry_url: str = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")

    # gRPC Dedup Service configuration
    dedup_service: str = os.getenv("DEDUP_SERVICE", "localhost:50051")

    # Sub-configurations
    kafka: KafkaConfig = KafkaConfig()
    language: LanguageConfig = LanguageConfig()
    deduplication: DuplicationConfig = DuplicationConfig()
    validation: ValidationConfig = ValidationConfig()
    redis: RedisConfig = RedisConfig()
    database: DatabaseConfig = DatabaseConfig()
    circuit_breaker: CircuitBreakerConfig = CircuitBreakerConfig()
    metrics: MetricsConfig = MetricsConfig()
    tracing: TracingConfig = TracingConfig()


@lru_cache(maxsize=1)
def get_config() -> ServiceConfig:
    """Get service configuration (cached singleton)."""
    return ServiceConfig()
