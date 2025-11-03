"""Circuit breaker pattern implementation."""

from enum import Enum
from typing import Callable, Any, Optional, Type, Union, Tuple
from datetime import datetime, timedelta
import asyncio


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = 0  # Normal operation
    OPEN = 1  # Failing, reject requests
    HALF_OPEN = 2  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for protecting external service calls."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        expected_exception: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            name: Service name
            failure_threshold: Number of failures before opening
            timeout_seconds: Seconds before attempting recovery
            expected_exception: Exception type to catch
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.expected_exception = expected_exception  # type: ignore

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
        self.lock = asyncio.Lock()

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return False

        elapsed = datetime.utcnow() - self.last_failure_time
        return elapsed >= timedelta(seconds=self.timeout_seconds)

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        async with self.lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                else:
                    from src.exceptions import CircuitBreakerOpenError

                    raise CircuitBreakerOpenError(self.name)

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self.lock:
            self.failure_count = 0

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= 2:  # 2 successes to close
                    self.state = CircuitBreakerState.CLOSED
                    self.success_count = 0

    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self.state

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""

    def __init__(self):
        """Initialize circuit breaker manager."""
        self.breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
    ) -> CircuitBreaker:
        """Get or create circuit breaker for service.

        Args:
            name: Service name
            failure_threshold: Number of failures before opening
            timeout_seconds: Seconds before attempting recovery

        Returns:
            CircuitBreaker instance
        """
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                timeout_seconds=timeout_seconds,
            )
        return self.breakers[name]

    def get_all_states(self) -> dict[str, str]:
        """Get state of all circuit breakers."""
        return {
            name: breaker.get_state().name for name, breaker in self.breakers.items()
        }


# Global circuit breaker manager
_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager (singleton)."""
    global _manager
    if _manager is None:
        _manager = CircuitBreakerManager()
    return _manager
