#!/usr/bin/env python3
"""Check clustering schema and tables."""

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
            ORDER BY schema_name
        """)
        print("All Schemas:")
        for row in schemas:
            print(f"  - {row['schema_name']}")
        
        # Check if clustering schema exists
        clustering_schema = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.schemata 
                WHERE schema_name = 'clustering'
            )
        """)
        print(f"\nClustering schema exists: {clustering_schema}")
        
        if clustering_schema:
            # Get tables in clustering schema
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'clustering'
                ORDER BY table_name
            """)
            print("\nTables in clustering schema:")
            for row in tables:
                print(f"  - {row['table_name']}")
            
            # Check clustering.clusters table
            clusters_count = await conn.fetchval("""
                SELECT COUNT(*) FROM clustering.clusters
            """)
            print(f"\nRows in clustering.clusters: {clusters_count}")
            
            if clusters_count > 0:
                # Show sample cluster
                sample = await conn.fetchrow("""
                    SELECT group_id, article_count, similarity_avg, topic_label 
                    FROM clustering.clusters 
                    LIMIT 1
                """)
                print(f"\nSample cluster:")
                print(f"  group_id: {sample['group_id']}")
                print(f"  article_count: {sample['article_count']}")
                print(f"  similarity_avg: {sample['similarity_avg']}")
                print(f"  topic_label: {sample['topic_label']}")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

