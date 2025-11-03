"""
HTTP fetcher for retrieving articles and feeds.

Implements async HTTP client with retry logic, circuit breaker, and timeout handling.
"""

import asyncio
import logging
import os
from typing import Optional
from datetime import datetime, timedelta
import aiohttp
from aiohttp import ClientSession, ClientConnectorError, ClientSSLError, TCPConnector
import ssl

from .exceptions import FetchError, CircuitBreakerOpenError
from .config import get_settings

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit breaker for handling failing sources.

    Prevents cascading failures by temporarily disabling sources that fail repeatedly.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        timeout_minutes: int = 10,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit.
            timeout_minutes: Minutes to keep circuit open.
        """
        self.failure_threshold = failure_threshold
        self.timeout_minutes = timeout_minutes
        self.failures: dict[str, int] = {}
        self.open_until: dict[str, datetime] = {}

    def record_failure(self, feed_id: str) -> None:
        """
        Record a failure for a feed source.

        Args:
            feed_id: Feed source identifier.
        """
        self.failures[feed_id] = self.failures.get(feed_id, 0) + 1

        if self.failures[feed_id] >= self.failure_threshold:
            self.open_until[feed_id] = (
                datetime.utcnow() + timedelta(minutes=self.timeout_minutes)
            )
            logger.warning(
                f"Circuit breaker opened for {feed_id} after "
                f"{self.failures[feed_id]} failures"
            )

    def record_success(self, feed_id: str) -> None:
        """
        Record a successful request for a feed source.

        Args:
            feed_id: Feed source identifier.
        """
        self.failures[feed_id] = 0
        self.open_until.pop(feed_id, None)

    def is_open(self, feed_id: str) -> bool:
        """
        Check if circuit breaker is open for a feed source.

        Args:
            feed_id: Feed source identifier.

        Returns:
            bool: True if circuit is open.
        """
        if feed_id not in self.open_until:
            return False

        if datetime.utcnow() > self.open_until[feed_id]:
            # Circuit timeout expired, close it
            self.open_until.pop(feed_id)
            self.failures[feed_id] = 0
            logger.info(f"Circuit breaker closed for {feed_id}")
            return False

        return True


class HTTPFetcher:
    """
    Async HTTP client for fetching articles and feeds.

    Implements retry logic, circuit breaker, and timeout handling.
    """

    def __init__(self) -> None:
        """Initialize HTTP fetcher."""
        self.settings = get_settings()
        self.session: Optional[ClientSession] = None
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.settings.circuit_breaker_failure_threshold,
            timeout_minutes=self.settings.circuit_breaker_timeout_minutes,
        )

    async def __aenter__(self) -> "HTTPFetcher":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()

    async def start(self) -> None:
        """Start HTTP session with optimized network configuration."""
        if not self.session:
            # Create SSL context that accepts self-signed certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Create TCP connector with optimized settings
            connector = TCPConnector(
                limit=100,  # Max connections
                limit_per_host=10,  # Max connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                ssl=ssl_context,
                enable_cleanup_closed=True,
                force_close=False,
            )

            # Create session with timeout and connector
            timeout = aiohttp.ClientTimeout(
                total=self.settings.request_timeout_seconds,
                connect=10,
                sock_read=10,
                sock_connect=10,
            )

            self.session = ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            logger.info("HTTP fetcher started with optimized network configuration")

    async def stop(self) -> None:
        """Stop HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("HTTP fetcher stopped")

    async def fetch(
        self,
        url: str,
        feed_id: str = "",
        timeout: Optional[int] = None,
    ) -> tuple[str, str]:
        """
        Fetch content from URL with advanced retry logic and error handling.

        Args:
            url: URL to fetch.
            feed_id: Feed source identifier for circuit breaker.
            timeout: Request timeout in seconds.

        Returns:
            tuple[str, str]: (content, content_type)

        Raises:
            FetchError: If fetch fails after retries.
            CircuitBreakerOpenError: If circuit breaker is open.
        """
        if feed_id and self.circuit_breaker.is_open(feed_id):
            raise CircuitBreakerOpenError(
                f"Circuit breaker is open for {feed_id}",
                feed_id=feed_id,
            )

        timeout_seconds = timeout or self.settings.request_timeout_seconds
        max_retries = self.settings.max_retries
        backoff_seconds = self.settings.retry_backoff_seconds

        last_error = None
        attempt_errors = []

        for attempt in range(max_retries + 1):
            try:
                if not self.session:
                    await self.start()

                logger.debug(f"Fetch attempt {attempt + 1}/{max_retries + 1} for {url}")

                # Try with SSL verification disabled first
                async with self.session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout_seconds),
                    ssl=False,
                    allow_redirects=True,
                ) as response:
                    if response.status == 200:
                        content = await response.text(errors='replace')
                        content_type = response.headers.get("Content-Type", "text/html")

                        if feed_id:
                            self.circuit_breaker.record_success(feed_id)

                        logger.info(f"Successfully fetched {url} (attempt {attempt + 1})")
                        return content, content_type

                    elif response.status in (301, 302, 303, 307, 308):
                        # Redirect - will be handled by allow_redirects=True
                        logger.warning(f"Redirect {response.status} for {url}")
                        raise FetchError(
                            f"HTTP {response.status} (redirect not followed)",
                            url=url,
                            status_code=response.status,
                            error_code="HTTP_REDIRECT",
                        )
                    else:
                        raise FetchError(
                            f"HTTP {response.status}",
                            url=url,
                            status_code=response.status,
                            error_code="HTTP_ERROR",
                        )

            except (ClientConnectorError, ClientSSLError, asyncio.TimeoutError, OSError) as e:
                last_error = e
                attempt_errors.append(str(e))

                if attempt < max_retries:
                    wait_time = backoff_seconds * (2**attempt)
                    logger.warning(
                        f"Fetch attempt {attempt + 1} failed for {url}, "
                        f"retrying in {wait_time}s: {type(e).__name__}: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Fetch failed after {max_retries + 1} attempts for {url}. "
                        f"Errors: {attempt_errors}"
                    )

            except FetchError as e:
                last_error = e
                attempt_errors.append(str(e))
                if attempt < max_retries:
                    wait_time = backoff_seconds * (2**attempt)
                    logger.warning(
                        f"Fetch error on attempt {attempt + 1}, retrying in {wait_time}s: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Fetch failed after {max_retries + 1} attempts: {str(e)}")

            except Exception as e:
                last_error = e
                attempt_errors.append(str(e))
                logger.error(f"Unexpected error fetching {url} on attempt {attempt + 1}: {type(e).__name__}: {str(e)}")
                if attempt < max_retries:
                    wait_time = backoff_seconds * (2**attempt)
                    await asyncio.sleep(wait_time)

        if feed_id:
            self.circuit_breaker.record_failure(feed_id)

        error_summary = "; ".join(attempt_errors[-3:])  # Last 3 errors
        raise FetchError(
            f"Failed to fetch {url} after {max_retries + 1} attempts: {error_summary}",
            url=url,
            error_code="FETCH_FAILED",
        )
