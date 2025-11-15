"""
Verify Neo4j Prediction nodes have correct features format.
"""

import asyncio
import logging
import os
import json
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


async def verify_neo4j_features():
    """Verify Neo4j BTC prediction nodes have correct features."""
    
    logger.info("=" * 80)
    logger.info("Verifying Neo4j BTC Prediction Features")
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
            
            # Query: Get all BTC predictions
            logger.info("\n" + "=" * 80)
            logger.info("BTC Prediction Nodes - Features Verification")
            logger.info("=" * 80)
            
            result = await session.run("""
                MATCH (p:Prediction)
                WHERE p.domain = 'btc'
                RETURN p
                ORDER BY p.created_at DESC
            """)
            
            btc_predictions = [record["p"] async for record in result]
            
            logger.info(f"\n📊 Found {len(btc_predictions)} BTC prediction nodes")
            
            empty_features_count = 0
            correct_features_count = 0
            
            for i, pred in enumerate(btc_predictions, 1):
                logger.info(f"\n{i}. BTC Prediction Node:")
                logger.info(f"   ID: {pred.get('id', 'N/A')}")
                logger.info(f"   Group ID: {pred.get('group_id', 'N/A')}")
                
                features_str = pred.get('features', None)
                
                if not features_str or features_str == '{}':
                    logger.info(f"   ❌ Status: EMPTY features")
                    empty_features_count += 1
                else:
                    try:
                        features = json.loads(features_str)
                        
                        # Check for BTC features with semantic_group_features: prefix
                        btc_close = features.get('semantic_group_features:btc_close', None)
                        btc_volume = features.get('semantic_group_features:btc_volume', None)
                        btc_volatility = features.get('semantic_group_features:btc_volatility_score', None)
                        
                        if btc_close is not None and btc_close != 0:
                            logger.info(f"   ✅ Status: CORRECT features format")
                            logger.info(f"   Features count: {len(features)}")
                            logger.info(f"   semantic_group_features:btc_close: {btc_close:.2f}")
                            logger.info(f"   semantic_group_features:btc_volume: {btc_volume:.6f if btc_volume else 'N/A'}")
                            logger.info(f"   semantic_group_features:btc_volatility_score: {btc_volatility:.6f if btc_volatility else 'N/A'}")
                            
                            # Show first 200 chars of features
                            logger.info(f"   Features preview: {features_str[:200]}...")
                            correct_features_count += 1
                        else:
                            logger.info(f"   ⚠️  Status: Features exist but BTC values are zero")
                            logger.info(f"   Features count: {len(features)}")
                            logger.info(f"   Features preview: {features_str[:200]}...")
                            empty_features_count += 1
                    except Exception as e:
                        logger.error(f"   ❌ Error parsing features: {e}")
                        logger.info(f"   Features string: {features_str[:200]}...")
                        empty_features_count += 1
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("SUMMARY")
            logger.info("=" * 80)
            logger.info(f"\n📊 BTC Prediction Nodes:")
            logger.info(f"   Total: {len(btc_predictions)}")
            logger.info(f"   ✅ With CORRECT features: {correct_features_count} ({correct_features_count/len(btc_predictions)*100:.1f}%)")
            logger.info(f"   ❌ With EMPTY/ZERO features: {empty_features_count} ({empty_features_count/len(btc_predictions)*100:.1f}%)")
            
            if correct_features_count == len(btc_predictions):
                logger.info(f"\n🎉 SUCCESS! All BTC prediction nodes have correct features format!")
            else:
                logger.warning(f"\n⚠️  WARNING: {empty_features_count} BTC prediction nodes still have empty/zero features")
            
    finally:
        await driver.close()
        logger.info("\n✅ Disconnected from Neo4j")


if __name__ == "__main__":
    asyncio.run(verify_neo4j_features())

