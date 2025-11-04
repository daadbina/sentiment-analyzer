"""Main entry point for embedding service."""

import logging
import asyncio
import signal
import sys
from typing import Optional

from src.service import EmbeddingService
from src.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages service lifecycle."""

    def __init__(self):
        """Initialize service manager."""
        self.service: Optional[EmbeddingService] = None
        self.task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the service."""
        try:
            logger.info("Starting embedding service...")
            self.service = EmbeddingService()
            self.task = asyncio.create_task(self.service.run())
            await self.task
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            raise

    def stop(self) -> None:
        """Stop the service."""
        if self.service:
            self.service.stop()

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        loop = asyncio.get_event_loop()

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Wait for task to complete
        if self.task:
            try:
                await self.task
            except asyncio.CancelledError:
                logger.info("Service task cancelled")


async def main() -> None:
    """Main entry point."""
    try:
        logger.info("=" * 80)
        logger.info("Embedding Service Starting")
        logger.info("=" * 80)

        # Log configuration
        logger.info(f"Kafka brokers: {config.kafka.brokers}")
        logger.info(f"Kafka input topic: {config.kafka.input_topic}")
        logger.info(f"Kafka output topic: {config.kafka.output_topic}")
        logger.info(f"Qdrant host: {config.qdrant.host}:{config.qdrant.port}")
        logger.info(f"PostgreSQL host: {config.postgres.host}:{config.postgres.port}")
        logger.info(f"Model device: {config.model.device}")
        logger.info(f"Batch size (GPU): {config.model.batch_size_gpu}")
        logger.info(f"Batch size (CPU): {config.model.batch_size_cpu}")

        manager = ServiceManager()
        await manager.start()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

