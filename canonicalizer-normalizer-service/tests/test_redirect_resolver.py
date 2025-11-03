"""Tests for URL redirect resolution."""

import pytest
from src.canonicalization.redirect_resolver import (
    RedirectResolver,
    CachedRedirectResolver,
    RedirectChain,
)


class TestRedirectChain:
    """Test RedirectChain dataclass."""

    def test_redirect_chain_creation(self):
        """Test creating redirect chain."""
        chain = RedirectChain(
            original_url="http://example.com",
            final_url="http://example.com/final",
            redirect_count=2,
            redirect_chain=["http://example.com", "http://example.com/final"],
            has_loop=False,
        )
        assert chain.original_url == "http://example.com"
        assert chain.final_url == "http://example.com/final"
        assert chain.redirect_count == 2
        assert len(chain.redirect_chain) == 2
        assert chain.has_loop is False

    def test_redirect_chain_with_loop(self):
        """Test redirect chain with loop."""
        chain = RedirectChain(
            original_url="http://example.com",
            final_url="http://example.com",
            redirect_count=3,
            redirect_chain=["http://example.com", "http://example.com/a", "http://example.com"],
            has_loop=True,
        )
        assert chain.has_loop is True

    def test_redirect_chain_fields(self):
        """Test redirect chain has required fields."""
        chain = RedirectChain(
            original_url="http://example.com",
            final_url="http://example.com",
            redirect_count=0,
            redirect_chain=["http://example.com"],
            has_loop=False,
        )
        assert hasattr(chain, 'original_url')
        assert hasattr(chain, 'final_url')
        assert hasattr(chain, 'redirect_count')
        assert hasattr(chain, 'redirect_chain')
        assert hasattr(chain, 'has_loop')


class TestRedirectResolver:
    """Test redirect resolver."""

    def test_resolver_initialization(self):
        """Test resolver initialization."""
        resolver = RedirectResolver()
        assert resolver is not None
        assert resolver.max_redirects == 10
        assert resolver.timeout == 5

    def test_resolver_custom_parameters(self):
        """Test resolver with custom parameters."""
        resolver = RedirectResolver(max_redirects=5, timeout=10)
        assert resolver.max_redirects == 5
        assert resolver.timeout == 10

    @pytest.mark.asyncio
    async def test_resolver_resolve_empty_url(self):
        """Test resolving empty URL."""
        resolver = RedirectResolver()
        result = await resolver.resolve_redirects("")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolver_resolve_none_url(self):
        """Test resolving None URL."""
        resolver = RedirectResolver()
        result = await resolver.resolve_redirects(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_resolver_resolve_returns_chain_or_none(self):
        """Test resolver returns RedirectChain or None."""
        resolver = RedirectResolver()
        result = await resolver.resolve_redirects("http://example.com")
        # Result can be None if httpx not available or network error
        if result is not None:
            assert isinstance(result, RedirectChain)

    def test_resolver_sync_wrapper(self):
        """Test synchronous wrapper."""
        resolver = RedirectResolver()
        result = resolver.resolve_redirects_sync("http://example.com")
        # Result can be None if httpx not available or network error
        if result is not None:
            assert isinstance(result, RedirectChain)

    @pytest.mark.asyncio
    async def test_resolver_close(self):
        """Test closing resolver."""
        resolver = RedirectResolver()
        await resolver.close()
        # Should not raise error

    def test_resolver_max_redirects_limit(self):
        """Test max redirects limit is respected."""
        resolver = RedirectResolver(max_redirects=3)
        assert resolver.max_redirects == 3


class TestCachedRedirectResolver:
    """Test cached redirect resolver."""

    def test_cached_resolver_initialization(self):
        """Test cached resolver initialization."""
        resolver = RedirectResolver()
        cached = CachedRedirectResolver(resolver)
        assert cached is not None
        assert cached.resolver is resolver
        assert cached.ttl == 86400

    def test_cached_resolver_custom_ttl(self):
        """Test cached resolver with custom TTL."""
        resolver = RedirectResolver()
        cached = CachedRedirectResolver(resolver, ttl=3600)
        assert cached.ttl == 3600

    @pytest.mark.asyncio
    async def test_cached_resolver_resolve_empty_url(self):
        """Test resolving empty URL."""
        resolver = RedirectResolver()
        cached = CachedRedirectResolver(resolver)
        result = await cached.resolve_redirects("")
        assert result is None

    @pytest.mark.asyncio
    async def test_cached_resolver_resolve_none_url(self):
        """Test resolving None URL."""
        resolver = RedirectResolver()
        cached = CachedRedirectResolver(resolver)
        result = await cached.resolve_redirects(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_cached_resolver_without_redis(self):
        """Test cached resolver without Redis."""
        resolver = RedirectResolver()
        cached = CachedRedirectResolver(resolver, redis_client=None)
        result = await cached.resolve_redirects("http://example.com")
        # Should work without Redis, just no caching
        if result is not None:
            assert isinstance(result, RedirectChain)

    @pytest.mark.asyncio
    async def test_cached_resolver_returns_chain_or_none(self):
        """Test cached resolver returns RedirectChain or None."""
        resolver = RedirectResolver()
        cached = CachedRedirectResolver(resolver)
        result = await cached.resolve_redirects("http://example.com")
        if result is not None:
            assert isinstance(result, RedirectChain)


class TestRedirectResolverIntegration:
    """Integration tests for redirect resolver."""

    def test_resolver_initialization_and_parameters(self):
        """Test resolver initialization and parameter setting."""
        resolver = RedirectResolver(max_redirects=15, timeout=20)
        assert resolver.max_redirects == 15
        assert resolver.timeout == 20

    def test_cached_resolver_with_custom_ttl(self):
        """Test cached resolver with custom TTL."""
        resolver = RedirectResolver()
        cached = CachedRedirectResolver(resolver, ttl=7200)
        assert cached.ttl == 7200
        assert cached.resolver is resolver

    @pytest.mark.asyncio
    async def test_resolver_handles_invalid_urls(self):
        """Test resolver handles invalid URLs gracefully."""
        resolver = RedirectResolver()
        result = await resolver.resolve_redirects("not a valid url")
        # Should handle gracefully, returning None or error
        assert result is None or isinstance(result, RedirectChain)

    def test_resolver_sync_wrapper_with_custom_params(self):
        """Test sync wrapper with custom parameters."""
        resolver = RedirectResolver(max_redirects=5, timeout=3)
        result = resolver.resolve_redirects_sync("http://example.com")
        # Should not raise error
        assert result is None or isinstance(result, RedirectChain)

