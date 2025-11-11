"""
Random Forest Regressor model implementation for BTC price prediction.

Ensemble regressor for BTC price change prediction.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from src.models.base_model import BaseModel
from src.config import config
from src.exceptions import TrainingError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class RandomForestRegressorModel(BaseModel):
    """Random Forest Regressor model for BTC price prediction."""

    def __init__(self):
        """Initialize Random Forest Regressor model."""
        model_config = {
            "n_estimators": 300,  # Increased from 100
            "max_depth": 15,  # Increased from 10
            "min_samples_split": 3,  # Decreased from 5 for more splits
            "min_samples_leaf": 1,  # Decreased from 2
            "max_features": "sqrt",  # Feature sampling
            "random_state": config.training.random_seed,
            "n_jobs": -1,
        }

        super().__init__(
            model_name="random_forest_btc_regressor",
            model_type="random_forest_regressor",
            config=model_config,
        )

        self.model = RandomForestRegressor(**model_config)
        logger.info("Random Forest Regressor model initialized")

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """Train Random Forest Regressor model."""
        with tracer.start_as_current_span("train_random_forest_regressor"):
            try:
                logger.info(f"Training Random Forest Regressor with {len(X_train)} samples, {X_train.shape[1]} features")
                logger.debug(f"Random Forest hyperparameters: n_estimators={self.config['n_estimators']}, max_depth={self.config['max_depth']}")

                self.model.fit(X_train, y_train)
                self.is_trained = True

                # Calculate training metrics
                train_pred = self.model.predict(X_train)
                train_rmse = np.sqrt(np.mean((y_train - train_pred) ** 2))
                train_r2 = self.model.score(X_train, y_train)

                logger.info(f"Training RMSE: {train_rmse:.4f}, R²: {train_r2:.4f}")

                metrics = {
                    "training_rmse": train_rmse,
                    "training_r2": train_r2,
                    "n_estimators": self.config["n_estimators"],
                    "max_depth": self.config["max_depth"],
                }

                # Calculate validation metrics if provided
                if X_val is not None and y_val is not None:
                    val_pred = self.model.predict(X_val)
                    val_rmse = np.sqrt(np.mean((y_val - val_pred) ** 2))
                    val_r2 = self.model.score(X_val, y_val)
                    metrics["validation_rmse"] = val_rmse
                    metrics["validation_r2"] = val_r2
                    logger.info(f"Validation RMSE: {val_rmse:.4f}, R²: {val_r2:.4f}")

                logger.info("Random Forest Regressor training complete")
                return metrics

            except Exception as e:
                logger.error(f"Random Forest Regressor training failed: {e}")
                raise TrainingError(f"Random Forest Regressor training failed: {e}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions."""
        if not self.is_trained:
            raise TrainingError("Model not trained yet")
        predictions = self.model.predict(X)
        logger.debug(f"Made predictions for {len(X)} samples")
        return predictions

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Get prediction probabilities (not applicable for regression)."""
        predictions = self.predict(X)
        return np.column_stack([np.zeros_like(predictions), predictions])

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        if not self.is_trained:
            raise TrainingError("Model not trained yet")
        importance = self.model.feature_importances_
        feature_names = self.model.feature_names_in_
        return dict(zip(feature_names, importance))

    def save(self, path: str) -> None:
        """Save model to disk."""
        import joblib
        if not self.is_trained:
            raise TrainingError("Model not trained yet")
        joblib.dump(self.model, path)
        logger.info(f"Random Forest Regressor model saved to {path}")

    def load(self, path: str) -> None:
        """Load model from disk."""
        import joblib
        self.model = joblib.load(path)
        self.is_trained = True
        logger.info(f"Random Forest Regressor model loaded from {path}")

