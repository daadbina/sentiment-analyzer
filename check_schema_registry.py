#!/usr/bin/env python
"""Check schema registry subjects."""

from confluent_kafka.schema_registry import SchemaRegistryClient

client = SchemaRegistryClient({"url": "http://154.53.166.231:8081"})

print("Registered subjects:")
subjects = client.get_subjects()
for subject in subjects:
    print(f"  {subject}")
    versions = client.get_versions(subject)
    print(f"    Versions: {versions}")
    for version in versions:
        schema = client.get_latest_version(subject)
        print(f"    Latest: ID={schema.schema_id}, Version={schema.version}")

