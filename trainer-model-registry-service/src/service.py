"""
Main trainer service orchestration.

Coordinates all training, evaluation, and registry operations.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from src.config import config
from src.clients.postgres_client import PostgreSQLClient
from src.clients.feast_client import FeastClient
from src.clients.mlflow_client import MLflowClientWrapper
from src.clients.s3_client import S3Client
from src.clients.kafka_producer import KafkaProducerClient
from src.data.feature_retriever import FeatureRetriever
from src.data.label_retriever import LabelRetriever
from src.data.preprocessor import DataPreprocessor
from src.data.splitter import DataSplitter
from src.training.trainer import Trainer
from src.training.hyperparameter_tuner import HyperparameterTuner
from src.evaluation.evaluator import Evaluator
from src.evaluation.drift_detector import DriftDetector
from src.registry.model_promoter import ModelPromoter
from src.registry.artifact_manager import ArtifactManager
from src.exceptions import TrainerError
from src.utils.trace import initialize_tracing, shutdown_tracing, get_tracer, TracingConfig
from src.metrics import metrics

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class TrainerService:
    """Main trainer service."""

    def __init__(self):
        """Initialize trainer service."""
        self.postgres_client = None
        self.feast_client = None
        self.mlflow_client = None
        self.s3_client = None
        self.kafka_producer = None
        self.feature_retriever = None
        self.label_retriever = None
        self.preprocessor = None
        self.splitter = None
        self.trainer = None
        self.hyperparameter_tuner = None
        self.evaluator = None
        self.drift_detector = None
        self.model_promoter = None
        self.artifact_manager = None
        logger.info("Trainer service initialized")

    async def start(self) -> None:
        """
        Start the service.

        Raises:
            TrainerError: If startup fails
        """
        with tracer.start_as_current_span("start_service"):
            try:
                logger.info("Starting trainer service")
                logger.info(f"Configuration: feast={config.feast}")

                # Initialize tracing
                tracing_config = TracingConfig(
                    service_name="trainer-service",
                    jaeger_host=config.jaeger.agent_host,
                    jaeger_port=config.jaeger.agent_port,
                    enabled=config.jaeger.enabled,
                )
                initialize_tracing(tracing_config)

                # Initialize clients
                self.postgres_client = PostgreSQLClient(config.postgres)
                await self.postgres_client.connect()

                self.feast_client = FeastClient(config.feast)
                self.feast_client.connect()

                self.mlflow_client = MLflowClientWrapper(config.mlflow)
                self.mlflow_client.connect()

                self.s3_client = S3Client(config.s3)
                self.s3_client.connect()

                self.kafka_producer = KafkaProducerClient(config.kafka)
                self.kafka_producer.connect()

                # Initialize components
                self.feature_retriever = FeatureRetriever(self.feast_client)
                self.label_retriever = LabelRetriever(self.postgres_client)
                self.preprocessor = DataPreprocessor()
                self.splitter = DataSplitter(
                    test_size=config.training.test_set_size,
                    validation_size=config.training.validation_set_size,
                    random_state=config.training.random_seed,
                )
                self.trainer = Trainer()
                self.hyperparameter_tuner = HyperparameterTuner()
                self.evaluator = Evaluator()
                self.drift_detector = DriftDetector()
                self.model_promoter = ModelPromoter(self.mlflow_client)
                self.artifact_manager = ArtifactManager(
                    self.s3_client, self.mlflow_client
                )

                # Health checks
                await self.postgres_client.health_check()
                self.feast_client.health_check()
                self.mlflow_client.health_check()
                self.s3_client.health_check()
                self.kafka_producer.health_check()

                logger.info("Trainer service started successfully")

            except Exception as e:
                logger.error(f"Failed to start trainer service: {e}")
                raise TrainerError(f"Failed to start service: {e}")

    async def shutdown(self) -> None:
        """
        Shutdown the service.

        Raises:
            TrainerError: If shutdown fails
        """
        with tracer.start_as_current_span("shutdown_service"):
            try:
                logger.info("Shutting down trainer service")

                # Close clients
                if self.postgres_client:
                    await self.postgres_client.disconnect()

                if self.kafka_producer:
                    self.kafka_producer.close()

                # Shutdown tracing
                shutdown_tracing()

                logger.info("Trainer service shut down successfully")

            except Exception as e:
                logger.error(f"Failed to shutdown trainer service: {e}")
                raise TrainerError(f"Failed to shutdown service: {e}")

    async def train_pipeline(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute complete training pipeline.

        Args:
            start_date: Optional start date for data retrieval
            end_date: Optional end date for data retrieval

        Returns:
            Dictionary with pipeline results

        Raises:
            TrainerError: If pipeline fails
        """
        with tracer.start_as_current_span("train_pipeline"):
            try:
                logger.info("Starting training pipeline")

                # Set default dates if not provided (18-month window)
                if not end_date:
                    end_date = datetime.now()
                else:
                    end_date = datetime.fromisoformat(end_date)

                if not start_date:
                    start_date = end_date - timedelta(days=18*30)  # 18 months
                else:
                    start_date = datetime.fromisoformat(start_date)

                logger.info(f"Training window: {start_date} to {end_date}")

                # Retrieve labels first
                logger.info("Retrieving labels")
                y = await self.label_retriever.retrieve_labels(
                    start_date=start_date,
                    end_date=end_date,
                )
                logger.info(f"Labels retrieved: shape={y.shape}")

                if y.empty:
                    logger.error("No labels retrieved for training!")
                    raise TrainerError("No training data available")

                # Extract group IDs from labels
                # Ground truth labels already have group_id mapped by labeler service
                logger.info("Extracting group IDs from labels")
                group_ids = y['group_id'].unique().tolist()
                # Remove None values
                group_ids = [gid for gid in group_ids if gid is not None]
                logger.info(f"Found {len(group_ids)} unique groups in labels")
                logger.debug(f"Group IDs (first 5): {group_ids[:5]}")

                if not group_ids:
                    logger.warning("No groups found in labeled data")
                    raise TrainerError("No semantic groups found in labeled data")

                # Retrieve features for the mapped group IDs
                logger.info("Retrieving features")
                X = self.feature_retriever.retrieve_features(
                    entity_ids=group_ids,
                    start_date=start_date,
                    end_date=end_date,
                )
                logger.info(f"Features retrieved: shape={X.shape}")

                # Check if we have data
                if X.empty:
                    logger.error("No features retrieved for training!")
                    raise TrainerError("No training data available")

                # Extract label column from labels DataFrame
                # Use label_realized as the target variable for event realization prediction
                if 'label_realized' not in y.columns:
                    logger.error(f"Label column 'label_realized' not found. Available columns: {list(y.columns)}")
                    raise TrainerError("Label column 'label_realized' not found in ground truth data")

                # Handle null values in label_realized
                null_count = y['label_realized'].isnull().sum()
                if null_count > 0:
                    logger.warning(f"Found {null_count} null values in label_realized column")
                    # Drop rows with null labels
                    y = y.dropna(subset=['label_realized'])
                    logger.info(f"After dropping nulls: {len(y)} labels remaining")

                    if y.empty:
                        logger.error("No valid labels after removing null values")
                        raise TrainerError("No valid labels available for training")

                # Convert boolean to int (0/1)
                y_series = y['label_realized'].astype(int)
                logger.info(f"Extracted label column: {y_series.shape}")
                logger.debug(f"Label distribution before preprocessing: {y_series.value_counts().to_dict()}")

                # Preprocess data
                logger.info("Preprocessing data")
                X_before = X.shape
                X, _ = self.preprocessor.preprocess(X, y_series, fit=True)
                logger.info(f"Data after preprocessing: {X.shape} (was {X_before})")

                # Split data
                logger.info("Splitting data")
                (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
                    self.splitter.split_temporal(X, y_series)
                )
                logger.info(f"Train set: {X_train.shape}, Val set: {X_val.shape}, Test set: {X_test.shape}")
                logger.info(f"Train labels distribution: {y_train.value_counts().to_dict()}")
                logger.info(f"Val labels distribution: {y_val.value_counts().to_dict()}")
                logger.info(f"Test labels distribution: {y_test.value_counts().to_dict()}")

                # Train models
                logger.info("Training models")
                models = self.trainer.train_all_models(X_train, y_train, X_val, y_val)
                logger.info(f"Models trained: {list(models.keys())}")

                # Evaluate models
                logger.info("Evaluating models")
                eval_results = self.evaluator.compare_models(
                    {k: v[0] for k, v in models.items()},
                    X_test,
                    y_test,
                )
                logger.info(f"Evaluation results: {eval_results}")

                # Detect drift
                logger.info("Detecting drift")
                feature_drift = self.drift_detector.detect_feature_drift(
                    X_train, X_test
                )
                target_drift = self.drift_detector.detect_target_drift(y_train, y_test)
                logger.info(f"Feature drift: {feature_drift}, Target drift: {target_drift}")

                result = {
                    "timestamp": datetime.now().isoformat(),
                    "models_trained": len(models),
                    "evaluation_results": eval_results,
                    "feature_drift": feature_drift,
                    "target_drift": target_drift,
                }

                logger.info(f"Training pipeline complete: {result}")
                return result

            except Exception as e:
                logger.error(f"Training pipeline failed: {e}", exc_info=True)
                raise TrainerError(f"Training pipeline failed: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Dictionary with health status
        """
        with tracer.start_as_current_span("health_check"):
            try:
                status = {
                    "service": "trainer-service",
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "components": {},
                }

                # Check components
                if self.postgres_client:
                    try:
                        await self.postgres_client.health_check()
                        status["components"]["postgres"] = "healthy"
                    except Exception as e:
                        status["components"]["postgres"] = f"unhealthy: {e}"

                if self.feast_client:
                    try:
                        self.feast_client.health_check()
                        status["components"]["feast"] = "healthy"
                    except Exception as e:
                        status["components"]["feast"] = f"unhealthy: {e}"

                if self.mlflow_client:
                    try:
                        self.mlflow_client.health_check()
                        status["components"]["mlflow"] = "healthy"
                    except Exception as e:
                        status["components"]["mlflow"] = f"unhealthy: {e}"

                if self.s3_client:
                    try:
                        self.s3_client.health_check()
                        status["components"]["s3"] = "healthy"
                    except Exception as e:
                        status["components"]["s3"] = f"unhealthy: {e}"

                if self.kafka_producer:
                    try:
                        self.kafka_producer.health_check()
                        status["components"]["kafka"] = "healthy"
                    except Exception as e:
                        status["components"]["kafka"] = f"unhealthy: {e}"

                logger.info(f"Health check: {status}")
                return status

            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise TrainerError(f"Health check failed: {e}")
