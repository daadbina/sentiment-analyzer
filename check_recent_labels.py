import asyncio
import asyncpg
from datetime import datetime, timedelta

async def check_recent_labels():
    conn = await asyncpg.connect(
        host='154.53.166.231',
        port=5432,
        user='adminsentiment',
        password='wp2400!!!!',
        database='sentiment'
    )
    
    # Check when labels were last written
    result = await conn.fetch('''
        SELECT MAX(created_at) as last_created
        FROM ground_truth
    ''')

    print('Last label write times:')
    print(f'  Last created: {result[0]["last_created"]}')
    
    # Check labels from last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent = await conn.fetch('''
        SELECT COUNT(*) as count
        FROM ground_truth
        WHERE created_at >= $1
    ''', yesterday)
    
    print(f'Labels created in last 24 hours: {recent[0]["count"]}')
    
    await conn.close()

asyncio.run(check_recent_labels())

