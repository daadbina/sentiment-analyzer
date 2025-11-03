"""Timestamp validation and normalization."""

import logging
from datetime import datetime
from dateutil import parser as dateutil_parser
import pytz  # type: ignore
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TimestampValidator:
    """Validates and normalizes timestamps."""

    # Maximum age for articles (5 years)
    MAX_AGE_DAYS = 365 * 5

    # Maximum future offset (24 hours)
    MAX_FUTURE_HOURS = 24

    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from various formats.

        Supports:
        - ISO-8601 (2025-11-02T10:30:00Z)
        - RFC-2822 (Fri, 02 Nov 2025 10:30:00 +0000)
        - Unix timestamp (1730534400)
        - Common locale formats

        Args:
            timestamp_str: Timestamp string

        Returns:
            Parsed datetime or None if parsing fails
        """
        if not timestamp_str or not isinstance(timestamp_str, str):
            return None

        timestamp_str = timestamp_str.strip()

        try:
            # Try Unix timestamp first
            try:
                timestamp_float = float(timestamp_str)
                if 0 < timestamp_float < 2**31:  # Reasonable Unix timestamp range
                    return datetime.fromtimestamp(timestamp_float, tz=pytz.UTC)
            except (ValueError, OSError):
                pass

            # Try dateutil parser (handles most formats)
            dt = dateutil_parser.parse(timestamp_str)

            # Ensure timezone aware
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)

            return dt

        except Exception as e:
            logger.debug(f"Failed to parse timestamp '{timestamp_str}': {e}")
            return None

    @staticmethod
    def validate_temporal_coherence(
        published_at: datetime,
        crawled_at: datetime,
    ) -> bool:
        """Validate temporal coherence (published <= crawled).

        Args:
            published_at: Article publication time
            crawled_at: Article crawl time

        Returns:
            True if coherent, False otherwise
        """
        return published_at <= crawled_at

    @staticmethod
    def validate_age(published_at: datetime) -> Tuple[bool, Optional[str]]:
        """Validate article age.

        Args:
            published_at: Article publication time

        Returns:
            Tuple of (is_valid, warning_message)
        """
        now = datetime.now(tz=pytz.UTC)
        age = now - published_at

        # Check if too old
        if age.days > TimestampValidator.MAX_AGE_DAYS:
            return (
                False,
                f"Article is {age.days} days old (max {TimestampValidator.MAX_AGE_DAYS})",
            )

        # Check if in future
        if age.total_seconds() < 0:
            future_hours = abs(age.total_seconds()) / 3600
            if future_hours > TimestampValidator.MAX_FUTURE_HOURS:
                return (
                    False,
                    f"Article is {future_hours:.1f} hours in future (max {TimestampValidator.MAX_FUTURE_HOURS})",
                )
            else:
                return True, f"Article is {future_hours:.1f} hours in future"

        return True, None

    @staticmethod
    def normalize_to_utc(dt: datetime) -> str:
        """Normalize datetime to UTC ISO-8601 string.

        Args:
            dt: Datetime object

        Returns:
            ISO-8601 UTC string
        """
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        # Convert to UTC
        dt_utc = dt.astimezone(pytz.UTC)

        # Return ISO-8601 format
        return dt_utc.isoformat().replace("+00:00", "Z")

    @staticmethod
    def validate_and_normalize(
        source_published_at_raw: str,
        crawled_at: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate and normalize timestamps.

        Args:
            source_published_at_raw: Raw published timestamp from source
            crawled_at: Crawl timestamp

        Returns:
            Tuple of (is_valid, normalized_published_at_utc, error_message)
        """
        try:
            # Parse timestamps
            published_dt = TimestampValidator.parse_timestamp(source_published_at_raw)
            if not published_dt:
                return False, None, "Failed to parse published_at timestamp"

            crawled_dt = TimestampValidator.parse_timestamp(crawled_at)
            if not crawled_dt:
                return False, None, "Failed to parse crawled_at timestamp"

            # Validate temporal coherence
            if not TimestampValidator.validate_temporal_coherence(
                published_dt, crawled_dt
            ):
                return False, None, "Published time is after crawl time"

            # Validate age
            is_valid_age, age_warning = TimestampValidator.validate_age(published_dt)
            if not is_valid_age:
                return False, None, age_warning or "Article age validation failed"

            # Normalize to UTC
            normalized_utc = TimestampValidator.normalize_to_utc(published_dt)

            return True, normalized_utc, age_warning

        except Exception as e:
            logger.error(f"Timestamp validation error: {e}")
            return False, None, str(e)
