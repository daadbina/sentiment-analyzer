"""PostgreSQL client for publisher registry."""

import logging
from typing import Optional, List, Dict, Any
import asyncpg

from src.config import get_settings
from src.exceptions import DatabaseError
from src.models import PublisherEntity

logger = logging.getLogger(__name__)


class PostgresClient:
    """PostgreSQL client for publisher registry and audit logging."""

    def __init__(self):
        """Initialize PostgreSQL client."""
        self.settings = get_settings()
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Connect to PostgreSQL."""
        try:
            self.pool = await asyncpg.create_pool(
                self.settings.postgres.dsn,
                min_size=5,
                max_size=self.settings.postgres.pool_size,
            )
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise DatabaseError(f"PostgreSQL connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL."""
        if self.pool:
            try:
                await self.pool.close()
                logger.info("Disconnected from PostgreSQL")
            except Exception as e:
                logger.error(f"Error disconnecting from PostgreSQL: {e}")

    async def get_publisher_by_domain(self, domain: str) -> Optional[PublisherEntity]:
        """Get publisher by domain.

        Args:
            domain: Domain name

        Returns:
            PublisherEntity or None if not found
        """
        if not self.pool:
            raise DatabaseError("Database not connected")

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT publisher_id, name, domain, credibility_score, country, ownership_type, verified
                    FROM publishers
                    WHERE domain = $1 OR domain = $2
                    LIMIT 1
                    """,
                    domain,
                    f"www.{domain}",
                )

                if row:
                    return PublisherEntity(
                        publisher_id=row["publisher_id"],
                        name=row["name"],
                        domain=row["domain"],
                        credibility_score=row["credibility_score"],
                        country=row["country"],
                        ownership_type=row["ownership_type"],
                        verified=row["verified"],
                    )
                return None

        except Exception as e:
            logger.error(f"Failed to get publisher by domain {domain}: {e}")
            raise DatabaseError(f"Publisher lookup failed: {e}")

    async def log_canonicalization(
        self,
        article_id: str,
        stage: str,
        transformation_type: str,
        before_value: str,
        after_value: str,
        success: bool,
        error_message: Optional[str] = None,
        trace_id: Optional[str] = None,
        processing_duration_ms: int = 0,
    ) -> None:
        """Log canonicalization transformation.

        Args:
            article_id: Article ID
            stage: Pipeline stage
            transformation_type: Type of transformation
            before_value: Value before transformation
            after_value: Value after transformation
            success: Whether transformation succeeded
            error_message: Error message if failed
            trace_id: Trace ID for distributed tracing
            processing_duration_ms: Processing duration in milliseconds
        """
        if not self.pool:
            logger.warning("Database not connected, skipping audit log")
            return

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO canonicalization_audit_log
                    (article_id, timestamp, stage, transformation_type, before_value, after_value, success, error_message, trace_id, processing_duration_ms)
                    VALUES ($1, NOW(), $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    article_id,
                    stage,
                    transformation_type,
                    before_value,
                    after_value,
                    success,
                    error_message,
                    trace_id,
                    processing_duration_ms,
                )
        except Exception as e:
            logger.error(f"Failed to log canonicalization: {e}")

    async def log_normalization_summary(
        self,
        batch_id: str,
        articles_processed: int,
        avg_normalization_score: float,
        url_success_rate: float,
        publisher_resolution_rate: float,
        fuzzy_duplicates_found: int,
        avg_processing_duration_ms: float,
    ) -> None:
        """Log normalization summary.

        Args:
            batch_id: Batch ID
            articles_processed: Number of articles processed
            avg_normalization_score: Average normalization score
            url_success_rate: URL canonicalization success rate
            publisher_resolution_rate: Publisher resolution rate
            fuzzy_duplicates_found: Number of fuzzy duplicates found
            avg_processing_duration_ms: Average processing duration
        """
        if not self.pool:
            logger.warning("Database not connected, skipping summary log")
            return

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO normalization_summary
                    (batch_id, articles_processed, avg_normalization_score, url_success_rate, publisher_resolution_rate, fuzzy_duplicates_found, avg_processing_duration_ms)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    batch_id,
                    articles_processed,
                    avg_normalization_score,
                    url_success_rate,
                    publisher_resolution_rate,
                    fuzzy_duplicates_found,
                    avg_processing_duration_ms,
                )
        except Exception as e:
            logger.error(f"Failed to log normalization summary: {e}")

