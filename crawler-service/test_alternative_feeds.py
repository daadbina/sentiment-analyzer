#!/usr/bin/env python3
"""Test alternative news feeds for Reuters and ISNA."""

import requests
import feedparser

print("=" * 80)
print("TESTING ALTERNATIVE NEWS FEEDS")
print("=" * 80)

# Alternative feeds to test
feeds = {
    # Reuters alternatives
    'apnews': 'https://apnews.com/apf-services/feeds/rss.xml',
    'bbc_world': 'https://feeds.bbci.co.uk/news/world/rss.xml',
    'guardian': 'https://www.theguardian.com/world/rss',
    'nyt': 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    
    # ISNA alternatives (Persian news)
    'mehr_news': 'https://www.mehrnews.com/rss/all',
    'irna': 'https://en.irna.ir/rss',
    'khabar_online': 'https://www.khabaronline.ir/rss',
    'farsnews': 'https://www.farsnews.ir/rss',
}

results = {}

for name, url in feeds.items():
    print(f'\nTesting {name}')
    print(f'  URL: {url}')
    try:
        resp = requests.get(url, timeout=10, verify=False)
        print(f'  Status: {resp.status_code}')
        
        feed = feedparser.parse(resp.content)
        entries = len(feed.get('entries', []))
        print(f'  Entries: {entries}')
        
        if entries > 0:
            first = feed.entries[0]
            title = first.get('title', 'N/A')[:60]
            print(f'  First: {title}')
            results[name] = {'status': 'OK', 'entries': entries}
            print(f'  ✅ WORKING')
        else:
            results[name] = {'status': 'NO_ENTRIES', 'entries': 0}
            print(f'  ⚠️  No entries')
    except Exception as e:
        results[name] = {'status': 'ERROR', 'error': str(e)[:50]}
        print(f'  ❌ Error: {str(e)[:80]}')

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

working = {k: v for k, v in results.items() if v['status'] == 'OK'}
print(f'\nWorking feeds: {len(working)}/{len(results)}')
for name, info in working.items():
    print(f'  ✅ {name}: {info["entries"]} entries')

print(f'\nNon-working feeds:')
for name, info in results.items():
    if info['status'] != 'OK':
        print(f'  ❌ {name}: {info["status"]}')

