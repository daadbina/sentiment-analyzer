"""PostgreSQL client with connection pooling."""

import asyncpg
import structlog
import json
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
        """Get latest conflict predictions with country extraction from features and semantic_groups."""
        query = """
            SELECT
                p.id,
                p.group_id,
                p.domain,
                p.prediction_probability,
                p.prediction_confidence,
                p.model_version,
                p.features,
                p.predicted_at,
                p.created_at,
                sg.countries as sg_countries
            FROM predictions p
            LEFT JOIN semantic_groups sg ON p.group_id::uuid = sg.group_id
            WHERE p.domain IN ('conflict', 'geopolitical')
                AND p.prediction_confidence >= $1
                AND p.predicted_at >= NOW() - INTERVAL '1 hour' * $2
            ORDER BY p.predicted_at DESC
            LIMIT $3
        """

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, min_confidence, hours, limit)

            predictions = []
            for row in rows:
                # Parse features if it's a string (JSONB column)
                features = row['features']
                if isinstance(features, str):
                    try:
                        features = json.loads(features)
                    except (json.JSONDecodeError, TypeError):
                        features = {}
                elif features is None:
                    features = {}

                countries = []

                # Try to extract country1 and country2 from features
                if 'country1' in features:
                    countries.append(features['country1'])
                if 'country2' in features:
                    countries.append(features['country2'])

                # If no countries in features, try countries array from features
                if not countries and 'countries' in features:
                    countries = features['countries']

                # Fallback to semantic_groups.countries if still no countries
                if not countries and row['sg_countries']:
                    countries = row['sg_countries']

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
            logger.error("latest_predictions_fetch_failed", error=str(e))
            raise

    async def get_btc_predictions(
        self,
        limit: int = 10,
        min_confidence: float = 0.0,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get latest Bitcoin price predictions."""
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
            WHERE domain = 'btc'
                AND prediction_confidence >= $1
                AND predicted_at >= NOW() - INTERVAL '1 hour' * $2
            ORDER BY predicted_at DESC
            LIMIT $3
        """

        try:
            async with self.pool.acquire() as conn:
                # Fetch more rows than needed to allow for deduplication
                rows = await conn.fetch(query, min_confidence, hours, limit * 10)

            # Deduplicate predictions by grouping into 2-hour windows
            # Keep only the most recent prediction in each window
            predictions_by_window = {}

            for row in rows:
                # Parse features if it's a string (JSONB column)
                features = row['features']
                if isinstance(features, str):
                    try:
                        features = json.loads(features)
                    except (json.JSONDecodeError, TypeError):
                        features = {}
                elif features is None:
                    features = {}

                # Extract BTC-specific fields from root level of features
                # The predictor service stores them at the root level
                prediction_magnitude = features.get('prediction_magnitude', 0.0)
                prediction_direction = features.get('prediction_direction', 'neutral')
                prediction_strength = features.get('prediction_strength', 'unknown')
                prediction_description = features.get('prediction_description', '')

                # Group predictions into 2-hour windows (7200 seconds)
                # This ensures we don't show predictions within ±1 hour of each other
                predicted_at = row['predicted_at']
                window_key = int(predicted_at.timestamp() // 7200)  # 2-hour window

                # Keep only the most recent prediction in each window
                if window_key not in predictions_by_window:
                    predictions_by_window[window_key] = {
                        'id': row['id'],
                        'group_id': row['group_id'],
                        'domain': row['domain'],
                        'prediction_probability': float(row['prediction_probability']),
                        'prediction_confidence': float(row['prediction_confidence']),
                        'model_version': row['model_version'],
                        'features': features,
                        'predicted_at': row['predicted_at'],
                        'created_at': row['created_at'],
                        # BTC-specific fields
                        'prediction_magnitude': float(prediction_magnitude),
                        'prediction_direction': prediction_direction,
                        'prediction_strength': prediction_strength,
                        'prediction_description': prediction_description,
                    }

            # Convert to list and sort by predicted_at descending, then limit
            predictions = sorted(
                predictions_by_window.values(),
                key=lambda x: x['predicted_at'],
                reverse=True
            )[:limit]

            logger.info(
                "btc_predictions_fetched",
                count=len(predictions),
                limit=limit,
                min_confidence=min_confidence,
                deduplicated_from=len(rows),
            )
            return predictions

        except Exception as e:
            logger.error("btc_predictions_fetch_failed", error=str(e))
            raise
            
        except Exception as e:
            logger.error("get_latest_predictions_failed", error=str(e))
            raise

    async def get_country_risk_scores(self) -> List[Dict[str, Any]]:
        """Get aggregated risk scores by country from features and semantic_groups."""
        query = """
            SELECT
                country,
                AVG(prediction_probability) as risk_score,
                COUNT(*) as prediction_count,
                AVG(prediction_confidence) as avg_confidence,
                MAX(predicted_at) as last_updated
            FROM (
                SELECT
                    unnest(
                        CASE
                            -- First try features.country1 and country2
                            WHEN p.features ? 'country1' AND p.features ? 'country2' THEN
                                ARRAY[p.features->>'country1', p.features->>'country2']
                            -- Then try features.countries array
                            WHEN p.features ? 'countries' THEN
                                ARRAY(SELECT jsonb_array_elements_text(p.features->'countries'))
                            -- Fallback to semantic_groups.countries
                            WHEN sg.countries IS NOT NULL THEN
                                sg.countries
                            ELSE ARRAY[]::text[]
                        END
                    ) as country,
                    p.prediction_probability,
                    p.prediction_confidence,
                    p.predicted_at
                FROM predictions p
                LEFT JOIN semantic_groups sg ON p.group_id::uuid = sg.group_id
                WHERE p.domain IN ('conflict', 'geopolitical')
                    AND p.predicted_at >= NOW() - INTERVAL '24 hours'
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
                    'country': row['country'],
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
        """Get top country pairs by conflict probability from features and semantic_groups."""
        query = """
            WITH country_pairs AS (
                SELECT
                    p.prediction_probability,
                    p.prediction_confidence,
                    p.predicted_at,
                    -- Extract country1 and country2
                    CASE
                        WHEN p.features ? 'country1' THEN p.features->>'country1'
                        WHEN p.features ? 'countries' THEN
                            (SELECT jsonb_array_elements_text(p.features->'countries') LIMIT 1)
                        WHEN sg.countries IS NOT NULL AND array_length(sg.countries, 1) >= 1 THEN
                            sg.countries[1]
                        ELSE NULL
                    END as country1,
                    CASE
                        WHEN p.features ? 'country2' THEN p.features->>'country2'
                        WHEN p.features ? 'countries' THEN
                            (SELECT jsonb_array_elements_text(p.features->'countries') OFFSET 1 LIMIT 1)
                        WHEN sg.countries IS NOT NULL AND array_length(sg.countries, 1) >= 2 THEN
                            sg.countries[2]
                        ELSE NULL
                    END as country2
                FROM predictions p
                LEFT JOIN semantic_groups sg ON p.group_id::uuid = sg.group_id
                WHERE p.domain IN ('conflict', 'geopolitical')
                    AND p.predicted_at >= NOW() - INTERVAL '24 hours'
            )
            SELECT
                country1,
                country2,
                AVG(prediction_probability) as avg_probability,
                AVG(prediction_confidence) as avg_confidence,
                COUNT(*) as prediction_count,
                MAX(predicted_at) as last_predicted
            FROM country_pairs
            WHERE country1 IS NOT NULL AND country2 IS NOT NULL
                AND country1 != '' AND country2 != ''
            GROUP BY country1, country2
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
        """Get overall dashboard statistics from features and semantic_groups."""
        query = """
            WITH all_countries AS (
                SELECT DISTINCT
                    unnest(
                        CASE
                            -- First try features.country1 and country2
                            WHEN p.features ? 'country1' AND p.features ? 'country2' THEN
                                ARRAY[p.features->>'country1', p.features->>'country2']
                            -- Then try features.countries array
                            WHEN p.features ? 'countries' THEN
                                ARRAY(SELECT jsonb_array_elements_text(p.features->'countries'))
                            -- Fallback to semantic_groups.countries
                            WHEN sg.countries IS NOT NULL THEN
                                sg.countries
                            ELSE ARRAY[]::text[]
                        END
                    ) as country
                FROM predictions p
                LEFT JOIN semantic_groups sg ON p.group_id::uuid = sg.group_id
                WHERE p.domain IN ('conflict', 'geopolitical')
                    AND p.predicted_at >= NOW() - INTERVAL '24 hours'
            )
            SELECT
                (SELECT COUNT(*) FROM predictions
                 WHERE domain IN ('conflict', 'geopolitical')
                   AND predicted_at >= NOW() - INTERVAL '24 hours') as total_predictions,
                (SELECT COUNT(*) FROM all_countries WHERE country IS NOT NULL AND country != '') as total_countries,
                (SELECT AVG(prediction_probability) FROM predictions
                 WHERE domain IN ('conflict', 'geopolitical')
                   AND predicted_at >= NOW() - INTERVAL '24 hours') as avg_probability,
                (SELECT AVG(prediction_confidence) FROM predictions
                 WHERE domain IN ('conflict', 'geopolitical')
                   AND predicted_at >= NOW() - INTERVAL '24 hours') as avg_confidence,
                (SELECT COUNT(*) FROM predictions
                 WHERE domain IN ('conflict', 'geopolitical')
                   AND predicted_at >= NOW() - INTERVAL '24 hours'
                   AND prediction_probability > 0.7) as high_risk_count,
                (SELECT MAX(predicted_at) FROM predictions
                 WHERE domain IN ('conflict', 'geopolitical')
                   AND predicted_at >= NOW() - INTERVAL '24 hours') as last_updated
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

    async def get_network_graph_data(self, min_confidence: float = 0.5, hours: int = 168) -> Dict[str, Any]:
        """
        Get network graph data with nodes (countries) and edges (predictions).

        Args:
            min_confidence: Minimum confidence threshold
            hours: Time window in hours (default 168 = 7 days)

        Returns:
            Dict with 'nodes' (countries with risk scores) and 'links' (predictions between countries)
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            async with self.pool.acquire() as conn:
                # Get all predictions with country pairs
                # JOIN with semantic_groups to get countries array since predictions.features is often empty
                predictions_query = """
                    SELECT
                        p.id,
                        p.prediction_probability,
                        p.prediction_confidence,
                        p.features,
                        p.predicted_at,
                        p.model_version,
                        sg.countries
                    FROM predictions p
                    LEFT JOIN semantic_groups sg ON p.group_id::uuid = sg.group_id
                    WHERE p.domain IN ('conflict', 'geopolitical')
                        AND p.prediction_confidence >= $1
                        AND p.predicted_at >= $2
                    ORDER BY p.predicted_at DESC
                """

                rows = await conn.fetch(predictions_query, min_confidence, cutoff_time)

                # Extract country pairs and build graph structure
                nodes_dict = {}  # country_code -> {id, risk_score, prediction_count}
                links = []  # {source, target, probability, confidence, timestamp}

                for row in rows:
                    # Parse features if it's a string (JSONB column)
                    features = row['features']
                    if isinstance(features, str):
                        try:
                            features = json.loads(features)
                        except (json.JSONDecodeError, TypeError):
                            features = {}
                    elif features is None:
                        features = {}

                    # Extract countries from features
                    country1 = features.get('country1')
                    country2 = features.get('country2')

                    # Fallback to countries in features (could be array or comma-separated string)
                    if not country1 or not country2:
                        countries = features.get('countries', [])

                        # Handle case where countries is a comma-separated string
                        if isinstance(countries, str):
                            countries = [c.strip() for c in countries.split(',') if c.strip()]

                        if isinstance(countries, list) and len(countries) >= 2:
                            country1 = countries[0]
                            country2 = countries[1]

                    # Fallback to semantic_groups.countries array
                    if not country1 or not country2:
                        sg_countries = row.get('countries', [])
                        if sg_countries and len(sg_countries) >= 2:
                            country1 = sg_countries[0]
                            country2 = sg_countries[1]

                    if country1 and country2:
                        # Add countries to nodes
                        for country in [country1, country2]:
                            if country not in nodes_dict:
                                nodes_dict[country] = {
                                    'id': country,
                                    'name': country,
                                    'risk_score': 0.0,
                                    'prediction_count': 0,
                                    'total_confidence': 0.0,
                                }

                            # Update risk score (average confidence)
                            nodes_dict[country]['total_confidence'] += float(row['prediction_confidence'])
                            nodes_dict[country]['prediction_count'] += 1

                        # Add link
                        links.append({
                            'source': country1,
                            'target': country2,
                            'probability': float(row['prediction_probability']),
                            'confidence': float(row['prediction_confidence']),
                            'timestamp': row['predicted_at'].isoformat() if row['predicted_at'] else None,
                            'model_version': row['model_version'],
                        })

                # Calculate average risk scores for nodes (based on confidence)
                nodes = []
                for country_code, node_data in nodes_dict.items():
                    if node_data['prediction_count'] > 0:
                        node_data['risk_score'] = node_data['total_confidence'] / node_data['prediction_count']
                    del node_data['total_confidence']  # Remove temporary field
                    nodes.append(node_data)

                result = {
                    'nodes': nodes,
                    'links': links,
                    'metadata': {
                        'node_count': len(nodes),
                        'link_count': len(links),
                        'min_confidence': min_confidence,
                        'time_window_hours': hours,
                        'generated_at': datetime.utcnow().isoformat(),
                    }
                }

                logger.info(
                    "network_graph_data_fetched",
                    node_count=len(nodes),
                    link_count=len(links),
                )

                return result

        except Exception as e:
            logger.error("get_network_graph_data_failed", error=str(e))
            raise

