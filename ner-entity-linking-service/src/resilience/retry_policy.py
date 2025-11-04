"""Retry policy for resilience."""

import time
import logging
import random
from typing import Callable, Any, Optional, List, Type
from enum import Enum

logger = logging.getLogger(__name__)


class BackoffStrategy(str, Enum):
    """Backoff strategies for retries."""

    FIXED = "FIXED"
    LINEAR = "LINEAR"
    EXPONENTIAL = "EXPONENTIAL"
    RANDOM = "RANDOM"


class RetryPolicy:
    """Retry policy for handling transient failures."""

    def __init__(
        self,
        name: str,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        """Initialize retry policy.

        Args:
            name: Policy name
            max_attempts: Maximum number of attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_strategy: Backoff strategy to use
            retryable_exceptions: List of exceptions to retry on
        """
        self.name = name
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_strategy = backoff_strategy
        self.retryable_exceptions = retryable_exceptions or [Exception]
        self.attempt_count = 0
        self.last_exception: Optional[Exception] = None

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry policy.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries fail
        """
        self.attempt_count = 0
        self.last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            self.attempt_count = attempt
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"Retry policy {self.name} succeeded on attempt {attempt}")
                return result
            except Exception as e:
                self.last_exception = e
                if not self._is_retryable(e):
                    raise
                if attempt == self.max_attempts:
                    logger.error(
                        f"Retry policy {self.name} failed after {self.max_attempts} attempts"
                    )
                    raise
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Retry policy {self.name} attempt {attempt} failed, "
                    f"retrying in {delay:.2f}s: {str(e)}"
                )
                time.sleep(delay)

    def _is_retryable(self, exception: Exception) -> bool:
        """Check if exception is retryable.

        Args:
            exception: Exception to check

        Returns:
            True if exception is retryable
        """
        return any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions)

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Delay in seconds
        """
        if self.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.initial_delay
        elif self.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.initial_delay * attempt
        elif self.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.initial_delay * (2 ** (attempt - 1))
        elif self.backoff_strategy == BackoffStrategy.RANDOM:
            delay = random.uniform(self.initial_delay, self.max_delay)
        else:
            delay = self.initial_delay

        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, delay * 0.1)
        delay = min(delay + jitter, self.max_delay)
        return delay

    def get_stats(self) -> dict:
        """Get retry statistics.

        Returns:
            Dictionary with retry stats
        """
        return {
            "name": self.name,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "last_exception": str(self.last_exception) if self.last_exception else None,
        }


class RetryPolicyRegistry:
    """Registry for managing multiple retry policies."""

    def __init__(self):
        """Initialize retry policy registry."""
        self.policies: dict[str, RetryPolicy] = {}

    def register(
        self,
        name: str,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
    ) -> RetryPolicy:
        """Register a new retry policy.

        Args:
            name: Policy name
            max_attempts: Maximum number of attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_strategy: Backoff strategy to use
            retryable_exceptions: List of exceptions to retry on

        Returns:
            RetryPolicy instance
        """
        if name not in self.policies:
            policy = RetryPolicy(
                name=name,
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                backoff_strategy=backoff_strategy,
                retryable_exceptions=retryable_exceptions,
            )
            self.policies[name] = policy
            logger.info(f"Registered retry policy: {name}")
        return self.policies[name]

    def get(self, name: str) -> Optional[RetryPolicy]:
        """Get retry policy by name.

        Args:
            name: Policy name

        Returns:
            RetryPolicy instance or None
        """
        return self.policies.get(name)


# Global registry
_registry = RetryPolicyRegistry()


def get_retry_policy(
    name: str,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
) -> RetryPolicy:
    """Get or create a retry policy.

    Args:
        name: Policy name
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_strategy: Backoff strategy to use
        retryable_exceptions: List of exceptions to retry on

    Returns:
        RetryPolicy instance
    """
    return _registry.register(
        name=name,
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_strategy=backoff_strategy,
        retryable_exceptions=retryable_exceptions,
    )

