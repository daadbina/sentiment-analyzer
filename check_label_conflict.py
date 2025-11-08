import asyncio
import asyncpg

async def check_label_conflict():
    conn = await asyncpg.connect(
        host='154.53.166.231',
        port=5432,
        user='adminsentiment',
        password='wp2400!!!!',
        database='sentiment'
    )
    
    # Check if label_conflict column exists
    columns = await conn.fetch('''
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'ground_truth'
        ORDER BY ordinal_position
    ''')
    
    print('Ground Truth table columns:')
    for col in columns:
        print(f'  - {col["column_name"]}')
    
    await conn.close()

asyncio.run(check_label_conflict())

