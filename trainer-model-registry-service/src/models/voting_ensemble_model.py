"""
Voting Ensemble model implementation.

Combines multiple base models using voting strategy following Strategy pattern.
"""

import logging
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from sklearn.ensemble import VotingClassifier

from src.models.base_model import BaseModel
from src.exceptions import TrainingError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class VotingEnsembleModel(BaseModel):
    """Voting ensemble combining multiple base models."""

    def __init__(self, base_models: List[BaseModel], config: Dict[str, Any]):
        """
        Initialize Voting Ensemble model.

        Args:
            base_models: List of base models to combine
            config: Model configuration dictionary
        """
        super().__init__(
            model_name="voting_ensemble",
            model_type="voting_ensemble",
            config=config,
        )
        self.base_models = base_models
        self.model = None
        logger.info(
            f"Voting Ensemble initialized with {len(base_models)} base models: "
            f"{[m.model_name for m in base_models]}"
        )

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Train all base models.

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
        with tracer.start_as_current_span("train_voting_ensemble"):
            try:
                logger.info(
                    f"Training Voting Ensemble with {X_train.shape[0]} samples, "
                    f"{X_train.shape[1]} features"
                )

                # Train all base models
                base_model_metrics = {}
                for base_model in self.base_models:
                    logger.info(f"Training base model: {base_model.model_name}")
                    metrics = base_model.train(X_train, y_train, X_val, y_val)
                    base_model_metrics[base_model.model_name] = metrics
                    logger.info(f"Base model {base_model.model_name} trained")

                # Create voting classifier
                voting_method = self.config.get("voting", "soft")
                estimators = [
                    (model.model_name, model.model) for model in self.base_models
                ]

                self.model = VotingClassifier(
                    estimators=estimators,
                    voting=voting_method,
                )

                # Fit voting classifier (refit on training data)
                self.model.fit(X_train, y_train)
                self.is_trained = True

                # Compute ensemble metrics
                train_score = self.model.score(X_train, y_train)
                logger.info(f"Ensemble training accuracy: {train_score:.4f}")

                metrics = {
                    "ensemble_training_accuracy": train_score,
                    "voting_method": voting_method,
                    "num_base_models": len(self.base_models),
                    "base_model_metrics": base_model_metrics,
                }

                # Validation metrics if provided
                if X_val is not None and y_val is not None:
                    val_score = self.model.score(X_val, y_val)
                    metrics["ensemble_validation_accuracy"] = val_score
                    logger.info(f"Ensemble validation accuracy: {val_score:.4f}")

                logger.info("Voting Ensemble training complete")
                return metrics

            except Exception as e:
                logger.error(f"Voting Ensemble training failed: {e}")
                raise TrainingError(
                    f"Voting Ensemble training failed: {e}",
                    model_name=self.model_name,
                )

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions using ensemble voting.

        Args:
            X: Features for prediction

        Returns:
            Predicted class labels

        Raises:
            TrainingError: If model not trained or prediction fails
        """
        with tracer.start_as_current_span("predict_voting_ensemble"):
            try:
                if not self.is_trained or self.model is None:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                predictions = self.model.predict(X)
                logger.debug(f"Made ensemble predictions for {len(predictions)} samples")
                return predictions

            except Exception as e:
                logger.error(f"Prediction failed: {e}")
                raise TrainingError(
                    f"Prediction failed: {e}",
                    model_name=self.model_name,
                )

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Get prediction probabilities using ensemble voting.

        Args:
            X: Features for prediction

        Returns:
            Prediction probabilities

        Raises:
            TrainingError: If model not trained or prediction fails
        """
        with tracer.start_as_current_span("predict_proba_voting_ensemble"):
            try:
                if not self.is_trained or self.model is None:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                probabilities = self.model.predict_proba(X)
                logger.debug(f"Computed ensemble probabilities for {len(probabilities)} samples")
                return probabilities

            except Exception as e:
                logger.error(f"Probability prediction failed: {e}")
                raise TrainingError(
                    f"Probability prediction failed: {e}",
                    model_name=self.model_name,
                )

    def get_feature_importance(self) -> Dict[str, Any]:
        """
        Get feature importance from base models.

        Returns:
            Dictionary with feature importances from each base model

        Raises:
            TrainingError: If models not trained
        """
        with tracer.start_as_current_span("get_feature_importance_voting_ensemble"):
            try:
                if not self.is_trained:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                importances = {}
                for base_model in self.base_models:
                    try:
                        base_importance = base_model.get_feature_importance()
                        importances[base_model.model_name] = base_importance
                    except Exception as e:
                        logger.warning(
                            f"Could not get importance from {base_model.model_name}: {e}"
                        )

                logger.debug(f"Extracted feature importances from {len(importances)} models")
                return importances

            except Exception as e:
                logger.error(f"Failed to get feature importance: {e}")
                raise TrainingError(
                    f"Failed to get feature importance: {e}",
                    model_name=self.model_name,
                )

    def serialize(self) -> bytes:
        """
        Serialize ensemble model to bytes.

        Returns:
            Serialized model

        Raises:
            TrainingError: If serialization fails
        """
        with tracer.start_as_current_span("serialize_voting_ensemble"):
            try:
                import pickle

                if not self.is_trained or self.model is None:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                serialized = pickle.dumps(self.model)
                logger.debug(f"Serialized ensemble model: {len(serialized)} bytes")
                return serialized

            except Exception as e:
                logger.error(f"Serialization failed: {e}")
                raise TrainingError(
                    f"Serialization failed: {e}",
                    model_name=self.model_name,
                )

    def deserialize(self, data: bytes) -> None:
        """
        Deserialize ensemble model from bytes.

        Args:
            data: Serialized model data

        Raises:
            TrainingError: If deserialization fails
        """
        with tracer.start_as_current_span("deserialize_voting_ensemble"):
            try:
                import pickle

                self.model = pickle.loads(data)
                self.is_trained = True
                logger.debug("Deserialized ensemble model successfully")

            except Exception as e:
                logger.error(f"Deserialization failed: {e}")
                raise TrainingError(
                    f"Deserialization failed: {e}",
                    model_name=self.model_name,
                )

