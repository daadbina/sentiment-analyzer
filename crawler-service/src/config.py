"""
Configuration management for Crawler Service.

Handles environment variables, Vault integration, and application settings.
Implements dependency injection for HTTP client, Kafka producer, and other services.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field, validator


class CrawlerSettings(BaseSettings):
    """
    Crawler Service configuration settings.

    All settings can be overridden via environment variables.
    """

    # Crawling Configuration
    crawl_interval_minutes: int = Field(
        default=30,
        description="Crawl frequency in minutes",
        env="CRAWL_INTERVAL_MINUTES",
    )
    max_concurrent_requests: int = Field(
        default=50,
        description="Maximum concurrent HTTP requests",
        env="MAX_CONCURRENT_REQUESTS",
    )
    request_timeout_seconds: int = Field(
        default=10,
        description="HTTP request timeout in seconds",
        env="REQUEST_TIMEOUT_SECONDS",
    )
    retry_backoff_seconds: int = Field(
        default=30,
        description="Initial backoff interval for retries in seconds",
        env="RETRY_BACKOFF_SECONDS",
    )
    max_retries: int = Field(
        default=5,
        description="Maximum retry attempts for failed requests",
        env="MAX_RETRIES",
    )

    # Language Detection Configuration
    lang_conf_threshold: float = Field(
        default=0.8,
        description="Minimum language detection confidence threshold",
        env="LANG_CONF_THRESHOLD",
    )

    # Schema Configuration
    schema_version: str = Field(
        default="v1.0",
        description="Current schema version tag",
        env="SCHEMA_VERSION",
    )

    # Kafka Configuration
    kafka_brokers: str = Field(
        default="localhost:9092",
        description="Kafka broker addresses (comma-separated)",
        env="KAFKA_BROKERS",
    )
    kafka_topic: str = Field(
        default="news_raw",
        description="Output Kafka topic name",
        env="KAFKA_TOPIC",
    )
    kafka_acks: str = Field(
        default="all",
        description="Kafka acknowledgement level (all, leader, none)",
        env="KAFKA_ACKS",
    )
    kafka_max_retries: int = Field(
        default=5,
        description="Kafka producer retry attempts",
        env="KAFKA_MAX_RETRIES",
    )
    kafka_dlq_topic: str = Field(
        default="news_raw_dlq",
        description="Dead-letter queue topic for failed messages",
        env="KAFKA_DLQ_TOPIC",
    )

    # Schema Registry Configuration
    schema_registry_url: str = Field(
        default="http://localhost:8081",
        description="Schema Registry URL",
        env="SCHEMA_REGISTRY_URL",
    )

    # Database Configuration (PostgreSQL/TimescaleDB)
    postgres_host: str = Field(
        default="localhost",
        description="PostgreSQL host",
        env="POSTGRES_HOST",
    )
    postgres_port: int = Field(
        default=5432,
        description="PostgreSQL port",
        env="POSTGRES_PORT",
    )
    postgres_user: str = Field(
        default="crawler",
        description="PostgreSQL user",
        env="POSTGRES_USER",
    )
    postgres_password: str = Field(
        default="crawler_password",
        description="PostgreSQL password",
        env="POSTGRES_PASSWORD",
    )
    postgres_db: str = Field(
        default="crawler_db",
        description="PostgreSQL database name",
        env="POSTGRES_DB",
    )
    db_min_pool_size: int = Field(
        default=5,
        description="Minimum database connection pool size",
        env="DB_MIN_POOL_SIZE",
    )
    db_max_pool_size: int = Field(
        default=20,
        description="Maximum database connection pool size",
        env="DB_MAX_POOL_SIZE",
    )

    # Monitoring Configuration
    prometheus_port: int = Field(
        default=9101,
        description="Prometheus metrics endpoint port",
        env="PROMETHEUS_PORT",
    )
    prometheus_host: str = Field(
        default="127.0.0.1",  # nosec B104 - Changed from 0.0.0.0 for security
        description="Prometheus metrics endpoint host",
        env="PROMETHEUS_HOST",
    )

    # Jaeger Tracing Configuration
    jaeger_enabled: bool = Field(
        default=False,
        description="Enable Jaeger distributed tracing",
        env="JAEGER_ENABLED",
    )
    jaeger_agent_host: str = Field(
        default="localhost",
        description="Jaeger agent host",
        env="JAEGER_AGENT_HOST",
    )
    jaeger_agent_port: int = Field(
        default=6831,
        description="Jaeger agent port",
        env="JAEGER_AGENT_PORT",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        env="LOG_LEVEL",
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)",
        env="LOG_FORMAT",
    )

    # Application Configuration
    app_name: str = Field(
        default="crawler-service",
        description="Application name",
        env="APP_NAME",
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version",
        env="APP_VERSION",
    )
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
        env="ENVIRONMENT",
    )

    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = Field(
        default=3,
        description="Number of failures before circuit breaker opens",
        env="CIRCUIT_BREAKER_FAILURE_THRESHOLD",
    )
    circuit_breaker_timeout_minutes: int = Field(
        default=10,
        description="Circuit breaker timeout in minutes",
        env="CIRCUIT_BREAKER_TIMEOUT_MINUTES",
    )

    # Deduplication Configuration
    dedup_cache_size: int = Field(
        default=10000,
        description="Maximum size of deduplication cache",
        env="DEDUP_CACHE_SIZE",
    )

    # Proxy Configuration
    http_proxy: str = Field(
        default="",
        description="HTTP proxy URL (optional)",
        env="HTTP_PROXY",
    )
    https_proxy: str = Field(
        default="",
        description="HTTPS proxy URL (optional)",
        env="HTTPS_PROXY",
    )
    no_proxy: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated list of hosts to bypass proxy",
        env="NO_PROXY",
    )

    @validator("lang_conf_threshold")
    def validate_lang_conf_threshold(cls, v: float) -> float:
        """Validate language confidence threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("lang_conf_threshold must be between 0 and 1")
        return v

    @validator("prometheus_port")
    def validate_prometheus_port(cls, v: int) -> int:
        """Validate Prometheus port is in valid range."""
        if not 1024 <= v <= 65535:
            raise ValueError("prometheus_port must be between 1024 and 65535")
        return v

    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @property
    def database_url(self) -> str:
        """
        Get PostgreSQL connection URL.

        Returns:
            str: Database connection URL.
        """
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> CrawlerSettings:
    """
    Get cached application settings.

    Returns:
        CrawlerSettings: Application configuration instance.
    """
    return CrawlerSettings()


def get_config_dict() -> dict:
    """
    Get configuration as dictionary.

    Returns:
        dict: Configuration dictionary.
    """
    settings = get_settings()
    return settings.model_dump()
