"""
Initialize crawler feeds from Task.md specifications.

Registers all required news sources with proper RSS feed URLs.
"""

import asyncio
import logging
import sys
import json
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Feed configurations from Task.md
# Languages: Persian, Russian, Chinese, English
# Sources: CNN, BBC, Reuters, Xinhua, Tasnim, ISNA, RT, Aljazeera

FEEDS_CONFIG: List[Dict[str, Any]] = [
    # English sources
    {
        "feed_id": "cnn",
        "name": "CNN",
        "url": "http://rss.cnn.com/rss/edition.rss",
        "feed_type": "rss",
        "language": "en",
        "country": "US",
        "enabled": True,
        "crawl_interval_minutes": 30,
        "timeout_seconds": 15,
    },
    {
        "feed_id": "bbc",
        "name": "BBC News",
        "url": "http://feeds.bbc.co.uk/news/rss.xml",
        "feed_type": "rss",
        "language": "en",
        "country": "GB",
        "enabled": True,
        "crawl_interval_minutes": 30,
        "timeout_seconds": 15,
    },
    {
        "feed_id": "reuters",
        "name": "Reuters",
        "url": "http://feeds.reuters.com/reuters/topNews",
        "feed_type": "rss",
        "language": "en",
        "country": "GB",
        "enabled": True,
        "crawl_interval_minutes": 30,
        "timeout_seconds": 15,
    },
    {
        "feed_id": "aljazeera",
        "name": "Al Jazeera",
        "url": "http://www.aljazeera.com/xml/rss/all.xml",
        "feed_type": "rss",
        "language": "en",
        "country": "QA",
        "enabled": True,
        "crawl_interval_minutes": 30,
        "timeout_seconds": 15,
    },
    # Chinese sources
    {
        "feed_id": "xinhua",
        "name": "Xinhua News",
        "url": "http://www.xinhuanet.com/english/rss.xml",
        "feed_type": "rss",
        "language": "zh",
        "country": "CN",
        "enabled": True,
        "crawl_interval_minutes": 30,
        "timeout_seconds": 15,
    },
    # Russian sources
    {
        "feed_id": "rt",
        "name": "RT News",
        "url": "http://rt.com/rss/",
        "feed_type": "rss",
        "language": "ru",
        "country": "RU",
        "enabled": True,
        "crawl_interval_minutes": 30,
        "timeout_seconds": 15,
    },
    # Persian sources
    {
        "feed_id": "tasnim",
        "name": "Tasnim News Agency",
        "url": "http://www.tasnimnews.com/rss/feed/0/en",
        "feed_type": "rss",
        "language": "fa",
        "country": "IR",
        "enabled": True,
        "crawl_interval_minutes": 30,
        "timeout_seconds": 15,
    },
    {
        "feed_id": "isna",
        "name": "ISNA News Agency",
        "url": "http://isna.ir/en/rss",
        "feed_type": "rss",
        "language": "fa",
        "country": "IR",
        "enabled": True,
        "crawl_interval_minutes": 30,
        "timeout_seconds": 15,
    },
]


async def register_feeds(base_url: str = "http://localhost:8000") -> None:
    """
    Register all feeds with the crawler service.

    Args:
        base_url: Base URL of crawler service.
    """
    import aiohttp

    async with aiohttp.ClientSession() as session:
        for feed_config in FEEDS_CONFIG:
            try:
                logger.info(f"Registering feed: {feed_config['feed_id']} ({feed_config['name']})")
                
                async with session.post(
                    f"{base_url}/feeds",
                    json=feed_config,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✓ Successfully registered: {feed_config['feed_id']}")
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"✗ Failed to register {feed_config['feed_id']}: "
                            f"HTTP {response.status} - {error_text}"
                        )
            except Exception as e:
                logger.error(f"✗ Error registering {feed_config['feed_id']}: {str(e)}")

    logger.info("Feed registration complete")


async def list_feeds(base_url: str = "http://localhost:8000") -> None:
    """
    List all registered feeds.

    Args:
        base_url: Base URL of crawler service.
    """
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/feeds",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Total feeds registered: {result['total']}")
                    for feed in result['feeds']:
                        logger.info(
                            f"  - {feed['feed_id']}: {feed['name']} "
                            f"({feed['language']}/{feed['country']}) "
                            f"[{'enabled' if feed['enabled'] else 'disabled'}]"
                        )
                else:
                    logger.error(f"Failed to list feeds: HTTP {response.status}")
    except Exception as e:
        logger.error(f"Error listing feeds: {str(e)}")


async def main() -> None:
    """Main entry point."""
    logger.info("Starting feed initialization...")
    logger.info(f"Registering {len(FEEDS_CONFIG)} feeds from Task.md specifications")
    
    await register_feeds()
    await asyncio.sleep(1)
    await list_feeds()
    
    logger.info("Feed initialization complete!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

