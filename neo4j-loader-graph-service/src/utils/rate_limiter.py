"""
Rate limiter implementation for Neo4j Loader Graph Service.
Provides backpressure management to prevent overwhelming Neo4j.
"""

from typing import Optional
import time
import asyncio
import structlog
from collections import deque

from ..metrics import rate_limiter_queue_size, rate_limiter_wait_time_seconds

logger = structlog.get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rate.
    
    Implements backpressure by limiting the rate of operations
    and queuing excess requests.
    """

    def __init__(
        self,
        name: str,
        max_rate: int = 1000,  # Max operations per second
        max_queue_size: int = 1000,  # Max queued operations
        burst_size: Optional[int] = None,  # Max burst size
    ):
        """
        Initialize rate limiter.
        
        Args:
            name: Rate limiter name for identification
            max_rate: Maximum operations per second
            max_queue_size: Maximum queue size for backpressure
            burst_size: Maximum burst size (defaults to max_rate)
        """
        self.name = name
        self.max_rate = max_rate
        self.max_queue_size = max_queue_size
        self.burst_size = burst_size or max_rate
        
        # Token bucket
        self._tokens = float(self.burst_size)
        self._last_update = time.time()
        
        # Queue for backpressure
        self._queue: deque = deque()
        self._lock = asyncio.Lock()
        
        logger.info(
            "rate_limiter_initialized",
            name=self.name,
            max_rate=self.max_rate,
            max_queue_size=self.max_queue_size,
            burst_size=self.burst_size,
        )

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.max_rate
        self._tokens = min(self.burst_size, self._tokens + tokens_to_add)
        self._last_update = now

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens from the rate limiter.
        
        Blocks if insufficient tokens are available.
        
        Args:
            tokens: Number of tokens to acquire
            
        Raises:
            ValueError: If tokens exceeds burst_size
        """
        if tokens > self.burst_size:
            raise ValueError(
                f"Requested tokens ({tokens}) exceeds burst size ({self.burst_size})"
            )
        
        async with self._lock:
            # Check queue size for backpressure
            if len(self._queue) >= self.max_queue_size:
                logger.warning(
                    "rate_limiter_queue_full",
                    name=self.name,
                    queue_size=len(self._queue),
                    max_queue_size=self.max_queue_size,
                )
                # Wait for queue to drain
                while len(self._queue) >= self.max_queue_size:
                    await asyncio.sleep(0.1)
            
            # Add to queue
            self._queue.append(tokens)
            
            # Update queue size metric
            rate_limiter_queue_size.labels(
                limiter_name=self.name,
            ).set(len(self._queue))
            
            start_time = time.time()
            
            # Wait for tokens
            while True:
                self._refill_tokens()
                
                if self._tokens >= tokens:
                    # Consume tokens
                    self._tokens -= tokens
                    self._queue.popleft()
                    
                    # Update metrics
                    wait_time = time.time() - start_time
                    rate_limiter_wait_time_seconds.labels(
                        limiter_name=self.name,
                    ).observe(wait_time)
                    
                    rate_limiter_queue_size.labels(
                        limiter_name=self.name,
                    ).set(len(self._queue))
                    
                    if wait_time > 1.0:
                        logger.debug(
                            "rate_limiter_acquired_after_wait",
                            name=self.name,
                            tokens=tokens,
                            wait_time_seconds=wait_time,
                        )
                    
                    return
                
                # Calculate wait time
                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed / self.max_rate
                
                # Wait for tokens to refill
                await asyncio.sleep(min(wait_time, 0.1))

    async def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        if tokens > self.burst_size:
            return False
        
        async with self._lock:
            self._refill_tokens()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            
            return False

    def get_queue_size(self) -> int:
        """
        Get current queue size.
        
        Returns:
            Number of operations in queue
        """
        return len(self._queue)

    def is_queue_full(self) -> bool:
        """
        Check if queue is full.
        
        Returns:
            True if queue is at max capacity
        """
        return len(self._queue) >= self.max_queue_size

    def get_available_tokens(self) -> float:
        """
        Get number of available tokens.
        
        Returns:
            Number of available tokens
        """
        self._refill_tokens()
        return self._tokens

    async def wait_for_capacity(self, threshold: float = 0.5) -> None:
        """
        Wait until queue has capacity.
        
        Args:
            threshold: Queue capacity threshold (0.0-1.0)
        """
        max_size = int(self.max_queue_size * threshold)
        
        while len(self._queue) > max_size:
            logger.debug(
                "rate_limiter_waiting_for_capacity",
                name=self.name,
                queue_size=len(self._queue),
                threshold_size=max_size,
            )
            await asyncio.sleep(0.5)


class BackpressureManager:
    """
    Manages backpressure across multiple rate limiters.
    
    Coordinates rate limiting for different operations to prevent
    overwhelming downstream services.
    """

    def __init__(self):
        """Initialize backpressure manager."""
        self._limiters: dict[str, RateLimiter] = {}
        
        logger.info("backpressure_manager_initialized")

    def create_limiter(
        self,
        name: str,
        max_rate: int = 1000,
        max_queue_size: int = 1000,
        burst_size: Optional[int] = None,
    ) -> RateLimiter:
        """
        Create a new rate limiter.
        
        Args:
            name: Rate limiter name
            max_rate: Maximum operations per second
            max_queue_size: Maximum queue size
            burst_size: Maximum burst size
            
        Returns:
            Created rate limiter
        """
        limiter = RateLimiter(
            name=name,
            max_rate=max_rate,
            max_queue_size=max_queue_size,
            burst_size=burst_size,
        )
        
        self._limiters[name] = limiter
        
        return limiter

    def get_limiter(self, name: str) -> Optional[RateLimiter]:
        """
        Get rate limiter by name.
        
        Args:
            name: Rate limiter name
            
        Returns:
            Rate limiter or None if not found
        """
        return self._limiters.get(name)

    def get_total_queue_size(self) -> int:
        """
        Get total queue size across all limiters.
        
        Returns:
            Total number of queued operations
        """
        return sum(limiter.get_queue_size() for limiter in self._limiters.values())

    async def wait_for_all_capacity(self, threshold: float = 0.5) -> None:
        """
        Wait until all limiters have capacity.
        
        Args:
            threshold: Queue capacity threshold (0.0-1.0)
        """
        await asyncio.gather(*[
            limiter.wait_for_capacity(threshold)
            for limiter in self._limiters.values()
        ])


# Global backpressure manager instance
backpressure_manager = BackpressureManager()

