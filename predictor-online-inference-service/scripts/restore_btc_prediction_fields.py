"""
Restore BTC prediction fields from export file.

This script:
1. Reads the export file to get original BTC prediction data
2. Extracts prediction_value, prediction_direction, prediction_magnitude, prediction_strength, prediction_description
3. Merges these fields with the current BTC features in PostgreSQL
4. Updates Neo4j nodes with these fields as well
"""

import asyncio
import logging
import os
import json
import re
from pathlib import Path
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


def parse_export_file(export_path: Path) -> dict:
    """Parse export file to extract BTC prediction data."""

    logger.info(f"Parsing export file: {export_path}")

    with open(export_path, 'r') as f:
        lines = f.readlines()

    predictions = {}
    current_id = None
    current_domain = None

    for i, line in enumerate(lines):
        # Check for ID
        if line.startswith('ID:'):
            current_id = int(line.split(':')[1].strip())

        # Check for Domain
        elif line.startswith('Domain:'):
            current_domain = line.split(':')[1].strip()

        # Check for Features line (BTC predictions only)
        elif line.startswith('Features (Full Metadata):') and current_domain == 'btc':
            # Next line contains the JSON
            if i + 2 < len(lines):
                features_line = lines[i + 2].strip()
                # Remove quotes at start and end
                if features_line.startswith('"') and features_line.endswith('"'):
                    features_line = features_line[1:-1]

                # Unescape the JSON
                features_line = features_line.replace('\\"', '"')

                try:
                    features = json.loads(features_line)

                    # Extract BTC-specific fields
                    btc_data = {
                        'id': current_id,
                        'group_id': features.get('group_id'),
                        'prediction_value': features.get('prediction_value'),
                        'prediction_direction': features.get('prediction_direction'),
                        'prediction_magnitude': features.get('prediction_magnitude'),
                        'prediction_strength': features.get('prediction_strength'),
                        'prediction_description': features.get('prediction_description'),
                    }

                    predictions[current_id] = btc_data
                    logger.info(f"Parsed BTC prediction ID {current_id}: {btc_data['prediction_description']}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse features for ID {current_id}: {e}")
                    logger.error(f"Features line: {features_line[:200]}")

    logger.info(f"Parsed {len(predictions)} BTC predictions from export file")
    return predictions


async def restore_btc_fields():
    """Restore BTC prediction fields."""
    
    logger.info("=" * 80)
    logger.info("Restoring BTC Prediction Fields")
    logger.info("=" * 80)
    
    # Parse export file
    export_path = Path(__file__).parent.parent / "predictions_export_20251115_140854.txt"
    btc_predictions = parse_export_file(export_path)
    
    if not btc_predictions:
        logger.error("No BTC predictions found in export file!")
        return
    
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
        # Step 1: Update PostgreSQL
        logger.info("\n" + "=" * 80)
        logger.info("Step 1: Update PostgreSQL with BTC prediction fields")
        logger.info("=" * 80)
        
        updated_count = 0
        
        for pred_id, btc_data in btc_predictions.items():
            # Get current features
            row = await pg_conn.fetchrow(
                "SELECT features FROM predictions WHERE id = $1",
                pred_id
            )
            
            if not row:
                logger.warning(f"Prediction ID {pred_id} not found in database")
                continue
            
            current_features = row['features']
            if isinstance(current_features, str):
                current_features = json.loads(current_features)
            
            # Add BTC prediction fields to features
            current_features['prediction_value'] = btc_data['prediction_value']
            current_features['prediction_direction'] = btc_data['prediction_direction']
            current_features['prediction_magnitude'] = btc_data['prediction_magnitude']
            current_features['prediction_strength'] = btc_data['prediction_strength']
            current_features['prediction_description'] = btc_data['prediction_description']
            
            # Update PostgreSQL
            await pg_conn.execute(
                "UPDATE predictions SET features = $1::jsonb WHERE id = $2",
                json.dumps(current_features),
                pred_id
            )
            
            updated_count += 1
            logger.info(f"✅ Updated PostgreSQL ID {pred_id}: {btc_data['prediction_description']}")
        
        logger.info(f"\n✅ Updated {updated_count}/{len(btc_predictions)} PostgreSQL predictions")

        # Step 2: Update Neo4j
        logger.info("\n" + "=" * 80)
        logger.info("Step 2: Update Neo4j with BTC prediction fields")
        logger.info("=" * 80)

        async with neo4j_driver.session(database=neo4j_database) as session:
            neo4j_updated_count = 0

            for pred_id, btc_data in btc_predictions.items():
                group_id = btc_data['group_id']

                # Find Neo4j node by group_id
                find_query = """
                    MATCH (p:Prediction {group_id: $group_id, domain: 'btc'})
                    RETURN p.id as id, p.features as features
                """

                result = await session.run(find_query, group_id=group_id)
                record = await result.single()

                if not record:
                    logger.warning(f"Neo4j node not found for group_id: {group_id}")
                    continue

                neo4j_id = record['id']
                current_features_str = record['features']

                # Parse current features
                if current_features_str:
                    try:
                        current_features = json.loads(current_features_str)
                    except:
                        current_features = {}
                else:
                    current_features = {}

                # Add BTC prediction fields with semantic_group_features: prefix for consistency
                current_features['prediction_value'] = btc_data['prediction_value']
                current_features['prediction_direction'] = btc_data['prediction_direction']
                current_features['prediction_magnitude'] = btc_data['prediction_magnitude']
                current_features['prediction_strength'] = btc_data['prediction_strength']
                current_features['prediction_description'] = btc_data['prediction_description']

                # Update Neo4j node
                update_query = """
                    MATCH (p:Prediction {id: $neo4j_id})
                    SET p.features = $features
                    RETURN p
                """

                result = await session.run(
                    update_query,
                    neo4j_id=neo4j_id,
                    features=json.dumps(current_features)
                )

                record = await result.single()
                if record:
                    neo4j_updated_count += 1
                    logger.info(f"✅ Updated Neo4j node {neo4j_id}: {btc_data['prediction_description']}")
                else:
                    logger.warning(f"Failed to update Neo4j node {neo4j_id}")

            logger.info(f"\n✅ Updated {neo4j_updated_count}/{len(btc_predictions)} Neo4j nodes")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"\n✅ Successfully restored BTC prediction fields:")
        logger.info(f"   - PostgreSQL: {updated_count}/{len(btc_predictions)} predictions")
        logger.info(f"   - Neo4j: {neo4j_updated_count}/{len(btc_predictions)} nodes")
        logger.info(f"\n📋 Restored fields:")
        logger.info(f"   - prediction_value")
        logger.info(f"   - prediction_direction")
        logger.info(f"   - prediction_magnitude")
        logger.info(f"   - prediction_strength")
        logger.info(f"   - prediction_description")

    finally:
        await pg_conn.close()
        await neo4j_driver.close()
        logger.info("\n✅ Disconnected from databases")


if __name__ == "__main__":
    asyncio.run(restore_btc_fields())

