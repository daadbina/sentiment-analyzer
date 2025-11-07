"""PostgreSQL writer for ground truth labels."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncpg

from src.config import config
from src.exceptions import StorageError, DatabaseError
from src.utils.trace import get_logger
from src.metrics import get_metrics


logger = get_logger(__name__, config.logging.log_level)
metrics = get_metrics(config.metrics.prometheus_port)


class PostgreSQLWriter:
    """Write labels to PostgreSQL."""

    def __init__(self):
        """Initialize PostgreSQL writer."""
        self.dsn = config.postgresql.dsn
        self.pool: Optional[asyncpg.Pool] = None
        logger.info(
            "Initializing PostgreSQL writer",
            operation="init_postgres_writer",
            host=config.postgresql.host,
            database=config.postgresql.database
        )

    async def connect(self):
        """Create connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=5,
                max_size=config.postgresql.pool_size,
                max_queries=50000,
                max_cached_statement_lifetime=300,
                max_cacheable_statement_size=15000
            )
            logger.info(
                "PostgreSQL connection pool created",
                operation="connect"
            )
        except Exception as e:
            logger.error(
                f"Failed to create PostgreSQL connection pool: {str(e)}",
                operation="connect",
                error_type=type(e).__name__
            )
            raise StorageError("postgresql", "connect", str(e))

    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info(
                "PostgreSQL connection pool closed",
                operation="disconnect"
            )

    async def _ensure_tables(self):
        """Ensure required tables exist."""
        if not self.pool:
            raise StorageError("postgresql", "_ensure_tables", "Connection pool not initialized")

        async with self.pool.acquire() as conn:
            # Create ground_truth table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ground_truth (
                    id SERIAL PRIMARY KEY,
                    event_id VARCHAR(255) NOT NULL,
                    group_id VARCHAR(255),
                    description TEXT,
                    domain VARCHAR(50),
                    time_window VARCHAR(255),
                    realization_metric VARCHAR(255),
                    threshold FLOAT,
                    verified_at TIMESTAMP,
                    label_realized BOOLEAN,
                    label_confidence FLOAT,
                    source_confidence FLOAT,
                    label_source VARCHAR(50),
                    label_source_license VARCHAR(255),
                    label_source_url TEXT,
                    last_license_check TIMESTAMP,
                    last_updated TIMESTAMP,
                    trace_id VARCHAR(255),
                    schema_version VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(event_id, label_source)
                )
            """)

            # Create reconciliation_log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS reconciliation_log (
                    id SERIAL PRIMARY KEY,
                    batch_id VARCHAR(255),
                    group_id VARCHAR(255),
                    label_id VARCHAR(255),
                    confidence FLOAT,
                    status VARCHAR(50),
                    temporal_confidence FLOAT,
                    semantic_confidence FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create license_audit table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS license_audit (
                    id SERIAL PRIMARY KEY,
                    source VARCHAR(50),
                    license_type VARCHAR(255),
                    last_check TIMESTAMP,
                    status VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            logger.info(
                "Database tables ensured",
                operation="_ensure_tables"
            )

    async def write_labels(self, labels: List[Dict[str, Any]]) -> bool:
        """Write labels to PostgreSQL using batch inserts."""
        if not labels:
            return True

        if not self.pool:
            raise StorageError("postgresql", "write_labels", "Connection pool not initialized")

        start_time = time.time()
        batch_size = 1000  # Insert in batches of 1000
        total_inserted = 0

        try:
            async with self.pool.acquire() as conn:
                # Process labels in batches
                for i in range(0, len(labels), batch_size):
                    batch = labels[i:i + batch_size]

                    # Prepare batch data
                    batch_data = [
                        (
                            label.get("event_id"),
                            label.get("group_id"),
                            label.get("description"),
                            label.get("domain"),
                            label.get("time_window"),
                            label.get("realization_metric"),
                            label.get("threshold"),
                            label.get("verified_at"),
                            label.get("label_realized"),
                            label.get("label_confidence"),
                            label.get("source_confidence"),
                            label.get("label_source"),
                            label.get("label_source_license"),
                            label.get("label_source_url"),
                            label.get("last_license_check"),
                            label.get("last_updated"),
                            label.get("trace_id"),
                            label.get("schema_version")
                        )
                        for label in batch
                    ]

                    # Use executemany for batch insert
                    async with conn.transaction():
                        await conn.executemany("""
                            INSERT INTO ground_truth (
                                event_id, group_id, description, domain, time_window,
                                realization_metric, threshold, verified_at, label_realized,
                                label_confidence, source_confidence, label_source,
                                label_source_license, label_source_url, last_license_check,
                                last_updated, trace_id, schema_version
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                            )
                            ON CONFLICT (event_id, label_source) DO UPDATE SET
                                label_confidence = EXCLUDED.label_confidence,
                                last_updated = CURRENT_TIMESTAMP
                        """, batch_data)

                    total_inserted += len(batch)

                    logger.info(
                        f"Batch inserted {len(batch)} labels to PostgreSQL",
                        operation="write_labels_batch",
                        batch_index=i // batch_size,
                        batch_size=len(batch),
                        total_inserted=total_inserted
                    )

            duration_seconds = time.time() - start_time
            metrics.record_storage("postgresql", duration_seconds)

            logger.info(
                f"Successfully wrote {total_inserted} labels to PostgreSQL",
                operation="write_labels",
                label_count=total_inserted,
                duration_seconds=duration_seconds
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to write labels to PostgreSQL: {str(e)}",
                operation="write_labels",
                error_type=type(e).__name__,
                total_inserted=total_inserted
            )
            raise StorageError("postgresql", "write_labels", str(e))

    async def write_reconciliation_log(
        self,
        batch_id: str,
        results: List[Dict[str, Any]]
    ) -> bool:
        """Write reconciliation log to PostgreSQL."""
        if not results:
            return True

        if not self.pool:
            raise StorageError("postgresql", "write_reconciliation_log", "Connection pool not initialized")

        start_time = time.time()

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for result in results:
                        await conn.execute("""
                            INSERT INTO reconciliation_log (
                                batch_id, group_id, label_id, confidence, status,
                                temporal_confidence, semantic_confidence
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                            batch_id,
                            result.get("group_id"),
                            result.get("label", {}).get("event_id"),
                            result.get("confidence"),
                            "reconciled",
                            result.get("temporal_confidence"),
                            result.get("semantic_confidence")
                        )

            duration_seconds = time.time() - start_time
            metrics.record_storage("postgresql_reconciliation", duration_seconds)

            logger.info(
                f"Successfully wrote {len(results)} reconciliation logs to PostgreSQL",
                operation="write_reconciliation_log",
                result_count=len(results),
                duration_seconds=duration_seconds
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to write reconciliation log to PostgreSQL: {str(e)}",
                operation="write_reconciliation_log",
                error_type=type(e).__name__
            )
            raise StorageError("postgresql", "write_reconciliation_log", str(e))

    async def fetch_semantic_groups(self) -> List[Dict[str, Any]]:
        """Fetch all semantic groups from PostgreSQL.

        Returns:
            List of semantic group dictionaries with datetime objects converted to ISO strings
        """
        if not self.pool:
            raise StorageError("postgresql", "fetch_semantic_groups", "Connection pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT
                        group_id,
                        article_count,
                        similarity_avg,
                        topic_label,
                        centroid_vector,
                        cluster_metadata,
                        created_at,
                        updated_at
                    FROM semantic_groups
                    ORDER BY created_at DESC
                """)

            groups = []
            for row in rows:
                group_dict = dict(row)
                # Convert datetime objects to ISO format strings for JSON serialization
                if group_dict.get("created_at"):
                    group_dict["created_at"] = group_dict["created_at"].isoformat()
                if group_dict.get("updated_at"):
                    group_dict["updated_at"] = group_dict["updated_at"].isoformat()
                groups.append(group_dict)

            logger.info(
                f"Fetched {len(groups)} semantic groups from PostgreSQL",
                operation="fetch_semantic_groups",
                group_count=len(groups)
            )

            return groups

        except Exception as e:
            logger.error(
                f"Failed to fetch semantic groups from PostgreSQL: {str(e)}",
                operation="fetch_semantic_groups",
                error_type=type(e).__name__
            )
            raise StorageError("postgresql", "fetch_semantic_groups", str(e))

    async def write_license_audit(
        self,
        source: str,
        license_type: str,
        status: str = "valid"
    ) -> bool:
        """Write license audit to PostgreSQL."""
        if not self.pool:
            raise StorageError("postgresql", "write_license_audit", "Connection pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO license_audit (source, license_type, last_check, status)
                    VALUES ($1, $2, CURRENT_TIMESTAMP, $3)
                """,
                    source,
                    license_type,
                    status
                )

            logger.info(
                f"License audit written to PostgreSQL",
                operation="write_license_audit",
                source=source,
                status=status
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to write license audit to PostgreSQL: {str(e)}",
                operation="write_license_audit",
                error_type=type(e).__name__
            )
            raise StorageError("postgresql", "write_license_audit", str(e))

