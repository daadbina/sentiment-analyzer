"""Label reconciliation engine."""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from src.config import config
from src.exceptions import ReconciliationError
from src.utils.trace import get_logger


logger = get_logger(__name__, config.logging.log_level)


class TemporalMatcher:
    """Temporal matching for labels and semantic groups."""

    def __init__(self, threshold_hours: int = 48):
        """Initialize temporal matcher."""
        self.threshold_hours = threshold_hours

    @staticmethod
    def parse_timestamp(ts: Union[str, int, float]) -> Optional[datetime]:
        """Parse timestamp from various formats.

        Args:
            ts: Timestamp as ISO string, Unix timestamp (int/float), or other format

        Returns:
            datetime object (always offset-aware with UTC timezone) or None if parsing fails
        """
        if not ts:
            return None

        try:
            # Try Unix timestamp (int or float)
            if isinstance(ts, (int, float)):
                return datetime.fromtimestamp(ts, tz=timezone.utc)

            # Try ISO format string
            if isinstance(ts, str):
                # Handle ISO format with Z suffix
                ts_clean = ts.replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts_clean)

                # Ensure the datetime is offset-aware (has timezone info)
                if dt.tzinfo is None:
                    # If no timezone info, assume UTC
                    dt = dt.replace(tzinfo=timezone.utc)

                return dt

            return None

        except Exception as e:
            logger.debug(f"Failed to parse timestamp {ts}: {str(e)}")
            return None

    def match(
        self,
        label_timestamp: Union[str, int, float],
        group_timestamp: Union[str, int, float]
    ) -> Tuple[bool, float]:
        """
        Match label and group by temporal proximity.

        Returns:
            Tuple of (matched: bool, confidence: float)
        """
        try:
            label_dt = self.parse_timestamp(label_timestamp)
            group_dt = self.parse_timestamp(group_timestamp)

            if not label_dt or not group_dt:
                logger.debug(
                    f"Could not parse timestamps",
                    operation="temporal_match",
                    label_ts=label_timestamp,
                    group_ts=group_timestamp
                )
                return False, 0.0

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

    def __init__(self, similarity_threshold: float = 0.3):
        """Initialize semantic matcher.

        Args:
            similarity_threshold: Minimum Jaccard similarity for match (default 0.3 for lenient matching)
        """
        self.similarity_threshold = similarity_threshold

    def match(
        self,
        label_description: str,
        group_description: str
    ) -> Tuple[bool, float]:
        """
        Match label and group by semantic similarity using Jaccard index.

        Uses lenient keyword-based matching to handle diverse label formats.
        Returns confidence based on word overlap between label and group descriptions.

        Returns:
            Tuple of (matched: bool, confidence: float)
        """
        try:
            # Extract words and filter out common stop words
            label_words = set(w.lower() for w in label_description.split() if len(w) > 2)
            group_words = set(w.lower() for w in group_description.split() if len(w) > 2)

            if not label_words or not group_words:
                # If either is empty, return low confidence but don't reject
                return False, 0.1

            # Calculate Jaccard similarity
            intersection = len(label_words & group_words)
            union = len(label_words | group_words)

            similarity = intersection / union if union > 0 else 0.0

            # Match if similarity meets threshold
            matched = similarity >= self.similarity_threshold

            logger.debug(
                f"Semantic matching result",
                operation="semantic_match",
                label_words=len(label_words),
                group_words=len(group_words),
                intersection=intersection,
                similarity=similarity,
                matched=matched
            )

            return matched, similarity

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

            # Use event_timestamp (actual event time) instead of fetched_at (when fetched from API)
            label_timestamp = label.get("event_timestamp") or label.get("fetched_at", "")

            if not label_timestamp:
                logger.warning(
                    f"Label has no timestamp for reconciliation",
                    operation="reconcile",
                    event_id=label.get("event_id")
                )
                return None

            for group in semantic_groups:
                # Temporal matching using event_timestamp
                temporal_match, temporal_conf = self.temporal_matcher.match(
                    label_timestamp,
                    group.get("created_at", "")
                )

                if not temporal_match:
                    continue

                # Semantic matching - try multiple description fields
                label_description = (
                    label.get("description") or
                    label.get("title") or
                    label.get("event_type") or
                    ""
                )
                # Try multiple fields for group description (topic_label might be null)
                group_description = (
                    group.get("topic_label") or
                    group.get("cluster_metadata", {}).get("topic_label") or
                    ""
                )

                semantic_match, semantic_conf = self.semantic_matcher.match(
                    label_description,
                    group_description
                )

                # Combined confidence
                combined_confidence = (temporal_conf * 0.5) + (semantic_conf * 0.5)

                # Debug logging for first few matches
                if best_confidence < 0.1:  # Log first few attempts
                    logger.debug(
                        f"Reconciliation attempt",
                        operation="reconcile",
                        event_id=label.get("event_id"),
                        group_id=group.get("group_id"),
                        label_desc=label_description[:100] if label_description else "EMPTY",
                        group_desc=group_description[:100] if group_description else "EMPTY",
                        temporal_conf=temporal_conf,
                        semantic_conf=semantic_conf,
                        combined_conf=combined_confidence
                    )

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
                    event_id=label.get("event_id"),
                    group_id=best_match["group_id"],
                    confidence=best_confidence,
                    temporal_conf=best_match["temporal_confidence"],
                    semantic_conf=best_match["semantic_confidence"]
                )
                return best_match
            else:
                logger.warning(
                    f"No matching group found for label",
                    operation="reconcile",
                    event_id=label.get("event_id"),
                    best_confidence=best_confidence
                )
                return None

        except Exception as e:
            logger.error(
                f"Reconciliation failed: {str(e)}",
                operation="reconcile",
                event_id=label.get("event_id"),
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

