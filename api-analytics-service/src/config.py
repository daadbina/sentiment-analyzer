"""Configuration management for API Analytics Service.

All configuration is loaded from environment variables.
No hardcoded values are allowed.
"""

from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgreSQLSettings(BaseSettings):
    """PostgreSQL database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    host: str = Field(
        ...,
        description="PostgreSQL host"
    )
    port: int = Field(
        default=5432,
        description="PostgreSQL port"
    )
    user: str = Field(
        ...,
        description="PostgreSQL username"
    )
    password: str = Field(
        ...,
        description="PostgreSQL password"
    )
    database: str = Field(
        ...,
        description="PostgreSQL database name"
    )
    pool_size: int = Field(
        default=50,
        description="Connection pool size"
    )
    max_overflow: int = Field(
        default=10,
        description="Maximum overflow connections"
    )
    pool_timeout: int = Field(
        default=30,
        description="Pool timeout in seconds"
    )


class Neo4jSettings(BaseSettings):
    """Neo4j database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    uri: str = Field(
        ...,
        description="Neo4j connection URI (bolt://...)"
    )
    user: str = Field(
        ...,
        description="Neo4j username"
    )
    password: str = Field(
        ...,
        description="Neo4j password"
    )
    pool_size: int = Field(
        default=50,
        description="Connection pool size"
    )
    connection_timeout: int = Field(
        default=30,
        description="Connection timeout in seconds"
    )


class RedisSettings(BaseSettings):
    """Redis cache configuration."""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    host: str = Field(
        default="localhost",
        description="Redis host"
    )
    port: int = Field(
        default=6379,
        description="Redis port"
    )
    db: int = Field(
        default=0,
        description="Redis database number"
    )
    password: Optional[str] = Field(
        default=None,
        description="Redis password"
    )
    pool_size: int = Field(
        default=50,
        description="Connection pool size"
    )


class JWTSettings(BaseSettings):
    """JWT authentication configuration."""

    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    secret_key: str = Field(
        ...,
        description="JWT signing secret key"
    )
    algorithm: str = Field(
        default="HS256",
        description="JWT algorithm"
    )
    expiration_hours: int = Field(
        default=24,
        description="Token expiration in hours"
    )


class CacheSettings(BaseSettings):
    """Cache configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    ttl_seconds: int = Field(
        default=3600,
        description="Cache TTL in seconds"
    )
    max_size: int = Field(
        default=10000,
        description="Maximum cache size"
    )


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    requests: int = Field(
        default=1000,
        description="Requests per window"
    )
    window_seconds: int = Field(
        default=60,
        description="Rate limit window in seconds"
    )


class APISettings(BaseSettings):
    """REST API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="API_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    host: str = Field(
        default="0.0.0.0",
        description="API host"
    )
    port: int = Field(
        default=8000,
        description="API port"
    )
    workers: int = Field(
        default=4,
        description="Number of worker processes"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    cors_origins: List[str] = Field(
        default=["*"],
        description="CORS allowed origins"
    )
    title: str = Field(
        default="API Analytics Service",
        description="API title"
    )
    version: str = Field(
        default="1.0.0",
        description="API version"
    )


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MONITORING_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    prometheus_port: int = Field(
        default=9111,
        description="Prometheus metrics port"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    enable_tracing: bool = Field(
        default=True,
        description="Enable distributed tracing"
    )


class ServiceSettings(BaseSettings):
    """Service-level configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SERVICE_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    app_name: str = Field(
        default="api-analytics-service",
        description="Application name"
    )
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )


class Config:
    """Main configuration class combining all settings."""

    def __init__(self):
        """Initialize configuration from environment."""
        self.postgres = PostgreSQLSettings()
        self.neo4j = Neo4jSettings()
        self.redis = RedisSettings()
        self.jwt = JWTSettings()
        self.cache = CacheSettings()
        self.rate_limit = RateLimitSettings()
        self.api = APISettings()
        self.monitoring = MonitoringSettings()
        self.service = ServiceSettings()


# Global configuration instance
config = Config()

