"""
Test script for Feast HTTP client.

Run this to verify connectivity to the remote Feast server.
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime
from feast_http_client import FeastHTTPClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_health_check(client: FeastHTTPClient):
    """Test Feast server health check."""
    logger.info("=" * 60)
    logger.info("TEST 1: Health Check")
    logger.info("=" * 60)
    
    is_healthy = await client.health_check()
    if is_healthy:
        logger.info("✓ Feast server is healthy")
    else:
        logger.error("✗ Feast server health check failed")
    
    return is_healthy


async def test_get_feature_view_info(client: FeastHTTPClient):
    """Test getting feature view information."""
    logger.info("=" * 60)
    logger.info("TEST 2: Get Feature View Info")
    logger.info("=" * 60)
    
    try:
        info = await client.get_feature_view_info("semantic_group_features")
        if info:
            logger.info(f"✓ Feature view info retrieved: {info}")
        else:
            logger.warning("✗ Feature view not found (may need to apply features.py first)")
    except Exception as e:
        logger.error(f"✗ Failed to get feature view info: {e}")


async def test_push_features(client: FeastHTTPClient):
    """Test pushing features to online store."""
    logger.info("=" * 60)
    logger.info("TEST 3: Push Features")
    logger.info("=" * 60)
    
    # Create sample feature data
    sample_data = pd.DataFrame({
        "group_id": ["test-group-1", "test-group-2"],
        "event_timestamp": [datetime.now(), datetime.now()],
        "sentiment_mean": [0.5, -0.3],
        "sentiment_std": [0.2, 0.15],
        "entity_count": [10, 15],
        "btc_change_pct_10h": [2.5, -1.2],
    })
    
    try:
        result = await client.push_features(
            push_source_name="semantic_group_push",
            df=sample_data,
            to="online"
        )
        logger.info(f"✓ Features pushed successfully: {result}")
    except Exception as e:
        logger.error(f"✗ Failed to push features: {e}")


async def test_get_online_features(client: FeastHTTPClient):
    """Test retrieving online features."""
    logger.info("=" * 60)
    logger.info("TEST 4: Get Online Features")
    logger.info("=" * 60)
    
    feature_refs = [
        "semantic_group_features:sentiment_mean",
        "semantic_group_features:sentiment_std",
        "semantic_group_features:entity_count",
        "semantic_group_features:btc_change_pct_10h",
    ]
    
    entity_rows = [
        {"group_id": "test-group-1"},
        {"group_id": "test-group-2"},
    ]
    
    try:
        df = await client.get_online_features(
            feature_refs=feature_refs,
            entity_rows=entity_rows
        )
        logger.info(f"✓ Retrieved features:")
        logger.info(f"\n{df}")
    except Exception as e:
        logger.error(f"✗ Failed to get online features: {e}")


async def main():
    """Run all tests."""
    logger.info("Starting Feast HTTP Client Tests")
    logger.info(f"Target server: http://154.53.166.231:6566")
    logger.info("")
    
    # Initialize client
    client = FeastHTTPClient(feature_server_url="http://154.53.166.231:6566")
    
    # Run tests
    await test_health_check(client)
    await test_get_feature_view_info(client)
    await test_push_features(client)
    await test_get_online_features(client)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("All tests completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

