"""Circuit breaker pattern for resilience."""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Circuit breaker for handling failures gracefully."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to catch
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.lock = Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit {self.name} entering HALF_OPEN state")
                else:
                    raise Exception(f"Circuit {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _on_success(self) -> None:
        """Handle successful call."""
        with self.lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logger.info(f"Circuit {self.name} closed after successful call")

    def _on_failure(self) -> None:
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit {self.name} opened after {self.failure_count} failures"
                )

    def get_state(self) -> str:
        """Get current circuit state."""
        return self.state.value

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            logger.info(f"Circuit {self.name} manually reset")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        """Initialize circuit breaker registry."""
        self.breakers: dict[str, CircuitBreaker] = {}
        self.lock = Lock()

    def register(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ) -> CircuitBreaker:
        """Register a new circuit breaker.

        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to catch

        Returns:
            CircuitBreaker instance
        """
        with self.lock:
            if name not in self.breakers:
                breaker = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    expected_exception=expected_exception,
                )
                self.breakers[name] = breaker
                logger.info(f"Registered circuit breaker: {name}")
            return self.breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name.

        Args:
            name: Circuit breaker name

        Returns:
            CircuitBreaker instance or None
        """
        return self.breakers.get(name)

    def get_all_states(self) -> dict[str, str]:
        """Get states of all circuit breakers.

        Returns:
            Dictionary of circuit breaker names and states
        """
        return {name: breaker.get_state() for name, breaker in self.breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        with self.lock:
            for breaker in self.breakers.values():
                breaker.reset()
            logger.info("All circuit breakers reset")


# Global registry
_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
) -> CircuitBreaker:
    """Get or create a circuit breaker.

    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before attempting recovery
        expected_exception: Exception type to catch

    Returns:
        CircuitBreaker instance
    """
    return _registry.register(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
    )


def get_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry.

    Returns:
        CircuitBreakerRegistry instance
    """
    return _registry

