"""Check PostgreSQL features format."""
import asyncio
import asyncpg
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def check():
    conn = await asyncpg.connect(
        host=os.getenv('POSTGRES_HOST'),
        port=int(os.getenv('POSTGRES_PORT')),
        database=os.getenv('POSTGRES_DATABASE'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD')
    )
    
    row = await conn.fetchrow("SELECT features FROM predictions WHERE domain = 'btc' LIMIT 1")
    features = json.loads(row['features'])
    
    print("PostgreSQL features keys:")
    for key in sorted(features.keys()):
        print(f"  - {key}: {features[key]}")
    
    await conn.close()

asyncio.run(check())

