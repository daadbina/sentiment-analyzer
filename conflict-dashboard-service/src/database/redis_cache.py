"""Redis cache client."""

import json
import redis.asyncio as redis
import structlog
from typing import Optional, Any

from ..config import settings

logger = structlog.get_logger()


class RedisCache:
    """Redis cache for dashboard data."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        
    async def connect(self):
        """Connect to Redis."""
        try:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
            )
            # Test connection
            await self.client.ping()
            logger.info(
                "redis_connected",
                host=settings.redis_host,
                port=settings.redis_port,
            )
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise
            
    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("redis_disconnected")
            
    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return False
            
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.client.get(key)
            if value:
                logger.debug("cache_hit", key=key)
                return json.loads(value)
            logger.debug("cache_miss", key=key)
            return None
        except Exception as e:
            logger.error("cache_get_failed", key=key, error=str(e))
            return None
            
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with TTL."""
        try:
            ttl = ttl or settings.cache_ttl
            await self.client.setex(
                key,
                ttl,
                json.dumps(value, default=str),
            )
            logger.debug("cache_set", key=key, ttl=ttl)
        except Exception as e:
            logger.error("cache_set_failed", key=key, error=str(e))
            
    async def delete(self, key: str):
        """Delete key from cache."""
        try:
            await self.client.delete(key)
            logger.debug("cache_deleted", key=key)
        except Exception as e:
            logger.error("cache_delete_failed", key=key, error=str(e))
            
    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern."""
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self.client.delete(*keys)
                logger.info("cache_pattern_cleared", pattern=pattern, count=len(keys))
        except Exception as e:
            logger.error("cache_clear_pattern_failed", pattern=pattern, error=str(e))

