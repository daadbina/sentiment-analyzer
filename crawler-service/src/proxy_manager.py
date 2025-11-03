"""
Proxy manager for handling region-blocked feeds.

Implements proxy rotation strategy to bypass geographic restrictions on news feeds.
Follows Strategy Pattern for pluggable proxy providers.
"""

import logging
import random
from typing import Optional, List
from dataclasses import dataclass
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class Proxy:
    """Proxy configuration."""
    url: str
    protocol: str = "http"
    
    def get_proxy_url(self) -> str:
        """Get full proxy URL."""
        if self.url.startswith(("http://", "https://")):
            return self.url
        return f"{self.protocol}://{self.url}"


class ProxyProvider:
    """Base class for proxy providers."""
    
    async def get_proxies(self) -> List[Proxy]:
        """Get list of available proxies."""
        raise NotImplementedError


class FreeProxyProvider(ProxyProvider):
    """
    Free proxy provider using public proxy lists.
    
    Fetches proxies from free-proxy-list.net API.
    """
    
    def __init__(self):
        """Initialize free proxy provider."""
        self.proxies: List[Proxy] = []
        self.last_fetch = None
    
    async def get_proxies(self) -> List[Proxy]:
        """
        Get free proxies from public sources.
        
        Returns:
            List of available proxies.
        """
        # For now, return empty list - can be extended with actual free proxy APIs
        # This is a placeholder for future implementation
        return []


class ProxyRotator:
    """
    Proxy rotation manager.
    
    Implements Strategy Pattern for selecting proxies.
    Supports multiple proxy providers and rotation strategies.
    """
    
    def __init__(self, providers: Optional[List[ProxyProvider]] = None):
        """
        Initialize proxy rotator.
        
        Args:
            providers: List of proxy providers to use.
        """
        self.providers = providers or []
        self.proxies: List[Proxy] = []
        self.current_index = 0
        self.failed_proxies: set = set()
    
    async def refresh_proxies(self) -> None:
        """Refresh proxy list from all providers."""
        all_proxies = []
        for provider in self.providers:
            try:
                proxies = await provider.get_proxies()
                all_proxies.extend(proxies)
                logger.info(f"Fetched {len(proxies)} proxies from {provider.__class__.__name__}")
            except Exception as e:
                logger.warning(f"Failed to fetch proxies from {provider.__class__.__name__}: {e}")
        
        self.proxies = all_proxies
        self.current_index = 0
        self.failed_proxies.clear()
        logger.info(f"Proxy pool refreshed with {len(self.proxies)} proxies")
    
    def get_next_proxy(self) -> Optional[Proxy]:
        """
        Get next proxy in rotation.
        
        Returns:
            Next proxy or None if no proxies available.
        """
        if not self.proxies:
            return None
        
        # Skip failed proxies
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            
            if proxy.url not in self.failed_proxies:
                return proxy
            attempts += 1
        
        return None
    
    def get_random_proxy(self) -> Optional[Proxy]:
        """
        Get random proxy from pool.
        
        Returns:
            Random proxy or None if no proxies available.
        """
        if not self.proxies:
            return None
        
        available = [p for p in self.proxies if p.url not in self.failed_proxies]
        if not available:
            return None
        
        return random.choice(available)
    
    def mark_proxy_failed(self, proxy: Proxy) -> None:
        """
        Mark proxy as failed.
        
        Args:
            proxy: Proxy that failed.
        """
        self.failed_proxies.add(proxy.url)
        logger.warning(f"Marked proxy as failed: {proxy.url}")
    
    def reset_failed_proxies(self) -> None:
        """Reset failed proxy tracking."""
        self.failed_proxies.clear()
        logger.info("Reset failed proxy tracking")


class ProxyAwareSession:
    """
    HTTP session with proxy support.
    
    Wraps aiohttp.ClientSession with automatic proxy rotation.
    """
    
    def __init__(
        self,
        rotator: Optional[ProxyRotator] = None,
        use_proxy: bool = False,
    ):
        """
        Initialize proxy-aware session.
        
        Args:
            rotator: Proxy rotator instance.
            use_proxy: Whether to use proxies.
        """
        self.rotator = rotator
        self.use_proxy = use_proxy
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def start(self) -> None:
        """Start HTTP session."""
        if not self.session:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=10,
                ttl_dns_cache=300,
                ssl=ssl_context,
            )
            
            timeout = aiohttp.ClientTimeout(total=15, connect=10)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """
        GET request with optional proxy.
        
        Args:
            url: URL to fetch.
            **kwargs: Additional arguments for session.get().
        
        Returns:
            Response object.
        """
        if not self.session:
            await self.start()
        
        proxy_url = None
        if self.use_proxy and self.rotator:
            proxy = self.rotator.get_next_proxy()
            if proxy:
                proxy_url = proxy.get_proxy_url()
        
        return await self.session.get(url, proxy=proxy_url, **kwargs)


import ssl

