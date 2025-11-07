"""Outbox pattern implementation for atomic writes across Kafka and PostgreSQL."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from src.config import config
from src.utils.trace import get_logger

logger = get_logger(__name__, config.logging.log_level)


class OutboxManager:
    """Manages outbox table for atomic writes across Kafka and PostgreSQL."""

    def __init__(self, postgres_writer):
        """Initialize outbox manager.

        Args:
            postgres_writer: PostgreSQL writer instance with pool
        """
        self.postgres_writer = postgres_writer
        self.outbox_table = "outbox"

    async def initialize(self):
        """Create outbox table if not exists."""
        try:
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.outbox_table} (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                aggregate_id VARCHAR(255) NOT NULL,
                aggregate_type VARCHAR(255) NOT NULL,
                event_type VARCHAR(255) NOT NULL,
                payload JSONB NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                published_at TIMESTAMP,
                published BOOLEAN NOT NULL DEFAULT FALSE,
                retry_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                trace_id VARCHAR(255)
            );

            CREATE INDEX IF NOT EXISTS idx_outbox_published
                ON {self.outbox_table}(published)
                WHERE published = FALSE;

            CREATE INDEX IF NOT EXISTS idx_outbox_created_at
                ON {self.outbox_table}(created_at);
            """

            conn = await self.postgres_writer.pool.acquire()
            try:
                await conn.execute(create_table_sql)
            finally:
                await self.postgres_writer.pool.release(conn)

            logger.info(
                "Outbox table initialized",
                operation="initialize",
                table=self.outbox_table
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize outbox table: {str(e)}",
                operation="initialize",
                error_type=type(e).__name__
            )
            raise

    async def write_event(
        self,
        aggregate_id: str,
        aggregate_type: str,
        event_type: str,
        payload: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> str:
        """Write event to outbox.
        
        Args:
            aggregate_id: ID of aggregate (e.g., group_id)
            aggregate_type: Type of aggregate (e.g., "semantic_group")
            event_type: Type of event (e.g., "label_created")
            payload: Event payload
            trace_id: Distributed trace ID
            
        Returns:
            Event ID
        """
        try:
            event_id = str(uuid.uuid4())

            insert_sql = f"""
            INSERT INTO {self.outbox_table}
            (id, aggregate_id, aggregate_type, event_type, payload, trace_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            """

            conn = await self.postgres_writer.pool.acquire()
            try:
                await conn.execute(
                    insert_sql,
                    event_id,
                    aggregate_id,
                    aggregate_type,
                    event_type,
                    json.dumps(payload),
                    trace_id
                )
            finally:
                await self.postgres_writer.pool.release(conn)
            
            # Only log every 1000 events to reduce noise
            # (removed verbose per-event logging)
            
            return event_id
            
        except Exception as e:
            logger.error(
                f"Failed to write event to outbox: {str(e)}",
                operation="write_event",
                error_type=type(e).__name__
            )
            raise

    async def write_events_batch(
        self,
        events: List[Dict[str, Any]]
    ) -> List[str]:
        """Write multiple events to outbox in a single batch operation.

        Args:
            events: List of event dictionaries with keys:
                - aggregate_id: ID of aggregate
                - aggregate_type: Type of aggregate
                - event_type: Type of event
                - payload: Event payload
                - trace_id: Optional distributed trace ID

        Returns:
            List of event IDs
        """
        if not events:
            return []

        try:
            event_ids = []

            # Use executemany for batch insert
            insert_sql = f"""
            INSERT INTO {self.outbox_table}
            (id, aggregate_id, aggregate_type, event_type, payload, trace_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            """

            conn = await self.postgres_writer.pool.acquire()
            try:
                # Prepare batch data
                batch_data = []
                for event in events:
                    event_id = str(uuid.uuid4())
                    event_ids.append(event_id)
                    batch_data.append((
                        event_id,
                        event["aggregate_id"],
                        event["aggregate_type"],
                        event["event_type"],
                        json.dumps(event["payload"]),
                        event.get("trace_id")
                    ))

                # Execute batch insert
                await conn.executemany(insert_sql, batch_data)

                logger.info(
                    f"Batch wrote {len(event_ids)} events to outbox",
                    operation="write_events_batch",
                    event_count=len(event_ids)
                )

            finally:
                await self.postgres_writer.pool.release(conn)

            return event_ids

        except Exception as e:
            logger.error(
                f"Failed to write batch events to outbox: {str(e)}",
                operation="write_events_batch",
                error_type=type(e).__name__,
                event_count=len(events)
            )
            raise

    async def get_unpublished_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get unpublished events from outbox.
        
        Args:
            limit: Maximum number of events to retrieve
            
        Returns:
            List of unpublished events
        """
        try:
            select_sql = f"""
            SELECT id, aggregate_id, aggregate_type, event_type, payload, trace_id
            FROM {self.outbox_table}
            WHERE published = FALSE
            ORDER BY created_at ASC
            LIMIT $1
            """

            conn = await self.postgres_writer.pool.acquire()
            try:
                rows = await conn.fetch(select_sql, limit)
            finally:
                await self.postgres_writer.pool.release(conn)

            events = [
                {
                    "id": row["id"],
                    "aggregate_id": row["aggregate_id"],
                    "aggregate_type": row["aggregate_type"],
                    "event_type": row["event_type"],
                    "payload": json.loads(row["payload"]),
                    "trace_id": row["trace_id"]
                }
                for row in rows
            ]
            
            logger.debug(
                "Retrieved unpublished events",
                operation="get_unpublished_events",
                event_count=len(events)
            )
            
            return events
            
        except Exception as e:
            logger.error(
                f"Failed to get unpublished events: {str(e)}",
                operation="get_unpublished_events",
                error_type=type(e).__name__
            )
            return []

    async def mark_published(self, event_id: str):
        """Mark event as published.
        
        Args:
            event_id: Event ID to mark as published
        """
        try:
            update_sql = f"""
            UPDATE {self.outbox_table}
            SET published = TRUE, published_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """

            conn = await self.postgres_writer.pool.acquire()
            try:
                await conn.execute(update_sql, event_id)
            finally:
                await self.postgres_writer.pool.release(conn)

            # Removed verbose "Event marked as published" log - too noisy
            
        except Exception as e:
            logger.error(
                f"Failed to mark event as published: {str(e)}",
                operation="mark_published",
                event_id=event_id,
                error_type=type(e).__name__
            )
            raise

    async def cleanup_published_events(self, days_old: int = 7):
        """Clean up published events older than specified days.
        
        Args:
            days_old: Delete events published more than N days ago
        """
        try:
            delete_sql = f"""
            DELETE FROM {self.outbox_table}
            WHERE published = TRUE
            AND published_at < CURRENT_TIMESTAMP - INTERVAL '{days_old} days'
            """

            conn = await self.postgres_writer.pool.acquire()
            try:
                await conn.execute(delete_sql)
            finally:
                await self.postgres_writer.pool.release(conn)
            
            logger.info(
                "Cleaned up published events",
                operation="cleanup_published_events",
                days_old=days_old
            )
            
        except Exception as e:
            logger.error(
                f"Failed to cleanup published events: {str(e)}",
                operation="cleanup_published_events",
                error_type=type(e).__name__
            )

