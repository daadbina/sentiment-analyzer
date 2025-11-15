"""Main FastAPI application for conflict dashboard service."""

import structlog
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry, REGISTRY
from fastapi import Response
import os

from .config import settings
from .database import PostgresClient, RedisCache
from .api import routes
from .models import HealthResponse
from . import __version__, __service_name__

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Prometheus metrics - use try/except to handle reload scenarios
try:
    request_count = Counter(
        "dashboard_requests_total",
        "Total dashboard requests",
        ["endpoint", "method", "status"],
    )
    request_duration = Histogram(
        "dashboard_request_duration_seconds",
        "Dashboard request duration",
        ["endpoint"],
    )
except ValueError:
    # Metrics already registered (happens during reload)
    request_count = REGISTRY._names_to_collectors.get("dashboard_requests_total")
    request_duration = REGISTRY._names_to_collectors.get("dashboard_request_duration_seconds")

# Initialize database clients
postgres_client = PostgresClient()
redis_cache = RedisCache()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown)."""
    # Startup
    logger.info(
        "service_starting",
        service=__service_name__,
        version=__version__,
        port=settings.service_port,
    )

    # Connect to PostgreSQL
    await postgres_client.connect()

    # Connect to Redis
    await redis_cache.connect()

    logger.info("service_started")

    yield

    # Shutdown
    logger.info("service_shutting_down")

    # Disconnect from PostgreSQL
    await postgres_client.disconnect()

    # Disconnect from Redis
    await redis_cache.disconnect()

    logger.info("service_stopped")


# Create FastAPI app
app = FastAPI(
    title="Conflict Prediction Dashboard Service",
    description="Interactive dashboard for conflict predictions",
    version=__version__,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set global instances for routes
routes.postgres_client = postgres_client
routes.redis_cache = redis_cache


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    db_healthy = await postgres_client.health_check()
    cache_healthy = await redis_cache.health_check()
    
    status = "healthy" if (db_healthy and cache_healthy) else "unhealthy"
    
    return HealthResponse(
        status=status,
        service=__service_name__,
        version=__version__,
        timestamp=datetime.utcnow(),
        database="connected" if db_healthy else "disconnected",
        cache="connected" if cache_healthy else "disconnected",
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Include dashboard routes
app.include_router(routes.router)


# Serve frontend static files (will be added later)
frontend_dist = os.path.join(os.path.dirname(__file__), "static", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        """Serve frontend index.html."""
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )

