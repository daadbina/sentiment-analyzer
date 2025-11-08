"""FastAPI application factory."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from src.config import config
from src.clients import postgres_client, neo4j_client, redis_client
from src.storage import init_cache_manager, init_rate_limiter
from src.exceptions import APIError
from src.utils.logging import get_logger, LogContext
from src.api.routes import router as api_router
from src.metrics import metrics_recorder

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting API Analytics Service...")

    try:
        # Connect to databases
        logger.info("Connecting to databases...")
        await postgres_client.connect()
        await neo4j_client.connect()
        await redis_client.connect()

        # Initialize cache manager
        init_cache_manager(redis_client)

        # Initialize rate limiter
        init_rate_limiter(
            redis_client,
            config.rate_limit.requests_per_window,
            config.rate_limit.window_seconds,
        )

        # Health checks
        logger.info("Running health checks...")
        pg_health = await postgres_client.health_check()
        neo4j_health = await neo4j_client.health_check()
        redis_health = await redis_client.health_check()

        if not (pg_health and neo4j_health and redis_health):
            logger.error("Health check failed")
            raise RuntimeError("Health check failed")

        logger.info("API Analytics Service started successfully")

    except Exception as e:
        logger.error(f"Failed to start service: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down API Analytics Service...")

    try:
        await postgres_client.disconnect()
        await neo4j_client.disconnect()
        await redis_client.disconnect()

        logger.info("API Analytics Service shut down successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


def create_app() -> FastAPI:
    """Create FastAPI application.

    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="API Analytics Service",
        description="REST API for querying semantic groups, predictions, and analytics",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all requests."""
        with LogContext() as ctx:
            logger.info(
                f"{request.method} {request.url.path}",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "client": request.client.host if request.client else None,
                    }
                },
            )

            response = await call_next(request)

            logger.info(
                f"{request.method} {request.url.path} - {response.status_code}",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                    }
                },
            )

            return response

    # Exception handlers
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        """Handle API errors."""
        logger.error(
            f"API Error: {exc.message}",
            extra={
                "extra_fields": {
                    "error_code": exc.error_code,
                    "status_code": exc.status_code,
                    "details": exc.details,
                }
            },
        )

        metrics_recorder.record_error(request.url.path, exc.message)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "trace_id": exc.trace_id,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.error(
            f"HTTP Error: {exc.detail}",
            extra={
                "extra_fields": {
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                }
            },
        )

        metrics_recorder.record_error(request.url.path, str(exc.detail))

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": "HTTP_ERROR",
                "message": exc.detail,
                "details": None,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(
            f"Unhandled Exception: {str(exc)}",
            extra={
                "extra_fields": {
                    "exception_type": type(exc).__name__,
                    "path": request.url.path,
                }
            },
        )

        metrics_recorder.record_error(request.url.path, str(exc))

        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": None,
            },
        )

    # Health check endpoints
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        """Readiness check endpoint."""
        pg_health = await postgres_client.health_check()
        neo4j_health = await neo4j_client.health_check()
        redis_health = await redis_client.health_check()

        if pg_health and neo4j_health and redis_health:
            return {"status": "ready"}

        return JSONResponse(
            status_code=503,
            content={"status": "not_ready"},
        )

    @app.get("/live")
    async def live():
        """Liveness check endpoint."""
        return {"status": "alive"}

    # Include API routes
    app.include_router(api_router)

    logger.info("FastAPI application created")

    return app


# Create application instance
app = create_app()

