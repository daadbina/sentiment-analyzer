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
    ) -> Dict[str, Any]:
        """
        Evaluate model on test set.

        Args:
            model: Trained model
            X_test: Test features
            y_test: Test labels
            model_type: Type of model

        Returns:
            Dictionary with evaluation metrics

        Raises:
            EvaluationError: If evaluation fails
        """
        with tracer.start_as_current_span("evaluate") as span:
            span.set_attribute("model_type", model_type)
            span.set_attribute("num_test_samples", len(X_test))

            try:
                logger.info(f"Evaluating {model_type} on {len(X_test)} test samples")

                # Get predictions
                y_pred = model.predict(X_test)
                y_pred_proba = model.predict_proba(X_test)[:, 1]

                # Compute metrics
                metrics_dict = self._compute_metrics(
                    y_test, y_pred, y_pred_proba, model_type
                )

                # Store results
                self.evaluation_results[model_type] = metrics_dict

                # Record metrics
                metrics.record_model_auc(metrics_dict["auc"])
                metrics.record_model_precision(metrics_dict["precision"])
                metrics.record_model_recall(metrics_dict["recall"])
                metrics.record_model_f1(metrics_dict["f1"])

                logger.info(f"Evaluation complete for {model_type}: {metrics_dict}")
                return metrics_dict

            except Exception as e:
                logger.error(f"Evaluation failed: {e}")
                raise EvaluationError(
                    f"Evaluation failed: {e}",
                    model_name=model_type,
                )

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

                # Classification metrics
                accuracy = accuracy_score(y_true, y_pred)
                precision = precision_score(y_true, y_pred, zero_division=0)
                recall = recall_score(y_true, y_pred, zero_division=0)
                f1 = f1_score(y_true, y_pred, zero_division=0)

                # AUC-ROC
                auc = roc_auc_score(y_true, y_pred_proba)

                # Confusion matrix
                tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

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

    def compare_models(
        self,
        models: Dict[str, BaseModel],
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare multiple models.

        Args:
            models: Dictionary mapping model types to models
            X_test: Test features
            y_test: Test labels

        Returns:
            Dictionary with evaluation results for all models

        Raises:
            EvaluationError: If comparison fails
        """
        with tracer.start_as_current_span("compare_models"):
            try:
                logger.info(f"Comparing {len(models)} models")

                results = {}
                for model_type, model in models.items():
                    try:
                        result = self.evaluate(model, X_test, y_test, model_type)
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

    def get_best_model(self) -> Optional[tuple]:
        """
        Get best model by AUC.

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

                # Find model with highest AUC
                best_model_type = max(
                    self.evaluation_results.keys(),
                    key=lambda x: self.evaluation_results[x]["auc"],
                )

                best_metrics = self.evaluation_results[best_model_type]
                logger.info(
                    f"Best model: {best_model_type} with AUC {best_metrics['auc']}"
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
