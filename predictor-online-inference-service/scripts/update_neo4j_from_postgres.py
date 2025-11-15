"""
Update Neo4j Prediction nodes with correct features from PostgreSQL.

This script:
1. Fetches all BTC predictions from PostgreSQL with their features
2. Updates corresponding Neo4j Prediction nodes with the same features
3. Ensures features are stored as JSON string with semantic_group_features: prefix
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


async def update_neo4j_from_postgres():
    """Update Neo4j with features from PostgreSQL."""
    
    logger.info("=" * 80)
    logger.info("Updating Neo4j Prediction Nodes from PostgreSQL")
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
        # Fetch all BTC predictions from PostgreSQL
        logger.info("\n" + "=" * 80)
        logger.info("Step 1: Fetch BTC predictions from PostgreSQL")
        logger.info("=" * 80)
        
        query = """
            SELECT id, group_id, domain, features, predicted_at, created_at
            FROM predictions
            WHERE domain = 'btc'
            ORDER BY created_at DESC
        """
        
        predictions = await pg_conn.fetch(query)
        logger.info(f"\n📊 Found {len(predictions)} BTC predictions in PostgreSQL")
        
        # Update Neo4j nodes
        logger.info("\n" + "=" * 80)
        logger.info("Step 2: Update Neo4j Prediction nodes")
        logger.info("=" * 80)
        
        updated_count = 0
        not_found_count = 0
        
        for i, pred in enumerate(predictions, 1):
            group_id = pred['group_id']
            features = pred['features']
            
            if isinstance(features, str):
                features = json.loads(features)
            
            logger.info(f"\n[{i}/{len(predictions)}] Processing group_id: {group_id}")
            
            # Update Neo4j
            async with neo4j_driver.session(database=neo4j_database) as session:
                # Find the Neo4j node by group_id and domain
                find_query = """
                    MATCH (p:Prediction)
                    WHERE p.group_id = $group_id AND p.domain = 'btc'
                    RETURN p.id as neo4j_id, p.features as current_features
                    LIMIT 1
                """
                
                find_result = await session.run(find_query, group_id=group_id)
                find_record = await find_result.single()
                
                if find_record:
                    neo4j_id = find_record['neo4j_id']
                    current_features_str = find_record['current_features']
                    
                    logger.info(f"   Found Neo4j node: {neo4j_id}")
                    
                    # Parse current features
                    if current_features_str:
                        try:
                            current_features = json.loads(current_features_str)
                        except:
                            current_features = {}
                    else:
                        current_features = {}

                    # Convert PostgreSQL features to Neo4j format with semantic_group_features: prefix
                    neo4j_features = {}
                    for key, value in features.items():
                        # Add semantic_group_features: prefix to BTC features
                        if key.startswith('btc_'):
                            neo4j_features[f'semantic_group_features:{key}'] = value
                        elif not key.startswith('semantic_group_features:'):
                            # Add prefix to any other features that don't have it
                            neo4j_features[f'semantic_group_features:{key}'] = value
                        else:
                            # Already has prefix
                            neo4j_features[key] = value

                    # Merge Neo4j-formatted features into current features
                    # This preserves existing semantic_group_features and adds BTC features
                    merged_features = {**current_features, **neo4j_features}
                    
                    # Update the node
                    update_query = """
                        MATCH (p:Prediction {id: $neo4j_id})
                        SET p.features = $features
                        RETURN p
                    """
                    
                    result = await session.run(
                        update_query,
                        neo4j_id=neo4j_id,
                        features=json.dumps(merged_features)
                    )
                    
                    record = await result.single()
                    if record:
                        logger.info(f"   ✅ Updated Neo4j node with {len(merged_features)} features")
                        updated_count += 1
                    else:
                        logger.warning(f"   ⚠️  Failed to update Neo4j node")
                else:
                    logger.warning(f"   ⚠️  Neo4j node not found for group_id: {group_id}")
                    not_found_count += 1
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"\n✅ Successfully updated {updated_count}/{len(predictions)} Neo4j Prediction nodes")
        if not_found_count > 0:
            logger.info(f"⚠️  {not_found_count} nodes not found in Neo4j")
        
    finally:
        await pg_conn.close()
        await neo4j_driver.close()
        logger.info("\n✅ Disconnected from databases")


if __name__ == "__main__":
    asyncio.run(update_neo4j_from_postgres())

