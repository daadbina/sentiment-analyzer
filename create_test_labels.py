#!/usr/bin/env python3
"""Create test labels in ground_truth table for trainer testing."""

import asyncio
import asyncpg
from datetime import datetime, timedelta
import random

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
        # First, create the ground_truth table if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ground_truth (
                id SERIAL PRIMARY KEY,
                event_id VARCHAR(255) NOT NULL,
                group_id VARCHAR(255),
                description TEXT,
                domain VARCHAR(50),
                time_window VARCHAR(255),
                realization_metric VARCHAR(255),
                threshold FLOAT,
                verified_at TIMESTAMP,
                label_realized BOOLEAN,
                label_confidence FLOAT,
                source_confidence FLOAT,
                label_source VARCHAR(50),
                label_source_license VARCHAR(255),
                label_source_url TEXT,
                last_license_check TIMESTAMP,
                last_updated TIMESTAMP,
                trace_id VARCHAR(255),
                schema_version VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_id, label_source)
            )
        """)
        print("✓ ground_truth table created/verified")
        
        # Get semantic groups from semantic_groups table
        groups = await conn.fetch("""
            SELECT id FROM semantic_groups LIMIT 50
        """)
        print(f"✓ Found {len(groups)} semantic groups")
        
        if not groups:
            print("✗ No semantic groups found. Run clustering first.")
            return
        
        # Create test labels
        labels = []
        for i, group in enumerate(groups):
            group_id = group['id']
            event_id = f"test_event_{i}_{datetime.utcnow().timestamp()}"
            label_realized = random.choice([True, False])
            label_confidence = random.uniform(0.7, 0.99)
            
            labels.append((
                event_id,
                group_id,
                f"Test event {i}",
                "test",
                "2025-11-01T00:00:00Z/2025-11-08T23:59:59Z",
                "sentiment_change",
                0.5,
                datetime.utcnow(),
                label_realized,
                label_confidence,
                label_confidence,
                "test_source",
                "CC-BY-4.0",
                "https://test.example.com",
                datetime.utcnow(),
                datetime.utcnow(),
                f"trace_{i}",
                "1.0"
            ))
        
        # Insert labels
        async with conn.transaction():
            await conn.executemany("""
                INSERT INTO ground_truth (
                    event_id, group_id, description, domain, time_window,
                    realization_metric, threshold, verified_at, label_realized,
                    label_confidence, source_confidence, label_source,
                    label_source_license, label_source_url, last_license_check,
                    last_updated, trace_id, schema_version
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                )
                ON CONFLICT (event_id, label_source) DO NOTHING
            """, labels)
        
        print(f"✓ Inserted {len(labels)} test labels")
        
        # Verify
        count = await conn.fetchval("SELECT COUNT(*) FROM ground_truth")
        print(f"✓ Total labels in ground_truth: {count}")
        
        # Check distribution
        dist = await conn.fetch("""
            SELECT label_realized, COUNT(*) as count
            FROM ground_truth
            WHERE label_realized IS NOT NULL
            GROUP BY label_realized
        """)
        print(f"✓ Label distribution:")
        for row in dist:
            print(f"    {row['label_realized']}: {row['count']}")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

