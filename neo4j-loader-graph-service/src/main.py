"""
Main entry point for Neo4j Loader Graph Service.
"""

import sys
import structlog

from .service.orchestrator import orchestrator
from .config import config

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def main() -> int:
    """
    Main entry point.
    
    Returns:
        Exit code
    """
    try:
        logger.info(
            "neo4j_loader_graph_service_starting",
            version="1.0.0",
            neo4j_uri=config.neo4j_uri,
            kafka_bootstrap_servers=config.kafka_bootstrap_servers,
        )
        
        # Run service
        orchestrator.run()
        
        return 0
        
    except Exception as e:
        logger.error("service_failed", error=str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

