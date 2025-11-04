#!/usr/bin/env python3
"""
Reset Kafka topic and consumer group for feature-engineering-service.
This script:
1. Deletes the semantic_groups topic
2. Recreates it empty
3. Deletes the consumer group
"""

import subprocess
import time
import sys

KAFKA_BROKER = "154.53.166.231:9092"
TOPIC = "semantic_groups"
CONSUMER_GROUP = "feature-engineering-group"

def run_command(cmd, description):
    """Run a shell command and report results."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        if result.returncode != 0:
            print(f"⚠️  Command returned code {result.returncode}")
        else:
            print("✅ Command succeeded")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔄 Resetting Kafka topic and consumer group...")
    
    # Step 1: Delete topic
    cmd = f'kafka-topics --bootstrap-server {KAFKA_BROKER} --delete --topic {TOPIC}'
    run_command(cmd, f"Delete topic {TOPIC}")
    
    # Wait a bit
    print("\n⏳ Waiting 3 seconds...")
    time.sleep(3)
    
    # Step 2: Recreate topic
    cmd = f'kafka-topics --bootstrap-server {KAFKA_BROKER} --create --topic {TOPIC} --partitions 3 --replication-factor 1'
    run_command(cmd, f"Recreate topic {TOPIC}")
    
    # Wait a bit
    print("\n⏳ Waiting 2 seconds...")
    time.sleep(2)
    
    # Step 3: Delete consumer group
    cmd = f'kafka-consumer-groups --bootstrap-server {KAFKA_BROKER} --delete --group {CONSUMER_GROUP}'
    run_command(cmd, f"Delete consumer group {CONSUMER_GROUP}")
    
    print("\n" + "="*60)
    print("✅ Kafka reset complete!")
    print("="*60)

if __name__ == "__main__":
    main()

