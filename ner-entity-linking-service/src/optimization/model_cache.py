"""
Model caching optimization with LRU eviction policy.
"""
import logging
from typing import Dict, Any, Optional
from functools import lru_cache
from threading import Lock
from prometheus_client import Gauge, Counter, CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)

# Global metrics (registered once)
try:
    _cache_hits = REGISTRY._names_to_collectors.get("ner_model_cache_hits_total")
    if _cache_hits is None:
        _cache_hits = Counter(
            "ner_model_cache_hits_total",
            "Total model cache hits",
            ["model_id"],
        )
except:
    _cache_hits = Counter(
        "ner_model_cache_hits_total",
        "Total model cache hits",
        ["model_id"],
    )

try:
    _cache_misses = REGISTRY._names_to_collectors.get("ner_model_cache_misses_total")
    if _cache_misses is None:
        _cache_misses = Counter(
            "ner_model_cache_misses_total",
            "Total model cache misses",
            ["model_id"],
        )
except:
    _cache_misses = Counter(
        "ner_model_cache_misses_total",
        "Total model cache misses",
        ["model_id"],
    )

try:
    _cache_size = REGISTRY._names_to_collectors.get("ner_model_cache_size")
    if _cache_size is None:
        _cache_size = Gauge(
            "ner_model_cache_size",
            "Current model cache size",
        )
except:
    _cache_size = Gauge(
        "ner_model_cache_size",
        "Current model cache size",
    )

try:
    _cache_evictions = REGISTRY._names_to_collectors.get("ner_model_cache_evictions_total")
    if _cache_evictions is None:
        _cache_evictions = Counter(
            "ner_model_cache_evictions_total",
            "Total model cache evictions",
            ["model_id"],
        )
except:
    _cache_evictions = Counter(
        "ner_model_cache_evictions_total",
        "Total model cache evictions",
        ["model_id"],
    )


class ModelCache:
    """LRU cache for NER models with thread-safe access."""

    def __init__(self, max_size: int = 5):
        """
        Initialize model cache.

        Args:
            max_size: Maximum number of models to cache (default 5)
        """
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.lock = Lock()

        # Use global metrics
        self.cache_hits = _cache_hits
        self.cache_misses = _cache_misses
        self.cache_size = _cache_size
        self.cache_evictions = _cache_evictions

    def get(self, model_id: str) -> Optional[Any]:
        """
        Get model from cache.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Model if found, None otherwise
        """
        with self.lock:
            if model_id in self.cache:
                self.cache_hits.labels(model_id=model_id).inc()
                logger.debug(f"Cache hit for model {model_id}")
                return self.cache[model_id]
            else:
                self.cache_misses.labels(model_id=model_id).inc()
                logger.debug(f"Cache miss for model {model_id}")
                return None

    def put(self, model_id: str, model: Any) -> None:
        """
        Put model in cache with LRU eviction.
        
        Args:
            model_id: Model identifier
            model: Model object to cache
        """
        with self.lock:
            # If cache is full, evict least recently used
            if len(self.cache) >= self.max_size and model_id not in self.cache:
                # Remove first item (oldest)
                evicted_id = next(iter(self.cache))
                del self.cache[evicted_id]
                self.cache_evictions.labels(model_id=evicted_id).inc()
                logger.info(f"Evicted model {evicted_id} from cache")
            
            self.cache[model_id] = model
            self.cache_size.set(len(self.cache))
            logger.debug(f"Cached model {model_id}")

    def clear(self) -> None:
        """Clear all models from cache."""
        with self.lock:
            self.cache.clear()
            self.cache_size.set(0)
            logger.info("Cleared model cache")

    def size(self) -> int:
        """Get current cache size."""
        with self.lock:
            return len(self.cache)

    def contains(self, model_id: str) -> bool:
        """Check if model is in cache."""
        with self.lock:
            return model_id in self.cache


class BatchProcessor:
    """Batch processing optimization for entity extraction."""

    def __init__(self, batch_size: int = 32):
        """
        Initialize batch processor.

        Args:
            batch_size: Number of items to process in batch (default 32)
        """
        self.batch_size = batch_size

        # Use global metrics (avoid duplicate registration)
        try:
            self.batch_processing_time = REGISTRY._names_to_collectors.get("ner_batch_processing_duration_seconds")
            if self.batch_processing_time is None:
                self.batch_processing_time = Gauge(
                    "ner_batch_processing_duration_seconds",
                    "Batch processing duration in seconds",
                )
        except:
            self.batch_processing_time = Gauge(
                "ner_batch_processing_duration_seconds",
                "Batch processing duration in seconds",
            )

        try:
            self.batch_size_metric = REGISTRY._names_to_collectors.get("ner_batch_size")
            if self.batch_size_metric is None:
                self.batch_size_metric = Gauge(
                    "ner_batch_size",
                    "Current batch size",
                )
        except:
            self.batch_size_metric = Gauge(
                "ner_batch_size",
                "Current batch size",
            )

    def create_batches(self, items: list, batch_size: Optional[int] = None) -> list:
        """
        Create batches from items.
        
        Args:
            items: List of items to batch
            batch_size: Batch size (uses default if not specified)
            
        Returns:
            List of batches
        """
        if batch_size is None:
            batch_size = self.batch_size
        
        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batches.append(batch)
            self.batch_size_metric.set(len(batch))
        
        return batches


class ConnectionPoolOptimizer:
    """Optimize database connection pooling."""

    def __init__(self, pool_size: int = 20, max_overflow: int = 10):
        """
        Initialize connection pool optimizer.

        Args:
            pool_size: Base pool size (default 20)
            max_overflow: Maximum overflow connections (default 10)
        """
        self.pool_size = pool_size
        self.max_overflow = max_overflow

        # Use global metrics (avoid duplicate registration)
        try:
            self.pool_utilization = REGISTRY._names_to_collectors.get("ner_connection_pool_utilization")
            if self.pool_utilization is None:
                self.pool_utilization = Gauge(
                    "ner_connection_pool_utilization",
                    "Connection pool utilization percentage",
                )
        except:
            self.pool_utilization = Gauge(
                "ner_connection_pool_utilization",
                "Connection pool utilization percentage",
            )

        try:
            self.pool_wait_time = REGISTRY._names_to_collectors.get("ner_connection_pool_wait_time_seconds")
            if self.pool_wait_time is None:
                self.pool_wait_time = Gauge(
                    "ner_connection_pool_wait_time_seconds",
                    "Time waiting for connection from pool",
                )
        except:
            self.pool_wait_time = Gauge(
                "ner_connection_pool_wait_time_seconds",
                "Time waiting for connection from pool",
            )

    def get_optimal_pool_size(self, num_workers: int) -> int:
        """
        Calculate optimal pool size based on number of workers.
        
        Args:
            num_workers: Number of concurrent workers
            
        Returns:
            Recommended pool size
        """
        # Formula: pool_size = num_workers * 2 + 5
        optimal_size = max(num_workers * 2 + 5, self.pool_size)
        logger.info(f"Optimal pool size for {num_workers} workers: {optimal_size}")
        return optimal_size

    def get_optimal_overflow(self, pool_size: int) -> int:
        """
        Calculate optimal overflow size based on pool size.
        
        Args:
            pool_size: Base pool size
            
        Returns:
            Recommended overflow size
        """
        # Formula: overflow = pool_size / 2
        optimal_overflow = max(pool_size // 2, self.max_overflow)
        logger.info(f"Optimal overflow for pool size {pool_size}: {optimal_overflow}")
        return optimal_overflow


class QueryOptimizer:
    """Optimize database queries."""

    @staticmethod
    def add_indexes(connection) -> None:
        """
        Add indexes to optimize queries.
        
        Args:
            connection: Database connection
        """
        cursor = connection.cursor()
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_actors_normalized_name ON actors(normalized_name)",
            "CREATE INDEX IF NOT EXISTS idx_actors_wikidata_id ON actors(wikidata_id)",
            "CREATE INDEX IF NOT EXISTS idx_actors_type ON actors(type)",
            "CREATE INDEX IF NOT EXISTS idx_actors_country ON actors(country)",
            "CREATE INDEX IF NOT EXISTS idx_ner_audit_article_id ON ner_audit_log(article_id)",
            "CREATE INDEX IF NOT EXISTS idx_ner_audit_timestamp ON ner_audit_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_entity_linking_normalized ON entity_linking_log(normalized_text)",
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                logger.info(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Index creation failed: {e}")
        
        connection.commit()
        cursor.close()

    @staticmethod
    def analyze_tables(connection) -> None:
        """
        Analyze tables for query optimization.
        
        Args:
            connection: Database connection
        """
        cursor = connection.cursor()
        
        tables = ["actors", "ner_audit_log", "entity_linking_log", "ner_summary"]
        
        for table in tables:
            try:
                cursor.execute(f"ANALYZE {table}")
                logger.info(f"Analyzed table: {table}")
            except Exception as e:
                logger.warning(f"Table analysis failed for {table}: {e}")
        
        connection.commit()
        cursor.close()

