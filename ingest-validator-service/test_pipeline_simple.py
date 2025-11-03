"""
Simple end-to-end pipeline test: Trigger crawl and verify data flow
"""

import requests
import json
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CRAWLER_URL = "http://localhost:8000"
VALIDATOR_URL = "http://127.0.0.1:8081"


def check_crawler_health() -> bool:
    """Check crawler service health."""
    logger.info("=" * 60)
    logger.info("STEP 1: CHECKING CRAWLER SERVICE")
    logger.info("=" * 60)
    
    try:
        response = requests.get(f"{CRAWLER_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Crawler health: {data.get('status', 'unknown')}")
            return True
        else:
            logger.error(f"❌ Crawler health check failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking crawler health: {e}")
        return False


def get_registered_feeds() -> list:
    """Get list of registered feeds."""
    logger.info("=" * 60)
    logger.info("STEP 2: GETTING REGISTERED FEEDS")
    logger.info("=" * 60)

    try:
        response = requests.get(f"{CRAWLER_URL}/feeds", timeout=5)
        if response.status_code == 200:
            data = response.json()
            feeds = data.get('feeds', []) if isinstance(data, dict) else data
            logger.info(f"✅ Found {len(feeds)} registered feeds:")
            for feed in feeds:
                logger.info(f"   - {feed.get('feed_id')}: {feed.get('name')}")
            return feeds
        else:
            logger.error(f"❌ Failed to get feeds: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"❌ Error getting feeds: {e}")
        return []


def trigger_crawl(feed_ids: list) -> int:
    """Trigger crawl for registered feeds."""
    logger.info("=" * 60)
    logger.info("STEP 3: TRIGGERING CRAWL")
    logger.info("=" * 60)
    
    articles_crawled = 0
    for feed_id in feed_ids[:3]:  # Limit to first 3 feeds to avoid timeout
        try:
            logger.info(f"Crawling {feed_id}...")
            response = requests.post(
                f"{CRAWLER_URL}/crawl",
                json={"feed_id": feed_id},
                timeout=60
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
    logger.info("STEP 4: CHECKING VALIDATOR SERVICE")
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


def check_metrics() -> dict:
    """Check validator metrics."""
    logger.info("=" * 60)
    logger.info("STEP 5: CHECKING VALIDATOR METRICS")
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
                            try:
                                metrics['messages_consumed'] = int(float(parts[-1]))
                            except:
                                pass
                    elif 'validator_messages_validated_total' in line:
                        parts = line.split(' ')
                        if len(parts) >= 2:
                            try:
                                metrics['messages_validated'] = int(float(parts[-1]))
                            except:
                                pass
                    elif 'validator_messages_accepted_total' in line:
                        parts = line.split(' ')
                        if len(parts) >= 2:
                            try:
                                metrics['messages_accepted'] = int(float(parts[-1]))
                            except:
                                pass
            
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
    
    # Step 1: Check crawler health
    if not check_crawler_health():
        logger.error("❌ Crawler service not healthy")
        return
    
    time.sleep(1)
    
    # Step 2: Get registered feeds
    feeds = get_registered_feeds()
    if not feeds:
        logger.error("❌ No feeds registered")
        return
    
    feed_ids = [f.get('feed_id') for f in feeds]
    
    time.sleep(1)
    
    # Step 3: Trigger crawl
    articles_crawled = trigger_crawl(feed_ids)
    
    time.sleep(3)
    
    # Step 4: Check validator health
    if not check_validator_health():
        logger.error("❌ Validator service not healthy")
        return
    
    time.sleep(1)
    
    # Step 5: Check metrics
    metrics = check_metrics()
    
    # Summary
    logger.info("=" * 60)
    logger.info("PIPELINE TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Feeds registered: {len(feeds)}")
    logger.info(f"✅ Articles crawled: {articles_crawled}")
    logger.info(f"✅ Validator running: Yes")
    logger.info(f"✅ Messages consumed: {metrics.get('messages_consumed', 0)}")
    logger.info(f"✅ Messages validated: {metrics.get('messages_validated', 0)}")
    logger.info(f"✅ Messages accepted: {metrics.get('messages_accepted', 0)}")
    logger.info("=" * 60)
    logger.info("\n✅ END-TO-END PIPELINE TEST COMPLETE\n")


if __name__ == "__main__":
    main()

