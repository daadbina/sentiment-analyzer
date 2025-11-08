"""
Circuit breaker implementation for Neo4j Loader Graph Service.
Provides fault tolerance and prevents cascading failures.
"""

from typing import Callable, Any, Optional
from enum import Enum
import time
import structlog
from functools import wraps

from ..exceptions import CircuitBreakerError
from ..metrics import circuit_breaker_state, circuit_breaker_failures_total

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by stopping requests to a failing service
    and allowing it time to recover.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name for identification
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        
        # Update initial state metric
        circuit_breaker_state.labels(
            circuit_name=self.name,
            state=self._state.value,
        ).set(1)
        
        logger.info(
            "circuit_breaker_initialized",
            name=self.name,
            failure_threshold=self.failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    def _set_state(self, new_state: CircuitState) -> None:
        """
        Set circuit state and update metrics.
        
        Args:
            new_state: New circuit state
        """
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            
            # Update metrics
            circuit_breaker_state.labels(
                circuit_name=self.name,
                state=old_state.value,
            ).set(0)
            circuit_breaker_state.labels(
                circuit_name=self.name,
                state=new_state.value,
            ).set(1)
            
            logger.info(
                "circuit_breaker_state_changed",
                name=self.name,
                old_state=old_state.value,
                new_state=new_state.value,
                failure_count=self._failure_count,
            )

    def _should_attempt_reset(self) -> bool:
        """
        Check if circuit should attempt to reset.
        
        Returns:
            True if recovery timeout has elapsed
        """
        if self._last_failure_time is None:
            return False
        
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.recovery_timeout

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function raises exception
        """
        # Check if circuit is open
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(
                    "circuit_breaker_attempting_reset",
                    name=self.name,
                )
                self._set_state(CircuitState.HALF_OPEN)
            else:
                logger.warning(
                    "circuit_breaker_open",
                    name=self.name,
                    failure_count=self._failure_count,
                )
                raise CircuitBreakerError(
                    message=f"Circuit breaker '{self.name}' is open",
                    circuit_name=self.name,
                    state=self._state.value,
                )
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Success - reset failure count
            self._on_success()
            
            return result
            
        except self.expected_exception as e:
            # Failure - increment count and potentially open circuit
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful function execution."""
        self._failure_count = 0
        self._last_success_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            logger.info(
                "circuit_breaker_recovered",
                name=self.name,
            )
            self._set_state(CircuitState.CLOSED)

    def _on_failure(self) -> None:
        """Handle failed function execution."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        circuit_breaker_failures_total.labels(
            circuit_name=self.name,
        ).inc()
        
        logger.warning(
            "circuit_breaker_failure",
            name=self.name,
            failure_count=self._failure_count,
            threshold=self.failure_threshold,
        )
        
        if self._failure_count >= self.failure_threshold:
            logger.error(
                "circuit_breaker_opening",
                name=self.name,
                failure_count=self._failure_count,
            )
            self._set_state(CircuitState.OPEN)

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        logger.info(
            "circuit_breaker_manual_reset",
            name=self.name,
        )
        self._failure_count = 0
        self._last_failure_time = None
        self._set_state(CircuitState.CLOSED)


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
):
    """
    Decorator for circuit breaker protection.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds to wait before recovery attempt
        expected_exception: Exception type to catch
        
    Returns:
        Decorated function
        
    Example:
        @circuit_breaker(name="neo4j", failure_threshold=5)
        def query_neo4j():
            # Query logic
            pass
    """
    breaker = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
    )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    
    return decorator

