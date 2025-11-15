"""Test the lookback-only fix for BTC feature extraction."""
import asyncio
import asyncpg
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

# Database config
DB_CONFIG = {
    'host': '154.53.166.231',
    'port': 5432,
    'database': 'sentiment',
    'user': 'adminsentiment',
    'password': 'wp2400!!!!'
}

async def test_lookback_query():
    """Test the new lookback-only query approach."""
    
    # Load semantic groups to get actual timestamps
    repo_root = Path(__file__).parent.parent
    semantic_groups_path = repo_root / "feast" / "offline_store" / "semantic_groups.parquet"
    df_semantic = pd.read_parquet(semantic_groups_path)
    df_semantic['timestamp'] = pd.to_datetime(df_semantic['timestamp'])
    
    # Get rows that previously had zero BTC features
    zero_btc_rows = df_semantic[df_semantic['btc_change_pct_10h'] == 0].head(10)
    
    print("=" * 100)
    print("TESTING LOOKBACK-ONLY FIX FOR BTC FEATURE EXTRACTION")
    print("=" * 100)
    
    # Connect to database
    print("\n1. Connecting to PostgreSQL...")
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print("   ✓ Connected successfully")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return
    
    # Test the NEW lookback-only query
    print("\n2. Testing NEW lookback-only query:")
    print("-" * 100)
    
    max_lookback_hours = 24
    success_count = 0
    fail_count = 0
    
    for idx, row in zero_btc_rows.iterrows():
        sg_timestamp = row['timestamp']
        
        # Convert to timezone-naive (as the code does)
        timestamp_naive = sg_timestamp.tz_localize(None) if sg_timestamp.tzinfo else sg_timestamp
        min_lookback_time = timestamp_naive - timedelta(hours=max_lookback_hours)
        
        print(f"\n[Row {idx}] Semantic group timestamp: {sg_timestamp}")
        print(f"  Lookback window: {min_lookback_time} to {timestamp_naive}")
        
        # Execute the NEW lookback-only query
        query = """
            SELECT
                change_pct_10h,
                volatility_score,
                volume,
                label_spike,
                timestamp,
                close
            FROM btc_truth
            WHERE timestamp <= $1
            AND timestamp >= $2
            AND close > 10000
            ORDER BY timestamp DESC
            LIMIT 1
        """
        
        try:
            result = await conn.fetch(query, timestamp_naive, min_lookback_time)
            
            if result and len(result) > 0:
                row_data = dict(result[0])
                time_diff = timestamp_naive - row_data['timestamp']
                time_diff_minutes = time_diff.total_seconds() / 60
                
                print(f"  ✓ Query returned 1 row")
                print(f"    BTC timestamp: {row_data['timestamp']}")
                print(f"    Time difference: {time_diff_minutes:.1f} minutes (lookback)")
                print(f"    BTC close: ${row_data['close']:,.2f}")
                print(f"    BTC change_pct_10h: {row_data['change_pct_10h']:.2f}%")
                print(f"    BTC volume: {row_data['volume']:.2f}")
                success_count += 1
            else:
                print(f"  ✗ Query returned NO rows")
                fail_count += 1
                
        except Exception as e:
            print(f"  ✗ Query failed with error: {type(e).__name__}: {e}")
            fail_count += 1
    
    print("\n" + "=" * 100)
    print("RESULTS SUMMARY")
    print("=" * 100)
    print(f"\n✓ Successful queries: {success_count} / {len(zero_btc_rows)}")
    print(f"✗ Failed queries: {fail_count} / {len(zero_btc_rows)}")
    
    if success_count == len(zero_btc_rows):
        print("\n🎉 SUCCESS! All previously failing semantic groups now return BTC data!")
        print("   The lookback-only approach eliminates the race condition.")
    else:
        print(f"\n⚠️  WARNING: {fail_count} queries still failing")
    
    # Compare OLD vs NEW approach
    print("\n" + "=" * 100)
    print("COMPARISON: OLD (±1 hour window) vs NEW (lookback-only)")
    print("=" * 100)
    
    # Test one example with both approaches
    test_row = zero_btc_rows.iloc[0]
    test_timestamp = test_row['timestamp'].tz_localize(None) if test_row['timestamp'].tzinfo else test_row['timestamp']
    
    print(f"\nTest timestamp: {test_timestamp}")
    
    # OLD approach (±1 hour window)
    print("\nOLD APPROACH (±1 hour window):")
    window_hours = 1
    start_time = test_timestamp - timedelta(hours=window_hours)
    end_time = test_timestamp + timedelta(hours=window_hours)
    
    old_query = """
        SELECT timestamp, close, change_pct_10h
        FROM btc_truth
        WHERE timestamp >= $1 AND timestamp <= $2
        AND close > 10000
        ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - $3)))
        LIMIT 1
    """
    
    old_result = await conn.fetch(old_query, start_time, end_time, test_timestamp)
    if old_result:
        print(f"  ✓ Found: {old_result[0]['timestamp']} (close: ${old_result[0]['close']:,.2f})")
    else:
        print(f"  ✗ No data found (this is the race condition!)")
    
    # NEW approach (lookback-only)
    print("\nNEW APPROACH (lookback-only):")
    new_result = await conn.fetch(query, test_timestamp, test_timestamp - timedelta(hours=max_lookback_hours))
    if new_result:
        time_diff = test_timestamp - new_result[0]['timestamp']
        print(f"  ✓ Found: {new_result[0]['timestamp']} (close: ${new_result[0]['close']:,.2f})")
        print(f"    Lookback: {time_diff.total_seconds() / 60:.1f} minutes")
    else:
        print(f"  ✗ No data found")
    
    await conn.close()
    print("\n✓ Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_lookback_query())

