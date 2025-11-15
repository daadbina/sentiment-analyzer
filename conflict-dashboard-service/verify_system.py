#!/usr/bin/env python3
"""
System Verification Script
This script mimics how the conflict-dashboard-service reads, fetches, and extracts data.
It verifies the database schema and tests all data extraction queries.
"""

import asyncio
import asyncpg
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sys


# Database configuration (from config.py)
DB_CONFIG = {
    'host': '154.53.166.231',
    'port': 5432,
    'user': 'adminsentiment',
    'password': 'wp2400!!!!',
    'database': 'sentiment',
}


class SystemVerifier:
    """Verifies the system's database schema and data extraction logic."""
    
    def __init__(self):
        self.conn = None
        
    async def connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.conn = await asyncpg.connect(**DB_CONFIG)
            print(f"✓ Connected to database: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from database."""
        if self.conn:
            await self.conn.close()
            print("✓ Disconnected from database")
            
    async def verify_schema(self):
        """Verify database schema matches expected structure."""
        print("\n" + "="*80)
        print("SCHEMA VERIFICATION")
        print("="*80)
        
        # Check predictions table
        print("\n1. Checking 'predictions' table...")
        predictions_schema = await self.conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'predictions'
            ORDER BY ordinal_position
        """)
        
        if not predictions_schema:
            print("✗ Table 'predictions' does not exist!")
            return False
            
        print("✓ Table 'predictions' exists with columns:")
        expected_columns = {
            'id', 'group_id', 'domain', 'prediction_probability', 
            'prediction_confidence', 'model_version', 'features',
            'predicted_at', 'created_at'
        }
        found_columns = set()
        
        for col in predictions_schema:
            col_name = col['column_name']
            found_columns.add(col_name)
            print(f"  - {col_name:25s} {col['data_type']:20s} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")
            
        missing = expected_columns - found_columns
        if missing:
            print(f"⚠ Missing expected columns: {missing}")
        else:
            print("✓ All expected columns present")
            
        # Check semantic_groups table
        print("\n2. Checking 'semantic_groups' table...")
        semantic_groups_schema = await self.conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'semantic_groups'
            ORDER BY ordinal_position
        """)
        
        if semantic_groups_schema:
            print("✓ Table 'semantic_groups' exists with columns:")
            for col in semantic_groups_schema:
                print(f"  - {col['column_name']:25s} {col['data_type']:20s} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")
        else:
            print("⚠ Table 'semantic_groups' does not exist (optional)")
            
        # Check indexes
        print("\n3. Checking indexes...")
        indexes = await self.conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename IN ('predictions', 'semantic_groups')
            ORDER BY tablename, indexname
        """)
        
        if indexes:
            print("✓ Found indexes:")
            for idx in indexes:
                print(f"  - {idx['indexname']}")
        else:
            print("⚠ No indexes found")

        return True

    async def test_data_extraction(self):
        """Test all data extraction queries used by the system."""
        print("\n" + "="*80)
        print("DATA EXTRACTION TESTS")
        print("="*80)

        # Test 1: Get latest predictions
        print("\n1. Testing get_latest_predictions query...")
        try:
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
            rows = await self.conn.fetch(query, 0.0, 24, 10)
            print(f"✓ Query executed successfully, returned {len(rows)} rows")

            if rows:
                print(f"  Sample prediction:")
                row = rows[0]
                # Parse features if it's a string (JSONB column)
                features = row['features']
                if isinstance(features, str):
                    try:
                        features = json.loads(features)
                    except (json.JSONDecodeError, TypeError):
                        features = {}
                elif features is None:
                    features = {}

                print(f"    ID: {row['id']}")
                print(f"    Domain: {row['domain']}")
                print(f"    Probability: {row['prediction_probability']:.4f}")
                print(f"    Confidence: {row['prediction_confidence']:.4f}")
                print(f"    Features keys: {list(features.keys()) if features else 'None'}")
                print(f"    Predicted at: {row['predicted_at']}")

                # Extract countries
                countries = []
                if 'country1' in features:
                    countries.append(features['country1'])
                if 'country2' in features:
                    countries.append(features['country2'])
                if not countries and 'countries' in features:
                    countries = features['countries']
                print(f"    Extracted countries: {countries}")
            else:
                print("  ⚠ No conflict/geopolitical predictions found in last 24 hours")

        except Exception as e:
            print(f"✗ Query failed: {e}")

        # Test 2: Get BTC predictions
        print("\n2. Testing get_btc_predictions query...")
        try:
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
            rows = await self.conn.fetch(query, 0.0, 24, 10)
            print(f"✓ Query executed successfully, returned {len(rows)} rows")

            if rows:
                print(f"  Sample BTC prediction:")
                row = rows[0]
                # Parse features if it's a string (JSONB column)
                features = row['features']
                if isinstance(features, str):
                    try:
                        features = json.loads(features)
                    except (json.JSONDecodeError, TypeError):
                        features = {}
                elif features is None:
                    features = {}

                print(f"    ID: {row['id']}")
                print(f"    Probability: {row['prediction_probability']:.4f}")
                print(f"    Confidence: {row['prediction_confidence']:.4f}")

                # Extract BTC-specific fields
                prediction_magnitude = features.get('prediction_magnitude', 0.0)
                prediction_direction = features.get('prediction_direction', 'neutral')
                prediction_strength = features.get('prediction_strength', 'unknown')
                prediction_description = features.get('prediction_description', '')

                print(f"    Direction: {prediction_direction}")
                print(f"    Magnitude: {prediction_magnitude}")
                print(f"    Strength: {prediction_strength}")
                desc_display = f"{prediction_description[:50]}..." if len(prediction_description) > 50 else prediction_description
                print(f"    Description: {desc_display}")
            else:
                print("  ⚠ No BTC predictions found in last 24 hours")

        except Exception as e:
            print(f"✗ Query failed: {e}")

        # Test 3: Get country risk scores
        print("\n3. Testing get_country_risk_scores query...")
        try:
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
                LIMIT 5
            """
            rows = await self.conn.fetch(query)
            print(f"✓ Query executed successfully, returned {len(rows)} countries")

            if rows:
                print(f"  Top 5 countries by risk score:")
                for i, row in enumerate(rows[:5], 1):
                    country = row['country'].strip('"')
                    print(f"    {i}. {country:20s} Risk: {row['risk_score']:.4f} Count: {row['prediction_count']}")
            else:
                print("  ⚠ No country risk data found")

        except Exception as e:
            print(f"✗ Query failed: {e}")

        # Test 4: Get trend data
        print("\n4. Testing get_trend_data query...")
        try:
            query = """
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
            rows = await self.conn.fetch(query, 'day', 7)
            print(f"✓ Query executed successfully, returned {len(rows)} data points")

            if rows:
                print(f"  Trend data (last 7 days):")
                for row in rows[:5]:
                    print(f"    {row['timestamp'].date()}: {row['prediction_count']} predictions, avg prob: {row['avg_probability']:.4f}")
            else:
                print("  ⚠ No trend data found")

        except Exception as e:
            print(f"✗ Query failed: {e}")

        # Test 5: Get top country pairs
        print("\n5. Testing get_top_country_pairs query...")
        try:
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
                LIMIT 5
            """
            rows = await self.conn.fetch(query)
            print(f"✓ Query executed successfully, returned {len(rows)} country pairs")

            if rows:
                print(f"  Top 5 country pairs:")
                for i, row in enumerate(rows[:5], 1):
                    if row['country1'] and row['country2']:
                        print(f"    {i}. {row['country1']} - {row['country2']}: prob={row['avg_probability']:.4f}, count={row['prediction_count']}")
            else:
                print("  ⚠ No country pairs found")

        except Exception as e:
            print(f"✗ Query failed: {e}")

        # Test 6: Get dashboard stats
        print("\n6. Testing get_dashboard_stats query...")
        try:
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
            row = await self.conn.fetchrow(query)
            print(f"✓ Query executed successfully")

            if row:
                print(f"  Dashboard statistics:")
                print(f"    Total predictions: {row['total_predictions']}")
                print(f"    Total countries: {row['total_countries']}")
                avg_prob = row['avg_probability'] if row['avg_probability'] else 0.0
                avg_conf = row['avg_confidence'] if row['avg_confidence'] else 0.0
                print(f"    Avg probability: {avg_prob:.4f}")
                print(f"    Avg confidence: {avg_conf:.4f}")
                print(f"    High risk count (>0.7): {row['high_risk_count']}")
                print(f"    Last updated: {row['last_updated']}")
            else:
                print("  ⚠ No stats data found")

        except Exception as e:
            print(f"✗ Query failed: {e}")

        # Test 7: Get network graph data
        print("\n7. Testing get_network_graph_data query...")
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=168)
            query = """
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
                LIMIT 100
            """
            rows = await self.conn.fetch(query, 0.5, cutoff_time)
            print(f"✓ Query executed successfully, returned {len(rows)} rows")

            # Process network graph data
            nodes_dict = {}
            links = []

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

                country1 = features.get('country1')
                country2 = features.get('country2')

                # Fallback to semantic_groups.countries
                if not country1 or not country2:
                    sg_countries = row.get('countries', [])
                    if sg_countries and len(sg_countries) >= 2:
                        country1 = sg_countries[0]
                        country2 = sg_countries[1]

                if country1 and country2:
                    for country in [country1, country2]:
                        if country not in nodes_dict:
                            nodes_dict[country] = {'count': 0, 'total_conf': 0.0}
                        nodes_dict[country]['count'] += 1
                        nodes_dict[country]['total_conf'] += float(row['prediction_confidence'])
                    links.append((country1, country2))

            print(f"  Network graph extracted:")
            print(f"    Nodes (countries): {len(nodes_dict)}")
            print(f"    Links (predictions): {len(links)}")

            if nodes_dict:
                print(f"  Top 5 countries by prediction count:")
                sorted_countries = sorted(nodes_dict.items(), key=lambda x: x[1]['count'], reverse=True)
                for i, (country, data) in enumerate(sorted_countries[:5], 1):
                    avg_conf = data['total_conf'] / data['count']
                    print(f"    {i}. {country:20s} Count: {data['count']}, Avg Conf: {avg_conf:.4f}")

        except Exception as e:
            print(f"✗ Query failed: {e}")

    async def check_data_statistics(self):
        """Check overall data statistics in the database."""
        print("\n" + "="*80)
        print("DATA STATISTICS")
        print("="*80)

        # Total predictions by domain
        print("\n1. Predictions by domain:")
        try:
            query = """
                SELECT domain, COUNT(*) as count
                FROM predictions
                GROUP BY domain
                ORDER BY count DESC
            """
            rows = await self.conn.fetch(query)
            for row in rows:
                print(f"  {row['domain']:20s}: {row['count']:,} predictions")
        except Exception as e:
            print(f"✗ Query failed: {e}")

        # Recent predictions (last 7 days)
        print("\n2. Recent predictions (last 7 days):")
        try:
            query = """
                SELECT
                    domain,
                    COUNT(*) as count,
                    AVG(prediction_probability) as avg_prob,
                    AVG(prediction_confidence) as avg_conf
                FROM predictions
                WHERE predicted_at >= NOW() - INTERVAL '7 days'
                GROUP BY domain
                ORDER BY count DESC
            """
            rows = await self.conn.fetch(query)
            for row in rows:
                print(f"  {row['domain']:20s}: {row['count']:,} predictions, avg prob: {row['avg_prob']:.4f}, avg conf: {row['avg_conf']:.4f}")
        except Exception as e:
            print(f"✗ Query failed: {e}")

        # Check semantic_groups data
        print("\n3. Semantic groups statistics:")
        try:
            query = """
                SELECT COUNT(*) as total_groups
                FROM semantic_groups
            """
            row = await self.conn.fetchrow(query)
            if row:
                print(f"  Total semantic groups: {row['total_groups']:,}")

                # Check groups with countries
                query2 = """
                    SELECT COUNT(*) as groups_with_countries
                    FROM semantic_groups
                    WHERE countries IS NOT NULL AND array_length(countries, 1) > 0
                """
                row2 = await self.conn.fetchrow(query2)
                if row2:
                    print(f"  Groups with countries: {row2['groups_with_countries']:,}")
        except Exception as e:
            print(f"  ⚠ Semantic groups table not accessible: {e}")

        # Check features data quality
        print("\n4. Features data quality:")
        try:
            query = """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE features IS NOT NULL) as has_features,
                    COUNT(*) FILTER (WHERE features ? 'country1') as has_country1,
                    COUNT(*) FILTER (WHERE features ? 'country2') as has_country2,
                    COUNT(*) FILTER (WHERE features ? 'countries') as has_countries_array
                FROM predictions
                WHERE domain IN ('conflict', 'geopolitical')
                    AND predicted_at >= NOW() - INTERVAL '7 days'
            """
            row = await self.conn.fetchrow(query)
            if row:
                total = row['total']
                print(f"  Total conflict/geopolitical predictions (7 days): {total:,}")
                print(f"  Has features: {row['has_features']:,} ({row['has_features']/total*100:.1f}%)")
                print(f"  Has country1: {row['has_country1']:,} ({row['has_country1']/total*100:.1f}%)")
                print(f"  Has country2: {row['has_country2']:,} ({row['has_country2']/total*100:.1f}%)")
                print(f"  Has countries array: {row['has_countries_array']:,} ({row['has_countries_array']/total*100:.1f}%)")
        except Exception as e:
            print(f"✗ Query failed: {e}")


async def main():
    """Main verification routine."""
    print("="*80)
    print("CONFLICT DASHBOARD SERVICE - SYSTEM VERIFICATION")
    print("="*80)
    print("\nThis script mimics how the system reads, fetches, and extracts data.")
    print("It will verify the database schema and test all data extraction queries.\n")

    verifier = SystemVerifier()

    # Connect to database
    if not await verifier.connect():
        print("\n✗ Cannot proceed without database connection")
        return 1

    try:
        # Run verification steps
        await verifier.verify_schema()
        await verifier.test_data_extraction()
        await verifier.check_data_statistics()

        print("\n" + "="*80)
        print("VERIFICATION COMPLETE")
        print("="*80)
        print("\n✓ All tests completed. Review the output above for any warnings or errors.")

    except Exception as e:
        print(f"\n✗ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await verifier.disconnect()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

