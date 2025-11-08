#!/usr/bin/env python3
"""Check all tables in all schemas."""

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
        # Get all schemas
        schemas = await conn.fetch("""
            SELECT schema_name 
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
            ORDER BY schema_name
        """)
        print("Schemas:")
        for row in schemas:
            print(f"  - {row['schema_name']}")
        
        # Get all tables in all schemas
        tables = await conn.fetch("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """)
        print("\nTables:")
        for row in tables:
            print(f"  {row['table_schema']}.{row['table_name']}")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

