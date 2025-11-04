"""
Tests for optimization module.
"""
import pytest
from src.optimization.model_cache import (
    ModelCache,
    BatchProcessor,
    ConnectionPoolOptimizer,
    QueryOptimizer,
)


class TestModelCache:
    """Tests for model cache."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = ModelCache(max_size=5)
        assert cache.max_size == 5
        assert cache.size() == 0

    def test_cache_put_and_get(self):
        """Test putting and getting from cache."""
        cache = ModelCache(max_size=5)
        model = {"name": "test-model", "version": "1.0"}
        
        cache.put("model-1", model)
        retrieved = cache.get("model-1")
        
        assert retrieved == model
        assert cache.size() == 1

    def test_cache_miss(self):
        """Test cache miss."""
        cache = ModelCache(max_size=5)
        retrieved = cache.get("nonexistent")
        assert retrieved is None

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = ModelCache(max_size=3)
        
        # Fill cache
        cache.put("model-1", {"id": 1})
        cache.put("model-2", {"id": 2})
        cache.put("model-3", {"id": 3})
        
        assert cache.size() == 3
        
        # Add one more (should evict model-1)
        cache.put("model-4", {"id": 4})
        
        assert cache.size() == 3
        assert cache.get("model-1") is None
        assert cache.get("model-4") is not None

    def test_cache_contains(self):
        """Test checking if model is in cache."""
        cache = ModelCache(max_size=5)
        cache.put("model-1", {"id": 1})
        
        assert cache.contains("model-1")
        assert not cache.contains("model-2")

    def test_cache_clear(self):
        """Test clearing cache."""
        cache = ModelCache(max_size=5)
        cache.put("model-1", {"id": 1})
        cache.put("model-2", {"id": 2})
        
        cache.clear()
        
        assert cache.size() == 0
        assert cache.get("model-1") is None


class TestBatchProcessor:
    """Tests for batch processor."""

    def test_batch_processor_initialization(self):
        """Test batch processor initialization."""
        processor = BatchProcessor(batch_size=32)
        assert processor.batch_size == 32

    def test_create_batches(self):
        """Test creating batches."""
        processor = BatchProcessor(batch_size=3)
        items = list(range(10))
        
        batches = processor.create_batches(items)
        
        assert len(batches) == 4
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 3
        assert len(batches[3]) == 1

    def test_create_batches_custom_size(self):
        """Test creating batches with custom size."""
        processor = BatchProcessor(batch_size=32)
        items = list(range(100))
        
        batches = processor.create_batches(items, batch_size=25)
        
        assert len(batches) == 4
        assert len(batches[0]) == 25
        assert len(batches[3]) == 25

    def test_create_batches_empty_list(self):
        """Test creating batches from empty list."""
        processor = BatchProcessor(batch_size=32)
        items = []
        
        batches = processor.create_batches(items)
        
        assert len(batches) == 0

    def test_create_batches_single_item(self):
        """Test creating batches with single item."""
        processor = BatchProcessor(batch_size=32)
        items = [1]
        
        batches = processor.create_batches(items)
        
        assert len(batches) == 1
        assert batches[0] == [1]


class TestConnectionPoolOptimizer:
    """Tests for connection pool optimizer."""

    def test_pool_optimizer_initialization(self):
        """Test pool optimizer initialization."""
        optimizer = ConnectionPoolOptimizer(pool_size=20, max_overflow=10)
        assert optimizer.pool_size == 20
        assert optimizer.max_overflow == 10

    def test_optimal_pool_size_calculation(self):
        """Test optimal pool size calculation."""
        optimizer = ConnectionPoolOptimizer(pool_size=20, max_overflow=10)
        
        # For 4 workers: 4 * 2 + 5 = 13
        optimal_size = optimizer.get_optimal_pool_size(4)
        assert optimal_size >= 13

    def test_optimal_overflow_calculation(self):
        """Test optimal overflow calculation."""
        optimizer = ConnectionPoolOptimizer(pool_size=20, max_overflow=10)
        
        # For pool size 20: 20 / 2 = 10
        optimal_overflow = optimizer.get_optimal_overflow(20)
        assert optimal_overflow >= 10

    def test_pool_size_scales_with_workers(self):
        """Test pool size scales with number of workers."""
        optimizer = ConnectionPoolOptimizer(pool_size=20, max_overflow=10)
        
        size_4 = optimizer.get_optimal_pool_size(4)
        size_8 = optimizer.get_optimal_pool_size(8)
        
        assert size_8 > size_4


class TestQueryOptimizer:
    """Tests for query optimizer."""

    def test_query_optimizer_exists(self):
        """Test query optimizer class exists."""
        assert QueryOptimizer is not None

    def test_add_indexes_method_exists(self):
        """Test add_indexes method exists."""
        assert hasattr(QueryOptimizer, "add_indexes")

    def test_analyze_tables_method_exists(self):
        """Test analyze_tables method exists."""
        assert hasattr(QueryOptimizer, "analyze_tables")

