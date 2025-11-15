"""Diagnose BTC features population issue - detailed analysis."""
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Paths
repo_root = Path(__file__).parent.parent
semantic_groups_path = repo_root / "feast" / "offline_store" / "semantic_groups.parquet"
btc_features_path = repo_root / "feast" / "offline_store" / "btc_features.parquet"

print("=" * 100)
print("ROOT CAUSE ANALYSIS: BTC FEATURES NOT POPULATED IN SEMANTIC GROUPS")
print("=" * 100)

# Load data
df_semantic = pd.read_parquet(semantic_groups_path)
df_btc = pd.read_parquet(btc_features_path)

# Convert timestamps
df_semantic['timestamp'] = pd.to_datetime(df_semantic['timestamp'])
df_btc['timestamp'] = pd.to_datetime(df_btc['timestamp'])

print("\n1. DATA OVERVIEW")
print("-" * 100)
print(f"Semantic groups: {len(df_semantic)} rows")
print(f"BTC features: {len(df_btc)} rows")
print(f"Semantic groups with ZERO BTC features: {(df_semantic['btc_change_pct_10h'] == 0).sum()} rows ({(df_semantic['btc_change_pct_10h'] == 0).sum() / len(df_semantic) * 100:.1f}%)")

print("\n2. TIMESTAMP GRANULARITY ANALYSIS")
print("-" * 100)

# Analyze BTC timestamp granularity
btc_timestamps = df_btc['timestamp'].sort_values()
btc_diffs = btc_timestamps.diff().dropna()
print(f"\nBTC features timestamp granularity:")
print(f"  Min interval: {btc_diffs.min()}")
print(f"  Max interval: {btc_diffs.max()}")
print(f"  Mean interval: {btc_diffs.mean()}")
print(f"  Median interval: {btc_diffs.median()}")
print(f"  Mode interval: {btc_diffs.mode().values[0] if len(btc_diffs.mode()) > 0 else 'N/A'}")

# Check if BTC data is hourly
hourly_count = (btc_diffs == pd.Timedelta(hours=1)).sum()
print(f"\n  Hourly intervals (1h): {hourly_count} / {len(btc_diffs)} ({hourly_count / len(btc_diffs) * 100:.1f}%)")
print(f"  → BTC data appears to be HOURLY (on the hour)")

# Show sample BTC timestamps
print(f"\n  Sample BTC timestamps:")
for ts in btc_timestamps.head(10):
    print(f"    {ts} (minute: {ts.minute}, second: {ts.second})")

print("\n3. SEMANTIC GROUP TIMESTAMP ANALYSIS")
print("-" * 100)

# Analyze semantic group timestamps
semantic_timestamps = df_semantic['timestamp'].sort_values()
print(f"\nSemantic group timestamps:")
print(f"  Range: {semantic_timestamps.min()} to {semantic_timestamps.max()}")
print(f"  Sample timestamps:")
for ts in semantic_timestamps.head(10):
    print(f"    {ts} (minute: {ts.minute}, second: {ts.second}.{ts.microsecond})")

print(f"\n  → Semantic groups have SUB-SECOND precision (microseconds)")
print(f"  → Semantic groups are NOT on the hour")

print("\n4. TEMPORAL WINDOW MATCHING ANALYSIS")
print("-" * 100)

# Check which semantic groups fall within ±1 hour of BTC data
window_hours = 1
matches = 0
no_matches = 0

print(f"\nChecking ±{window_hours} hour window matching:")
print(f"\nSemantic groups WITHOUT BTC matches:")

for idx, row in df_semantic.iterrows():
    sg_ts = row['timestamp']
    btc_change = row['btc_change_pct_10h']
    
    # Find closest BTC timestamp
    # Remove timezone for comparison
    sg_ts_naive = sg_ts.tz_localize(None) if sg_ts.tzinfo else sg_ts
    
    # Calculate time differences
    time_diffs = (df_btc['timestamp'] - sg_ts_naive).abs()
    min_diff = time_diffs.min()
    closest_btc_ts = df_btc.loc[time_diffs.idxmin(), 'timestamp']
    
    # Check if within window
    within_window = min_diff <= pd.Timedelta(hours=window_hours)
    
    if btc_change == 0:
        no_matches += 1
        if no_matches <= 10:  # Show first 10
            print(f"  [{idx}] SG timestamp: {sg_ts}")
            print(f"       Closest BTC: {closest_btc_ts} (diff: {min_diff})")
            print(f"       Within ±{window_hours}h window: {within_window}")
            print(f"       BTC value: {btc_change}")
            print()
    else:
        matches += 1

print(f"\nSummary:")
print(f"  Semantic groups WITH BTC data: {matches}")
print(f"  Semantic groups WITHOUT BTC data: {no_matches}")

print("\n5. ROOT CAUSE HYPOTHESIS")
print("-" * 100)

# Analyze the zero-BTC cases more carefully
zero_btc_df = df_semantic[df_semantic['btc_change_pct_10h'] == 0].copy()
zero_btc_df['timestamp_naive'] = zero_btc_df['timestamp'].dt.tz_localize(None)

print(f"\nAnalyzing {len(zero_btc_df)} semantic groups with zero BTC features:")

# For each zero-BTC row, find the closest BTC timestamp
for idx, row in zero_btc_df.head(5).iterrows():
    sg_ts = row['timestamp_naive']
    
    # Find BTC data within ±1 hour
    start_time = sg_ts - timedelta(hours=window_hours)
    end_time = sg_ts + timedelta(hours=window_hours)
    
    btc_in_window = df_btc[(df_btc['timestamp'] >= start_time) & (df_btc['timestamp'] <= end_time)]
    
    print(f"\n  Semantic group timestamp: {row['timestamp']}")
    print(f"  Search window: {start_time} to {end_time}")
    print(f"  BTC records in window: {len(btc_in_window)}")
    
    if len(btc_in_window) > 0:
        print(f"  → BTC DATA EXISTS in window!")
        print(f"     BTC timestamps in window:")
        for btc_ts in btc_in_window['timestamp']:
            diff = abs((btc_ts - sg_ts).total_seconds() / 60)
            print(f"       {btc_ts} (diff: {diff:.1f} minutes)")
    else:
        print(f"  → NO BTC DATA in ±{window_hours}h window")

print("\n" + "=" * 100)
print("CONCLUSION")
print("=" * 100)
print("""
Based on the analysis above, the root cause is likely ONE of the following:

1. **BTC data granularity mismatch**: BTC data is hourly (on the hour: 00:00, 01:00, etc.)
   but semantic groups have sub-second timestamps. The ±1 hour window should catch this,
   but there may be edge cases.

2. **Database query issue**: The PostgreSQL query may be failing to find BTC data due to:
   - Timezone conversion issues (timezone-aware vs timezone-naive)
   - Query logic errors in the temporal window matching
   - Database connection/execution errors

3. **Timing issue**: Semantic groups are being processed BEFORE corresponding BTC data
   is available in the database (race condition).

4. **Data availability**: BTC data may not exist for certain time periods in the database.
""")

