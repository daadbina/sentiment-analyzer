#!/usr/bin/env python3
"""Check ground_truth table data."""

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
        # Get ground_truth table schema
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'ground_truth'
            ORDER BY ordinal_position
        """)
        print("ground_truth table schema:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Check row count
        count = await conn.fetchval("SELECT COUNT(*) FROM ground_truth")
        print(f"\nTotal rows: {count}")
        
        # Check group_id distribution
        group_id_stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT group_id) as unique_groups,
                COUNT(CASE WHEN group_id IS NULL THEN 1 END) as null_groups
            FROM ground_truth
        """)
        print(f"\ngroup_id statistics:")
        print(f"  - Total rows: {group_id_stats['total']}")
        print(f"  - Unique group_ids: {group_id_stats['unique_groups']}")
        print(f"  - Null group_ids: {group_id_stats['null_groups']}")
        
        # Check label_realized distribution
        label_stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN label_realized IS NULL THEN 1 END) as null_labels,
                COUNT(CASE WHEN label_realized = true THEN 1 END) as true_labels,
                COUNT(CASE WHEN label_realized = false THEN 1 END) as false_labels
            FROM ground_truth
        """)
        print(f"\nlabel_realized statistics:")
        print(f"  - Total rows: {label_stats['total']}")
        print(f"  - Null labels: {label_stats['null_labels']}")
        print(f"  - True labels: {label_stats['true_labels']}")
        print(f"  - False labels: {label_stats['false_labels']}")
        
        # Show sample rows
        samples = await conn.fetch("""
            SELECT event_id, group_id, label_realized, label_confidence, created_at
            FROM ground_truth
            LIMIT 5
        """)
        print(f"\nSample rows:")
        for row in samples:
            print(f"  - event_id: {row['event_id']}, group_id: {row['group_id']}, label: {row['label_realized']}, confidence: {row['label_confidence']}")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

