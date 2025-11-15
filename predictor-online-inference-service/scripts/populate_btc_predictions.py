"""
Populate prediction table and Neo4j with correct BTC features.

This script:
1. Reads BTC predictions from the database that have zero features
2. Calculates correct BTC features from btc_features.parquet
3. Updates the predictions table with correct features
4. Updates Neo4j prediction nodes with correct features
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
        Get BTC features for a given timestamp.
        
        Args:
            timestamp: Timestamp to find nearest BTC data for
            
        Returns:
            Dictionary with 17 BTC features
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
        
        # Build 17-feature vector
        return {
            'btc_close': close_price,
            'btc_high': high_price,
            'btc_low': low_price,
            'btc_open': open_price,
            'btc_price_range_pct': price_range_pct,
            'btc_body_size_pct': body_size_pct,
            'btc_close_position_in_range': close_position_in_range,
            'btc_is_bullish': is_bullish,
            'btc_change_pct_10h_backward': change_pct_10h,
            'btc_momentum_strength': momentum_strength,
            'btc_volume': volume_normalized,
            'btc_volatility_score': volatility_score,
            'btc_label_spike': label_spike,
            'btc_hour_sin': hour_sin,
            'btc_hour_cos': hour_cos,
            'btc_day_sin': day_sin,
            'btc_day_cos': day_cos,
        }


async def populate_btc_predictions():
    """Populate prediction table and Neo4j with correct BTC features."""
    
    logger.info("=" * 80)
    logger.info("Populating BTC Predictions with Correct Features")
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
    
    logger.info(f"\n📡 Connecting to PostgreSQL: {db_config['host']}:{db_config['port']}")
    logger.info(f"📡 Connecting to Neo4j: {neo4j_uri}")
    
    # Connect to PostgreSQL
    pg_conn = await asyncpg.connect(**db_config)
    
    # Connect to Neo4j
    neo4j_driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        # Fetch all BTC predictions with zero features
        logger.info("\n" + "=" * 80)
        logger.info("Step 1: Fetch BTC predictions with zero features")
        logger.info("=" * 80)
        
        query = """
            SELECT id, group_id, domain, features, predicted_at, created_at
            FROM predictions
            WHERE domain = 'btc'
            ORDER BY created_at DESC
        """
        
        predictions = await pg_conn.fetch(query)
        logger.info(f"\n📊 Found {len(predictions)} BTC predictions")

        # Filter predictions with zero features
        zero_feature_predictions = []
        for pred in predictions:
            features = pred['features']
            if isinstance(features, str):
                features = json.loads(features)

            btc_close = features.get('btc_close', 0.0)
            btc_volume = features.get('btc_volume', 0.0)
            btc_volatility = features.get('btc_volatility_score', 0.0)

            if btc_close == 0.0 and btc_volume == 0.0 and btc_volatility == 0.0:
                zero_feature_predictions.append(pred)

        logger.info(f"📊 Found {len(zero_feature_predictions)} BTC predictions with ZERO features")

        if len(zero_feature_predictions) == 0:
            logger.info("\n✅ No BTC predictions need updating!")
            return

        # Step 2: Calculate correct features and update database
        logger.info("\n" + "=" * 80)
        logger.info("Step 2: Calculate correct BTC features and update database")
        logger.info("=" * 80)

        updated_count = 0
        for i, pred in enumerate(zero_feature_predictions, 1):
            pred_id = pred['id']
            group_id = pred['group_id']
            timestamp = pred['predicted_at'] or pred['created_at']

            logger.info(f"\n[{i}/{len(zero_feature_predictions)}] Processing prediction ID: {pred_id}")
            logger.info(f"   Group ID: {group_id}")
            logger.info(f"   Timestamp: {timestamp}")

            # Calculate correct BTC features
            try:
                btc_features = calculator.get_btc_features(timestamp)

                logger.info(f"   ✅ Calculated BTC features:")
                logger.info(f"      btc_close: {btc_features['btc_close']:.2f}")
                logger.info(f"      btc_volume: {btc_features['btc_volume']:.6f}")
                logger.info(f"      btc_volatility_score: {btc_features['btc_volatility_score']:.6f}")

                # Update PostgreSQL
                update_query = """
                    UPDATE predictions
                    SET features = $1
                    WHERE id = $2
                """

                await pg_conn.execute(update_query, json.dumps(btc_features), pred_id)
                logger.info(f"   ✅ Updated PostgreSQL prediction ID: {pred_id}")

                # Update Neo4j
                async with neo4j_driver.session() as session:
                    neo4j_query = """
                        MATCH (p:Prediction {id: $pred_id})
                        SET p.features = $features,
                            p.btc_close = $btc_close,
                            p.btc_volume = $btc_volume,
                            p.btc_volatility_score = $btc_volatility_score,
                            p.updated_at = datetime()
                        RETURN p
                    """

                    result = await session.run(
                        neo4j_query,
                        pred_id=str(pred_id),
                        features=json.dumps(btc_features),
                        btc_close=btc_features['btc_close'],
                        btc_volume=btc_features['btc_volume'],
                        btc_volatility_score=btc_features['btc_volatility_score']
                    )

                    record = await result.single()
                    if record:
                        logger.info(f"   ✅ Updated Neo4j prediction node ID: {pred_id}")
                    else:
                        logger.warning(f"   ⚠️  Neo4j prediction node not found for ID: {pred_id}")

                updated_count += 1

            except Exception as e:
                logger.error(f"   ❌ Failed to update prediction ID {pred_id}: {e}")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"\n✅ Successfully updated {updated_count}/{len(zero_feature_predictions)} BTC predictions")
        logger.info(f"   - PostgreSQL: Updated features column")
        logger.info(f"   - Neo4j: Updated Prediction nodes")

    finally:
        await pg_conn.close()
        await neo4j_driver.close()
        logger.info("\n✅ Disconnected from databases")


if __name__ == "__main__":
    asyncio.run(populate_btc_predictions())

