"""
Analyze Neo4j schema to understand Prediction node structure.

This script:
1. Connects to Neo4j
2. Analyzes Prediction node schema
3. Shows sample Prediction nodes
4. Identifies what needs to be updated
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


async def analyze_neo4j_schema():
    """Analyze Neo4j schema for Prediction nodes."""
    
    logger.info("=" * 80)
    logger.info("Analyzing Neo4j Schema - Prediction Nodes")
    logger.info("=" * 80)
    
    # Neo4j connection
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    neo4j_database = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    logger.info(f"\n📡 Connecting to Neo4j: {neo4j_uri}")
    logger.info(f"   Database: {neo4j_database}")
    
    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session(database=neo4j_database) as session:
            
            # Query 1: Get all node labels
            logger.info("\n" + "=" * 80)
            logger.info("QUERY 1: All Node Labels in Database")
            logger.info("=" * 80)
            
            result = await session.run("CALL db.labels()")
            labels = [record["label"] async for record in result]
            
            logger.info(f"\n📊 Found {len(labels)} node labels:")
            for label in labels:
                logger.info(f"   - {label}")
            
            # Query 2: Count Prediction nodes
            logger.info("\n" + "=" * 80)
            logger.info("QUERY 2: Count Prediction Nodes")
            logger.info("=" * 80)
            
            result = await session.run("MATCH (p:Prediction) RETURN count(p) as count")
            record = await result.single()
            prediction_count = record["count"] if record else 0
            
            logger.info(f"\n📊 Total Prediction nodes: {prediction_count}")
            
            if prediction_count == 0:
                logger.warning("\n⚠️  No Prediction nodes found in Neo4j!")
                return
            
            # Query 3: Get Prediction node properties
            logger.info("\n" + "=" * 80)
            logger.info("QUERY 3: Prediction Node Properties")
            logger.info("=" * 80)
            
            result = await session.run("""
                MATCH (p:Prediction)
                WITH p LIMIT 1
                RETURN keys(p) as properties
            """)
            record = await result.single()
            properties = record["properties"] if record else []
            
            logger.info(f"\n📊 Prediction node has {len(properties)} properties:")
            for prop in sorted(properties):
                logger.info(f"   - {prop}")
            
            # Query 4: Sample Prediction nodes
            logger.info("\n" + "=" * 80)
            logger.info("QUERY 4: Sample Prediction Nodes (first 5)")
            logger.info("=" * 80)
            
            result = await session.run("""
                MATCH (p:Prediction)
                RETURN p
                ORDER BY p.created_at DESC
                LIMIT 5
            """)
            
            sample_predictions = [record["p"] async for record in result]
            
            logger.info(f"\n📊 Sample Prediction nodes:")
            for i, pred in enumerate(sample_predictions, 1):
                logger.info(f"\n  {i}. Prediction Node:")
                for key in sorted(pred.keys()):
                    value = pred[key]
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    logger.info(f"     {key}: {value}")
            
            # Query 5: Check for BTC domain predictions
            logger.info("\n" + "=" * 80)
            logger.info("QUERY 5: BTC Domain Predictions")
            logger.info("=" * 80)
            
            result = await session.run("""
                MATCH (p:Prediction)
                WHERE p.domain = 'btc'
                RETURN count(p) as count
            """)
            record = await result.single()
            btc_count = record["count"] if record else 0
            
            logger.info(f"\n📊 BTC Prediction nodes: {btc_count}")
            
            # Query 6: Sample BTC predictions with feature analysis
            logger.info("\n" + "=" * 80)
            logger.info("QUERY 6: Sample BTC Predictions - Feature Analysis")
            logger.info("=" * 80)
            
            result = await session.run("""
                MATCH (p:Prediction)
                WHERE p.domain = 'btc'
                RETURN p
                ORDER BY p.created_at DESC
                LIMIT 5
            """)
            
            btc_predictions = [record["p"] async for record in result]
            
            logger.info(f"\n📊 Analyzing {len(btc_predictions)} BTC predictions:")
            for i, pred in enumerate(btc_predictions, 1):
                logger.info(f"\n  {i}. BTC Prediction:")
                logger.info(f"     ID: {pred.get('id', 'N/A')}")
                logger.info(f"     Group ID: {pred.get('group_id', 'N/A')}")
                logger.info(f"     Domain: {pred.get('domain', 'N/A')}")
                logger.info(f"     Probability: {pred.get('prediction_probability', 'N/A')}")
                logger.info(f"     Confidence: {pred.get('prediction_confidence', 'N/A')}")
                
                # Check if features exist
                if 'features' in pred:
                    logger.info(f"     ✅ Has 'features' property")
                else:
                    logger.info(f"     ❌ Missing 'features' property")
                
                # Check for individual BTC feature properties
                btc_close = pred.get('btc_close', None)
                btc_volume = pred.get('btc_volume', None)
                btc_volatility = pred.get('btc_volatility_score', None)
                
                if btc_close is not None:
                    logger.info(f"     btc_close: {btc_close}")
                else:
                    logger.info(f"     ❌ Missing 'btc_close' property")
                
                if btc_volume is not None:
                    logger.info(f"     btc_volume: {btc_volume}")
                else:
                    logger.info(f"     ❌ Missing 'btc_volume' property")
                
                if btc_volatility is not None:
                    logger.info(f"     btc_volatility_score: {btc_volatility}")
                else:
                    logger.info(f"     ❌ Missing 'btc_volatility_score' property")
            
            # Query 7: Check relationships
            logger.info("\n" + "=" * 80)
            logger.info("QUERY 7: Prediction Node Relationships")
            logger.info("=" * 80)
            
            result = await session.run("""
                MATCH (p:Prediction)-[r]->(n)
                RETURN type(r) as rel_type, labels(n) as target_labels, count(*) as count
                ORDER BY count DESC
                LIMIT 10
            """)
            
            relationships = [record async for record in result]
            
            if relationships:
                logger.info(f"\n📊 Prediction node relationships:")
                for rel in relationships:
                    logger.info(f"   - {rel['rel_type']} -> {rel['target_labels']}: {rel['count']} relationships")
            else:
                logger.info("\n⚠️  No relationships found for Prediction nodes")
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("SUMMARY - What Needs to be Updated")
            logger.info("=" * 80)
            
            logger.info(f"\n📊 Current State:")
            logger.info(f"   - Total Prediction nodes: {prediction_count}")
            logger.info(f"   - BTC Prediction nodes: {btc_count}")
            logger.info(f"   - Properties per node: {len(properties)}")
            
            logger.info(f"\n🔧 Update Strategy:")
            logger.info(f"   1. Update 'features' property with correct BTC features (JSON string)")
            logger.info(f"   2. Add/Update individual BTC feature properties:")
            logger.info(f"      - btc_close")
            logger.info(f"      - btc_volume")
            logger.info(f"      - btc_volatility_score")
            logger.info(f"      - btc_change_pct_10h_backward")
            logger.info(f"      - (and other 13 BTC features)")
            logger.info(f"   3. Set 'updated_at' timestamp")
            
    finally:
        await driver.close()
        logger.info("\n✅ Disconnected from Neo4j")


if __name__ == "__main__":
    asyncio.run(analyze_neo4j_schema())

