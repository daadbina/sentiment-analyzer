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

            logger.info("Checking for baseline models to upload...")

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
                    import mlflow
                    import mlflow.sklearn

                    with mlflow.start_run(run_name=f"baseline_{full_model_name}"):
                        # Log the model
                        mlflow.sklearn.log_model(model, "model")

                        # Log metadata
                        mlflow.log_param("source", "baseline")
                        mlflow.log_param("pipeline", pipeline_name)
                        mlflow.log_param("model_type", model_name)

                        # Get run ID
                        run_id = mlflow.active_run().info.run_id

                        # Register model
                        model_uri = f"runs:/{run_id}/model"
                        mv = mlflow.register_model(model_uri, full_model_name)

                        logger.info(f"Baseline model registered: {full_model_name} version {mv.version}")

                        # Promote to Production stage
                        self.mlflow_client.client.transition_model_version_stage(
                            name=full_model_name,
                            version=mv.version,
                            stage="Production",
                        )

                        logger.info(f"Baseline model promoted to Production: {full_model_name} v{mv.version}")

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
        Uses BTC features + relevant sentiment features.

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

                # Set default dates
                if not end_date:
                    end_date = datetime.now(timezone.utc)
                else:
                    end_date = datetime.fromisoformat(end_date)

                if not start_date:
                    start_date = end_date - timedelta(days=18*30)
                else:
                    start_date = datetime.fromisoformat(start_date)

                if start_date.tzinfo is not None:
                    start_date = start_date.replace(tzinfo=None)
                if end_date.tzinfo is not None:
                    end_date = end_date.replace(tzinfo=None)

                logger.info(f"Training window: {start_date} to {end_date}")

                # NEW APPROACH: Use BTC timestamps as anchor, not semantic group timestamps
                # This allows us to use ALL historical BTC data (2979 records with 10h future data)
                # instead of only recent semantic groups (which have no future data)

                logger.info("Fetching BTC records with future price data available")
                btc_records = await self._fetch_btc_records_with_future_data(
                    hours_ahead=10,
                    start_date=start_date,
                    end_date=end_date
                )

                if not btc_records:
                    logger.warning("No BTC records with future data found")
                    raise TrainerError("No BTC records with future data")

                logger.info(f"Found {len(btc_records)} BTC records with future data")

                # For each BTC timestamp, get news sentiment features and calculate forward target
                logger.info("Building training dataset from BTC timestamps")
                X_btc_final, y_btc = await self._build_btc_training_data(btc_records)

                if X_btc_final.empty or len(y_btc) == 0:
                    logger.warning("No training data could be built from BTC records")
                    raise TrainerError("No training data could be built")

                logger.info(f"BTC training data: X shape={X_btc_final.shape}, y shape={y_btc.shape}")
                logger.info(f"BTC target distribution: min={y_btc.min():.4f}, max={y_btc.max():.4f}, mean={y_btc.mean():.4f}, std={y_btc.std():.4f}")

                # Check for null values in target
                null_count = y_btc.isnull().sum()
                if null_count > 0:
                    logger.warning(f"Found {null_count} null values in BTC target, dropping them")
                    valid_mask = ~y_btc.isnull()
                    X_btc_final = X_btc_final[valid_mask]
                    y_btc = y_btc[valid_mask]
                    logger.info(f"After dropping nulls: {len(y_btc)} samples remaining")

                # Validate minimum dataset size
                min_samples_required = 50
                if len(y_btc) < min_samples_required:
                    logger.error(f"Insufficient BTC training data: {len(y_btc)} samples (minimum {min_samples_required} required)")
                    raise TrainerError(f"Insufficient BTC training data: {len(y_btc)} samples")

                # Preprocess data
                logger.info("Preprocessing BTC data")
                X_btc_processed, _ = self.preprocessor.preprocess(X_btc_final, y_btc, fit=True)
                logger.info(f"BTC data after preprocessing: {X_btc_processed.shape}")

                # Split data (no stratification for regression)
                logger.info("Splitting BTC data")
                from sklearn.model_selection import train_test_split
                X_train, X_temp, y_train, y_temp = train_test_split(
                    X_btc_processed, y_btc, test_size=0.3, random_state=config.training.random_seed
                )
                X_val, X_test, y_val, y_test = train_test_split(
                    X_temp, y_temp, test_size=0.67, random_state=config.training.random_seed
                )
                logger.info(f"BTC Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

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

                # Save BTC models and preprocessor to local, S3, and MLflow
                logger.info("Saving BTC models to local/S3/MLflow")
                await self._save_models_and_preprocessor(
                    models=btc_models,
                    preprocessor=self.preprocessor,
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
                    "num_features": X_btc_processed.shape[1],
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

        Trains classification models to predict conflict between countries.
        Uses sentiment features + entity features (excludes BTC features).

        Args:
            start_date: Optional start date for data retrieval
            end_date: Optional end date for data retrieval

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

                # Set default dates
                if not end_date:
                    end_date = datetime.now(timezone.utc)
                else:
                    end_date = datetime.fromisoformat(end_date)

                if not start_date:
                    start_date = end_date - timedelta(days=18*30)
                else:
                    start_date = datetime.fromisoformat(start_date)

                if start_date.tzinfo is not None:
                    start_date = start_date.replace(tzinfo=None)
                if end_date.tzinfo is not None:
                    end_date = end_date.replace(tzinfo=None)

                logger.info(f"Training window: {start_date} to {end_date}")

                # Retrieve labels - for conflict we need binary labels
                logger.info("Retrieving conflict labels (binary)")
                y = await self.label_retriever.retrieve_labels(
                    start_date=start_date,
                    end_date=end_date,
                )

                if y.empty:
                    logger.error("No labels retrieved for conflict training!")
                    raise TrainerError("No conflict training data available")

                # Extract group IDs
                group_ids = y['group_id'].unique().tolist()
                group_ids = [gid for gid in group_ids if gid is not None]
                logger.info(f"Found {len(group_ids)} unique groups in labels")

                if not group_ids:
                    raise TrainerError("No semantic groups found in labeled data")

                # Retrieve features
                logger.info("Retrieving features for conflict prediction")
                X = self.feature_retriever.retrieve_features(
                    entity_ids=group_ids,
                    start_date=start_date,
                    end_date=end_date,
                )

                if X.empty:
                    logger.error("No features retrieved for conflict training!")
                    raise TrainerError("No conflict training data available")

                # Filter to conflict-relevant features (EXCLUDE BTC features)
                # Note: Features in Feast have the prefix 'semantic_group_features:'
                conflict_feature_names = [
                    'sentiment_mean', 'sentiment_std', 'sentiment_polarity_ratio', 'sentiment_volatility',
                    'entity_count', 'entity_diversity', 'entity_prominence', 'entity_concentration',
                    'num_sources', 'source_credibility_avg', 'source_credibility_std', 'source_diversity_score',
                    'time_span_hours', 'publication_velocity', 'temporal_concentration', 'days_since_first_article',
                    'avg_word_count', 'avg_title_length', 'language_diversity', 'domain_diversity',
                    'centroid_magnitude', 'intra_cluster_similarity_mean', 'intra_cluster_similarity_std', 'embedding_drift_score',
                ]

                # Keep only conflict features that exist in X (with or without prefix)
                available_conflict_features = []
                for col in X.columns:
                    if col == 'group_id':
                        continue
                    # Check if column name (with or without prefix) matches any conflict feature
                    col_name = col.replace('semantic_group_features:', '')
                    if col_name in conflict_feature_names:
                        available_conflict_features.append(col)
                logger.info(f"Conflict features available: {available_conflict_features}")

                # Keep group_id for alignment
                if 'group_id' in X.columns:
                    X_conflict = X[['group_id'] + available_conflict_features].copy()
                else:
                    X_conflict = X[available_conflict_features].copy()

                logger.info(f"Filtered to {X_conflict.shape[1]} conflict-relevant features (BTC features excluded)")

                # For conflict prediction, we use label_realized as binary target
                if 'label_realized' not in y.columns:
                    logger.error("label_realized not found in labels - cannot train conflict prediction model")
                    raise TrainerError("Conflict target variable not available")

                # Handle null values in label_realized
                null_count = y['label_realized'].isnull().sum()
                if null_count > 0:
                    logger.warning(f"Found {null_count} null values in label_realized, dropping them")
                    y = y.dropna(subset=['label_realized'])
                    logger.info(f"After dropping nulls: {len(y)} labels remaining")

                # Align features with labels
                logger.info("Aligning features with labels by group_id")
                X_indexed = X_conflict.set_index('group_id') if 'group_id' in X_conflict.columns else X_conflict

                aligned_X_list = []
                aligned_y_list = []
                matched_labels = 0

                for idx, label_row in y.iterrows():
                    group_id = label_row['group_id']
                    if group_id in X_indexed.index:
                        feature_row = X_indexed.loc[group_id]
                        if isinstance(feature_row, pd.DataFrame):
                            feature_row = feature_row.iloc[0]

                        aligned_X_list.append(feature_row)
                        aligned_y_list.append(label_row['label_realized'])
                        matched_labels += 1

                logger.info(f"Alignment results: {matched_labels} matched labels")

                if not aligned_X_list:
                    logger.error("No labels could be aligned with conflict features!")
                    raise TrainerError("No labels could be aligned with conflict features")

                # Create aligned dataframes
                X_conflict_final = pd.DataFrame(aligned_X_list).reset_index(drop=True)
                y_conflict = pd.Series(aligned_y_list, dtype=int).reset_index(drop=True)

                logger.info(f"Conflict training data: X shape={X_conflict_final.shape}, y shape={y_conflict.shape}")
                logger.info(f"Conflict label distribution: {y_conflict.value_counts().to_dict()}")

                # CRITICAL: Filter to only samples with real features (not all NULL)
                # Training on all-NULL samples adds noise and reduces model performance
                # We'll use a rule-based approach for samples without features
                logger.info("Filtering samples with real features")

                # Count NULL values per row
                null_counts_per_row = X_conflict_final.isnull().sum(axis=1)
                total_features = X_conflict_final.shape[1]

                # Keep only rows with at least SOME real data (not all NULL)
                has_features_mask = null_counts_per_row < total_features

                X_conflict_filtered = X_conflict_final[has_features_mask].copy()
                y_conflict_filtered = y_conflict[has_features_mask].copy()

                logger.info(f"Filtered conflict data: {len(X_conflict_filtered)} samples with features (removed {len(X_conflict_final) - len(X_conflict_filtered)} all-NULL samples)")
                logger.info(f"Filtered label distribution: {y_conflict_filtered.value_counts().to_dict()}")

                # Calculate base rate for samples without features (for rule-based prediction)
                no_features_mask = ~has_features_mask
                if no_features_mask.sum() > 0:
                    no_features_realized_rate = y_conflict[no_features_mask].mean()
                    logger.info(f"Base rate for samples without features: {no_features_realized_rate:.3f} ({y_conflict[no_features_mask].sum()}/{no_features_mask.sum()})")

                # Use filtered data for training
                X_conflict_final = X_conflict_filtered
                y_conflict = y_conflict_filtered

                # Validate minimum dataset size
                min_samples_required = 50
                if len(y_conflict) < min_samples_required:
                    logger.error(f"Insufficient conflict training data: {len(y_conflict)} samples (minimum {min_samples_required} required)")
                    raise TrainerError(f"Insufficient conflict training data: {len(y_conflict)} samples")

                # Validate minimum samples per class
                class_counts = y_conflict.value_counts().to_dict()
                min_class_samples = min(class_counts.values())
                min_class_required = 10
                if min_class_samples < min_class_required:
                    logger.warning(f"Low sample count for minority class: {min_class_samples} samples")

                # Preprocess data
                logger.info("Preprocessing conflict data")
                X_conflict_processed, _ = self.preprocessor.preprocess(X_conflict_final, y_conflict, fit=True)
                logger.info(f"Conflict data after preprocessing: {X_conflict_processed.shape}")

                # Split data with stratification
                logger.info("Splitting conflict data with stratification")
                (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
                    self.splitter.split_stratified(X_conflict_processed, y_conflict)
                )
                logger.info(f"Conflict Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")
                logger.info(f"Train labels: {y_train.value_counts().to_dict()}")
                logger.info(f"Val labels: {y_val.value_counts().to_dict()}")
                logger.info(f"Test labels: {y_test.value_counts().to_dict()}")

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

                # Save conflict models and preprocessor to local, S3, and MLflow
                logger.info("Saving conflict models to local/S3/MLflow")
                await self._save_models_and_preprocessor(
                    models=conflict_models,
                    preprocessor=self.preprocessor,
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
                    "num_features": X_conflict_processed.shape[1],
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
        Build training dataset from BTC records.

        For each BTC timestamp T:
        1. Get BTC features at time T (volatility, volume, spike, etc.)
        2. Calculate forward price change from T to T+10h (target)

        Uses ONLY BTC price data, no semantic/sentiment features.

        Args:
            btc_records: List of BTC records with timestamp and close price

        Returns:
            Tuple of (features DataFrame, targets Series)
        """
        try:
            from datetime import timedelta

            X_list = []
            y_list = []
            skipped_no_future = 0
            skipped_no_features = 0

            logger.info(f"Processing {len(btc_records)} BTC records...")

            for i, record in enumerate(btc_records):
                timestamp_t = record["timestamp"]
                price_t = record["close"]

                # Calculate future timestamp
                timestamp_future = timestamp_t + timedelta(hours=10)

                # Get BTC features at time T from btc_truth table
                # Filter by BTCUSDT only to avoid mixing different cryptocurrencies
                query_features = """
                    SELECT
                        change_pct_10h,
                        volatility_score,
                        volume,
                        label_spike,
                        open,
                        high,
                        low,
                        close
                    FROM btc_truth
                    WHERE timestamp = $1
                    AND event_id LIKE 'binance_BTCUSDT_%'
                    LIMIT 1
                """

                row_features = await self.postgres_client.fetch_one(
                    query_features,
                    timestamp_t
                )

                if not row_features:
                    skipped_no_features += 1
                    continue

                # Get future BTC price for target calculation
                # Filter by BTCUSDT only to avoid mixing different cryptocurrencies
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

                # Build feature vector from BTC data with selected features
                open_price = float(row_features['open']) if row_features['open'] is not None else price_t
                high_price = float(row_features['high']) if row_features['high'] is not None else price_t
                low_price = float(row_features['low']) if row_features['low'] is not None else price_t
                close_price = float(row_features['close']) if row_features['close'] is not None else price_t
                volume = float(row_features['volume']) if row_features['volume'] is not None else 0.0

                # Calculate key derived features (reduced set to avoid overfitting)
                price_range_pct = ((high_price - low_price) / close_price * 100.0) if close_price > 0 and high_price > low_price else 0.0
                body_size_pct = (abs(close_price - open_price) / close_price * 100.0) if close_price > 0 else 0.0
                is_bullish = 1 if close_price > open_price else 0

                # Price position in range (key indicator)
                price_range = high_price - low_price if high_price > low_price else 0.0
                close_position_in_range = ((close_price - low_price) / price_range) if price_range > 0 else 0.5

                # Momentum features (using backward change as proxy)
                backward_change = float(row_features['change_pct_10h']) if row_features['change_pct_10h'] is not None else 0.0
                momentum_strength = abs(backward_change)

                # Volume features
                volume_normalized = volume / 1000000.0  # Normalize volume to millions

                # Cyclical time encoding (to capture periodic patterns)
                import math
                hour_sin = math.sin(2 * math.pi * timestamp_t.hour / 24)
                hour_cos = math.cos(2 * math.pi * timestamp_t.hour / 24)
                day_sin = math.sin(2 * math.pi * timestamp_t.weekday() / 7)
                day_cos = math.cos(2 * math.pi * timestamp_t.weekday() / 7)

                features = {
                    # Core price features
                    'btc_close': close_price,
                    'btc_high': high_price,
                    'btc_low': low_price,
                    'btc_open': open_price,
                    # Key derived features
                    'btc_price_range_pct': price_range_pct,
                    'btc_body_size_pct': body_size_pct,
                    'btc_close_position_in_range': close_position_in_range,
                    'btc_is_bullish': is_bullish,
                    # Momentum features
                    'btc_change_pct_10h_backward': backward_change,
                    'btc_momentum_strength': momentum_strength,
                    # Volume and volatility
                    'btc_volume': volume_normalized,
                    'btc_volatility_score': float(row_features['volatility_score']) if row_features['volatility_score'] is not None else 0.0,
                    'btc_label_spike': int(row_features['label_spike']) if row_features['label_spike'] is not None else 0,
                    # Cyclical time features
                    'btc_hour_sin': hour_sin,
                    'btc_hour_cos': hour_cos,
                    'btc_day_sin': day_sin,
                    'btc_day_cos': day_cos,
                }

                X_list.append(features)
                y_list.append(target)

                if (i + 1) % 500 == 0:
                    logger.info(f"Processed {i + 1}/{len(btc_records)} BTC records...")

            logger.info(f"Built training data: {len(X_list)} samples")
            logger.info(f"Skipped {skipped_no_future} records without future price")
            logger.info(f"Skipped {skipped_no_features} records without BTC features")

            if not X_list:
                return pd.DataFrame(), pd.Series(dtype=float)

            X = pd.DataFrame(X_list)
            y = pd.Series(y_list, dtype=float)

            logger.info(f"BTC training data shape: X={X.shape}, y={y.shape}")
            logger.info(f"BTC features: {list(X.columns)}")
            logger.info(f"Target distribution: min={y.min():.2f}%, max={y.max():.2f}%, mean={y.mean():.2f}%, std={y.std():.2f}%")

            return X, y

        except Exception as e:
            logger.error(f"Failed to build BTC training data: {e}", exc_info=True)
            return pd.DataFrame(), pd.Series(dtype=float)

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

                # Upload preprocessor to S3
                preprocessor_s3_key = f"models/{pipeline_name}/preprocessor.pkl"
                self.s3_client.upload_file(str(preprocessor_local_path), preprocessor_s3_key)
                logger.info(f"Preprocessor uploaded to S3: {preprocessor_s3_key}")

                # Save each model
                for model_type, (model_instance, metrics) in models.items():
                    try:
                        # Save model to temp file
                        model_local_path = temp_path / f"{model_type}.pkl"
                        with open(model_local_path, "wb") as f:
                            pickle.dump(model_instance.model, f)
                        logger.info(f"Model saved to temp: {model_local_path}")

                        # Upload model to S3
                        model_s3_key = f"models/{pipeline_name}/{model_type}/model.pkl"
                        self.s3_client.upload_file(str(model_local_path), model_s3_key)
                        logger.info(f"Model uploaded to S3: {model_s3_key}")

                        # Log model to MLflow (suppress Unicode errors on Windows)
                        import sys
                        import io

                        # Temporarily redirect stdout to suppress MLflow emoji output
                        old_stdout = sys.stdout
                        sys.stdout = io.StringIO()

                        try:
                            with mlflow.start_run(run_name=f"{pipeline_name}_{model_type}"):
                                # Log parameters
                                mlflow.log_param("pipeline", pipeline_name)
                                mlflow.log_param("model_type", model_type)
                                mlflow.log_param("is_best_model", model_type == best_model_type)

                                # Log metrics
                                for metric_name, metric_value in metrics.items():
                                    if isinstance(metric_value, (int, float)):
                                        mlflow.log_metric(metric_name, metric_value)

                                # Log evaluation results for this model
                                if model_type in evaluation_results:
                                    for metric_name, metric_value in evaluation_results[model_type].items():
                                        if isinstance(metric_value, (int, float)):
                                            mlflow.log_metric(f"eval_{metric_name}", metric_value)

                                # Log model using appropriate flavor
                                if "xgboost" in model_type.lower():
                                    mlflow.xgboost.log_model(model_instance.model, "model")
                                else:
                                    mlflow.sklearn.log_model(model_instance.model, "model")

                                # Register model in MLflow Model Registry
                                run_id = mlflow.active_run().info.run_id
                                model_uri = f"runs:/{run_id}/model"
                                model_name = f"{pipeline_name}_{model_type}"

                                model_version = mlflow.register_model(model_uri, model_name)
                                logger.info(f"Model registered in MLflow: {model_name} version {model_version.version}")

                                # Promote best model to Production stage
                                if model_type == best_model_type:
                                    self.mlflow_client.transition_model_stage(
                                        model_name=model_name,
                                        version=int(model_version.version),
                                        stage="Production"
                                    )
                                    logger.info(f"Best model promoted to Production: {model_name} v{model_version.version}")
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


