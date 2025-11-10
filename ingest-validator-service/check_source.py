import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect('postgresql://adminsentiment:wp2400!!!!@154.53.166.231:5432/sentiment')
    rows = await conn.fetch("SELECT id, name, credibility_score, is_active, publisher_id FROM sources WHERE id = 'webhose_free_datasets'")
    print(f"Found {len(rows)} rows:")
    for row in rows:
        print(f"  ID: {row['id']}, Name: {row['name']}, Credibility: {row['credibility_score']}, Active: {row['is_active']}, Publisher: {row['publisher_id']}")
    await conn.close()

asyncio.run(check())

