"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
import time
import asyncio

from .config import config
from .scheduler import ClusteringScheduler
from .migrations import MigrationRunner
from .semantic_group_initializer import initialize_semantic_groups
from .pipeline_orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)

# Initialize scheduler and orchestrator
scheduler = ClusteringScheduler()
orchestrator = scheduler.orchestrator  # Get reference to orchestrator

# Prometheus metrics
clustering_jobs_total = Counter(
    "clustering_jobs_total",
    "Total clustering jobs executed",
    ["status"],
)
clustering_duration_seconds = Histogram(
    "clustering_duration_seconds",
    "Clustering job duration in seconds",
)
clusters_created_total = Counter(
    "clusters_created_total",
    "Total clusters created",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting clustering service")
    try:
        # Run database migrations
        logger.info("Running database migrations")
        migration_runner = MigrationRunner()
        migration_runner.reset_migrations()  # Reset for development
        migration_runner.run_all_migrations()
        logger.info("Database migrations completed")

        # Initialize semantic groups at startup (country+event combinations)
        # DISABLED: Do not initialize 540 semantic groups - let them be created organically from clustering
        # logger.info("Initializing semantic groups...")
        # await initialize_semantic_groups(
        #     db_host=config.postgres.host,
        #     db_port=config.postgres.port,
        #     db_user=config.postgres.user,
        #     db_password=config.postgres.password,
        #     db_name=config.postgres.database
        # )
        logger.info("Semantic groups initialization completed")

        # Start background entities consumer
        await orchestrator.start_entities_consumer_background()
        logger.info("Background entities consumer started")

        # Start scheduler
        scheduler.start()
        logger.info("Service started successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down clustering service")
    try:
        # Stop background entities consumer
        await orchestrator.stop_entities_consumer_background()
        logger.info("Background entities consumer stopped")

        scheduler.stop()
        logger.info("Service shut down successfully")
    except Exception as e:
        logger.error(f"Shutdown failed: {e}", exc_info=True)


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Clustering-Semantic-Grouping-Service",
    description="Phase 2 semantic clustering service",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "clustering-semantic-grouping-service",
        "version": "0.1.0",
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        status = scheduler.get_job_status()
        return {
            "ready": True,
            "scheduler": status,
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


@app.get("/status")
async def get_status():
    """Get service status."""
    try:
        status = scheduler.get_job_status()
        return {
            "service": "clustering-semantic-grouping-service",
            "version": "0.1.0",
            "scheduler": status,
            "config": {
                "algorithm": config.clustering.algorithm,
                "min_cluster_size": config.clustering.min_cluster_size,
                "similarity_threshold": config.clustering.similarity_threshold,
                "execution_frequency_hours": config.clustering.execution_frequency_hours,
            },
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting status")


@app.post("/jobs/clustering/run")
async def run_clustering_job():
    """Manually trigger clustering job."""
    try:
        start_time = time.time()
        total, valid, invalid = scheduler.orchestrator.run_clustering_job()
        duration = time.time() - start_time

        clustering_jobs_total.labels(status="success").inc()
        clustering_duration_seconds.observe(duration)
        clusters_created_total.inc(valid)

        return {
            "status": "success",
            "total_clusters": total,
            "valid_clusters": valid,
            "invalid_clusters": invalid,
            "duration_seconds": duration,
        }

    except Exception as e:
        logger.error(f"Error running clustering job: {e}", exc_info=True)
        clustering_jobs_total.labels(status="error").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/clustering/status")
async def get_clustering_status():
    """Get clustering job status."""
    try:
        return scheduler.get_job_status()
    except Exception as e:
        logger.error(f"Error getting job status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting job status")


@app.post("/admin/migrate-entity-cache")
async def migrate_entity_cache_to_redis():
    """
    MIGRATION ENDPOINT: Export current in-memory entity cache to Redis.

    This endpoint should be called ONCE before upgrading to Redis-backed entity cache.
    It will copy all entities from the in-memory cache to Redis.

    After calling this endpoint and verifying success, you can restart the service
    with the new Redis-backed implementation.
    """
    try:
        # Get current in-memory cache
        entity_cache = orchestrator.entity_cache

        if not entity_cache:
            return {
                "status": "success",
                "message": "Entity cache is empty, nothing to migrate",
                "migrated_count": 0,
            }

        # Migrate to Redis using batch operation
        migrated_count = orchestrator.cache.set_entities_batch(entity_cache)

        logger.info(f"Migrated {migrated_count} entities from in-memory cache to Redis")

        return {
            "status": "success",
            "message": f"Successfully migrated {migrated_count} entities to Redis",
            "migrated_count": migrated_count,
            "cache_size_before": len(entity_cache),
            "redis_cache_size_after": orchestrator.cache.get_entity_cache_size(),
        }

    except Exception as e:
        logger.error(f"Error migrating entity cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@app.get("/admin/entity-cache-status")
async def get_entity_cache_status():
    """
    Get entity cache status (both in-memory and Redis).

    Useful for verifying migration and monitoring cache health.
    """
    try:
        in_memory_size = len(orchestrator.entity_cache)
        redis_size = orchestrator.cache.get_entity_cache_size()

        return {
            "in_memory_cache_size": in_memory_size,
            "redis_cache_size": redis_size,
            "cache_type": "in-memory" if hasattr(orchestrator, '_use_memory_cache') else "redis",
        }

    except Exception as e:
        logger.error(f"Error getting entity cache status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.service.api_host,
        port=config.service.api_port,
        log_level=config.service.log_level.lower(),
    )

