"""Tests for circuit breaker resilience under failure conditions."""

import pytest
import asyncio
import time
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState
from src.exceptions import CircuitBreakerOpenError


class TestCircuitBreakerResilience:
    """Test circuit breaker behavior under simulated failure conditions."""

    def setup_method(self):
        """Setup test fixtures."""
        self.circuit_breaker = CircuitBreaker(
            name="test_breaker",
            failure_threshold=3,
            timeout_seconds=2,
        )

    def test_circuit_breaker_initial_state(self):
        """Test that circuit breaker starts in CLOSED state."""
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED
        assert self.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_success_call(self):
        """Test that successful calls don't increment failure count."""
        async def success_func():
            return "success"

        result = await self.circuit_breaker.call(success_func)
        assert result == "success"
        assert self.circuit_breaker.failure_count == 0
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_increments_count(self):
        """Test that failures increment the failure count."""
        async def failing_func():
            raise Exception("Test failure")

        with pytest.raises(Exception):
            await self.circuit_breaker.call(failing_func)

        assert self.circuit_breaker.failure_count == 1
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit breaker opens after failure threshold."""
        async def failing_func():
            raise Exception("Test failure")

        # Record failures up to threshold
        for _ in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)

        assert self.circuit_breaker.failure_count == 3
        assert self.circuit_breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_calls_when_open(self):
        """Test that circuit breaker rejects calls when OPEN."""
        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)

        assert self.circuit_breaker.state == CircuitBreakerState.OPEN

        # Subsequent calls should raise CircuitBreakerOpenError
        async def success_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError):
            await self.circuit_breaker.call(success_func)

    def test_circuit_breaker_allows_calls_when_closed(self):
        """Test that circuit breaker allows calls when CLOSED."""
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_transitions_to_half_open(self):
        """Test that circuit breaker transitions to HALF_OPEN after timeout."""
        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)

        assert self.circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout
        await asyncio.sleep(2.1)

        # Next call should transition to HALF_OPEN
        async def success_func():
            return "success"

        result = await self.circuit_breaker.call(success_func)
        assert result == "success"
        # After 2 successes in HALF_OPEN, should close
        result = await self.circuit_breaker.call(success_func)
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_on_success_in_half_open(self):
        """Test that circuit breaker closes after success in HALF_OPEN state."""
        async def failing_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)

        # Wait for timeout to transition to HALF_OPEN
        await asyncio.sleep(2.1)

        # Record 2 successes to close
        result1 = await self.circuit_breaker.call(success_func)
        assert result1 == "success"

        result2 = await self.circuit_breaker.call(success_func)
        assert result2 == "success"

        # Should close
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED
        assert self.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_reopens_on_failure_in_half_open(self):
        """Test that circuit breaker reopens on failure in HALF_OPEN state."""
        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)

        # Wait for timeout to transition to HALF_OPEN
        await asyncio.sleep(2.1)

        # Record failure in HALF_OPEN
        with pytest.raises(Exception):
            await self.circuit_breaker.call(failing_func)

        # Should reopen
        assert self.circuit_breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_multiple_failures_before_threshold(self):
        """Test circuit breaker with multiple failures below threshold."""
        async def failing_func():
            raise Exception("Test failure")

        for i in range(2):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)
            assert self.circuit_breaker.state == CircuitBreakerState.CLOSED
            assert self.circuit_breaker.failure_count == i + 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_cycle(self):
        """Test complete recovery cycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
        async def failing_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # Start in CLOSED
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED

        # Fail to OPEN
        for _ in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)
        assert self.circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for HALF_OPEN
        await asyncio.sleep(2.1)

        # Succeed to CLOSED (need 2 successes)
        result1 = await self.circuit_breaker.call(success_func)
        assert result1 == "success"
        result2 = await self.circuit_breaker.call(success_func)
        assert result2 == "success"
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_name_attribute(self):
        """Test that circuit breaker has name attribute."""
        assert self.circuit_breaker.name == "test_breaker"

    @pytest.mark.asyncio
    async def test_circuit_breaker_threshold_configuration(self):
        """Test that circuit breaker respects configured threshold."""
        cb = CircuitBreaker(name="test", failure_threshold=5, timeout_seconds=1)

        async def failing_func():
            raise Exception("Test failure")

        # Should not open until 5 failures
        for i in range(4):
            with pytest.raises(Exception):
                await cb.call(failing_func)
            assert cb.state == CircuitBreakerState.CLOSED

        # 5th failure should open
        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_timeout_configuration(self):
        """Test that circuit breaker respects configured timeout."""
        cb = CircuitBreaker(name="test", failure_threshold=1, timeout_seconds=1)

        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.state == CircuitBreakerState.OPEN

        # Should still be OPEN before timeout
        await asyncio.sleep(0.5)

        async def success_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(success_func)

        # Should transition to HALF_OPEN after timeout
        await asyncio.sleep(0.6)
        result = await cb.call(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_transitions_tracked(self):
        """Test that circuit breaker state transitions are tracked."""
        async def failing_func():
            raise Exception("Test failure")

        # Record initial state
        initial_state = self.circuit_breaker.state

        # Trigger state change
        for _ in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)

        # Verify state changed
        assert self.circuit_breaker.state != initial_state
        assert self.circuit_breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_cascading_failures(self):
        """Test that circuit breaker prevents cascading failures."""
        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)

        assert self.circuit_breaker.state == CircuitBreakerState.OPEN

        # Subsequent calls should be rejected without executing
        async def success_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError):
            await self.circuit_breaker.call(success_func)

        # This prevents cascading failures to downstream services

    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset."""
        self.circuit_breaker.failure_count = 5
        self.circuit_breaker.state = CircuitBreakerState.OPEN

        self.circuit_breaker.reset()

        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED
        assert self.circuit_breaker.failure_count == 0
        assert self.circuit_breaker.success_count == 0

