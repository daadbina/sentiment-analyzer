"""Rate limiting for API endpoints."""

from typing import Optional
import logging
from datetime import datetime, timedelta

from src.clients import RedisClient
from src.exceptions import RateLimitError
from src.utils.logging import get_logger
from src.metrics import metrics_recorder

logger = get_logger(__name__)


class RateLimiter:
    """Rate limit API requests."""

    def __init__(
        self,
        redis_client: RedisClient,
        requests_per_window: int,
        window_seconds: int,
    ):
        """Initialize rate limiter.

        Args:
            redis_client: Redis client instance
            requests_per_window: Max requests per window
            window_seconds: Window duration in seconds
        """
        self.redis_client = redis_client
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.rate_limit_prefix = "rate_limit:"

    def _get_key(self, user_id: str, endpoint: str) -> str:
        """Get rate limit key.

        Args:
            user_id: User ID
            endpoint: Endpoint path

        Returns:
            Rate limit key
        """
        return f"{self.rate_limit_prefix}{user_id}:{endpoint}"

    async def check_limit(
        self,
        user_id: str,
        endpoint: str,
    ) -> bool:
        """Check if request is within rate limit.

        Args:
            user_id: User ID
            endpoint: Endpoint path

        Returns:
            True if within limit, False otherwise

        Raises:
            RateLimitError: If rate limit exceeded
        """
        try:
            key = self._get_key(user_id, endpoint)

            # Get current count
            current = await self.redis_client.get(key)
            count = int(current) if current else 0

            if count >= self.requests_per_window:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "extra_fields": {
                            "user_id": user_id,
                            "endpoint": endpoint,
                            "count": count,
                        }
                    },
                )
                metrics_recorder.record_rate_limit_exceeded(user_id, endpoint)
                raise RateLimitError(
                    message="Rate limit exceeded",
                    details={
                        "user_id": user_id,
                        "endpoint": endpoint,
                        "limit": self.requests_per_window,
                        "window_seconds": self.window_seconds,
                    },
                )

            # Increment count
            if count == 0:
                # First request in window
                await self.redis_client.set(
                    key,
                    1,
                    self.window_seconds,
                )
            else:
                # Increment existing counter
                # Note: Redis INCR would be better, but we're using set/get
                await self.redis_client.set(
                    key,
                    count + 1,
                    self.window_seconds,
                )

            return True

        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            # Fail open - allow request if rate limiter fails
            return True

    async def get_remaining(
        self,
        user_id: str,
        endpoint: str,
    ) -> int:
        """Get remaining requests in current window.

        Args:
            user_id: User ID
            endpoint: Endpoint path

        Returns:
            Remaining requests
        """
        try:
            key = self._get_key(user_id, endpoint)
            current = await self.redis_client.get(key)
            count = int(current) if current else 0

            return max(0, self.requests_per_window - count)

        except Exception as e:
            logger.error(f"Failed to get remaining requests: {str(e)}")
            return self.requests_per_window

    async def get_reset_time(
        self,
        user_id: str,
        endpoint: str,
    ) -> Optional[datetime]:
        """Get when rate limit resets.

        Args:
            user_id: User ID
            endpoint: Endpoint path

        Returns:
            Reset time or None
        """
        try:
            key = self._get_key(user_id, endpoint)
            ttl = await self.redis_client.get_ttl(key)

            if ttl > 0:
                return datetime.utcnow() + timedelta(seconds=ttl)

            return None

        except Exception as e:
            logger.error(f"Failed to get reset time: {str(e)}")
            return None

    async def reset(self, user_id: str, endpoint: str) -> None:
        """Reset rate limit for user/endpoint.

        Args:
            user_id: User ID
            endpoint: Endpoint path
        """
        try:
            key = self._get_key(user_id, endpoint)
            await self.redis_client.delete(key)

            logger.info(
                "Rate limit reset",
                extra={
                    "extra_fields": {
                        "user_id": user_id,
                        "endpoint": endpoint,
                    }
                },
            )

        except Exception as e:
            logger.error(f"Failed to reset rate limit: {str(e)}")


# Global rate limiter instance
rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance.

    Returns:
        Rate limiter instance

    Raises:
        RuntimeError: If rate limiter not initialized
    """
    global rate_limiter

    if rate_limiter is None:
        raise RuntimeError("Rate limiter not initialized")

    return rate_limiter


def init_rate_limiter(
    redis_client: RedisClient,
    requests_per_window: int,
    window_seconds: int,
) -> RateLimiter:
    """Initialize global rate limiter.

    Args:
        redis_client: Redis client instance
        requests_per_window: Max requests per window
        window_seconds: Window duration in seconds

    Returns:
        Rate limiter instance
    """
    global rate_limiter

    rate_limiter = RateLimiter(
        redis_client,
        requests_per_window,
        window_seconds,
    )

    logger.info(
        "Rate limiter initialized",
        extra={
            "extra_fields": {
                "requests_per_window": requests_per_window,
                "window_seconds": window_seconds,
            }
        },
    )

    return rate_limiter

