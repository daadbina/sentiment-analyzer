"""Configuration management for NER Entity Linking Service."""

import os
from typing import Dict, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class KafkaConfig(BaseSettings):
    """Kafka configuration."""

    brokers: str = Field(default="localhost:9092", env="KAFKA_BROKERS")
    consumer_group: str = Field(default="ner-service-group", env="CONSUMER_GROUP")
    schema_registry_url: str = Field(
        default="http://localhost:8081", env="SCHEMA_REGISTRY_URL"
    )
    input_topic: str = Field(default="news_canonical", env="KAFKA_INPUT_TOPIC")
    output_topic: str = Field(default="entities_extracted", env="KAFKA_OUTPUT_TOPIC")
    auto_offset_reset: str = Field(default="earliest", env="KAFKA_AUTO_OFFSET_RESET")
    session_timeout_ms: int = Field(default=30000, env="KAFKA_SESSION_TIMEOUT_MS")
    request_timeout_ms: int = Field(default=40000, env="KAFKA_REQUEST_TIMEOUT_MS")

    class Config:
        env_file = ".env"
        case_sensitive = False


class PostgresConfig(BaseSettings):
    """PostgreSQL configuration."""

    host: str = Field(default="localhost", env="POSTGRES_HOST")
    port: int = Field(default=5432, env="POSTGRES_PORT")
    user: str = Field(default="postgres", env="POSTGRES_USER")
    password: str = Field(default="", env="POSTGRES_PASSWORD")
    database: str = Field(default="sentiment", env="POSTGRES_DATABASE")
    pool_size: int = Field(default=20, env="POSTGRES_POOL_SIZE")
    max_overflow: int = Field(default=10, env="POSTGRES_MAX_OVERFLOW")
    ssl_mode: str = Field(default="prefer", env="POSTGRES_SSL_MODE")

    @property
    def connection_string(self) -> str:
        """Build PostgreSQL connection string."""
        return (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        )

    @property
    def async_connection_string(self) -> str:
        """Build async PostgreSQL connection string."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = False


class RedisConfig(BaseSettings):
    """Redis configuration."""

    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    db: int = Field(default=0, env="REDIS_DB")
    password: str = Field(default="", env="REDIS_PASSWORD")
    cache_ttl_seconds: int = Field(
        default=2592000, env="ENTITY_LINKING_CACHE_TTL_SECONDS"
    )  # 30 days
    socket_connect_timeout: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")

    @property
    def connection_url(self) -> str:
        """Build Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

    class Config:
        env_file = ".env"
        case_sensitive = False


class NERConfig(BaseSettings):
    """NER model configuration."""

    confidence_threshold_default: float = Field(
        default=0.80, env="NER_CONFIDENCE_THRESHOLD_DEFAULT"
    )
    entity_linking_confidence_threshold: float = Field(
        default=0.75, env="ENTITY_LINKING_CONFIDENCE_THRESHOLD"
    )
    coverage_threshold_en: float = Field(default=0.80, env="COVERAGE_THRESHOLD_EN")
    coverage_threshold_other: float = Field(
        default=0.70, env="COVERAGE_THRESHOLD_OTHER"
    )
    fuzzy_match_similarity_threshold: float = Field(
        default=0.90, env="FUZZY_MATCH_SIMILARITY_THRESHOLD"
    )
    processing_timeout_seconds: int = Field(
        default=30, env="PROCESSING_TIMEOUT_SECONDS"
    )
    model_cache_size: int = Field(default=5, env="MODEL_CACHE_SIZE")

    class Config:
        env_file = ".env"
        case_sensitive = False


class ExternalAPIsConfig(BaseSettings):
    """External APIs configuration."""

    wikidata_api_url: str = Field(
        default="https://query.wikidata.org/sparql", env="WIKIDATA_API_URL"
    )
    dbpedia_spotlight_url: str = Field(
        default="https://api.dbpedia-spotlight.org/en/annotate",
        env="DBPEDIA_SPOTLIGHT_URL",
    )
    opensanctions_api_url: str = Field(
        default="", env="OPENSANCTIONS_API_URL"
    )
    wikidata_timeout_seconds: int = Field(default=10, env="WIKIDATA_TIMEOUT_SECONDS")
    dbpedia_timeout_seconds: int = Field(default=10, env="DBPEDIA_TIMEOUT_SECONDS")
    circuit_breaker_threshold: int = Field(
        default=5, env="CIRCUIT_BREAKER_THRESHOLD"
    )
    circuit_breaker_timeout: int = Field(
        default=60, env="CIRCUIT_BREAKER_TIMEOUT"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration."""

    prometheus_port: int = Field(default=9104, env="PROMETHEUS_PORT")
    jaeger_enabled: bool = Field(default=False, env="JAEGER_ENABLED")
    jaeger_agent_host: str = Field(default="localhost", env="JAEGER_AGENT_HOST")
    jaeger_agent_port: int = Field(default=6831, env="JAEGER_AGENT_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    json_logs: bool = Field(default=True, env="JSON_LOGS")

    class Config:
        env_file = ".env"
        case_sensitive = False


class ServiceConfig(BaseSettings):
    """Main service configuration."""

    service_name: str = Field(default="ner-entity-linking-service", env="SERVICE_NAME")
    service_version: str = Field(default="1.0.0", env="SERVICE_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    kafka: KafkaConfig = KafkaConfig()
    postgres: PostgresConfig = PostgresConfig()
    redis: RedisConfig = RedisConfig()
    ner: NERConfig = NERConfig()
    external_apis: ExternalAPIsConfig = ExternalAPIsConfig()
    monitoring: MonitoringConfig = MonitoringConfig()

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_config() -> ServiceConfig:
    """Get service configuration."""
    return ServiceConfig()

