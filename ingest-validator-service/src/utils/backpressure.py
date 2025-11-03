"""Backpressure handling for Kafka consumer."""

import logging
import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BackpressureManager:
    """Manages backpressure handling for Kafka consumer.
    
    Monitors consumer lag and applies dynamic throttling when:
    1. Consumer lag exceeds threshold
    2. Circuit breakers are open
    3. Downstream services are unhealthy
    """

    def __init__(
        self,
        lag_threshold: int = 10000,
        throttle_delay_ms: int = 100,
        max_throttle_delay_ms: int = 5000,
    ):
        """Initialize backpressure manager.
        
        Args:
            lag_threshold: Consumer lag threshold (messages)
            throttle_delay_ms: Initial throttle delay (milliseconds)
            max_throttle_delay_ms: Maximum throttle delay (milliseconds)
        """
        self.lag_threshold = lag_threshold
        self.throttle_delay_ms = throttle_delay_ms
        self.max_throttle_delay_ms = max_throttle_delay_ms
        
        # State tracking
        self.current_throttle_delay_ms = throttle_delay_ms
        self.is_throttled = False
        self.throttle_start_time: Optional[datetime] = None
        self.circuit_breaker_open = False
        self.last_lag_check: Optional[datetime] = None
        self.last_lag_values: Dict[int, int] = {}  # partition -> lag

    def update_consumer_lag(self, lag_dict: Dict[int, int]) -> None:
        """Update consumer lag values.
        
        Args:
            lag_dict: Dictionary of partition -> lag
        """
        self.last_lag_values = lag_dict
        self.last_lag_check = datetime.utcnow()

    def get_max_lag(self) -> int:
        """Get maximum lag across all partitions.
        
        Returns:
            Maximum lag value
        """
        if not self.last_lag_values:
            return 0
        return max(self.last_lag_values.values())

    def should_throttle(self) -> bool:
        """Check if consumer should be throttled.
        
        Returns:
            True if throttling should be applied
        """
        max_lag = self.get_max_lag()
        
        # Check lag threshold
        if max_lag > self.lag_threshold:
            if not self.is_throttled:
                logger.warning(
                    f"Consumer lag {max_lag} exceeds threshold {self.lag_threshold}, "
                    f"applying backpressure"
                )
                self.is_throttled = True
                self.throttle_start_time = datetime.utcnow()
                self.current_throttle_delay_ms = self.throttle_delay_ms
            return True
        
        # Check if circuit breaker is open
        if self.circuit_breaker_open:
            if not self.is_throttled:
                logger.warning("Circuit breaker open, applying backpressure")
                self.is_throttled = True
                self.throttle_start_time = datetime.utcnow()
                self.current_throttle_delay_ms = self.throttle_delay_ms
            return True
        
        # Lag is below threshold and circuit breaker is closed
        if self.is_throttled:
            logger.info(
                f"Consumer lag {max_lag} below threshold {self.lag_threshold}, "
                f"removing backpressure"
            )
            self.is_throttled = False
            self.throttle_start_time = None
            self.current_throttle_delay_ms = self.throttle_delay_ms
        
        return False

    async def apply_throttle(self) -> None:
        """Apply throttle delay if needed."""
        if self.should_throttle():
            # Exponential backoff: increase delay up to max
            delay_seconds = min(
                self.current_throttle_delay_ms / 1000.0,
                self.max_throttle_delay_ms / 1000.0,
            )
            
            logger.debug(
                f"Applying backpressure: throttle delay {delay_seconds:.2f}s, "
                f"max lag {self.get_max_lag()}"
            )
            
            await asyncio.sleep(delay_seconds)
            
            # Increase delay for next iteration (exponential backoff)
            self.current_throttle_delay_ms = min(
                int(self.current_throttle_delay_ms * 1.5),
                self.max_throttle_delay_ms,
            )

    def set_circuit_breaker_open(self, is_open: bool) -> None:
        """Set circuit breaker state.
        
        Args:
            is_open: True if circuit breaker is open
        """
        if is_open != self.circuit_breaker_open:
            self.circuit_breaker_open = is_open
            if is_open:
                logger.warning("Circuit breaker opened, enabling backpressure")
            else:
                logger.info("Circuit breaker closed, may disable backpressure")

    def get_status(self) -> dict:
        """Get backpressure status.
        
        Returns:
            Status dictionary
        """
        return {
            "is_throttled": self.is_throttled,
            "current_throttle_delay_ms": self.current_throttle_delay_ms,
            "max_lag": self.get_max_lag(),
            "lag_threshold": self.lag_threshold,
            "circuit_breaker_open": self.circuit_breaker_open,
            "throttle_duration_seconds": (
                (datetime.utcnow() - self.throttle_start_time).total_seconds()
                if self.throttle_start_time
                else 0
            ),
            "lag_by_partition": self.last_lag_values,
        }

