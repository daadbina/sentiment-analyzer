"""Test BTC database query to diagnose the issue."""
import asyncio
import asyncpg
from datetime import datetime, timedelta, timezone
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

async def test_btc_query():
    """Test BTC query with actual semantic group timestamps."""
    
    # Load semantic groups to get actual timestamps
    repo_root = Path(__file__).parent.parent
    semantic_groups_path = repo_root / "feast" / "offline_store" / "semantic_groups.parquet"
    df_semantic = pd.read_parquet(semantic_groups_path)
    df_semantic['timestamp'] = pd.to_datetime(df_semantic['timestamp'])
    
    # Get rows with zero BTC features
    zero_btc_rows = df_semantic[df_semantic['btc_change_pct_10h'] == 0].head(5)
    
    print("=" * 100)
    print("TESTING BTC DATABASE QUERIES")
    print("=" * 100)
    
    # Connect to database
    print("\n1. Connecting to PostgreSQL...")
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print("   ✓ Connected successfully")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return
    
    # Test queries for each zero-BTC row
    print("\n2. Testing queries for semantic groups with zero BTC features:")
    print("-" * 100)
    
    for idx, row in zero_btc_rows.iterrows():
        sg_timestamp = row['timestamp']
        print(f"\n[Row {idx}] Semantic group timestamp: {sg_timestamp}")
        
        # Convert to timezone-naive (as the code does)
        timestamp_naive = sg_timestamp.tz_localize(None) if sg_timestamp.tzinfo else sg_timestamp
        
        # Calculate time window (±1 hour)
        window_hours = 1
        start_time_naive = timestamp_naive - timedelta(hours=window_hours)
        end_time_naive = timestamp_naive + timedelta(hours=window_hours)
        
        print(f"  Search window: {start_time_naive} to {end_time_naive}")
        print(f"  Query timestamp: {timestamp_naive}")
        
        # Execute the EXACT query from the code
        query = """
            SELECT
                change_pct_10h,
                volatility_score,
                volume,
                label_spike,
                timestamp,
                close
            FROM btc_truth
            WHERE timestamp >= $1 AND timestamp <= $2
            AND close > 10000
            ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - $3)))
            LIMIT 1
        """
        
        try:
            result = await conn.fetch(query, start_time_naive, end_time_naive, timestamp_naive)
            
            if result and len(result) > 0:
                row_data = dict(result[0])
                print(f"  ✓ Query returned {len(result)} row(s)")
                print(f"    BTC timestamp: {row_data['timestamp']}")
                print(f"    BTC close: {row_data['close']}")
                print(f"    BTC change_pct_10h: {row_data['change_pct_10h']}")
                print(f"    BTC volume: {row_data['volume']}")
            else:
                print(f"  ✗ Query returned NO rows")
                
                # Try to understand why - check if ANY BTC data exists in window
                check_query = """
                    SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
                    FROM btc_truth
                    WHERE timestamp >= $1 AND timestamp <= $2
                """
                check_result = await conn.fetchrow(check_query, start_time_naive, end_time_naive)
                print(f"    BTC rows in window (no close filter): {check_result['count']}")
                if check_result['count'] > 0:
                    print(f"    BTC timestamp range: {check_result['min']} to {check_result['max']}")
                
                # Check with close > 10000 filter
                check_query2 = """
                    SELECT COUNT(*), MIN(close), MAX(close)
                    FROM btc_truth
                    WHERE timestamp >= $1 AND timestamp <= $2
                    AND close > 10000
                """
                check_result2 = await conn.fetchrow(check_query2, start_time_naive, end_time_naive)
                print(f"    BTC rows in window (close > 10000): {check_result2['count']}")
                if check_result2['count'] > 0:
                    print(f"    BTC close range: {check_result2['min']} to {check_result2['max']}")
                
        except Exception as e:
            print(f"  ✗ Query failed with error: {type(e).__name__}: {e}")
    
    # Check overall BTC data availability
    print("\n" + "=" * 100)
    print("3. OVERALL BTC DATA AVAILABILITY")
    print("=" * 100)
    
    try:
        # Get BTC data count and time range
        stats_query = """
            SELECT 
                COUNT(*) as total_rows,
                MIN(timestamp) as min_ts,
                MAX(timestamp) as max_ts,
                MIN(close) as min_close,
                MAX(close) as max_close,
                COUNT(CASE WHEN close > 10000 THEN 1 END) as btc_rows,
                COUNT(CASE WHEN close <= 10000 THEN 1 END) as non_btc_rows
            FROM btc_truth
        """
        stats = await conn.fetchrow(stats_query)
        
        print(f"\nTotal rows in btc_truth: {stats['total_rows']}")
        print(f"Timestamp range: {stats['min_ts']} to {stats['max_ts']}")
        print(f"Close price range: ${stats['min_close']:,.2f} to ${stats['max_close']:,.2f}")
        print(f"BTC rows (close > $10,000): {stats['btc_rows']}")
        print(f"Non-BTC rows (close <= $10,000): {stats['non_btc_rows']}")
        
        # Get sample BTC data around the semantic group timestamps
        sample_query = """
            SELECT timestamp, close, change_pct_10h, volume
            FROM btc_truth
            WHERE timestamp >= $1 AND timestamp <= $2
            AND close > 10000
            ORDER BY timestamp
            LIMIT 10
        """
        
        sg_min = df_semantic['timestamp'].min().tz_localize(None)
        sg_max = df_semantic['timestamp'].max().tz_localize(None)
        
        print(f"\nSample BTC data around semantic group timestamps ({sg_min} to {sg_max}):")
        sample_result = await conn.fetch(sample_query, sg_min - timedelta(hours=2), sg_max + timedelta(hours=2))
        
        for row in sample_result:
            print(f"  {row['timestamp']} | close: ${row['close']:,.2f} | change: {row['change_pct_10h']:.2f}% | volume: {row['volume']:.2f}")
        
    except Exception as e:
        print(f"Error getting BTC stats: {e}")
    
    await conn.close()
    print("\n✓ Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_btc_query())

