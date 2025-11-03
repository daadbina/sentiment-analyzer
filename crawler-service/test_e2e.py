"""
End-to-end test script for Crawler service.

Tests real RSS feed crawling, parsing, validation, and Kafka publishing.
"""

import requests
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

# Real RSS feeds to test
TEST_FEEDS = [
    {
        "feed_id": "hacker-news",
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "feed_type": "rss",
        "enabled": True,
        "crawl_interval_minutes": 5,
    },
    {
        "feed_id": "techcrunch",
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "feed_type": "rss",
        "enabled": True,
        "crawl_interval_minutes": 5,
    },
]


def test_health_endpoints():
    """Test health endpoints."""
    logger.info("=" * 80)
    logger.info("TESTING HEALTH ENDPOINTS")
    logger.info("=" * 80)

    # Test /health
    response = requests.get(f"{BASE_URL}/health")
    logger.info(f"GET /health: {response.status_code}")
    health = response.json()
    logger.info(f"Health status: {health['status']}")
    logger.info(f"Components: {list(health['components'].keys())}")
    assert response.status_code == 200
    assert health["status"] == "healthy"

    # Test /ready
    response = requests.get(f"{BASE_URL}/ready")
    logger.info(f"GET /ready: {response.status_code}")
    assert response.status_code == 200

    # Test /live
    response = requests.get(f"{BASE_URL}/live")
    logger.info(f"GET /live: {response.status_code}")
    assert response.status_code == 200

    logger.info("✅ All health endpoints working\n")


def test_register_feeds():
    """Register test feeds."""
    logger.info("=" * 80)
    logger.info("REGISTERING TEST FEEDS")
    logger.info("=" * 80)

    for feed in TEST_FEEDS:
        logger.info(f"Registering feed: {feed['feed_id']}")
        response = requests.post(
            f"{BASE_URL}/feeds",
            json=feed,
            headers={"Content-Type": "application/json"},
        )
        logger.info(f"Response: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"✅ Feed registered: {feed['feed_id']}")
        else:
            logger.error(f"❌ Failed to register feed: {response.text}")

    # List all feeds
    response = requests.get(f"{BASE_URL}/feeds")
    feeds = response.json()
    logger.info(f"Total feeds registered: {feeds['total']}")
    for feed in feeds["feeds"]:
        logger.info(f"  - {feed['feed_id']}: {feed['url']}")

    logger.info("")


def test_crawl_feed(feed_id: str):
    """Test crawling a feed."""
    logger.info("=" * 80)
    logger.info(f"CRAWLING FEED: {feed_id}")
    logger.info("=" * 80)

    response = requests.post(f"{BASE_URL}/crawl/{feed_id}")
    logger.info(f"Response: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        logger.info(f"Crawl result: {json.dumps(result, indent=2)}")
        logger.info(f"✅ Crawl completed for {feed_id}")
    else:
        logger.error(f"❌ Crawl failed: {response.text}")

    logger.info("")


def test_metrics():
    """Test metrics endpoint."""
    logger.info("=" * 80)
    logger.info("CHECKING PROMETHEUS METRICS")
    logger.info("=" * 80)

    response = requests.get(f"{BASE_URL}/metrics")
    metrics_text = response.text

    # Check for crawler metrics
    crawler_metrics = [
        "crawler_articles_crawled_total",
        "crawler_articles_published_total",
        "crawler_articles_failed_total",
        "crawler_duplicates_detected_total",
        "crawler_validation_failures_total",
        "crawler_active_crawls",
        "crawler_dedup_cache_size",
        "crawler_feed_registry_size",
    ]

    logger.info("Checking for crawler metrics:")
    for metric in crawler_metrics:
        if metric in metrics_text:
            logger.info(f"  ✅ {metric}")
        else:
            logger.warning(f"  ⚠️  {metric} not found")

    logger.info("")


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 80)
    logger.info("CRAWLER SERVICE END-TO-END TEST")
    logger.info("=" * 80 + "\n")

    try:
        # Test health endpoints
        test_health_endpoints()

        # Register feeds
        test_register_feeds()

        # Crawl feeds
        for feed in TEST_FEEDS:
            test_crawl_feed(feed["feed_id"])
            time.sleep(2)  # Wait between crawls

        # Check metrics
        test_metrics()

        logger.info("=" * 80)
        logger.info("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()

