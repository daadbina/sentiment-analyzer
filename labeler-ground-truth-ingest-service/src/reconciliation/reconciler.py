"""Label reconciliation engine."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from src.config import config
from src.exceptions import ReconciliationError
from src.utils.trace import get_logger


logger = get_logger(__name__, config.logging.log_level)


class TemporalMatcher:
    """Temporal matching for labels and semantic groups."""

    def __init__(self, threshold_hours: int = 48):
        """Initialize temporal matcher."""
        self.threshold_hours = threshold_hours

    def match(
        self,
        label_timestamp: str,
        group_timestamp: str
    ) -> Tuple[bool, float]:
        """
        Match label and group by temporal proximity.

        Returns:
            Tuple of (matched: bool, confidence: float)
        """
        try:
            label_dt = datetime.fromisoformat(label_timestamp.replace("Z", "+00:00"))
            group_dt = datetime.fromisoformat(group_timestamp.replace("Z", "+00:00"))

            time_diff = abs((label_dt - group_dt).total_seconds() / 3600)  # hours

            if time_diff <= self.threshold_hours:
                # Confidence decreases with time difference
                confidence = 1.0 - (time_diff / self.threshold_hours) * 0.5
                return True, confidence
            else:
                return False, 0.0

        except Exception as e:
            logger.error(
                f"Temporal matching failed: {str(e)}",
                operation="temporal_match",
                error_type=type(e).__name__
            )
            return False, 0.0


class SemanticMatcher:
    """Semantic matching for labels and semantic groups."""

    def __init__(self, similarity_threshold: float = 0.85):
        """Initialize semantic matcher."""
        self.similarity_threshold = similarity_threshold

    def match(
        self,
        label_description: str,
        group_description: str
    ) -> Tuple[bool, float]:
        """
        Match label and group by semantic similarity.

        Returns:
            Tuple of (matched: bool, confidence: float)
        """
        try:
            # Simple keyword-based matching
            label_words = set(label_description.lower().split())
            group_words = set(group_description.lower().split())

            if not label_words or not group_words:
                return False, 0.0

            intersection = len(label_words & group_words)
            union = len(label_words | group_words)

            similarity = intersection / union if union > 0 else 0.0

            if similarity >= self.similarity_threshold:
                return True, similarity
            else:
                return False, similarity

        except Exception as e:
            logger.error(
                f"Semantic matching failed: {str(e)}",
                operation="semantic_match",
                error_type=type(e).__name__
            )
            return False, 0.0


class LabelReconciler:
    """Reconcile labels with semantic groups."""

    def __init__(self):
        """Initialize label reconciler."""
        self.temporal_matcher = TemporalMatcher(
            threshold_hours=config.label.reconciliation_threshold_hours
        )
        self.semantic_matcher = SemanticMatcher(
            similarity_threshold=config.label.confidence_threshold
        )

    async def reconcile(
        self,
        label: Dict[str, Any],
        semantic_groups: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Reconcile label with semantic groups.

        Returns:
            Reconciliation result with group_id and confidence, or None if no match
        """
        try:
            best_match = None
            best_confidence = 0.0

            for group in semantic_groups:
                # Temporal matching
                temporal_match, temporal_conf = self.temporal_matcher.match(
                    label.get("fetched_at", ""),
                    group.get("created_at", "")
                )

                if not temporal_match:
                    continue

                # Semantic matching
                semantic_match, semantic_conf = self.semantic_matcher.match(
                    label.get("description", ""),
                    group.get("topic_label", "")
                )

                # Combined confidence
                combined_confidence = (temporal_conf * 0.5) + (semantic_conf * 0.5)

                if combined_confidence > best_confidence:
                    best_confidence = combined_confidence
                    best_match = {
                        "group_id": group.get("group_id"),
                        "confidence": combined_confidence,
                        "temporal_confidence": temporal_conf,
                        "semantic_confidence": semantic_conf
                    }

            if best_match and best_confidence >= config.reconciliation.confidence_threshold:
                logger.info(
                    f"Label reconciled successfully",
                    operation="reconcile",
                    group_id=best_match["group_id"],
                    confidence=best_confidence
                )
                return best_match
            else:
                logger.warning(
                    f"No matching group found for label",
                    operation="reconcile",
                    best_confidence=best_confidence
                )
                return None

        except Exception as e:
            logger.error(
                f"Reconciliation failed: {str(e)}",
                operation="reconcile",
                error_type=type(e).__name__
            )
            raise ReconciliationError(
                label.get("event_id", "unknown"),
                "unknown",
                str(e)
            )

    async def reconcile_batch(
        self,
        labels: List[Dict[str, Any]],
        semantic_groups: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Reconcile batch of labels."""
        results = []

        for label in labels:
            result = await self.reconcile(label, semantic_groups)
            if result:
                result["label"] = label
                results.append(result)

        logger.info(
            f"Batch reconciliation completed",
            operation="reconcile_batch",
            total_labels=len(labels),
            matched_labels=len(results)
        )

        return results

