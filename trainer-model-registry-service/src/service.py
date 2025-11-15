"""
Main trainer service orchestration.

Coordinates all training, evaluation, and registry operations.
"""

import logging
import asyncio
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
import pandas as pd

# Disable MLflow emoji output to avoid Unicode errors on Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'

import mlflow
import mlflow.sklearn
import mlflow.xgboost

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
from src.data.parquet_loader import ParquetDataLoader
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
        self.parquet_loader = None  # NEW: Parquet data loader
        self.btc_preprocessor = None  # Separate preprocessor for BTC prediction
        self.conflict_preprocessor = None  # Separate preprocessor for conflict prediction
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

                # Set AWS credentials as environment variables for boto3/MLflow
                import os
                os.environ['AWS_ACCESS_KEY_ID'] = config.s3.access_key_id
                os.environ['AWS_SECRET_ACCESS_KEY'] = config.s3.secret_access_key
                os.environ['AWS_DEFAULT_REGION'] = config.s3.region
                if config.s3.endpoint_url:
                    os.environ['MLFLOW_S3_ENDPOINT_URL'] = config.s3.endpoint_url
                logger.info("AWS credentials set for boto3/MLflow")

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

                # Initialize Feast SDK client with repo_path (use feature-engineering-service directory)
                # This ensures we use the same registry as feature-engineering-service
                self.feast_client = FeastClient(config.feast, repo_path="../feature-engineering-service")
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

                # NEW: Initialize parquet data loader (root is one level up from service directory)
                self.parquet_loader = ParquetDataLoader(root_path="..")
                logger.info("Initialized parquet data loader")

                # Separate preprocessors for BTC and conflict models
                # BTC uses technical indicators from btc_features.parquet
                # Conflict uses semantic features from semantic_groups.parquet
                self.btc_preprocessor = DataPreprocessor(scaling_method="standard")
                self.conflict_preprocessor = DataPreprocessor(scaling_method="standard")
                logger.info("Initialized separate preprocessors for BTC and conflict models")

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

                # Upload baseline models if not already in MLflow/S3
                await self._upload_baseline_models_if_needed()

                logger.info("Trainer service started successfully")

            except Exception as e:
                logger.error(f"Failed to start trainer service: {e}")
                raise TrainerError(f"Failed to start service: {e}")

    async def _upload_baseline_models_if_needed(self) -> None:
        """
        Upload baseline models from local filesystem to MLflow and S3 if they don't exist yet.

        This ensures predictor service can access models even before first training.
        """
        try:
            import pickle
            from pathlib import Path
            import mlflow
            import mlflow.sklearn
            from mlflow.exceptions import MlflowException

            logger.info("Checking for baseline models to upload...")

            # First, verify MLflow is accessible
            try:
                # Test MLflow connectivity with a simple operation
                mlflow.get_tracking_uri()
                # Try to list experiments to verify server is responding
                self.mlflow_client.client.search_experiments(max_results=1)
                logger.info("MLflow server is accessible")
            except Exception as mlflow_error:
                logger.warning(
                    f"MLflow server not accessible, skipping baseline model upload: {mlflow_error}"
                )
                return

            # Get the models directory
            service_dir = Path(__file__).parent.parent
            models_dir = service_dir / "models"

            if not models_dir.exists():
                logger.info("No baseline models directory found - skipping baseline upload")
                return

            # Check each pipeline directory
            for pipeline_dir in models_dir.iterdir():
                if not pipeline_dir.is_dir():
                    continue

                pipeline_name = pipeline_dir.name
                logger.info(f"Checking baseline models for pipeline: {pipeline_name}")

                # Find all model files in this pipeline
                model_files = list(pipeline_dir.glob("*.pkl"))
                if not model_files:
                    logger.info(f"No baseline models found in {pipeline_name}")
                    continue

                # Upload each model
                for model_file in model_files:
                    try:
                        model_name = model_file.stem  # e.g., "xgboost_regressor"
                        full_model_name = f"{pipeline_name}_{model_name}_base"  # Add _base suffix

                        # Check if model already exists in MLflow
                        try:
                            versions = self.mlflow_client.client.search_model_versions(f"name='{full_model_name}'")
                            if versions:
                                logger.info(f"Model {full_model_name} already exists in MLflow - skipping")
                                continue
                        except Exception:
                            # Model doesn't exist, proceed with upload
                            pass

                        logger.info(f"Uploading baseline model: {full_model_name}")

                        # Load the model
                        with open(model_file, 'rb') as f:
                            model = pickle.load(f)

                        # Create a temporary MLflow run to log the model
                        with mlflow.start_run(run_name=f"baseline_{full_model_name}"):
                            # Log the model using 'name' parameter (artifact_path is deprecated in MLflow 3.5+)
                            import warnings
                            from mlflow.exceptions import MlflowException

                            with warnings.catch_warnings():
                                warnings.filterwarnings("ignore", message=".*artifact_path.*deprecated.*")
                                try:
                                    mlflow.sklearn.log_model(model, "model", registered_model_name=full_model_name)
                                except MlflowException as e:
                                    # Suppress 404 errors from /logged-models endpoint (version compatibility issue)
                                    if "404" not in str(e) or "logged-models" not in str(e).lower():
                                        raise

                            # Log metadata
                            mlflow.log_param("source", "baseline")
                            mlflow.log_param("pipeline", pipeline_name)
                            mlflow.log_param("model_type", model_name)

                            # Get run ID
                            run_id = mlflow.active_run().info.run_id
                            logger.info(f"Baseline model logged: {full_model_name} (run: {run_id})")

                            # Promote to Production stage
                            try:
                                # Get the latest version that was just registered
                                versions = self.mlflow_client.client.search_model_versions(f"name='{full_model_name}'")
                                if versions:
                                    latest_version = max(versions, key=lambda v: int(v.version))
                                    self.mlflow_client.client.transition_model_version_stage(
                                        name=full_model_name,
                                        version=latest_version.version,
                                        stage="Production",
                                    )
                                    logger.info(f"Baseline model promoted to Production: {full_model_name} v{latest_version.version}")
                            except Exception as stage_error:
                                logger.info(f"Baseline model {full_model_name} registered (stage transition skipped)")

                    except Exception as model_error:
                        logger.warning(
                            f"Failed to upload baseline model {model_file.name}: {model_error}",
                            exc_info=True
                        )
                        # Continue with next model
                        continue

            logger.info("Baseline model upload check complete")

        except Exception as e:
            logger.warning(f"Failed to upload baseline models: {e}", exc_info=True)
            # Don't fail startup if baseline upload fails

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

        Trains TWO separate model pipelines:
        1. BTC price prediction (regression) - predicts BTC percent change for next 10 hours
        2. Conflict prediction (classification) - predicts conflict between countries

        Args:
            start_date: Optional start date for data retrieval
            end_date: Optional end date for data retrieval

        Returns:
            Dictionary with pipeline results for both pipelines

        Raises:
            TrainerError: If pipeline fails
        """
        with tracer.start_as_current_span("train_pipeline"):
            try:
                logger.info("=" * 100)
                logger.info("STARTING COMPLETE TRAINING PIPELINE - TWO SEPARATE MODELS")
                logger.info("=" * 100)
                logger.info("Pipeline 1: BTC Price Prediction (Regression)")
                logger.info("Pipeline 2: Conflict Prediction (Classification)")
                logger.info("=" * 100)

                results = {}

                # Execute BTC prediction pipeline
                try:
                    logger.info("\n\n>>> EXECUTING BTC PREDICTION PIPELINE <<<\n")
                    btc_results = await self.train_btc_prediction_pipeline(start_date, end_date)
                    results['btc_prediction'] = btc_results
                    logger.info(f"BTC pipeline completed successfully: Best R²={btc_results.get('best_r2', 'N/A')}")
                except Exception as e:
                    logger.error(f"BTC prediction pipeline failed: {e}", exc_info=True)
                    results['btc_prediction'] = {"status": "failed", "error": str(e)}

                # Execute conflict prediction pipeline
                try:
                    logger.info("\n\n>>> EXECUTING CONFLICT PREDICTION PIPELINE <<<\n")
                    conflict_results = await self.train_conflict_prediction_pipeline(start_date, end_date)
                    results['conflict_prediction'] = conflict_results
                    logger.info(f"Conflict pipeline completed successfully: Best AUC={conflict_results.get('best_auc', 'N/A')}")
                except Exception as e:
                    logger.error(f"Conflict prediction pipeline failed: {e}", exc_info=True)
                    results['conflict_prediction'] = {"status": "failed", "error": str(e)}

                logger.info("=" * 100)
                logger.info("COMPLETE TRAINING PIPELINE FINISHED")
                logger.info("=" * 100)
                logger.info(f"BTC Prediction: {results.get('btc_prediction', {}).get('status', 'completed')}")
                logger.info(f"Conflict Prediction: {results.get('conflict_prediction', {}).get('status', 'completed')}")
                logger.info("=" * 100)

                return results

            except Exception as e:
                logger.error(f"Training pipeline failed: {e}", exc_info=True)
                raise TrainerError(f"Training pipeline failed: {e}")

    async def train_btc_prediction_pipeline(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute BTC price prediction training pipeline (REGRESSION).

        Trains regression models to predict BTC price change percentage for next 10 hours.
        Uses technical indicators from btc_features.parquet as features.

        Args:
            start_date: Optional start date for data retrieval
            end_date: Optional end date for data retrieval

        Returns:
            Dictionary with pipeline results

        Raises:
            TrainerError: If pipeline fails
        """
        with tracer.start_as_current_span("train_btc_prediction_pipeline"):
            try:
                logger.info("=" * 80)
                logger.info("STARTING BTC PRICE PREDICTION PIPELINE (REGRESSION)")
                logger.info("=" * 80)

                # Load BTC training data from parquet
                logger.info("Loading BTC training data from parquet file")
                X_btc_final, y_btc = self.parquet_loader.prepare_btc_training_data()

                if X_btc_final.empty or len(y_btc) == 0:
                    logger.warning("No BTC training data loaded")
                    raise TrainerError("No BTC training data loaded")

                logger.info(f"BTC training data: X shape={X_btc_final.shape}, y shape={y_btc.shape}")
                logger.info(f"BTC features: {list(X_btc_final.columns)}")
                logger.info(f"BTC target distribution: min={y_btc.min():.4f}, max={y_btc.max():.4f}, mean={y_btc.mean():.4f}, std={y_btc.std():.4f}")

                # Validate minimum dataset size
                min_samples_required = 50
                if len(y_btc) < min_samples_required:
                    logger.error(f"Insufficient BTC training data: {len(y_btc)} samples (minimum {min_samples_required} required)")
                    raise TrainerError(f"Insufficient BTC training data: {len(y_btc)} samples")

                # FIXED: Split data FIRST (before preprocessing) to prevent data leakage
                logger.info("Splitting BTC data (BEFORE preprocessing)")
                from sklearn.model_selection import train_test_split
                X_train, X_temp, y_train, y_temp = train_test_split(
                    X_btc_final, y_btc, test_size=0.3, random_state=config.training.random_seed
                )
                X_val, X_test, y_val, y_test = train_test_split(
                    X_temp, y_temp, test_size=0.67, random_state=config.training.random_seed
                )
                logger.info(f"BTC Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

                # FIXED: Preprocess training data and FIT preprocessor on training data ONLY
                logger.info("Preprocessing BTC TRAINING data (fitting preprocessor)")
                X_train, _ = self.btc_preprocessor.preprocess(X_train, y_train, fit=True)
                logger.info(f"BTC training data after preprocessing: {X_train.shape}")
                logger.info(f"BTC preprocessor feature names: {self.btc_preprocessor.get_feature_names()}")
                logger.info(f"BTC preprocessor constant features removed: {self.btc_preprocessor.get_constant_features()}")

                # FIXED: Transform validation and test sets using fitted preprocessor (fit=False)
                logger.info("Preprocessing BTC VALIDATION data (transforming only)")
                X_val, _ = self.btc_preprocessor.preprocess(X_val, y_val, fit=False)
                logger.info(f"BTC validation data after preprocessing: {X_val.shape}")

                logger.info("Preprocessing BTC TEST data (transforming only)")
                X_test, _ = self.btc_preprocessor.preprocess(X_test, y_test, fit=False)
                logger.info(f"BTC test data after preprocessing: {X_test.shape}")

                # Train BTC regression models
                logger.info("Training BTC regression models")
                from src.models.xgboost_regressor_model import XGBoostRegressorModel
                from src.models.random_forest_regressor_model import RandomForestRegressorModel
                from src.models.gradient_boosting_regressor_model import GradientBoostingRegressorModel

                btc_models = {}

                # XGBoost Regressor
                logger.info("Training XGBoost Regressor for BTC")
                xgb_reg = XGBoostRegressorModel()
                xgb_metrics = xgb_reg.train(X_train, y_train, X_val, y_val)
                btc_models['xgboost_regressor'] = (xgb_reg, xgb_metrics)

                # Random Forest Regressor
                logger.info("Training Random Forest Regressor for BTC")
                rf_reg = RandomForestRegressorModel()
                rf_metrics = rf_reg.train(X_train, y_train, X_val, y_val)
                btc_models['random_forest_regressor'] = (rf_reg, rf_metrics)

                # Gradient Boosting Regressor
                logger.info("Training Gradient Boosting Regressor for BTC")
                gb_reg = GradientBoostingRegressorModel()
                gb_metrics = gb_reg.train(X_train, y_train, X_val, y_val)
                btc_models['gradient_boosting_regressor'] = (gb_reg, gb_metrics)

                logger.info(f"BTC models trained: {list(btc_models.keys())}")

                # Evaluate BTC models
                logger.info("Evaluating BTC regression models")
                btc_eval_results = self.evaluator.compare_models(
                    {k: v[0] for k, v in btc_models.items()},
                    X_test,
                    y_test,
                    task_type="regression",
                )
                logger.info(f"BTC evaluation results: {btc_eval_results}")

                # Find best BTC model
                best_btc_model_type, best_btc_metrics = self.evaluator.get_best_model(task_type="regression")
                logger.info(f"Best BTC model: {best_btc_model_type} with R²={best_btc_metrics.get('r2', 'N/A')}")

                # Save BTC models and BTC preprocessor to local, S3, and MLflow
                logger.info("Saving BTC models and BTC preprocessor to local/S3/MLflow")
                await self._save_models_and_preprocessor(
                    models=btc_models,
                    preprocessor=self.btc_preprocessor,
                    pipeline_name="btc_prediction",
                    best_model_type=best_btc_model_type,
                    evaluation_results=btc_eval_results
                )

                logger.info("=" * 80)
                logger.info("BTC PRICE PREDICTION PIPELINE COMPLETE")
                logger.info("=" * 80)

                return {
                    "pipeline": "btc_prediction",
                    "task_type": "regression",
                    "models": list(btc_models.keys()),
                    "best_model": best_btc_model_type,
                    "best_r2": best_btc_metrics.get('r2'),
                    "best_rmse": best_btc_metrics.get('rmse'),
                    "evaluation_results": btc_eval_results,
                    "num_samples": len(y_btc),
                    "num_features": X_train.shape[1],  # Fixed: use X_train instead of X_btc_processed
                }

            except Exception as e:
                logger.error(f"BTC prediction pipeline failed: {e}", exc_info=True)
                raise TrainerError(f"BTC prediction pipeline failed: {e}")

    async def train_conflict_prediction_pipeline(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute conflict prediction training pipeline (CLASSIFICATION).

        Trains classification models to predict conflict probability.
        Uses semantic features from semantic_groups.parquet.

        Conflict labels are created based on:
        - Multiple countries mentioned (>= 2)
        - Negative sentiment (sentiment_mean < -0.1)
        - High entity prominence

        Args:
            start_date: Optional start date for data retrieval (not used with parquet)
            end_date: Optional end date for data retrieval (not used with parquet)

        Returns:
            Dictionary with pipeline results

        Raises:
            TrainerError: If pipeline fails
        """
        with tracer.start_as_current_span("train_conflict_prediction_pipeline"):
            try:
                logger.info("=" * 80)
                logger.info("STARTING CONFLICT PREDICTION PIPELINE (CLASSIFICATION)")
                logger.info("=" * 80)

                # Load conflict training data from parquet
                logger.info("Loading conflict training data from parquet file")
                X_conflict_final, y_conflict = self.parquet_loader.prepare_conflict_training_data()

                if X_conflict_final.empty or len(y_conflict) == 0:
                    logger.warning("No conflict training data loaded")
                    raise TrainerError("No conflict training data loaded")

                logger.info(f"Conflict training data: X shape={X_conflict_final.shape}, y shape={y_conflict.shape}")
                logger.info(f"Conflict features: {list(X_conflict_final.columns)}")
                logger.info(f"Label distribution: {y_conflict.value_counts().to_dict()}")
                logger.info(f"Conflict rate: {y_conflict.mean():.2%}")

                # Validate minimum dataset size
                min_samples_required = 50
                if len(y_conflict) < min_samples_required:
                    logger.error(f"Insufficient conflict training data: {len(y_conflict)} samples (minimum {min_samples_required} required)")
                    raise TrainerError(f"Insufficient conflict training data: {len(y_conflict)} samples")

                # Validate minimum samples per class
                class_counts = y_conflict.value_counts().to_dict()
                if len(class_counts) < 2:
                    logger.error(f"Only one class present in training data: {class_counts}")
                    raise TrainerError("Need at least 2 classes for classification")

                min_class_samples = min(class_counts.values())
                min_class_required = 10
                if min_class_samples < min_class_required:
                    logger.warning(f"Low sample count for minority class: {min_class_samples} samples")

                # FIXED: Split data FIRST (before preprocessing) to prevent data leakage
                logger.info("Splitting conflict data with stratification (BEFORE preprocessing)")
                (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
                    self.splitter.split_stratified(X_conflict_final, y_conflict)
                )
                logger.info(f"Conflict Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")
                logger.info(f"Train labels: {y_train.value_counts().to_dict()}")
                logger.info(f"Val labels: {y_val.value_counts().to_dict()}")
                logger.info(f"Test labels: {y_test.value_counts().to_dict()}")

                # FIXED: Preprocess training data and FIT preprocessor on training data ONLY
                logger.info("Preprocessing conflict TRAINING data (fitting preprocessor)")
                X_train, _ = self.conflict_preprocessor.preprocess(X_train, y_train, fit=True)
                logger.info(f"Conflict training data after preprocessing: {X_train.shape}")
                logger.info(f"Conflict preprocessor feature names: {self.conflict_preprocessor.get_feature_names()}")
                logger.info(f"Conflict preprocessor constant features removed: {self.conflict_preprocessor.get_constant_features()}")

                # FIXED: Transform validation and test sets using fitted preprocessor (fit=False)
                logger.info("Preprocessing conflict VALIDATION data (transforming only)")
                X_val, _ = self.conflict_preprocessor.preprocess(X_val, y_val, fit=False)
                logger.info(f"Conflict validation data after preprocessing: {X_val.shape}")

                logger.info("Preprocessing conflict TEST data (transforming only)")
                X_test, _ = self.conflict_preprocessor.preprocess(X_test, y_test, fit=False)
                logger.info(f"Conflict test data after preprocessing: {X_test.shape}")

                # Train conflict classification models
                logger.info("Training conflict classification models")
                conflict_models = self.trainer.train_all_models(X_train, y_train, X_val, y_val)
                logger.info(f"Conflict models trained: {list(conflict_models.keys())}")

                # Evaluate conflict models
                logger.info("Evaluating conflict classification models")
                conflict_eval_results = self.evaluator.compare_models(
                    {k: v[0] for k, v in conflict_models.items()},
                    X_test,
                    y_test,
                    task_type="classification",
                )
                logger.info(f"Conflict evaluation results: {conflict_eval_results}")

                # Find best conflict model
                best_conflict_model_type, best_conflict_metrics = self.evaluator.get_best_model(task_type="classification")
                logger.info(f"Best conflict model: {best_conflict_model_type} with AUC={best_conflict_metrics.get('auc', 'N/A')}")

                # Save conflict models and conflict preprocessor to local, S3, and MLflow
                logger.info("Saving conflict models and conflict preprocessor to local/S3/MLflow")
                await self._save_models_and_preprocessor(
                    models=conflict_models,
                    preprocessor=self.conflict_preprocessor,
                    pipeline_name="conflict_prediction",
                    best_model_type=best_conflict_model_type,
                    evaluation_results=conflict_eval_results
                )

                logger.info("=" * 80)
                logger.info("CONFLICT PREDICTION PIPELINE COMPLETE")
                logger.info("=" * 80)

                return {
                    "pipeline": "conflict_prediction",
                    "task_type": "classification",
                    "models": list(conflict_models.keys()),
                    "best_model": best_conflict_model_type,
                    "best_auc": best_conflict_metrics.get('auc'),
                    "best_f1": best_conflict_metrics.get('f1'),
                    "evaluation_results": conflict_eval_results,
                    "num_samples": len(y_conflict),
                    "num_features": X_train.shape[1],  # Fixed: use X_train instead of X_conflict_processed
                }

            except Exception as e:
                logger.error(f"Conflict prediction pipeline failed: {e}", exc_info=True)
                raise TrainerError(f"Conflict prediction pipeline failed: {e}")

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

    async def _fetch_btc_records_with_future_data(
        self,
        hours_ahead: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[dict]:
        """
        Fetch BTC records that have future price data available.

        Args:
            hours_ahead: Hours to look ahead for future price
            start_date: Optional start date filter
            end_date: Optional end date filter (will be adjusted to exclude records without future data)

        Returns:
            List of BTC records with timestamp and close price
        """
        try:
            from datetime import timedelta

            # Adjust end_date to exclude records without future data
            # If end_date is None, use current time minus hours_ahead
            if end_date is None:
                end_date = datetime.utcnow() - timedelta(hours=hours_ahead)
            else:
                # Make sure we don't include records that don't have future data yet
                max_end = datetime.utcnow() - timedelta(hours=hours_ahead)
                if end_date > max_end:
                    end_date = max_end

            query = """
                SELECT timestamp, close
                FROM btc_truth
                WHERE timestamp <= $1
                AND event_id LIKE 'binance_BTCUSDT_%'
            """
            params = [end_date]

            if start_date:
                query += " AND timestamp >= $2"
                params.append(start_date)

            query += " ORDER BY timestamp DESC LIMIT 500"

            rows = await self.postgres_client.fetch_all(query, *params)

            logger.info(f"Fetched {len(rows)} BTC records with future data available")

            return [{"timestamp": row["timestamp"], "close": float(row["close"])} for row in rows]

        except Exception as e:
            logger.error(f"Failed to fetch BTC records: {e}", exc_info=True)
            return []

    async def _build_btc_training_data(
        self,
        btc_records: List[dict]
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Build training dataset from BTC records with Feast features.

        For each BTC timestamp T:
        1. Find nearest semantic group by timestamp
        2. Retrieve ALL 28 features from Feast (24 base + 4 BTC)
        3. Calculate forward price change from T to T+10h (target)

        Note: BTC features (btc_change_pct_10h, btc_volatility_score, btc_volume, btc_label_spike)
        are computed by feature-engineering-service and stored in Feast, so we retrieve them
        from Feast instead of querying btc_truth table directly.

        Args:
            btc_records: List of BTC records with timestamp and close price

        Returns:
            Tuple of (features DataFrame with 28 features, targets Series)
        """
        try:
            from datetime import timedelta

            X_list = []
            y_list = []
            skipped_no_future = 0
            skipped_no_group = 0
            skipped_no_feast_features = 0

            logger.info(f"Processing {len(btc_records)} BTC records with Feast features...")

            for i, record in enumerate(btc_records):
                timestamp_t = record["timestamp"]
                price_t = record["close"]

                # Calculate future timestamp for target
                timestamp_future = timestamp_t + timedelta(hours=10)

                # Step 1: Find nearest semantic group by timestamp (within ±2 hours)
                query_group = """
                    SELECT group_id, created_at
                    FROM semantic_groups
                    WHERE created_at >= $1 AND created_at <= $2
                    ORDER BY ABS(EXTRACT(EPOCH FROM (created_at - $3)))
                    LIMIT 1
                """

                start_window = timestamp_t - timedelta(hours=2)
                end_window = timestamp_t + timedelta(hours=2)

                row_group = await self.postgres_client.fetch_one(
                    query_group,
                    start_window,
                    end_window,
                    timestamp_t
                )

                if not row_group:
                    skipped_no_group += 1
                    continue

                group_id = row_group["group_id"]
                group_timestamp = row_group["created_at"]

                # Step 2: Retrieve ALL 28 features from Feast (24 base + 4 BTC)
                # BTC features are computed by feature-engineering-service and stored in Feast
                try:
                    # Get BTC feature list (28 features)
                    btc_feature_list = self.feature_retriever._get_btc_features()

                    feast_features_df = self.feature_retriever.retrieve_features(
                        entity_ids=[group_id],
                        start_date=group_timestamp - timedelta(hours=1),
                        end_date=group_timestamp + timedelta(hours=1),
                        features=btc_feature_list  # Explicitly request 28 features
                    )

                    if feast_features_df.empty:
                        skipped_no_feast_features += 1
                        continue

                    # Extract first row (should only be one row per group_id)
                    feast_features = feast_features_df.iloc[0].to_dict()

                    # Remove group_id and timestamp columns if present
                    feast_features = {k: v for k, v in feast_features.items()
                                    if k not in ['group_id', 'timestamp', 'event_timestamp']}

                except Exception as e:
                    logger.warning(f"Failed to retrieve Feast features for group {group_id}: {e}")
                    skipped_no_feast_features += 1
                    continue

                # Step 3: Get future BTC price for target calculation
                query_future = """
                    SELECT close
                    FROM btc_truth
                    WHERE timestamp >= $1 AND timestamp <= $2
                    AND event_id LIKE 'binance_BTCUSDT_%'
                    ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - $3)))
                    LIMIT 1
                """

                start_future = timestamp_future - timedelta(hours=1)
                end_future = timestamp_future + timedelta(hours=1)

                row_future = await self.postgres_client.fetch_one(
                    query_future,
                    start_future,
                    end_future,
                    timestamp_future
                )

                if not row_future:
                    skipped_no_future += 1
                    continue

                price_future = float(row_future["close"])

                # Calculate target: forward price change from T to T+10h
                target = ((price_future - price_t) / price_t) * 100.0

                # Use all 28 features from Feast (no local BTC feature extraction)
                X_list.append(feast_features)
                y_list.append(target)

                if (i + 1) % 500 == 0:
                    logger.info(f"Processed {i + 1}/{len(btc_records)} BTC records...")

            logger.info(f"Built training data: {len(X_list)} samples")
            logger.info(f"Skipped {skipped_no_group} records without nearby semantic group")
            logger.info(f"Skipped {skipped_no_feast_features} records without Feast features")
            logger.info(f"Skipped {skipped_no_future} records without future price")

            if not X_list:
                return pd.DataFrame(), pd.Series(dtype=float)

            X = pd.DataFrame(X_list)
            y = pd.Series(y_list, dtype=float)

            logger.info(f"BTC training data shape: X={X.shape}, y={y.shape}")
            logger.info(f"BTC features ({len(X.columns)} total): {list(X.columns)}")
            logger.info(f"Target distribution: min={y.min():.2f}%, max={y.max():.2f}%, mean={y.mean():.2f}%, std={y.std():.2f}%")

            return X, y

        except Exception as e:
            logger.error(f"Failed to build BTC training data: {e}", exc_info=True)
            return pd.DataFrame(), pd.Series(dtype=float)

    async def _build_country_pair_training_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Build training dataset for country-pair conflict prediction.

        For each semantic group with countries and labels:
        1. Retrieve 24 base features from Feast
        2. Get countries from reconciliation_log
        3. Generate all country pairs from the countries list
        4. Create training samples: (group_id, country1, country2, 24 features) -> conflict_label
        5. Label = 1 if label_realized=1 (conflict occurred), 0 otherwise

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval

        Returns:
            Tuple of (features DataFrame with 24 features + country pair, targets Series)
        """
        try:
            from itertools import combinations

            X_list = []
            y_list = []
            skipped_no_countries = 0
            skipped_single_country = 0
            skipped_no_features = 0
            skipped_no_label = 0

            logger.info(f"Building country-pair conflict training data from {start_date} to {end_date}...")

            # Step 1: Query ground_truth for labels with group_id
            query_labels = """
                SELECT
                    group_id,
                    label_realized,
                    label_confidence,
                    created_at
                FROM ground_truth
                WHERE created_at >= $1 AND created_at <= $2
                AND group_id IS NOT NULL
                ORDER BY created_at DESC
            """

            label_rows = await self.postgres_client.fetch_all(
                query_labels,
                start_date,
                end_date
            )

            if not label_rows:
                logger.warning("No labels found for country-pair conflict training")
                return pd.DataFrame(), pd.Series(dtype=int)

            logger.info(f"Found {len(label_rows)} labels with group_id")

            # Step 2: For each label, get countries from reconciliation_log
            for label_row in label_rows:
                group_id = label_row["group_id"]
                label_realized = label_row["label_realized"]
                label_created_at = label_row["created_at"]

                if label_realized is None:
                    skipped_no_label += 1
                    continue

                # Query reconciliation_log for countries
                query_countries = """
                    SELECT countries
                    FROM reconciliation_log
                    WHERE group_id = $1
                    AND countries IS NOT NULL
                    AND array_length(countries, 1) >= 2
                    ORDER BY created_at DESC
                    LIMIT 1
                """

                country_row = await self.postgres_client.fetch_one(
                    query_countries,
                    group_id
                )

                if not country_row or not country_row["countries"]:
                    skipped_no_countries += 1
                    continue

                countries = country_row["countries"]

                if len(countries) < 2:
                    skipped_single_country += 1
                    continue

                # Step 3: Retrieve 24 base features from Feast for this group
                # Explicitly request only base features (no BTC features for conflict model)
                try:
                    # Get base feature list (24 features, no BTC)
                    base_feature_list = self.feature_retriever._get_default_features()

                    feast_features_df = self.feature_retriever.retrieve_features(
                        entity_ids=[group_id],
                        start_date=label_created_at - timedelta(hours=1),
                        end_date=label_created_at + timedelta(hours=1),
                        features=base_feature_list  # Explicitly request only 24 base features
                    )

                    if feast_features_df.empty:
                        skipped_no_features += 1
                        continue

                    # Extract first row
                    feast_features = feast_features_df.iloc[0].to_dict()

                    # Remove group_id and timestamp columns
                    feast_features = {k: v for k, v in feast_features.items()
                                    if k not in ['group_id', 'timestamp', 'event_timestamp']}

                except Exception as e:
                    logger.warning(f"Failed to retrieve Feast features for group {group_id}: {e}")
                    skipped_no_features += 1
                    continue

                # Step 4: Generate all country pairs
                country_pairs = list(combinations(sorted(countries), 2))

                # Step 5: Create training samples for each country pair
                for country1, country2 in country_pairs:
                    # Combine features with country pair
                    sample_features = {
                        **feast_features,
                        'country1': country1,
                        'country2': country2,
                    }

                    X_list.append(sample_features)
                    y_list.append(int(label_realized))

            logger.info(f"Built country-pair training data: {len(X_list)} samples")
            logger.info(f"Skipped {skipped_no_countries} groups without countries")
            logger.info(f"Skipped {skipped_single_country} groups with single country")
            logger.info(f"Skipped {skipped_no_features} groups without Feast features")
            logger.info(f"Skipped {skipped_no_label} groups without label")

            if not X_list:
                return pd.DataFrame(), pd.Series(dtype=int)

            X = pd.DataFrame(X_list)
            y = pd.Series(y_list, dtype=int)

            logger.info(f"Country-pair training data shape: X={X.shape}, y={y.shape}")
            logger.info(f"Features ({len(X.columns)} total): {list(X.columns)}")
            logger.info(f"Label distribution: {y.value_counts().to_dict()}")

            return X, y

        except Exception as e:
            logger.error(f"Failed to build country-pair training data: {e}", exc_info=True)
            return pd.DataFrame(), pd.Series(dtype=int)

    async def _save_models_and_preprocessor(
        self,
        models: Dict[str, Tuple[Any, Dict[str, Any]]],
        preprocessor: Any,
        pipeline_name: str,
        best_model_type: str,
        evaluation_results: Dict[str, Any]
    ) -> None:
        """
        Save trained models and preprocessor to:
        1. Local models/ directory (baseline models for cold start)
        2. S3 (artifact storage)
        3. MLflow (model registry with versioning)

        Args:
            models: Dictionary of {model_type: (model_instance, metrics)}
            preprocessor: Fitted preprocessor instance
            pipeline_name: Name of pipeline (e.g., 'btc_prediction', 'conflict_prediction')
            best_model_type: Type of best performing model
            evaluation_results: Evaluation metrics for all models
        """
        import pickle
        import tempfile
        from pathlib import Path

        try:
            # Note: Local model saving is disabled - models are saved to S3 and MLflow only
            # Baseline models in trainer-model-registry-service/models/ are uploaded on startup

            logger.info(f"Saving {len(models)} models for {pipeline_name} pipeline to S3 and MLflow")

            # Create temporary directory for model files before upload
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Save preprocessor to temp file
                preprocessor_local_path = temp_path / "preprocessor.pkl"
                with open(preprocessor_local_path, "wb") as f:
                    pickle.dump(preprocessor, f)
                logger.info(f"Preprocessor saved to temp: {preprocessor_local_path}")

                # Upload preprocessor to S3 (non-blocking - log warning if fails)
                preprocessor_s3_key = f"models/{pipeline_name}/preprocessor.pkl"
                try:
                    self.s3_client.upload_file(str(preprocessor_local_path), preprocessor_s3_key)
                    logger.info(f"Preprocessor uploaded to S3: {preprocessor_s3_key}")
                except Exception as s3_error:
                    logger.warning(f"Failed to upload preprocessor to S3 (non-critical): {s3_error}")
                    logger.info("Continuing with MLflow model registration...")

                # Save each model
                for model_type, (model_instance, metrics) in models.items():
                    try:
                        # Save model to temp file
                        model_local_path = temp_path / f"{model_type}.pkl"
                        with open(model_local_path, "wb") as f:
                            pickle.dump(model_instance.model, f)
                        logger.info(f"Model saved to temp: {model_local_path}")

                        # Upload model to S3 (non-blocking - log warning if fails)
                        model_s3_key = f"models/{pipeline_name}/{model_type}/model.pkl"
                        try:
                            self.s3_client.upload_file(str(model_local_path), model_s3_key)
                            logger.info(f"Model uploaded to S3: {model_s3_key}")
                        except Exception as s3_error:
                            logger.warning(f"Failed to upload {model_type} to S3 (non-critical): {s3_error}")
                            logger.info("Continuing with MLflow model registration...")

                        # Log model to MLflow (suppress Unicode errors on Windows)
                        import sys
                        import io

                        # Temporarily redirect stdout to suppress MLflow emoji output
                        old_stdout = sys.stdout
                        sys.stdout = io.StringIO()

                        try:
                            import warnings
                            from mlflow.exceptions import MlflowException

                            with warnings.catch_warnings():
                                warnings.filterwarnings("ignore", message=".*artifact_path.*deprecated.*")

                                with mlflow.start_run(run_name=f"{pipeline_name}_{model_type}"):
                                    # Log parameters
                                    mlflow.log_param("pipeline", pipeline_name)
                                    mlflow.log_param("model_type", model_type)
                                    mlflow.log_param("is_best_model", model_type == best_model_type)
                                    mlflow.log_param("scaling_method", preprocessor.scaling_method)

                                    # Log metrics
                                    for metric_name, metric_value in metrics.items():
                                        if isinstance(metric_value, (int, float)):
                                            mlflow.log_metric(metric_name, metric_value)

                                    # Log evaluation results for this model
                                    if model_type in evaluation_results:
                                        for metric_name, metric_value in evaluation_results[model_type].items():
                                            if isinstance(metric_value, (int, float)):
                                                mlflow.log_metric(f"eval_{metric_name}", metric_value)

                                    # Log model using appropriate flavor WITHOUT registered_model_name (for old MLflow server)
                                    model_name = f"{pipeline_name}_{model_type}"

                                    # Use a workaround for old MLflow servers that don't support /logged-models endpoint
                                    # Save model to temp directory using save_model() then log as artifact
                                    import tempfile
                                    import shutil

                                    with tempfile.TemporaryDirectory() as temp_dir:
                                        model_dir = Path(temp_dir) / "model"
                                        model_dir.mkdir(parents=True, exist_ok=True)

                                        # Save model using appropriate MLflow save method (not log_model)
                                        if "xgboost" in model_type.lower():
                                            mlflow.xgboost.save_model(model_instance.model, str(model_dir))
                                        else:
                                            mlflow.sklearn.save_model(model_instance.model, str(model_dir))

                                        # Log the model directory as artifact
                                        mlflow.log_artifacts(str(model_dir), "model")
                                        logger.info(f"Model artifacts logged to MLflow")

                                    # Log preprocessor as sklearn model
                                    preprocessor_name = f"{pipeline_name}_preprocessor"
                                    with tempfile.TemporaryDirectory() as temp_dir:
                                        preprocessor_dir = Path(temp_dir) / "preprocessor"
                                        preprocessor_dir.mkdir(parents=True, exist_ok=True)

                                        # Save preprocessor using MLflow save method (not log_model)
                                        mlflow.sklearn.save_model(preprocessor, str(preprocessor_dir))

                                        # Log the preprocessor directory as artifact
                                        mlflow.log_artifacts(str(preprocessor_dir), "preprocessor")
                                        logger.info(f"Preprocessor artifacts logged to MLflow")

                                    # Log preprocessing metadata
                                    preprocessing_metadata = {
                                        "feature_names": preprocessor.get_feature_names() or [],
                                        "constant_features_removed": preprocessor.get_constant_features() or [],
                                        "n_features": len(preprocessor.get_feature_names() or []),
                                        "scaling_method": preprocessor.scaling_method,
                                    }
                                    mlflow.log_dict(preprocessing_metadata, "preprocessing_metadata.json")

                                    # Get run ID
                                    run_id = mlflow.active_run().info.run_id
                                    logger.info(f"Model and preprocessor logged to MLflow (run: {run_id})")

                                    # Explicitly register models (for old MLflow server compatibility)
                                    model_uri = f"runs:/{run_id}/model"
                                    preprocessor_uri = f"runs:/{run_id}/preprocessor"

                                    try:
                                        # Register or create new version of model
                                        mv = self.mlflow_client.client.create_model_version(
                                            name=model_name,
                                            source=model_uri,
                                            run_id=run_id
                                        )
                                        logger.info(f"Registered model {model_name} version {mv.version}")
                                    except Exception as e:
                                        if "RESOURCE_ALREADY_EXISTS" in str(e):
                                            # Model already registered, create new version
                                            mv = self.mlflow_client.client.create_model_version(
                                                name=model_name,
                                                source=model_uri,
                                                run_id=run_id
                                            )
                                            logger.info(f"Created new version {mv.version} for model {model_name}")
                                        else:
                                            # Model doesn't exist, create it first
                                            try:
                                                self.mlflow_client.client.create_registered_model(model_name)
                                                logger.info(f"Created registered model {model_name}")
                                                mv = self.mlflow_client.client.create_model_version(
                                                    name=model_name,
                                                    source=model_uri,
                                                    run_id=run_id
                                                )
                                                logger.info(f"Registered model {model_name} version {mv.version}")
                                            except Exception as e2:
                                                logger.error(f"Failed to register model {model_name}: {e2}")

                                    try:
                                        # Register or create new version of preprocessor
                                        pv = self.mlflow_client.client.create_model_version(
                                            name=preprocessor_name,
                                            source=preprocessor_uri,
                                            run_id=run_id
                                        )
                                        logger.info(f"Registered preprocessor {preprocessor_name} version {pv.version}")
                                    except Exception as e:
                                        if "RESOURCE_ALREADY_EXISTS" in str(e):
                                            pv = self.mlflow_client.client.create_model_version(
                                                name=preprocessor_name,
                                                source=preprocessor_uri,
                                                run_id=run_id
                                            )
                                            logger.info(f"Created new version {pv.version} for preprocessor {preprocessor_name}")
                                        else:
                                            try:
                                                self.mlflow_client.client.create_registered_model(preprocessor_name)
                                                logger.info(f"Created registered preprocessor {preprocessor_name}")
                                                pv = self.mlflow_client.client.create_model_version(
                                                    name=preprocessor_name,
                                                    source=preprocessor_uri,
                                                    run_id=run_id
                                                )
                                                logger.info(f"Registered preprocessor {preprocessor_name} version {pv.version}")
                                            except Exception as e2:
                                                logger.error(f"Failed to register preprocessor {preprocessor_name}: {e2}")

                                    # Promote best model to Production stage
                                    if model_type == best_model_type:
                                        # Get the latest versions that were just registered
                                        model_versions = self.mlflow_client.client.search_model_versions(f"name='{model_name}'")
                                        preprocessor_versions = self.mlflow_client.client.search_model_versions(f"name='{preprocessor_name}'")

                                        if model_versions:
                                            latest_model_version = max(model_versions, key=lambda v: int(v.version))
                                            self.mlflow_client.transition_model_stage(
                                                model_name=model_name,
                                                version=int(latest_model_version.version),
                                                stage="Production"
                                            )
                                            logger.info(f"Best model promoted to Production: {model_name} v{latest_model_version.version}")

                                        if preprocessor_versions:
                                            latest_preprocessor_version = max(preprocessor_versions, key=lambda v: int(v.version))
                                            self.mlflow_client.transition_model_stage(
                                                model_name=preprocessor_name,
                                                version=int(latest_preprocessor_version.version),
                                                stage="Production"
                                            )
                                            logger.info(f"Preprocessor promoted to Production: {preprocessor_name} v{latest_preprocessor_version.version}")
                        finally:
                            # Restore stdout
                            sys.stdout = old_stdout

                    except Exception as e:
                        logger.error(f"Failed to save model {model_type}: {e}", exc_info=True)
                        # Continue with other models

                logger.info(f"All models and preprocessor saved for {pipeline_name} pipeline")

        except Exception as e:
            logger.error(f"Failed to save models and preprocessor: {e}", exc_info=True)
            raise


