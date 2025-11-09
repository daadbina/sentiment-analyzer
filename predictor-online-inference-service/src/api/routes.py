"""
API routes for prediction service.

Provides REST endpoints for synchronous inference.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from ..exceptions import (
    FeatureFetchError,
    FeatureValidationError,
    InferenceError,
)
from ..features.feature_fetcher import FeatureFetcher
from ..features.feature_validator import FeatureValidator
from ..inference.batch_predictor import BatchPredictor
from ..metrics import MetricsCollector
from ..models.model_manager import ModelManager
from ..storage.prediction_cache import PredictionCache
from ..storage.prediction_logger import PredictionLogger
from ..utils.trace import TracingContext, trace_span, generate_trace_id
from .schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    ErrorResponse,
    HealthResponse,
    ModelMetadataResponse,
    PredictionRequest,
    PredictionResponse,
)

logger = logging.getLogger(__name__)


# Create router
router = APIRouter()


# Dependency injection - will be set by main application
_batch_predictor: BatchPredictor = None
_model_manager: ModelManager = None
_feature_fetcher: FeatureFetcher = None
_feature_validator: FeatureValidator = None
_prediction_cache: PredictionCache = None
_prediction_logger: PredictionLogger = None


def set_dependencies(
    batch_predictor: BatchPredictor,
    model_manager: ModelManager,
    feature_fetcher: FeatureFetcher,
    feature_validator: FeatureValidator,
    prediction_cache: PredictionCache,
    prediction_logger: PredictionLogger,
) -> None:
    """
    Set dependencies for API routes.

    Args:
        batch_predictor: Batch predictor instance
        model_manager: Model manager instance
        feature_fetcher: Feature fetcher instance
        feature_validator: Feature validator instance
        prediction_cache: Prediction cache instance
        prediction_logger: Prediction logger instance
    """
    global _batch_predictor, _model_manager, _feature_fetcher, _feature_validator, _prediction_cache, _prediction_logger
    _batch_predictor = batch_predictor
    _model_manager = model_manager
    _feature_fetcher = feature_fetcher
    _feature_validator = feature_validator
    _prediction_cache = prediction_cache
    _prediction_logger = prediction_logger


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Make single prediction",
    description="Make prediction for a single semantic group",
)
async def predict(request: PredictionRequest) -> PredictionResponse:
    """
    Make prediction for a single semantic group.

    Args:
        request: Prediction request

    Returns:
        Prediction response

    Raises:
        HTTPException: If prediction fails
    """
    trace_id = generate_trace_id()

    with trace_span(
        "api_predict",
        attributes={
            "group_id": request.group_id,
            "domain": request.domain,
            "trace_id": trace_id,
        },
    ):
        start_time = datetime.now()

        try:
            logger.info(
                f"API predict request: group_id={request.group_id}, domain={request.domain}",
                extra={"trace_id": trace_id, "group_id": request.group_id},
            )

            # Make batch prediction with single group
            predictions = await _batch_predictor.predict_batch(
                group_ids=[request.group_id],
                domain=request.domain,
                trace_id=trace_id,
            )

            if not predictions:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No prediction returned",
                )

            prediction = predictions[0]

            # Calculate API latency
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Record API metrics
            MetricsCollector.record_api_request(
                endpoint="/predict",
                method="POST",
                status_code=200,
                latency_ms=latency_ms,
            )

            logger.info(
                f"API predict completed: group_id={request.group_id}, "
                f"latency_ms={latency_ms:.2f}",
                extra={"trace_id": trace_id, "latency_ms": latency_ms},
            )

            return PredictionResponse(
                group_id=prediction["group_id"],
                domain=prediction["domain"],
                prediction_probability=prediction["prediction_probability"],
                prediction_confidence=prediction["prediction_confidence"],
                model_version=prediction["model_version"],
                predicted_at=prediction["predicted_at"],
                trace_id=trace_id,
            )

        except (FeatureFetchError, FeatureValidationError, InferenceError) as e:
            logger.error(
                f"API predict failed: group_id={request.group_id}, error={e}",
                exc_info=True,
                extra={"trace_id": trace_id},
            )

            # Record API metrics
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            MetricsCollector.record_api_request(
                endpoint="/predict",
                method="POST",
                status_code=500,
                latency_ms=latency_ms,
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": type(e).__name__,
                    "message": str(e),
                    "trace_id": trace_id,
                },
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected API error: group_id={request.group_id}, error={e}",
                exc_info=True,
                extra={"trace_id": trace_id},
            )

            # Record API metrics
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            MetricsCollector.record_api_request(
                endpoint="/predict",
                method="POST",
                status_code=500,
                latency_ms=latency_ms,
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "InternalServerError",
                    "message": "An unexpected error occurred",
                    "trace_id": trace_id,
                },
            ) from e


@router.post(
    "/predict/batch",
    response_model=BatchPredictionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Make batch predictions",
    description="Make predictions for multiple semantic groups",
)
async def predict_batch(request: BatchPredictionRequest) -> BatchPredictionResponse:
    """
    Make predictions for multiple semantic groups.

    Args:
        request: Batch prediction request

    Returns:
        Batch prediction response

    Raises:
        HTTPException: If prediction fails
    """
    trace_id = generate_trace_id()

    with trace_span(
        "api_predict_batch",
        attributes={
            "batch_size": len(request.group_ids),
            "domain": request.domain,
            "trace_id": trace_id,
        },
    ):
        start_time = datetime.now()

        try:
            logger.info(
                f"API batch predict request: batch_size={len(request.group_ids)}, "
                f"domain={request.domain}",
                extra={"trace_id": trace_id},
            )

            # Make batch prediction
            predictions = await _batch_predictor.predict_batch(
                group_ids=request.group_ids,
                domain=request.domain,
                trace_id=trace_id,
            )

            # Calculate API latency
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Record API metrics
            MetricsCollector.record_api_request(
                endpoint="/predict/batch",
                method="POST",
                status_code=200,
                latency_ms=latency_ms,
            )

            logger.info(
                f"API batch predict completed: batch_size={len(request.group_ids)}, "
                f"predictions={len(predictions)}, latency_ms={latency_ms:.2f}",
                extra={"trace_id": trace_id, "latency_ms": latency_ms},
            )

            # Convert to response models
            prediction_responses = [
                PredictionResponse(
                    group_id=p["group_id"],
                    domain=p["domain"],
                    prediction_probability=p["prediction_probability"],
                    prediction_confidence=p["prediction_confidence"],
                    model_version=p["model_version"],
                    predicted_at=p["predicted_at"],
                    trace_id=trace_id,
                )
                for p in predictions
            ]

            return BatchPredictionResponse(
                predictions=prediction_responses,
                total=len(prediction_responses),
            )

        except Exception as e:
            logger.error(
                f"API batch predict failed: error={e}",
                exc_info=True,
                extra={"trace_id": trace_id},
            )

            # Record API metrics
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            MetricsCollector.record_api_request(
                endpoint="/predict/batch",
                method="POST",
                status_code=500,
                latency_ms=latency_ms,
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": type(e).__name__,
                    "message": str(e),
                    "trace_id": trace_id,
                },
            ) from e


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check service and dependency health",
)
async def health() -> HealthResponse:
    """
    Check service and dependency health.

    Returns:
        Health response with service and dependency status
    """
    dependencies = {}

    # Check MLflow
    try:
        if _model_manager and _model_manager.mlflow_client:
            await _model_manager.mlflow_client.health_check()
            dependencies["mlflow"] = "healthy"
        else:
            dependencies["mlflow"] = "not_initialized"
    except Exception as e:
        logger.warning(f"MLflow health check failed: {e}")
        dependencies["mlflow"] = "unhealthy"

    # Check Feast
    try:
        if _feature_fetcher and _feature_fetcher.feast_client:
            await _feature_fetcher.feast_client.health_check()
            dependencies["feast"] = "healthy"
        else:
            dependencies["feast"] = "not_initialized"
    except Exception as e:
        logger.warning(f"Feast health check failed: {e}")
        dependencies["feast"] = "unhealthy"

    # Check Redis
    try:
        if _prediction_cache and _prediction_cache.redis_client:
            await _prediction_cache.redis_client.health_check()
            dependencies["redis"] = "healthy"
        else:
            dependencies["redis"] = "not_initialized"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        dependencies["redis"] = "unhealthy"

    # Check PostgreSQL
    try:
        if _prediction_logger and _prediction_logger.postgres_client:
            await _prediction_logger.postgres_client.health_check()
            dependencies["postgres"] = "healthy"
        else:
            dependencies["postgres"] = "not_initialized"
    except Exception as e:
        logger.warning(f"PostgreSQL health check failed: {e}")
        dependencies["postgres"] = "unhealthy"

    # Check Kafka
    try:
        if _prediction_logger and _prediction_logger.kafka_producer:
            await _prediction_logger.kafka_producer.health_check()
            dependencies["kafka"] = "healthy"
        else:
            dependencies["kafka"] = "not_initialized"
    except Exception as e:
        logger.warning(f"Kafka health check failed: {e}")
        dependencies["kafka"] = "unhealthy"

    # Determine overall status
    all_healthy = all(status == "healthy" for status in dependencies.values())
    overall_status = "healthy" if all_healthy else "degraded"

    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        dependencies=dependencies,
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if service is ready to accept requests (all dependencies healthy)",
)
async def ready() -> HealthResponse:
    """
    Check if service is ready to accept requests.

    Returns 200 only if all dependencies are healthy and initialized.
    Used by Kubernetes readiness probes.

    Returns:
        Health response with service and dependency status

    Raises:
        HTTPException: If service is not ready (503)
    """
    dependencies = {}

    # Check all dependencies - must all be healthy for readiness
    checks = {
        "mlflow": (_model_manager, lambda: _model_manager.mlflow_client.health_check()),
        "feast": (_feature_fetcher, lambda: _feature_fetcher.feast_client.health_check()),
        "redis": (_prediction_cache, lambda: _prediction_cache.redis_client.health_check()),
        "postgres": (_prediction_logger, lambda: _prediction_logger.postgres_client.health_check()),
        "kafka": (_prediction_logger, lambda: _prediction_logger.kafka_producer.health_check()),
    }

    for name, (component, health_check) in checks.items():
        try:
            if component:
                await health_check()
                dependencies[name] = "healthy"
            else:
                dependencies[name] = "not_initialized"
        except Exception as e:
            logger.warning(f"{name} readiness check failed: {e}")
            dependencies[name] = "unhealthy"

    # Service is ready only if all dependencies are healthy
    all_healthy = all(status == "healthy" for status in dependencies.values())

    if not all_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "dependencies": dependencies,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    return HealthResponse(
        status="ready",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        dependencies=dependencies,
    )


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Check if service is alive (basic health check)",
)
async def live() -> dict[str, Any]:
    """
    Check if service is alive.

    Returns 200 if the service process is running.
    Used by Kubernetes liveness probes.
    Does not check dependencies - only checks if the service itself is responsive.

    Returns:
        Basic liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@router.get(
    "/model/metadata",
    response_model=ModelMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Get model metadata",
    description="Get metadata for the current model version",
)
async def get_model_metadata() -> ModelMetadataResponse:
    """
    Get metadata for the current model version.

    Returns:
        Model metadata response

    Raises:
        HTTPException: If metadata retrieval fails
    """
    try:
        metadata = await _model_manager.get_model_metadata()

        return ModelMetadataResponse(
            model_name=metadata.get("name", "unknown"),
            model_version=metadata.get("version", "unknown"),
            stage=metadata.get("stage", "unknown"),
            created_at=metadata.get("creation_timestamp"),
            description=metadata.get("description"),
            tags=metadata.get("tags", {}),
        )

    except Exception as e:
        logger.error(f"Failed to get model metadata: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ModelMetadataError",
                "message": str(e),
            },
        ) from e
