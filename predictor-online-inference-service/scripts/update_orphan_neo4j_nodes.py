"""
Update orphan Neo4j conflict nodes (nodes without PostgreSQL records) with BTC features.
"""

import asyncio
import logging
import os
import json
import math
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
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
        """Get BTC features for a given timestamp with semantic_group_features: prefix."""
        if self.btc_df is None:
            self.load_parquet()

        # Convert timestamp to pandas Timestamp and remove timezone for comparison
        pd_timestamp = pd.Timestamp(timestamp)
        if pd_timestamp.tz is not None:
            pd_timestamp = pd_timestamp.tz_localize(None)

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
        
        # Build 17-feature vector with semantic_group_features: prefix
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


async def update_orphan_nodes():
    """Update orphan Neo4j nodes with BTC features."""
    
    logger.info("=" * 80)
    logger.info("Updating Orphan Neo4j Conflict Nodes with BTC Features")
    logger.info("=" * 80)
    
    # Initialize BTC feature calculator
    btc_parquet_path = Path(__file__).parent.parent.parent / "feast" / "offline_store" / "btc_features.parquet"
    calculator = BtcFeatureCalculator(btc_parquet_path)
    calculator.load_parquet()
    
    # Neo4j connection
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    neo4j_database = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    logger.info(f"\n📡 Connecting to Neo4j: {neo4j_uri}")
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    # Orphan node IDs (nodes without PostgreSQL records)
    orphan_node_ids = [
        '01KA2TBD8JAB2XKBNVY6HM65JG',  # Group: 583a804e-88bd-05b2-436c-00cc4be24974
        '01KA2SVDFMDV2BMQY4WZK3D3CG',  # Group: d8b78350-d4a5-0d8f-c7d0-c80de03e525f
        '01KA2SSRQP8BK3301TKVFH975F',  # Group: e26e1df8-70e5-19ce-0a17-ea9db8537715
    ]
    
    try:
        async with driver.session(database=neo4j_database) as session:
            updated_count = 0
            
            for i, node_id in enumerate(orphan_node_ids, 1):
                logger.info(f"\n[{i}/{len(orphan_node_ids)}] Processing orphan node: {node_id}")
                
                # Get node details
                find_query = """
                    MATCH (p:Prediction {id: $node_id})
                    RETURN p.id as id, p.group_id as group_id, p.created_at as created_at, p.features as features
                """
                
                result = await session.run(find_query, node_id=node_id)
                record = await result.single()
                
                if not record:
                    logger.warning(f"   ⚠️  Node not found: {node_id}")
                    continue
                
                group_id = record['group_id']
                created_at_str = record['created_at']
                current_features_str = record['features']
                
                # Parse created_at - handle Neo4j DateTime type
                if isinstance(created_at_str, str):
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                elif hasattr(created_at_str, 'to_native'):
                    # Neo4j DateTime object
                    created_at = created_at_str.to_native()
                else:
                    created_at = created_at_str
                
                logger.info(f"   Group ID: {group_id}")
                logger.info(f"   Created at: {created_at}")
                
                # Parse current features
                if current_features_str:
                    try:
                        current_features = json.loads(current_features_str)
                    except:
                        current_features = {}
                else:
                    current_features = {}
                
                # Calculate BTC features
                btc_features = calculator.get_btc_features(created_at)
                
                # Merge BTC features into current features
                merged_features = {**current_features, **btc_features}
                
                # Update Neo4j node
                update_query = """
                    MATCH (p:Prediction {id: $node_id})
                    SET p.features = $features
                    RETURN p
                """
                
                result = await session.run(
                    update_query,
                    node_id=node_id,
                    features=json.dumps(merged_features)
                )
                
                record = await result.single()
                if record:
                    updated_count += 1
                    logger.info(f"   ✅ Updated with {len(btc_features)} BTC features")
                else:
                    logger.warning(f"   ⚠️  Failed to update node")
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("SUMMARY")
            logger.info("=" * 80)
            logger.info(f"\n✅ Successfully updated {updated_count}/{len(orphan_node_ids)} orphan Neo4j nodes")
        
    finally:
        await driver.close()
        logger.info("\n✅ Disconnected from Neo4j")


if __name__ == "__main__":
    asyncio.run(update_orphan_nodes())

