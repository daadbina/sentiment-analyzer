#!/usr/bin/env python3
"""Check metadata in ground_truth table."""

import asyncpg
import asyncio
import json

async def check_metadata():
    conn = await asyncpg.connect('postgresql://adminsentiment:wp2400!!!!@154.53.166.231:5432/sentiment')
    
    # Get recent ground_truth records
    records = await conn.fetch('SELECT * FROM ground_truth ORDER BY created_at DESC LIMIT 5')
    
    print(f"Found {len(records)} records\n")
    
    for i, record in enumerate(records, 1):
        print(f"Record {i}:")
        print(f"  Event ID: {record['event_id']}")
        print(f"  Group ID: {record['group_id']}")
        print(f"  Label Confidence: {record['label_confidence']}")
        print(f"  Source Confidence: {record['source_confidence']}")
        print(f"  Label Source: {record['label_source']}")
        print(f"  Label Source License: {record['label_source_license']}")
        print(f"  Verified At: {record['verified_at']}")
        print(f"  Description: {record['description'][:50] if record['description'] else 'None'}...")
        print()
    
    await conn.close()

asyncio.run(check_metadata())

