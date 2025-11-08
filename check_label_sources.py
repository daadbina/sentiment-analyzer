import asyncio
import asyncpg

async def check_label_sources():
    conn = await asyncpg.connect(
        host='154.53.166.231',
        port=5432,
        user='adminsentiment',
        password='wp2400!!!!',
        database='sentiment'
    )
    
    # Check label sources
    result = await conn.fetch('''
        SELECT label_source, COUNT(*) as count
        FROM ground_truth
        GROUP BY label_source
        ORDER BY count DESC
    ''')
    
    print('Label sources in ground_truth:')
    for row in result:
        print(f'  {row["label_source"]}: {row["count"]}')
    
    # Check a sample label from each source
    print('\nSample labels:')
    for source in ['acled', 'gdelt', 'binance', 'coingecko']:
        sample = await conn.fetch('''
            SELECT event_id, description, label_source, label_confidence
            FROM ground_truth
            WHERE label_source = $1
            LIMIT 1
        ''', source)
        
        if sample:
            row = sample[0]
            print(f'\n{source}:')
            print(f'  event_id: {row["event_id"]}')
            print(f'  description: {row["description"][:100] if row["description"] else "None"}')
            print(f'  label_confidence: {row["label_confidence"]}')
    
    await conn.close()

asyncio.run(check_label_sources())

