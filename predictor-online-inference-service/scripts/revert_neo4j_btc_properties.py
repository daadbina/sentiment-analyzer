"""
Revert incorrect BTC property additions to Neo4j Prediction nodes.

This script removes the individual BTC properties that were incorrectly added
as separate properties instead of being part of the features JSON string.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def revert_neo4j_properties():
    """Revert incorrect BTC properties from Neo4j Prediction nodes."""
    
    logger.info("=" * 80)
    logger.info("Reverting Incorrect BTC Properties from Neo4j")
    logger.info("=" * 80)
    
    # Neo4j connection
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    neo4j_database = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    logger.info(f"\n📡 Connecting to Neo4j: {neo4j_uri}")
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session(database=neo4j_database) as session:
            
            # Remove individual BTC properties from all Prediction nodes
            logger.info("\n" + "=" * 80)
            logger.info("Removing Individual BTC Properties")
            logger.info("=" * 80)
            
            revert_query = """
                MATCH (p:Prediction)
                WHERE p.domain = 'btc'
                REMOVE p.btc_close,
                       p.btc_high,
                       p.btc_low,
                       p.btc_open,
                       p.btc_volume,
                       p.btc_volatility_score,
                       p.btc_change_pct_10h_backward,
                       p.btc_price_range_pct,
                       p.btc_body_size_pct,
                       p.btc_close_position_in_range,
                       p.btc_is_bullish,
                       p.btc_momentum_strength,
                       p.btc_label_spike,
                       p.btc_hour_sin,
                       p.btc_hour_cos,
                       p.btc_day_sin,
                       p.btc_day_cos,
                       p.updated_at
                RETURN count(p) as count
            """
            
            result = await session.run(revert_query)
            record = await result.single()
            count = record['count'] if record else 0
            
            logger.info(f"\n✅ Removed individual BTC properties from {count} Prediction nodes")
            
            # Verify the revert
            logger.info("\n" + "=" * 80)
            logger.info("Verifying Revert")
            logger.info("=" * 80)
            
            verify_query = """
                MATCH (p:Prediction)
                WHERE p.domain = 'btc'
                RETURN p.id as id, 
                       p.btc_close as btc_close,
                       p.features as features
                LIMIT 3
            """
            
            result = await session.run(verify_query)
            records = [record async for record in result]
            
            logger.info(f"\n📊 Sample BTC predictions after revert:")
            for i, record in enumerate(records, 1):
                logger.info(f"\n  {i}. ID: {record['id']}")
                logger.info(f"     btc_close property: {record['btc_close']}")
                logger.info(f"     features: {record['features'][:100] if record['features'] else 'empty'}...")
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ Revert Complete")
            logger.info("=" * 80)
            
    finally:
        await driver.close()
        logger.info("\n✅ Disconnected from Neo4j")


if __name__ == "__main__":
    asyncio.run(revert_neo4j_properties())

