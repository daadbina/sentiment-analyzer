"""
Check what fields are currently in BTC predictions.
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


async def check_btc_fields():
    """Check BTC prediction fields."""
    
    logger.info("=" * 80)
    logger.info("Checking BTC Prediction Fields")
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
        logger.info("PostgreSQL BTC Predictions - Sample Record")
        logger.info("=" * 80)
        
        # Get all columns
        query = """
            SELECT *
            FROM predictions
            WHERE domain = 'btc'
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        pred = await pg_conn.fetchrow(query)
        
        if pred:
            logger.info(f"\n📊 PostgreSQL columns and values:")
            for key in pred.keys():
                value = pred[key]
                if key == 'features':
                    if isinstance(value, str):
                        value = json.loads(value)
                    logger.info(f"\n   {key}:")
                    if isinstance(value, dict):
                        for fkey, fval in value.items():
                            logger.info(f"      - {fkey}: {fval}")
                else:
                    logger.info(f"   {key}: {value}")
        
        # Check Neo4j
        logger.info("\n" + "=" * 80)
        logger.info("Neo4j BTC Predictions - Sample Node")
        logger.info("=" * 80)
        
        async with neo4j_driver.session(database=neo4j_database) as session:
            result = await session.run("""
                MATCH (p:Prediction)
                WHERE p.domain = 'btc'
                RETURN p
                ORDER BY p.created_at DESC
                LIMIT 1
            """)
            
            record = await result.single()
            
            if record:
                node = record["p"]
                logger.info(f"\n📊 Neo4j node properties:")
                
                for key in sorted(node.keys()):
                    value = node[key]
                    if key == 'features':
                        try:
                            features = json.loads(value)
                            logger.info(f"\n   {key}:")
                            for fkey, fval in features.items():
                                logger.info(f"      - {fkey}: {fval}")
                        except:
                            logger.info(f"   {key}: {value}")
                    else:
                        logger.info(f"   {key}: {value}")
        
        # Check what BTC-specific fields should exist
        logger.info("\n" + "=" * 80)
        logger.info("Expected BTC Prediction Fields")
        logger.info("=" * 80)
        
        expected_fields = [
            'prediction_magnitude',
            'prediction_strength', 
            'prediction_direction',
            'prediction_description',
            'prediction_probability',
            'prediction_confidence'
        ]
        
        logger.info(f"\n📋 Expected BTC-specific fields:")
        for field in expected_fields:
            logger.info(f"   - {field}")
        
    finally:
        await pg_conn.close()
        await neo4j_driver.close()
        logger.info("\n✅ Disconnected from databases")


if __name__ == "__main__":
    asyncio.run(check_btc_fields())

