#!/usr/bin/env python
"""Check Kafka topic directly."""

from confluent_kafka import Consumer, KafkaError
import time

consumer = Consumer({
    "bootstrap.servers": "154.53.166.231:9092",
    "group.id": "debug-group-raw",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
})

consumer.subscribe(["semantic_groups"])

print("Waiting for messages...")
time.sleep(2)

print("Reading messages from semantic_groups topic...")
count = 0
for i in range(20):
    msg = consumer.poll(timeout=1.0)
    
    if msg is None:
        print(f"No message (timeout)")
        continue
    
    if msg.error():
        if msg.error().code() == KafkaError._PARTITION_EOF:
            print(f"End of partition")
            break
        else:
            print(f"Error: {msg.error()}")
            break
    
    # Get raw bytes
    value_bytes = msg.value()
    print(f"\nMessage {count}:")
    print(f"  Partition: {msg.partition()}, Offset: {msg.offset()}")
    print(f"  Length: {len(value_bytes)} bytes")
    print(f"  First 30 bytes (hex): {value_bytes[:30].hex()}")
    
    # Check for magic byte
    if value_bytes[0] == 0x00:
        print(f"  ✓ Avro format (magic byte 0x00)")
        # Extract schema ID (bytes 1-4)
        schema_id = int.from_bytes(value_bytes[1:5], byteorder='big')
        print(f"  Schema ID: {schema_id}")
    else:
        print(f"  ✗ NOT Avro format (first byte: {hex(value_bytes[0])})")
    
    count += 1

print(f"\nTotal messages read: {count}")
consumer.close()

