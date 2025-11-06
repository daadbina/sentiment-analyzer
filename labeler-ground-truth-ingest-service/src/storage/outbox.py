"""Outbox pattern implementation for atomic writes across Kafka and PostgreSQL."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from src.config import config
from src.utils.trace import get_logger
from src.clients.postgres_client import PostgreSQLClient

logger = get_logger(__name__, config.logging.log_level)


class OutboxManager:
    """Manages outbox table for atomic writes across Kafka and PostgreSQL."""

    def __init__(self, postgres_client: PostgreSQLClient):
        """Initialize outbox manager.
        
        Args:
            postgres_client: PostgreSQL client instance
        """
        self.postgres_client = postgres_client
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
            
            async with self.postgres_client.get_connection() as conn:
                await conn.execute(text(create_table_sql))
                await conn.commit()
            
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
            VALUES (:id, :aggregate_id, :aggregate_type, :event_type, :payload, :trace_id)
            """
            
            async with self.postgres_client.get_connection() as conn:
                await conn.execute(
                    text(insert_sql),
                    {
                        "id": event_id,
                        "aggregate_id": aggregate_id,
                        "aggregate_type": aggregate_type,
                        "event_type": event_type,
                        "payload": json.dumps(payload),
                        "trace_id": trace_id
                    }
                )
                await conn.commit()
            
            logger.debug(
                "Event written to outbox",
                operation="write_event",
                event_id=event_id,
                aggregate_id=aggregate_id,
                event_type=event_type,
                trace_id=trace_id
            )
            
            return event_id
            
        except Exception as e:
            logger.error(
                f"Failed to write event to outbox: {str(e)}",
                operation="write_event",
                error_type=type(e).__name__
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
            LIMIT :limit
            """
            
            async with self.postgres_client.get_connection() as conn:
                result = await conn.execute(
                    text(select_sql),
                    {"limit": limit}
                )
                rows = result.fetchall()
            
            events = [
                {
                    "id": row[0],
                    "aggregate_id": row[1],
                    "aggregate_type": row[2],
                    "event_type": row[3],
                    "payload": json.loads(row[4]),
                    "trace_id": row[5]
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
            WHERE id = :id
            """
            
            async with self.postgres_client.get_connection() as conn:
                await conn.execute(
                    text(update_sql),
                    {"id": event_id}
                )
                await conn.commit()
            
            logger.debug(
                "Event marked as published",
                operation="mark_published",
                event_id=event_id
            )
            
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
            
            async with self.postgres_client.get_connection() as conn:
                result = await conn.execute(text(delete_sql))
                await conn.commit()
            
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

