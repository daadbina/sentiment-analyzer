"""
Main Service Orchestrator for Predictor Online Inference Service.

Coordinates all components including feature store, label store, models,
and provides unified service lifecycle management.
"""

import logging
import asyncio
from typing import Optional
from datetime import datetime

from .config import Config, get_config
from .clients import (
    FeastClient,
    MLflowModelClient,
    RedisClient,
    PostgresClient,
    KafkaConsumerClient,
    KafkaProducerClient,
)
from .features import (
    FeatureFetcher,
    FeatureValidator,
    FeatureReconciliationChecker,
)
from .features.feature_store_adapter import FeatureStoreAdapter
from .features.feature_quality_monitor import FeatureQualityMonitor
from .validation import LabelRetriever
from .validation.prediction_validator import PredictionValidator
from .validation.label_reconciliation_service import LabelReconciliationService
from .validation.drift_detector import DriftDetector
from .models import ModelManager
from .models.model_loader import ModelLoader
from .storage import PredictionCache, PredictionLogger
from .inference import BatchPredictor
from .inference.streaming_predictor import StreamingPredictor
from .inference.confidence_scorer import ConfidenceScorer
from .metrics import MetricsCollector
from .utils.logging_config import setup_logging
from .utils.trace import initialize_tracing
from .utils.ab_testing import create_ab_testing_strategy
from .exceptions import ServiceError

logger = logging.getLogger(__name__)


class PredictorService:
    """
    Main orchestrator for Predictor Online Inference Service.
    
    Coordinates all components and provides unified lifecycle management.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize predictor service.
        
        Args:
            config: Service configuration (None = load from environment)
        """
        self.config = config or get_config()
        self._initialized = False
        self._running = False
        
        # Clients
        self.feast_client: Optional[FeastClient] = None
        self.mlflow_client: Optional[MLflowModelClient] = None
        self.redis_client: Optional[RedisClient] = None
        self.postgres_client: Optional[PostgresClient] = None
        self.kafka_consumer: Optional[KafkaConsumerClient] = None
        self.kafka_producer: Optional[KafkaProducerClient] = None
        
        # Core components
        self.metrics: Optional[MetricsCollector] = None
        self.feature_store_adapter: Optional[FeatureStoreAdapter] = None
        self.model_loader: Optional[ModelLoader] = None
        self.confidence_scorer: Optional[ConfidenceScorer] = None
        self.prediction_validator: Optional[PredictionValidator] = None
        self.feature_quality_monitor: Optional[FeatureQualityMonitor] = None
        self.drift_detector: Optional[DriftDetector] = None
        
        # Existing components
        self.feature_fetcher: Optional[FeatureFetcher] = None
        self.feature_validator: Optional[FeatureValidator] = None
        self.feature_reconciliation_checker: Optional[FeatureReconciliationChecker] = None
        self.label_retriever: Optional[LabelRetriever] = None
        self.model_manager: Optional[ModelManager] = None
        self.prediction_cache: Optional[PredictionCache] = None
        self.prediction_logger: Optional[PredictionLogger] = None
        
        # Predictors
        self.batch_predictor: Optional[BatchPredictor] = None
        self.streaming_predictor: Optional[StreamingPredictor] = None
        
        # Services
        self.label_reconciliation_service: Optional[LabelReconciliationService] = None
        
        logger.info("PredictorService initialized")
    
    async def initialize(self) -> None:
        """
        Initialize all components.
        
        Raises:
            ServiceError: If initialization fails
        """
        if self._initialized:
            logger.warning("Service already initialized")
            return
        
        try:
            logger.info("Initializing PredictorService")
            
            # Setup logging and tracing
            setup_logging(self.config.monitoring.log_level)
            initialize_tracing(
                service_name="predictor-online-inference-service",
                jaeger_host=self.config.monitoring.jaeger_host,
                jaeger_port=self.config.monitoring.jaeger_port,
            )
            
            # Initialize metrics collector
            self.metrics = MetricsCollector()
            
            # Initialize clients
            await self._initialize_clients()
            
            # Initialize core components
            await self._initialize_components()
            
            # Initialize predictors
            await self._initialize_predictors()
            
            # Initialize services
            await self._initialize_services()
            
            # Load default model
            await self._load_default_model()
            
            self._initialized = True
            
            logger.info("PredictorService initialization complete")
            
        except Exception as e:
            logger.error(
                "Failed to initialize PredictorService",
                extra={"error": str(e)},
                exc_info=True
            )
            raise ServiceError(
                message=f"Service initialization failed: {str(e)}",
                details={}
            ) from e
    
    async def _initialize_clients(self) -> None:
        """Initialize all clients."""
        logger.info("Initializing clients")
        
        # Create clients
        self.feast_client = FeastClient(self.config.feast)
        self.mlflow_client = MLflowModelClient(self.config.mlflow)
        self.redis_client = RedisClient(self.config.redis)
        self.postgres_client = PostgresClient(self.config.postgres)
        self.kafka_consumer = KafkaConsumerClient(self.config.kafka)
        self.kafka_producer = KafkaProducerClient(self.config.kafka)
        
        # Connect clients
        await self.feast_client.connect()
        await self.redis_client.connect()
        await self.postgres_client.connect()
        await self.kafka_producer.connect()
        
        logger.info("All clients connected")
    
    async def _initialize_components(self) -> None:
        """Initialize all components."""
        logger.info("Initializing components")
        
        # Initialize A/B testing strategy
        ab_testing_strategy = create_ab_testing_strategy(self.config.inference)
        
        # Initialize new components
        self.feature_store_adapter = FeatureStoreAdapter(
            config=self.config.feast,
            metrics=self.metrics
        )
        await self.feature_store_adapter.connect()
        
        self.model_loader = ModelLoader(
            config=self.config.mlflow,
            metrics=self.metrics
        )
        
        self.confidence_scorer = ConfidenceScorer(metrics=self.metrics)
        
        self.prediction_validator = PredictionValidator(
            metrics=self.metrics,
            consistency_threshold=self.config.validation.label_consistency_threshold
        )
        
        self.feature_quality_monitor = FeatureQualityMonitor(
            metrics=self.metrics,
            freshness_threshold_seconds=self.config.validation.feature_freshness_threshold_seconds
        )
        
        self.drift_detector = DriftDetector(
            metrics=self.metrics,
            drift_threshold=0.05
        )
        
        # Initialize existing components
        self.feature_fetcher = FeatureFetcher(self.feast_client)
        
        self.feature_validator = FeatureValidator(
            feature_freshness_threshold_seconds=self.config.validation.feature_freshness_threshold_seconds
        )
        
        self.feature_reconciliation_checker = FeatureReconciliationChecker(
            reconciliation_threshold=self.config.validation.feature_reconciliation_threshold
        )
        
        self.label_retriever = LabelRetriever(self.postgres_client)
        
        self.model_manager = ModelManager(self.mlflow_client, ab_testing_strategy)
        
        self.prediction_cache = PredictionCache(
            self.redis_client,
            ttl_seconds=self.config.inference.cache_ttl_seconds
        )
        
        self.prediction_logger = PredictionLogger(
            self.postgres_client,
            self.kafka_producer
        )
        
        logger.info("All components initialized")
    
    async def _initialize_predictors(self) -> None:
        """Initialize predictors."""
        logger.info("Initializing predictors")
        
        self.batch_predictor = BatchPredictor(
            model_manager=self.model_manager,
            feature_fetcher=self.feature_fetcher,
            feature_validator=self.feature_validator,
            prediction_cache=self.prediction_cache,
            prediction_logger=self.prediction_logger,
            batch_size=self.config.inference.batch_size,
        )
        
        self.streaming_predictor = StreamingPredictor(
            model_manager=self.model_manager,
            feature_fetcher=self.feature_fetcher,
            feature_validator=self.feature_validator,
            prediction_cache=self.prediction_cache,
            prediction_logger=self.prediction_logger,
            kafka_consumer=self.kafka_consumer,
        )
        
        logger.info("Predictors initialized")
    
    async def _initialize_services(self) -> None:
        """Initialize services."""
        logger.info("Initializing services")
        
        self.label_reconciliation_service = LabelReconciliationService(
            config=self.config,
            kafka_consumer=self.kafka_consumer,
            postgres_client=self.postgres_client,
            prediction_validator=self.prediction_validator,
            metrics=self.metrics
        )
        
        logger.info("Services initialized")
    
    async def _load_default_model(self) -> None:
        """Load default model."""
        try:
            logger.info("Loading default model")
            await self.model_loader.lazy_load_model()
            await self.model_manager.load_model()
            logger.info("Default model loaded successfully")
        except Exception as e:
            logger.error(
                "Failed to load default model",
                extra={"error": str(e)},
                exc_info=True
            )
            # Continue anyway - model will be loaded on first request
    
    async def start(self) -> None:
        """
        Start the service.
        
        Raises:
            ServiceError: If service start fails
        """
        if not self._initialized:
            await self.initialize()
        
        if self._running:
            logger.warning("Service already running")
            return
        
        try:
            logger.info("Starting PredictorService")
            
            # Start streaming predictor if enabled
            if self.config.inference.enable_streaming:
                asyncio.create_task(self.streaming_predictor.start())
                logger.info("Streaming predictor started")
            
            # Start label reconciliation service
            asyncio.create_task(self.label_reconciliation_service.start())
            logger.info("Label reconciliation service started")
            
            self._running = True
            
            logger.info("PredictorService started successfully")

        except Exception as e:
            logger.error(
                "Failed to start PredictorService",
                extra={"error": str(e)},
                exc_info=True
            )
            raise ServiceError(
                message=f"Service start failed: {str(e)}",
                details={}
            ) from e

    async def stop(self) -> None:
        """
        Stop the service.

        Raises:
            ServiceError: If service stop fails
        """
        if not self._running:
            logger.warning("Service not running")
            return

        try:
            logger.info("Stopping PredictorService")

            # Stop streaming predictor
            if self.streaming_predictor and self.streaming_predictor.is_running():
                await self.streaming_predictor.stop()
                logger.info("Streaming predictor stopped")

            # Stop label reconciliation service
            if self.label_reconciliation_service:
                await self.label_reconciliation_service.stop()
                logger.info("Label reconciliation service stopped")

            # Disconnect clients
            if self.feast_client:
                await self.feast_client.disconnect()
            if self.redis_client:
                await self.redis_client.disconnect()
            if self.postgres_client:
                await self.postgres_client.disconnect()
            if self.kafka_producer:
                await self.kafka_producer.close()
            if self.feature_store_adapter:
                await self.feature_store_adapter.close()

            logger.info("All clients disconnected")

            self._running = False

            logger.info("PredictorService stopped successfully")

        except Exception as e:
            logger.error(
                "Failed to stop PredictorService",
                extra={"error": str(e)},
                exc_info=True
            )
            raise ServiceError(
                message=f"Service stop failed: {str(e)}",
                details={}
            ) from e

    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running

    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    async def health_check(self) -> dict:
        """
        Perform health check.

        Returns:
            Health check status dictionary
        """
        try:
            health_status = {
                "service": "predictor-online-inference-service",
                "status": "healthy" if self._running else "stopped",
                "timestamp": datetime.now().isoformat(),
                "components": {}
            }

            # Check clients
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                    health_status["components"]["redis"] = "healthy"
                except Exception as e:
                    health_status["components"]["redis"] = f"unhealthy: {str(e)}"

            if self.postgres_client:
                try:
                    await self.postgres_client.execute_query("SELECT 1")
                    health_status["components"]["postgres"] = "healthy"
                except Exception as e:
                    health_status["components"]["postgres"] = f"unhealthy: {str(e)}"

            # Check model
            if self.model_manager:
                try:
                    model = self.model_manager.get_model()
                    health_status["components"]["model"] = "loaded" if model else "not_loaded"
                except Exception as e:
                    health_status["components"]["model"] = f"error: {str(e)}"

            # Check streaming predictor
            if self.streaming_predictor:
                health_status["components"]["streaming_predictor"] = (
                    "running" if self.streaming_predictor.is_running() else "stopped"
                )

            # Overall status
            unhealthy_components = [
                k for k, v in health_status["components"].items()
                if isinstance(v, str) and ("unhealthy" in v or "error" in v)
            ]

            if unhealthy_components:
                health_status["status"] = "degraded"
                health_status["unhealthy_components"] = unhealthy_components

            return health_status

        except Exception as e:
            logger.error(
                "Health check failed",
                extra={"error": str(e)},
                exc_info=True
            )
            return {
                "service": "predictor-online-inference-service",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

