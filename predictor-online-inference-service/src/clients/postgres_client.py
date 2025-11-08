"""
PostgreSQL client for prediction storage and label retrieval.

Provides abstraction over asyncpg for async database operations.
Handles connection pooling, query execution, and error recovery.
"""

import logging
from datetime import datetime
from typing import Any

import asyncpg
from asyncpg import Pool

from ..config import PostgresConfig
from ..exceptions import LabelFetchError, PostgresError
from ..metrics import (
    postgres_connection_pool_size,
    postgres_errors_total,
    postgres_query_duration_seconds,
)
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class PostgresClient:
    """
    Client for interacting with PostgreSQL database.

    Provides methods for storing predictions and retrieving ground-truth labels.
    Handles connection pooling and transaction management.
    """

    def __init__(self, config: PostgresConfig):
        """
        Initialize PostgreSQL client.

        Args:
            config: PostgreSQL configuration
        """
        self.config = config
        self._pool: Pool | None = None

        logger.info(
            f"Initializing PostgreSQL client: host={config.host}, "
            f"port={config.port}, database={config.database}"
        )

    async def connect(self) -> None:
        """
        Connect to PostgreSQL and create connection pool.

        Raises:
            PostgresError: If connection fails
        """
        try:
            logger.info(
                f"Connecting to PostgreSQL: {self.config.host}:{self.config.port}/{self.config.database}"
            )

            # Create connection pool
            self._pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                min_size=self.config.min_pool_size,
                max_size=self.config.max_pool_size,
                command_timeout=self.config.command_timeout,
                ssl=self.config.ssl_mode if self.config.ssl_mode != "disable" else None,
            )

            # Test connection
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            # Update pool size metrics
            postgres_connection_pool_size.labels(state="idle").set(self.config.min_pool_size)
            postgres_connection_pool_size.labels(state="max").set(self.config.max_pool_size)

            logger.info(
                f"Connected to PostgreSQL: host={self.config.host}, "
                f"database={self.config.database}, pool_size={self.config.min_pool_size}-{self.config.max_pool_size}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}", exc_info=True)
            raise PostgresError(
                f"Failed to connect to PostgreSQL: {e}",
                operation="connect",
            )

    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL and close connection pool."""
        if self._pool:
            logger.info("Disconnecting from PostgreSQL")
            await self._pool.close()
            self._pool = None

    def _ensure_connected(self) -> Pool:
        """
        Ensure client is connected.

        Returns:
            Connection pool instance

        Raises:
            PostgresError: If not connected
        """
        if self._pool is None:
            raise PostgresError(
                "PostgreSQL client not connected. Call connect() first.",
                operation="ensure_connected",
            )
        return self._pool

    async def store_prediction(
        self,
        group_id: str,
        domain: str,
        prediction_probability: float,
        prediction_confidence: float,
        model_version: str,
        features: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Store prediction in database.

        Args:
            group_id: Semantic group ID
            domain: Domain of prediction (btc/conflict/geopolitical)
            prediction_probability: Predicted probability
            prediction_confidence: Confidence score
            model_version: Model version used
            features: Feature values used for prediction
            trace_id: Optional trace ID for distributed tracing

        Raises:
            PostgresError: If storage fails
        """
        pool = self._ensure_connected()

        with trace_span(
            "postgres_store_prediction",
            attributes={"group_id": group_id, "trace_id": trace_id},
        ):
            try:
                start_time = datetime.now()

                query = """
                    INSERT INTO predictions (
                        group_id, domain, prediction_probability, prediction_confidence,
                        model_version, features, predicted_at, trace_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """

                async with pool.acquire() as conn:
                    await conn.execute(
                        query,
                        group_id,
                        domain,
                        prediction_probability,
                        prediction_confidence,
                        model_version,
                        features,
                        datetime.utcnow(),
                        trace_id,
                    )

                # Record latency
                duration_seconds = (datetime.now() - start_time).total_seconds()
                postgres_query_duration_seconds.labels(operation="insert").observe(duration_seconds)

                logger.debug(
                    f"Stored prediction: group_id={group_id}, domain={domain}, "
                    f"model_version={model_version}, duration_seconds={duration_seconds:.4f}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

            except Exception as e:
                logger.error(
                    f"Failed to store prediction: group_id={group_id}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                postgres_errors_total.labels(operation="insert", error_type=type(e).__name__).inc()
                raise PostgresError(
                    f"Failed to store prediction: {e}",
                    operation="insert",
                    context={"group_id": group_id},
                    trace_id=trace_id,
                )

    async def get_ground_truth_label(
        self,
        group_id: str,
        trace_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Retrieve ground-truth label for a semantic group.

        Args:
            group_id: Semantic group ID
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Dictionary containing label information, or None if not found

        Raises:
            LabelFetchError: If retrieval fails
        """
        pool = self._ensure_connected()

        with trace_span(
            "postgres_get_ground_truth",
            attributes={"group_id": group_id, "trace_id": trace_id},
        ):
            try:
                start_time = datetime.now()

                query = """
                    SELECT
                        group_id, domain, label_value, label_confidence,
                        label_source, labeled_at, event_timestamp
                    FROM ground_truth
                    WHERE group_id = $1
                    ORDER BY labeled_at DESC
                    LIMIT 1
                """

                async with pool.acquire() as conn:
                    row = await conn.fetchrow(query, group_id)

                # Record latency
                duration_seconds = (datetime.now() - start_time).total_seconds()
                postgres_query_duration_seconds.labels(operation="select").observe(duration_seconds)

                if row is None:
                    logger.debug(
                        f"No ground-truth label found: group_id={group_id}",
                        extra={"trace_id": trace_id, "group_id": group_id},
                    )
                    return None

                result = {
                    "group_id": row["group_id"],
                    "domain": row["domain"],
                    "label_value": row["label_value"],
                    "label_confidence": row["label_confidence"],
                    "label_source": row["label_source"],
                    "labeled_at": row["labeled_at"],
                    "event_timestamp": row["event_timestamp"],
                }

                logger.debug(
                    f"Retrieved ground-truth label: group_id={group_id}, "
                    f"label_source={result['label_source']}, duration_seconds={duration_seconds:.4f}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

                return result

            except Exception as e:
                logger.error(
                    f"Failed to retrieve ground-truth label: group_id={group_id}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                postgres_errors_total.labels(operation="select", error_type=type(e).__name__).inc()
                raise LabelFetchError(
                    f"Failed to retrieve ground-truth label: {e}",
                    group_id=group_id,
                    source="postgres",
                    trace_id=trace_id,
                )

    async def get_predictions_for_validation(
        self,
        limit: int = 100,
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve recent predictions for validation.

        Args:
            limit: Maximum number of predictions to retrieve
            trace_id: Optional trace ID for distributed tracing

        Returns:
            List of prediction dictionaries

        Raises:
            PostgresError: If retrieval fails
        """
        pool = self._ensure_connected()

        with trace_span(
            "postgres_get_predictions_for_validation",
            attributes={"limit": limit, "trace_id": trace_id},
        ):
            try:
                start_time = datetime.now()

                query = """
                    SELECT
                        p.group_id, p.domain, p.prediction_probability,
                        p.prediction_confidence, p.model_version, p.predicted_at,
                        gt.label_value, gt.label_confidence, gt.label_source
                    FROM predictions p
                    LEFT JOIN ground_truth gt ON p.group_id = gt.group_id
                    WHERE p.predicted_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY p.predicted_at DESC
                    LIMIT $1
                """

                async with pool.acquire() as conn:
                    rows = await conn.fetch(query, limit)

                # Record latency
                duration_seconds = (datetime.now() - start_time).total_seconds()
                postgres_query_duration_seconds.labels(operation="select").observe(duration_seconds)

                results = [dict(row) for row in rows]

                logger.debug(
                    f"Retrieved predictions for validation: count={len(results)}, "
                    f"duration_seconds={duration_seconds:.4f}",
                    extra={"trace_id": trace_id},
                )

                return results

            except Exception as e:
                logger.error(
                    f"Failed to retrieve predictions for validation: error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                postgres_errors_total.labels(operation="select", error_type=type(e).__name__).inc()
                raise PostgresError(
                    f"Failed to retrieve predictions for validation: {e}",
                    operation="select",
                    trace_id=trace_id,
                )

    async def health_check(self) -> bool:
        """
        Check if PostgreSQL is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            pool = self._ensure_connected()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL health check failed: {e}")
            return False
