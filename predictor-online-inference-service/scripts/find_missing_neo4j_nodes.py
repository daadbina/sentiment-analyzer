"""
Find Neo4j conflict nodes that are missing BTC features.
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


async def find_missing_nodes():
    """Find Neo4j nodes missing BTC features."""
    
    logger.info("=" * 80)
    logger.info("Finding Neo4j Conflict Nodes Missing BTC Features")
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
            result = await session.run("""
                MATCH (p:Prediction)
                WHERE p.domain = 'conflict'
                RETURN p
                ORDER BY p.created_at DESC
            """)
            
            nodes = [record["p"] async for record in result]
            
            logger.info(f"\n📊 Found {len(nodes)} conflict prediction nodes")
            
            missing_btc = []
            
            for i, node in enumerate(nodes, 1):
                node_id = node.get('id')
                group_id = node.get('group_id')
                created_at = node.get('created_at')
                features_str = node.get('features', '')
                
                if features_str:
                    try:
                        features = json.loads(features_str)
                    except:
                        features = {}
                else:
                    features = {}
                
                # Check for BTC features
                has_btc = 'semantic_group_features:btc_close' in features and \
                          features['semantic_group_features:btc_close'] != 0
                
                logger.info(f"\n{i}. Node ID: {node_id}")
                logger.info(f"   Group ID: {group_id}")
                logger.info(f"   Created: {created_at}")
                logger.info(f"   Features count: {len(features)}")
                
                if has_btc:
                    logger.info(f"   ✅ Has BTC features")
                else:
                    logger.info(f"   ❌ Missing BTC features")
                    missing_btc.append({
                        'id': node_id,
                        'group_id': group_id,
                        'created_at': created_at
                    })
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("SUMMARY")
            logger.info("=" * 80)
            logger.info(f"\n📊 Total nodes: {len(nodes)}")
            logger.info(f"✅ With BTC features: {len(nodes) - len(missing_btc)}")
            logger.info(f"❌ Missing BTC features: {len(missing_btc)}")
            
            if missing_btc:
                logger.info("\n❌ Nodes missing BTC features:")
                for node in missing_btc:
                    logger.info(f"   - ID: {node['id']}, Group: {node['group_id']}")
        
    finally:
        await driver.close()
        logger.info("\n✅ Disconnected from Neo4j")


if __name__ == "__main__":
    asyncio.run(find_missing_nodes())

