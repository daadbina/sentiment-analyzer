#!/usr/bin/env python3
"""Refresh Redis and Qdrant caches."""

import redis
from qdrant_client import QdrantClient

# Flush Redis
print("Flushing Redis...")
r = redis.Redis(host='localhost', port=6379, db=0)
r.flushall()
print("✓ Redis flushed")

# Clear Qdrant collections
print("Clearing Qdrant collections...")
client = QdrantClient('localhost', port=6333)
collections = client.get_collections()
for collection in collections.collections:
    try:
        client.delete_collection(collection.name)
        print(f"✓ Deleted collection: {collection.name}")
    except Exception as e:
        print(f"✗ Failed to delete {collection.name}: {e}")

print("✓ Qdrant cleared")
print("\nCache refresh complete!")

