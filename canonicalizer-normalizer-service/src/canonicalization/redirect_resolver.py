"""URL redirect resolution and following."""

import logging
from typing import Optional
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class RedirectChain:
    """Result of redirect resolution."""

    original_url: str
    final_url: str
    redirect_count: int
    redirect_chain: list[str]
    has_loop: bool


class RedirectResolver:
    """Resolve URL redirects to final destination."""

    def __init__(self, max_redirects: int = 10, timeout: int = 5):
        """Initialize redirect resolver.

        Args:
            max_redirects: Maximum number of redirects to follow
            timeout: Request timeout in seconds
        """
        self.max_redirects = max_redirects
        self.timeout = timeout
        self.available = False
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize HTTP client."""
        try:
            import httpx
            self.client = httpx.AsyncClient(
                follow_redirects=False,
                timeout=self.timeout,
            )
            self.available = True
            logger.info("Redirect resolver initialized")
        except ImportError:
            logger.warning("httpx library not available, redirect resolution disabled")
            self.available = False
        except Exception as e:
            logger.error(f"Error initializing redirect resolver: {e}")
            self.available = False

    async def resolve_redirects(self, url: str) -> Optional[RedirectChain]:
        """Resolve URL redirects to final destination.

        Args:
            url: URL to resolve

        Returns:
            RedirectChain with final URL and redirect information
        """
        if not self.available or not url:
            return None

        try:
            redirect_chain = [url]
            current_url = url
            redirect_count = 0
            seen_urls = {url}

            while redirect_count < self.max_redirects:
                try:
                    response = await self.client.head(
                        current_url,
                        allow_redirects=False,
                        timeout=self.timeout,
                    )

                    # Check for redirect status codes
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get('location')
                        if not location:
                            break

                        # Handle relative redirects
                        if location.startswith('/'):
                            from urllib.parse import urlparse, urlunparse
                            parsed = urlparse(current_url)
                            location = urlunparse((
                                parsed.scheme,
                                parsed.netloc,
                                location,
                                '',
                                '',
                                ''
                            ))

                        # Check for redirect loops
                        if location in seen_urls:
                            return RedirectChain(
                                original_url=url,
                                final_url=current_url,
                                redirect_count=redirect_count,
                                redirect_chain=redirect_chain,
                                has_loop=True,
                            )

                        redirect_chain.append(location)
                        seen_urls.add(location)
                        current_url = location
                        redirect_count += 1
                    else:
                        # No more redirects
                        break

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout resolving redirects for {url}")
                    break
                except Exception as e:
                    logger.warning(f"Error following redirect: {e}")
                    break

            return RedirectChain(
                original_url=url,
                final_url=current_url,
                redirect_count=redirect_count,
                redirect_chain=redirect_chain,
                has_loop=False,
            )

        except Exception as e:
            logger.error(f"Error resolving redirects: {e}")
            return None

    def resolve_redirects_sync(self, url: str) -> Optional[RedirectChain]:
        """Synchronous wrapper for redirect resolution.

        Args:
            url: URL to resolve

        Returns:
            RedirectChain with final URL and redirect information
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, return None
                logger.warning("Cannot use sync wrapper in async context")
                return None
            return loop.run_until_complete(self.resolve_redirects(url))
        except RuntimeError:
            # No event loop, create new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.resolve_redirects(url))
            finally:
                loop.close()

    async def close(self) -> None:
        """Close HTTP client."""
        if self.available and self.client:
            await self.client.aclose()


class CachedRedirectResolver:
    """Redirect resolver with Redis caching."""

    def __init__(self, resolver: RedirectResolver, redis_client=None, ttl: int = 86400):
        """Initialize cached redirect resolver.

        Args:
            resolver: Base redirect resolver
            redis_client: Redis client for caching
            ttl: Cache TTL in seconds (default 24 hours)
        """
        self.resolver = resolver
        self.redis_client = redis_client
        self.ttl = ttl

    async def resolve_redirects(self, url: str) -> Optional[RedirectChain]:
        """Resolve redirects with caching.

        Args:
            url: URL to resolve

        Returns:
            RedirectChain with final URL
        """
        if not url:
            return None

        # Try to get from cache
        if self.redis_client:
            try:
                cache_key = f"redirect:{url}"
                cached = await self.redis_client.get(cache_key)
                if cached:
                    import json
                    data = json.loads(cached)
                    return RedirectChain(**data)
            except Exception as e:
                logger.warning(f"Error getting redirect from cache: {e}")

        # Resolve redirects
        result = await self.resolver.resolve_redirects(url)

        # Cache result
        if result and self.redis_client:
            try:
                import json
                cache_key = f"redirect:{url}"
                data = {
                    'original_url': result.original_url,
                    'final_url': result.final_url,
                    'redirect_count': result.redirect_count,
                    'redirect_chain': result.redirect_chain,
                    'has_loop': result.has_loop,
                }
                await self.redis_client.setex(
                    cache_key,
                    self.ttl,
                    json.dumps(data)
                )
            except Exception as e:
                logger.warning(f"Error caching redirect: {e}")

        return result

