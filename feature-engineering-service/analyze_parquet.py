"""Analyze parquet files to diagnose BTC features issue."""
import pandas as pd
from pathlib import Path

# Paths
repo_root = Path(__file__).parent.parent
semantic_groups_path = repo_root / "feast" / "offline_store" / "semantic_groups.parquet"
btc_features_path = repo_root / "feast" / "offline_store" / "btc_features.parquet"

print("=" * 80)
print("SEMANTIC GROUPS PARQUET ANALYSIS")
print("=" * 80)

if semantic_groups_path.exists():
    df_semantic = pd.read_parquet(semantic_groups_path)
    print(f"\nShape: {df_semantic.shape}")
    print(f"\nColumns ({len(df_semantic.columns)}):")
    for col in sorted(df_semantic.columns):
        print(f"  - {col}")
    
    # Check for BTC columns
    btc_cols = [c for c in df_semantic.columns if 'btc' in c.lower()]
    print(f"\nBTC-related columns ({len(btc_cols)}):")
    for col in btc_cols:
        print(f"  - {col}")
    
    if btc_cols:
        print(f"\nBTC columns statistics:")
        print(df_semantic[btc_cols].describe())
        
        print(f"\nNull/NaN counts in BTC columns:")
        for col in btc_cols:
            null_count = df_semantic[col].isna().sum()
            zero_count = (df_semantic[col] == 0).sum() if df_semantic[col].dtype in ['float64', 'int64'] else 0
            print(f"  {col}: {null_count} nulls, {zero_count} zeros out of {len(df_semantic)} rows")
        
        print(f"\nSample BTC values (first 10 rows):")
        print(df_semantic[['timestamp'] + btc_cols].head(10))
        
        print(f"\nSample BTC values (last 10 rows):")
        print(df_semantic[['timestamp'] + btc_cols].tail(10))
    else:
        print("\n⚠️  NO BTC COLUMNS FOUND IN SEMANTIC GROUPS!")
    
    print(f"\nTimestamp column info:")
    if 'timestamp' in df_semantic.columns:
        print(f"  Type: {df_semantic['timestamp'].dtype}")
        print(f"  Range: {df_semantic['timestamp'].min()} to {df_semantic['timestamp'].max()}")
        print(f"  Count: {len(df_semantic)}")
else:
    print(f"\n⚠️  File not found: {semantic_groups_path}")

print("\n" + "=" * 80)
print("BTC FEATURES PARQUET ANALYSIS")
print("=" * 80)

if btc_features_path.exists():
    df_btc = pd.read_parquet(btc_features_path)
    print(f"\nShape: {df_btc.shape}")
    print(f"\nColumns ({len(df_btc.columns)}):")
    for col in sorted(df_btc.columns):
        print(f"  - {col}")
    
    print(f"\nFirst 5 rows:")
    print(df_btc.head())
    
    print(f"\nLast 5 rows:")
    print(df_btc.tail())
    
    if 'timestamp' in df_btc.columns:
        print(f"\nTimestamp info:")
        print(f"  Type: {df_btc['timestamp'].dtype}")
        print(f"  Range: {df_btc['timestamp'].min()} to {df_btc['timestamp'].max()}")
        print(f"  Count: {len(df_btc)}")
else:
    print(f"\n⚠️  File not found: {btc_features_path}")

print("\n" + "=" * 80)
print("TIMESTAMP COMPARISON")
print("=" * 80)

if semantic_groups_path.exists() and btc_features_path.exists():
    df_semantic = pd.read_parquet(semantic_groups_path)
    df_btc = pd.read_parquet(btc_features_path)
    
    if 'timestamp' in df_semantic.columns and 'timestamp' in df_btc.columns:
        print(f"\nSemantic groups timestamp range:")
        print(f"  {df_semantic['timestamp'].min()} to {df_semantic['timestamp'].max()}")
        
        print(f"\nBTC features timestamp range:")
        print(f"  {df_btc['timestamp'].min()} to {df_btc['timestamp'].max()}")
        
        # Check for overlap
        semantic_min = df_semantic['timestamp'].min()
        semantic_max = df_semantic['timestamp'].max()
        btc_min = df_btc['timestamp'].min()
        btc_max = df_btc['timestamp'].max()
        
        overlap = not (semantic_max < btc_min or btc_max < semantic_min)
        print(f"\nTimestamp ranges overlap: {overlap}")
        
        if not overlap:
            print("\n⚠️  WARNING: No timestamp overlap between semantic groups and BTC features!")
            print("   This could explain why BTC features are not being populated.")

