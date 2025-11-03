"""Check if feeds are loaded."""
import requests
import time

time.sleep(5)
r = requests.get("http://localhost:8000/feeds", timeout=5)
result = r.json()
print(f"Feeds registered: {result['total']}")
for feed in result['feeds']:
    print(f"  - {feed['feed_id']}: {feed['name']}")

