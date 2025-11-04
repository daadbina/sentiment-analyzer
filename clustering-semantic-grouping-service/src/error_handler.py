"""Error handling and retry logic with exponential backoff."""

import logging
import asyncio
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retries
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class ErrorHandler:
    """Handles errors with retry logic and exponential backoff."""

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize error handler.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        logger.info(f"Initialized ErrorHandler: max_retries={self.config.max_retries}")

    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculate backoff delay with exponential backoff and jitter.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.config.initial_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return delay

    async def retry_async(
        self,
        func: Callable,
        *args,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> Any:
        """
        Retry async function with exponential backoff.

        Args:
            func: Async function to retry
            *args: Function arguments
            retryable_exceptions: Exceptions to retry on
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.config.max_retries + 1}")
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Succeeded after {attempt} retries")
                
                return result
                
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    delay = self.calculate_backoff(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_retries + 1} attempts failed")
        
        raise last_exception

    def retry_sync(
        self,
        func: Callable,
        *args,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> Any:
        """
        Retry sync function with exponential backoff.

        Args:
            func: Sync function to retry
            *args: Function arguments
            retryable_exceptions: Exceptions to retry on
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.config.max_retries + 1}")
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Succeeded after {attempt} retries")
                
                return result
                
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    delay = self.calculate_backoff(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    asyncio.run(asyncio.sleep(delay))
                else:
                    logger.error(f"All {self.config.max_retries + 1} attempts failed")
        
        raise last_exception

    def retry_decorator(
        self,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Decorator for retrying functions.

        Args:
            retryable_exceptions: Exceptions to retry on

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    return await self.retry_async(
                        func,
                        *args,
                        retryable_exceptions=retryable_exceptions,
                        **kwargs
                    )
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    return self.retry_sync(
                        func,
                        *args,
                        retryable_exceptions=retryable_exceptions,
                        **kwargs
                    )
                return sync_wrapper
        
        return decorator


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Timeout in seconds before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
        logger.info(
            f"Initialized CircuitBreaker: "
            f"threshold={failure_threshold}, timeout={recovery_timeout}s"
        )

    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.is_open = False
        logger.debug("Circuit breaker: success recorded")

    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )

    def can_execute(self) -> bool:
        """
        Check if operation can be executed.

        Returns:
            True if circuit is closed or recovery timeout expired
        """
        if not self.is_open:
            return True
        
        if self.last_failure_time:
            elapsed = (datetime.now() - self.last_failure_time).total_seconds()
            if elapsed >= self.recovery_timeout:
                logger.info("Circuit breaker: attempting recovery")
                self.is_open = False
                self.failure_count = 0
                return True
        
        return False

