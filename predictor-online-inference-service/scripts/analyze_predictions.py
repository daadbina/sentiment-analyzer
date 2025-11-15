"""
Analyze predictions from the database.

This script:
1. Fetches all predictions with model_version = 1
2. Identifies duplicate BTC predictions for the same group_id
3. Analyzes BTC feature quality (zero vs non-zero)
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
import asyncpg

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def analyze_predictions():
    """Analyze predictions from the database."""
    
    logger.info("=" * 80)
    logger.info("Analyzing Predictions from Database")
    logger.info("=" * 80)
    
    # Database connection parameters
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DATABASE', 'sentiment'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
    }
    
    logger.info(f"\n📡 Connecting to PostgreSQL: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    # Connect to database
    conn = await asyncpg.connect(**db_config)
    
    try:
        # Query 1: Get all predictions with model_version = 1
        logger.info("\n" + "=" * 80)
        logger.info("QUERY 1: Predictions with model_version = 1")
        logger.info("=" * 80)

        query_v1 = """
            SELECT
                id, group_id, domain, prediction_probability,
                prediction_confidence, model_version, features,
                predicted_at, created_at
            FROM predictions
            WHERE model_version = '1'
            ORDER BY created_at DESC
        """

        rows_v1 = await conn.fetch(query_v1)
        logger.info(f"\n📊 Found {len(rows_v1)} predictions with model_version = 1")

        if rows_v1:
            logger.info("\nAll predictions with model_version = 1:")
            for i, row in enumerate(rows_v1, 1):
                logger.info(f"\n  {i}. ID: {row['id']}")
                logger.info(f"     Group ID: {row['group_id']}")
                logger.info(f"     Domain: {row['domain']}")
                logger.info(f"     Probability: {row['prediction_probability']:.4f}")
                logger.info(f"     Confidence: {row['prediction_confidence']:.4f}")
                logger.info(f"     Predicted at: {row['predicted_at']}")

        # Query 1b: Get conflict domain predictions with model_version = 1
        logger.info("\n" + "=" * 80)
        logger.info("QUERY 1b: CONFLICT domain predictions with model_version = 1")
        logger.info("=" * 80)

        query_conflict_v1 = """
            SELECT
                id, group_id, domain, prediction_probability,
                prediction_confidence, model_version, features,
                predicted_at, created_at
            FROM predictions
            WHERE model_version = '1' AND domain = 'conflict'
            ORDER BY created_at DESC
        """

        conflict_v1 = await conn.fetch(query_conflict_v1)
        logger.info(f"\n📊 Found {len(conflict_v1)} CONFLICT predictions with model_version = 1")

        if conflict_v1:
            logger.info("\nAll CONFLICT predictions with model_version = 1:")
            for i, row in enumerate(conflict_v1, 1):
                logger.info(f"\n  {i}. ID: {row['id']}")
                logger.info(f"     Group ID: {row['group_id']}")
                logger.info(f"     Domain: {row['domain']}")
                logger.info(f"     Probability: {row['prediction_probability']:.4f}")
                logger.info(f"     Confidence: {row['prediction_confidence']:.4f}")
                logger.info(f"     Model Version: {row['model_version']}")
                logger.info(f"     Predicted at: {row['predicted_at']}")
        
        # Query 2: Find duplicate BTC predictions for same group_id
        logger.info("\n" + "=" * 80)
        logger.info("QUERY 2: Duplicate BTC predictions for same group_id")
        logger.info("=" * 80)
        
        query_duplicates = """
            SELECT 
                group_id,
                COUNT(*) as prediction_count,
                array_agg(id ORDER BY created_at) as prediction_ids,
                array_agg(prediction_probability ORDER BY created_at) as probabilities,
                array_agg(model_version ORDER BY created_at) as model_versions,
                array_agg(created_at ORDER BY created_at) as timestamps
            FROM predictions
            WHERE domain = 'btc'
            GROUP BY group_id
            HAVING COUNT(*) > 1
            ORDER BY prediction_count DESC
        """
        
        duplicates = await conn.fetch(query_duplicates)
        logger.info(f"\n📊 Found {len(duplicates)} group_ids with duplicate BTC predictions")
        
        if duplicates:
            logger.info("\nDuplicate BTC predictions:")
            for i, dup in enumerate(duplicates[:10], 1):
                logger.info(f"\n  {i}. Group ID: {dup['group_id']}")
                logger.info(f"     Prediction count: {dup['prediction_count']}")
                logger.info(f"     Prediction IDs: {dup['prediction_ids']}")
                logger.info(f"     Probabilities: {[f'{p:.4f}' for p in dup['probabilities']]}")
                logger.info(f"     Model versions: {dup['model_versions']}")
                logger.info(f"     Timestamps: {dup['timestamps']}")
        else:
            logger.info("\n✅ No duplicate BTC predictions found!")
        
        # Query 3: Analyze BTC feature quality
        logger.info("\n" + "=" * 80)
        logger.info("QUERY 3: Analyze BTC feature quality (zero vs non-zero)")
        logger.info("=" * 80)
        
        query_all = """
            SELECT 
                id, group_id, domain, features, model_version
            FROM predictions
            ORDER BY created_at DESC
        """
        
        all_rows = await conn.fetch(query_all)
        logger.info(f"\n📊 Analyzing {len(all_rows)} total predictions")
        
        # Analyze BTC features
        btc_predictions = [r for r in all_rows if r['domain'] == 'btc']
        conflict_predictions = [r for r in all_rows if r['domain'] == 'conflict']
        
        logger.info(f"\n   BTC predictions: {len(btc_predictions)}")
        logger.info(f"   Conflict predictions: {len(conflict_predictions)}")
        
        # Check for zero BTC features
        zero_btc_features = 0
        nonzero_btc_features = 0
        
        logger.info("\n📊 BTC Feature Analysis:")
        logger.info("\nSample BTC predictions with feature analysis:")
        
        for i, row in enumerate(btc_predictions[:10], 1):
            features = row['features']

            # Parse features if it's a JSON string
            if isinstance(features, str):
                features = json.loads(features)

            # Check key BTC features
            btc_close = features.get('btc_close', 0.0)
            btc_volume = features.get('btc_volume', 0.0)
            btc_volatility = features.get('btc_volatility_score', 0.0)
            btc_change = features.get('btc_change_pct_10h_backward', 0.0)
            
            is_zero = (btc_close == 0.0 and btc_volume == 0.0 and btc_volatility == 0.0)
            
            if is_zero:
                zero_btc_features += 1
                status = "❌ ZERO"
            else:
                nonzero_btc_features += 1
                status = "✅ NON-ZERO"
            
            logger.info(f"\n  {i}. ID: {row['id']} | Group: {row['group_id']} | Model: {row['model_version']}")
            logger.info(f"     Status: {status}")
            logger.info(f"     btc_close: {btc_close}")
            logger.info(f"     btc_volume: {btc_volume}")
            logger.info(f"     btc_volatility_score: {btc_volatility}")
            logger.info(f"     btc_change_pct_10h_backward: {btc_change}")
        
        # Summary statistics
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY STATISTICS")
        logger.info("=" * 80)
        
        total_btc = len(btc_predictions)
        if total_btc > 0:
            zero_pct = (zero_btc_features / total_btc) * 100
            nonzero_pct = (nonzero_btc_features / total_btc) * 100
            
            logger.info(f"\n📊 BTC Predictions Feature Quality:")
            logger.info(f"   Total BTC predictions: {total_btc}")
            logger.info(f"   ❌ With ZERO BTC features: {zero_btc_features} ({zero_pct:.1f}%)")
            logger.info(f"   ✅ With NON-ZERO BTC features: {nonzero_btc_features} ({nonzero_pct:.1f}%)")
        
        logger.info(f"\n📊 Model Version Distribution:")
        model_versions = defaultdict(int)
        for row in all_rows:
            model_versions[row['model_version']] += 1
        
        for version, count in sorted(model_versions.items()):
            logger.info(f"   Model v{version}: {count} predictions")
        
        logger.info(f"\n📊 Domain Distribution:")
        domains = defaultdict(int)
        for row in all_rows:
            domains[row['domain']] += 1
        
        for domain, count in sorted(domains.items()):
            logger.info(f"   {domain}: {count} predictions")
        
        logger.info("\n" + "=" * 80)
        logger.info("Analysis completed!")
        logger.info("=" * 80)
        
    finally:
        await conn.close()
        logger.info("\n✅ Disconnected from PostgreSQL")


if __name__ == "__main__":
    asyncio.run(analyze_predictions())

