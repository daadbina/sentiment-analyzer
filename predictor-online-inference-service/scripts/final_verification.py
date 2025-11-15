"""
Final verification of BTC features in conflict predictions.
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


async def final_verification():
    """Final verification of BTC features."""
    
    logger.info("=" * 80)
    logger.info("Final Verification - BTC Features in Conflict Predictions")
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
    
    # Connect to PostgreSQL
    pg_conn = await asyncpg.connect(**db_config)
    
    # Connect to Neo4j
    neo4j_driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        # Check PostgreSQL
        logger.info("\n" + "=" * 80)
        logger.info("PostgreSQL Conflict Predictions")
        logger.info("=" * 80)
        
        query = """
            SELECT id, group_id, features
            FROM predictions
            WHERE domain = 'conflict'
        """
        
        predictions = await pg_conn.fetch(query)
        
        total = len(predictions)
        with_btc = 0
        without_btc = 0
        
        for pred in predictions:
            features = pred['features']
            if isinstance(features, str):
                features = json.loads(features)
            
            nested_features = features.get('features', {})
            if isinstance(nested_features, str):
                nested_features = json.loads(nested_features)
            
            # Check for BTC features
            has_btc = 'btc_close' in nested_features and nested_features['btc_close'] != 0
            
            if has_btc:
                with_btc += 1
            else:
                without_btc += 1
        
        logger.info(f"\n📊 PostgreSQL Summary:")
        logger.info(f"   Total conflict predictions: {total}")
        logger.info(f"   ✅ With BTC features: {with_btc} ({with_btc/total*100:.1f}%)")
        logger.info(f"   ❌ Without BTC features: {without_btc} ({without_btc/total*100:.1f}%)")
        
        # Check Neo4j
        logger.info("\n" + "=" * 80)
        logger.info("Neo4j Conflict Predictions")
        logger.info("=" * 80)
        
        async with neo4j_driver.session(database=neo4j_database) as session:
            result = await session.run("""
                MATCH (p:Prediction)
                WHERE p.domain = 'conflict'
                RETURN p
            """)
            
            nodes = [record["p"] async for record in result]
            
            total = len(nodes)
            with_btc = 0
            without_btc = 0
            
            for node in nodes:
                features_str = node.get('features', '')
                if features_str:
                    try:
                        features = json.loads(features_str)
                    except:
                        features = {}
                else:
                    features = {}
                
                # Check for BTC features with semantic_group_features: prefix
                has_btc = 'semantic_group_features:btc_close' in features and \
                          features['semantic_group_features:btc_close'] != 0
                
                if has_btc:
                    with_btc += 1
                else:
                    without_btc += 1
            
            logger.info(f"\n📊 Neo4j Summary:")
            logger.info(f"   Total conflict prediction nodes: {total}")
            logger.info(f"   ✅ With BTC features: {with_btc} ({with_btc/total*100:.1f}%)")
            logger.info(f"   ❌ Without BTC features: {without_btc} ({without_btc/total*100:.1f}%)")
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 80)
        
        if with_btc == total:
            logger.info("\n🎉 SUCCESS! All conflict predictions have correct BTC features!")
            logger.info("\n✅ PostgreSQL: Features stored in nested 'features' dict WITHOUT prefix")
            logger.info("✅ Neo4j: Features stored WITH 'semantic_group_features:' prefix")
        else:
            logger.warning(f"\n⚠️  WARNING: Some predictions still missing BTC features")
        
    finally:
        await pg_conn.close()
        await neo4j_driver.close()
        logger.info("\n✅ Disconnected from databases")


if __name__ == "__main__":
    asyncio.run(final_verification())

