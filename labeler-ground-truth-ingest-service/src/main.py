"""Main entry point for labeler-ground-truth-ingest-service."""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import config
from src.service import LabelerService
from src.utils.trace import get_logger


logger = get_logger(__name__, config.logging.log_level)


async def main():
    """Main entry point."""
    logger.info(
        f"Starting {config.service.service_name} v{config.service.service_version}",
        operation="main",
        environment=config.service.environment
    )

    service = LabelerService()

    try:
        # Start service
        await service.start()

        # Run service
        await service.run()

    except KeyboardInterrupt:
        logger.info(
            "Received keyboard interrupt",
            operation="main"
        )

    except Exception as e:
        logger.error(
            f"Fatal error: {str(e)}",
            operation="main",
            error_type=type(e).__name__
        )
        sys.exit(1)

    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

