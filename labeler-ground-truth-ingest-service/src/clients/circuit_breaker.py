"""Circuit breaker pattern implementation for resilient Kafka connections."""

import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta

from src.utils.trace import get_logger
from src.config import config

logger = get_logger(__name__, config.logging.log_level)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for resilient Kafka connections."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        expected_exception: type = Exception
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening circuit
            recovery_timeout_seconds: Seconds to wait before trying recovery
            expected_exception: Exception type to catch
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    f"Circuit breaker {self.name} transitioning to HALF_OPEN",
                    operation="circuit_breaker",
                    state=self.state.value
                )
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.last_success_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info(
                f"Circuit breaker {self.name} recovered, transitioning to CLOSED",
                operation="circuit_breaker",
                state=self.state.value
            )

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        logger.warning(
            f"Circuit breaker {self.name} failure",
            operation="circuit_breaker",
            failure_count=self.failure_count,
            threshold=self.failure_threshold
        )
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker {self.name} opened after {self.failure_count} failures",
                operation="circuit_breaker",
                state=self.state.value
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout_seconds

    def get_state(self) -> dict:
        """Get circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None
        }


class ExponentialBackoff:
    """Exponential backoff with jitter for retries."""

    def __init__(
        self,
        initial_delay_ms: int = 100,
        max_delay_ms: int = 30000,
        multiplier: float = 2.0,
        jitter: bool = True
    ):
        """Initialize exponential backoff.
        
        Args:
            initial_delay_ms: Initial delay in milliseconds
            max_delay_ms: Maximum delay in milliseconds
            multiplier: Multiplier for each retry
            jitter: Add random jitter to delay
        """
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.multiplier = multiplier
        self.jitter = jitter
        self.attempt = 0

    async def wait(self):
        """Wait with exponential backoff."""
        delay_ms = min(
            self.initial_delay_ms * (self.multiplier ** self.attempt),
            self.max_delay_ms
        )
        
        if self.jitter:
            import random
            delay_ms = delay_ms * (0.5 + random.random())
        
        self.attempt += 1
        
        logger.debug(
            "Exponential backoff wait",
            operation="exponential_backoff",
            delay_ms=delay_ms,
            attempt=self.attempt
        )
        
        await asyncio.sleep(delay_ms / 1000.0)

    def reset(self):
        """Reset backoff counter."""
        self.attempt = 0

