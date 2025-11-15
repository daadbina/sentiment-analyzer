"""Main entry point for feature engineering service."""

import sys
import logging
import asyncio
from prometheus_client import start_http_server
from .service import FeatureEngineeringService
from .config import config
from .utils import StructuredLogger

logger = StructuredLogger(__name__)


def setup_logging():
    """Setup logging configuration."""
    log_level = getattr(logging, config.monitoring.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def async_main():
    """Async main entry point."""
    # Setup logging
    setup_logging()

    logger.info("Feature Engineering Service starting")
    logger.info(f"Configuration: {config}")

    # Start Prometheus metrics server
    metrics_port = config.monitoring.prometheus_port
    start_http_server(metrics_port)
    logger.info(f"Prometheus metrics server started on port {metrics_port}")

    # Create and start service
    service = FeatureEngineeringService()
    await service.start()


def main():
    """Main entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

