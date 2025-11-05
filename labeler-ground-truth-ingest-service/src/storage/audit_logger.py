"""Comprehensive audit logging for label operations."""

from datetime import datetime
from typing import Dict, Any, Optional
from src.config import config
from src.utils.trace import get_logger
import asyncpg


logger = get_logger(__name__, config.logging.log_level)


class AuditLogger:
    """Log all label operations with full context."""

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        """Initialize audit logger."""
        self.db_pool = db_pool
        logger.info(
            "Audit logger initialized",
            operation="init"
        )

    async def ensure_audit_table(self) -> None:
        """Ensure audit table exists."""
        if not self.db_pool:
            logger.warning(
                "Database pool not available for audit logging",
                operation="ensure_audit_table"
            )
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS label_audit_log (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        operation VARCHAR(50) NOT NULL,
                        label_id VARCHAR(255),
                        source VARCHAR(50),
                        status VARCHAR(20),
                        message TEXT,
                        context JSONB,
                        trace_id VARCHAR(255),
                        duration_ms FLOAT
                    )
                """)
            
            logger.info(
                "Audit table ensured",
                operation="ensure_audit_table"
            )
        except Exception as e:
            logger.error(
                f"Failed to ensure audit table: {str(e)}",
                operation="ensure_audit_table",
                error_type=type(e).__name__
            )

    async def log_fetch(
        self,
        source: str,
        label_count: int,
        duration_ms: float,
        status: str = "success",
        trace_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Log label fetch operation."""
        try:
            context = {
                "label_count": label_count,
                "source": source
            }
            
            await self._write_audit_log(
                operation="fetch",
                source=source,
                status=status,
                message=error_message or f"Fetched {label_count} labels",
                context=context,
                trace_id=trace_id,
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error(
                f"Failed to log fetch operation: {str(e)}",
                operation="log_fetch",
                error_type=type(e).__name__
            )

    async def log_validation(
        self,
        source: str,
        total_labels: int,
        valid_labels: int,
        invalid_labels: int,
        duration_ms: float,
        trace_id: Optional[str] = None
    ) -> None:
        """Log label validation operation."""
        try:
            context = {
                "source": source,
                "total_labels": total_labels,
                "valid_labels": valid_labels,
                "invalid_labels": invalid_labels
            }
            
            status = "success" if invalid_labels == 0 else "partial"
            
            await self._write_audit_log(
                operation="validation",
                source=source,
                status=status,
                message=f"Validated {valid_labels}/{total_labels} labels",
                context=context,
                trace_id=trace_id,
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error(
                f"Failed to log validation operation: {str(e)}",
                operation="log_validation",
                error_type=type(e).__name__
            )

    async def log_reconciliation(
        self,
        source: str,
        total_labels: int,
        reconciled_labels: int,
        duration_ms: float,
        trace_id: Optional[str] = None
    ) -> None:
        """Log label reconciliation operation."""
        try:
            context = {
                "source": source,
                "total_labels": total_labels,
                "reconciled_labels": reconciled_labels
            }
            
            status = "success" if reconciled_labels > 0 else "no_matches"
            
            await self._write_audit_log(
                operation="reconciliation",
                source=source,
                status=status,
                message=f"Reconciled {reconciled_labels}/{total_labels} labels",
                context=context,
                trace_id=trace_id,
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error(
                f"Failed to log reconciliation operation: {str(e)}",
                operation="log_reconciliation",
                error_type=type(e).__name__
            )

    async def log_deduplication(
        self,
        source: str,
        total_labels: int,
        unique_labels: int,
        duplicate_labels: int,
        duration_ms: float,
        trace_id: Optional[str] = None
    ) -> None:
        """Log label deduplication operation."""
        try:
            context = {
                "source": source,
                "total_labels": total_labels,
                "unique_labels": unique_labels,
                "duplicate_labels": duplicate_labels
            }
            
            await self._write_audit_log(
                operation="deduplication",
                source=source,
                status="success",
                message=f"Deduplicated {duplicate_labels} labels",
                context=context,
                trace_id=trace_id,
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error(
                f"Failed to log deduplication operation: {str(e)}",
                operation="log_deduplication",
                error_type=type(e).__name__
            )

    async def log_storage(
        self,
        storage_type: str,
        label_count: int,
        duration_ms: float,
        status: str = "success",
        trace_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Log label storage operation."""
        try:
            context = {
                "storage_type": storage_type,
                "label_count": label_count
            }
            
            await self._write_audit_log(
                operation="storage",
                source=storage_type,
                status=status,
                message=error_message or f"Stored {label_count} labels",
                context=context,
                trace_id=trace_id,
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error(
                f"Failed to log storage operation: {str(e)}",
                operation="log_storage",
                error_type=type(e).__name__
            )

    async def _write_audit_log(
        self,
        operation: str,
        source: str,
        status: str,
        message: str,
        context: Dict[str, Any],
        trace_id: Optional[str] = None,
        duration_ms: float = 0.0
    ) -> None:
        """Write audit log entry to database."""
        if not self.db_pool:
            logger.debug(
                f"Audit log (no DB): {operation}",
                operation=operation,
                source=source,
                status=status
            )
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO label_audit_log 
                    (operation, source, status, message, context, trace_id, duration_ms)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, operation, source, status, message, context, trace_id, duration_ms)
            
            logger.debug(
                f"Audit log written",
                operation=operation,
                source=source,
                status=status
            )
        except Exception as e:
            logger.error(
                f"Failed to write audit log: {str(e)}",
                operation="_write_audit_log",
                error_type=type(e).__name__
            )

