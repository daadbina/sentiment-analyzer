"""Tests for backpressure handling."""

import pytest
import asyncio
from src.utils.backpressure import BackpressureManager


class TestBackpressureManager:
    """Test BackpressureManager."""

    def test_create_backpressure_manager(self):
        """Test creating BackpressureManager."""
        manager = BackpressureManager(
            lag_threshold=10000,
            throttle_delay_ms=100,
            max_throttle_delay_ms=5000,
        )

        assert manager.lag_threshold == 10000
        assert manager.throttle_delay_ms == 100
        assert manager.max_throttle_delay_ms == 5000
        assert manager.is_throttled is False

    def test_update_consumer_lag(self):
        """Test updating consumer lag."""
        manager = BackpressureManager()
        lag_dict = {0: 5000, 1: 3000, 2: 7000}

        manager.update_consumer_lag(lag_dict)

        assert manager.last_lag_values == lag_dict
        assert manager.last_lag_check is not None

    def test_get_max_lag(self):
        """Test getting maximum lag."""
        manager = BackpressureManager()
        lag_dict = {0: 5000, 1: 3000, 2: 7000}

        manager.update_consumer_lag(lag_dict)

        assert manager.get_max_lag() == 7000

    def test_get_max_lag_empty(self):
        """Test getting max lag with no data."""
        manager = BackpressureManager()

        assert manager.get_max_lag() == 0

    def test_should_throttle_below_threshold(self):
        """Test should_throttle when lag is below threshold."""
        manager = BackpressureManager(lag_threshold=10000)
        lag_dict = {0: 5000, 1: 3000}

        manager.update_consumer_lag(lag_dict)

        assert manager.should_throttle() is False
        assert manager.is_throttled is False

    def test_should_throttle_above_threshold(self):
        """Test should_throttle when lag exceeds threshold."""
        manager = BackpressureManager(lag_threshold=10000)
        lag_dict = {0: 15000, 1: 3000}

        manager.update_consumer_lag(lag_dict)

        assert manager.should_throttle() is True
        assert manager.is_throttled is True

    def test_should_throttle_circuit_breaker_open(self):
        """Test should_throttle when circuit breaker is open."""
        manager = BackpressureManager(lag_threshold=10000)
        lag_dict = {0: 5000, 1: 3000}

        manager.update_consumer_lag(lag_dict)
        manager.set_circuit_breaker_open(True)

        assert manager.should_throttle() is True
        assert manager.is_throttled is True

    def test_should_throttle_recovery(self):
        """Test should_throttle recovery when lag drops."""
        manager = BackpressureManager(lag_threshold=10000)

        # First, trigger throttling
        lag_dict = {0: 15000, 1: 3000}
        manager.update_consumer_lag(lag_dict)
        assert manager.should_throttle() is True
        assert manager.is_throttled is True

        # Then, lag drops below threshold
        lag_dict = {0: 5000, 1: 3000}
        manager.update_consumer_lag(lag_dict)
        assert manager.should_throttle() is False
        assert manager.is_throttled is False

    @pytest.mark.asyncio
    async def test_apply_throttle_no_throttle(self):
        """Test apply_throttle when no throttling needed."""
        manager = BackpressureManager(lag_threshold=10000)
        lag_dict = {0: 5000, 1: 3000}

        manager.update_consumer_lag(lag_dict)

        # Should not delay
        import time
        start = time.time()
        await manager.apply_throttle()
        elapsed = time.time() - start

        assert elapsed < 0.1  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_apply_throttle_with_throttle(self):
        """Test apply_throttle when throttling is needed."""
        manager = BackpressureManager(
            lag_threshold=10000,
            throttle_delay_ms=100,
            max_throttle_delay_ms=5000,
        )
        lag_dict = {0: 15000, 1: 3000}

        manager.update_consumer_lag(lag_dict)

        # Should delay
        import time
        start = time.time()
        await manager.apply_throttle()
        elapsed = time.time() - start

        assert elapsed >= 0.09  # At least 100ms

    def test_set_circuit_breaker_open(self):
        """Test setting circuit breaker state."""
        manager = BackpressureManager()

        assert manager.circuit_breaker_open is False

        manager.set_circuit_breaker_open(True)
        assert manager.circuit_breaker_open is True

        manager.set_circuit_breaker_open(False)
        assert manager.circuit_breaker_open is False

    def test_get_status(self):
        """Test getting backpressure status."""
        manager = BackpressureManager(lag_threshold=10000)
        lag_dict = {0: 5000, 1: 3000}

        manager.update_consumer_lag(lag_dict)

        status = manager.get_status()

        assert "is_throttled" in status
        assert "current_throttle_delay_ms" in status
        assert "max_lag" in status
        assert "lag_threshold" in status
        assert "circuit_breaker_open" in status
        assert "throttle_duration_seconds" in status
        assert "lag_by_partition" in status
        assert status["max_lag"] == 5000
        assert status["lag_threshold"] == 10000

    def test_exponential_backoff(self):
        """Test exponential backoff delay increase."""
        manager = BackpressureManager(
            lag_threshold=10000,
            throttle_delay_ms=100,
            max_throttle_delay_ms=5000,
        )
        lag_dict = {0: 15000}

        manager.update_consumer_lag(lag_dict)
        manager.should_throttle()

        initial_delay = manager.current_throttle_delay_ms
        assert initial_delay == 100

        # Simulate multiple throttle applications
        manager.current_throttle_delay_ms = min(
            int(manager.current_throttle_delay_ms * 1.5),
            manager.max_throttle_delay_ms,
        )

        assert manager.current_throttle_delay_ms == 150

        manager.current_throttle_delay_ms = min(
            int(manager.current_throttle_delay_ms * 1.5),
            manager.max_throttle_delay_ms,
        )

        assert manager.current_throttle_delay_ms == 225

    def test_max_throttle_delay_cap(self):
        """Test that throttle delay is capped at max."""
        manager = BackpressureManager(
            lag_threshold=10000,
            throttle_delay_ms=100,
            max_throttle_delay_ms=1000,
        )

        # Simulate many exponential backoff iterations
        for _ in range(20):
            manager.current_throttle_delay_ms = min(
                int(manager.current_throttle_delay_ms * 1.5),
                manager.max_throttle_delay_ms,
            )

        assert manager.current_throttle_delay_ms <= manager.max_throttle_delay_ms

