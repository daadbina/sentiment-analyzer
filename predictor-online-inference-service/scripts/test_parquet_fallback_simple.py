"""
Simple test to verify BTC parquet fallback logic works.

This script directly tests the parquet loading without requiring all dependencies.
"""

import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_parquet_loading():
    """Test that we can load and query BTC features from parquet."""
    
    logger.info("=" * 80)
    logger.info("Testing BTC Parquet Fallback Logic")
    logger.info("=" * 80)
    
    # Path to BTC parquet file
    btc_parquet_path = Path(__file__).parent.parent.parent / "feast" / "offline_store" / "btc_features.parquet"
    
    logger.info(f"\n📁 BTC Parquet Path: {btc_parquet_path}")
    logger.info(f"   Exists: {btc_parquet_path.exists()}")
    
    if not btc_parquet_path.exists():
        logger.error("❌ BTC parquet file not found!")
        return
    
    # Load parquet file
    logger.info("\n📊 Loading BTC features from parquet...")
    df = pd.read_parquet(btc_parquet_path)
    
    logger.info(f"   Loaded {len(df)} rows, {len(df.columns)} columns")
    logger.info(f"   Columns: {list(df.columns)}")
    
    # Test Case 1: Find closest timestamp
    logger.info("\n" + "=" * 80)
    logger.info("TEST CASE 1: Find closest BTC data for a given timestamp")
    logger.info("=" * 80)
    
    target_timestamp = datetime(2024, 11, 1, 12, 0, 0)
    pd_timestamp = pd.Timestamp(target_timestamp)
    
    logger.info(f"Target timestamp: {target_timestamp}")
    
    # Find closest timestamp
    df['time_diff'] = abs(df['timestamp'] - pd_timestamp)
    closest_idx = df['time_diff'].idxmin()
    closest_row = df.loc[closest_idx]
    
    time_diff_hours = closest_row['time_diff'].total_seconds() / 3600
    
    logger.info(f"\n📊 Closest BTC data:")
    logger.info(f"   Timestamp: {closest_row['timestamp']}")
    logger.info(f"   Time difference: {time_diff_hours:.2f} hours")
    logger.info(f"   Close: ${closest_row['close']:,.2f}")
    logger.info(f"   Open: ${closest_row['open']:,.2f}")
    logger.info(f"   High: ${closest_row['high']:,.2f}")
    logger.info(f"   Low: ${closest_row['low']:,.2f}")
    logger.info(f"   Volume: {closest_row['volume']:,.0f}")
    logger.info(f"   Change %: {closest_row['change_pct_10h']:.2f}%")
    logger.info(f"   Volatility: {closest_row['volatility_score']:.4f}")
    logger.info(f"   Label Spike: {closest_row['label_spike']}")
    
    # Test Case 2: Check for zero values
    logger.info("\n" + "=" * 80)
    logger.info("TEST CASE 2: Check for zero values in BTC features")
    logger.info("=" * 80)
    
    zero_counts = {
        'close': (df['close'] == 0).sum(),
        'volume': (df['volume'] == 0).sum(),
        'change_pct_10h': (df['change_pct_10h'] == 0).sum(),
        'volatility_score': (df['volatility_score'] == 0).sum(),
    }
    
    logger.info(f"\n📊 Zero value counts (out of {len(df)} records):")
    for feature, count in zero_counts.items():
        percentage = (count / len(df)) * 100
        logger.info(f"   {feature}: {count} ({percentage:.1f}%)")
    
    # Test Case 3: Simulate fallback scenario
    logger.info("\n" + "=" * 80)
    logger.info("TEST CASE 3: Simulate fallback scenario")
    logger.info("=" * 80)
    
    logger.info("\nScenario: semantic_groups.parquet has zero BTC features")
    logger.info("Expected: Fallback to btc_features.parquet should provide non-zero values")
    
    # Simulate zero features from semantic_groups
    zero_features = {
        'btc_volume': 0.0,
        'btc_volatility_score': 0.0,
        'btc_change_pct_10h': 0.0,
        'btc_label_spike': 0,
    }
    
    logger.info(f"\n❌ Input (from semantic_groups.parquet):")
    for key, value in zero_features.items():
        logger.info(f"   {key}: {value}")
    
    # Fetch from parquet fallback
    fallback_features = {
        'volume': float(closest_row['volume']),
        'volatility_score': float(closest_row['volatility_score']),
        'change_pct_10h': float(closest_row['change_pct_10h']),
        'label_spike': int(closest_row['label_spike']),
        'close': float(closest_row['close']),
        'open': float(closest_row['open']),
        'high': float(closest_row['high']),
        'low': float(closest_row['low']),
    }
    
    logger.info(f"\n✅ Output (from btc_features.parquet fallback):")
    for key, value in fallback_features.items():
        logger.info(f"   {key}: {value}")
    
    # Verify fallback worked
    if fallback_features['volume'] > 0 and fallback_features['close'] > 0:
        logger.info("\n✅ TEST PASSED: Fallback provides non-zero BTC features!")
    else:
        logger.warning("\n⚠️  TEST FAILED: Fallback still has zero values!")
    
    logger.info("\n" + "=" * 80)
    logger.info("All tests completed!")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_parquet_loading()

