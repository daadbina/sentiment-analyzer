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
                    domain VARCHAR(255),
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

            # Alter existing table to increase domain column size if needed
            # This is safe to run multiple times - PostgreSQL will ignore if already correct size
            try:
                await conn.execute("""
                    ALTER TABLE ground_truth
                    ALTER COLUMN domain TYPE VARCHAR(255)
                """)
            except Exception:
                # Column might not exist yet or already correct size - safe to ignore
                pass

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
                    countries TEXT[],
                    event_code INT,
                    event_type VARCHAR(100),
                    goldstein_scale FLOAT,
                    label_conflict INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Add countries column if it doesn't exist (migration)
            try:
                await conn.execute("""
                    ALTER TABLE reconciliation_log
                    ADD COLUMN IF NOT EXISTS countries TEXT[]
                """)
            except Exception:
                # Column might already exist - safe to ignore
                pass

            # Add GDELT metadata columns if they don't exist (migration)
            try:
                await conn.execute("""
                    ALTER TABLE reconciliation_log
                    ADD COLUMN IF NOT EXISTS event_code INT,
                    ADD COLUMN IF NOT EXISTS event_type VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS goldstein_scale FLOAT,
                    ADD COLUMN IF NOT EXISTS label_conflict INT
                """)
            except Exception:
                # Columns might already exist - safe to ignore
                pass

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

            # Create deduplication_cache table for persistent deduplication
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS deduplication_cache (
                    id SERIAL PRIMARY KEY,
                    label_hash VARCHAR(64) NOT NULL UNIQUE,
                    event_id VARCHAR(255) NOT NULL,
                    event_date VARCHAR(50),
                    label_source VARCHAR(50) NOT NULL,
                    label_confidence FLOAT,
                    label_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index on label_hash for fast lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dedup_cache_hash ON deduplication_cache(label_hash)
            """)

            # Create index on event_id and label_source for deduplication queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dedup_cache_event_source ON deduplication_cache(event_id, label_source)
            """)

            # Create btc_truth table (Dataset 7: Bitcoin & Financial Prices)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS btc_truth (
                    id SERIAL PRIMARY KEY,
                    event_id VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    open FLOAT,
                    close FLOAT,
                    high FLOAT,
                    low FLOAT,
                    volume FLOAT,
                    change_pct_10h FLOAT,
                    label_spike BOOLEAN,
                    volatility_score FLOAT,
                    api_source VARCHAR(100),
                    api_timestamp TIMESTAMP,
                    exchange_avg FLOAT,
                    source_rate_limit_token VARCHAR(255),
                    label_confidence FLOAT,
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

            # Create indexes for btc_truth
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_btc_truth_event_id ON btc_truth(event_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_btc_truth_timestamp ON btc_truth(timestamp)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_btc_truth_label_source ON btc_truth(label_source)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_btc_truth_created_at ON btc_truth(created_at)
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
                    batch_data = []
                    for label in batch:
                        # Parse ISO format timestamps to datetime objects
                        def parse_iso_timestamp(ts_str):
                            if not ts_str:
                                return None
                            try:
                                if isinstance(ts_str, str):
                                    ts_clean = ts_str.replace("Z", "+00:00")
                                    dt = datetime.fromisoformat(ts_clean)
                                    # Convert to offset-naive for PostgreSQL
                                    if dt.tzinfo is not None:
                                        dt = dt.replace(tzinfo=None)
                                    return dt
                                return ts_str  # Already a datetime
                            except:
                                return None

                        batch_data.append((
                            label.get("event_id"),
                            label.get("group_id"),
                            label.get("description"),
                            label.get("domain"),
                            label.get("time_window"),
                            label.get("realization_metric"),
                            label.get("threshold"),
                            parse_iso_timestamp(label.get("verified_at")),
                            label.get("label_realized"),
                            label.get("label_confidence"),
                            label.get("source_confidence"),
                            label.get("label_source"),
                            label.get("label_source_license"),
                            label.get("label_source_url"),
                            parse_iso_timestamp(label.get("last_license_check")),
                            parse_iso_timestamp(label.get("last_updated")),
                            label.get("trace_id"),
                            label.get("schema_version")
                        ))

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

    async def write_crypto_labels(self, labels: List[Dict[str, Any]]) -> bool:
        """Write crypto labels to btc_truth table (Dataset 7).

        Crypto labels (Binance, CoinGecko) are NOT reconciled with semantic groups.
        They are stored separately in btc_truth table per Architecture.md.
        """
        if not labels:
            return True

        if not self.pool:
            raise StorageError("postgresql", "write_crypto_labels", "Connection pool not initialized")

        start_time = time.time()
        batch_size = 1000
        total_inserted = 0

        try:
            async with self.pool.acquire() as conn:
                # Process labels in batches
                for i in range(0, len(labels), batch_size):
                    batch = labels[i:i + batch_size]

                    # Prepare batch data for btc_truth table
                    batch_data = []
                    for label in batch:
                        # Parse timestamp from ISO string to datetime (offset-naive UTC for PostgreSQL)
                        def parse_iso_timestamp(ts_str):
                            if not ts_str:
                                return None
                            try:
                                if isinstance(ts_str, str):
                                    ts_clean = ts_str.replace("Z", "+00:00")
                                    dt = datetime.fromisoformat(ts_clean)
                                    # Convert to UTC and then to offset-naive for PostgreSQL
                                    # PostgreSQL will interpret offset-naive timestamps as UTC
                                    if dt.tzinfo is not None:
                                        from datetime import timezone
                                        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                                    return dt
                                return ts_str  # Already a datetime
                            except:
                                return None

                        ts_str = label.get("event_timestamp") or label.get("timestamp")
                        ts = parse_iso_timestamp(ts_str)

                        batch_data.append((
                            label.get("event_id"),
                            ts,
                            label.get("open"),
                            label.get("close"),
                            label.get("high"),
                            label.get("low"),
                            label.get("volume"),
                            label.get("change_pct_10p"),  # Note: Binance uses change_pct_10p
                            label.get("label_spike"),
                            label.get("volatility_score"),
                            label.get("api_source"),
                            label.get("api_timestamp"),
                            label.get("exchange_avg"),
                            label.get("source_rate_limit_token"),
                            label.get("label_confidence"),
                            label.get("label_source"),
                            label.get("label_source_license"),
                            label.get("label_source_url"),
                            parse_iso_timestamp(label.get("last_license_check")),
                            parse_iso_timestamp(label.get("last_updated")),
                            label.get("trace_id"),
                            label.get("schema_version")
                        ))

                    # Use executemany for batch insert with UPSERT logic
                    # Update existing records if they already exist (based on event_id and label_source)
                    async with conn.transaction():
                        await conn.executemany("""
                            INSERT INTO btc_truth (
                                event_id, timestamp, open, close, high, low, volume,
                                change_pct_10h, label_spike, volatility_score, api_source,
                                api_timestamp, exchange_avg, source_rate_limit_token,
                                label_confidence, label_source, label_source_license,
                                label_source_url, last_license_check, last_updated,
                                trace_id, schema_version
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                                $15, $16, $17, $18, $19, $20, $21, $22
                            )
                            ON CONFLICT (event_id, label_source) DO UPDATE SET
                                close = EXCLUDED.close,
                                change_pct_10h = EXCLUDED.change_pct_10h,
                                label_spike = EXCLUDED.label_spike,
                                volatility_score = EXCLUDED.volatility_score,
                                last_updated = CURRENT_TIMESTAMP
                        """, batch_data)

                    total_inserted += len(batch)

            duration_seconds = time.time() - start_time
            metrics.record_storage("postgresql_crypto", duration_seconds)

            logger.info(
                f"Successfully wrote {total_inserted} crypto labels to btc_truth",
                operation="write_crypto_labels",
                label_count=total_inserted,
                duration_seconds=duration_seconds
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to write crypto labels to btc_truth: {str(e)}",
                operation="write_crypto_labels",
                error_type=type(e).__name__,
                total_inserted=total_inserted
            )
            raise StorageError("postgresql", "write_crypto_labels", str(e))

    async def write_reconciliation_log(
        self,
        batch_id: str,
        results: List[Dict[str, Any]]
    ) -> bool:
        """Write reconciliation log to PostgreSQL using batch insert."""
        if not results:
            return True

        if not self.pool:
            raise StorageError("postgresql", "write_reconciliation_log", "Connection pool not initialized")

        start_time = time.time()

        try:
            # Prepare batch data for executemany
            batch_data = []
            for result in results:
                label = result.get("label", {})
                countries = label.get("countries", [])

                # Extract GDELT metadata if available
                event_code = label.get("event_code")
                event_type = label.get("event_type")
                goldstein_scale = label.get("goldstein_scale")
                label_conflict = label.get("label_conflict")

                batch_data.append((
                    batch_id,
                    result.get("group_id"),
                    label.get("event_id"),
                    result.get("confidence"),
                    "reconciled",
                    result.get("temporal_confidence"),
                    result.get("semantic_confidence"),
                    countries if countries else [],
                    event_code,
                    event_type,
                    goldstein_scale,
                    label_conflict
                ))

            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Use executemany for batch insert (100x faster than individual inserts)
                    await conn.executemany("""
                        INSERT INTO reconciliation_log (
                            batch_id, group_id, label_id, confidence, status,
                            temporal_confidence, semantic_confidence, countries,
                            event_code, event_type, goldstein_scale, label_conflict
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """, batch_data)

            duration_seconds = time.time() - start_time
            metrics.record_storage("postgresql_reconciliation", duration_seconds)

            logger.info(
                f"Successfully wrote {len(results)} reconciliation logs to PostgreSQL (batch)",
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

