import asyncio
import asyncpg

async def update_label_realized():
    conn = await asyncpg.connect(
        host='154.53.166.231',
        port=5432,
        user='adminsentiment',
        password='wp2400!!!!',
        database='sentiment'
    )
    
    # Update label_realized for GDELT labels
    # GDELT only includes conflict events, so all should be TRUE
    result = await conn.execute('''
        UPDATE ground_truth
        SET label_realized = TRUE
        WHERE label_source = 'gdelt' AND label_realized IS NULL
    ''')
    
    print(f'Updated {result} GDELT labels with label_realized = 1')
    
    # Verify the update
    check = await conn.fetch('''
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN label_realized IS NOT NULL THEN 1 END) as non_null_realized,
            COUNT(CASE WHEN label_realized = TRUE THEN 1 END) as realized_true,
            COUNT(CASE WHEN label_realized = FALSE THEN 1 END) as realized_false
        FROM ground_truth
    ''')
    
    print('\nGround Truth Table Stats after update:')
    print(f'  Total rows: {check[0]["total"]}')
    print(f'  Non-null label_realized: {check[0]["non_null_realized"]}')
    print(f'  label_realized = TRUE: {check[0]["realized_true"]}')
    print(f'  label_realized = FALSE: {check[0]["realized_false"]}')
    
    await conn.close()

asyncio.run(update_label_realized())

