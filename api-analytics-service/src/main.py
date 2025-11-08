"""Main entry point for API Analytics Service."""

import uvicorn
import logging
import signal
import sys

from src.config import config
from src.app import app
from src.utils.logging import get_logger

logger = get_logger(__name__)


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {sig}, shutting down...")
    sys.exit(0)


def main():
    """Run the API Analytics Service."""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Starting API Analytics Service")
    logger.info(
        f"Configuration: {config.api.host}:{config.api.port}",
        extra={
            "extra_fields": {
                "host": config.api.host,
                "port": config.api.port,
                "workers": config.api.workers,
            }
        },
    )

    # Run uvicorn server
    uvicorn.run(
        "src.app:app",
        host=config.api.host,
        port=config.api.port,
        workers=config.api.workers,
        log_level=config.api.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()

