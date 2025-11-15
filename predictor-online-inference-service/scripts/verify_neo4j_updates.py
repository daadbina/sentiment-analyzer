"""
Verify Neo4j BTC prediction nodes have been updated with correct features.
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


async def verify_neo4j_updates():
    """Verify Neo4j BTC prediction nodes have correct features."""
    
    logger.info("=" * 80)
    logger.info("Verifying Neo4j BTC Prediction Updates")
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
            
            # Query: Get all BTC predictions with feature analysis
            logger.info("\n" + "=" * 80)
            logger.info("BTC Prediction Nodes - Feature Verification")
            logger.info("=" * 80)
            
            result = await session.run("""
                MATCH (p:Prediction)
                WHERE p.domain = 'btc'
                RETURN p
                ORDER BY p.created_at DESC
            """)
            
            btc_predictions = [record["p"] async for record in result]
            
            logger.info(f"\n📊 Found {len(btc_predictions)} BTC prediction nodes")
            
            zero_count = 0
            non_zero_count = 0
            
            for i, pred in enumerate(btc_predictions, 1):
                logger.info(f"\n{i}. BTC Prediction Node:")
                logger.info(f"   ID: {pred.get('id', 'N/A')}")
                logger.info(f"   Group ID: {pred.get('group_id', 'N/A')}")
                logger.info(f"   Model Version: {pred.get('model_version', 'N/A')}")
                
                # Check BTC features
                btc_close = pred.get('btc_close', None)
                btc_volume = pred.get('btc_volume', None)
                btc_volatility = pred.get('btc_volatility_score', None)
                btc_change = pred.get('btc_change_pct_10h_backward', None)
                btc_high = pred.get('btc_high', None)
                btc_low = pred.get('btc_low', None)
                
                if btc_close is not None and btc_close != 0:
                    logger.info(f"   ✅ Status: NON-ZERO features")
                    logger.info(f"   btc_close: {btc_close:.2f}")
                    if btc_high is not None:
                        logger.info(f"   btc_high: {btc_high:.2f}")
                    else:
                        logger.info(f"   btc_high: N/A")
                    if btc_low is not None:
                        logger.info(f"   btc_low: {btc_low:.2f}")
                    else:
                        logger.info(f"   btc_low: N/A")
                    if btc_volume is not None:
                        logger.info(f"   btc_volume: {btc_volume:.6f}")
                    else:
                        logger.info(f"   btc_volume: N/A")
                    if btc_volatility is not None:
                        logger.info(f"   btc_volatility_score: {btc_volatility:.6f}")
                    else:
                        logger.info(f"   btc_volatility_score: N/A")
                    if btc_change is not None:
                        logger.info(f"   btc_change_pct_10h_backward: {btc_change:.6f}")
                    else:
                        logger.info(f"   btc_change_pct_10h_backward: N/A")
                    non_zero_count += 1
                else:
                    logger.info(f"   ❌ Status: ZERO or MISSING features")
                    logger.info(f"   btc_close: {btc_close}")
                    logger.info(f"   btc_volume: {btc_volume}")
                    logger.info(f"   btc_volatility_score: {btc_volatility}")
                    zero_count += 1
                
                # Check if updated_at exists
                updated_at = pred.get('updated_at', None)
                if updated_at:
                    logger.info(f"   Updated at: {updated_at}")
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("SUMMARY")
            logger.info("=" * 80)
            logger.info(f"\n📊 BTC Prediction Nodes:")
            logger.info(f"   Total: {len(btc_predictions)}")
            logger.info(f"   ✅ With NON-ZERO features: {non_zero_count} ({non_zero_count/len(btc_predictions)*100:.1f}%)")
            logger.info(f"   ❌ With ZERO/MISSING features: {zero_count} ({zero_count/len(btc_predictions)*100:.1f}%)")
            
            if non_zero_count == len(btc_predictions):
                logger.info(f"\n🎉 SUCCESS! All BTC prediction nodes have been updated with correct features!")
            else:
                logger.warning(f"\n⚠️  WARNING: {zero_count} BTC prediction nodes still have zero/missing features")
            
    finally:
        await driver.close()
        logger.info("\n✅ Disconnected from Neo4j")


if __name__ == "__main__":
    asyncio.run(verify_neo4j_updates())

