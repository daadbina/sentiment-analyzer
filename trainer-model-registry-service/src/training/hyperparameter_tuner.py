"""
Hyperparameter tuning using Optuna.

Bayesian optimization for model hyperparameters.
"""

import logging
from typing import Dict, Any, Optional, Callable
import pandas as pd
import numpy as np
import optuna
from optuna.samplers import TPESampler
from sklearn.metrics import roc_auc_score

from src.models.xgboost_model import XGBoostModel
from src.models.logistic_regression_model import LogisticRegressionModel
from src.config import config
from src.exceptions import TrainingError
from src.utils.trace import get_tracer
from src.metrics import metrics

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class HyperparameterTuner:
    """Tunes hyperparameters using Optuna."""

    def __init__(self):
        """Initialize hyperparameter tuner."""
        self.best_params: Dict[str, Dict[str, Any]] = {}
        self.best_scores: Dict[str, float] = {}
        self.study_history: Dict[str, optuna.Study] = {}
        logger.info("Hyperparameter tuner initialized")

    def tune_xgboost(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> Dict[str, Any]:
        """
        Tune XGBoost hyperparameters.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels

        Returns:
            Dictionary with best parameters and score

        Raises:
            TrainingError: If tuning fails
        """
        with tracer.start_as_current_span("tune_xgboost") as span:
            span.set_attribute("num_trials", config.hyperparameter_tuning.n_trials)

            try:
                logger.info(
                    f"Starting XGBoost hyperparameter tuning with "
                    f"{config.hyperparameter_tuning.n_trials} trials"
                )

                def objective(trial: optuna.Trial) -> float:
                    """Objective function for Optuna."""
                    # Suggest hyperparameters
                    max_depth = trial.suggest_int("max_depth", 3, 10)
                    learning_rate = trial.suggest_float("learning_rate", 0.01, 0.3)
                    subsample = trial.suggest_float("subsample", 0.5, 1.0)
                    colsample_bytree = trial.suggest_float("colsample_bytree", 0.5, 1.0)

                    # Create and train model
                    model = XGBoostModel()
                    model.set_model_params({
                        "max_depth": max_depth,
                        "learning_rate": learning_rate,
                        "subsample": subsample,
                        "colsample_bytree": colsample_bytree,
                    })

                    model.train(X_train, y_train, X_val, y_val)

                    # Evaluate on validation set
                    y_pred_proba = model.predict_proba(X_val)[:, 1]
                    auc_score = roc_auc_score(y_val, y_pred_proba)

                    return auc_score

                # Create study
                sampler = TPESampler(seed=config.training.random_seed)
                study = optuna.create_study(
                    direction="maximize",
                    sampler=sampler,
                )

                # Optimize
                study.optimize(
                    objective,
                    n_trials=config.hyperparameter_tuning.n_trials,
                    show_progress_bar=True,
                )

                # Store results
                self.best_params["xgboost"] = study.best_params
                self.best_scores["xgboost"] = study.best_value
                self.study_history["xgboost"] = study

                result = {
                    "model_type": "xgboost",
                    "best_params": study.best_params,
                    "best_score": study.best_value,
                    "n_trials": len(study.trials),
                }

                logger.info(f"XGBoost tuning complete: {result}")
                metrics.record_hyperparameter_tuning("xgboost")

                return result

            except Exception as e:
                logger.error(f"XGBoost tuning failed: {e}")
                raise TrainingError(
                    f"XGBoost tuning failed: {e}",
                    model_name="xgboost",
                )

    def tune_logistic_regression(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> Dict[str, Any]:
        """
        Tune Logistic Regression hyperparameters.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels

        Returns:
            Dictionary with best parameters and score

        Raises:
            TrainingError: If tuning fails
        """
        with tracer.start_as_current_span("tune_logistic_regression"):
            try:
                logger.info(
                    f"Starting Logistic Regression hyperparameter tuning with "
                    f"{config.hyperparameter_tuning.n_trials} trials"
                )

                def objective(trial: optuna.Trial) -> float:
                    """Objective function for Optuna."""
                    # Suggest hyperparameters
                    C = trial.suggest_float("C", 0.001, 100.0, log=True)

                    # Create and train model
                    model = LogisticRegressionModel()
                    model.set_model_params({"C": C})

                    model.train(X_train, y_train, X_val, y_val)

                    # Evaluate on validation set
                    y_pred_proba = model.predict_proba(X_val)[:, 1]
                    auc_score = roc_auc_score(y_val, y_pred_proba)

                    return auc_score

                # Create study
                sampler = TPESampler(seed=config.training.random_seed)
                study = optuna.create_study(
                    direction="maximize",
                    sampler=sampler,
                )

                # Optimize
                study.optimize(
                    objective,
                    n_trials=config.hyperparameter_tuning.n_trials,
                    show_progress_bar=True,
                )

                # Store results
                self.best_params["logistic_regression"] = study.best_params
                self.best_scores["logistic_regression"] = study.best_value
                self.study_history["logistic_regression"] = study

                result = {
                    "model_type": "logistic_regression",
                    "best_params": study.best_params,
                    "best_score": study.best_value,
                    "n_trials": len(study.trials),
                }

                logger.info(f"Logistic Regression tuning complete: {result}")
                metrics.record_hyperparameter_tuning("logistic_regression")

                return result

            except Exception as e:
                logger.error(f"Logistic Regression tuning failed: {e}")
                raise TrainingError(
                    f"Logistic Regression tuning failed: {e}",
                    model_name="logistic_regression",
                )

    def get_best_params(self, model_type: str) -> Optional[Dict[str, Any]]:
        """
        Get best parameters for model type.

        Args:
            model_type: Type of model

        Returns:
            Best parameters or None
        """
        return self.best_params.get(model_type)

    def get_best_score(self, model_type: str) -> Optional[float]:
        """
        Get best score for model type.

        Args:
            model_type: Type of model

        Returns:
            Best score or None
        """
        return self.best_scores.get(model_type)

