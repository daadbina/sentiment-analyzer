"""Tests for cache manager."""

import pytest
from src.optimization.cache_manager import (
    CacheManager,
    NormalizationResultCache,
    CacheStats,
)


class TestCacheStats:
    """Test cache statistics."""

    def test_cache_stats_initialization(self):
        """Test cache stats initialization."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0

    def test_cache_stats_hit_rate_zero(self):
        """Test hit rate with zero accesses."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_cache_stats_hit_rate_all_hits(self):
        """Test hit rate with all hits."""
        stats = CacheStats(hits=10, misses=0)
        assert stats.hit_rate == 1.0

    def test_cache_stats_hit_rate_all_misses(self):
        """Test hit rate with all misses."""
        stats = CacheStats(hits=0, misses=10)
        assert stats.hit_rate == 0.0

    def test_cache_stats_hit_rate_mixed(self):
        """Test hit rate with mixed hits and misses."""
        stats = CacheStats(hits=7, misses=3)
        assert stats.hit_rate == 0.7


class TestCacheManager:
    """Test cache manager."""

    def test_cache_manager_initialization(self):
        """Test cache manager initialization."""
        manager = CacheManager()
        assert manager is not None
        assert manager.ttl == 3600
        assert manager.redis_client is None

    def test_cache_manager_custom_ttl(self):
        """Test cache manager with custom TTL."""
        manager = CacheManager(ttl=7200)
        assert manager.ttl == 7200

    @pytest.mark.asyncio
    async def test_cache_manager_get_miss(self):
        """Test cache get on miss."""
        manager = CacheManager()
        result = await manager.get("nonexistent")
        assert result is None
        assert manager.stats.misses == 1

    @pytest.mark.asyncio
    async def test_cache_manager_set_and_get(self):
        """Test cache set and get."""
        manager = CacheManager()
        await manager.set("key1", {"value": "test"})
        result = await manager.get("key1")
        assert result == {"value": "test"}
        assert manager.stats.hits == 1

    @pytest.mark.asyncio
    async def test_cache_manager_delete(self):
        """Test cache delete."""
        manager = CacheManager()
        await manager.set("key1", "value1")
        await manager.delete("key1")
        result = await manager.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_manager_clear(self):
        """Test cache clear."""
        manager = CacheManager()
        await manager.set("key1", "value1")
        await manager.set("key2", "value2")
        await manager.clear()
        result1 = await manager.get("key1")
        result2 = await manager.get("key2")
        assert result1 is None
        assert result2 is None

    @pytest.mark.asyncio
    async def test_cache_manager_get_stats(self):
        """Test getting cache stats."""
        manager = CacheManager()
        await manager.set("key1", "value1")
        await manager.get("key1")
        await manager.get("nonexistent")
        stats = manager.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1

    @pytest.mark.asyncio
    async def test_cache_manager_reset_stats(self):
        """Test resetting cache stats."""
        manager = CacheManager()
        await manager.set("key1", "value1")
        await manager.get("key1")
        manager.reset_stats()
        stats = manager.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0


class TestNormalizationResultCache:
    """Test normalization result cache."""

    def test_normalization_cache_initialization(self):
        """Test normalization cache initialization."""
        manager = CacheManager()
        cache = NormalizationResultCache(manager)
        assert cache is not None
        assert cache.cache_manager is manager

    @pytest.mark.asyncio
    async def test_get_canonicalization_miss(self):
        """Test getting canonicalization on miss."""
        manager = CacheManager()
        cache = NormalizationResultCache(manager)
        result = await cache.get_canonicalization("http://example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_canonicalization(self):
        """Test setting and getting canonicalization."""
        manager = CacheManager()
        cache = NormalizationResultCache(manager)
        canon_result = {"url": "http://example.com", "canonical": "http://example.com/"}
        await cache.set_canonicalization("http://example.com", canon_result)
        result = await cache.get_canonicalization("http://example.com")
        assert result == canon_result

    @pytest.mark.asyncio
    async def test_set_and_get_classification(self):
        """Test setting and getting classification."""
        manager = CacheManager()
        cache = NormalizationResultCache(manager)
        class_result = {"domain": "politics", "confidence": 0.95}
        await cache.set_classification("hash123", class_result)
        result = await cache.get_classification("hash123")
        assert result == class_result

    @pytest.mark.asyncio
    async def test_set_and_get_publisher(self):
        """Test setting and getting publisher."""
        manager = CacheManager()
        cache = NormalizationResultCache(manager)
        pub_info = {"domain": "example.com", "credibility": 0.9}
        await cache.set_publisher("example.com", pub_info)
        result = await cache.get_publisher("example.com")
        assert result == pub_info

    @pytest.mark.asyncio
    async def test_invalidate_url(self):
        """Test invalidating URL cache."""
        manager = CacheManager()
        cache = NormalizationResultCache(manager)
        canon_result = {"url": "http://example.com"}
        await cache.set_canonicalization("http://example.com", canon_result)
        await cache.invalidate_url("http://example.com")
        result = await cache.get_canonicalization("http://example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_content(self):
        """Test invalidating content cache."""
        manager = CacheManager()
        cache = NormalizationResultCache(manager)
        class_result = {"domain": "politics"}
        await cache.set_classification("hash123", class_result)
        await cache.invalidate_content("hash123")
        result = await cache.get_classification("hash123")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_publisher(self):
        """Test invalidating publisher cache."""
        manager = CacheManager()
        cache = NormalizationResultCache(manager)
        pub_info = {"domain": "example.com"}
        await cache.set_publisher("example.com", pub_info)
        await cache.invalidate_publisher("example.com")
        result = await cache.get_publisher("example.com")
        assert result is None

