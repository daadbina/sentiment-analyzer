"""Pytest configuration and fixtures."""

import pytest
import os
from datetime import datetime
import pytz
from src.models import NewsRaw, ValidationContext, ValidationDetails


@pytest.fixture
def sample_news_raw():
    """Create sample NewsRaw message."""
    return NewsRaw(
        id="test_123",
        title="Test Article Title",
        body="This is a test article body. It has multiple sentences. And it is long enough.",
        url="https://example.com/article",
        published_at="2025-11-02T10:00:00Z",
        language="en",
        source="test_source",
        feed_id="feed_123",
        job_id="job_123",
        validation_score=0.8,
        crawled_at="2025-11-02T11:00:00Z",
        checksum="abc123def456",
    )


@pytest.fixture
def sample_validation_context(sample_news_raw):
    """Create sample ValidationContext."""
    return ValidationContext(
        article_id="art_123",
        trace_id="trace_123",
        job_id="job_123",
        raw_message=sample_news_raw,
    )


@pytest.fixture
def sample_validation_details():
    """Create sample ValidationDetails."""
    return ValidationDetails(
        schema_valid=True,
        encoding_valid=True,
        timestamp_valid=True,
        source_verified=True,
        language_detected=True,
        not_duplicate=True,
        content_quality_ok=True,
    )


@pytest.fixture
def current_utc_time():
    """Get current UTC time."""
    return datetime.now(tz=pytz.UTC)


@pytest.fixture
def past_utc_time(current_utc_time):
    """Get past UTC time (1 day ago)."""
    from datetime import timedelta

    return current_utc_time - timedelta(days=1)


@pytest.fixture
def future_utc_time(current_utc_time):
    """Get future UTC time (1 day from now)."""
    from datetime import timedelta

    return current_utc_time + timedelta(days=1)


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment."""
    # Set test environment variables
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"
    yield
    # Cleanup
    if "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]
