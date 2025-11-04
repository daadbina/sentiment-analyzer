#!/usr/bin/env python3
"""
Reset Kafka topic and consumer group using Python Kafka client.
"""

from confluent_kafka.admin import AdminClient, NewTopic, ConfigResource, ConfigSource
from confluent_kafka import Consumer
import time

KAFKA_BROKER = "154.53.166.231:9092"
TOPIC = "semantic_groups"
CONSUMER_GROUP = "feature-engineering-group"

def reset_kafka():
    """Reset Kafka topic and consumer group."""
    
    admin_client = AdminClient({"bootstrap.servers": KAFKA_BROKER})
    
    print("🔄 Resetting Kafka topic and consumer group...")
    
    # Step 1: Delete topic
    print(f"\n1️⃣  Deleting topic '{TOPIC}'...")
    try:
        fs = admin_client.delete_topics([TOPIC], operation_timeout=30)
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print(f"   ✅ Topic '{topic}' deleted")
            except Exception as e:
                print(f"   ⚠️  Error deleting topic: {e}")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
    
    # Wait for deletion
    print("   ⏳ Waiting 3 seconds for deletion to propagate...")
    time.sleep(3)
    
    # Step 2: Recreate topic
    print(f"\n2️⃣  Recreating topic '{TOPIC}'...")
    try:
        new_topic = NewTopic(TOPIC, num_partitions=3, replication_factor=1)
        fs = admin_client.create_topics([new_topic], operation_timeout=30)
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print(f"   ✅ Topic '{topic}' created")
            except Exception as e:
                print(f"   ⚠️  Error creating topic: {e}")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
    
    # Wait for creation
    print("   ⏳ Waiting 2 seconds for creation to propagate...")
    time.sleep(2)
    
    # Step 3: Delete consumer group
    print(f"\n3️⃣  Deleting consumer group '{CONSUMER_GROUP}'...")
    try:
        # Create a consumer to delete the group
        consumer = Consumer({
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": CONSUMER_GROUP,
            "auto.offset.reset": "earliest"
        })
        consumer.close()
        
        # Now delete the group
        fs = admin_client.delete_consumer_groups([CONSUMER_GROUP], operation_timeout=30)
        for group, f in fs.items():
            try:
                f.result()
                print(f"   ✅ Consumer group '{group}' deleted")
            except Exception as e:
                print(f"   ⚠️  Error deleting group: {e}")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
    
    print("\n" + "="*60)
    print("✅ Kafka reset complete!")
    print("="*60)

if __name__ == "__main__":
    reset_kafka()

