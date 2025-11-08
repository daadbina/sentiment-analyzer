"""
Main entry point for the predictor-online-inference-service.

Starts the FastAPI application with Uvicorn and handles graceful shutdown.
"""

import argparse
import asyncio
import logging
import signal
import sys

import uvicorn

from .config import get_config
from .metrics_server import MetricsServer
from .service import PredictorService
from .utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

# Global service instance for signal handling
_service: PredictorService | None = None
_metrics_server: MetricsServer | None = None


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Predictor Online Inference Service"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to (overrides config)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (overrides config)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes (overrides config)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level (overrides config)"
    )
    parser.add_argument(
        "--skip-startup-checks",
        action="store_true",
        help="Skip startup health checks"
    )

    return parser.parse_args()


async def perform_startup_checks(config) -> bool:
    """
    Perform startup health checks.

    Args:
        config: Service configuration

    Returns:
        True if all checks pass, False otherwise
    """
    logger.info("Performing startup health checks")

    try:
        # Import clients here to avoid circular imports
        from .clients import (
            FeastClient,
            KafkaProducerClient,
            MLflowModelClient,
            PostgresClient,
            RedisClient,
        )

        # Check MLflow connectivity
        logger.info("Checking MLflow connectivity")
        try:
            MLflowModelClient(config.mlflow)
            # Try to list models to verify connectivity
            logger.info("✓ MLflow connectivity verified")
        except Exception as e:
            logger.error(f"✗ MLflow connectivity check failed: {e}")
            return False

        # Check Feast repository
        logger.info("Checking Feast repository")
        try:
            feast_client = FeastClient(config.feast)
            await feast_client.connect()
            await feast_client.disconnect()
            logger.info("✓ Feast repository validated")
        except Exception as e:
            logger.error(f"✗ Feast repository check failed: {e}")
            return False

        # Check Redis health
        logger.info("Checking Redis health")
        try:
            redis_client = RedisClient(config.redis)
            await redis_client.connect()
            await redis_client.ping()
            await redis_client.disconnect()
            logger.info("✓ Redis health check passed")
        except Exception as e:
            logger.error(f"✗ Redis health check failed: {e}")
            return False

        # Check PostgreSQL schema
        logger.info("Checking PostgreSQL schema")
        try:
            postgres_client = PostgresClient(config.postgres)
            await postgres_client.connect()
            # Verify predictions table exists
            await postgres_client.execute_query(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'predictions')"
            )
            await postgres_client.disconnect()
            logger.info("✓ PostgreSQL schema validated")
        except Exception as e:
            logger.error(f"✗ PostgreSQL schema check failed: {e}")
            return False

        # Check Kafka topic availability
        logger.info("Checking Kafka topic availability")
        try:
            kafka_producer = KafkaProducerClient(config.kafka)
            await kafka_producer.connect()
            await kafka_producer.close()
            logger.info("✓ Kafka topics verified")
        except Exception as e:
            logger.error(f"✗ Kafka topic check failed: {e}")
            return False

        logger.info("All startup checks passed ✓")
        return True

    except Exception as e:
        logger.error(f"Startup checks failed: {e}", exc_info=True)
        return False


def handle_signal(signum, frame):
    """
    Handle termination signals for graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global _service, _metrics_server

    signal_name = signal.Signals(signum).name
    logger.info(f"Received signal {signal_name}, initiating graceful shutdown")

    # Create event loop if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Stop metrics server
    if _metrics_server and _metrics_server.is_running():
        loop.run_until_complete(_metrics_server.stop())
        logger.info("Metrics server stopped gracefully")

    # Stop service
    if _service and _service.is_running():
        loop.run_until_complete(_service.stop())
        logger.info("Service stopped gracefully")

    sys.exit(0)


async def start_metrics_server(config) -> MetricsServer:
    """
    Start the metrics server in the background.

    Args:
        config: Service configuration

    Returns:
        MetricsServer instance
    """
    metrics_server = MetricsServer(
        host=config.monitoring.prometheus_host,
        port=config.monitoring.prometheus_port,
    )
    await metrics_server.start()
    return metrics_server


def main() -> None:
    """
    Main entry point.

    Starts the FastAPI application with Uvicorn and metrics server.
    """
    global _service, _metrics_server

    try:
        # Parse command-line arguments
        args = parse_args()

        # Load configuration
        config = get_config()

        # Override config with command-line arguments
        if args.host:
            config.api.host = args.host
        if args.port:
            config.api.port = args.port
        if args.workers:
            config.api.workers = args.workers
        if args.log_level:
            config.monitoring.log_level = args.log_level

        # Setup logging
        setup_logging(config.monitoring.log_level)

        # Validate configuration
        config.validate()

        logger.info(
            f"Starting service: host={config.api.host}, port={config.api.port}, "
            f"workers={config.api.workers}, log_level={config.monitoring.log_level}"
        )

        # Perform startup checks
        if not args.skip_startup_checks:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            checks_passed = loop.run_until_complete(perform_startup_checks(config))

            # Start metrics server
            logger.info("Starting metrics server")
            _metrics_server = loop.run_until_complete(start_metrics_server(config))

            loop.close()

            if not checks_passed:
                logger.error("Startup checks failed, exiting")
                sys.exit(1)
        else:
            logger.warning("Skipping startup checks (--skip-startup-checks flag set)")

            # Start metrics server
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("Starting metrics server")
            _metrics_server = loop.run_until_complete(start_metrics_server(config))
            loop.close()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        logger.info("Signal handlers registered for graceful shutdown")

        # Start Uvicorn server
        uvicorn.run(
            "src.app:app",
            host=config.api.host,
            port=config.api.port,
            workers=config.api.workers,
            log_level=config.monitoring.log_level.lower(),
            access_log=True,
            reload=False,
        )

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")

        # Create event loop if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Stop metrics server
        if _metrics_server and _metrics_server.is_running():
            loop.run_until_complete(_metrics_server.stop())

        # Stop service
        if _service and _service.is_running():
            loop.run_until_complete(_service.stop())

        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start service: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

