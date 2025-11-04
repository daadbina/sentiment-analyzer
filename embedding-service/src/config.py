"""Configuration management for Embedding Service."""

from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class KafkaConfig:
    """Kafka configuration."""

    brokers: str = os.getenv("KAFKA_BROKERS", "154.53.166.231:9092")
    consumer_group: str = os.getenv("CONSUMER_GROUP", "embedding-service-group")
    schema_registry_url: str = os.getenv(
        "SCHEMA_REGISTRY_URL", "http://154.53.166.231:8081"
    )
    input_topic: str = os.getenv("KAFKA_INPUT_TOPIC", "news_canonical")
    output_topic: str = os.getenv("KAFKA_OUTPUT_TOPIC", "embeddings")
    max_poll_interval_ms: int = int(
        os.getenv("MAX_POLL_INTERVAL_MS", "300000")
    )
    processing_timeout_seconds: int = int(
        os.getenv("PROCESSING_TIMEOUT_SECONDS", "30")
    )


@dataclass(frozen=True)
class PostgresConfig:
    """PostgreSQL configuration."""

    host: str = os.getenv("POSTGRES_HOST", "154.53.166.231")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    user: str = os.getenv("POSTGRES_USER", "adminsentiment")
    password: str = os.getenv("POSTGRES_PASSWORD", "wp2400!!!!")
    database: str = os.getenv("POSTGRES_DB", "sentiment")
    min_pool_size: int = int(os.getenv("DB_MIN_POOL_SIZE", "5"))
    max_pool_size: int = int(os.getenv("DB_MAX_POOL_SIZE", "20"))

    @property
    def dsn(self) -> str:
        """PostgreSQL connection string."""
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


@dataclass(frozen=True)
class QdrantConfig:
    """Qdrant configuration."""

    host: str = os.getenv("QDRANT_HOST", "localhost")
    port: int = int(os.getenv("QDRANT_PORT", "6333"))
    api_key: Optional[str] = os.getenv("QDRANT_API_KEY")
    collection_name: str = os.getenv(
        "QDRANT_COLLECTION_NAME", "news_embeddings_v1"
    )
    vector_size: int = int(os.getenv("QDRANT_VECTOR_SIZE", "768"))


@dataclass(frozen=True)
class RedisConfig:
    """Redis configuration."""

    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")
    db: int = int(os.getenv("REDIS_DB", "0"))
    cache_ttl_seconds: int = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "86400"))
    socket_timeout: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))


@dataclass(frozen=True)
class ModelConfig:
    """Model configuration."""

    cache_dir: str = os.getenv("MODEL_CACHE_DIR", "/models")
    default_model: str = os.getenv(
        "DEFAULT_MODEL_NAME", "paraphrase-multilingual-mpnet-base-v2"
    )
    max_sequence_length: int = int(os.getenv("MAX_SEQUENCE_LENGTH", "384"))
    batch_size_gpu: int = int(os.getenv("BATCH_SIZE_GPU", "32"))
    batch_size_cpu: int = int(os.getenv("BATCH_SIZE_CPU", "8"))
    batch_timeout_ms: int = int(os.getenv("BATCH_TIMEOUT_MS", "100"))
    device: str = os.getenv("DEVICE", "auto")
    gpu_memory_fraction: float = float(
        os.getenv("GPU_MEMORY_FRACTION", "0.8")
    )
    model_pool_size: int = int(os.getenv("MODEL_POOL_SIZE", "3"))


@dataclass(frozen=True)
class ValidationConfig:
    """Validation configuration."""

    enabled: bool = os.getenv("EMBEDDING_VALIDATION_ENABLED", "true").lower() == "true"
    drift_detection_enabled: bool = (
        os.getenv("DRIFT_DETECTION_ENABLED", "true").lower() == "true"
    )
    drift_sample_size: int = int(
        os.getenv("DRIFT_DETECTION_SAMPLE_SIZE", "1000")
    )
    drift_threshold: float = float(os.getenv("DRIFT_THRESHOLD", "0.05"))


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    timeout_seconds: int = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))


@dataclass(frozen=True)
class MetricsConfig:
    """Metrics configuration."""

    prometheus_port: int = int(os.getenv("PROMETHEUS_PORT", "9105"))
    enabled: bool = True


@dataclass(frozen=True)
class Config:
    """Main configuration class."""

    kafka: KafkaConfig = KafkaConfig()
    postgres: PostgresConfig = PostgresConfig()
    qdrant: QdrantConfig = QdrantConfig()
    redis: RedisConfig = RedisConfig()
    model: ModelConfig = ModelConfig()
    validation: ValidationConfig = ValidationConfig()
    circuit_breaker: CircuitBreakerConfig = CircuitBreakerConfig()
    metrics: MetricsConfig = MetricsConfig()
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    environment: str = os.getenv("ENVIRONMENT", "development")

    def __post_init__(self):
        """Validate configuration on initialization."""
        if self.model.gpu_memory_fraction < 0.0 or self.model.gpu_memory_fraction > 1.0:
            raise ValueError("GPU memory fraction must be between 0.0 and 1.0")
        if self.model.batch_size_gpu < 1:
            raise ValueError("Batch size must be at least 1")
        if self.model.batch_size_cpu < 1:
            raise ValueError("Batch size must be at least 1")


# Global config instance
config = Config()

