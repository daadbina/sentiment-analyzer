"""
Test crawling from all registered feeds.

Tests network connectivity and data retrieval from each source.
"""

import asyncio
import logging
import sys
import json
from typing import Dict, Any

import aiohttp

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def crawl_feed(session: aiohttp.ClientSession, feed_id: str, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Crawl a single feed.

    Args:
        session: aiohttp session.
        feed_id: Feed identifier.
        base_url: Base URL of crawler service.

    Returns:
        dict: Crawl result.
    """
    try:
        logger.info(f"Crawling feed: {feed_id}")

        async with session.post(
            f"{base_url}/crawl/{feed_id}",
            timeout=aiohttp.ClientTimeout(total=60),
        ) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(
                    f"✓ {feed_id}: Crawled {result.get('articles_crawled', 0)} articles, "
                    f"published {result.get('articles_published', 0)}"
                )
                return {
                    "feed_id": feed_id,
                    "status": "success",
                    "result": result,
                }
            else:
                error_text = await response.text()
                logger.warning(f"✗ {feed_id}: HTTP {response.status} - {error_text}")
                return {
                    "feed_id": feed_id,
                    "status": "failed",
                    "error": f"HTTP {response.status}",
                }
    except asyncio.TimeoutError:
        logger.error(f"✗ {feed_id}: Timeout")
        return {
            "feed_id": feed_id,
            "status": "timeout",
            "error": "Request timeout",
        }
    except Exception as e:
        logger.error(f"✗ {feed_id}: {type(e).__name__}: {str(e)}")
        return {
            "feed_id": feed_id,
            "status": "error",
            "error": str(e),
        }


async def crawl_all_feeds(base_url: str = "http://localhost:8000") -> None:
    """
    Crawl all registered feeds.

    Args:
        base_url: Base URL of crawler service.
    """
    feed_ids = ["cnn", "bbc", "reuters", "aljazeera", "xinhua", "rt", "tasnim", "isna"]
    
    logger.info(f"Starting crawl of {len(feed_ids)} feeds...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [crawl_feed(session, feed_id, base_url) for feed_id in feed_ids]
        results = await asyncio.gather(*tasks)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("CRAWL SUMMARY")
    logger.info("="*80)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] != "success")
    
    total_articles = 0
    total_published = 0
    
    for result in results:
        if result["status"] == "success":
            articles = result["result"].get("articles_crawled", 0)
            published = result["result"].get("articles_published", 0)
            total_articles += articles
            total_published += published
            logger.info(
                f"  {result['feed_id']:12} - {articles:3} articles, {published:3} published"
            )
        else:
            logger.info(f"  {result['feed_id']:12} - FAILED: {result.get('error', 'Unknown error')}")
    
    logger.info("="*80)
    logger.info(f"Total: {success_count}/{len(feed_ids)} feeds successful")
    logger.info(f"Total articles crawled: {total_articles}")
    logger.info(f"Total articles published: {total_published}")
    logger.info("="*80)


async def main() -> None:
    """Main entry point."""
    logger.info("Testing crawler with all feeds from Task.md...")
    await crawl_all_feeds()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

