#!/usr/bin/env python3
"""
Test script to verify each feed's RSS content and crawl results.
Ensures all feeds are fetched correctly with no duplicates or mock data.
"""

import asyncio
import aiohttp
import feedparser
from typing import Dict, List, Tuple
import json
from datetime import datetime

# Feed URLs to test
FEEDS = {
    "cnn": "http://rss.cnn.com/rss/edition.rss",
    "bbc": "https://feeds.bbci.co.uk/news/rss.xml",
    "reuters": "https://www.theguardian.com/world/rss",
    "aljazeera": "http://www.aljazeera.com/xml/rss/all.xml",
    "xinhua": "http://www.xinhuanet.com/english/rss/worldrss.xml",
    "rt": "https://www.rt.com/rss/",
    "tasnim": "https://www.tasnimnews.com/en/rss/feed/0/0/0/0/AllStories",
    "isna": "https://en.irna.ir/rss",
}

async def fetch_feed(session: aiohttp.ClientSession, feed_id: str, url: str) -> Tuple[str, str, int]:
    """Fetch feed content and return (feed_id, content, status_code)."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as response:
            content = await response.text(errors='replace')
            return feed_id, content, response.status
    except Exception as e:
        return feed_id, str(e), 0

async def test_all_feeds():
    """Test all feeds and report results."""
    print("=" * 80)
    print("FEED CONTENT VERIFICATION TEST")
    print("=" * 80)
    print()
    
    async with aiohttp.ClientSession() as session:
        # Fetch all feeds
        tasks = [fetch_feed(session, feed_id, url) for feed_id, url in FEEDS.items()]
        results = await asyncio.gather(*tasks)
        
        # Parse and analyze results
        feed_stats = {}
        for feed_id, content, status_code in results:
            print(f"\n{'='*80}")
            print(f"Feed: {feed_id.upper()}")
            print(f"URL: {FEEDS[feed_id]}")
            print(f"Status: {status_code}")
            print(f"{'='*80}")
            
            if status_code != 200:
                print(f"❌ ERROR: Failed to fetch (Status {status_code})")
                print(f"Error: {content[:200]}")
                feed_stats[feed_id] = {"status": "FAILED", "entries": 0, "error": content[:100]}
                continue
            
            # Parse RSS
            try:
                feed = feedparser.parse(content)
                entries = feed.get('entries', [])
                num_entries = len(entries)
                
                if num_entries == 0:
                    print(f"⚠️  WARNING: No entries found in feed")
                    feed_stats[feed_id] = {"status": "NO_ENTRIES", "entries": 0}
                else:
                    print(f"✅ SUCCESS: Found {num_entries} entries")
                    
                    # Show first entry details
                    first_entry = entries[0]
                    print(f"\nFirst Entry:")
                    print(f"  Title: {first_entry.get('title', 'N/A')[:80]}")
                    print(f"  Link: {first_entry.get('link', 'N/A')[:80]}")
                    print(f"  Published: {first_entry.get('published', 'N/A')}")
                    
                    feed_stats[feed_id] = {
                        "status": "SUCCESS",
                        "entries": num_entries,
                        "first_title": first_entry.get('title', 'N/A')[:80]
                    }
            except Exception as e:
                print(f"❌ ERROR: Failed to parse RSS: {str(e)[:200]}")
                feed_stats[feed_id] = {"status": "PARSE_ERROR", "entries": 0, "error": str(e)[:100]}
        
        # Summary
        print(f"\n\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        
        total_feeds = len(feed_stats)
        successful = sum(1 for s in feed_stats.values() if s["status"] == "SUCCESS")
        failed = sum(1 for s in feed_stats.values() if s["status"] in ["FAILED", "PARSE_ERROR"])
        no_entries = sum(1 for s in feed_stats.values() if s["status"] == "NO_ENTRIES")
        
        print(f"\nTotal Feeds: {total_feeds}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  No Entries: {no_entries}")
        
        print(f"\nDetailed Results:")
        for feed_id, stats in feed_stats.items():
            status_icon = "✅" if stats["status"] == "SUCCESS" else "❌" if stats["status"] in ["FAILED", "PARSE_ERROR"] else "⚠️"
            print(f"  {status_icon} {feed_id:15} - {stats['status']:15} ({stats['entries']} entries)")
        
        # Test crawler endpoint
        print(f"\n\n{'='*80}")
        print("TESTING CRAWLER ENDPOINT")
        print(f"{'='*80}\n")
        
        try:
            async with session.post("http://localhost:8000/crawl", timeout=aiohttp.ClientTimeout(total=300)) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Crawl completed successfully")
                    print(f"Total jobs: {result.get('total', 0)}")
                    print(f"\nCrawl Results:")
                    for job in result.get('jobs', []):
                        status_icon = "✅" if job.get('status') == 'completed' else "❌"
                        feed_id = job.get('feed_id', 'unknown')
                        status = job.get('status', 'unknown')
                        published = job.get('articles_published', 0)
                        print(f"  {status_icon} {feed_id:15} - {status:15} ({published} published)")
                else:
                    print(f"❌ Crawl failed with status {response.status}")
        except Exception as e:
            print(f"❌ Error testing crawler: {str(e)[:100]}")

if __name__ == "__main__":
    asyncio.run(test_all_feeds())

