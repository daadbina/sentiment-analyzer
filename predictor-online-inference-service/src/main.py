"""
Main entry point for the predictor-online-inference-service.

Starts the FastAPI application with Uvicorn.
"""

import logging
import sys

import uvicorn

from .config import get_config


logger = logging.getLogger(__name__)


def main() -> None:
    """
    Main entry point.
    
    Starts the FastAPI application with Uvicorn.
    """
    try:
        # Load configuration
        config = get_config()
        
        # Validate configuration
        config.validate()
        
        logger.info(
            f"Starting service: host={config.api.host}, port={config.api.port}, "
            f"workers={config.api.workers}"
        )
        
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
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

