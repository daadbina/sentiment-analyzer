#!/usr/bin/env python
"""Test Avro serialization with confluent_kafka."""

import json
from confluent_kafka import Producer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

# Schema
SCHEMA = {
    "type": "record",
    "name": "TestMessage",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "value", "type": "int"}
    ]
}

# Initialize
schema_registry_client = SchemaRegistryClient({"url": "http://154.53.166.231:8081"})
avro_serializer = AvroSerializer(schema_registry_client, json.dumps(SCHEMA))

producer = Producer({
    "bootstrap.servers": "154.53.166.231:9092",
    "acks": "all",
})

# Test message
test_msg = {"id": "test-1", "value": 42}

# Serialize
ctx = SerializationContext("test_topic", MessageField.VALUE)
try:
    serialized = avro_serializer(test_msg, ctx)
    print(f"Serialized successfully!")
    print(f"First 10 bytes: {serialized[:10]}")
    print(f"Hex: {serialized[:10].hex()}")
    
    # Check for magic byte
    if serialized[0] == 0x00:
        print("✓ Magic byte (0x00) found!")
    else:
        print(f"✗ Magic byte NOT found! First byte: {hex(serialized[0])}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

