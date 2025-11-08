#!/usr/bin/env python3
"""Check what tables exist in the database."""

import asyncio
import asyncpg

async def main():
    # Connect to PostgreSQL
    conn = await asyncpg.connect(
        host='154.53.166.231',
        port=5432,
        user='adminsentiment',
        password='wp2400!!!!',
        database='sentiment_analyzer'
    )
    
    try:
        # Get all tables
        tables = await conn.fetch('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        ''')
        print("Tables in sentiment_analyzer database:")
        for row in tables:
            print(f"  - {row['table_name']}")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

