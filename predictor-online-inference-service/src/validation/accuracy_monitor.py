"""
Accuracy monitor for tracking prediction accuracy against ground-truth labels.

Computes label consistency metric and tracks model performance.
Implements validation requirements from Architecture.md.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..validation.label_retriever import LabelRetriever
from ..utils.trace import trace_span
from ..metrics import MetricsCollector


logger = logging.getLogger(__name__)


class AccuracyMonitor:
    """
    Monitor for tracking prediction accuracy.
    
    Computes label consistency and tracks model performance over time.
    """
    
    def __init__(
        self,
        label_retriever: LabelRetriever,
        consistency_threshold: float = 0.85,
    ):
        """
        Initialize accuracy monitor.
        
        Args:
            label_retriever: Label retriever instance
            consistency_threshold: Target label consistency (≥0.85)
        """
        self.label_retriever = label_retriever
        self.consistency_threshold = consistency_threshold
        
        logger.info(
            f"Initialized accuracy monitor: consistency_threshold={consistency_threshold}"
        )
    
    async def compute_label_consistency(
        self,
        hours: int = 24,
        trace_id: Optional[str] = None,
    ) -> float:
        """
        Compute label consistency for recent predictions.
        
        Label consistency is the percentage of predictions that match
        ground-truth labels (within tolerance).
        
        Args:
            hours: Number of hours to look back
            trace_id: Optional trace ID for distributed tracing
        
        Returns:
            Label consistency score (0.0-1.0)
        """
        with trace_span(
            "compute_label_consistency",
            attributes={"hours": hours, "trace_id": trace_id},
        ):
            try:
                # Get recent predictions with labels
                labeled_predictions = await self.label_retriever.get_recent_labels(
                    hours=hours,
                    trace_id=trace_id,
                )
                
                if not labeled_predictions:
                    logger.warning(
                        f"No labeled predictions found in last {hours} hours",
                        extra={"trace_id": trace_id},
                    )
                    return 0.0
                
                # Compute consistency
                total = len(labeled_predictions)
                consistent = 0
                
                for pred in labeled_predictions:
                    prediction_probability = pred["prediction_probability"]
                    label_value = pred["label_value"]
                    
                    # Convert probability to binary prediction (threshold 0.5)
                    predicted_class = 1.0 if prediction_probability >= 0.5 else 0.0
                    
                    # Check if prediction matches label
                    if predicted_class == label_value:
                        consistent += 1
                
                consistency = consistent / total if total > 0 else 0.0
                
                # Record metric
                MetricsCollector.record_label_consistency(consistency)
                
                logger.info(
                    f"Label consistency computed: consistency={consistency:.4f}, "
                    f"total={total}, consistent={consistent}",
                    extra={"trace_id": trace_id},
                )
                
                # Check if consistency meets threshold
                if consistency < self.consistency_threshold:
                    logger.warning(
                        f"Label consistency below threshold: {consistency:.4f} < {self.consistency_threshold}",
                        extra={"trace_id": trace_id},
                    )
                
                return consistency
                
            except Exception as e:
                logger.error(
                    f"Failed to compute label consistency: error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                return 0.0
    
    async def compute_model_accuracy(
        self,
        model_version: str,
        hours: int = 24,
        trace_id: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Compute accuracy metrics for a specific model version.
        
        Args:
            model_version: Model version to evaluate
            hours: Number of hours to look back
            trace_id: Optional trace ID for distributed tracing
        
        Returns:
            Dictionary containing accuracy metrics:
                - accuracy: Overall accuracy
                - precision: Precision for positive class
                - recall: Recall for positive class
                - f1_score: F1 score
        """
        with trace_span(
            "compute_model_accuracy",
            attributes={"model_version": model_version, "hours": hours, "trace_id": trace_id},
        ):
            try:
                # Get recent predictions with labels
                labeled_predictions = await self.label_retriever.get_recent_labels(
                    hours=hours,
                    trace_id=trace_id,
                )
                
                # Filter by model version
                model_predictions = [
                    p for p in labeled_predictions
                    if p["model_version"] == model_version
                ]
                
                if not model_predictions:
                    logger.warning(
                        f"No labeled predictions found for model {model_version}",
                        extra={"trace_id": trace_id, "model_version": model_version},
                    )
                    return {
                        "accuracy": 0.0,
                        "precision": 0.0,
                        "recall": 0.0,
                        "f1_score": 0.0,
                    }
                
                # Compute confusion matrix
                tp = 0  # True positives
                fp = 0  # False positives
                tn = 0  # True negatives
                fn = 0  # False negatives
                
                for pred in model_predictions:
                    prediction_probability = pred["prediction_probability"]
                    label_value = pred["label_value"]
                    
                    # Convert probability to binary prediction
                    predicted_class = 1.0 if prediction_probability >= 0.5 else 0.0
                    
                    if predicted_class == 1.0 and label_value == 1.0:
                        tp += 1
                    elif predicted_class == 1.0 and label_value == 0.0:
                        fp += 1
                    elif predicted_class == 0.0 and label_value == 0.0:
                        tn += 1
                    elif predicted_class == 0.0 and label_value == 1.0:
                        fn += 1
                
                # Compute metrics
                total = tp + fp + tn + fn
                accuracy = (tp + tn) / total if total > 0 else 0.0
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                f1_score = (
                    2 * (precision * recall) / (precision + recall)
                    if (precision + recall) > 0
                    else 0.0
                )
                
                metrics = {
                    "accuracy": accuracy,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1_score,
                }
                
                logger.info(
                    f"Model accuracy computed: model_version={model_version}, "
                    f"accuracy={accuracy:.4f}, precision={precision:.4f}, "
                    f"recall={recall:.4f}, f1_score={f1_score:.4f}",
                    extra={"trace_id": trace_id, "model_version": model_version},
                )
                
                return metrics
                
            except Exception as e:
                logger.error(
                    f"Failed to compute model accuracy: model_version={model_version}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                return {
                    "accuracy": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0,
                }

