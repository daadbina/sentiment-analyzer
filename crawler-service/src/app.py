"""
FastAPI application for crawler service.

Provides REST API endpoints for crawler management and monitoring.
"""

import logging
from typing import Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest

from .config import get_settings
from .crawler import CrawlerApplication
from .models import FeedSource
from .logging_config import setup_logging

logger = logging.getLogger(__name__)

# Global crawler instance
crawler_app: CrawlerApplication = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.

    Handles startup and shutdown events.
    """
    global crawler_app

    # Startup
    logger.info("Starting FastAPI application")
    setup_logging()

    crawler_app = CrawlerApplication()
    await crawler_app.start()

    # Load default feeds from Task.md if registry is empty
    if len(crawler_app.feed_registry.get_all_feeds()) == 0:
        logger.info("Loading default feeds from Task.md specifications...")
        _load_default_feeds(crawler_app)

        # Schedule all feeds after loading them
        logger.info("Scheduling feeds after loading default feeds...")
        await crawler_app._schedule_all_feeds()

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application")
    await crawler_app.stop()


def _load_default_feeds(crawler_app: "CrawlerApplication") -> None:
    """
    Load default feeds from Task.md specifications.

    Args:
        crawler_app: Crawler application instance.
    """
    from .models import FeedSource

    default_feeds = [
        # English sources
        FeedSource(
            feed_id="cnn",
            name="CNN",
            url="http://rss.cnn.com/rss/edition.rss",
            feed_type="rss",
            language="en",
            country="US",
            enabled=True,
            crawl_interval_minutes=30,
            timeout_seconds=15,
        ),
        FeedSource(
            feed_id="bbc",
            name="BBC News",
            url="https://feeds.bbci.co.uk/news/rss.xml",
            feed_type="rss",
            language="en",
            country="GB",
            enabled=True,
            crawl_interval_minutes=30,
            timeout_seconds=15,
        ),
        FeedSource(
            feed_id="reuters",
            name="Reuters",
            url="https://www.theguardian.com/world/rss",  # Using Guardian RSS as Reuters alternative (Reuters website has anti-bot protection)
            feed_type="rss",
            language="en",
            country="US",
            enabled=True,
            crawl_interval_minutes=30,
            timeout_seconds=15,
        ),
        FeedSource(
            feed_id="aljazeera",
            name="Al Jazeera",
            url="http://www.aljazeera.com/xml/rss/all.xml",
            feed_type="rss",
            language="en",
            country="QA",
            enabled=True,
            crawl_interval_minutes=30,
            timeout_seconds=15,
        ),
        # Chinese sources
        FeedSource(
            feed_id="xinhua",
            name="Xinhua News",
            url="http://www.xinhuanet.com/english/rss/worldrss.xml",
            feed_type="rss",
            language="zh",
            country="CN",
            enabled=True,
            crawl_interval_minutes=30,
            timeout_seconds=15,
        ),
        # Russian sources
        FeedSource(
            feed_id="rt",
            name="RT News",
            url="https://www.rt.com/rss/",
            feed_type="rss",
            language="ru",
            country="RU",
            enabled=True,
            crawl_interval_minutes=30,
            timeout_seconds=15,
        ),
        # Persian sources
        FeedSource(
            feed_id="tasnim",
            name="Tasnim News Agency",
            url="https://www.tasnimnews.com/en/rss/feed/0/0/0/0/AllStories",
            feed_type="rss",
            language="fa",
            country="IR",
            enabled=True,
            crawl_interval_minutes=30,
            timeout_seconds=15,
        ),
        FeedSource(
            feed_id="isna",
            name="ISNA News Agency",
            url="https://en.irna.ir/rss",  # Using IRNA RSS as ISNA alternative (ISNA website has complex structure)
            feed_type="rss",
            language="fa",
            country="IR",
            enabled=True,
            crawl_interval_minutes=30,
            timeout_seconds=15,
        ),
    ]

    for feed in default_feeds:
        try:
            crawler_app.feed_registry.add_feed(feed)
            logger.info(f"Loaded feed: {feed.feed_id}")

            # Log alternative feed sources
            if feed.feed_id == "reuters" and "theguardian.com" in feed.url:
                logger.info(f"NOTE: Reuters feed is using Guardian RSS as alternative source (Reuters website has anti-bot protection)")
            elif feed.feed_id == "isna" and "irna.ir" in feed.url:
                logger.info(f"NOTE: ISNA feed is using IRNA RSS as alternative source (ISNA website has complex structure)")
        except Exception as e:
            logger.warning(f"Failed to load feed {feed.feed_id}: {str(e)}")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title="Crawler Service",
    description="News crawler microservice for sentiment-analyzer-v2",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Health & Monitoring Endpoints
# ============================================================================


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Health status.
    """
    if not crawler_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    health = crawler_app.get_health_status()
    status_code = 200 if health["status"] == "healthy" else 503

    return JSONResponse(content=health, status_code=status_code)


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint.

    Returns:
        dict: Readiness status.
    """
    if not crawler_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    ready = crawler_app.health_manager.get_readiness()
    status_code = 200 if ready else 503

    return JSONResponse(
        content={"ready": ready},
        status_code=status_code,
    )


@app.get("/live", tags=["Health"])
async def liveness_check():
    """
    Liveness check endpoint.

    Returns:
        dict: Liveness status.
    """
    return JSONResponse(content={"alive": True})


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns:
        str: Prometheus metrics.
    """
    return generate_latest()


# ============================================================================
# Feed Management Endpoints
# ============================================================================


@app.post("/feeds", tags=["Feeds"])
async def add_feed(feed: FeedSource):
    """
    Add new feed to registry.

    Args:
        feed: Feed configuration.

    Returns:
        dict: Added feed.
    """
    if not crawler_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    try:
        crawler_app.feed_registry.add_feed(feed)
        return {"status": "success", "feed": feed.model_dump()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@app.get("/feeds", tags=["Feeds"])
async def list_feeds():
    """
    List all feeds.

    Returns:
        dict: List of feeds.
    """
    if not crawler_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    feeds = crawler_app.feed_registry.get_all_feeds()
    return {
        "total": len(feeds),
        "feeds": [feed.model_dump() for feed in feeds],
    }


@app.get("/feeds/{feed_id}", tags=["Feeds"])
async def get_feed(feed_id: str):
    """
    Get feed by ID.

    Args:
        feed_id: Feed identifier.

    Returns:
        dict: Feed configuration.
    """
    if not crawler_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    feed = crawler_app.feed_registry.get_feed(feed_id)
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )

    return feed.model_dump()


@app.delete("/feeds/{feed_id}", tags=["Feeds"])
async def delete_feed(feed_id: str):
    """
    Delete feed.

    Args:
        feed_id: Feed identifier.

    Returns:
        dict: Status.
    """
    if not crawler_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    try:
        crawler_app.feed_registry.remove_feed(feed_id)
        return {"status": "success", "message": f"Feed {feed_id} deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ============================================================================
# Crawl Endpoints
# ============================================================================


@app.post("/crawl/training-data", tags=["Crawling"])
async def crawl_training_data(
    categories: Optional[List[str]] = None,
    sentiments: Optional[List[str]] = None,
    max_datasets: Optional[int] = None,
):
    """
    Fetch training data from GitHub repository and produce to Kafka.

    This endpoint downloads labeled news articles from the Webhose free-news-datasets
    repository and produces them to the news_raw topic with is_training_data flag.

    Args:
        categories: List of categories to fetch (None = all available).
        sentiments: List of sentiments to fetch (None = both positive and negative).
        max_datasets: Maximum number of datasets to fetch (None = all).

    Returns:
        dict: Training data fetch job result.

    Example:
        POST /crawl/training-data
        {
            "categories": ["War, Conflict and Unrest", "Politics"],
            "sentiments": ["positive", "negative"],
            "max_datasets": 5
        }
    """
    if not crawler_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    try:
        job = await crawler_app.crawl_training_data(
            categories=categories,
            sentiments=sentiments,
            max_datasets=max_datasets,
        )
        return job.model_dump()
    except Exception as e:
        logger.error(f"Training data fetch failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.post("/crawl/{feed_id}", tags=["Crawling"])
async def crawl_feed(feed_id: str):
    """
    Manually trigger crawl for feed.

    Args:
        feed_id: Feed identifier.

    Returns:
        dict: Crawl job result.
    """
    if not crawler_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    feed = crawler_app.feed_registry.get_feed(feed_id)
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )

    try:
        job = await crawler_app.crawl_feed(feed)
        return job.model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.post("/crawl", tags=["Crawling"])
async def crawl_all():
    """
    Manually trigger crawl for all feeds.

    Returns:
        dict: List of crawl jobs.
    """
    if not crawler_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    try:
        jobs = await crawler_app.crawl_all_feeds()
        return {
            "total": len(jobs),
            "jobs": [job.model_dump() for job in jobs],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Info Endpoints
# ============================================================================


@app.get("/info", tags=["Info"])
async def info():
    """
    Get service information.

    Returns:
        dict: Service info.
    """
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
    }
