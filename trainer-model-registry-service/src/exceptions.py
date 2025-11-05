"""
Custom exception hierarchy for Trainer & Model Registry Service.

Provides structured error handling with specific exception types
for different failure scenarios.
"""

from typing import Optional, Any


class TrainerError(Exception):
    """Base exception for all trainer service errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize TrainerError.

        Args:
            message: Error message
            error_code: Optional error code for categorization
            details: Optional dictionary with additional error details
        """
        self.message = message
        self.error_code = error_code or "TRAINER_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return formatted error string."""
        return f"[{self.error_code}] {self.message}"


class TrainingError(TrainerError):
    """Exception raised during model training."""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize TrainingError.

        Args:
            message: Error message
            model_name: Name of the model being trained
            details: Optional error details
        """
        super().__init__(message, "TRAINING_ERROR", details or {})
        self.model_name = model_name
        if model_name:
            self.details["model_name"] = model_name


class EvaluationError(TrainerError):
    """Exception raised during model evaluation."""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        metric_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize EvaluationError.

        Args:
            message: Error message
            model_name: Name of the model being evaluated
            metric_name: Name of the metric being computed
            details: Optional error details
        """
        super().__init__(message, "EVALUATION_ERROR", details or {})
        self.model_name = model_name
        self.metric_name = metric_name
        if model_name:
            self.details["model_name"] = model_name
        if metric_name:
            self.details["metric_name"] = metric_name


class RegistrationError(TrainerError):
    """Exception raised during model registration."""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize RegistrationError.

        Args:
            message: Error message
            model_name: Name of the model being registered
            model_version: Version of the model
            details: Optional error details
        """
        super().__init__(message, "REGISTRATION_ERROR", details or {})
        self.model_name = model_name
        self.model_version = model_version
        if model_name:
            self.details["model_name"] = model_name
        if model_version:
            self.details["model_version"] = model_version


class PromotionError(TrainerError):
    """Exception raised during model promotion."""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        current_stage: Optional[str] = None,
        target_stage: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize PromotionError.

        Args:
            message: Error message
            model_name: Name of the model being promoted
            current_stage: Current model stage
            target_stage: Target model stage
            details: Optional error details
        """
        super().__init__(message, "PROMOTION_ERROR", details or {})
        self.model_name = model_name
        self.current_stage = current_stage
        self.target_stage = target_stage
        if model_name:
            self.details["model_name"] = model_name
        if current_stage:
            self.details["current_stage"] = current_stage
        if target_stage:
            self.details["target_stage"] = target_stage


class DriftDetectionError(TrainerError):
    """Exception raised during drift detection."""

    def __init__(
        self,
        message: str,
        drift_type: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize DriftDetectionError.

        Args:
            message: Error message
            drift_type: Type of drift (feature, target, etc.)
            details: Optional error details
        """
        super().__init__(message, "DRIFT_DETECTION_ERROR", details or {})
        self.drift_type = drift_type
        if drift_type:
            self.details["drift_type"] = drift_type


class DataPreparationError(TrainerError):
    """Exception raised during data preparation."""

    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize DataPreparationError.

        Args:
            message: Error message
            stage: Stage of data preparation (retrieval, preprocessing, splitting)
            details: Optional error details
        """
        super().__init__(message, "DATA_PREPARATION_ERROR", details or {})
        self.stage = stage
        if stage:
            self.details["stage"] = stage


class ConfigurationError(TrainerError):
    """Exception raised due to configuration issues."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize ConfigurationError.

        Args:
            message: Error message
            config_key: Configuration key that caused the error
            details: Optional error details
        """
        super().__init__(message, "CONFIGURATION_ERROR", details or {})
        self.config_key = config_key
        if config_key:
            self.details["config_key"] = config_key


class ExternalServiceError(TrainerError):
    """Exception raised when external service fails."""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize ExternalServiceError.

        Args:
            message: Error message
            service_name: Name of the external service (Feast, MLflow, S3, etc.)
            status_code: HTTP status code if applicable
            details: Optional error details
        """
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details or {})
        self.service_name = service_name
        self.status_code = status_code
        if service_name:
            self.details["service_name"] = service_name
        if status_code:
            self.details["status_code"] = status_code
