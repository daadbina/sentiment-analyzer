"""Job lifecycle management with checkpointing and recovery."""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import asyncpg

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobManager:
    """Manages job lifecycle with checkpointing and recovery."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ):
        """
        Initialize job manager.

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
        logger.info(f"Initialized JobManager: {host}:{port}/{database}")

    async def initialize(self):
        """Initialize database connection pool and schema."""
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
            
            # Create job tracking tables
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS clustering.jobs (
                        id UUID PRIMARY KEY,
                        status VARCHAR(50) NOT NULL,
                        window_start TIMESTAMP WITH TIME ZONE NOT NULL,
                        window_end TIMESTAMP WITH TIME ZONE NOT NULL,
                        articles_processed INTEGER DEFAULT 0,
                        clusters_created INTEGER DEFAULT 0,
                        started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP WITH TIME ZONE,
                        error_message TEXT,
                        INDEX idx_status (status),
                        INDEX idx_started_at (started_at)
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS clustering.job_checkpoints (
                        id SERIAL PRIMARY KEY,
                        job_id UUID NOT NULL,
                        checkpoint_name VARCHAR(255) NOT NULL,
                        checkpoint_data JSONB NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (job_id) REFERENCES clustering.jobs(id) ON DELETE CASCADE,
                        INDEX idx_job_id (job_id),
                        UNIQUE(job_id, checkpoint_name)
                    )
                """)
            
            logger.info("JobManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize JobManager: {e}", exc_info=True)
            raise

    async def create_job(
        self,
        window_start: datetime,
        window_end: datetime
    ) -> str:
        """
        Create a new job.

        Args:
            window_start: Window start time
            window_end: Window end time

        Returns:
            Job ID
        """
        try:
            job_id = str(uuid.uuid4())
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO clustering.jobs (id, status, window_start, window_end)
                    VALUES ($1, $2, $3, $4)
                """, job_id, JobStatus.PENDING.value, window_start, window_end)
            
            logger.info(f"Created job {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to create job: {e}", exc_info=True)
            raise

    async def start_job(self, job_id: str) -> bool:
        """
        Start a job.

        Args:
            job_id: Job ID

        Returns:
            True if successful
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE clustering.jobs
                    SET status = $1, started_at = CURRENT_TIMESTAMP
                    WHERE id = $2
                """, JobStatus.RUNNING.value, job_id)
            
            logger.info(f"Started job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start job: {e}", exc_info=True)
            return False

    async def complete_job(
        self,
        job_id: str,
        articles_processed: int,
        clusters_created: int
    ) -> bool:
        """
        Complete a job.

        Args:
            job_id: Job ID
            articles_processed: Number of articles processed
            clusters_created: Number of clusters created

        Returns:
            True if successful
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE clustering.jobs
                    SET status = $1, completed_at = CURRENT_TIMESTAMP,
                        articles_processed = $2, clusters_created = $3
                    WHERE id = $4
                """, JobStatus.COMPLETED.value, articles_processed, clusters_created, job_id)
            
            logger.info(f"Completed job {job_id}: {articles_processed} articles, {clusters_created} clusters")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete job: {e}", exc_info=True)
            return False

    async def fail_job(self, job_id: str, error_message: str) -> bool:
        """
        Mark job as failed.

        Args:
            job_id: Job ID
            error_message: Error message

        Returns:
            True if successful
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE clustering.jobs
                    SET status = $1, completed_at = CURRENT_TIMESTAMP, error_message = $2
                    WHERE id = $3
                """, JobStatus.FAILED.value, error_message, job_id)
            
            logger.error(f"Failed job {job_id}: {error_message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark job as failed: {e}", exc_info=True)
            return False

    async def save_checkpoint(
        self,
        job_id: str,
        checkpoint_name: str,
        checkpoint_data: Dict[str, Any]
    ) -> bool:
        """
        Save job checkpoint.

        Args:
            job_id: Job ID
            checkpoint_name: Checkpoint name
            checkpoint_data: Checkpoint data

        Returns:
            True if successful
        """
        try:
            import json
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO clustering.job_checkpoints (job_id, checkpoint_name, checkpoint_data)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (job_id, checkpoint_name)
                    DO UPDATE SET checkpoint_data = $3, created_at = CURRENT_TIMESTAMP
                """, job_id, checkpoint_name, json.dumps(checkpoint_data))
            
            logger.debug(f"Saved checkpoint {checkpoint_name} for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}", exc_info=True)
            return False

    async def get_checkpoint(
        self,
        job_id: str,
        checkpoint_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get job checkpoint.

        Args:
            job_id: Job ID
            checkpoint_name: Checkpoint name

        Returns:
            Checkpoint data or None
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT checkpoint_data FROM clustering.job_checkpoints
                    WHERE job_id = $1 AND checkpoint_name = $2
                """, job_id, checkpoint_name)
            
            if row:
                logger.debug(f"Retrieved checkpoint {checkpoint_name} for job {job_id}")
                return row['checkpoint_data']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get checkpoint: {e}", exc_info=True)
            return None

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("JobManager closed")

