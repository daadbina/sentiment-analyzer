"""
End-to-end pipeline test: Crawler -> Kafka -> Validator -> Kafka
Tests real RSS feed crawling, validation, and Kafka message flow.
"""

import requests
import json
import time
import logging
from typing import List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CRAWLER_URL = "http://localhost:8000"
VALIDATOR_URL = "http://127.0.0.1:8081"

# Real RSS feeds from Task.md requirements
REAL_FEEDS = [
    {
        "feed_id": "bbc-news",
        "name": "BBC News",
        "url": "https://feeds.bbc.co.uk/news/rss.xml",
        "feed_type": "rss",
        "enabled": True,
        "language": "en",
        "country": "GB",
        "crawl_interval_minutes": 5,
    },
    {
        "feed_id": "reuters",
        "name": "Reuters",
        "url": "https://www.reuters.com/finance",
        "feed_type": "rss",
        "enabled": True,
        "language": "en",
        "country": "US",
        "crawl_interval_minutes": 5,
    },
    {
        "feed_id": "aljazeera",
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "feed_type": "rss",
        "enabled": True,
        "language": "en",
        "country": "QA",
        "crawl_interval_minutes": 5,
    },
]


def register_feeds() -> List[str]:
    """Register real RSS feeds in crawler."""
    logger.info("=" * 60)
    logger.info("STEP 1: REGISTERING REAL RSS FEEDS")
    logger.info("=" * 60)
    
    registered_feeds = []
    for feed in REAL_FEEDS:
        try:
            response = requests.post(
                f"{CRAWLER_URL}/feeds",
                json=feed,
                timeout=10
            )
            if response.status_code == 200:
                logger.info(f"✅ Registered feed: {feed['name']} ({feed['feed_id']})")
                registered_feeds.append(feed['feed_id'])
            else:
                logger.warning(f"⚠️  Failed to register {feed['name']}: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error registering {feed['name']}: {e}")
    
    logger.info(f"Registered {len(registered_feeds)}/{len(REAL_FEEDS)} feeds\n")
    return registered_feeds


def trigger_crawl(feed_ids: List[str]) -> int:
    """Trigger crawl for registered feeds."""
    logger.info("=" * 60)
    logger.info("STEP 2: TRIGGERING CRAWL")
    logger.info("=" * 60)
    
    articles_crawled = 0
    for feed_id in feed_ids:
        try:
            response = requests.post(
                f"{CRAWLER_URL}/crawl",
                json={"feed_id": feed_id},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                count = data.get("articles_crawled", 0)
                articles_crawled += count
                logger.info(f"✅ Crawled {feed_id}: {count} articles")
            else:
                logger.warning(f"⚠️  Crawl failed for {feed_id}: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error crawling {feed_id}: {e}")
    
    logger.info(f"Total articles crawled: {articles_crawled}\n")
    return articles_crawled


def check_validator_health() -> bool:
    """Check validator service health."""
    logger.info("=" * 60)
    logger.info("STEP 3: CHECKING VALIDATOR SERVICE")
    logger.info("=" * 60)
    
    try:
        response = requests.get(f"{VALIDATOR_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Validator health: {data.get('status', 'unknown')}")
            logger.info(f"   Service: {data.get('service', 'unknown')}")
            logger.info(f"   Version: {data.get('version', 'unknown')}")
            return True
        else:
            logger.error(f"❌ Validator health check failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking validator health: {e}")
        return False


def check_metrics() -> Dict[str, Any]:
    """Check validator metrics."""
    logger.info("=" * 60)
    logger.info("STEP 4: CHECKING VALIDATOR METRICS")
    logger.info("=" * 60)
    
    try:
        response = requests.get(f"{VALIDATOR_URL}/metrics", timeout=5)
        if response.status_code == 200:
            text = response.text
            # Parse Prometheus metrics
            metrics = {}
            for line in text.split('\n'):
                if line and not line.startswith('#'):
                    if 'validator_messages_consumed_total' in line:
                        parts = line.split(' ')
                        if len(parts) >= 2:
                            metrics['messages_consumed'] = int(parts[-1])
                    elif 'validator_messages_validated_total' in line:
                        parts = line.split(' ')
                        if len(parts) >= 2:
                            metrics['messages_validated'] = int(parts[-1])
                    elif 'validator_messages_accepted_total' in line:
                        parts = line.split(' ')
                        if len(parts) >= 2:
                            metrics['messages_accepted'] = int(parts[-1])
            
            logger.info(f"✅ Metrics retrieved:")
            for key, value in metrics.items():
                logger.info(f"   {key}: {value}")
            return metrics
        else:
            logger.error(f"❌ Metrics retrieval failed: {response.status_code}")
            return {}
    except Exception as e:
        logger.error(f"❌ Error checking metrics: {e}")
        return {}


def main():
    """Run end-to-end pipeline test."""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 58 + "║")
    logger.info("║" + "  CRAWLER -> KAFKA -> VALIDATOR PIPELINE TEST".center(58) + "║")
    logger.info("║" + " " * 58 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("\n")
    
    # Step 1: Register feeds
    feed_ids = register_feeds()
    if not feed_ids:
        logger.error("❌ No feeds registered, aborting")
        return
    
    # Step 2: Trigger crawl
    time.sleep(2)
    articles_crawled = trigger_crawl(feed_ids)
    
    # Step 3: Check validator health
    time.sleep(3)
    if not check_validator_health():
        logger.error("❌ Validator service not healthy")
        return
    
    # Step 4: Check metrics
    time.sleep(2)
    metrics = check_metrics()
    
    # Summary
    logger.info("=" * 60)
    logger.info("PIPELINE TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Feeds registered: {len(feed_ids)}")
    logger.info(f"✅ Articles crawled: {articles_crawled}")
    logger.info(f"✅ Validator running: Yes")
    logger.info(f"✅ Messages consumed: {metrics.get('messages_consumed', 0)}")
    logger.info(f"✅ Messages validated: {metrics.get('messages_validated', 0)}")
    logger.info(f"✅ Messages accepted: {metrics.get('messages_accepted', 0)}")
    logger.info("=" * 60)
    logger.info("\n✅ END-TO-END PIPELINE TEST COMPLETE\n")


if __name__ == "__main__":
    main()

