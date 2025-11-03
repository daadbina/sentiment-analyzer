"""Comprehensive tests for circuit breaker."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from src.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerManager,
    get_circuit_breaker_manager,
)
from src.exceptions import CircuitBreakerOpenError


class TestCircuitBreakerState:
    """Test circuit breaker state enum."""

    def test_circuit_breaker_state_values(self):
        """Test circuit breaker state values."""
        assert CircuitBreakerState.CLOSED.value == 0
        assert CircuitBreakerState.OPEN.value == 1
        assert CircuitBreakerState.HALF_OPEN.value == 2

    def test_circuit_breaker_state_names(self):
        """Test circuit breaker state names."""
        assert CircuitBreakerState.CLOSED.name == "CLOSED"
        assert CircuitBreakerState.OPEN.name == "OPEN"
        assert CircuitBreakerState.HALF_OPEN.name == "HALF_OPEN"


class TestCircuitBreaker:
    """Test circuit breaker."""

    def test_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker("test_service")

        assert cb.name == "test_service"
        assert cb.failure_threshold == 5
        assert cb.timeout_seconds == 60
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None

    def test_initialization_custom_params(self):
        """Test circuit breaker initialization with custom parameters."""
        cb = CircuitBreaker(
            "test_service",
            failure_threshold=3,
            timeout_seconds=30,
        )

        assert cb.failure_threshold == 3
        assert cb.timeout_seconds == 30

    def test_get_state(self):
        """Test getting circuit breaker state."""
        cb = CircuitBreaker("test_service")

        assert cb.get_state() == CircuitBreakerState.CLOSED

    def test_reset(self):
        """Test resetting circuit breaker."""
        cb = CircuitBreaker("test_service")
        cb.state = CircuitBreakerState.OPEN
        cb.failure_count = 5
        cb.success_count = 2
        cb.last_failure_time = datetime.utcnow()

        cb.reset()

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None

    @pytest.mark.asyncio
    async def test_call_success(self):
        """Test successful call through circuit breaker."""
        cb = CircuitBreaker("test_service")

        async def success_func():
            return "success"

        result = await cb.call(success_func)

        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_call_with_args(self):
        """Test call with arguments."""
        cb = CircuitBreaker("test_service")

        async def add_func(a, b):
            return a + b

        result = await cb.call(add_func, 2, 3)

        assert result == 5

    @pytest.mark.asyncio
    async def test_call_with_kwargs(self):
        """Test call with keyword arguments."""
        cb = CircuitBreaker("test_service")

        async def greet_func(name, greeting="Hello"):
            return f"{greeting}, {name}"

        result = await cb.call(greet_func, name="World", greeting="Hi")

        assert result == "Hi, World"

    @pytest.mark.asyncio
    async def test_call_failure(self):
        """Test failed call through circuit breaker."""
        cb = CircuitBreaker("test_service", failure_threshold=2)

        async def fail_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await cb.call(fail_func)

        assert cb.failure_count == 1
        assert cb.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_call_multiple_failures_opens_circuit(self):
        """Test that multiple failures open the circuit."""
        cb = CircuitBreaker("test_service", failure_threshold=2)

        async def fail_func():
            raise ValueError("Test error")

        # First failure
        with pytest.raises(ValueError):
            await cb.call(fail_func)

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            await cb.call(fail_func)

        assert cb.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_call_open_circuit_raises_error(self):
        """Test that open circuit raises CircuitBreakerOpenError."""
        cb = CircuitBreaker("test_service", failure_threshold=1)

        async def fail_func():
            raise ValueError("Test error")

        # Open the circuit
        with pytest.raises(ValueError):
            await cb.call(fail_func)

        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(fail_func)

    @pytest.mark.asyncio
    async def test_half_open_state_recovery(self):
        """Test recovery from half-open state."""
        cb = CircuitBreaker("test_service", failure_threshold=1, timeout_seconds=0)

        async def fail_func():
            raise ValueError("Test error")

        async def success_func():
            return "success"

        # Open the circuit
        with pytest.raises(ValueError):
            await cb.call(fail_func)

        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout (0 seconds)
        await asyncio.sleep(0.1)

        # Next call should transition to HALF_OPEN
        result = await cb.call(success_func)
        assert result == "success"

        # One success in HALF_OPEN, need another
        result = await cb.call(success_func)
        assert result == "success"

        # Should be closed now
        assert cb.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """Test that failure in half-open state reopens circuit."""
        cb = CircuitBreaker("test_service", failure_threshold=1, timeout_seconds=0)

        async def fail_func():
            raise ValueError("Test error")

        # Open the circuit
        with pytest.raises(ValueError):
            await cb.call(fail_func)

        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.1)

        # Fail in HALF_OPEN state - should reopen
        with pytest.raises(ValueError):
            await cb.call(fail_func)

        assert cb.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Test that success resets failure count."""
        cb = CircuitBreaker("test_service", failure_threshold=3)

        async def fail_func():
            raise ValueError("Test error")

        async def success_func():
            return "success"

        # One failure
        with pytest.raises(ValueError):
            await cb.call(fail_func)

        assert cb.failure_count == 1

        # Success should reset failure count
        await cb.call(success_func)

        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_different_exception_types(self):
        """Test circuit breaker with different exception types."""
        cb = CircuitBreaker("test_service", expected_exception=ValueError)

        async def raise_type_error():
            raise TypeError("Wrong type")

        # TypeError should not be caught
        with pytest.raises(TypeError):
            await cb.call(raise_type_error)

        # Circuit should still be closed
        assert cb.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerManager:
    """Test circuit breaker manager."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = CircuitBreakerManager()

        assert manager.breakers == {}

    def test_get_or_create_new(self):
        """Test getting or creating new circuit breaker."""
        manager = CircuitBreakerManager()

        cb = manager.get_or_create("service1")

        assert cb is not None
        assert cb.name == "service1"
        assert "service1" in manager.breakers

    def test_get_or_create_existing(self):
        """Test getting existing circuit breaker."""
        manager = CircuitBreakerManager()

        cb1 = manager.get_or_create("service1")
        cb2 = manager.get_or_create("service1")

        assert cb1 is cb2

    def test_get_or_create_multiple(self):
        """Test creating multiple circuit breakers."""
        manager = CircuitBreakerManager()

        cb1 = manager.get_or_create("service1")
        cb2 = manager.get_or_create("service2")
        cb3 = manager.get_or_create("service3")

        assert cb1.name == "service1"
        assert cb2.name == "service2"
        assert cb3.name == "service3"
        assert len(manager.breakers) == 3

    def test_get_or_create_custom_params(self):
        """Test creating circuit breaker with custom parameters."""
        manager = CircuitBreakerManager()

        cb = manager.get_or_create(
            "service1",
            failure_threshold=3,
            timeout_seconds=30,
        )

        assert cb.failure_threshold == 3
        assert cb.timeout_seconds == 30

    def test_get_all_states(self):
        """Test getting all circuit breaker states."""
        manager = CircuitBreakerManager()

        cb1 = manager.get_or_create("service1")
        cb2 = manager.get_or_create("service2")

        states = manager.get_all_states()

        assert states["service1"] == "CLOSED"
        assert states["service2"] == "CLOSED"

    def test_get_all_states_mixed(self):
        """Test getting states with mixed states."""
        manager = CircuitBreakerManager()

        cb1 = manager.get_or_create("service1")
        cb2 = manager.get_or_create("service2")

        cb1.state = CircuitBreakerState.OPEN
        cb2.state = CircuitBreakerState.HALF_OPEN

        states = manager.get_all_states()

        assert states["service1"] == "OPEN"
        assert states["service2"] == "HALF_OPEN"


class TestCircuitBreakerGlobal:
    """Test global circuit breaker manager."""

    def test_get_circuit_breaker_manager_singleton(self):
        """Test that global manager is singleton."""
        manager1 = get_circuit_breaker_manager()
        manager2 = get_circuit_breaker_manager()

        assert manager1 is manager2

    def test_get_circuit_breaker_manager_creates_breaker(self):
        """Test creating circuit breaker through global manager."""
        manager = get_circuit_breaker_manager()

        cb = manager.get_or_create("global_service")

        assert cb is not None
        assert cb.name == "global_service"

    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_calls(self):
        """Test circuit breaker with concurrent calls."""
        cb = CircuitBreaker("test_service", failure_threshold=5)

        async def success_func():
            await asyncio.sleep(0.01)
            return "success"

        # Run multiple concurrent calls
        tasks = [cb.call(success_func) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r == "success" for r in results)
        assert cb.state == CircuitBreakerState.CLOSED

