"""FastAPI application for Ingest Validator Service.

Provides REST API endpoints for health checks, readiness probes, and metrics.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from prometheus_client import generate_latest, REGISTRY

from src.config import get_config
from src.service import ValidatorService
from src.logging_config import setup_logging
from src.metrics import get_metrics
from src.models import NewsRaw

logger = logging.getLogger(__name__)

# Global validator instance
validator_service: ValidatorService = None
consumer_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.

    Handles startup and shutdown events.
    """
    global validator_service, consumer_task

    # Startup
    logger.info("Starting FastAPI application")
    setup_logging()

    # Initialize metrics
    metrics = get_metrics()
    logger.info("Metrics initialized")

    validator_service = ValidatorService()
    await validator_service.initialize()

    # Start message consumption loop as background task
    consumer_task = asyncio.create_task(_run_message_consumer())
    logger.info("Message consumer loop started")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application")

    # Cancel consumer task with timeout
    if consumer_task and not consumer_task.done():
        consumer_task.cancel()
        try:
            # Wait for consumer task to complete with 5-second timeout
            await asyncio.wait_for(consumer_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Consumer task did not complete within timeout, forcing shutdown")
        except asyncio.CancelledError:
            logger.info("Message consumer loop cancelled")

    # Shutdown service with 30-second timeout
    try:
        await asyncio.wait_for(validator_service.shutdown(), timeout=30.0)
    except asyncio.TimeoutError:
        logger.error("Service shutdown exceeded 30-second timeout")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


async def _run_message_consumer():
    """Run message consumer loop in background."""
    try:
        logger.info("Message consumer loop initialized")
        while True:
            try:
                await validator_service.process_message()
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                logger.info("Message consumer loop cancelled")
                raise
            except Exception as e:
                logger.error(f"Message processing error: {e}", exc_info=True)
                await asyncio.sleep(1)  # Back off on error
    except asyncio.CancelledError:
        logger.info("Message consumer loop stopped")
    except Exception as e:
        logger.error(f"Message consumer loop error: {e}", exc_info=True)


# Create FastAPI app
config = get_config()
app = FastAPI(
    title="Ingest Validator Service",
    description="Validation microservice for sentiment-analyzer-v2",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Health & Monitoring Endpoints
# ============================================================================


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Health status.
    """
    if not validator_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    health = validator_service.get_health_status()
    status_code = 200 if health["status"] == "healthy" else 503

    return JSONResponse(content=health, status_code=status_code)


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint.

    Returns:
        dict: Readiness status.
    """
    if not validator_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    ready = validator_service.is_ready()
    status_code = 200 if ready else 503

    return JSONResponse(
        content={"ready": ready},
        status_code=status_code,
    )


@app.get("/live", tags=["Health"])
async def liveness_check():
    """
    Liveness check endpoint.

    Returns:
        dict: Liveness status.
    """
    return JSONResponse(content={"alive": True})


@app.get("/metrics", tags=["Monitoring"])
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns:
        str: Prometheus metrics.
    """
    return PlainTextResponse(generate_latest(REGISTRY))


# ============================================================================
# Service Info Endpoints
# ============================================================================


@app.get("/info", tags=["Info"])
async def service_info():
    """
    Get service information.

    Returns:
        dict: Service metadata.
    """
    return JSONResponse(
        content={
            "name": "Ingest Validator Service",
            "version": "1.0.0",
            "environment": config.environment,
            "kafka_brokers": config.kafka_brokers,
            "schema_registry_url": config.schema_registry_url,
        }
    )


# ============================================================================
# Batch Processing Endpoints
# ============================================================================


class BatchValidateRequest(BaseModel):
    """Request model for batch validation."""

    messages: List[dict]


@app.post("/batch/validate", tags=["Batch"])
async def batch_validate(request: BatchValidateRequest):
    """
    Validate a batch of messages.

    Args:
        request: Batch validation request with list of messages

    Returns:
        dict: Batch validation results
    """
    if not validator_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    if not request.messages:
        return JSONResponse(
            content={
                "status": "error",
                "message": "No messages provided",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Convert dict messages to NewsRaw objects
    try:
        messages = [NewsRaw(**msg) for msg in request.messages]
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Invalid message format: {str(e)}",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    result = await validator_service.validate_batch(messages)
    status_code = 200 if result["status"] == "success" else 400

    return JSONResponse(content=result, status_code=status_code)


# ============================================================================
# Message Replay Endpoints
# ============================================================================


@app.post("/replay", tags=["Replay"])
async def replay_from_offset(partition: int, offset: int):
    """
    Replay messages from specific offset.

    Args:
        partition: Partition number
        offset: Offset to start replay from

    Returns:
        dict: Replay status information
    """
    if not validator_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    result = validator_service.replay_from_offset(partition, offset)
    status_code = 200 if result["status"] == "success" else 400

    return JSONResponse(content=result, status_code=status_code)


@app.get("/offsets/{partition}", tags=["Replay"])
async def get_partition_offsets(partition: int):
    """
    Get current and committed offsets for a partition.

    Args:
        partition: Partition number

    Returns:
        dict: Offset information
    """
    if not validator_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    result = validator_service.get_partition_offsets(partition)
    status_code = 200 if result["status"] == "success" else 400

    return JSONResponse(content=result, status_code=status_code)


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

