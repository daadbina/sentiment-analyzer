import asyncio
import asyncpg

async def check_labels():
    conn = await asyncpg.connect(
        host='154.53.166.231',
        port=5432,
        user='adminsentiment',
        password='wp2400!!!!',
        database='sentiment'
    )
    
    # Check label_realized values
    result = await conn.fetch('''
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN label_realized IS NOT NULL THEN 1 END) as non_null_realized,
            COUNT(CASE WHEN group_id IS NOT NULL THEN 1 END) as non_null_group_id
        FROM ground_truth
    ''')
    
    print('Ground Truth Table Stats:')
    print(f'  Total rows: {result[0]["total"]}')
    print(f'  Non-null label_realized: {result[0]["non_null_realized"]}')
    print(f'  Non-null group_id: {result[0]["non_null_group_id"]}')
    
    # Check a sample of recent labels
    sample = await conn.fetch('''
        SELECT event_id, group_id, label_realized, label_confidence, created_at
        FROM ground_truth
        WHERE label_realized IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 5
    ''')
    
    print('\nSample of labels with label_realized:')
    for row in sample:
        print(f'  event_id={row["event_id"]}, group_id={row["group_id"]}, label_realized={row["label_realized"]}')
    
    await conn.close()

asyncio.run(check_labels())

