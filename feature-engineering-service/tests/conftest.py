"""Pytest configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration."""
    return {
        "kafka_bootstrap_servers": "localhost:9092",
        "postgres_host": "localhost",
        "redis_host": "localhost",
    }

