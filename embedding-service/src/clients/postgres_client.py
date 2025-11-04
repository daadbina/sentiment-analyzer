"""PostgreSQL client for audit logging."""

import logging
import asyncpg
from datetime import datetime
from typing import Optional

from src.config import config
from src.exceptions import DatabaseConnectionError, DatabaseError

logger = logging.getLogger(__name__)


class PostgresClient:
    """PostgreSQL client for audit logging and metadata storage."""

    def __init__(self):
        """Initialize PostgreSQL client."""
        self.config = config.postgres
        self.pool = None

    async def initialize(self) -> None:
        """Initialize database connection pool."""
        try:
            logger.info(f"Initializing PostgreSQL connection pool")

            self.pool = await asyncpg.create_pool(
                self.config.dsn,
                min_size=self.config.min_pool_size,
                max_size=self.config.max_pool_size,
                command_timeout=120,
            )

            await self._create_tables()
            logger.info("PostgreSQL connection pool initialized")

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise DatabaseConnectionError(f"Failed to connect to database: {e}")

    async def _create_tables(self) -> None:
        """Create audit tables if they don't exist."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_audit_log (
                    id SERIAL PRIMARY KEY,
                    article_id VARCHAR(255) NOT NULL,
                    embedding_id VARCHAR(255),
                    model_name VARCHAR(255),
                    language VARCHAR(10),
                    embedding_dimension INT,
                    processing_time_ms FLOAT,
                    status VARCHAR(50),
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(255) NOT NULL,
                    metric_value FLOAT,
                    labels JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    async def log_embedding(
        self,
        article_id: str,
        embedding_id: Optional[str] = None,
        model_name: Optional[str] = None,
        language: Optional[str] = None,
        embedding_dimension: Optional[int] = None,
        processing_time_ms: Optional[float] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log embedding computation to audit table.

        Args:
            article_id: Article ID
            embedding_id: Embedding ID
            model_name: Model name used
            language: Language code
            embedding_dimension: Embedding dimension
            processing_time_ms: Processing time in milliseconds
            status: Status (success, failure, etc.)
            error_message: Optional error message
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO embedding_audit_log
                    (article_id, embedding_id, model_name, language,
                     embedding_dimension, processing_time_ms, status, error_message)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    article_id,
                    embedding_id,
                    model_name,
                    language,
                    embedding_dimension,
                    processing_time_ms,
                    status,
                    error_message,
                )

            logger.debug(f"Logged embedding for article: {article_id}")

        except Exception as e:
            logger.warning(f"Failed to log embedding: {e}")

    async def log_metric(
        self,
        metric_name: str,
        metric_value: float,
        labels: Optional[dict] = None,
    ) -> None:
        """
        Log a metric value.

        Args:
            metric_name: Name of the metric
            metric_value: Metric value
            labels: Optional labels dictionary
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO embedding_metrics
                    (metric_name, metric_value, labels)
                    VALUES ($1, $2, $3)
                    """,
                    metric_name,
                    metric_value,
                    labels,
                )

        except Exception as e:
            logger.warning(f"Failed to log metric: {e}")

    async def get_embedding_stats(self, hours: int = 24) -> dict:
        """Get embedding statistics for the last N hours."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_embeddings,
                        COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                        COUNT(CASE WHEN status = 'failure' THEN 1 END) as failed,
                        AVG(processing_time_ms) as avg_processing_time,
                        MAX(processing_time_ms) as max_processing_time
                    FROM embedding_audit_log
                    WHERE created_at > NOW() - INTERVAL '%s hours'
                    """ % hours
                )

                return dict(row) if row else {}

        except Exception as e:
            logger.warning(f"Failed to get embedding stats: {e}")
            return {}

    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")

