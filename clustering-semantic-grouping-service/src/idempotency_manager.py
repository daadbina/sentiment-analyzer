"""Idempotency and deduplication for exactly-once processing."""

import logging
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import asyncpg
import redis

logger = logging.getLogger(__name__)


class IdempotencyManager:
    """Manages idempotency keys and deduplication."""

    def __init__(
        self,
        postgres_host: str,
        postgres_port: int,
        postgres_user: str,
        postgres_password: str,
        postgres_db: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        ttl_seconds: int = 86400,
    ):
        """
        Initialize idempotency manager.

        Args:
            postgres_host: PostgreSQL host
            postgres_port: PostgreSQL port
            postgres_user: PostgreSQL user
            postgres_password: PostgreSQL password
            postgres_db: PostgreSQL database
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database
            ttl_seconds: TTL for idempotency keys
        """
        self.postgres_host = postgres_host
        self.postgres_port = postgres_port
        self.postgres_user = postgres_user
        self.postgres_password = postgres_password
        self.postgres_db = postgres_db
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.ttl_seconds = ttl_seconds
        self.pg_pool = None
        self.redis_client = None
        logger.info("Initialized IdempotencyManager")

    async def initialize(self):
        """Initialize database and cache connections."""
        try:
            # Initialize PostgreSQL pool
            self.pg_pool = await asyncpg.create_pool(
                host=self.postgres_host,
                port=self.postgres_port,
                user=self.postgres_user,
                password=self.postgres_password,
                database=self.postgres_db,
                min_size=2,
                max_size=10,
            )
            
            # Initialize Redis client
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True,
            )
            
            # Create idempotency table
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS clustering.idempotency_keys (
                        id SERIAL PRIMARY KEY,
                        idempotency_key VARCHAR(255) NOT NULL UNIQUE,
                        request_hash VARCHAR(64) NOT NULL,
                        result JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP WITH TIME ZONE,
                        INDEX idx_idempotency_key (idempotency_key),
                        INDEX idx_expires_at (expires_at)
                    )
                """)
            
            logger.info("IdempotencyManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize IdempotencyManager: {e}", exc_info=True)
            raise

    def generate_idempotency_key(self, data: Dict[str, Any]) -> str:
        """
        Generate idempotency key from data.

        Args:
            data: Data to generate key from

        Returns:
            Idempotency key
        """
        import json
        data_str = json.dumps(data, sort_keys=True)
        key = hashlib.sha256(data_str.encode()).hexdigest()
        logger.debug(f"Generated idempotency key: {key}")
        return key

    async def check_idempotency(
        self,
        idempotency_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if request was already processed.

        Args:
            idempotency_key: Idempotency key

        Returns:
            Previous result if exists, None otherwise
        """
        try:
            # Check Redis cache first (fast path)
            cached_result = self.redis_client.get(f"idempotency:{idempotency_key}")
            if cached_result:
                logger.debug(f"Found cached result for key {idempotency_key}")
                import json
                return json.loads(cached_result)
            
            # Check PostgreSQL
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT result FROM clustering.idempotency_keys
                    WHERE idempotency_key = $1 AND expires_at > CURRENT_TIMESTAMP
                """, idempotency_key)
            
            if row and row['result']:
                logger.debug(f"Found result in database for key {idempotency_key}")
                # Cache in Redis
                import json
                self.redis_client.setex(
                    f"idempotency:{idempotency_key}",
                    self.ttl_seconds,
                    json.dumps(row['result'])
                )
                return row['result']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check idempotency: {e}", exc_info=True)
            return None

    async def store_result(
        self,
        idempotency_key: str,
        result: Dict[str, Any],
        request_hash: str = ""
    ) -> bool:
        """
        Store result for idempotency key.

        Args:
            idempotency_key: Idempotency key
            result: Result to store
            request_hash: Request hash for verification

        Returns:
            True if successful
        """
        try:
            import json
            expires_at = datetime.now() + timedelta(seconds=self.ttl_seconds)
            
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO clustering.idempotency_keys
                    (idempotency_key, request_hash, result, expires_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (idempotency_key)
                    DO UPDATE SET result = $3, expires_at = $4
                """, idempotency_key, request_hash, json.dumps(result), expires_at)
            
            # Cache in Redis
            self.redis_client.setex(
                f"idempotency:{idempotency_key}",
                self.ttl_seconds,
                json.dumps(result)
            )
            
            logger.debug(f"Stored result for key {idempotency_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store result: {e}", exc_info=True)
            return False

    async def cleanup_expired(self) -> int:
        """
        Clean up expired idempotency keys.

        Returns:
            Number of keys deleted
        """
        try:
            async with self.pg_pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM clustering.idempotency_keys
                    WHERE expires_at < CURRENT_TIMESTAMP
                """)
            
            # Extract count from result string
            count = int(result.split()[-1]) if result else 0
            logger.info(f"Cleaned up {count} expired idempotency keys")
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired keys: {e}", exc_info=True)
            return 0

    async def close(self):
        """Close connections."""
        if self.pg_pool:
            await self.pg_pool.close()
        if self.redis_client:
            self.redis_client.close()
        logger.info("IdempotencyManager closed")

