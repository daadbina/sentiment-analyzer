"""Quick script to check semantic groups in PostgreSQL."""
import asyncio
import asyncpg


async def check_semantic_groups():
    """Check semantic groups count and details."""
    conn = await asyncpg.connect(
        host="154.53.166.231",
        port=5432,
        user="adminsentiment",
        password="wp2400!!!!",
        database="sentiment",
    )
    
    # Total count
    total = await conn.fetchval("SELECT COUNT(*) FROM semantic_groups;")
    print(f"\n=== SEMANTIC GROUPS SUMMARY ===")
    print(f"Total semantic groups: {total}")
    
    # Get sample groups
    rows = await conn.fetch("""
        SELECT 
            group_id, 
            topic_label, 
            article_count,
            similarity_avg,
            created_at
        FROM semantic_groups
        ORDER BY created_at DESC
        LIMIT 20;
    """)
    
    print(f"\n=== RECENT SEMANTIC GROUPS (Last 20) ===")
    for row in rows:
        print(f"  {row['group_id'][:8]}... | {row['topic_label'][:50]:50s} | Articles: {row['article_count']:3d} | Sim: {row['similarity_avg']:.3f} | {row['created_at']}")
    
    # Check sample GDELT events
    gdelt_sample = await conn.fetch("""
        SELECT
            event_id,
            event_type,
            countries,
            description,
            event_timestamp
        FROM event_labels
        WHERE source = 'gdelt'
        ORDER BY event_timestamp DESC
        LIMIT 5;
    """)

    print(f"\n=== SAMPLE GDELT EVENTS (Last 5) ===")
    for event in gdelt_sample:
        print(f"  {event['event_id'][:20]:20s} | {event['event_type'][:20]:20s} | {str(event['countries'])[:30]:30s} | {event['description'][:50]:50s}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(check_semantic_groups())

