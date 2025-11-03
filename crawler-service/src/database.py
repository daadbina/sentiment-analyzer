"""
Database initialization and connection management.

Handles PostgreSQL connection pooling and schema initialization.
"""

import logging
from typing import Optional
import asyncpg

from .config import get_settings
from .exceptions import ConfigError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL database connections and initialization.

    Implements connection pooling and schema creation.
    """

    def __init__(self) -> None:
        """Initialize database manager."""
        self.settings = get_settings()
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """
        Initialize database connection pool and create schema.

        Creates tables if they don't exist.

        Raises:
            ConfigError: If database initialization fails.
        """
        try:
            logger.info("Initializing database connection pool...")

            # Create connection pool
            self.pool = await asyncpg.create_pool(
                host=self.settings.postgres_host,
                port=self.settings.postgres_port,
                user=self.settings.postgres_user,
                password=self.settings.postgres_password,
                database=self.settings.postgres_db,
                min_size=self.settings.db_min_pool_size,
                max_size=self.settings.db_max_pool_size,
                command_timeout=60,
            )

            logger.info(
                f"Database pool created: {self.settings.postgres_host}:"
                f"{self.settings.postgres_port}/{self.settings.postgres_db}"
            )

            # Create schema
            await self._create_schema()

            logger.info("Database initialization complete")

        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise ConfigError(
                f"Failed to initialize database: {str(e)}",
                error_code="DB_INIT_FAILED",
            )

    async def _create_schema(self) -> None:
        """
        Create database schema if it doesn't exist.

        Creates tables for feed sources, crawl jobs, validation logs, and anomaly events.
        """
        if not self.pool:
            raise ConfigError(
                "Database pool not initialized",
                error_code="DB_POOL_NOT_INITIALIZED",
            )

        async with self.pool.acquire() as conn:
            # Create feed_sources table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS feed_sources (
                    feed_id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(500) NOT NULL,
                    url TEXT NOT NULL,
                    feed_type VARCHAR(50) NOT NULL,
                    language VARCHAR(10) NOT NULL,
                    country VARCHAR(10),
                    enabled BOOLEAN DEFAULT TRUE,
                    crawl_interval_minutes INTEGER DEFAULT 30,
                    timeout_seconds INTEGER DEFAULT 10,
                    headers JSONB DEFAULT '{}',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_crawled_at TIMESTAMP,
                    last_success_at TIMESTAMP,
                    failure_count INTEGER DEFAULT 0,
                    circuit_breaker_open BOOLEAN DEFAULT FALSE
                )
            """)

            # Create crawl_jobs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS crawl_jobs (
                    job_id VARCHAR(255) PRIMARY KEY,
                    feed_id VARCHAR(255) NOT NULL REFERENCES feed_sources(feed_id),
                    status VARCHAR(50) NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    articles_fetched INTEGER DEFAULT 0,
                    articles_published INTEGER DEFAULT 0,
                    articles_failed INTEGER DEFAULT 0,
                    duplicates_skipped INTEGER DEFAULT 0,
                    error_message TEXT,
                    trace_id VARCHAR(255),
                    metadata JSONB DEFAULT '{}'
                )
            """)

            # Create data_validation_log table (R1-R12 validation rules)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS data_validation_log (
                    id SERIAL PRIMARY KEY,
                    record_id VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rule_id VARCHAR(10) NOT NULL,
                    error_message TEXT NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    schema_version VARCHAR(20) NOT NULL,
                    feed_id VARCHAR(255),
                    job_id VARCHAR(255),
                    trace_id VARCHAR(255),
                    metadata JSONB DEFAULT '{}'
                )
            """)

            # Create data_anomaly_events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS data_anomaly_events (
                    event_id VARCHAR(255) PRIMARY KEY,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    type VARCHAR(100) NOT NULL,
                    description TEXT NOT NULL,
                    trace_id VARCHAR(255),
                    feed_id VARCHAR(255),
                    severity VARCHAR(20) NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TIMESTAMP,
                    metadata JSONB DEFAULT '{}'
                )
            """)

            # Create indices for performance
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_crawl_jobs_feed_id 
                ON crawl_jobs(feed_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_crawl_jobs_started_at 
                ON crawl_jobs(started_at DESC)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_validation_log_timestamp 
                ON data_validation_log(timestamp DESC)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_validation_log_rule_id 
                ON data_validation_log(rule_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_anomaly_events_detected_at 
                ON data_anomaly_events(detected_at DESC)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_anomaly_events_feed_id 
                ON data_anomaly_events(feed_id)
            """)

            logger.info("Database schema created successfully")

    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def health_check(self) -> bool:
        """
        Check database connection health.

        Returns:
            bool: True if database is healthy, False otherwise.
        """
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

    async def get_connection(self) -> asyncpg.Connection:
        """
        Get database connection from pool.

        Returns:
            asyncpg.Connection: Database connection.

        Raises:
            ConfigError: If pool not initialized.
        """
        if not self.pool:
            raise ConfigError(
                "Database pool not initialized",
                error_code="DB_POOL_NOT_INITIALIZED",
            )

        return await self.pool.acquire()

    async def execute(self, query: str, *args) -> str:
        """
        Execute SQL query.

        Args:
            query: SQL query to execute.
            *args: Query parameters.

        Returns:
            str: Query result status.
        """
        if not self.pool:
            raise ConfigError(
                "Database pool not initialized",
                error_code="DB_POOL_NOT_INITIALIZED",
            )

        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """
        Fetch query results.

        Args:
            query: SQL query to execute.
            *args: Query parameters.

        Returns:
            list: Query results.
        """
        if not self.pool:
            raise ConfigError(
                "Database pool not initialized",
                error_code="DB_POOL_NOT_INITIALIZED",
            )

        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Fetch single row.

        Args:
            query: SQL query to execute.
            *args: Query parameters.

        Returns:
            Optional[asyncpg.Record]: Query result or None.
        """
        if not self.pool:
            raise ConfigError(
                "Database pool not initialized",
                error_code="DB_POOL_NOT_INITIALIZED",
            )

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

