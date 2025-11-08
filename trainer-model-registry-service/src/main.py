"""
Main entry point for trainer service.

Starts the service and handles lifecycle.
"""

import logging
import asyncio
import signal
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from src.config import config
from src.service import TrainerService
from src.exceptions import TrainerError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

# Global service instance
service: TrainerService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage service lifecycle.

    Args:
        app: FastAPI application
    """
    global service

    # Startup
    logger.info("Starting trainer service")
    service = TrainerService()
    await service.start()

    yield

    # Shutdown
    logger.info("Shutting down trainer service")
    await service.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Trainer & Model Registry Service",
    description="ML model training, evaluation, and registry management",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status
    """
    try:
        status = await service.health_check()
        return JSONResponse(status_code=200, content=status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": str(e)},
        )


@app.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes.

    Returns:
        Readiness status
    """
    try:
        status = await service.health_check()
        # Service is ready if all components are healthy
        if status.get("status") == "healthy":
            return JSONResponse(status_code=200, content={"ready": True})
        else:
            return JSONResponse(
                status_code=503,
                content={"ready": False, "details": status},
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"ready": False, "error": str(e)},
        )


@app.get("/live")
async def liveness_check():
    """
    Liveness check endpoint for Kubernetes.

    Returns:
        Liveness status
    """
    try:
        # Service is alive if it can respond
        return JSONResponse(
            status_code=200,
            content={"alive": True, "timestamp": datetime.now().isoformat()},
        )
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"alive": False, "error": str(e)},
        )


@app.post("/train")
async def train_models(
    start_date: str = None,
    end_date: str = None,
):
    """
    Trigger model training pipeline.

    Args:
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        Training results
    """
    try:
        logger.info("Training request received")
        result = await service.train_pipeline(start_date, end_date)
        return JSONResponse(status_code=200, content=result)
    except TrainerError as e:
        logger.error(f"Training failed: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)},
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.get("/models")
async def list_models():
    """
    List trained models.

    Returns:
        List of models
    """
    try:
        if not service.trainer:
            return JSONResponse(
                status_code=400,
                content={"error": "No models trained yet"},
            )

        models = service.trainer.compare_models()
        return JSONResponse(status_code=200, content=models)
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.get("/evaluation")
async def get_evaluation_results():
    """
    Get model evaluation results.

    Returns:
        Evaluation results
    """
    try:
        if not service.evaluator:
            return JSONResponse(
                status_code=400,
                content={"error": "No evaluations performed yet"},
            )

        results = service.evaluator.get_evaluation_results()
        return JSONResponse(status_code=200, content=results)
    except Exception as e:
        logger.error(f"Failed to get evaluation results: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.get("/drift")
async def get_drift_results():
    """
    Get drift detection results.

    Returns:
        Drift detection results
    """
    try:
        if not service.drift_detector:
            return JSONResponse(
                status_code=400,
                content={"error": "No drift detection performed yet"},
            )

        results = service.drift_detector.get_drift_history()
        return JSONResponse(status_code=200, content=results)
    except Exception as e:
        logger.error(f"Failed to get drift results: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.get("/artifacts")
async def list_artifacts():
    """
    List model artifacts.

    Returns:
        List of artifacts
    """
    try:
        if not service.artifact_manager:
            return JSONResponse(
                status_code=400,
                content={"error": "No artifacts registered yet"},
            )

        artifacts = service.artifact_manager.list_artifacts()
        return JSONResponse(status_code=200, content=artifacts)
    except Exception as e:
        logger.error(f"Failed to list artifacts: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


def main():
    """
    Main entry point.

    Starts the FastAPI server.
    """
    logger.info("Starting trainer service on port %d", config.service.port)

    uvicorn.run(
        app,
        host=config.service.host,
        port=config.service.port,
        log_level=config.service.log_level.lower(),
    )


if __name__ == "__main__":
    main()
