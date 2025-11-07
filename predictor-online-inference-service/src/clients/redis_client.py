"""
Redis client for caching predictions.

Provides abstraction over Redis for prediction caching with TTL support.
Implements cache-aside pattern with automatic serialization/deserialization.
"""

import logging
import json
from typing import Optional, Any
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from ..config import RedisConfig
from ..exceptions import CacheError
from ..utils.trace import trace_span
from ..metrics import redis_operation_duration_seconds, redis_errors_total


logger = logging.getLogger(__name__)


class RedisClient:
    """
    Client for interacting with Redis cache.
    
    Provides methods for caching predictions with automatic TTL management.
    Handles connection pooling and error recovery.
    """
    
    def __init__(self, config: RedisConfig):
        """
        Initialize Redis client.
        
        Args:
            config: Redis configuration
        """
        self.config = config
        self._client: Optional[Redis] = None
        
        logger.info(
            f"Initializing Redis client: host={config.host}, "
            f"port={config.port}, db={config.db}"
        )
    
    async def connect(self) -> None:
        """
        Connect to Redis server.
        
        Raises:
            CacheError: If connection fails
        """
        try:
            logger.info(f"Connecting to Redis: {self.config.host}:{self.config.port}")
            
            # Create Redis connection pool
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                ssl=self.config.ssl,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                decode_responses=True,  # Automatically decode responses to strings
            )
            
            # Test connection
            await self._client.ping()
            
            logger.info(
                f"Connected to Redis: host={self.config.host}, "
                f"port={self.config.port}, db={self.config.db}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            raise CacheError(
                f"Failed to connect to Redis: {e}",
                operation="connect",
            )
    
    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self._client:
            logger.info("Disconnecting from Redis")
            await self._client.close()
            self._client = None
    
    def _ensure_connected(self) -> Redis:
        """
        Ensure client is connected.
        
        Returns:
            Redis client instance
        
        Raises:
            CacheError: If not connected
        """
        if self._client is None:
            raise CacheError(
                "Redis client not connected. Call connect() first.",
                operation="ensure_connected",
            )
        return self._client
    
    async def get(
        self,
        key: str,
        trace_id: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            trace_id: Optional trace ID for distributed tracing
        
        Returns:
            Cached value as dictionary, or None if not found
        
        Raises:
            CacheError: If cache operation fails
        """
        client = self._ensure_connected()
        
        with trace_span(
            "redis_get",
            attributes={"key": key, "trace_id": trace_id},
        ):
            try:
                start_time = datetime.now()
                
                # Get value from Redis
                value = await client.get(key)
                
                # Record latency
                duration_seconds = (datetime.now() - start_time).total_seconds()
                redis_operation_duration_seconds.labels(operation="get").observe(duration_seconds)
                
                if value is None:
                    logger.debug(f"Cache miss: key={key}", extra={"trace_id": trace_id})
                    return None
                
                # Deserialize JSON
                result = json.loads(value)
                
                logger.debug(
                    f"Cache hit: key={key}, duration_seconds={duration_seconds:.4f}",
                    extra={"trace_id": trace_id},
                )
                
                return result
                
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to deserialize cached value: key={key}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                redis_errors_total.labels(operation="get", error_type="json_decode").inc()
                raise CacheError(
                    f"Failed to deserialize cached value: {e}",
                    operation="get",
                    key=key,
                    trace_id=trace_id,
                )
            except Exception as e:
                logger.error(
                    f"Failed to get from cache: key={key}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                redis_errors_total.labels(operation="get", error_type=type(e).__name__).inc()
                raise CacheError(
                    f"Failed to get from cache: {e}",
                    operation="get",
                    key=key,
                    trace_id=trace_id,
                )
    
    async def set(
        self,
        key: str,
        value: dict,
        ttl_seconds: Optional[int] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl_seconds: Time-to-live in seconds (None for no expiration)
            trace_id: Optional trace ID for distributed tracing
        
        Raises:
            CacheError: If cache operation fails
        """
        client = self._ensure_connected()
        
        with trace_span(
            "redis_set",
            attributes={"key": key, "ttl_seconds": ttl_seconds, "trace_id": trace_id},
        ):
            try:
                start_time = datetime.now()
                
                # Serialize to JSON
                serialized_value = json.dumps(value)
                
                # Set value in Redis with optional TTL
                if ttl_seconds:
                    await client.setex(key, ttl_seconds, serialized_value)
                else:
                    await client.set(key, serialized_value)
                
                # Record latency
                duration_seconds = (datetime.now() - start_time).total_seconds()
                redis_operation_duration_seconds.labels(operation="set").observe(duration_seconds)
                
                logger.debug(
                    f"Cache set: key={key}, ttl_seconds={ttl_seconds}, "
                    f"duration_seconds={duration_seconds:.4f}",
                    extra={"trace_id": trace_id},
                )
                
            except (TypeError, ValueError) as e:
                logger.error(
                    f"Failed to serialize value: key={key}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                redis_errors_total.labels(operation="set", error_type="json_encode").inc()
                raise CacheError(
                    f"Failed to serialize value: {e}",
                    operation="set",
                    key=key,
                    trace_id=trace_id,
                )
            except Exception as e:
                logger.error(
                    f"Failed to set in cache: key={key}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                redis_errors_total.labels(operation="set", error_type=type(e).__name__).inc()
                raise CacheError(
                    f"Failed to set in cache: {e}",
                    operation="set",
                    key=key,
                    trace_id=trace_id,
                )
    
    async def delete(
        self,
        key: str,
        trace_id: Optional[str] = None,
    ) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            trace_id: Optional trace ID for distributed tracing
        
        Returns:
            True if key was deleted, False if key didn't exist
        
        Raises:
            CacheError: If cache operation fails
        """
        client = self._ensure_connected()
        
        with trace_span(
            "redis_delete",
            attributes={"key": key, "trace_id": trace_id},
        ):
            try:
                start_time = datetime.now()
                
                # Delete key from Redis
                deleted_count = await client.delete(key)
                
                # Record latency
                duration_seconds = (datetime.now() - start_time).total_seconds()
                redis_operation_duration_seconds.labels(operation="delete").observe(duration_seconds)
                
                logger.debug(
                    f"Cache delete: key={key}, deleted={deleted_count > 0}, "
                    f"duration_seconds={duration_seconds:.4f}",
                    extra={"trace_id": trace_id},
                )
                
                return deleted_count > 0
                
            except Exception as e:
                logger.error(
                    f"Failed to delete from cache: key={key}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                redis_errors_total.labels(operation="delete", error_type=type(e).__name__).inc()
                raise CacheError(
                    f"Failed to delete from cache: {e}",
                    operation="delete",
                    key=key,
                    trace_id=trace_id,
                )
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if key exists, False otherwise
        """
        client = self._ensure_connected()
        
        try:
            return await client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Failed to check key existence: key={key}, error={e}")
            return False
    
    async def health_check(self) -> bool:
        """
        Check if Redis is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            client = self._ensure_connected()
            await client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False

