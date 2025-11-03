"""Tests for timestamp validator."""

from datetime import datetime, timedelta
import pytz
from src.validation.timestamp import TimestampValidator


class TestTimestampValidator:
    """Test timestamp validator."""

    def test_parse_iso8601_timestamp(self):
        """Test parsing ISO-8601 timestamp."""
        ts = "2025-11-02T10:30:00Z"
        result = TimestampValidator.parse_timestamp(ts)
        assert result is not None
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 2

    def test_parse_unix_timestamp(self):
        """Test parsing Unix timestamp."""
        ts = "1730534400"  # 2025-11-02 10:00:00 UTC
        result = TimestampValidator.parse_timestamp(ts)
        assert result is not None

    def test_parse_invalid_timestamp(self):
        """Test parsing invalid timestamp."""
        ts = "invalid"
        result = TimestampValidator.parse_timestamp(ts)
        assert result is None

    def test_parse_empty_timestamp(self):
        """Test parsing empty timestamp."""
        result = TimestampValidator.parse_timestamp("")
        assert result is None

    def test_validate_temporal_coherence_valid(self):
        """Test temporal coherence validation - valid case."""
        now = datetime.now(tz=pytz.UTC)
        published = now - timedelta(hours=1)
        crawled = now

        result = TimestampValidator.validate_temporal_coherence(published, crawled)
        assert result is True

    def test_validate_temporal_coherence_invalid(self):
        """Test temporal coherence validation - invalid case."""
        now = datetime.now(tz=pytz.UTC)
        published = now + timedelta(hours=1)
        crawled = now

        result = TimestampValidator.validate_temporal_coherence(published, crawled)
        assert result is False

    def test_validate_age_recent(self):
        """Test age validation - recent article."""
        now = datetime.now(tz=pytz.UTC)
        published = now - timedelta(days=1)

        is_valid, warning = TimestampValidator.validate_age(published)
        assert is_valid is True

    def test_validate_age_too_old(self):
        """Test age validation - too old."""
        now = datetime.now(tz=pytz.UTC)
        published = now - timedelta(days=2000)

        is_valid, warning = TimestampValidator.validate_age(published)
        assert is_valid is False

    def test_validate_age_future(self):
        """Test age validation - future timestamp."""
        now = datetime.now(tz=pytz.UTC)
        published = now + timedelta(hours=1)

        is_valid, warning = TimestampValidator.validate_age(published)
        assert is_valid is True  # Within 24 hour tolerance

    def test_normalize_to_utc(self):
        """Test UTC normalization."""
        dt = datetime(2025, 11, 2, 10, 30, 0, tzinfo=pytz.UTC)
        result = TimestampValidator.normalize_to_utc(dt)
        assert "2025-11-02" in result
        assert "Z" in result

    def test_validate_and_normalize_valid(self):
        """Test validate and normalize - valid case."""
        now = datetime.now(tz=pytz.UTC)
        published_str = now.isoformat()
        crawled_str = (now + timedelta(hours=1)).isoformat()

        is_valid, normalized, error = TimestampValidator.validate_and_normalize(
            published_str,
            crawled_str,
        )

        assert is_valid is True
        assert normalized is not None
        assert "Z" in normalized

    def test_validate_and_normalize_invalid_published(self):
        """Test validate and normalize - invalid published timestamp."""
        is_valid, normalized, error = TimestampValidator.validate_and_normalize(
            "invalid",
            "2025-11-02T10:30:00Z",
        )

        assert is_valid is False
        assert normalized is None
        assert error is not None

    def test_validate_and_normalize_invalid_crawled(self):
        """Test validate and normalize - invalid crawled timestamp."""
        is_valid, normalized, error = TimestampValidator.validate_and_normalize(
            "2025-11-02T10:30:00Z",
            "invalid",
        )

        assert is_valid is False
        assert normalized is None
        assert error is not None

    def test_validate_age_future_within_threshold(self):
        """Test age validation - future within threshold."""
        future_dt = datetime.now(tz=pytz.UTC) + timedelta(hours=12)
        is_valid, warning = TimestampValidator.validate_age(future_dt)
        assert is_valid is True
        assert warning is not None

    def test_validate_age_future_exceeds_threshold(self):
        """Test age validation - future exceeds threshold."""
        future_dt = datetime.now(tz=pytz.UTC) + timedelta(hours=25)
        is_valid, warning = TimestampValidator.validate_age(future_dt)
        assert is_valid is False
        assert warning is not None

    def test_normalize_to_utc_with_timezone(self):
        """Test UTC normalization with timezone."""
        dt = datetime(2025, 11, 2, 10, 30, 0, tzinfo=pytz.timezone('US/Eastern'))
        result = TimestampValidator.normalize_to_utc(dt)
        assert "Z" in result
        assert "2025-11-02" in result

    def test_normalize_to_utc_without_timezone(self):
        """Test UTC normalization without timezone."""
        dt = datetime(2025, 11, 2, 10, 30, 0)
        result = TimestampValidator.normalize_to_utc(dt)
        assert "Z" in result
        assert "2025-11-02" in result

    def test_validate_and_normalize_exception(self):
        """Test validate and normalize with exception."""
        is_valid, normalized, error = TimestampValidator.validate_and_normalize(
            None,
            "2025-11-02T10:30:00Z",
        )

        assert is_valid is False
        assert normalized is None
        assert error is not None

    def test_validate_age_old_article(self):
        """Test age validation - old article within threshold."""
        old_dt = datetime.now(tz=pytz.UTC) - timedelta(days=1000)
        is_valid, warning = TimestampValidator.validate_age(old_dt)
        assert is_valid is True
        assert warning is None

    def test_validate_age_too_old_article(self):
        """Test age validation - article too old."""
        too_old_dt = datetime.now(tz=pytz.UTC) - timedelta(days=2000)
        is_valid, warning = TimestampValidator.validate_age(too_old_dt)
        assert is_valid is False
        assert warning is not None
