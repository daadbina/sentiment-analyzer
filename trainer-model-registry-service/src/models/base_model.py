"""
Abstract base model for all model implementations.

Defines common interface for all model trainers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

from src.exceptions import TrainingError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class BaseModel(ABC):
    """Abstract base class for all models."""

    def __init__(self, model_name: str, model_type: str, config: Dict[str, Any]):
        """
        Initialize base model.

        Args:
            model_name: Name of the model
            model_type: Type of model (xgboost, logistic_regression, llm)
            config: Model configuration dictionary
        """
        self.model_name = model_name
        self.model_type = model_type
        self.config = config
        self.model = None
        self.is_trained = False
        logger.info(f"Initialized {model_type} model: {model_name}")

    @abstractmethod
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Train the model.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation features
            y_val: Optional validation labels

        Returns:
            Dictionary with training metrics

        Raises:
            TrainingError: If training fails
        """
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions.

        Args:
            X: Features for prediction

        Returns:
            Predictions

        Raises:
            TrainingError: If prediction fails
        """
        pass

    @abstractmethod
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Get prediction probabilities.

        Args:
            X: Features for prediction

        Returns:
            Prediction probabilities

        Raises:
            TrainingError: If prediction fails
        """
        pass

    @abstractmethod
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores.

        Returns:
            Dictionary mapping feature names to importance scores

        Raises:
            TrainingError: If model not trained
        """
        pass

    def validate_input(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> bool:
        """
        Validate input data.

        Args:
            X: Feature dataframe
            y: Optional label series

        Returns:
            True if valid, False otherwise

        Raises:
            TrainingError: If validation fails
        """
        with tracer.start_as_current_span("validate_input"):
            try:
                if X.empty:
                    raise TrainingError(
                        "Empty feature dataframe",
                        model_name=self.model_name,
                    )

                if X.isnull().sum().sum() > 0:
                    logger.warning("Found null values in features")

                if y is not None:
                    if len(X) != len(y):
                        raise TrainingError(
                            "Feature-label length mismatch",
                            model_name=self.model_name,
                        )

                    if y.isnull().sum() > 0:
                        logger.warning("Found null values in labels")

                logger.debug("Input validation passed")
                return True

            except Exception as e:
                logger.error(f"Input validation failed: {e}")
                raise TrainingError(
                    f"Input validation failed: {e}",
                    model_name=self.model_name,
                )

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model information.

        Returns:
            Dictionary with model info
        """
        return {
            "model_name": self.model_name,
            "model_type": self.model_type,
            "is_trained": self.is_trained,
            "config": self.config,
        }

    def save_model(self, path: str) -> None:
        """
        Save model to file.

        Args:
            path: Path to save model

        Raises:
            TrainingError: If save fails
        """
        with tracer.start_as_current_span("save_model"):
            try:
                if not self.is_trained:
                    raise TrainingError(
                        "Cannot save untrained model",
                        model_name=self.model_name,
                    )

                import pickle

                with open(path, "wb") as f:
                    pickle.dump(self.model, f)

                logger.info(f"Model saved to {path}")

            except Exception as e:
                logger.error(f"Failed to save model: {e}")
                raise TrainingError(
                    f"Failed to save model: {e}",
                    model_name=self.model_name,
                )

    def load_model(self, path: str) -> None:
        """
        Load model from file.

        Args:
            path: Path to load model from

        Raises:
            TrainingError: If load fails
        """
        with tracer.start_as_current_span("load_model"):
            try:
                import pickle

                with open(path, "rb") as f:
                    self.model = pickle.load(f)

                self.is_trained = True
                logger.info(f"Model loaded from {path}")

            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise TrainingError(
                    f"Failed to load model: {e}",
                    model_name=self.model_name,
                )
