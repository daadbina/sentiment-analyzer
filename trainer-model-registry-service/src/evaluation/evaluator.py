"""
Model evaluation and metrics computation.

Computes comprehensive evaluation metrics for model assessment.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
    roc_curve,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    mean_absolute_percentage_error,
)

from src.models.base_model import BaseModel
from src.config import config
from src.exceptions import EvaluationError
from src.utils.trace import get_tracer
from src.metrics import metrics

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class Evaluator:
    """Evaluates model performance."""

    def __init__(self):
        """Initialize evaluator."""
        self.evaluation_results: Dict[str, Dict[str, Any]] = {}
        logger.info("Evaluator initialized")

    def evaluate(
        self,
        model: BaseModel,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_type: str = "unknown",
        task_type: str = "classification",
    ) -> Dict[str, Any]:
        """
        Evaluate model on test set.

        Args:
            model: Trained model
            X_test: Test features
            y_test: Test labels
            model_type: Type of model
            task_type: Type of task (classification or regression)

        Returns:
            Dictionary with evaluation metrics

        Raises:
            EvaluationError: If evaluation fails
        """
        with tracer.start_as_current_span("evaluate") as span:
            span.set_attribute("model_type", model_type)
            span.set_attribute("task_type", task_type)
            span.set_attribute("num_test_samples", len(X_test))

            try:
                logger.info(f"Evaluating {model_type} on {len(X_test)} test samples (task: {task_type})")

                # Get predictions
                y_pred = model.predict(X_test)

                # Compute metrics based on task type
                if task_type == "regression":
                    metrics_dict = self._compute_regression_metrics(
                        y_test, y_pred, model_type
                    )
                else:
                    y_pred_proba = model.predict_proba(X_test)[:, 1]
                    metrics_dict = self._compute_metrics(
                        y_test, y_pred, y_pred_proba, model_type
                    )

                    # Record classification metrics
                    metrics.record_model_auc(metrics_dict["auc"])
                    metrics.record_model_precision(metrics_dict["precision"])
                    metrics.record_model_recall(metrics_dict["recall"])
                    metrics.record_model_f1(metrics_dict["f1"])

                # Store results
                self.evaluation_results[model_type] = metrics_dict

                logger.info(f"Evaluation complete for {model_type}: {metrics_dict}")
                return metrics_dict

            except Exception as e:
                logger.error(f"Evaluation failed: {e}")
                raise EvaluationError(
                    f"Evaluation failed: {e}",
                    model_name=model_type,
                )

    def _find_optimal_threshold(
        self,
        y_true: pd.Series,
        y_pred_proba: np.ndarray,
    ) -> float:
        """
        Find optimal decision threshold that maximizes F1 score.

        Args:
            y_true: True labels
            y_pred_proba: Predicted probabilities for positive class

        Returns:
            Optimal threshold value
        """
        fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)

        # Find threshold that maximizes F1 score
        best_f1 = 0
        best_threshold = 0.5

        for threshold in np.linspace(0, 1, 101):
            y_pred_threshold = (y_pred_proba >= threshold).astype(int)
            f1 = f1_score(y_true, y_pred_threshold, zero_division=0)

            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold

        logger.info(f"Optimal threshold: {best_threshold:.4f} (F1: {best_f1:.4f})")
        return best_threshold

    def _compute_metrics(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray,
        y_pred_proba: np.ndarray,
        model_type: str,
    ) -> Dict[str, Any]:
        """
        Compute evaluation metrics.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_pred_proba: Predicted probabilities
            model_type: Type of model

        Returns:
            Dictionary with metrics

        Raises:
            EvaluationError: If computation fails
        """
        with tracer.start_as_current_span("compute_metrics"):
            try:
                # Log prediction distributions
                logger.info(f"True labels distribution: {pd.Series(y_true).value_counts().to_dict()}")
                logger.info(f"Predicted labels distribution: {pd.Series(y_pred).value_counts().to_dict()}")
                logger.debug(f"Predicted probabilities (class 1) - min: {y_pred_proba.min():.4f}, max: {y_pred_proba.max():.4f}, mean: {y_pred_proba.mean():.4f}")

                # Find optimal threshold
                optimal_threshold = self._find_optimal_threshold(y_true, y_pred_proba)

                # Re-compute predictions using optimal threshold
                y_pred_optimized = (y_pred_proba >= optimal_threshold).astype(int)
                logger.info(f"Using optimized threshold {optimal_threshold:.4f} instead of default 0.5")

                # Classification metrics (using optimized predictions)
                accuracy = accuracy_score(y_true, y_pred_optimized)
                precision = precision_score(y_true, y_pred_optimized, zero_division=0)
                recall = recall_score(y_true, y_pred_optimized, zero_division=0)
                f1 = f1_score(y_true, y_pred_optimized, zero_division=0)

                # AUC-ROC (always uses probabilities, not affected by threshold)
                auc = roc_auc_score(y_true, y_pred_proba)

                # Confusion matrix (using optimized predictions)
                tn, fp, fn, tp = confusion_matrix(y_true, y_pred_optimized).ravel()

                # Specificity
                specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

                metrics_dict = {
                    "model_type": model_type,
                    "accuracy": float(accuracy),
                    "precision": float(precision),
                    "recall": float(recall),
                    "f1": float(f1),
                    "auc": float(auc),
                    "specificity": float(specificity),
                    "true_negatives": int(tn),
                    "false_positives": int(fp),
                    "false_negatives": int(fn),
                    "true_positives": int(tp),
                    "optimal_threshold": float(optimal_threshold),
                }

                logger.info(f"Confusion matrix - TP: {tp}, TN: {tn}, FP: {fp}, FN: {fn}")
                logger.info(f"Computed metrics: {metrics_dict}")
                return metrics_dict

            except Exception as e:
                logger.error(f"Metrics computation failed: {e}")
                raise EvaluationError(
                    f"Metrics computation failed: {e}",
                    model_name=model_type,
                )

    def _compute_regression_metrics(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray,
        model_type: str,
    ) -> Dict[str, Any]:
        """
        Compute regression evaluation metrics.

        Args:
            y_true: True values
            y_pred: Predicted values
            model_type: Type of model

        Returns:
            Dictionary with regression metrics

        Raises:
            EvaluationError: If computation fails
        """
        try:
            logger.info(f"Computing regression metrics for {model_type}")
            logger.info(f"True values - min: {y_true.min():.4f}, max: {y_true.max():.4f}, mean: {y_true.mean():.4f}")
            logger.info(f"Predicted values - min: {y_pred.min():.4f}, max: {y_pred.max():.4f}, mean: {y_pred.mean():.4f}")

            # Compute regression metrics
            mae = mean_absolute_error(y_true, y_pred)
            mse = mean_squared_error(y_true, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_true, y_pred)

            # Compute MAPE (handle division by zero)
            mape = mean_absolute_percentage_error(y_true, y_pred) if (y_true != 0).all() else np.nan

            # Compute additional metrics
            residuals = y_true - y_pred
            mean_residual = np.mean(residuals)
            std_residual = np.std(residuals)

            metrics_dict = {
                "model_type": model_type,
                "mae": float(mae),
                "mse": float(mse),
                "rmse": float(rmse),
                "r2": float(r2),
                "mape": float(mape) if not np.isnan(mape) else None,
                "mean_residual": float(mean_residual),
                "std_residual": float(std_residual),
            }

            logger.info(f"Regression metrics: MAE={mae:.4f}, RMSE={rmse:.4f}, R²={r2:.4f}")
            logger.info(f"Computed regression metrics: {metrics_dict}")
            return metrics_dict

        except Exception as e:
            logger.error(f"Regression metrics computation failed: {e}")
            raise EvaluationError(
                f"Regression metrics computation failed: {e}",
                model_name=model_type,
            )

    def compare_models(
        self,
        models: Dict[str, BaseModel],
        X_test: pd.DataFrame,
        y_test: pd.Series,
        task_type: str = "classification",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare multiple models.

        Args:
            models: Dictionary mapping model types to models
            X_test: Test features
            y_test: Test labels
            task_type: Type of task (classification or regression)

        Returns:
            Dictionary with evaluation results for all models

        Raises:
            EvaluationError: If comparison fails
        """
        with tracer.start_as_current_span("compare_models"):
            try:
                logger.info(f"Comparing {len(models)} models (task: {task_type})")

                results = {}
                for model_type, model in models.items():
                    try:
                        result = self.evaluate(model, X_test, y_test, model_type, task_type)
                        results[model_type] = result
                    except Exception as e:
                        logger.error(f"Failed to evaluate {model_type}: {e}")

                logger.info(
                    f"Model comparison complete: {len(results)} models evaluated"
                )
                return results

            except Exception as e:
                logger.error(f"Model comparison failed: {e}")
                raise EvaluationError(
                    f"Model comparison failed: {e}",
                    model_name="all",
                )

    def get_best_model(self, task_type: str = "classification") -> Optional[tuple]:
        """
        Get best model by AUC (classification) or R² (regression).

        Args:
            task_type: Type of task (classification or regression)

        Returns:
            Tuple of (model_type, metrics) or None

        Raises:
            EvaluationError: If no models evaluated
        """
        with tracer.start_as_current_span("get_best_model"):
            try:
                if not self.evaluation_results:
                    raise EvaluationError(
                        "No models evaluated",
                        model_name="all",
                    )

                # Find best model based on task type
                if task_type == "regression":
                    # Find model with highest R²
                    best_model_type = max(
                        self.evaluation_results.keys(),
                        key=lambda x: self.evaluation_results[x].get("r2", -float('inf')),
                    )
                    best_metrics = self.evaluation_results[best_model_type]
                    logger.info(
                        f"Best model: {best_model_type} with R² {best_metrics.get('r2', 'N/A')}"
                    )
                else:
                    # Find model with highest AUC
                    best_model_type = max(
                        self.evaluation_results.keys(),
                        key=lambda x: self.evaluation_results[x].get("auc", 0),
                    )
                    best_metrics = self.evaluation_results[best_model_type]
                    logger.info(
                        f"Best model: {best_model_type} with AUC {best_metrics.get('auc', 'N/A')}"
                    )

                return best_model_type, best_metrics

            except Exception as e:
                logger.error(f"Failed to get best model: {e}")
                raise EvaluationError(
                    f"Failed to get best model: {e}",
                    model_name="all",
                )

    def get_evaluation_results(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all evaluation results.

        Returns:
            Dictionary with evaluation results
        """
        return self.evaluation_results
