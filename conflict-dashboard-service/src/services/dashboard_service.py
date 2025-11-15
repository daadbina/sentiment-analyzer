"""Dashboard service with caching logic."""

import structlog
from typing import List, Dict, Any

from ..database import PostgresClient, RedisCache
from ..models import (
    ConflictPrediction,
    CountryRisk,
    TrendData,
    TrendDataPoint,
    CountryPair,
    DashboardStats,
)

logger = structlog.get_logger()


class DashboardService:
    """Service for dashboard data with caching."""
    
    def __init__(self, postgres: PostgresClient, cache: RedisCache):
        self.postgres = postgres
        self.cache = cache
        
    async def get_latest_predictions(
        self,
        limit: int = 100,
        min_confidence: float = 0.0,
        hours: int = 24,
    ) -> List[ConflictPrediction]:
        """Get latest predictions with caching."""
        cache_key = f"latest_predictions:{limit}:{min_confidence}:{hours}"
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("latest_predictions_from_cache", count=len(cached))
            return [ConflictPrediction(**p) for p in cached]
            
        # Fetch from database
        predictions = await self.postgres.get_latest_predictions(
            limit=limit,
            min_confidence=min_confidence,
            hours=hours,
        )
        
        # Cache the results
        await self.cache.set(cache_key, predictions)
        
        return [ConflictPrediction(**p) for p in predictions]
        
    async def get_country_risk_scores(self) -> List[CountryRisk]:
        """Get country risk scores with caching."""
        cache_key = "country_risk_scores"
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("country_risk_scores_from_cache", count=len(cached))
            return [CountryRisk(**c) for c in cached]
            
        # Fetch from database
        scores = await self.postgres.get_country_risk_scores()
        
        # Cache the results
        await self.cache.set(cache_key, scores)
        
        return [CountryRisk(**s) for s in scores]
        
    async def get_trend_data(self, period: str = "day", days: int = 7) -> TrendData:
        """Get trend data with caching."""
        cache_key = f"trend_data:{period}:{days}"
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("trend_data_from_cache", period=period)
            return TrendData(
                period=period,
                data_points=[TrendDataPoint(**dp) for dp in cached],
            )
            
        # Fetch from database
        data_points = await self.postgres.get_trend_data(period=period, days=days)
        
        # Cache the results
        await self.cache.set(cache_key, data_points)
        
        return TrendData(
            period=period,
            data_points=[TrendDataPoint(**dp) for dp in data_points],
        )
        
    async def get_top_country_pairs(self, limit: int = 10) -> List[CountryPair]:
        """Get top country pairs with caching."""
        cache_key = f"top_country_pairs:{limit}"
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("top_country_pairs_from_cache", count=len(cached))
            return [CountryPair(**cp) for cp in cached]
            
        # Fetch from database
        pairs = await self.postgres.get_top_country_pairs(limit=limit)
        
        # Cache the results
        await self.cache.set(cache_key, pairs)
        
        return [CountryPair(**cp) for cp in pairs]
        
    async def get_dashboard_stats(self) -> DashboardStats:
        """Get dashboard statistics with caching."""
        cache_key = "dashboard_stats"
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("dashboard_stats_from_cache")
            return DashboardStats(**cached)
            
        # Fetch from database
        stats = await self.postgres.get_dashboard_stats()

        # Cache the results
        await self.cache.set(cache_key, stats)

        return DashboardStats(**stats)

    async def get_network_graph_data(
        self,
        min_confidence: float = 0.5,
        hours: int = 168,
    ) -> Dict[str, Any]:
        """Get network graph data with caching."""
        cache_key = f"network_graph:{min_confidence}:{hours}"

        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("network_graph_from_cache")
            return cached

        # Fetch from database
        graph_data = await self.postgres.get_network_graph_data(
            min_confidence=min_confidence,
            hours=hours,
        )

        # Cache the results
        await self.cache.set(cache_key, graph_data)

        return graph_data

    async def get_btc_predictions(
        self,
        limit: int = 10,
        min_confidence: float = 0.0,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get Bitcoin predictions with caching."""
        cache_key = f"btc_predictions:{limit}:{min_confidence}:{hours}"

        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("btc_predictions_from_cache", count=len(cached))
            return cached

        # Fetch from database
        predictions = await self.postgres.get_btc_predictions(
            limit=limit,
            min_confidence=min_confidence,
            hours=hours,
        )

        # Cache the results
        await self.cache.set(cache_key, predictions)

        logger.info("get_btc_predictions_success", count=len(predictions))
        return predictions

