"""
Check conflict predictions in PostgreSQL and Neo4j.
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


async def check_conflict_predictions():
    """Check conflict predictions."""
    
    logger.info("=" * 80)
    logger.info("Checking Conflict Predictions")
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
        # Check PostgreSQL
        logger.info("\n" + "=" * 80)
        logger.info("PostgreSQL Conflict Predictions")
        logger.info("=" * 80)
        
        query = """
            SELECT id, group_id, domain, features, predicted_at
            FROM predictions
            WHERE domain = 'conflict'
            ORDER BY created_at DESC
            LIMIT 3
        """
        
        predictions = await pg_conn.fetch(query)
        logger.info(f"\n📊 Sample conflict predictions from PostgreSQL:")
        
        for i, pred in enumerate(predictions, 1):
            features = pred['features']
            if isinstance(features, str):
                features = json.loads(features)
            
            logger.info(f"\n{i}. ID: {pred['id']}, Group: {pred['group_id']}")
            logger.info(f"   Features count: {len(features)}")
            logger.info(f"   Feature keys (first 10):")
            for key in list(features.keys())[:10]:
                logger.info(f"     - {key}: {features[key]}")
        
        # Check Neo4j
        logger.info("\n" + "=" * 80)
        logger.info("Neo4j Conflict Predictions")
        logger.info("=" * 80)
        
        async with neo4j_driver.session(database=neo4j_database) as session:
            result = await session.run("""
                MATCH (p:Prediction)
                WHERE p.domain = 'conflict'
                RETURN p
                ORDER BY p.created_at DESC
                LIMIT 3
            """)
            
            nodes = [record["p"] async for record in result]
            
            logger.info(f"\n📊 Sample conflict predictions from Neo4j:")
            
            for i, node in enumerate(nodes, 1):
                features_str = node.get('features', '')
                if features_str:
                    try:
                        features = json.loads(features_str)
                    except:
                        features = {}
                else:
                    features = {}
                
                logger.info(f"\n{i}. ID: {node.get('id')}, Group: {node.get('group_id')}")
                logger.info(f"   Features count: {len(features)}")
                logger.info(f"   Feature keys (first 10):")
                for key in list(features.keys())[:10]:
                    logger.info(f"     - {key}: {features[key]}")
                
                # Check for BTC features
                btc_keys = [k for k in features.keys() if 'btc' in k.lower()]
                if btc_keys:
                    logger.info(f"   BTC-related features found: {len(btc_keys)}")
                    for key in btc_keys[:5]:
                        logger.info(f"     - {key}: {features[key]}")
                else:
                    logger.info(f"   ❌ No BTC features found")
        
    finally:
        await pg_conn.close()
        await neo4j_driver.close()
        logger.info("\n✅ Disconnected from databases")


if __name__ == "__main__":
    asyncio.run(check_conflict_predictions())

