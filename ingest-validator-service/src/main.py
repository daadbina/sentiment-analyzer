"""Main entry point for validator service."""

import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file BEFORE importing config
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

import uvicorn
from src.config import get_config
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    try:
        config = get_config()

        # Setup logging
        setup_logging(log_level=config.log_level)

        logger.info(f"Starting Ingest Validator Service v{config.service_version}")
        logger.info(f"Environment: {config.environment}")

        # Start Uvicorn server
        uvicorn.run(
            "src.app:app",
            host="127.0.0.1",
            port=config.api_port,
            workers=1,
            log_level=config.log_level.lower(),
            access_log=True,
            reload=False,
        )

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
