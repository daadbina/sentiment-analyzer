#!/usr/bin/env python3
"""Check sentiment database tables."""

import asyncio
import asyncpg

async def main():
    # Connect to sentiment database
    conn = await asyncpg.connect(
        host='154.53.166.231',
        port=5432,
        user='adminsentiment',
        password='wp2400!!!!',
        database='sentiment'
    )
    
    try:
        # Get all tables in public schema
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        print("Tables in public schema (sentiment database):")
        for row in tables:
            print(f"  - {row['table_name']}")
        
        # Check if ground_truth table exists
        ground_truth_exists = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'ground_truth'
            )
        """)
        print(f"\nground_truth table exists: {ground_truth_exists}")
        
        if ground_truth_exists:
            # Check row count
            count = await conn.fetchval("SELECT COUNT(*) FROM ground_truth")
            print(f"Rows in ground_truth: {count}")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

