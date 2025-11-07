#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect(host='154.53.166.231', user='adminsentiment', password='wp2400!!!!', database='sentiment')
cur = conn.cursor()

print("=" * 80)
print("GDELT LABELS - DETAILED ANALYSIS")
print("=" * 80)

cur.execute('''SELECT event_id, label_source, label_confidence, description, group_id 
FROM ground_truth 
WHERE label_source = 'gdelt' 
LIMIT 5''')

print('\nGDELT Labels (first 5):')
for event_id, source, conf, desc, gid in cur.fetchall():
    print(f'  Event: {event_id[:50]}')
    print(f'    Source: {source}, Confidence: {conf}, Group: {gid}')
    desc_str = desc[:60] if desc else 'N/A'
    print(f'    Desc: {desc_str}')
    print()

print("\n" + "=" * 80)
print("BINANCE LABELS - DETAILED ANALYSIS")
print("=" * 80)

cur.execute('''SELECT event_id, label_source, label_confidence, description, group_id 
FROM ground_truth 
WHERE label_source = 'binance' 
LIMIT 5''')

print('\nBinance Labels (first 5):')
for event_id, source, conf, desc, gid in cur.fetchall():
    print(f'  Event: {event_id[:50]}')
    print(f'    Source: {source}, Confidence: {conf}, Group: {gid}')
    desc_str = desc[:60] if desc else 'N/A'
    print(f'    Desc: {desc_str}')
    print()

cur.close()
conn.close()

