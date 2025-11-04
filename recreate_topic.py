#!/usr/bin/env python
"""Recreate semantic_groups topic."""

import time
from confluent_kafka.admin import AdminClient, NewTopic

time.sleep(3)

admin = AdminClient({'bootstrap.servers': '154.53.166.231:9092'})

# Create the topic
print('Creating semantic_groups topic...')
try:
    fs = admin.create_topics([NewTopic('semantic_groups', num_partitions=3, replication_factor=1)])
    for topic, f in fs.items():
        try:
            f.result()
            print(f'Topic {topic} created')
        except Exception as e:
            print(f'Error creating {topic}: {e}')
except Exception as e:
    print(f'Error: {e}')

