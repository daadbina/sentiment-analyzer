"""
Gradient Boosting model implementation.

Implements ensemble learning with Gradient Boosting following Strategy pattern.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

from src.models.base_model import BaseModel
from src.exceptions import TrainingError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class GradientBoostingModel(BaseModel):
    """Gradient Boosting classifier for news realization prediction."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Gradient Boosting model.

        Args:
            config: Model configuration dictionary with hyperparameters
        """
        super().__init__(
            model_name="gradient_boosting",
            model_type="gradient_boosting",
            config=config,
        )
        self.model = None
        logger.info("Gradient Boosting model initialized")

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Train Gradient Boosting model.

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
        with tracer.start_as_current_span("train_gradient_boosting"):
            try:
                logger.info(
                    f"Training Gradient Boosting with {X_train.shape[0]} samples, "
                    f"{X_train.shape[1]} features"
                )

                # Extract hyperparameters from config
                n_estimators = self.config.get("n_estimators", 100)
                learning_rate = self.config.get("learning_rate", 0.1)
                max_depth = self.config.get("max_depth", 5)
                min_samples_split = self.config.get("min_samples_split", 5)
                min_samples_leaf = self.config.get("min_samples_leaf", 2)
                subsample = self.config.get("subsample", 0.8)
                random_state = self.config.get("random_state", 42)

                logger.debug(
                    f"Gradient Boosting hyperparameters: "
                    f"n_estimators={n_estimators}, learning_rate={learning_rate}, "
                    f"max_depth={max_depth}"
                )

                # Create and train model
                self.model = GradientBoostingClassifier(
                    n_estimators=n_estimators,
                    learning_rate=learning_rate,
                    max_depth=max_depth,
                    min_samples_split=min_samples_split,
                    min_samples_leaf=min_samples_leaf,
                    subsample=subsample,
                    random_state=random_state,
                )

                self.model.fit(X_train, y_train)
                self.is_trained = True

                # Compute training metrics
                train_score = self.model.score(X_train, y_train)
                logger.info(f"Training accuracy: {train_score:.4f}")

                metrics = {
                    "training_accuracy": train_score,
                    "n_estimators": n_estimators,
                    "learning_rate": learning_rate,
                    "max_depth": max_depth,
                }

                # Validation metrics if provided
                if X_val is not None and y_val is not None:
                    val_score = self.model.score(X_val, y_val)
                    metrics["validation_accuracy"] = val_score
                    logger.info(f"Validation accuracy: {val_score:.4f}")

                logger.info("Gradient Boosting training complete")
                return metrics

            except Exception as e:
                logger.error(f"Gradient Boosting training failed: {e}")
                raise TrainingError(
                    f"Gradient Boosting training failed: {e}",
                    model_name=self.model_name,
                )

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions.

        Args:
            X: Features for prediction

        Returns:
            Predicted class labels

        Raises:
            TrainingError: If model not trained or prediction fails
        """
        with tracer.start_as_current_span("predict_gradient_boosting"):
            try:
                if not self.is_trained or self.model is None:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                predictions = self.model.predict(X)
                logger.debug(f"Made predictions for {len(predictions)} samples")
                return predictions

            except Exception as e:
                logger.error(f"Prediction failed: {e}")
                raise TrainingError(
                    f"Prediction failed: {e}",
                    model_name=self.model_name,
                )

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Get prediction probabilities.

        Args:
            X: Features for prediction

        Returns:
            Prediction probabilities

        Raises:
            TrainingError: If model not trained or prediction fails
        """
        with tracer.start_as_current_span("predict_proba_gradient_boosting"):
            try:
                if not self.is_trained or self.model is None:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                probabilities = self.model.predict_proba(X)
                logger.debug(f"Computed probabilities for {len(probabilities)} samples")
                return probabilities

            except Exception as e:
                logger.error(f"Probability prediction failed: {e}")
                raise TrainingError(
                    f"Probability prediction failed: {e}",
                    model_name=self.model_name,
                )

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores.

        Returns:
            Dictionary mapping feature names to importance scores

        Raises:
            TrainingError: If model not trained
        """
        with tracer.start_as_current_span("get_feature_importance_gradient_boosting"):
            try:
                if not self.is_trained or self.model is None:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                importances = self.model.feature_importances_
                logger.debug(f"Extracted feature importances: {len(importances)} features")
                return {"feature_importances": importances.tolist()}

            except Exception as e:
                logger.error(f"Failed to get feature importance: {e}")
                raise TrainingError(
                    f"Failed to get feature importance: {e}",
                    model_name=self.model_name,
                )

    def serialize(self) -> bytes:
        """
        Serialize model to bytes.

        Returns:
            Serialized model

        Raises:
            TrainingError: If serialization fails
        """
        with tracer.start_as_current_span("serialize_gradient_boosting"):
            try:
                import pickle

                if not self.is_trained or self.model is None:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                serialized = pickle.dumps(self.model)
                logger.debug(f"Serialized model: {len(serialized)} bytes")
                return serialized

            except Exception as e:
                logger.error(f"Serialization failed: {e}")
                raise TrainingError(
                    f"Serialization failed: {e}",
                    model_name=self.model_name,
                )

    def deserialize(self, data: bytes) -> None:
        """
        Deserialize model from bytes.

        Args:
            data: Serialized model data

        Raises:
            TrainingError: If deserialization fails
        """
        with tracer.start_as_current_span("deserialize_gradient_boosting"):
            try:
                import pickle

                self.model = pickle.loads(data)
                self.is_trained = True
                logger.debug("Deserialized model successfully")

            except Exception as e:
                logger.error(f"Deserialization failed: {e}")
                raise TrainingError(
                    f"Deserialization failed: {e}",
                    model_name=self.model_name,
                )

