"""
Main FastAPI application.

Orchestrates all components and provides REST API.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from .config import get_config
from .utils.logging_config import setup_logging
from .utils.trace import initialize_tracing
from .utils.ab_testing import create_ab_testing_strategy
from .clients import (
    FeastClient,
    MLflowModelClient,
    RedisClient,
    PostgresClient,
    KafkaConsumerClient,
    KafkaProducerClient,
)
from .features import FeatureFetcher, FeatureValidator, FeatureReconciliationChecker
from .validation import LabelRetriever
from .models import ModelManager
from .storage import PredictionCache, PredictionLogger
from .inference import BatchPredictor
from .inference.streaming_predictor import StreamingPredictor
from .api import router, set_dependencies


logger = logging.getLogger(__name__)


# Global components
_streaming_predictor: StreamingPredictor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown logic.
    """
    # Startup
    logger.info("Starting predictor-online-inference-service")
    
    config = get_config()
    
    # Initialize clients
    feast_client = FeastClient(config.feast)
    mlflow_client = MLflowModelClient(config.mlflow)
    redis_client = RedisClient(config.redis)
    postgres_client = PostgresClient(config.postgres)
    kafka_consumer = KafkaConsumerClient(config.kafka)
    kafka_producer = KafkaProducerClient(config.kafka)
    
    # Connect clients
    await feast_client.connect()
    await redis_client.connect()
    await postgres_client.connect()
    await kafka_producer.connect()
    
    logger.info("All clients connected")
    
    # Initialize A/B testing strategy
    ab_testing_strategy = create_ab_testing_strategy(config.inference)
    
    # Initialize components
    feature_fetcher = FeatureFetcher(feast_client)
    feature_validator = FeatureValidator(
        feature_freshness_threshold_seconds=config.validation.feature_freshness_threshold_seconds
    )
    feature_reconciliation_checker = FeatureReconciliationChecker(
        reconciliation_threshold=config.validation.feature_reconciliation_threshold
    )
    label_retriever = LabelRetriever(postgres_client)
    model_manager = ModelManager(mlflow_client, ab_testing_strategy)
    prediction_cache = PredictionCache(redis_client, ttl_seconds=config.inference.cache_ttl_seconds)
    prediction_logger = PredictionLogger(postgres_client, kafka_producer)
    
    # Initialize predictors
    batch_predictor = BatchPredictor(
        model_manager=model_manager,
        feature_fetcher=feature_fetcher,
        feature_validator=feature_validator,
        prediction_cache=prediction_cache,
        prediction_logger=prediction_logger,
        batch_size=config.inference.batch_size,
    )
    
    global _streaming_predictor
    _streaming_predictor = StreamingPredictor(
        model_manager=model_manager,
        feature_fetcher=feature_fetcher,
        feature_validator=feature_validator,
        prediction_cache=prediction_cache,
        prediction_logger=prediction_logger,
        kafka_consumer=kafka_consumer,
    )
    
    # Set API dependencies
    set_dependencies(
        batch_predictor=batch_predictor,
        model_manager=model_manager,
        feature_fetcher=feature_fetcher,
        feature_validator=feature_validator,
        prediction_cache=prediction_cache,
        prediction_logger=prediction_logger,
    )
    
    # Load default model
    try:
        await model_manager.load_model()
        logger.info("Default model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load default model: {e}", exc_info=True)
        # Continue anyway - model will be loaded on first request
    
    # Start streaming predictor if enabled
    if config.inference.enable_streaming:
        import asyncio
        asyncio.create_task(_streaming_predictor.start())
        logger.info("Streaming predictor started")
    
    logger.info("Service startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down predictor-online-inference-service")
    
    # Stop streaming predictor
    if _streaming_predictor and _streaming_predictor.is_running():
        await _streaming_predictor.stop()
        logger.info("Streaming predictor stopped")
    
    # Disconnect clients
    await feast_client.disconnect()
    await redis_client.disconnect()
    await postgres_client.disconnect()
    await kafka_producer.close()
    
    logger.info("Service shutdown complete")


def create_app() -> FastAPI:
    """
    Create FastAPI application.
    
    Returns:
        FastAPI application instance
    """
    # Load configuration
    config = get_config()
    
    # Setup logging
    setup_logging(config.monitoring.log_level)
    
    # Initialize tracing
    initialize_tracing(
        service_name="predictor-online-inference-service",
        jaeger_host=config.monitoring.jaeger_host,
        jaeger_port=config.monitoring.jaeger_port,
    )
    
    # Create FastAPI app
    app = FastAPI(
        title="Predictor Online Inference Service",
        description="Real-time and batch ML inference for event realization predictions",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(router, prefix="/api/v1")
    
    # Mount Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    
    logger.info("FastAPI application created")
    
    return app


# Create application instance
app = create_app()

