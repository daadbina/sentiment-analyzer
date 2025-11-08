"""
Configuration module for Neo4j Loader Graph Service.
All configuration parameters are externalized via environment variables.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """
    Configuration class for Neo4j Loader Graph Service.
    All settings are loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Kafka Configuration
    kafka_brokers: str = Field(
        default="154.53.166.231:9092",
        description="Kafka bootstrap servers (comma-separated)",
    )
    consumer_group: str = Field(
        default="neo4j-loader-group",
        description="Kafka consumer group identifier",
    )
    schema_registry_url: str = Field(
        default="http://154.53.166.231:8081",
        description="Schema Registry endpoint URL",
    )
    kafka_topics: List[str] = Field(
        default=["semantic_groups", "entities_extracted", "predictions", "news_canonical"],
        description="Kafka topics to consume",
    )
    kafka_auto_offset_reset: str = Field(
        default="earliest",
        description="Kafka auto offset reset policy",
    )
    kafka_enable_auto_commit: bool = Field(
        default=False,
        description="Enable Kafka auto commit (use manual commit for exactly-once)",
    )
    kafka_session_timeout_ms: int = Field(
        default=30000,
        description="Kafka session timeout in milliseconds",
    )
    kafka_max_poll_interval_ms: int = Field(
        default=300000,
        description="Kafka max poll interval in milliseconds",
    )

    # Neo4j Configuration
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI",
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username",
    )
    neo4j_password: str = Field(
        ...,
        description="Neo4j password (required)",
    )
    neo4j_database: str = Field(
        default="neo4j",
        description="Neo4j database name",
    )
    neo4j_max_connection_lifetime: int = Field(
        default=3600,
        description="Neo4j max connection lifetime in seconds",
    )
    neo4j_max_connection_pool_size: int = Field(
        default=50,
        description="Neo4j max connection pool size",
    )
    neo4j_connection_timeout: int = Field(
        default=30,
        description="Neo4j connection timeout in seconds",
    )
    neo4j_encrypted: bool = Field(
        default=False,
        description="Enable TLS for Neo4j connection",
    )

    # PostgreSQL Configuration
    postgres_host: str = Field(
        default="154.53.166.231",
        description="PostgreSQL host",
    )
    postgres_port: int = Field(
        default=5432,
        description="PostgreSQL port",
    )
    postgres_user: str = Field(
        default="adminsentiment",
        description="PostgreSQL username",
    )
    postgres_password: str = Field(
        ...,
        description="PostgreSQL password (required)",
    )
    postgres_database: str = Field(
        default="sentiment",
        description="PostgreSQL database name",
    )
    postgres_min_pool_size: int = Field(
        default=10,
        description="PostgreSQL minimum connection pool size",
    )
    postgres_max_pool_size: int = Field(
        default=50,
        description="PostgreSQL maximum connection pool size",
    )
    postgres_ssl_mode: str = Field(
        default="prefer",
        description="PostgreSQL SSL mode (disable, allow, prefer, require)",
    )

    # Redis Configuration (for query caching)
    redis_host: str = Field(
        default="localhost",
        description="Redis host",
    )
    redis_port: int = Field(
        default=6379,
        description="Redis port",
    )
    redis_db: int = Field(
        default=0,
        description="Redis database number",
    )
    redis_password: str = Field(
        default="",
        description="Redis password (optional)",
    )
    redis_cache_ttl: int = Field(
        default=3600,
        description="Redis cache TTL in seconds",
    )

    # Batch Processing Configuration
    batch_size: int = Field(
        default=1000,
        description="Batch size for bulk loading nodes and relationships",
    )
    stream_buffer_size: int = Field(
        default=100,
        description="Stream buffer size for real-time updates",
    )
    stream_flush_timeout: int = Field(
        default=5,
        description="Stream buffer flush timeout in seconds",
    )
    max_retry_attempts: int = Field(
        default=3,
        description="Maximum retry attempts for failed operations",
    )
    retry_backoff_base: float = Field(
        default=2.0,
        description="Exponential backoff base for retries",
    )
    write_failure_threshold: float = Field(
        default=0.005,
        description="Write failure rate threshold (0.5%)",
    )

    # Graph Metrics Configuration
    centrality_computation_enabled: bool = Field(
        default=True,
        description="Enable centrality metrics computation",
    )
    clustering_detection_enabled: bool = Field(
        default=True,
        description="Enable community detection",
    )
    centrality_schedule_hours: int = Field(
        default=6,
        description="Centrality computation schedule interval in hours",
    )
    clustering_schedule_hours: int = Field(
        default=12,
        description="Clustering detection schedule interval in hours",
    )
    centrality_sample_size: int = Field(
        default=100000,
        description="Sample size for centrality computation (0 = all nodes)",
    )

    # Snapshot & Backup Configuration
    snapshot_interval_hours: int = Field(
        default=24,
        description="Graph snapshot frequency in hours",
    )
    snapshot_variance_threshold: float = Field(
        default=0.05,
        description="Snapshot variance threshold for alerts (5%)",
    )
    backup_retention_days: int = Field(
        default=30,
        description="Backup retention period in days",
    )
    backup_storage_path: str = Field(
        default="/backups",
        description="Backup storage path (local or S3/MinIO)",
    )

    # Monitoring Configuration
    prometheus_port: int = Field(
        default=9110,
        description="Prometheus metrics endpoint port",
    )
    jaeger_agent_host: str = Field(
        default="localhost",
        description="Jaeger agent host",
    )
    jaeger_agent_port: int = Field(
        default=6831,
        description="Jaeger agent port",
    )
    tracing_enabled: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing",
    )
    tracing_sample_rate: float = Field(
        default=0.1,
        description="Tracing sample rate (0.0-1.0)",
    )

    # Service Configuration
    service_name: str = Field(
        default="neo4j-loader-graph-service",
        description="Service name for logging and tracing",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    health_check_port: int = Field(
        default=8080,
        description="Health check endpoint port",
    )
    graceful_shutdown_timeout: int = Field(
        default=30,
        description="Graceful shutdown timeout in seconds",
    )

    # Circuit Breaker Configuration
    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker for Neo4j",
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        description="Circuit breaker failure threshold",
    )
    circuit_breaker_timeout: int = Field(
        default=60,
        description="Circuit breaker timeout in seconds",
    )
    rate_limit_queue_size: int = Field(
        default=1000,
        description="Rate limit queue size for backpressure",
    )

    # Kafka Producer Configuration
    kafka_producer_topic: str = Field(
        default="graph_updated",
        description="Kafka topic for graph update events",
    )
    kafka_producer_acks: str = Field(
        default="all",
        description="Kafka producer acks setting",
    )
    kafka_producer_retries: int = Field(
        default=3,
        description="Kafka producer retry attempts",
    )
    kafka_producer_idempotence: bool = Field(
        default=True,
        description="Enable Kafka producer idempotence",
    )

    def get_neo4j_config(self) -> dict:
        """Get Neo4j driver configuration."""
        return {
            "uri": self.neo4j_uri,
            "auth": (self.neo4j_user, self.neo4j_password),
            "database": self.neo4j_database,
            "max_connection_lifetime": self.neo4j_max_connection_lifetime,
            "max_connection_pool_size": self.neo4j_max_connection_pool_size,
            "connection_timeout": self.neo4j_connection_timeout,
            "encrypted": self.neo4j_encrypted,
        }

    def get_postgres_dsn(self) -> str:
        """Get PostgreSQL connection DSN."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )

    def get_kafka_consumer_config(self) -> dict:
        """Get Kafka consumer configuration."""
        return {
            "bootstrap.servers": self.kafka_brokers,
            "group.id": self.consumer_group,
            "auto.offset.reset": self.kafka_auto_offset_reset,
            "enable.auto.commit": self.kafka_enable_auto_commit,
            "session.timeout.ms": self.kafka_session_timeout_ms,
            "max.poll.interval.ms": self.kafka_max_poll_interval_ms,
        }

    def get_kafka_producer_config(self) -> dict:
        """Get Kafka producer configuration."""
        return {
            "bootstrap.servers": self.kafka_brokers,
            "acks": self.kafka_producer_acks,
            "retries": self.kafka_producer_retries,
            "enable.idempotence": self.kafka_producer_idempotence,
        }


# Global configuration instance
config = Config()

