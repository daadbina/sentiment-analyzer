"""PostgreSQL client with connection pooling."""

import asyncpg
import structlog
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from ..config import settings

logger = structlog.get_logger()


class PostgresClient:
    """PostgreSQL client for predictions data."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self):
        """Create connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_database,
                min_size=settings.postgres_pool_min_size,
                max_size=settings.postgres_pool_max_size,
            )
            logger.info(
                "postgres_connected",
                host=settings.postgres_host,
                database=settings.postgres_database,
            )
        except Exception as e:
            logger.error("postgres_connection_failed", error=str(e))
            raise
            
    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("postgres_disconnected")
            
    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error("postgres_health_check_failed", error=str(e))
            return False
            
    async def get_latest_predictions(
        self,
        limit: int = 100,
        min_confidence: float = 0.0,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get latest conflict predictions with country extraction."""
        query = """
            SELECT 
                id,
                group_id,
                domain,
                prediction_probability,
                prediction_confidence,
                model_version,
                features,
                predicted_at,
                created_at
            FROM predictions
            WHERE domain IN ('conflict', 'geopolitical')
                AND prediction_confidence >= $1
                AND predicted_at >= NOW() - INTERVAL '1 hour' * $2
            ORDER BY predicted_at DESC
            LIMIT $3
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, min_confidence, hours, limit)
                
            predictions = []
            for row in rows:
                # Extract countries from features JSONB
                features = row['features'] or {}
                countries = []
                
                # Try to extract country1 and country2 from features
                if 'country1' in features:
                    countries.append(features['country1'])
                if 'country2' in features:
                    countries.append(features['country2'])
                    
                # If no countries in features, try to extract from other fields
                if not countries and 'countries' in features:
                    countries = features['countries']
                    
                predictions.append({
                    'id': row['id'],
                    'group_id': row['group_id'],
                    'domain': row['domain'],
                    'prediction_probability': float(row['prediction_probability']),
                    'prediction_confidence': float(row['prediction_confidence']),
                    'model_version': row['model_version'],
                    'countries': countries,
                    'predicted_at': row['predicted_at'],
                    'created_at': row['created_at'],
                })
                
            logger.info(
                "latest_predictions_fetched",
                count=len(predictions),
                limit=limit,
                min_confidence=min_confidence,
            )
            return predictions
            
        except Exception as e:
            logger.error("get_latest_predictions_failed", error=str(e))
            raise

    async def get_country_risk_scores(self) -> List[Dict[str, Any]]:
        """Get aggregated risk scores by country."""
        query = """
            SELECT
                country,
                AVG(prediction_probability) as risk_score,
                COUNT(*) as prediction_count,
                AVG(prediction_confidence) as avg_confidence,
                MAX(predicted_at) as last_updated
            FROM (
                SELECT
                    jsonb_array_elements_text(
                        CASE
                            WHEN features ? 'country1' AND features ? 'country2' THEN
                                jsonb_build_array(features->'country1', features->'country2')
                            WHEN features ? 'countries' THEN
                                features->'countries'
                            ELSE '[]'::jsonb
                        END
                    ) as country,
                    prediction_probability,
                    prediction_confidence,
                    predicted_at
                FROM predictions
                WHERE domain IN ('conflict', 'geopolitical')
                    AND predicted_at >= NOW() - INTERVAL '24 hours'
            ) as country_predictions
            WHERE country IS NOT NULL AND country != ''
            GROUP BY country
            ORDER BY risk_score DESC
        """

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)

            results = []
            for row in rows:
                results.append({
                    'country': row['country'].strip('"'),  # Remove JSON quotes
                    'risk_score': float(row['risk_score']),
                    'prediction_count': row['prediction_count'],
                    'avg_confidence': float(row['avg_confidence']),
                    'last_updated': row['last_updated'],
                })

            logger.info("country_risk_scores_fetched", count=len(results))
            return results

        except Exception as e:
            logger.error("get_country_risk_scores_failed", error=str(e))
            raise

    async def get_trend_data(self, period: str = "day", days: int = 7) -> List[Dict[str, Any]]:
        """Get time-series trend data for conflict predictions."""
        if period == "day":
            interval = "1 day"
            trunc = "day"
        elif period == "week":
            interval = "1 week"
            trunc = "week"
        else:  # month
            interval = "1 month"
            trunc = "month"

        query = f"""
            SELECT
                DATE_TRUNC($1, predicted_at) as timestamp,
                COUNT(*) as prediction_count,
                AVG(prediction_probability) as avg_probability,
                AVG(prediction_confidence) as avg_confidence
            FROM predictions
            WHERE domain IN ('conflict', 'geopolitical')
                AND predicted_at >= NOW() - INTERVAL '1 day' * $2
            GROUP BY DATE_TRUNC($1, predicted_at)
            ORDER BY timestamp ASC
        """

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, trunc, days)

            results = []
            for row in rows:
                results.append({
                    'timestamp': row['timestamp'],
                    'prediction_count': row['prediction_count'],
                    'avg_probability': float(row['avg_probability']),
                    'avg_confidence': float(row['avg_confidence']),
                })

            logger.info("trend_data_fetched", period=period, count=len(results))
            return results

        except Exception as e:
            logger.error("get_trend_data_failed", error=str(e))
            raise

    async def get_top_country_pairs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top country pairs by conflict probability."""
        query = """
            SELECT
                features->>'country1' as country1,
                features->>'country2' as country2,
                AVG(prediction_probability) as avg_probability,
                AVG(prediction_confidence) as avg_confidence,
                COUNT(*) as prediction_count,
                MAX(predicted_at) as last_predicted
            FROM predictions
            WHERE domain IN ('conflict', 'geopolitical')
                AND features ? 'country1'
                AND features ? 'country2'
                AND predicted_at >= NOW() - INTERVAL '24 hours'
            GROUP BY features->>'country1', features->>'country2'
            ORDER BY avg_probability DESC
            LIMIT $1
        """

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, limit)

            results = []
            for row in rows:
                if row['country1'] and row['country2']:
                    results.append({
                        'country1': row['country1'],
                        'country2': row['country2'],
                        'probability': float(row['avg_probability']),
                        'confidence': float(row['avg_confidence']),
                        'prediction_count': row['prediction_count'],
                        'last_predicted': row['last_predicted'],
                    })

            logger.info("top_country_pairs_fetched", count=len(results))
            return results

        except Exception as e:
            logger.error("get_top_country_pairs_failed", error=str(e))
            raise

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get overall dashboard statistics."""
        query = """
            SELECT
                COUNT(*) as total_predictions,
                COUNT(DISTINCT
                    CASE
                        WHEN features ? 'country1' THEN features->>'country1'
                        WHEN features ? 'countries' THEN NULL
                    END
                ) + COUNT(DISTINCT
                    CASE
                        WHEN features ? 'country2' THEN features->>'country2'
                        WHEN features ? 'countries' THEN NULL
                    END
                ) as total_countries,
                AVG(prediction_probability) as avg_probability,
                AVG(prediction_confidence) as avg_confidence,
                COUNT(*) FILTER (WHERE prediction_probability > 0.7) as high_risk_count,
                MAX(predicted_at) as last_updated
            FROM predictions
            WHERE domain IN ('conflict', 'geopolitical')
                AND predicted_at >= NOW() - INTERVAL '24 hours'
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query)

            result = {
                'total_predictions': row['total_predictions'] or 0,
                'total_countries': row['total_countries'] or 0,
                'avg_probability': float(row['avg_probability']) if row['avg_probability'] else 0.0,
                'avg_confidence': float(row['avg_confidence']) if row['avg_confidence'] else 0.0,
                'high_risk_count': row['high_risk_count'] or 0,
                'last_updated': row['last_updated'] or datetime.utcnow(),
            }

            logger.info("dashboard_stats_fetched", stats=result)
            return result

        except Exception as e:
            logger.error("get_dashboard_stats_failed", error=str(e))
            raise

