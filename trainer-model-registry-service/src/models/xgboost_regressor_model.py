"""
XGBoost Regressor model implementation for BTC price prediction.

Predicts continuous BTC price change percentage.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import xgboost as xgb

from src.models.base_model import BaseModel
from src.config import config
from src.exceptions import TrainingError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class XGBoostRegressorModel(BaseModel):
    """XGBoost Regressor model for BTC price prediction."""

    def __init__(self):
        """Initialize XGBoost Regressor model."""
        model_config = {
            "max_depth": 8,  # Increased from 6 for more complex patterns
            "learning_rate": 0.05,  # Decreased for better generalization
            "n_estimators": 300,  # Increased from 100 for better learning
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,  # Regularization
            "gamma": 0.1,  # Regularization
            "reg_alpha": 0.1,  # L1 regularization
            "reg_lambda": 1.0,  # L2 regularization
            "objective": "reg:squarederror",  # Regression objective
            "eval_metric": "rmse",  # Root Mean Squared Error
            "random_state": config.training.random_seed,
            "verbosity": 1,
        }

        super().__init__(
            model_name="xgboost_btc_regressor",
            model_type="xgboost_regressor",
            config=model_config,
        )

        self.model = xgb.XGBRegressor(**model_config)
        logger.info("XGBoost Regressor model initialized with config: %s", model_config)

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Train XGBoost Regressor model.

        Args:
            X_train: Training features
            y_train: Training labels (continuous values)
            X_val: Optional validation features
            y_val: Optional validation labels

        Returns:
            Dictionary with training metrics

        Raises:
            TrainingError: If training fails
        """
        with tracer.start_as_current_span("train_xgboost_regressor") as span:
            span.set_attribute("num_train_samples", len(X_train))
            if X_val is not None:
                span.set_attribute("num_val_samples", len(X_val))

            try:
                self.validate_input(X_train, y_train)

                logger.info(f"Training XGBoost Regressor model with {len(X_train)} samples")
                logger.info(f"Training data shape: {X_train.shape}")
                logger.info(f"Training labels distribution: min={y_train.min():.4f}, max={y_train.max():.4f}, mean={y_train.mean():.4f}, std={y_train.std():.4f}")
                logger.debug(f"Training features: {list(X_train.columns)}")
                logger.debug(f"Training data null values: {X_train.isnull().sum().sum()}")

                # Prepare evaluation set if validation data provided
                eval_set = []
                if X_val is not None and y_val is not None:
                    self.validate_input(X_val, y_val)
                    eval_set = [(X_val, y_val)]
                    logger.info(f"Validation data shape: {X_val.shape}")
                    logger.info(f"Validation labels distribution: min={y_val.min():.4f}, max={y_val.max():.4f}, mean={y_val.mean():.4f}")

                logger.info("Starting XGBoost Regressor model fitting...")

                # Train model
                self.model.fit(
                    X_train,
                    y_train,
                    eval_set=eval_set if eval_set else None,
                    verbose=False,
                )

                self.is_trained = True

                # Get best score
                best_score = None
                if eval_set:
                    # Get validation predictions
                    val_pred = self.model.predict(X_val)
                    # Calculate RMSE
                    rmse = np.sqrt(np.mean((y_val - val_pred) ** 2))
                    # Calculate R²
                    ss_res = np.sum((y_val - val_pred) ** 2)
                    ss_tot = np.sum((y_val - y_val.mean()) ** 2)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                    best_score = {"rmse": rmse, "r2": r2}
                    logger.info(f"Best validation RMSE: {rmse:.4f}, R²: {r2:.4f}")

                metrics = {
                    "model_type": "xgboost_regressor",
                    "num_train_samples": len(X_train),
                    "num_features": X_train.shape[1],
                    "n_estimators": self.config["n_estimators"],
                }
                if best_score:
                    metrics.update(best_score)

                logger.info(f"XGBoost Regressor training complete: {metrics}")
                return metrics

            except Exception as e:
                logger.error(f"XGBoost Regressor training failed: {e}")
                raise TrainingError(f"XGBoost Regressor training failed: {e}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions.

        Args:
            X: Features for prediction

        Returns:
            Predictions (continuous values)

        Raises:
            TrainingError: If prediction fails
        """
        with tracer.start_as_current_span("predict_xgboost_regressor"):
            try:
                if not self.is_trained:
                    raise TrainingError("Model not trained yet")

                self.validate_input(X)
                predictions = self.model.predict(X)
                logger.debug(f"Made predictions for {len(X)} samples")
                return predictions

            except Exception as e:
                logger.error(f"XGBoost Regressor prediction failed: {e}")
                raise TrainingError(f"XGBoost Regressor prediction failed: {e}")

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Get prediction probabilities (not applicable for regression).

        For regression, returns predictions as 2D array for compatibility.

        Args:
            X: Features for prediction

        Returns:
            Predictions as 2D array

        Raises:
            TrainingError: If prediction fails
        """
        predictions = self.predict(X)
        # Return as 2D array for compatibility with classification interface
        return np.column_stack([np.zeros_like(predictions), predictions])

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores.

        Returns:
            Dictionary mapping feature names to importance scores

        Raises:
            TrainingError: If model not trained
        """
        with tracer.start_as_current_span("get_feature_importance"):
            try:
                if not self.is_trained:
                    raise TrainingError("Model not trained yet")

                importance = self.model.feature_importances_
                feature_names = self.model.feature_names_in_

                importance_dict = dict(zip(feature_names, importance))
                logger.debug(f"Feature importance computed for {len(importance_dict)} features")

                return importance_dict

            except Exception as e:
                logger.error(f"Failed to get feature importance: {e}")
                raise TrainingError(f"Failed to get feature importance: {e}")

    def save(self, path: str) -> None:
        """
        Save model to disk.

        Args:
            path: Path to save model

        Raises:
            TrainingError: If save fails
        """
        with tracer.start_as_current_span("save_xgboost_regressor"):
            try:
                if not self.is_trained:
                    raise TrainingError("Model not trained yet")

                self.model.save_model(path)
                logger.info(f"XGBoost Regressor model saved to {path}")

            except Exception as e:
                logger.error(f"Failed to save XGBoost Regressor model: {e}")
                raise TrainingError(f"Failed to save model: {e}")

    def load(self, path: str) -> None:
        """
        Load model from disk.

        Args:
            path: Path to load model from

        Raises:
            TrainingError: If load fails
        """
        with tracer.start_as_current_span("load_xgboost_regressor"):
            try:
                self.model.load_model(path)
                self.is_trained = True
                logger.info(f"XGBoost Regressor model loaded from {path}")

            except Exception as e:
                logger.error(f"Failed to load XGBoost Regressor model: {e}")
                raise TrainingError(f"Failed to load model: {e}")

