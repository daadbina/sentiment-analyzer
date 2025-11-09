"""
Prediction cache for storing predictions in Redis.

Implements cache-aside pattern for prediction caching.
Provides TTL-based expiration for cache entries.
"""

import logging
from typing import Any

from ..clients import RedisClient
from ..exceptions import CacheError
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class PredictionCache:
    """
    Cache for storing predictions in Redis.

    Implements cache-aside pattern with TTL-based expiration.
    """

    def __init__(self, redis_client: RedisClient, ttl_seconds: int = 3600):
        """
        Initialize prediction cache.

        Args:
            redis_client: Redis client instance
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds

        logger.info(f"Initialized prediction cache: ttl={ttl_seconds}s")

    async def get_cached_prediction(
        self,
        group_id: str,
        domain: str,
        trace_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get cached prediction for a semantic group and domain.

        Args:
            group_id: Semantic group ID
            domain: Domain of prediction (btc/conflict/geopolitical)
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Cached prediction dictionary or None if not found
        """
        with trace_span(
            "get_cached_prediction",
            attributes={"group_id": group_id, "domain": domain, "trace_id": trace_id},
        ):
            try:
                cache_key = self._get_cache_key(group_id, domain)

                # Get from Redis
                cached_data = await self.redis_client.get(cache_key, trace_id)

                if cached_data is None:
                    logger.debug(
                        f"Cache miss: group_id={group_id}, domain={domain}",
                        extra={"trace_id": trace_id, "group_id": group_id, "domain": domain},
                    )
                    return None

                logger.debug(
                    f"Cache hit: group_id={group_id}, domain={domain}",
                    extra={"trace_id": trace_id, "group_id": group_id, "domain": domain},
                )

                return cached_data

            except CacheError:
                # Log but don't fail on cache errors
                logger.warning(
                    f"Cache get failed: group_id={group_id}, domain={domain}",
                    extra={"trace_id": trace_id},
                )
                return None
            except Exception as e:
                logger.warning(
                    f"Unexpected cache error: group_id={group_id}, domain={domain}, error={e}",
                    extra={"trace_id": trace_id},
                )
                return None

    async def cache_prediction(
        self,
        group_id: str,
        prediction: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Cache prediction for a semantic group.

        Args:
            group_id: Semantic group ID
            prediction: Prediction dictionary to cache (must contain 'domain' key)
            trace_id: Optional trace ID for distributed tracing
        """
        # Extract domain from prediction
        domain = prediction.get("domain", "conflict")

        with trace_span(
            "cache_prediction",
            attributes={"group_id": group_id, "domain": domain, "trace_id": trace_id},
        ):
            try:
                cache_key = self._get_cache_key(group_id, domain)

                # Store in Redis with TTL
                await self.redis_client.set(
                    cache_key,
                    prediction,
                    ttl_seconds=self.ttl_seconds,
                    trace_id=trace_id,
                )

                logger.debug(
                    f"Prediction cached: group_id={group_id}, domain={domain}, ttl={self.ttl_seconds}s",
                    extra={"trace_id": trace_id, "group_id": group_id, "domain": domain},
                )

            except CacheError:
                # Log but don't fail on cache errors
                logger.warning(
                    f"Cache set failed: group_id={group_id}, domain={domain}",
                    extra={"trace_id": trace_id},
                )
            except Exception as e:
                logger.warning(
                    f"Unexpected cache error: group_id={group_id}, domain={domain}, error={e}",
                    extra={"trace_id": trace_id},
                )

    async def invalidate_prediction(
        self,
        group_id: str,
        domain: str,
        trace_id: str | None = None,
    ) -> None:
        """
        Invalidate cached prediction for a semantic group and domain.

        Args:
            group_id: Semantic group ID
            domain: Domain of prediction (btc/conflict/geopolitical)
            trace_id: Optional trace ID for distributed tracing
        """
        with trace_span(
            "invalidate_cached_prediction",
            attributes={"group_id": group_id, "domain": domain, "trace_id": trace_id},
        ):
            try:
                cache_key = self._get_cache_key(group_id, domain)

                # Delete from Redis
                await self.redis_client.delete(cache_key, trace_id)

                logger.debug(
                    f"Prediction invalidated: group_id={group_id}, domain={domain}",
                    extra={"trace_id": trace_id, "group_id": group_id, "domain": domain},
                )

            except CacheError:
                # Log but don't fail on cache errors
                logger.warning(
                    f"Cache delete failed: group_id={group_id}, domain={domain}",
                    extra={"trace_id": trace_id},
                )
            except Exception as e:
                logger.warning(
                    f"Unexpected cache error: group_id={group_id}, domain={domain}, error={e}",
                    extra={"trace_id": trace_id},
                )

    def _get_cache_key(self, group_id: str, domain: str) -> str:
        """
        Get Redis cache key for a group ID and domain.

        Args:
            group_id: Semantic group ID
            domain: Domain of prediction (btc/conflict/geopolitical)

        Returns:
            Redis cache key
        """
        return f"prediction:{group_id}:{domain}"
