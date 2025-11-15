"""
Test script to verify BTC feature fallback logic.

This script tests that the BtcFeatureBuilder correctly falls back to
btc_features.parquet when semantic_groups.parquet has zero BTC features.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.clients.postgres_client import PostgresClient
from src.features.btc_feature_builder import BtcFeatureBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_btc_fallback():
    """Test BTC feature fallback logic."""

    logger.info("=" * 80)
    logger.info("Testing BTC Feature Fallback Logic")
    logger.info("=" * 80)

    # Initialize PostgreSQL client from environment variables
    postgres_client = PostgresClient(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', '5432')),
        database=os.getenv('POSTGRES_DATABASE', 'sentiment'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', ''),
    )
    
    try:
        # Connect to database
        await postgres_client.connect()
        logger.info("✅ Connected to PostgreSQL")
        
        # Initialize BTC feature builder
        btc_builder = BtcFeatureBuilder(postgres_client)
        logger.info("✅ Initialized BTC feature builder")
        
        # Test Case 1: All features are zero (should trigger fallback)
        logger.info("\n" + "=" * 80)
        logger.info("TEST CASE 1: Zero BTC features (should trigger parquet fallback)")
        logger.info("=" * 80)
        
        zero_features = {
            'btc_volume': 0.0,
            'btc_volatility_score': 0.0,
            'btc_change_pct_10h': 0.0,
            'btc_label_spike': 0,
        }
        
        timestamp = datetime(2024, 11, 1, 12, 0, 0)  # Use a timestamp within parquet range
        
        result = await btc_builder.build_btc_features(zero_features, timestamp)
        
        logger.info(f"\n📊 Result Features:")
        logger.info(f"  btc_close: {result['btc_close']}")
        logger.info(f"  btc_high: {result['btc_high']}")
        logger.info(f"  btc_low: {result['btc_low']}")
        logger.info(f"  btc_open: {result['btc_open']}")
        logger.info(f"  btc_volume: {result['btc_volume']}")
        logger.info(f"  btc_volatility_score: {result['btc_volatility_score']}")
        logger.info(f"  btc_change_pct_10h_backward: {result['btc_change_pct_10h_backward']}")
        logger.info(f"  btc_label_spike: {result['btc_label_spike']}")
        
        # Check if fallback worked (features should be non-zero)
        if result['btc_close'] > 0 and result['btc_volume'] > 0:
            logger.info("\n✅ TEST PASSED: Fallback to parquet worked! Features are non-zero.")
        else:
            logger.warning("\n⚠️  TEST FAILED: Features are still zero after fallback.")
        
        # Test Case 2: Non-zero features (should NOT trigger fallback)
        logger.info("\n" + "=" * 80)
        logger.info("TEST CASE 2: Non-zero BTC features (should NOT trigger fallback)")
        logger.info("=" * 80)
        
        nonzero_features = {
            'btc_volume': 1000000000.0,
            'btc_volatility_score': 0.5,
            'btc_change_pct_10h': 2.5,
            'btc_label_spike': 0,
        }
        
        result2 = await btc_builder.build_btc_features(nonzero_features, timestamp)
        
        logger.info(f"\n📊 Result Features:")
        logger.info(f"  btc_volume: {result2['btc_volume']}")
        logger.info(f"  btc_volatility_score: {result2['btc_volatility_score']}")
        logger.info(f"  btc_change_pct_10h_backward: {result2['btc_change_pct_10h_backward']}")
        
        # Check that original values were preserved
        if result2['btc_volatility_score'] == 0.5 and result2['btc_change_pct_10h_backward'] == 2.5:
            logger.info("\n✅ TEST PASSED: Original features preserved (no fallback triggered).")
        else:
            logger.warning("\n⚠️  TEST FAILED: Original features were modified.")
        
        # Test Case 3: Partial zero features (volume=0, volatility>0)
        logger.info("\n" + "=" * 80)
        logger.info("TEST CASE 3: Partial zero features (should NOT trigger fallback)")
        logger.info("=" * 80)
        
        partial_features = {
            'btc_volume': 0.0,
            'btc_volatility_score': 0.8,
            'btc_change_pct_10h': 0.0,
            'btc_label_spike': 0,
        }
        
        result3 = await btc_builder.build_btc_features(partial_features, timestamp)
        
        logger.info(f"\n📊 Result Features:")
        logger.info(f"  btc_volume: {result3['btc_volume']}")
        logger.info(f"  btc_volatility_score: {result3['btc_volatility_score']}")
        logger.info(f"  btc_change_pct_10h_backward: {result3['btc_change_pct_10h_backward']}")
        
        if result3['btc_volatility_score'] == 0.8:
            logger.info("\n✅ TEST PASSED: Partial features handled correctly.")
        else:
            logger.warning("\n⚠️  TEST FAILED: Partial features were modified.")
        
        logger.info("\n" + "=" * 80)
        logger.info("All tests completed!")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)
    
    finally:
        # Disconnect
        await postgres_client.disconnect()
        logger.info("✅ Disconnected from PostgreSQL")


if __name__ == "__main__":
    asyncio.run(test_btc_fallback())

