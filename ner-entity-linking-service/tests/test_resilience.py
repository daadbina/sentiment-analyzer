"""Tests for resilience patterns."""

import pytest
import time
from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_circuit_breaker,
)
from src.resilience.retry_policy import (
    RetryPolicy,
    BackoffStrategy,
    get_retry_policy,
)


class TestCircuitBreaker:
    """Tests for circuit breaker pattern."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        breaker = CircuitBreaker(
            name="test_breaker",
            failure_threshold=3,
            recovery_timeout=5,
        )
        assert breaker.name == "test_breaker"
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 5
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_successful_call(self):
        """Test successful call through circuit breaker."""
        breaker = CircuitBreaker(name="test_breaker")

        def successful_func():
            return "success"

        result = breaker.call(successful_func)
        assert result == "success"
        assert breaker.failure_count == 0

    def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(name="test_breaker", failure_threshold=2)

        def failing_func():
            raise ValueError("Test error")

        # First failure
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.failure_count == 1
        assert breaker.state == CircuitState.CLOSED

        # Second failure - should open
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.failure_count == 2
        assert breaker.state == CircuitState.OPEN

        # Third call - should raise circuit open error
        with pytest.raises(Exception, match="Circuit.*is OPEN"):
            breaker.call(failing_func)

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        breaker = CircuitBreaker(
            name="test_breaker",
            failure_threshold=1,
            recovery_timeout=1,
        )

        def failing_func():
            raise ValueError("Test error")

        # Trigger failure
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # Should attempt recovery
        def successful_func():
            return "success"

        result = breaker.call(successful_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset."""
        breaker = CircuitBreaker(name="test_breaker", failure_threshold=1)

        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == CircuitState.OPEN

        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_circuit_breaker_get_state(self):
        """Test getting circuit breaker state."""
        breaker = CircuitBreaker(name="test_breaker")
        assert breaker.get_state() == "CLOSED"


class TestRetryPolicy:
    """Tests for retry policy."""

    def test_retry_policy_initialization(self):
        """Test retry policy initialization."""
        policy = RetryPolicy(
            name="test_policy",
            max_attempts=3,
            initial_delay=0.1,
            max_delay=1.0,
        )
        assert policy.name == "test_policy"
        assert policy.max_attempts == 3
        assert policy.initial_delay == 0.1

    def test_retry_policy_successful_first_attempt(self):
        """Test successful call on first attempt."""
        policy = RetryPolicy(name="test_policy", max_attempts=3)

        def successful_func():
            return "success"

        result = policy.execute(successful_func)
        assert result == "success"
        assert policy.attempt_count == 1

    def test_retry_policy_success_after_retries(self):
        """Test successful call after retries."""
        policy = RetryPolicy(
            name="test_policy",
            max_attempts=3,
            initial_delay=0.01,
        )
        attempt_count = 0

        def failing_then_success():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Test error")
            return "success"

        result = policy.execute(failing_then_success)
        assert result == "success"
        assert policy.attempt_count == 3

    def test_retry_policy_max_attempts_exceeded(self):
        """Test retry policy fails after max attempts."""
        policy = RetryPolicy(
            name="test_policy",
            max_attempts=2,
            initial_delay=0.01,
        )

        def always_failing():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            policy.execute(always_failing)
        assert policy.attempt_count == 2

    def test_retry_policy_fixed_backoff(self):
        """Test fixed backoff strategy."""
        policy = RetryPolicy(
            name="test_policy",
            max_attempts=2,
            initial_delay=0.05,
            backoff_strategy=BackoffStrategy.FIXED,
        )

        def always_failing():
            raise ValueError("Test error")

        start_time = time.time()
        with pytest.raises(ValueError):
            policy.execute(always_failing)
        elapsed = time.time() - start_time

        # Should have one delay of ~0.05s
        assert elapsed >= 0.04

    def test_retry_policy_exponential_backoff(self):
        """Test exponential backoff strategy."""
        policy = RetryPolicy(
            name="test_policy",
            max_attempts=3,
            initial_delay=0.01,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
        )

        def always_failing():
            raise ValueError("Test error")

        start_time = time.time()
        with pytest.raises(ValueError):
            policy.execute(always_failing)
        elapsed = time.time() - start_time

        # Should have delays of ~0.01s and ~0.02s
        assert elapsed >= 0.02

    def test_retry_policy_get_stats(self):
        """Test getting retry policy statistics."""
        policy = RetryPolicy(name="test_policy", max_attempts=3)

        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            policy.execute(failing_func)

        stats = policy.get_stats()
        assert stats["name"] == "test_policy"
        assert stats["attempt_count"] == 3
        assert stats["max_attempts"] == 3
        assert stats["last_exception"] is not None


class TestCircuitBreakerRegistry:
    """Tests for circuit breaker registry."""

    def test_get_circuit_breaker(self):
        """Test getting circuit breaker from registry."""
        breaker = get_circuit_breaker("test_breaker")
        assert breaker is not None
        assert breaker.name == "test_breaker"

    def test_get_same_circuit_breaker(self):
        """Test getting same circuit breaker returns same instance."""
        breaker1 = get_circuit_breaker("test_breaker_2")
        breaker2 = get_circuit_breaker("test_breaker_2")
        assert breaker1 is breaker2


class TestRetryPolicyRegistry:
    """Tests for retry policy registry."""

    def test_get_retry_policy(self):
        """Test getting retry policy from registry."""
        policy = get_retry_policy("test_policy")
        assert policy is not None
        assert policy.name == "test_policy"

    def test_get_same_retry_policy(self):
        """Test getting same retry policy returns same instance."""
        policy1 = get_retry_policy("test_policy_2")
        policy2 = get_retry_policy("test_policy_2")
        assert policy1 is policy2

