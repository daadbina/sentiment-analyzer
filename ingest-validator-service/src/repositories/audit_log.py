"""Audit log repository."""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncpg
from src.config import get_config
from src.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class AuditLogRepository:
    """Repository for audit logs."""

    def __init__(self):
        """Initialize audit log repository."""
        self.config = get_config()
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.database.host,
                port=self.config.database.port,
                user=self.config.database.user,
                password=self.config.database.password,
                database=self.config.database.name,
                min_size=self.config.database.min_pool_size,
                max_size=self.config.database.max_pool_size,
            )
            logger.info("Database connection pool initialized for audit logs")
        except Exception as e:
            logger.debug(f"Database pool initialization skipped (optional component): {e}")
            # Database is optional - service continues without it
            self.pool = None

    async def log_validation(
        self,
        article_id: str,
        trace_id: str,
        job_id: str,
        validation_score: float,
        is_valid: bool,
        errors: List[str],
        warnings: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log validation result.

        Args:
            article_id: Article ID
            trace_id: Trace ID
            job_id: Job ID
            validation_score: Validation score
            is_valid: Whether article is valid
            errors: List of errors
            warnings: List of warnings
            metadata: Additional metadata

        Returns:
            True if successful
        """
        if not self.pool:
            logger.debug("Database not available, skipping audit log")
            return True

        try:
            async with self.pool.acquire() as conn:
                # Convert metadata dict to JSON string for JSONB column
                metadata_json = json.dumps(metadata or {})
                await conn.execute(
                    """
                    INSERT INTO audit_logs (
                        article_id, trace_id, job_id, validation_score,
                        is_valid, errors, warnings, metadata, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
                    """,
                    article_id,
                    trace_id,
                    job_id,
                    validation_score,
                    is_valid,
                    errors,
                    warnings,
                    metadata_json,
                    datetime.utcnow(),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to log validation: {e}")
            return False

    async def log_rejection(
        self,
        article_id: str,
        trace_id: str,
        job_id: str,
        rejection_reason: str,
        error_codes: List[str],
        retry_count: int = 0,
    ) -> bool:
        """Log article rejection.

        Args:
            article_id: Article ID
            trace_id: Trace ID
            job_id: Job ID
            rejection_reason: Reason for rejection
            error_codes: List of error codes
            retry_count: Number of retries

        Returns:
            True if successful
        """
        if not self.pool:
            logger.debug("Database not available, skipping rejection log")
            return True

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO rejection_logs (
                        article_id, trace_id, job_id, rejection_reason,
                        error_codes, retry_count, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    article_id,
                    trace_id,
                    job_id,
                    rejection_reason,
                    error_codes,
                    retry_count,
                    datetime.utcnow(),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to log rejection: {e}")
            return False

    async def get_article_history(self, article_id: str) -> List[Dict[str, Any]]:
        """Get validation history for article.

        Args:
            article_id: Article ID

        Returns:
            List of audit log entries
        """
        if not self.pool:
            logger.debug("Database not available, returning empty history")
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM audit_logs
                    WHERE article_id = $1
                    ORDER BY created_at DESC
                    LIMIT 100
                    """,
                    article_id,
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get article history: {e}")
            return []

    async def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get validation statistics.

        Args:
            hours: Number of hours to look back

        Returns:
            Statistics dictionary
        """
        if not self.pool:
            logger.debug("Database not available, returning empty stats")
            return {}

        try:
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) as valid_count,
                        SUM(CASE WHEN NOT is_valid THEN 1 ELSE 0 END) as invalid_count,
                        AVG(validation_score) as avg_score
                    FROM audit_logs
                    WHERE created_at > NOW() - INTERVAL '1 hour' * $1
                    """,
                    hours,
                )
                return dict(stats) if stats else {}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            try:
                await self.pool.close()
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error(f"Error closing database pool: {e}")
