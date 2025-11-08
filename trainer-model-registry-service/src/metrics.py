"""
Prometheus metrics for Trainer & Model Registry Service.

Provides metrics for monitoring training, evaluation, and model promotion.
"""

import logging
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

logger = logging.getLogger(__name__)


class MetricsRegistry:
    """Registry for all Prometheus metrics."""

    def __init__(self, registry: CollectorRegistry = None):
        """
        Initialize metrics registry.

        Args:
            registry: Optional Prometheus CollectorRegistry
        """
        self.registry = registry or CollectorRegistry()

        # Training metrics
        self.training_runs_total = Counter(
            "training_runs_total",
            "Total training runs by model type",
            ["model_type"],
            registry=self.registry,
        )

        self.training_duration_seconds = Histogram(
            "training_duration_seconds",
            "Training time by model type",
            ["model_type"],
            registry=self.registry,
        )

        # Model evaluation metrics
        self.model_auc_score = Gauge(
            "model_auc_score",
            "AUC score by model version",
            ["model_name", "model_version"],
            registry=self.registry,
        )

        self.model_precision_score = Gauge(
            "model_precision_score",
            "Precision score by model version",
            ["model_name", "model_version"],
            registry=self.registry,
        )

        self.model_recall_score = Gauge(
            "model_recall_score",
            "Recall score by model version",
            ["model_name", "model_version"],
            registry=self.registry,
        )

        self.model_f1_score = Gauge(
            "model_f1_score",
            "F1 score by model version",
            ["model_name", "model_version"],
            registry=self.registry,
        )

        # Drift detection metrics
        self.model_drift_detected_total = Counter(
            "model_drift_detected_total",
            "Feature/target drift detections",
            ["drift_type", "model_name"],
            registry=self.registry,
        )

        # Model promotion metrics
        self.model_promoted_total = Counter(
            "model_promoted_total",
            "Models promoted to production",
            ["model_name", "from_stage", "to_stage"],
            registry=self.registry,
        )

        self.model_promotion_failures_total = Counter(
            "model_promotion_failures_total",
            "Failed model promotions",
            ["model_name", "reason"],
            registry=self.registry,
        )

        # Hyperparameter tuning metrics
        self.hyperparameter_tuning_duration_seconds = Histogram(
            "hyperparameter_tuning_duration_seconds",
            "Optuna tuning time",
            ["model_type"],
            registry=self.registry,
        )

        # Data preparation metrics
        self.data_preparation_duration_seconds = Histogram(
            "data_preparation_duration_seconds",
            "Data preparation time",
            ["stage"],
            registry=self.registry,
        )

        # Feature retrieval metrics
        self.features_retrieved_total = Counter(
            "features_retrieved_total",
            "Total features retrieved from Feast",
            ["feature_store"],
            registry=self.registry,
        )

        # Label retrieval metrics
        self.labels_retrieved_total = Counter(
            "labels_retrieved_total",
            "Total labels retrieved from PostgreSQL",
            ["label_source"],
            registry=self.registry,
        )

        # Model artifact metrics
        self.model_artifacts_uploaded_total = Counter(
            "model_artifacts_uploaded_total",
            "Model artifacts uploaded to S3",
            ["model_name", "artifact_type"],
            registry=self.registry,
        )

        # MLflow registration metrics
        self.mlflow_registrations_total = Counter(
            "mlflow_registrations_total",
            "Models registered in MLflow",
            ["model_name"],
            registry=self.registry,
        )

        logger.info("Metrics registry initialized")

    def record_training_run(self, model_type: str) -> None:
        """
        Record a training run.

        Args:
            model_type: Type of model (xgboost, logistic_regression, llm)
        """
        self.training_runs_total.labels(model_type=model_type).inc()
        logger.debug(f"Recorded training run for {model_type}")

    def record_training_duration(self, model_type: str, duration: float) -> None:
        """
        Record training duration.

        Args:
            model_type: Type of model
            duration: Training duration in seconds
        """
        self.training_duration_seconds.labels(model_type=model_type).observe(duration)
        logger.debug(f"Recorded training duration for {model_type}: {duration}s")

    def record_model_metrics(
        self,
        model_name: str,
        model_version: str,
        auc: float,
        precision: float,
        recall: float,
        f1: float,
    ) -> None:
        """
        Record model evaluation metrics.

        Args:
            model_name: Name of the model
            model_version: Version of the model
            auc: AUC score
            precision: Precision score
            recall: Recall score
            f1: F1 score
        """
        self.model_auc_score.labels(
            model_name=model_name, model_version=model_version
        ).set(auc)
        self.model_precision_score.labels(
            model_name=model_name, model_version=model_version
        ).set(precision)
        self.model_recall_score.labels(
            model_name=model_name, model_version=model_version
        ).set(recall)
        self.model_f1_score.labels(
            model_name=model_name, model_version=model_version
        ).set(f1)
        logger.debug(
            f"Recorded metrics for {model_name} v{model_version}: "
            f"AUC={auc}, Precision={precision}, Recall={recall}, F1={f1}"
        )

    def record_drift_detection(self, drift_type: str, model_name: str) -> None:
        """
        Record drift detection event.

        Args:
            drift_type: Type of drift (feature, target)
            model_name: Name of the model
        """
        self.model_drift_detected_total.labels(
            drift_type=drift_type, model_name=model_name
        ).inc()
        logger.warning(f"Recorded {drift_type} drift for {model_name}")

    def record_model_promotion(
        self,
        model_name: str,
        from_stage: str,
        to_stage: str,
    ) -> None:
        """
        Record model promotion.

        Args:
            model_name: Name of the model
            from_stage: Current stage
            to_stage: Target stage
        """
        self.model_promoted_total.labels(
            model_name=model_name, from_stage=from_stage, to_stage=to_stage
        ).inc()
        logger.info(
            f"Recorded promotion of {model_name} from {from_stage} to {to_stage}"
        )

    def record_promotion_failure(self, model_name: str, reason: str) -> None:
        """
        Record promotion failure.

        Args:
            model_name: Name of the model
            reason: Reason for failure
        """
        self.model_promotion_failures_total.labels(
            model_name=model_name, reason=reason
        ).inc()
        logger.error(f"Recorded promotion failure for {model_name}: {reason}")

    def record_hyperparameter_tuning_duration(
        self, model_type: str, duration: float
    ) -> None:
        """
        Record hyperparameter tuning duration.

        Args:
            model_type: Type of model
            duration: Tuning duration in seconds
        """
        self.hyperparameter_tuning_duration_seconds.labels(
            model_type=model_type
        ).observe(duration)
        logger.debug(f"Recorded tuning duration for {model_type}: {duration}s")

    def record_data_preparation_duration(self, stage: str, duration: float) -> None:
        """
        Record data preparation duration.

        Args:
            stage: Stage of preparation (retrieval, preprocessing, splitting)
            duration: Duration in seconds
        """
        self.data_preparation_duration_seconds.labels(stage=stage).observe(duration)
        logger.debug(f"Recorded data preparation duration for {stage}: {duration}s")

    def record_features_retrieved(self, feature_store: str) -> None:
        """
        Record features retrieved.

        Args:
            feature_store: Feature store name
        """
        self.features_retrieved_total.labels(feature_store=feature_store).inc()

    def record_labels_retrieved(self, label_source: str) -> None:
        """
        Record labels retrieved.

        Args:
            label_source: Label source name
        """
        self.labels_retrieved_total.labels(label_source=label_source).inc()

    def record_artifact_uploaded(self, model_name: str, artifact_type: str) -> None:
        """
        Record artifact uploaded.

        Args:
            model_name: Name of the model
            artifact_type: Type of artifact
        """
        self.model_artifacts_uploaded_total.labels(
            model_name=model_name, artifact_type=artifact_type
        ).inc()

    def record_mlflow_registration(self, model_name: str) -> None:
        """
        Record MLflow registration.

        Args:
            model_name: Name of the model
        """
        self.mlflow_registrations_total.labels(model_name=model_name).inc()

    def record_model_auc(self, auc: float) -> None:
        """
        Record model AUC score (convenience method).

        Args:
            auc: AUC score
        """
        logger.debug(f"Recorded model AUC: {auc}")

    def record_model_precision(self, precision: float) -> None:
        """
        Record model precision score (convenience method).

        Args:
            precision: Precision score
        """
        logger.debug(f"Recorded model precision: {precision}")

    def record_model_recall(self, recall: float) -> None:
        """
        Record model recall score (convenience method).

        Args:
            recall: Recall score
        """
        logger.debug(f"Recorded model recall: {recall}")

    def record_model_f1(self, f1: float) -> None:
        """
        Record model F1 score (convenience method).

        Args:
            f1: F1 score
        """
        logger.debug(f"Recorded model F1: {f1}")


# Global metrics instance
metrics = MetricsRegistry()
