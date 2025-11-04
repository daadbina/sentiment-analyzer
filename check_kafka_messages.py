#!/usr/bin/env python
"""Check messages in Kafka topic."""

from confluent_kafka import Consumer, KafkaError

consumer = Consumer({
    "bootstrap.servers": "154.53.166.231:9092",
    "group.id": "debug-group",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
})

consumer.subscribe(["semantic_groups"])

print("Reading messages from semantic_groups topic...")
count = 0
for i in range(20):
    msg = consumer.poll(timeout=1.0)
    
    if msg is None:
        print(f"No more messages (timeout)")
        break
    
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
    print(f"  First 20 bytes (hex): {value_bytes[:20].hex()}")
    print(f"  First 20 bytes (repr): {repr(value_bytes[:20])}")
    
    # Check for magic byte
    if value_bytes[0] == 0x00:
        print(f"  ✓ Avro format (magic byte 0x00)")
    else:
        print(f"  ✗ NOT Avro format (first byte: {hex(value_bytes[0])})")
        # Try to decode as JSON
        try:
            import json
            data = json.loads(value_bytes.decode('utf-8'))
            print(f"  ✓ JSON format: {list(data.keys())[:5]}")
        except:
            print(f"  ? Unknown format")
    
    count += 1

print(f"\nTotal messages read: {count}")
consumer.close()

