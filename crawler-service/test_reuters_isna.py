#!/usr/bin/env python3
"""Test Reuters with GoogleNews and ISNA feed alternatives."""

import requests
import feedparser
from GoogleNews import GoogleNews

print("=" * 80)
print("TESTING ISNA FEED ALTERNATIVES")
print("=" * 80)

isna_urls = {
    'isna_no_en': 'https://www.isna.ir/rss',
    'isna_en': 'https://en.isna.ir/rss',
}

for name, url in isna_urls.items():
    print(f'\nTesting {name}: {url}')
    try:
        resp = requests.get(url, timeout=10, verify=False)
        print(f'  Status: {resp.status_code}')
        feed = feedparser.parse(resp.content)
        entries = len(feed.get('entries', []))
        print(f'  Entries: {entries}')
        if entries > 0:
            first = feed.entries[0]
            print(f'  First title: {first.get("title", "N/A")[:60]}')
            print(f'  First link: {first.get("link", "N/A")[:60]}')
    except Exception as e:
        print(f'  Error: {str(e)[:100]}')

print("\n" + "=" * 80)
print("TESTING REUTERS WITH GOOGLENEWS")
print("=" * 80)

try:
    gn = GoogleNews(lang='en')
    gn.search('reuters')
    results = gn.results()
    print(f'\nFound {len(results)} articles from GoogleNews search for "reuters"')
    
    # Filter by Reuters source
    reuters_articles = [r for r in results if 'reuters' in r.get('source', '').lower()]
    print(f'Reuters articles: {len(reuters_articles)}')
    
    if reuters_articles:
        print('\nFirst 3 Reuters articles:')
        for i, article in enumerate(reuters_articles[:3], 1):
            print(f'\n  {i}. Title: {article.get("title", "N/A")[:70]}')
            print(f'     Source: {article.get("source", "N/A")}')
            print(f'     Link: {article.get("link", "N/A")[:70]}')
except Exception as e:
    print(f'Error with GoogleNews: {str(e)}')

print("\n" + "=" * 80)
print("TESTING REUTERS DIRECT FEEDS")
print("=" * 80)

reuters_urls = {
    'reuters_world': 'http://feeds.reuters.com/reuters/worldNews',
    'reuters_top': 'http://feeds.reuters.com/reuters/topNews',
}

for name, url in reuters_urls.items():
    print(f'\nTesting {name}: {url}')
    try:
        resp = requests.get(url, timeout=10, verify=False)
        print(f'  Status: {resp.status_code}')
        feed = feedparser.parse(resp.content)
        entries = len(feed.get('entries', []))
        print(f'  Entries: {entries}')
        if entries > 0:
            first = feed.entries[0]
            print(f'  First title: {first.get("title", "N/A")[:60]}')
    except Exception as e:
        print(f'  Error: {str(e)[:100]}')

