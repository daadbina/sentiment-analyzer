"""
Feature Quality Monitor for Predictor Online Inference Service.

Tracks feature freshness, reconciliation rate, and alerts on
missing or stale features.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from ..metrics import MetricsCollector
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class FeatureQualityMonitor:
    """
    Monitor for tracking feature quality metrics.

    Tracks feature freshness, reconciliation rate, missing features,
    and stale features with alerting.
    """

    def __init__(
        self,
        metrics: MetricsCollector,
        freshness_threshold_seconds: int = 3600  # 1 hour
    ):
        """
        Initialize feature quality monitor.

        Args:
            metrics: Metrics collector
            freshness_threshold_seconds: Freshness threshold in seconds
        """
        self.metrics = metrics
        self.freshness_threshold_seconds = freshness_threshold_seconds
        self._feature_fetch_history: list[dict[str, Any]] = []
        self._missing_features_count: dict[str, int] = defaultdict(int)
        self._stale_features_count: dict[str, int] = defaultdict(int)

        logger.info(
            "Initialized FeatureQualityMonitor",
            extra={"freshness_threshold_seconds": freshness_threshold_seconds}
        )

    @trace_span("feature_quality_monitor.track_feature_fetch")
    def track_feature_fetch(
        self,
        group_id: str,
        features: dict[str, Any],
        feature_timestamp: datetime | None = None,
        trace_id: str | None = None
    ) -> dict[str, Any]:
        """
        Track a feature fetch operation.

        Args:
            group_id: Semantic group ID
            features: Fetched features
            feature_timestamp: Timestamp of features
            trace_id: Trace ID for correlation

        Returns:
            Quality metrics for this fetch
        """
        try:
            fetch_time = datetime.now()

            # Check feature freshness
            if feature_timestamp:
                age_seconds = (fetch_time - feature_timestamp).total_seconds()
                is_fresh = age_seconds <= self.freshness_threshold_seconds
            else:
                age_seconds = None
                is_fresh = True  # Assume fresh if no timestamp

            # Check for missing features
            expected_features = [
                "feature_num_sources",
                "feature_sentiment_mean",
                "feature_credibility_mean",
                "feature_entities",
                "feature_time_density"
            ]

            missing_features = [
                f for f in expected_features
                if f not in features or features[f] is None
            ]

            # Record fetch
            fetch_record = {
                "group_id": group_id,
                "fetch_time": fetch_time.isoformat(),
                "feature_timestamp": feature_timestamp.isoformat() if feature_timestamp else None,
                "age_seconds": age_seconds,
                "is_fresh": is_fresh,
                "missing_features": missing_features,
                "feature_count": len(features),
                "trace_id": trace_id
            }

            self._feature_fetch_history.append(fetch_record)

            # Update missing features count
            for feature in missing_features:
                self._missing_features_count[feature] += 1

            # Update stale features count
            if not is_fresh:
                self._stale_features_count[group_id] += 1

                # Alert on stale features
                logger.warning(
                    "Stale features detected",
                    extra={
                        "group_id": group_id,
                        "age_seconds": age_seconds,
                        "threshold_seconds": self.freshness_threshold_seconds,
                        "trace_id": trace_id
                    }
                )

                self.metrics.increment_stale_features_total()

            # Alert on missing features
            if missing_features:
                logger.warning(
                    "Missing features detected",
                    extra={
                        "group_id": group_id,
                        "missing_features": missing_features,
                        "trace_id": trace_id
                    }
                )

                self.metrics.increment_missing_features_total(len(missing_features))

            # Record metrics
            if age_seconds is not None:
                self.metrics.record_feature_age(age_seconds)

            logger.debug(
                "Tracked feature fetch",
                extra={
                    "group_id": group_id,
                    "is_fresh": is_fresh,
                    "missing_count": len(missing_features),
                    "trace_id": trace_id
                }
            )

            return {
                "is_fresh": is_fresh,
                "age_seconds": age_seconds,
                "missing_features": missing_features,
                "quality_score": self._calculate_quality_score(
                    is_fresh, len(missing_features), len(expected_features)
                )
            }

        except Exception as e:
            logger.error(
                "Failed to track feature fetch",
                extra={
                    "group_id": group_id,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            return {
                "is_fresh": False,
                "age_seconds": None,
                "missing_features": [],
                "quality_score": 0.0
            }

    def _calculate_quality_score(
        self,
        is_fresh: bool,
        missing_count: int,
        total_features: int
    ) -> float:
        """
        Calculate feature quality score.

        Args:
            is_fresh: Whether features are fresh
            missing_count: Number of missing features
            total_features: Total expected features

        Returns:
            Quality score [0, 1]
        """
        # Freshness component (50% weight)
        freshness_score = 1.0 if is_fresh else 0.0

        # Completeness component (50% weight)
        completeness_score = 1.0 - (missing_count / total_features)

        # Combined score
        return 0.5 * freshness_score + 0.5 * completeness_score


    def get_feature_freshness_rate(
        self,
        time_window_hours: int | None = None,
        trace_id: str | None = None
    ) -> float:
        """
        Get feature freshness rate over time window.

        Args:
            time_window_hours: Time window in hours (None = all history)
            trace_id: Trace ID for correlation

        Returns:
            Freshness rate [0, 1]
        """
        try:
            # Filter by time window
            if time_window_hours:
                cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
                relevant_fetches = [
                    f for f in self._feature_fetch_history
                    if datetime.fromisoformat(f["fetch_time"]) >= cutoff_time
                ]
            else:
                relevant_fetches = self._feature_fetch_history

            if not relevant_fetches:
                return 0.0

            fresh_count = sum(1 for f in relevant_fetches if f["is_fresh"])
            freshness_rate = fresh_count / len(relevant_fetches)

            logger.debug(
                "Calculated feature freshness rate",
                extra={
                    "freshness_rate": freshness_rate,
                    "fresh_count": fresh_count,
                    "total_count": len(relevant_fetches),
                    "time_window_hours": time_window_hours,
                    "trace_id": trace_id
                }
            )

            return freshness_rate

        except Exception as e:
            logger.error(
                "Failed to calculate feature freshness rate",
                extra={
                    "time_window_hours": time_window_hours,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            return 0.0

    def get_feature_reconciliation_rate(
        self,
        trace_id: str | None = None
    ) -> float:
        """
        Get feature reconciliation rate.

        This would compare offline vs online features.
        For now, returns a placeholder.

        Args:
            trace_id: Trace ID for correlation

        Returns:
            Reconciliation rate [0, 1]
        """
        # TODO: Implement actual reconciliation logic
        # This requires comparing offline and online feature values

        logger.debug(
            "Feature reconciliation rate requested",
            extra={"trace_id": trace_id}
        )

        return 0.99  # Placeholder

    def generate_quality_report(
        self,
        time_window_hours: int = 24,
        trace_id: str | None = None
    ) -> dict[str, Any]:
        """
        Generate feature quality report.

        Args:
            time_window_hours: Time window in hours
            trace_id: Trace ID for correlation

        Returns:
            Quality report dictionary
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            relevant_fetches = [
                f for f in self._feature_fetch_history
                if datetime.fromisoformat(f["fetch_time"]) >= cutoff_time
            ]

            if not relevant_fetches:
                return {
                    "time_window_hours": time_window_hours,
                    "total_fetches": 0,
                    "freshness_rate": 0.0,
                    "missing_features_by_name": {},
                    "stale_features_count": 0
                }

            # Calculate metrics
            fresh_count = sum(1 for f in relevant_fetches if f["is_fresh"])
            freshness_rate = fresh_count / len(relevant_fetches)

            # Count missing features by name
            missing_by_name = defaultdict(int)
            for fetch in relevant_fetches:
                for feature in fetch["missing_features"]:
                    missing_by_name[feature] += 1

            # Count stale features
            stale_count = sum(1 for f in relevant_fetches if not f["is_fresh"])

            report = {
                "time_window_hours": time_window_hours,
                "total_fetches": len(relevant_fetches),
                "fresh_fetches": fresh_count,
                "stale_fetches": stale_count,
                "freshness_rate": freshness_rate,
                "missing_features_by_name": dict(missing_by_name),
                "total_missing_features": sum(missing_by_name.values()),
                "generated_at": datetime.now().isoformat()
            }

            logger.info(
                "Generated feature quality report",
                extra={**report, "trace_id": trace_id}
            )

            return report

        except Exception as e:
            logger.error(
                "Failed to generate quality report",
                extra={
                    "time_window_hours": time_window_hours,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            return {
                "time_window_hours": time_window_hours,
                "error": str(e)
            }

    def clear_history(self, older_than_hours: int | None = None) -> int:
        """
        Clear feature fetch history.

        Args:
            older_than_hours: Clear entries older than this (None = clear all)

        Returns:
            Number of entries cleared
        """
        if older_than_hours is None:
            count = len(self._feature_fetch_history)
            self._feature_fetch_history.clear()
            self._missing_features_count.clear()
            self._stale_features_count.clear()
            logger.info(f"Cleared all feature fetch history: {count} entries")
            return count

        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        original_count = len(self._feature_fetch_history)

        self._feature_fetch_history = [
            f for f in self._feature_fetch_history
            if datetime.fromisoformat(f["fetch_time"]) >= cutoff_time
        ]

        cleared_count = original_count - len(self._feature_fetch_history)

        logger.info(
            "Cleared old feature fetch history",
            extra={
                "cleared_count": cleared_count,
                "remaining_count": len(self._feature_fetch_history),
                "older_than_hours": older_than_hours
            }
        )

        return cleared_count

