"""Entry point for NER Entity Linking Service."""

import logging
import sys
from src.config import get_config
from src.service import NEREntityLinkingService

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    try:
        config = get_config()
        logger.info(f"Starting {config.service_name} v{config.service_version}")
        logger.info(f"Environment: {config.environment}")

        service = NEREntityLinkingService()
        service.start()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

