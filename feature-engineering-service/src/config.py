"""Configuration management for feature-engineering-service."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class KafkaConfig(BaseSettings):
    """Kafka configuration."""

    brokers: str = Field(default="154.53.166.231:9092", alias="KAFKA_BROKERS")
    schema_registry_url: str = Field(
        default="http://154.53.166.231:8081", alias="SCHEMA_REGISTRY_URL"
    )
    consumer_group: str = Field(
        default="feature-engineering-group", alias="CONSUMER_GROUP"
    )
    input_topic: str = Field(default="semantic_groups", alias="KAFKA_INPUT_TOPIC")
    output_topic: str = Field(default="features_computed", alias="KAFKA_OUTPUT_TOPIC")
    max_poll_records: int = Field(default=100, alias="KAFKA_MAX_POLL_RECORDS")
    session_timeout_ms: int = Field(default=30000, alias="KAFKA_SESSION_TIMEOUT_MS")
    auto_offset_reset: str = Field(
        default="earliest",
        alias="KAFKA_AUTO_OFFSET_RESET",
        description="What to do when there is no initial offset or offset is out of range: earliest, latest, none"
    )
    max_poll_interval_ms: int = Field(
        default=300000,
        alias="KAFKA_MAX_POLL_INTERVAL_MS",
        description="Maximum time between polls before consumer is considered dead (5 minutes)"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class PostgresConfig(BaseSettings):
    """PostgreSQL configuration."""

    host: str = Field(default="154.53.166.231", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    user: str = Field(default="adminsentiment", alias="POSTGRES_USER")
    password: str = Field(default="wp2400!!!!", alias="POSTGRES_PASSWORD")
    database: str = Field(default="sentiment", alias="POSTGRES_DATABASE")
    pool_size: int = Field(default=10, alias="POSTGRES_POOL_SIZE")
    max_overflow: int = Field(default=20, alias="POSTGRES_MAX_OVERFLOW")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    @property
    def connection_string(self) -> str:
        """Build PostgreSQL connection string."""
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


class RedisConfig(BaseSettings):
    """Redis configuration."""

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    db: int = Field(default=0, alias="REDIS_DB")
    password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    ssl: bool = Field(default=False, alias="REDIS_SSL")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class QdrantConfig(BaseSettings):
    """Qdrant configuration."""

    host: str = Field(default="localhost", alias="QDRANT_HOST")
    port: int = Field(default=6333, alias="QDRANT_PORT")
    collection_name: str = Field(default="news_embeddings_v1", alias="QDRANT_COLLECTION_NAME")
    vector_size: int = Field(default=768, alias="QDRANT_VECTOR_SIZE")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class FeastConfig(BaseSettings):
    """Feast configuration."""

    repo_path: str = Field(default=".", alias="FEAST_REPO_PATH")
    registry_path: str = Field(default="registry.db", alias="FEAST_REGISTRY_PATH")
    offline_store: str = Field(default="delta", alias="FEAST_OFFLINE_STORE")
    online_store: str = Field(default="redis", alias="FEAST_ONLINE_STORE")
    feature_version: str = Field(default="v1.0", alias="FEATURE_VERSION")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class FeastHTTPConfig(BaseSettings):
    """Feast HTTP server configuration for remote feature store."""

    server_url: str = Field(
        default="http://154.53.166.231:6566",
        alias="FEAST_SERVER_URL"
    )
    timeout: int = Field(default=10, alias="FEAST_TIMEOUT")
    max_retries: int = Field(default=3, alias="FEAST_MAX_RETRIES")
    push_source_name: str = Field(
        default="semantic_group_push_source",
        alias="FEAST_PUSH_SOURCE_NAME"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class FeatureConfig(BaseSettings):
    """Feature computation configuration."""

    drift_detection_enabled: bool = Field(default=True, alias="DRIFT_DETECTION_ENABLED")
    drift_threshold: float = Field(default=0.05, alias="DRIFT_THRESHOLD")
    reconciliation_enabled: bool = Field(
        default=True, alias="RECONCILIATION_ENABLED"
    )
    reconciliation_interval_hours: int = Field(
        default=24, alias="RECONCILIATION_INTERVAL_HOURS"
    )
    batch_size: int = Field(default=100, alias="FEATURE_BATCH_SIZE")
    validation_enabled: bool = Field(default=True, alias="VALIDATION_ENABLED")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class MonitoringConfig(BaseSettings):
    """Monitoring configuration."""

    prometheus_port: int = Field(default=9106, alias="PROMETHEUS_PORT")
    jaeger_host: str = Field(default="localhost", alias="JAEGER_HOST")
    jaeger_port: int = Field(default=6831, alias="JAEGER_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class Config(BaseSettings):
    """Main configuration class."""

    kafka: KafkaConfig = KafkaConfig()
    postgres: PostgresConfig = PostgresConfig()
    redis: RedisConfig = RedisConfig()
    qdrant: QdrantConfig = QdrantConfig()
    feast: FeastConfig = FeastConfig()
    feature: FeatureConfig = FeatureConfig()
    monitoring: MonitoringConfig = MonitoringConfig()

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global config instance
config = Config()

