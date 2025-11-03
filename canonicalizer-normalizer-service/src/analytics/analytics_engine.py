"""Real-time analytics engine."""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesMetric:
    """Time series metric data."""

    timestamp: datetime
    value: float
    label: Optional[str] = None


@dataclass
class AnalyticsSnapshot:
    """Analytics snapshot at a point in time."""

    timestamp: datetime
    total_messages_processed: int = 0
    total_messages_accepted: int = 0
    total_messages_rejected: int = 0
    total_messages_review: int = 0
    average_processing_time_ms: float = 0.0
    error_rate: float = 0.0
    throughput_msg_per_sec: float = 0.0
    domain_distribution: Dict[str, int] = field(default_factory=dict)
    publisher_distribution: Dict[str, int] = field(default_factory=dict)
    cache_hit_rate: float = 0.0
    deduplication_rate: float = 0.0


class RealTimeAnalytics:
    """Real-time analytics engine for pipeline monitoring."""

    def __init__(self, window_size_seconds: int = 60, max_history: int = 1440):
        """Initialize analytics engine.

        Args:
            window_size_seconds: Time window for aggregation
            max_history: Maximum history to keep (in windows)
        """
        self.window_size_seconds = window_size_seconds
        self.max_history = max_history

        # Counters
        self.total_messages_processed = 0
        self.total_messages_accepted = 0
        self.total_messages_rejected = 0
        self.total_messages_review = 0
        self.total_errors = 0

        # Time series data
        self.processing_times: List[TimeSeriesMetric] = []
        self.throughput_metrics: List[TimeSeriesMetric] = []
        self.error_rate_metrics: List[TimeSeriesMetric] = []

        # Distributions
        self.domain_distribution: Dict[str, int] = defaultdict(int)
        self.publisher_distribution: Dict[str, int] = defaultdict(int)

        # Performance metrics
        self.cache_hits = 0
        self.cache_misses = 0
        self.deduplication_hits = 0

        # Snapshots
        self.snapshots: List[AnalyticsSnapshot] = []

    def record_message_processed(
        self,
        processing_time_ms: float,
        domain: Optional[str] = None,
        publisher: Optional[str] = None,
    ) -> None:
        """Record processed message.

        Args:
            processing_time_ms: Processing time in milliseconds
            domain: Message domain
            publisher: Message publisher
        """
        self.total_messages_processed += 1

        # Record processing time
        self.processing_times.append(
            TimeSeriesMetric(
                timestamp=datetime.now(timezone.utc),
                value=processing_time_ms,
            )
        )

        # Record domain distribution
        if domain:
            self.domain_distribution[domain] += 1

        # Record publisher distribution
        if publisher:
            self.publisher_distribution[publisher] += 1

    def record_message_accepted(self) -> None:
        """Record accepted message."""
        self.total_messages_accepted += 1

    def record_message_rejected(self) -> None:
        """Record rejected message."""
        self.total_messages_rejected += 1

    def record_message_review(self) -> None:
        """Record message for review."""
        self.total_messages_review += 1

    def record_error(self) -> None:
        """Record error."""
        self.total_errors += 1

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record cache miss."""
        self.cache_misses += 1

    def record_deduplication_hit(self) -> None:
        """Record deduplication hit."""
        self.deduplication_hits += 1

    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate.

        Returns:
            Cache hit rate (0.0-1.0)
        """
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def get_error_rate(self) -> float:
        """Get error rate.

        Returns:
            Error rate (0.0-1.0)
        """
        if self.total_messages_processed == 0:
            return 0.0
        return self.total_errors / self.total_messages_processed

    def get_deduplication_rate(self) -> float:
        """Get deduplication rate.

        Returns:
            Deduplication rate (0.0-1.0)
        """
        if self.total_messages_processed == 0:
            return 0.0
        return self.deduplication_hits / self.total_messages_processed

    def get_average_processing_time(self) -> float:
        """Get average processing time.

        Returns:
            Average processing time in milliseconds
        """
        if not self.processing_times:
            return 0.0
        return sum(m.value for m in self.processing_times) / len(self.processing_times)

    def get_throughput(self) -> float:
        """Get throughput.

        Returns:
            Messages per second
        """
        if not self.processing_times:
            return 0.0

        oldest = min(m.timestamp for m in self.processing_times)
        newest = max(m.timestamp for m in self.processing_times)
        duration = (newest - oldest).total_seconds()

        if duration == 0:
            return 0.0

        return len(self.processing_times) / duration

    def get_snapshot(self) -> AnalyticsSnapshot:
        """Get current analytics snapshot.

        Returns:
            Analytics snapshot
        """
        snapshot = AnalyticsSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_messages_processed=self.total_messages_processed,
            total_messages_accepted=self.total_messages_accepted,
            total_messages_rejected=self.total_messages_rejected,
            total_messages_review=self.total_messages_review,
            average_processing_time_ms=self.get_average_processing_time(),
            error_rate=self.get_error_rate(),
            throughput_msg_per_sec=self.get_throughput(),
            domain_distribution=dict(self.domain_distribution),
            publisher_distribution=dict(self.publisher_distribution),
            cache_hit_rate=self.get_cache_hit_rate(),
            deduplication_rate=self.get_deduplication_rate(),
        )

        self.snapshots.append(snapshot)

        # Keep only recent snapshots
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            seconds=self.window_size_seconds * self.max_history
        )
        self.snapshots = [s for s in self.snapshots if s.timestamp > cutoff_time]

        return snapshot

    def get_recent_snapshots(self, count: int = 10) -> List[AnalyticsSnapshot]:
        """Get recent snapshots.

        Args:
            count: Number of snapshots to return

        Returns:
            List of recent snapshots
        """
        return self.snapshots[-count:]

    def reset(self) -> None:
        """Reset analytics data."""
        self.total_messages_processed = 0
        self.total_messages_accepted = 0
        self.total_messages_rejected = 0
        self.total_messages_review = 0
        self.total_errors = 0
        self.processing_times.clear()
        self.throughput_metrics.clear()
        self.error_rate_metrics.clear()
        self.domain_distribution.clear()
        self.publisher_distribution.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.deduplication_hits = 0
        self.snapshots.clear()

