#!/usr/bin/env python3
"""Check ground_truth table content."""

import asyncio
import asyncpg
from datetime import datetime, timedelta

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
        # Check total count
        total = await conn.fetchval('SELECT COUNT(*) FROM ground_truth')
        print(f"Total records in ground_truth: {total}")
        
        # Check null counts
        null_counts = await conn.fetch('''
            SELECT 
                COUNT(CASE WHEN event_id IS NULL THEN 1 END) as null_event_id,
                COUNT(CASE WHEN group_id IS NULL THEN 1 END) as null_group_id,
                COUNT(CASE WHEN label_realized IS NULL THEN 1 END) as null_label_realized,
                COUNT(CASE WHEN label_confidence IS NULL THEN 1 END) as null_label_confidence,
                COUNT(CASE WHEN created_at IS NULL THEN 1 END) as null_created_at
            FROM ground_truth
        ''')
        print(f"\nNull counts:\n{null_counts}")
        
        # Check sample records
        samples = await conn.fetch('''
            SELECT event_id, group_id, label_realized, label_confidence, created_at
            FROM ground_truth
            LIMIT 10
        ''')
        print(f"\nSample records:")
        for row in samples:
            print(f"  {row}")
        
        # Check label_realized distribution
        dist = await conn.fetch('''
            SELECT label_realized, COUNT(*) as count
            FROM ground_truth
            WHERE label_realized IS NOT NULL
            GROUP BY label_realized
        ''')
        print(f"\nLabel realized distribution:")
        for row in dist:
            print(f"  {row}")
        
        # Check records from last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent = await conn.fetchval(
            'SELECT COUNT(*) FROM ground_truth WHERE created_at >= $1',
            seven_days_ago
        )
        print(f"\nRecords from last 7 days: {recent}")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

