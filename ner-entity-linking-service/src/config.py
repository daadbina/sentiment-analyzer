"""Configuration management for NER Entity Linking Service."""

import os
from pathlib import Path
from typing import Dict, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, ConfigDict
from dotenv import load_dotenv

# Load .env file from the service directory (absolute path) FIRST
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# Explicitly load the .env file BEFORE anything else
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)


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

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")


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

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")


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

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")


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
    min_entity_length: int = Field(
        default=2, env="MIN_ENTITY_LENGTH", description="Minimum entity text length"
    )
    cooccurrence_threshold: int = Field(
        default=3, env="COOCCURRENCE_THRESHOLD", description="Minimum co-occurrence count for entity clustering"
    )
    entity_linking_cache_ttl_seconds: int = Field(
        default=2592000, env="ENTITY_LINKING_CACHE_TTL_SECONDS", description="Cache TTL in seconds (default 30 days)"
    )

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")


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
    wikidata_timeout_seconds: int = Field(default=30, env="WIKIDATA_TIMEOUT_SECONDS")
    dbpedia_timeout_seconds: int = Field(default=30, env="DBPEDIA_TIMEOUT_SECONDS")
    circuit_breaker_threshold: int = Field(
        default=5, env="CIRCUIT_BREAKER_THRESHOLD"
    )
    circuit_breaker_timeout: int = Field(
        default=60, env="CIRCUIT_BREAKER_TIMEOUT"
    )

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")


class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration."""

    prometheus_port: int = Field(default=9104, env="PROMETHEUS_PORT")
    jaeger_enabled: bool = Field(default=False, env="JAEGER_ENABLED")
    jaeger_agent_host: str = Field(default="localhost", env="JAEGER_AGENT_HOST")
    jaeger_agent_port: int = Field(default=6831, env="JAEGER_AGENT_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    json_logs: bool = Field(default=True, env="JSON_LOGS")

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")


class ServiceConfig(BaseSettings):
    """Main service configuration."""

    service_name: str = Field(default="ner-entity-linking-service", env="SERVICE_NAME")
    service_version: str = Field(default="1.0.0", env="SERVICE_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    ner: NERConfig = Field(default_factory=NERConfig)
    external_apis: ExternalAPIsConfig = Field(default_factory=ExternalAPIsConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__"
    )


def get_config() -> ServiceConfig:
    """Get service configuration."""
    # Create nested configs using model_construct to read from os.environ
    kafka_config = KafkaConfig.model_construct(
        brokers=os.getenv("KAFKA_BROKERS", "localhost:9092"),
        consumer_group=os.getenv("CONSUMER_GROUP", "ner-service-group"),
        schema_registry_url=os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081"),
        input_topic=os.getenv("KAFKA_INPUT_TOPIC", "news_canonical"),
        output_topic=os.getenv("KAFKA_OUTPUT_TOPIC", "entities_extracted"),
        auto_offset_reset=os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest"),
        session_timeout_ms=int(os.getenv("KAFKA_SESSION_TIMEOUT_MS", "30000"))
    )

    postgres_config = PostgresConfig.model_construct(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        database=os.getenv("POSTGRES_DATABASE", "sentiment"),
        pool_size=int(os.getenv("POSTGRES_POOL_SIZE", "20")),
        max_overflow=int(os.getenv("POSTGRES_MAX_OVERFLOW", "10")),
        ssl_mode=os.getenv("POSTGRES_SSL_MODE", "prefer")
    )

    redis_config = RedisConfig.model_construct(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD", ""),
        db=int(os.getenv("REDIS_DB", "0")),
        socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
        socket_connect_timeout=int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5")),
        entity_linking_cache_ttl_seconds=int(os.getenv("ENTITY_LINKING_CACHE_TTL_SECONDS", "2592000"))
    )

    ner_config = NERConfig.model_construct(
        confidence_threshold_default=float(os.getenv("NER_CONFIDENCE_THRESHOLD_DEFAULT", "0.85")),
        entity_linking_confidence_threshold=float(os.getenv("ENTITY_LINKING_CONFIDENCE_THRESHOLD", "0.75")),
        coverage_threshold_en=float(os.getenv("COVERAGE_THRESHOLD_EN", "0.80")),
        coverage_threshold_other=float(os.getenv("COVERAGE_THRESHOLD_OTHER", "0.70")),
        fuzzy_match_similarity_threshold=float(os.getenv("FUZZY_MATCH_SIMILARITY_THRESHOLD", "0.90")),
        model_cache_size=int(os.getenv("MODEL_CACHE_SIZE", "5")),
        min_entity_length=int(os.getenv("MIN_ENTITY_LENGTH", "2")),
        cooccurrence_threshold=int(os.getenv("COOCCURRENCE_THRESHOLD", "3")),
        entity_linking_cache_ttl_seconds=int(os.getenv("ENTITY_LINKING_CACHE_TTL_SECONDS", "2592000"))
    )

    external_apis_config = ExternalAPIsConfig.model_construct(
        wikidata_api_url=os.getenv("WIKIDATA_API_URL", "https://query.wikidata.org/sparql"),
        dbpedia_spotlight_url=os.getenv("DBPEDIA_SPOTLIGHT_URL", "https://api.dbpedia-spotlight.org/en/annotate"),
        opensanctions_api_url=os.getenv("OPENSANCTIONS_API_URL", ""),
        wikidata_timeout_seconds=int(os.getenv("WIKIDATA_TIMEOUT_SECONDS", "30")),
        dbpedia_timeout_seconds=int(os.getenv("DBPEDIA_TIMEOUT_SECONDS", "30")),
        circuit_breaker_threshold=int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5")),
        circuit_breaker_timeout=int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))
    )

    monitoring_config = MonitoringConfig.model_construct(
        prometheus_port=int(os.getenv("PROMETHEUS_PORT", "9104")),
        jaeger_enabled=os.getenv("JAEGER_ENABLED", "false").lower() == "true",
        jaeger_agent_host=os.getenv("JAEGER_AGENT_HOST", "localhost"),
        jaeger_agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        json_logs=os.getenv("JSON_LOGS", "true").lower() == "true"
    )

    # Create service config with pre-instantiated nested configs
    return ServiceConfig(
        service_name=os.getenv("SERVICE_NAME", "ner-entity-linking-service"),
        service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        kafka=kafka_config,
        postgres=postgres_config,
        redis=redis_config,
        ner=ner_config,
        external_apis=external_apis_config,
        monitoring=monitoring_config
    )

