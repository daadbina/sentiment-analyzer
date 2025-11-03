"""
Timestamp utilities for handling dates and times.

Ensures all timestamps are ISO-8601 formatted and in UTC.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TimestampUtils:
    """
    Utilities for timestamp handling and validation.

    Ensures all timestamps are ISO-8601 formatted and in UTC timezone.
    """

    @staticmethod
    def now_utc() -> datetime:
        """
        Get current time in UTC.

        Returns:
            datetime: Current UTC time.
        """
        return datetime.now(timezone.utc)

    @staticmethod
    def to_iso8601(dt: datetime) -> str:
        """
        Convert datetime to ISO-8601 string.

        Args:
            dt: Datetime object.

        Returns:
            str: ISO-8601 formatted string.
        """
        if not isinstance(dt, datetime):
            raise ValueError(f"Expected datetime, got {type(dt)}")

        # Ensure UTC timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        # Return ISO-8601 format with Z suffix for UTC
        return dt.isoformat().replace("+00:00", "Z")

    @staticmethod
    def from_iso8601(timestamp_str: str) -> datetime:
        """
        Parse ISO-8601 timestamp string.

        Args:
            timestamp_str: ISO-8601 formatted timestamp.

        Returns:
            datetime: Parsed datetime in UTC.

        Raises:
            ValueError: If timestamp format is invalid.
        """
        if not isinstance(timestamp_str, str):
            raise ValueError(f"Expected string, got {type(timestamp_str)}")

        try:
            # Handle Z suffix for UTC
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"

            dt = datetime.fromisoformat(timestamp_str)

            # Ensure UTC timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)

            return dt

        except ValueError as e:
            raise ValueError(f"Invalid ISO-8601 timestamp: {timestamp_str}") from e

    @staticmethod
    def validate_iso8601(timestamp_str: str) -> bool:
        """
        Validate ISO-8601 timestamp format.

        Args:
            timestamp_str: Timestamp string to validate.

        Returns:
            bool: True if valid ISO-8601 format.
        """
        try:
            TimestampUtils.from_iso8601(timestamp_str)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_reasonable_date(dt: datetime, max_years_in_future: int = 0) -> bool:
        """
        Check if datetime is reasonable (not too far in past or future).

        Args:
            dt: Datetime to check.
            max_years_in_future: Maximum years in future allowed
                (default 0 = no future dates).

        Returns:
            bool: True if date is reasonable.
        """
        now = TimestampUtils.now_utc()

        # Ensure dt is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Check not more than 100 years in past
        if (now - dt).days > 36500:
            logger.warning(f"Date is too far in past: {dt}")
            return False

        # Check not in future (or beyond max_years_in_future)
        if (dt - now).days > (365 * max_years_in_future):
            logger.warning(f"Date is too far in future: {dt}")
            return False

        return True

    @staticmethod
    def get_timestamp_components(dt: datetime) -> dict:
        """
        Extract timestamp components.

        Args:
            dt: Datetime object.

        Returns:
            dict: Dictionary with year, month, day, hour, minute, second.
        """
        return {
            "year": dt.year,
            "month": dt.month,
            "day": dt.day,
            "hour": dt.hour,
            "minute": dt.minute,
            "second": dt.second,
            "iso8601": TimestampUtils.to_iso8601(dt),
        }
