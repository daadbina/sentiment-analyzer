"""Configuration management for conflict dashboard service."""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Service
    service_name: str = "conflict-dashboard-service"
    service_port: int = 8012
    log_level: str = "INFO"
    
    # PostgreSQL
    postgres_host: str = "154.53.166.231"
    postgres_port: int = 5432
    postgres_user: str = "adminsentiment"
    postgres_password: str = "wp2400!!!!"
    postgres_database: str = "sentiment"
    postgres_pool_min_size: int = 5
    postgres_pool_max_size: int = 20
    
    # Redis
    redis_host: str = "154.53.166.231"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    cache_ttl: int = 30  # seconds
    
    # API
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9112
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

