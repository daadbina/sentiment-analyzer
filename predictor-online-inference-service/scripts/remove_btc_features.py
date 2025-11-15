"""
Remove BTC features that were added to BTC predictions in PostgreSQL and Neo4j.

This script reverts the BTC feature additions to restore the original state.
"""

import asyncio
import logging
import os
import json
from dotenv import load_dotenv
import asyncpg
from neo4j import AsyncGraphDatabase

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def remove_btc_features():
    """Remove BTC features from BTC predictions in PostgreSQL and Neo4j."""
    
    logger.info("=" * 80)
    logger.info("Removing BTC Features from BTC Predictions")
    logger.info("=" * 80)
    
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
        # Step 1: Remove BTC features from PostgreSQL
        logger.info("\n" + "=" * 80)
        logger.info("Step 1: Remove BTC features from PostgreSQL")
        logger.info("=" * 80)
        
        # Set features to empty JSON for BTC predictions
        update_query = """
            UPDATE predictions
            SET features = '{}'::jsonb
            WHERE domain = 'btc'
            RETURNING id, group_id
        """
        
        updated_rows = await pg_conn.fetch(update_query)
        logger.info(f"\n✅ Removed BTC features from {len(updated_rows)} PostgreSQL predictions")
        
        for row in updated_rows:
            logger.info(f"   - ID: {row['id']}, Group: {row['group_id']}")
        
        # Step 2: Remove BTC features from Neo4j
        logger.info("\n" + "=" * 80)
        logger.info("Step 2: Remove BTC features from Neo4j")
        logger.info("=" * 80)
        
        async with neo4j_driver.session(database=neo4j_database) as session:
            # Get all BTC prediction nodes
            find_query = """
                MATCH (p:Prediction)
                WHERE p.domain = 'btc'
                RETURN p.id as id, p.group_id as group_id, p.features as features
            """
            
            result = await session.run(find_query)
            btc_nodes = [record async for record in result]
            
            logger.info(f"\n📊 Found {len(btc_nodes)} BTC prediction nodes in Neo4j")
            
            # Remove BTC features from each node
            for i, node in enumerate(btc_nodes, 1):
                neo4j_id = node['id']
                group_id = node['group_id']
                current_features_str = node['features']
                
                logger.info(f"\n[{i}/{len(btc_nodes)}] Processing Neo4j node: {neo4j_id}")
                
                # Parse current features
                if current_features_str:
                    try:
                        current_features = json.loads(current_features_str)
                    except:
                        current_features = {}
                else:
                    current_features = {}
                
                # Remove all BTC-related features (with and without prefix)
                cleaned_features = {}
                for key, value in current_features.items():
                    # Keep only non-BTC features
                    if not key.endswith('btc_close') and \
                       not key.endswith('btc_high') and \
                       not key.endswith('btc_low') and \
                       not key.endswith('btc_open') and \
                       not key.endswith('btc_volume') and \
                       not key.endswith('btc_volatility_score') and \
                       not key.endswith('btc_change_pct_10h_backward') and \
                       not key.endswith('btc_price_range_pct') and \
                       not key.endswith('btc_body_size_pct') and \
                       not key.endswith('btc_close_position_in_range') and \
                       not key.endswith('btc_is_bullish') and \
                       not key.endswith('btc_momentum_strength') and \
                       not key.endswith('btc_label_spike') and \
                       not key.endswith('btc_hour_sin') and \
                       not key.endswith('btc_hour_cos') and \
                       not key.endswith('btc_day_sin') and \
                       not key.endswith('btc_day_cos'):
                        cleaned_features[key] = value
                
                # Update the node with cleaned features
                update_query = """
                    MATCH (p:Prediction {id: $neo4j_id})
                    SET p.features = $features
                    RETURN p
                """
                
                result = await session.run(
                    update_query,
                    neo4j_id=neo4j_id,
                    features=json.dumps(cleaned_features)
                )
                
                record = await result.single()
                if record:
                    logger.info(f"   ✅ Cleaned features: {len(current_features)} -> {len(cleaned_features)}")
                else:
                    logger.warning(f"   ⚠️  Failed to update node")
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"\n✅ Successfully removed BTC features from:")
        logger.info(f"   - PostgreSQL: {len(updated_rows)} predictions")
        logger.info(f"   - Neo4j: {len(btc_nodes)} prediction nodes")
        
    finally:
        await pg_conn.close()
        await neo4j_driver.close()
        logger.info("\n✅ Disconnected from databases")


if __name__ == "__main__":
    asyncio.run(remove_btc_features())

