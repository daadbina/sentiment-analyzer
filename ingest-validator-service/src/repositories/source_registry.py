"""Source registry repository."""

import logging
from typing import Optional, Dict, Any
import asyncpg
from src.config import get_config
from src.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class SourceRegistryRepository:
    """Repository for source registry."""

    def __init__(self):
        """Initialize source registry repository."""
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
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.debug(f"Database pool initialization skipped (optional component): {e}")
            # Database is optional - service continues without it
            self.pool = None

    async def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get source by ID.

        Args:
            source_id: Source identifier

        Returns:
            Source data or None
        """
        if not self.pool:
            logger.debug("Database not available, returning None for source lookup")
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM sources WHERE id = $1",
                    source_id,
                )
                return dict(row) if row else None
        except Exception as e:
            logger.debug(f"Failed to get source (database optional): {e}")
            return None

    async def verify_source(self, source_id: str) -> bool:
        """Verify if source is registered and active.

        Args:
            source_id: Source identifier

        Returns:
            True if source is verified
        """
        try:
            source = await self.get_source(source_id)
            if not source:
                # If database is not available, allow source by default (lenient mode)
                # This allows validation to proceed even without source registry
                if not self.pool:
                    logger.debug(f"Database not available, allowing source {source_id} by default")
                    return True
                return False

            # Check if source is active
            is_active = source.get("is_active", False)
            return is_active

        except Exception as e:
            logger.error(f"Source verification failed: {e}")
            # If database is not available, allow source by default (lenient mode)
            if not self.pool:
                logger.debug(f"Database error, allowing source {source_id} by default")
                return True
            return False

    async def get_source_credibility(self, source_id: str) -> float:
        """Get source credibility score.

        Args:
            source_id: Source identifier

        Returns:
            Credibility score (0.0-1.0)
        """
        try:
            source = await self.get_source(source_id)
            if not source:
                return 0.0

            credibility = source.get("credibility_score", 0.5)
            return float(credibility)

        except Exception as e:
            logger.error(f"Failed to get source credibility: {e}")
            return 0.0

    async def get_publisher_id(self, source_id: str) -> Optional[str]:
        """Get publisher ID for source.

        Args:
            source_id: Source identifier

        Returns:
            Publisher ID or None
        """
        try:
            source = await self.get_source(source_id)
            if not source:
                return None

            return source.get("publisher_id")

        except Exception as e:
            logger.error(f"Failed to get publisher ID: {e}")
            return None

    async def create_source(
        self,
        source_id: str,
        name: str,
        credibility_score: float = 0.5,
        is_active: bool = True,
        publisher_id: Optional[str] = None,
    ) -> bool:
        """Create new source.

        Args:
            source_id: Source identifier
            name: Source name
            credibility_score: Initial credibility score
            is_active: Whether source is active
            publisher_id: Publisher identifier

        Returns:
            True if successful
        """
        if not self.pool:
            raise DatabaseError("Database pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO sources (id, name, credibility_score, is_active, publisher_id)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (id) DO UPDATE SET
                        name = $2,
                        credibility_score = $3,
                        is_active = $4,
                        publisher_id = $5
                    """,
                    source_id,
                    name,
                    credibility_score,
                    is_active,
                    publisher_id,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to create source: {e}")
            return False

    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            try:
                await self.pool.close()
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error(f"Error closing database pool: {e}")
