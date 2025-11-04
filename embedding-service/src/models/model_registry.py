"""Model registry for tracking model versions and metadata."""

import logging
from datetime import datetime
from typing import Optional, Dict, List
import asyncpg

from src.config import config
from src.exceptions import DatabaseError, DatabaseConnectionError

logger = logging.getLogger(__name__)


class ModelRegistry:
    """PostgreSQL-based model registry for version tracking."""

    def __init__(self, pool=None):
        """
        Initialize model registry.

        Args:
            pool: Optional shared asyncpg connection pool. If None, creates its own.
        """
        self.pool = pool
        self.config = config.postgres
        self._owns_pool = pool is None

    async def initialize(self) -> None:
        """Initialize database connection pool."""
        try:
            logger.info("Initializing model registry")

            # Only create pool if not provided
            if self._owns_pool:
                logger.info("Creating model registry connection pool")
                self.pool = await asyncpg.create_pool(
                    self.config.dsn,
                    min_size=self.config.min_pool_size,
                    max_size=self.config.max_pool_size,
                    command_timeout=120,
                )

            await self._create_tables()
            logger.info("Model registry initialized")
        except Exception as e:
            logger.error(f"Failed to initialize model registry: {e}")
            raise DatabaseConnectionError(
                f"Failed to connect to database: {e}"
            )

    async def _create_tables(self) -> None:
        """Create model registry tables if they don't exist."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_registry (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(255) NOT NULL,
                    model_version VARCHAR(50) NOT NULL,
                    model_hash VARCHAR(64) NOT NULL,
                    tokenizer_hash VARCHAR(64),
                    framework VARCHAR(50),
                    embedding_dimension INT,
                    max_sequence_length INT,
                    language VARCHAR(10),
                    domain VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(model_name, model_version)
                )
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_usage_log (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(255) NOT NULL,
                    model_version VARCHAR(50) NOT NULL,
                    num_texts INT,
                    total_tokens INT,
                    compute_time_ms FLOAT,
                    device VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    async def register_model(
        self,
        model_name: str,
        model_version: str,
        model_hash: str,
        tokenizer_hash: Optional[str] = None,
        framework: str = "sentence_transformers",
        embedding_dimension: int = 768,
        max_sequence_length: int = 384,
        language: str = "multilingual",
        domain: str = "general",
    ) -> None:
        """Register a model in the registry."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO model_registry 
                    (model_name, model_version, model_hash, tokenizer_hash, 
                     framework, embedding_dimension, max_sequence_length, 
                     language, domain)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (model_name, model_version) DO UPDATE
                    SET updated_at = CURRENT_TIMESTAMP
                    """,
                    model_name,
                    model_version,
                    model_hash,
                    tokenizer_hash,
                    framework,
                    embedding_dimension,
                    max_sequence_length,
                    language,
                    domain,
                )
            logger.info(f"Registered model: {model_name} v{model_version}")
        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            raise DatabaseError(f"Failed to register model: {e}")

    async def get_model_info(
        self,
        model_name: str,
        model_version: Optional[str] = None,
    ) -> Optional[Dict]:
        """Get model information from registry."""
        try:
            async with self.pool.acquire() as conn:
                if model_version:
                    row = await conn.fetchrow(
                        """
                        SELECT * FROM model_registry 
                        WHERE model_name = $1 AND model_version = $2
                        """,
                        model_name,
                        model_version,
                    )
                else:
                    row = await conn.fetchrow(
                        """
                        SELECT * FROM model_registry 
                        WHERE model_name = $1 
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        model_name,
                    )

                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            raise DatabaseError(f"Failed to get model info: {e}")

    async def log_model_usage(
        self,
        model_name: str,
        model_version: str,
        num_texts: int,
        total_tokens: int,
        compute_time_ms: float,
        device: str,
    ) -> None:
        """Log model usage for monitoring."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO model_usage_log 
                    (model_name, model_version, num_texts, total_tokens, 
                     compute_time_ms, device)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    model_name,
                    model_version,
                    num_texts,
                    total_tokens,
                    compute_time_ms,
                    device,
                )
        except Exception as e:
            logger.warning(f"Failed to log model usage: {e}")

    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool and self._owns_pool:
            await self.pool.close()
            logger.info("Model registry connection pool closed")

