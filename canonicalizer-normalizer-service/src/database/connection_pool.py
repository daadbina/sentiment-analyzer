"""Database connection pooling and health checks."""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class PoolStats:
    """Connection pool statistics."""

    total_connections: int
    available_connections: int
    in_use_connections: int
    total_created: int
    total_closed: int
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0


class ConnectionPoolManager:
    """Manage database connection pool with health checks."""

    def __init__(
        self,
        dsn: str,
        min_size: int = 10,
        max_size: int = 20,
        max_queries: int = 50000,
        max_cached_statement_lifetime: int = 300,
        max_cacheable_statement_size: int = 15000,
        health_check_interval: int = 30,
        health_check_timeout: int = 5,
    ):
        """Initialize connection pool manager.

        Args:
            dsn: Database connection string
            min_size: Minimum pool size
            max_size: Maximum pool size
            max_queries: Max queries before connection reset
            max_cached_statement_lifetime: Max statement cache lifetime
            max_cacheable_statement_size: Max statement cache size
            health_check_interval: Health check interval in seconds
            health_check_timeout: Health check timeout in seconds
        """
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.max_queries = max_queries
        self.max_cached_statement_lifetime = max_cached_statement_lifetime
        self.max_cacheable_statement_size = max_cacheable_statement_size
        self.health_check_interval = health_check_interval
        self.health_check_timeout = health_check_timeout

        self.pool: Optional[asyncpg.Pool] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.stats = PoolStats(
            total_connections=0,
            available_connections=0,
            in_use_connections=0,
            total_created=0,
            total_closed=0,
        )

    async def initialize(self) -> None:
        """Initialize connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=self.min_size,
                max_size=self.max_size,
                max_queries=self.max_queries,
                max_cached_statement_lifetime=self.max_cached_statement_lifetime,
                max_cacheable_statement_size=self.max_cacheable_statement_size,
            )
            logger.info(f"Connection pool initialized: min={self.min_size}, max={self.max_size}")

            # Start health check task
            self.health_check_task = asyncio.create_task(self._health_check_loop())
        except Exception as e:
            logger.error(f"Error initializing connection pool: {e}")
            raise

    async def close(self) -> None:
        """Close connection pool."""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        if self.pool:
            await self.pool.close()
            logger.info("Connection pool closed")

    async def acquire(self) -> asyncpg.Connection:
        """Acquire connection from pool.

        Returns:
            Database connection
        """
        if not self.pool:
            raise RuntimeError("Connection pool not initialized")
        return await self.pool.acquire()

    async def execute(self, query: str, *args) -> list:
        """Execute query using pool.

        Args:
            query: SQL query
            *args: Query arguments

        Returns:
            Query results
        """
        if not self.pool:
            raise RuntimeError("Connection pool not initialized")
        return await self.pool.fetch(query, *args)

    async def execute_one(self, query: str, *args) -> Optional[dict]:
        """Execute query and return one result.

        Args:
            query: SQL query
            *args: Query arguments

        Returns:
            Query result or None
        """
        if not self.pool:
            raise RuntimeError("Connection pool not initialized")
        return await self.pool.fetchrow(query, *args)

    async def execute_scalar(self, query: str, *args):
        """Execute query and return scalar value.

        Args:
            query: SQL query
            *args: Query arguments

        Returns:
            Scalar value
        """
        if not self.pool:
            raise RuntimeError("Connection pool not initialized")
        return await self.pool.fetchval(query, *args)

    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    async def _perform_health_check(self) -> None:
        """Perform health check on pool."""
        if not self.pool:
            return

        try:
            # Test connection
            async with asyncio.timeout(self.health_check_timeout):
                async with self.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")

            self.stats.last_health_check = datetime.now(timezone.utc)
            self.stats.health_check_failures = 0
            logger.debug("Health check passed")
        except Exception as e:
            self.stats.health_check_failures += 1
            logger.warning(f"Health check failed: {e}")

    def get_stats(self) -> PoolStats:
        """Get pool statistics.

        Returns:
            Pool statistics
        """
        if self.pool:
            self.stats.total_connections = self.pool.get_size()
            self.stats.available_connections = self.pool.get_idle_size()
            self.stats.in_use_connections = self.stats.total_connections - self.stats.available_connections
        return self.stats

    async def create_indexes(self) -> None:
        """Create database indexes for frequently queried fields."""
        if not self.pool:
            raise RuntimeError("Connection pool not initialized")

        indexes = [
            # Publisher domain index
            "CREATE INDEX IF NOT EXISTS idx_publishers_domain ON publishers(domain)",
            # Article URL hash index
            "CREATE INDEX IF NOT EXISTS idx_articles_url_hash ON articles(url_hash)",
            # Canonicalization timestamp index
            "CREATE INDEX IF NOT EXISTS idx_articles_canonicalized_at ON articles(canonicalized_at)",
            # Domain classification index
            "CREATE INDEX IF NOT EXISTS idx_articles_domain ON articles(domain)",
            # Publisher ID index
            "CREATE INDEX IF NOT EXISTS idx_articles_publisher_id ON articles(publisher_id)",
        ]

        try:
            for index_sql in indexes:
                await self.pool.execute(index_sql)
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            raise


class IndexManager:
    """Manage database indexes."""

    def __init__(self, pool_manager: ConnectionPoolManager):
        """Initialize index manager.

        Args:
            pool_manager: Connection pool manager
        """
        self.pool_manager = pool_manager

    async def create_all_indexes(self) -> None:
        """Create all recommended indexes."""
        await self.pool_manager.create_indexes()

    async def get_index_stats(self) -> dict:
        """Get index statistics.

        Returns:
            Index statistics
        """
        if not self.pool_manager.pool:
            return {}

        query = """
            SELECT
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """

        try:
            results = await self.pool_manager.execute(query)
            return {
                'indexes': [dict(row) for row in results],
                'count': len(results),
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}

