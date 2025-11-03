"""
Main entry point for crawler service.

Starts the FastAPI application with Uvicorn.
"""

import logging
import sys
import uvicorn

from src.config import get_settings
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Main entry point.

    Starts the crawler service.
    """
    settings = get_settings()

    # Setup logging
    setup_logging(log_level=settings.log_level)

    logger.info(f"Starting {settings.app_name} v1.0.0")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")

    # Start Uvicorn server
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        workers=1,
        log_level=settings.log_level.lower(),
        access_log=True,
        reload=settings.environment == "development",
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

