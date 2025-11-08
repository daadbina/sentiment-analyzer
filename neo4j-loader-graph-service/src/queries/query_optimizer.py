"""
Query optimizer with Redis caching for Neo4j queries.
"""

from typing import Dict, Any, List, Optional
import hashlib
import json
import structlog
import redis

from ..clients.neo4j_client import neo4j_client
from ..config import config
from ..exceptions import QueryError
from ..metrics import (
    graph_query_duration_seconds,
    graph_query_cache_hits_total,
    graph_query_cache_misses_total,
)

logger = structlog.get_logger(__name__)


class QueryOptimizer:
    """
    Query optimizer with Redis caching.
    """

    def __init__(self):
        """Initialize query optimizer."""
        self.client = neo4j_client
        self.redis_client: Optional[redis.Redis] = None
        self.cache_ttl = config.redis_cache_ttl

    def connect_redis(self) -> None:
        """Connect to Redis for query caching."""
        try:
            self.redis_client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                db=config.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            self.redis_client.ping()
            
            logger.info(
                "redis_connected",
                host=config.redis_host,
                port=config.redis_port,
                db=config.redis_db,
            )
            
        except Exception as e:
            logger.warning(
                "redis_connection_failed",
                error=str(e),
                host=config.redis_host,
            )
            self.redis_client = None

    def close_redis(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            self.redis_client.close()
            logger.info("redis_connection_closed")

    def _generate_cache_key(
        self,
        query: str,
        params: Dict[str, Any],
    ) -> str:
        """
        Generate cache key from query and parameters.
        
        Args:
            query: Cypher query
            params: Query parameters
            
        Returns:
            Cache key
        """
        # Create deterministic string from query and params
        cache_input = f"{query}:{json.dumps(params, sort_keys=True)}"
        
        # Hash to create cache key
        cache_key = hashlib.sha256(cache_input.encode()).hexdigest()
        
        return f"neo4j:query:{cache_key}"

    def execute_with_cache(
        self,
        query: str,
        params: Dict[str, Any],
        cache_enabled: bool = True,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute query with Redis caching.
        
        Args:
            query: Cypher query
            params: Query parameters
            cache_enabled: Whether to use cache
            trace_id: Trace ID for correlation
            
        Returns:
            Query results
            
        Raises:
            QueryError: If query execution fails
        """
        # Try cache first if enabled
        if cache_enabled and self.redis_client:
            cache_key = self._generate_cache_key(query, params)
            
            try:
                cached_result = self.redis_client.get(cache_key)
                
                if cached_result:
                    # Cache hit
                    graph_query_cache_hits_total.inc()
                    
                    result = json.loads(cached_result)
                    
                    logger.debug(
                        "query_cache_hit",
                        cache_key=cache_key,
                        result_count=len(result),
                        trace_id=trace_id,
                    )
                    
                    return result
                    
            except Exception as e:
                logger.warning(
                    "cache_read_failed",
                    error=str(e),
                    trace_id=trace_id,
                )
        
        # Cache miss or cache disabled - execute query
        if cache_enabled and self.redis_client:
            graph_query_cache_misses_total.inc()
        
        try:
            import time
            start_time = time.time()
            
            # Execute query
            result = self.client.execute_query(query, params, trace_id=trace_id)
            
            duration = time.time() - start_time
            
            # Record metrics
            graph_query_duration_seconds.observe(duration)
            
            # Store in cache if enabled
            if cache_enabled and self.redis_client:
                cache_key = self._generate_cache_key(query, params)
                
                try:
                    # Serialize result
                    cached_value = json.dumps(result)
                    
                    # Store with TTL
                    self.redis_client.setex(
                        cache_key,
                        self.cache_ttl,
                        cached_value,
                    )
                    
                    logger.debug(
                        "query_result_cached",
                        cache_key=cache_key,
                        ttl_seconds=self.cache_ttl,
                        trace_id=trace_id,
                    )
                    
                except Exception as e:
                    logger.warning(
                        "cache_write_failed",
                        error=str(e),
                        trace_id=trace_id,
                    )
            
            logger.info(
                "query_executed",
                query_preview=query[:100],
                result_count=len(result),
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "query_execution_failed",
                query_preview=query[:100],
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Query execution failed: {str(e)}",
                query=query[:200],
                details={"error": str(e)},
            ) from e

    def invalidate_cache(
        self,
        pattern: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> int:
        """
        Invalidate cache entries.
        
        Args:
            pattern: Cache key pattern (None = all neo4j queries)
            trace_id: Trace ID for correlation
            
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            logger.warning("redis_not_connected", trace_id=trace_id)
            return 0
        
        try:
            # Default pattern for all Neo4j query cache
            if pattern is None:
                pattern = "neo4j:query:*"
            
            # Find matching keys
            keys = list(self.redis_client.scan_iter(match=pattern))
            
            if not keys:
                logger.debug(
                    "no_cache_keys_found",
                    pattern=pattern,
                    trace_id=trace_id,
                )
                return 0
            
            # Delete keys
            deleted_count = self.redis_client.delete(*keys)
            
            logger.info(
                "cache_invalidated",
                pattern=pattern,
                deleted_count=deleted_count,
                trace_id=trace_id,
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(
                "cache_invalidation_failed",
                pattern=pattern,
                error=str(e),
                trace_id=trace_id,
            )
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics
        """
        if not self.redis_client:
            return {
                "connected": False,
                "error": "Redis not connected",
            }
        
        try:
            info = self.redis_client.info("stats")
            
            # Count Neo4j query cache keys
            query_cache_keys = len(list(
                self.redis_client.scan_iter(match="neo4j:query:*", count=1000)
            ))
            
            return {
                "connected": True,
                "query_cache_keys": query_cache_keys,
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
            
        except Exception as e:
            logger.error("cache_stats_failed", error=str(e))
            return {
                "connected": False,
                "error": str(e),
            }


# Global query optimizer instance
query_optimizer = QueryOptimizer()

