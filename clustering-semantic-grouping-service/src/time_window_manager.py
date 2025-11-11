"""Time window management for sliding window clustering."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class TimeWindowManager:
    """Manages sliding time windows for batch clustering."""

    def __init__(
        self,
        window_size_hours: int = 24,
        overlap_hours: int = 6,
    ):
        """
        Initialize time window manager.

        Args:
            window_size_hours: Size of processing window in hours
            overlap_hours: Overlap period for deduplication
        """
        self.window_size_hours = window_size_hours
        self.overlap_hours = overlap_hours
        logger.info(
            f"Initialized TimeWindowManager: window={window_size_hours}h, overlap={overlap_hours}h"
        )

    def calculate_window(
        self, last_run_time: Optional[datetime] = None
    ) -> Tuple[datetime, datetime]:
        """
        Calculate processing window with overlap handling.

        Args:
            last_run_time: Timestamp of last successful run (UTC)

        Returns:
            Tuple of (window_start, window_end) in UTC
        """
        now = datetime.now(timezone.utc)

        # Window end is current time
        window_end = now

        if last_run_time is None:
            # First run: use default window size
            window_start = window_end - timedelta(hours=self.window_size_hours)
            logger.info(
                f"First run: using default window size. "
                f"Window: {window_start.isoformat()} to {window_end.isoformat()}"
            )
        else:
            # Subsequent runs: start from last run minus overlap
            window_start = last_run_time - timedelta(hours=self.overlap_hours)
            logger.info(
                f"Subsequent run: using overlap strategy. "
                f"Last run: {last_run_time.isoformat()}, "
                f"Window: {window_start.isoformat()} to {window_end.isoformat()}"
            )

        return window_start, window_end

    def get_window_duration_hours(self, window_start: datetime, window_end: datetime) -> float:
        """
        Calculate duration of window in hours.

        Args:
            window_start: Start of window
            window_end: End of window

        Returns:
            Duration in hours
        """
        duration = (window_end - window_start).total_seconds() / 3600
        return duration

    def validate_window(self, window_start: datetime, window_end: datetime) -> bool:
        """
        Validate window parameters.

        Args:
            window_start: Start of window
            window_end: End of window

        Returns:
            True if valid, False otherwise
        """
        if window_start >= window_end:
            logger.error(f"Invalid window: start ({window_start}) >= end ({window_end})")
            return False

        duration = self.get_window_duration_hours(window_start, window_end)
        # Allow large windows for training data (up to 180 days)
        if duration > 4320:  # 180 days
            logger.warning(f"Window duration {duration}h exceeds 180 days")
            return False

        if duration > 168:  # 7 days
            logger.info(f"Using large time window: {duration}h ({duration/24:.1f} days)")

        return True

