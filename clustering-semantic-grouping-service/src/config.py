"""Configuration management for clustering service."""

import os
import logging
from typing import Optional
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file from the service root directory
env_file = Path(__file__).parent.parent / ".env"
logger.info(f"Looking for .env file at: {env_file}")
if env_file.exists():
    logger.info(f"Loading .env file from: {env_file}")
    load_dotenv(env_file, override=True)
    logger.info(f"QDRANT_PORT after load_dotenv: {os.getenv('QDRANT_PORT')}")
else:
    logger.warning(f".env file not found at: {env_file}")


class KafkaConfig(BaseSettings):
    """Kafka configuration."""
    brokers: str = Field(default=None)
    schema_registry_url: str = Field(default=None)
    input_topic: str = Field(default=None)
    output_topic: str = Field(default=None)
    consumer_group: str = Field(default=None)
    max_poll_interval_ms: int = Field(default=0)
    processing_timeout_seconds: int = Field(default=0)

    class Config:
        env_prefix = ""
        case_sensitive = False

    def __init__(self, **data):
        # Load from environment if not provided
        if not data.get("brokers"):
            data["brokers"] = os.getenv("KAFKA_BROKERS")
        if not data.get("schema_registry_url"):
            data["schema_registry_url"] = os.getenv("SCHEMA_REGISTRY_URL")
        if not data.get("input_topic"):
            data["input_topic"] = os.getenv("KAFKA_INPUT_TOPIC")
        if not data.get("output_topic"):
            data["output_topic"] = os.getenv("KAFKA_OUTPUT_TOPIC")
        if not data.get("consumer_group"):
            data["consumer_group"] = os.getenv("KAFKA_CONSUMER_GROUP")
        if not data.get("max_poll_interval_ms"):
            val = os.getenv("MAX_POLL_INTERVAL_MS")
            data["max_poll_interval_ms"] = int(val) if val else 0
        if not data.get("processing_timeout_seconds"):
            val = os.getenv("PROCESSING_TIMEOUT_SECONDS")
            data["processing_timeout_seconds"] = int(val) if val else 0

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
    host: str = Field(default=None)
    port: int = Field(default=0)
    collection_name: str = Field(default=None)
    vector_size: int = Field(default=0)
    timeout: int = Field(default=0)

    class Config:
        env_prefix = ""
        case_sensitive = False

    def __init__(self, **data):
        # Load from environment if not provided
        if not data.get("host"):
            data["host"] = os.getenv("QDRANT_HOST")
        if not data.get("port"):
            val = os.getenv("QDRANT_PORT")
            logger.info(f"QDRANT_PORT env var: {val}")
            data["port"] = int(val) if val else 0
            logger.info(f"QDRANT_PORT after conversion: {data['port']}")
        if not data.get("collection_name"):
            data["collection_name"] = os.getenv("QDRANT_COLLECTION_NAME")
        if not data.get("vector_size"):
            val = os.getenv("QDRANT_VECTOR_SIZE")
            data["vector_size"] = int(val) if val else 0
        if not data.get("timeout"):
            val = os.getenv("QDRANT_TIMEOUT")
            data["timeout"] = int(val) if val else 0

        super().__init__(**data)
        logger.info(f"QdrantConfig initialized: host={self.host}, port={self.port}, collection={self.collection_name}")

        if not self.host:
            raise ValueError("QDRANT_HOST environment variable is required")
        if self.port == 0:
            raise ValueError(f"QDRANT_PORT environment variable is required (got {self.port})")
        if not self.collection_name:
            raise ValueError("QDRANT_COLLECTION_NAME environment variable is required")
        if self.vector_size == 0:
            raise ValueError("QDRANT_VECTOR_SIZE environment variable is required")
        if self.timeout == 0:
            raise ValueError("QDRANT_TIMEOUT environment variable is required")


class PostgresConfig(BaseSettings):
    """PostgreSQL configuration."""
    host: str = Field(default=None)
    port: int = Field(default=0)
    user: str = Field(default=None)
    password: str = Field(default=None)
    database: str = Field(default=None)
    min_pool_size: int = Field(default=0)
    max_pool_size: int = Field(default=0)

    class Config:
        env_prefix = ""
        case_sensitive = False

    def __init__(self, **data):
        # Load from environment if not provided
        if not data.get("host"):
            data["host"] = os.getenv("POSTGRES_HOST")
        if not data.get("port"):
            val = os.getenv("POSTGRES_PORT")
            data["port"] = int(val) if val else 0
        if not data.get("user"):
            data["user"] = os.getenv("POSTGRES_USER")
        if not data.get("password"):
            data["password"] = os.getenv("POSTGRES_PASSWORD")
        if not data.get("database"):
            data["database"] = os.getenv("POSTGRES_DB")
        if not data.get("min_pool_size"):
            val = os.getenv("DB_MIN_POOL_SIZE")
            data["min_pool_size"] = int(val) if val else 0
        if not data.get("max_pool_size"):
            val = os.getenv("DB_MAX_POOL_SIZE")
            data["max_pool_size"] = int(val) if val else 0

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
    host: str = Field(default=None)
    port: int = Field(default=0)
    password: Optional[str] = Field(default=None)
    cache_ttl_seconds: int = Field(default=0)
    db: int = Field(default=0)
    socket_timeout: int = Field(default=0)

    class Config:
        env_prefix = ""
        case_sensitive = False

    def __init__(self, **data):
        # Load from environment if not provided
        if not data.get("host"):
            data["host"] = os.getenv("REDIS_HOST")
        if not data.get("port"):
            val = os.getenv("REDIS_PORT")
            data["port"] = int(val) if val else 0
        if data.get("password") is None:
            data["password"] = os.getenv("REDIS_PASSWORD")
        if not data.get("cache_ttl_seconds"):
            val = os.getenv("REDIS_CACHE_TTL_SECONDS")
            data["cache_ttl_seconds"] = int(val) if val else 0
        if not data.get("db"):
            val = os.getenv("REDIS_DB")
            data["db"] = int(val) if val else 0
        if not data.get("socket_timeout"):
            val = os.getenv("REDIS_SOCKET_TIMEOUT")
            data["socket_timeout"] = int(val) if val else 0

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
    algorithm: str = Field(default=None)
    min_cluster_size: int = Field(default=0)
    min_samples: int = Field(default=0)
    cluster_selection_epsilon: float = Field(default=0.0)
    metric: str = Field(default=None)
    similarity_threshold: float = Field(default=0.0)
    max_cluster_size: int = Field(default=0)
    time_window_hours: int = Field(default=0)
    overlap_hours: int = Field(default=0)
    execution_frequency_hours: int = Field(default=0)
    outlier_k_neighbors: int = Field(default=0)
    outlier_distance_threshold: float = Field(default=0.0)
    incremental_merge_threshold: float = Field(default=0.0)
    stability_min_score: float = Field(default=0.0)
    stability_history_window: int = Field(default=0)

    class Config:
        env_prefix = ""
        case_sensitive = False

    def __init__(self, **data):
        # Load from environment if not provided
        if not data.get("algorithm"):
            data["algorithm"] = os.getenv("CLUSTERING_ALGORITHM")
        if data.get("min_cluster_size") == 0:
            val = os.getenv("MIN_CLUSTER_SIZE")
            data["min_cluster_size"] = int(val) if val else 0
        if data.get("min_samples") == 0:
            val = os.getenv("MIN_SAMPLES")
            data["min_samples"] = int(val) if val else 0
        if data.get("cluster_selection_epsilon") == 0.0:
            val = os.getenv("CLUSTER_SELECTION_EPSILON")
            data["cluster_selection_epsilon"] = float(val) if val else 0.0
        if not data.get("metric"):
            data["metric"] = os.getenv("CLUSTERING_METRIC")
        if data.get("similarity_threshold") == 0.0:
            val = os.getenv("SIMILARITY_THRESHOLD")
            data["similarity_threshold"] = float(val) if val else 0.0
        if data.get("max_cluster_size") == 0:
            val = os.getenv("MAX_CLUSTER_SIZE")
            data["max_cluster_size"] = int(val) if val else 0
        if data.get("time_window_hours") == 0:
            val = os.getenv("TIME_WINDOW_HOURS")
            data["time_window_hours"] = int(val) if val else 0
        if data.get("overlap_hours") == 0:
            val = os.getenv("OVERLAP_HOURS")
            data["overlap_hours"] = int(val) if val else 0
        if data.get("execution_frequency_hours") == 0:
            val = os.getenv("EXECUTION_FREQUENCY_HOURS")
            data["execution_frequency_hours"] = int(val) if val else 0
        if data.get("outlier_k_neighbors") == 0:
            val = os.getenv("OUTLIER_K_NEIGHBORS")
            data["outlier_k_neighbors"] = int(val) if val else 0
        if data.get("outlier_distance_threshold") == 0.0:
            val = os.getenv("OUTLIER_DISTANCE_THRESHOLD")
            data["outlier_distance_threshold"] = float(val) if val else 0.0
        if data.get("incremental_merge_threshold") == 0.0:
            val = os.getenv("INCREMENTAL_MERGE_THRESHOLD")
            data["incremental_merge_threshold"] = float(val) if val else 0.0
        if data.get("stability_min_score") == 0.0:
            val = os.getenv("STABILITY_MIN_SCORE")
            data["stability_min_score"] = float(val) if val else 0.0
        if data.get("stability_history_window") == 0:
            val = os.getenv("STABILITY_HISTORY_WINDOW")
            data["stability_history_window"] = int(val) if val else 0

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
        if self.outlier_k_neighbors == 0:
            raise ValueError("OUTLIER_K_NEIGHBORS environment variable is required")
        if self.outlier_distance_threshold == 0.0:
            raise ValueError("OUTLIER_DISTANCE_THRESHOLD environment variable is required")
        if self.incremental_merge_threshold == 0.0:
            raise ValueError("INCREMENTAL_MERGE_THRESHOLD environment variable is required")
        if self.stability_min_score == 0.0:
            raise ValueError("STABILITY_MIN_SCORE environment variable is required")
        if self.stability_history_window == 0:
            raise ValueError("STABILITY_HISTORY_WINDOW environment variable is required")


class ValidationConfig(BaseSettings):
    """Validation configuration."""
    min_cluster_purity: float = Field(default=0.0)
    min_cluster_size: int = Field(default=0)
    max_time_span_hours: int = Field(default=0)
    min_sources: int = Field(default=0)
    language_consistency_threshold: float = Field(default=0.0)
    domain_consistency_threshold: float = Field(default=0.0)

    class Config:
        env_prefix = ""
        case_sensitive = False

    def __init__(self, **data):
        # Load from environment if not provided
        if data.get("min_cluster_purity") == 0.0:
            val = os.getenv("MIN_CLUSTER_PURITY")
            data["min_cluster_purity"] = float(val) if val else 0.0
        if data.get("min_cluster_size") == 0:
            val = os.getenv("MIN_CLUSTER_SIZE")
            data["min_cluster_size"] = int(val) if val else 0
        if data.get("max_time_span_hours") == 0:
            val = os.getenv("MAX_TIME_SPAN_HOURS")
            data["max_time_span_hours"] = int(val) if val else 0
        if data.get("min_sources") == 0:
            val = os.getenv("MIN_SOURCES")
            data["min_sources"] = int(val) if val else 0
        if data.get("language_consistency_threshold") == 0.0:
            val = os.getenv("LANGUAGE_CONSISTENCY_THRESHOLD")
            data["language_consistency_threshold"] = float(val) if val else 0.0
        if data.get("domain_consistency_threshold") == 0.0:
            val = os.getenv("DOMAIN_CONSISTENCY_THRESHOLD")
            data["domain_consistency_threshold"] = float(val) if val else 0.0

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
    environment: str = Field(default=None)
    log_level: str = Field(default=None)
    api_host: str = Field(default=None)
    api_port: int = Field(default=0)
    prometheus_port: int = Field(default=0)
    enable_tracing: str = Field(default=None)
    jaeger_host: str = Field(default=None)
    jaeger_port: int = Field(default=0)

    class Config:
        env_prefix = ""
        case_sensitive = False

    def __init__(self, **data):
        # Load from environment if not provided
        if not data.get("environment"):
            data["environment"] = os.getenv("ENVIRONMENT")
        if not data.get("log_level"):
            data["log_level"] = os.getenv("LOG_LEVEL")
        if not data.get("api_host"):
            data["api_host"] = os.getenv("API_HOST")
        if data.get("api_port") == 0:
            val = os.getenv("API_PORT")
            data["api_port"] = int(val) if val else 0
        if data.get("prometheus_port") == 0:
            val = os.getenv("PROMETHEUS_PORT")
            data["prometheus_port"] = int(val) if val else 0
        if not data.get("enable_tracing"):
            data["enable_tracing"] = os.getenv("ENABLE_TRACING")
        if not data.get("jaeger_host"):
            data["jaeger_host"] = os.getenv("JAEGER_HOST")
        if data.get("jaeger_port") == 0:
            val = os.getenv("JAEGER_PORT")
            data["jaeger_port"] = int(val) if val else 0

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
    """Main configuration class with lazy initialization."""

    _kafka: Optional[KafkaConfig] = None
    _qdrant: Optional[QdrantConfig] = None
    _postgres: Optional[PostgresConfig] = None
    _redis: Optional[RedisConfig] = None
    _clustering: Optional[ClusteringConfig] = None
    _validation: Optional[ValidationConfig] = None
    _service: Optional[ServiceConfig] = None

    @property
    def kafka(self) -> KafkaConfig:
        """Lazy load Kafka config."""
        if self._kafka is None:
            self._kafka = KafkaConfig()
        return self._kafka

    @property
    def qdrant(self) -> QdrantConfig:
        """Lazy load Qdrant config."""
        if self._qdrant is None:
            self._qdrant = QdrantConfig()
        return self._qdrant

    @property
    def postgres(self) -> PostgresConfig:
        """Lazy load PostgreSQL config."""
        if self._postgres is None:
            self._postgres = PostgresConfig()
        return self._postgres

    @property
    def redis(self) -> RedisConfig:
        """Lazy load Redis config."""
        if self._redis is None:
            self._redis = RedisConfig()
        return self._redis

    @property
    def clustering(self) -> ClusteringConfig:
        """Lazy load Clustering config."""
        if self._clustering is None:
            self._clustering = ClusteringConfig()
        return self._clustering

    @property
    def validation(self) -> ValidationConfig:
        """Lazy load Validation config."""
        if self._validation is None:
            self._validation = ValidationConfig()
        return self._validation

    @property
    def service(self) -> ServiceConfig:
        """Lazy load Service config."""
        if self._service is None:
            self._service = ServiceConfig()
        return self._service


# Global config instance
config = Config()

