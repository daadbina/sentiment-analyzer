"""FastAPI application for health checks and metrics."""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.config import config
from src.service import EmbeddingService

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Embedding Service",
    description="Multilingual embedding generation service",
    version="0.1.0",
)

# Global service instance
service: EmbeddingService = None


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    global service
    try:
        logger.info("Starting FastAPI application...")
        service = EmbeddingService()
        await service.initialize()
        logger.info("FastAPI application started")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global service
    if service:
        await service.shutdown()
        logger.info("FastAPI application shutdown")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": "embedding-service",
                "version": "0.1.0",
            },
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        if service is None:
            raise HTTPException(status_code=503, detail="Service not initialized")

        # Check Qdrant connection
        if not service.qdrant_client.client:
            raise HTTPException(status_code=503, detail="Qdrant not connected")

        # Check Kafka connection
        if not service.kafka_consumer.consumer:
            raise HTTPException(status_code=503, detail="Kafka not connected")

        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "service": "embedding-service",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    try:
        return app.response_class(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@app.get("/info")
async def service_info():
    """Get service information."""
    try:
        return JSONResponse(
            status_code=200,
            content={
                "service": "embedding-service",
                "version": "0.1.0",
                "kafka": {
                    "brokers": config.kafka.brokers,
                    "input_topic": config.kafka.input_topic,
                    "output_topic": config.kafka.output_topic,
                },
                "qdrant": {
                    "host": config.qdrant.host,
                    "port": config.qdrant.port,
                    "collection": config.qdrant.collection_name,
                },
                "model": {
                    "device": config.model.device,
                    "batch_size_gpu": config.model.batch_size_gpu,
                    "batch_size_cpu": config.model.batch_size_cpu,
                },
            },
        )
    except Exception as e:
        logger.error(f"Failed to get service info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service info")

