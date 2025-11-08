#!/usr/bin/env python
"""Inspect Feast registry file."""

import sqlite3
import json

registry_path = "C:\\feast\\registry"

print(f"Connecting to registry: {registry_path}")
conn = sqlite3.connect(registry_path)
cursor = conn.cursor()

# List all tables
print("\nTables in registry:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(f"  - {table[0]}")

# Check feature_views table
print("\nFeature views:")
try:
    cursor.execute("SELECT * FROM feature_views;")
    rows = cursor.fetchall()
    print(f"  Total: {len(rows)}")
    for row in rows:
        print(f"  - {row}")
except Exception as e:
    print(f"  Error: {e}")

# Check entities table
print("\nEntities:")
try:
    cursor.execute("SELECT * FROM entities;")
    rows = cursor.fetchall()
    print(f"  Total: {len(rows)}")
    for row in rows:
        print(f"  - {row}")
except Exception as e:
    print(f"  Error: {e}")

conn.close()

