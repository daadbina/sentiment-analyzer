import asyncio
import asyncpg

async def clear_db():
    conn = await asyncpg.connect(
        host='154.53.166.231',
        port=5432,
        user='adminsentiment',
        password='wp2400!!!!',
        database='sentiment'
    )
    
    try:
        # Clear tables
        await conn.execute('TRUNCATE TABLE deduplication_cache CASCADE')
        print('✓ Cleared deduplication_cache')
        
        await conn.execute('TRUNCATE TABLE ground_truth CASCADE')
        print('✓ Cleared ground_truth')
        
        await conn.execute('TRUNCATE TABLE btc_truth CASCADE')
        print('✓ Cleared btc_truth')
        
        await conn.execute('TRUNCATE TABLE outbox CASCADE')
        print('✓ Cleared outbox')
        
        print('\n✓ Database cleared successfully!')
    finally:
        await conn.close()

asyncio.run(clear_db())

