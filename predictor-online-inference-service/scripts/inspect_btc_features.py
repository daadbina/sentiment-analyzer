#!/usr/bin/env python3
"""
Script to inspect BTC features from parquet files and understand why they might be 0.
"""

import pandas as pd
import sys
from pathlib import Path

# Parquet file paths
BTC_FEATURES_PATH = r"C:\Users\daadb\Documents\sentiment-analyzer\feast\offline_store\btc_features.parquet"
SEMANTIC_GROUPS_PATH = r"C:\Users\daadb\Documents\sentiment-analyzer\feast\offline_store\semantic_groups.parquet"


def inspect_btc_features():
    """Inspect BTC features parquet file."""
    print("=" * 100)
    print("INSPECTING BTC FEATURES PARQUET FILE")
    print("=" * 100)
    
    if not Path(BTC_FEATURES_PATH).exists():
        print(f"❌ File not found: {BTC_FEATURES_PATH}")
        return
    
    # Load parquet file
    df = pd.read_parquet(BTC_FEATURES_PATH)
    
    print(f"\n✓ Loaded BTC features: {len(df)} rows, {len(df.columns)} columns")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nData types:\n{df.dtypes}")
    
    print(f"\n{'=' * 100}")
    print("SAMPLE DATA (First 5 rows)")
    print(f"{'=' * 100}")
    print(df.head())
    
    print(f"\n{'=' * 100}")
    print("SAMPLE DATA (Last 5 rows)")
    print(f"{'=' * 100}")
    print(df.tail())
    
    print(f"\n{'=' * 100}")
    print("STATISTICS FOR BTC FEATURES")
    print(f"{'=' * 100}")
    print(df.describe())
    
    # Check for zero values
    print(f"\n{'=' * 100}")
    print("CHECKING FOR ZERO/NULL VALUES")
    print(f"{'=' * 100}")
    
    for col in df.columns:
        if col in ['timestamp', 'event_timestamp', 'created']:
            continue
        
        zero_count = (df[col] == 0).sum()
        null_count = df[col].isnull().sum()
        total = len(df)
        
        if zero_count > 0 or null_count > 0:
            print(f"{col:30s} - Zeros: {zero_count:5d} ({zero_count/total*100:5.1f}%), "
                  f"Nulls: {null_count:5d} ({null_count/total*100:5.1f}%)")
    
    # Check specific BTC features mentioned in the code
    btc_feature_cols = [
        'btc_change_pct_10h', 'btc_volatility_score', 'btc_volume', 'btc_label_spike',
        'change_pct_10h', 'volatility_score', 'volume', 'label_spike',
        'close', 'open', 'high', 'low'
    ]
    
    print(f"\n{'=' * 100}")
    print("SPECIFIC BTC FEATURE VALUES")
    print(f"{'=' * 100}")
    
    for col in btc_feature_cols:
        if col in df.columns:
            print(f"\n{col}:")
            print(f"  Min: {df[col].min()}")
            print(f"  Max: {df[col].max()}")
            print(f"  Mean: {df[col].mean()}")
            print(f"  Median: {df[col].median()}")
            print(f"  Non-zero count: {(df[col] != 0).sum()} / {len(df)}")


def inspect_semantic_groups():
    """Inspect semantic groups parquet file."""
    print(f"\n\n{'=' * 100}")
    print("INSPECTING SEMANTIC GROUPS PARQUET FILE")
    print(f"{'=' * 100}")
    
    if not Path(SEMANTIC_GROUPS_PATH).exists():
        print(f"❌ File not found: {SEMANTIC_GROUPS_PATH}")
        return
    
    # Load parquet file
    df = pd.read_parquet(SEMANTIC_GROUPS_PATH)
    
    print(f"\n✓ Loaded semantic groups: {len(df)} rows, {len(df.columns)} columns")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nData types:\n{df.dtypes}")
    
    print(f"\n{'=' * 100}")
    print("SAMPLE DATA (First 5 rows)")
    print(f"{'=' * 100}")
    print(df.head())
    
    print(f"\n{'=' * 100}")
    print("SAMPLE DATA (Last 5 rows)")
    print(f"{'=' * 100}")
    print(df.tail())
    
    # Check for BTC-related columns
    btc_cols = [col for col in df.columns if 'btc' in col.lower()]
    if btc_cols:
        print(f"\n{'=' * 100}")
        print(f"BTC-RELATED COLUMNS IN SEMANTIC GROUPS: {btc_cols}")
        print(f"{'=' * 100}")
        
        for col in btc_cols:
            print(f"\n{col}:")
            print(f"  Min: {df[col].min()}")
            print(f"  Max: {df[col].max()}")
            print(f"  Mean: {df[col].mean()}")
            print(f"  Non-zero count: {(df[col] != 0).sum()} / {len(df)}")


def main():
    """Main function."""
    try:
        inspect_btc_features()
        inspect_semantic_groups()
        
        print(f"\n\n{'=' * 100}")
        print("INSPECTION COMPLETE")
        print(f"{'=' * 100}")
        
    except Exception as e:
        print(f"\n{'=' * 100}")
        print(f"ERROR: {e}")
        print(f"{'=' * 100}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

