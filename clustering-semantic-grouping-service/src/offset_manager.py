"""Offset management for exactly-once semantics in Kafka."""

import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
import asyncpg

logger = logging.getLogger(__name__)


class OffsetManager:
    """Manages Kafka offsets for exactly-once semantics."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ):
        """
        Initialize offset manager.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            user: PostgreSQL user
            password: PostgreSQL password
            database: PostgreSQL database
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool = None
        logger.info(f"Initialized OffsetManager: {host}:{port}/{database}")

    async def initialize(self):
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=2,
                max_size=10,
            )
            
            # Create offset tracking table if not exists
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS clustering.kafka_offsets (
                        id SERIAL PRIMARY KEY,
                        topic VARCHAR(255) NOT NULL,
                        partition INTEGER NOT NULL,
                        offset BIGINT NOT NULL,
                        group_id VARCHAR(255) NOT NULL,
                        committed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(topic, partition, group_id),
                        INDEX idx_topic_partition (topic, partition),
                        INDEX idx_group_id (group_id)
                    )
                """)
            
            logger.info("OffsetManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OffsetManager: {e}", exc_info=True)
            raise

    async def get_offset(
        self,
        topic: str,
        partition: int,
        group_id: str
    ) -> Optional[int]:
        """
        Get last committed offset.

        Args:
            topic: Kafka topic
            partition: Partition number
            group_id: Consumer group ID

        Returns:
            Last committed offset or None
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT offset FROM clustering.kafka_offsets
                    WHERE topic = $1 AND partition = $2 AND group_id = $3
                    ORDER BY committed_at DESC LIMIT 1
                """, topic, partition, group_id)
            
            if row:
                logger.debug(f"Retrieved offset for {topic}[{partition}]: {row['offset']}")
                return row['offset']
            
            logger.debug(f"No offset found for {topic}[{partition}], starting from beginning")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get offset: {e}", exc_info=True)
            raise

    async def commit_offset(
        self,
        topic: str,
        partition: int,
        offset: int,
        group_id: str
    ) -> bool:
        """
        Commit offset after successful processing.

        Args:
            topic: Kafka topic
            partition: Partition number
            offset: Offset to commit
            group_id: Consumer group ID

        Returns:
            True if successful
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO clustering.kafka_offsets (topic, partition, offset, group_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (topic, partition, group_id)
                    DO UPDATE SET offset = $3, committed_at = CURRENT_TIMESTAMP
                """, topic, partition, offset, group_id)
            
            logger.debug(f"Committed offset for {topic}[{partition}]: {offset}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit offset: {e}", exc_info=True)
            return False

    async def get_all_offsets(self, group_id: str) -> Dict[Tuple[str, int], int]:
        """
        Get all offsets for a consumer group.

        Args:
            group_id: Consumer group ID

        Returns:
            Dictionary of (topic, partition) -> offset
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT topic, partition, offset FROM clustering.kafka_offsets
                    WHERE group_id = $1
                """, group_id)
            
            offsets = {(row['topic'], row['partition']): row['offset'] for row in rows}
            logger.debug(f"Retrieved {len(offsets)} offsets for group {group_id}")
            return offsets
            
        except Exception as e:
            logger.error(f"Failed to get all offsets: {e}", exc_info=True)
            raise

    async def reset_offsets(self, group_id: str) -> bool:
        """
        Reset all offsets for a consumer group.

        Args:
            group_id: Consumer group ID

        Returns:
            True if successful
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    DELETE FROM clustering.kafka_offsets WHERE group_id = $1
                """, group_id)
            
            logger.info(f"Reset offsets for group {group_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset offsets: {e}", exc_info=True)
            return False

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("OffsetManager closed")

