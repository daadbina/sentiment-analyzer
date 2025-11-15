"""
Populate conflict predictions with correct BTC features from parquet file.

This script:
1. Fetches all conflict predictions from PostgreSQL
2. Calculates correct BTC features from btc_features.parquet based on timestamp
3. Updates PostgreSQL predictions table with BTC features in correct format
4. Updates Neo4j prediction nodes with BTC features in correct format
"""

import asyncio
import logging
import os
import json
import math
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import asyncpg
import pandas as pd
from neo4j import AsyncGraphDatabase

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BtcFeatureCalculator:
    """Calculate BTC features from parquet file."""
    
    def __init__(self, parquet_path: Path):
        """Initialize with parquet file path."""
        self.parquet_path = parquet_path
        self.btc_df = None
        
    def load_parquet(self):
        """Load BTC features from parquet file."""
        logger.info(f"Loading BTC features from: {self.parquet_path}")
        self.btc_df = pd.read_parquet(self.parquet_path)
        logger.info(f"Loaded {len(self.btc_df)} BTC records")
        
    def get_btc_features(self, timestamp: datetime) -> dict:
        """
        Get BTC features for a given timestamp with semantic_group_features: prefix.
        
        Args:
            timestamp: Timestamp to find nearest BTC data for
            
        Returns:
            Dictionary with 17 BTC features with semantic_group_features: prefix
        """
        if self.btc_df is None:
            self.load_parquet()
        
        # Convert timestamp to pandas Timestamp
        pd_timestamp = pd.Timestamp(timestamp)
        
        # Find closest timestamp
        self.btc_df['time_diff'] = abs(self.btc_df['timestamp'] - pd_timestamp)
        closest_idx = self.btc_df['time_diff'].idxmin()
        row = self.btc_df.loc[closest_idx]
        
        # Extract OHLC and other features
        open_price = float(row['open'])
        high_price = float(row['high'])
        low_price = float(row['low'])
        close_price = float(row['close'])
        volume = float(row['volume'])
        change_pct_10h = float(row['change_pct_10h'])
        volatility_score = float(row['volatility_score'])
        label_spike = int(row['label_spike'])
        parquet_timestamp = row['timestamp']
        
        # Calculate derived features
        price_range_pct = ((high_price - low_price) / close_price * 100.0) if close_price > 0 and high_price > low_price else 0.0
        body_size_pct = (abs(close_price - open_price) / close_price * 100.0) if close_price > 0 else 0.0
        is_bullish = 1 if close_price > open_price else 0
        
        price_range = high_price - low_price if high_price > low_price else 0.0
        close_position_in_range = ((close_price - low_price) / price_range) if price_range > 0 else 0.5
        
        momentum_strength = abs(change_pct_10h)
        volume_normalized = volume / 1000000.0 if volume > 0 else 0.0
        
        # Cyclical time encoding
        if isinstance(parquet_timestamp, pd.Timestamp):
            parquet_timestamp = parquet_timestamp.to_pydatetime()
        
        hour_sin = math.sin(2 * math.pi * parquet_timestamp.hour / 24)
        hour_cos = math.cos(2 * math.pi * parquet_timestamp.hour / 24)
        day_sin = math.sin(2 * math.pi * parquet_timestamp.weekday() / 7)
        day_cos = math.cos(2 * math.pi * parquet_timestamp.weekday() / 7)
        
        # Build 17-feature vector with semantic_group_features: prefix for Neo4j compatibility
        return {
            'semantic_group_features:btc_close': close_price,
            'semantic_group_features:btc_high': high_price,
            'semantic_group_features:btc_low': low_price,
            'semantic_group_features:btc_open': open_price,
            'semantic_group_features:btc_price_range_pct': price_range_pct,
            'semantic_group_features:btc_body_size_pct': body_size_pct,
            'semantic_group_features:btc_close_position_in_range': close_position_in_range,
            'semantic_group_features:btc_is_bullish': is_bullish,
            'semantic_group_features:btc_change_pct_10h_backward': change_pct_10h,
            'semantic_group_features:btc_momentum_strength': momentum_strength,
            'semantic_group_features:btc_volume': volume_normalized,
            'semantic_group_features:btc_volatility_score': volatility_score,
            'semantic_group_features:btc_label_spike': label_spike,
            'semantic_group_features:btc_hour_sin': hour_sin,
            'semantic_group_features:btc_hour_cos': hour_cos,
            'semantic_group_features:btc_day_sin': day_sin,
            'semantic_group_features:btc_day_cos': day_cos,
        }


async def populate_conflict_btc_features():
    """Populate conflict predictions with correct BTC features."""
    
    logger.info("=" * 80)
    logger.info("Populating Conflict Predictions with BTC Features")
    logger.info("=" * 80)
    
    # Initialize BTC feature calculator
    btc_parquet_path = Path(__file__).parent.parent.parent / "feast" / "offline_store" / "btc_features.parquet"
    calculator = BtcFeatureCalculator(btc_parquet_path)
    calculator.load_parquet()
    
    # Database connection
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DATABASE', 'sentiment'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
    }
    
    # Neo4j connection
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    neo4j_database = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    logger.info(f"\n📡 Connecting to PostgreSQL: {db_config['host']}:{db_config['port']}")
    logger.info(f"📡 Connecting to Neo4j: {neo4j_uri}")
    
    # Connect to PostgreSQL
    pg_conn = await asyncpg.connect(**db_config)
    
    # Connect to Neo4j
    neo4j_driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        # Fetch all conflict predictions
        logger.info("\n" + "=" * 80)
        logger.info("Step 1: Fetch conflict predictions from PostgreSQL")
        logger.info("=" * 80)

        query = """
            SELECT id, group_id, features, predicted_at
            FROM predictions
            WHERE domain = 'conflict'
            ORDER BY created_at DESC
        """

        predictions = await pg_conn.fetch(query)
        logger.info(f"\n📊 Found {len(predictions)} conflict predictions")

        # Step 2: Update PostgreSQL with BTC features
        logger.info("\n" + "=" * 80)
        logger.info("Step 2: Update PostgreSQL with BTC features")
        logger.info("=" * 80)

        updated_count = 0

        for i, pred in enumerate(predictions, 1):
            pred_id = pred['id']
            group_id = pred['group_id']
            predicted_at = pred['predicted_at']
            current_features = pred['features']

            # Parse current features
            if isinstance(current_features, str):
                current_features = json.loads(current_features)

            logger.info(f"\n[{i}/{len(predictions)}] Processing prediction ID: {pred_id}")
            logger.info(f"   Group ID: {group_id}")
            logger.info(f"   Predicted at: {predicted_at}")

            # Calculate BTC features
            btc_features = calculator.get_btc_features(predicted_at)

            # Remove semantic_group_features: prefix for PostgreSQL storage
            btc_features_no_prefix = {}
            for key, value in btc_features.items():
                # Remove the prefix for PostgreSQL
                clean_key = key.replace('semantic_group_features:', '')
                btc_features_no_prefix[clean_key] = value

            # Get the nested features dict
            nested_features = current_features.get('features', {})
            if isinstance(nested_features, str):
                nested_features = json.loads(nested_features)

            # Merge BTC features into nested features
            merged_nested_features = {**nested_features, **btc_features_no_prefix}

            # Update the features dict
            updated_features = {**current_features, 'features': merged_nested_features}

            # Update PostgreSQL
            update_query = """
                UPDATE predictions
                SET features = $1::jsonb
                WHERE id = $2
            """

            await pg_conn.execute(update_query, json.dumps(updated_features), pred_id)
            updated_count += 1

            logger.info(f"   ✅ Updated PostgreSQL with {len(btc_features_no_prefix)} BTC features")

        logger.info(f"\n✅ Updated {updated_count}/{len(predictions)} PostgreSQL predictions")

        # Step 3: Update Neo4j with BTC features
        logger.info("\n" + "=" * 80)
        logger.info("Step 3: Update Neo4j with BTC features")
        logger.info("=" * 80)

        async with neo4j_driver.session(database=neo4j_database) as session:
            neo4j_updated_count = 0

            for i, pred in enumerate(predictions, 1):
                group_id = pred['group_id']
                predicted_at = pred['predicted_at']

                logger.info(f"\n[{i}/{len(predictions)}] Processing group_id: {group_id}")

                # Find Neo4j node by group_id
                find_query = """
                    MATCH (p:Prediction {group_id: $group_id, domain: 'conflict'})
                    RETURN p.id as id, p.features as features
                """

                result = await session.run(find_query, group_id=group_id)
                record = await result.single()

                if not record:
                    logger.warning(f"   ⚠️  Neo4j node not found for group_id: {group_id}")
                    continue

                neo4j_id = record['id']
                current_features_str = record['features']

                logger.info(f"   Found Neo4j node: {neo4j_id}")

                # Parse current features
                if current_features_str:
                    try:
                        current_features = json.loads(current_features_str)
                    except:
                        current_features = {}
                else:
                    current_features = {}

                # Calculate BTC features (with semantic_group_features: prefix)
                btc_features = calculator.get_btc_features(predicted_at)

                # Merge BTC features into current features
                merged_features = {**current_features, **btc_features}

                # Update Neo4j node
                update_query = """
                    MATCH (p:Prediction {id: $neo4j_id})
                    SET p.features = $features
                    RETURN p
                """

                result = await session.run(
                    update_query,
                    neo4j_id=neo4j_id,
                    features=json.dumps(merged_features)
                )

                record = await result.single()
                if record:
                    neo4j_updated_count += 1
                    logger.info(f"   ✅ Updated Neo4j node with {len(btc_features)} BTC features")
                else:
                    logger.warning(f"   ⚠️  Failed to update Neo4j node")

            logger.info(f"\n✅ Updated {neo4j_updated_count}/{len(predictions)} Neo4j nodes")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"\n✅ Successfully populated conflict predictions with BTC features:")
        logger.info(f"   - PostgreSQL: {updated_count}/{len(predictions)} predictions")
        logger.info(f"   - Neo4j: {neo4j_updated_count}/{len(predictions)} nodes")

    finally:
        await pg_conn.close()
        await neo4j_driver.close()
        logger.info("\n✅ Disconnected from databases")


if __name__ == "__main__":
    asyncio.run(populate_conflict_btc_features())

