"""Configuration management for canonicalizer-normalizer service."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class KafkaSettings(BaseSettings):
    """Kafka configuration."""
    model_config = SettingsConfigDict(env_prefix="KAFKA_", case_sensitive=False, extra="ignore")

    brokers: str = "localhost:9092"
    schema_registry_url: str = "http://localhost:8081"
    consumer_group: str = "canonicalizer-service-group"
    input_topic: str = "news_validated"
    output_topic: str = "news_canonical"
    dlq_topic: str = "news_canonical_dlq"
    processing_timeout_seconds: int = 20
    max_poll_interval_ms: int = 300000


class PostgresSettings(BaseSettings):
    """PostgreSQL configuration."""
    model_config = SettingsConfigDict(env_prefix="POSTGRES_", case_sensitive=False, extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    database: str = "canonicalizer"
    pool_size: int = 10
    max_overflow: int = 20

    @property
    def dsn(self) -> str:
        """Get PostgreSQL DSN."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class RedisSettings(BaseSettings):
    """Redis configuration."""
    model_config = SettingsConfigDict(env_prefix="REDIS_", case_sensitive=False, extra="ignore")

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    url_cache_ttl_seconds: int = 604800  # 7 days
    publisher_cache_ttl_seconds: int = 86400  # 24 hours


class NormalizationSettings(BaseSettings):
    """Normalization pipeline configuration."""
    model_config = SettingsConfigDict(env_prefix="NORMALIZATION_", case_sensitive=False, extra="ignore")

    redirect_max_hops: int = 3
    redirect_timeout_seconds: int = 5
    fuzzy_dedup_threshold: float = 0.90
    fuzzy_dedup_time_window_hours: int = 48
    normalization_score_accept: float = 0.85
    normalization_score_review: float = 0.70
    ml_classifier_enabled: bool = False
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60


class ServiceSettings(BaseSettings):
    """Service configuration."""
    model_config = SettingsConfigDict(env_prefix="SERVICE_", case_sensitive=False, extra="ignore")

    app_name: str = "canonicalizer-normalizer-service"
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8103
    prometheus_port: int = 9103
    geolocation_service_url: Optional[str] = None


class Settings(BaseSettings):
    """Main settings class."""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    kafka: KafkaSettings = KafkaSettings()
    postgres: PostgresSettings = PostgresSettings()
    redis: RedisSettings = RedisSettings()
    normalization: NormalizationSettings = NormalizationSettings()
    service: ServiceSettings = ServiceSettings()


def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()

