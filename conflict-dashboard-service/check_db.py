"""Quick script to check database predictions."""

import asyncio
import asyncpg

async def check_predictions():
    conn = await asyncpg.connect(
        host="154.53.166.231",
        port=5432,
        user="adminsentiment",
        password="wp2400!!!!",
        database="sentiment",
    )
    
    # Check total predictions
    total = await conn.fetchval("SELECT COUNT(*) FROM predictions")
    print(f"Total predictions: {total}")
    
    # Check by domain
    domains = await conn.fetch("SELECT domain, COUNT(*) as count FROM predictions GROUP BY domain")
    print("\nPredictions by domain:")
    for row in domains:
        print(f"  {row['domain']}: {row['count']}")
    
    # Check recent predictions
    recent = await conn.fetch("""
        SELECT domain, prediction_probability, features, predicted_at 
        FROM predictions 
        ORDER BY predicted_at DESC 
        LIMIT 5
    """)
    print("\nRecent predictions:")
    for row in recent:
        print(f"  Domain: {row['domain']}, Prob: {row['prediction_probability']:.3f}, Time: {row['predicted_at']}")
        if row['features']:
            print(f"    Features keys: {list(row['features'].keys())}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_predictions())

