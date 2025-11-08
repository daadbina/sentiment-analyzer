"""
Prometheus metrics server.

Exposes metrics on a dedicated port (9109) for Prometheus scraping.
"""

import logging
import asyncio
from typing import Optional
from aiohttp import web
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .metrics import REGISTRY


logger = logging.getLogger(__name__)


class MetricsServer:
    """
    Dedicated metrics server for Prometheus.
    
    Runs on a separate port (9109) to expose metrics for scraping.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 9109):
        """
        Initialize metrics server.
        
        Args:
            host: Host to bind to
            port: Port to bind to (default: 9109)
        """
        self.host = host
        self.port = port
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self._running = False
        
        logger.info(f"Metrics server initialized: host={host}, port={port}")
    
    async def metrics_handler(self, request: web.Request) -> web.Response:
        """
        Handle metrics requests.
        
        Args:
            request: HTTP request
        
        Returns:
            HTTP response with metrics in Prometheus format
        """
        try:
            # Generate metrics in Prometheus format
            metrics_data = generate_latest(REGISTRY)
            
            return web.Response(
                body=metrics_data,
                content_type=CONTENT_TYPE_LATEST,
            )
        except Exception as e:
            logger.error(f"Failed to generate metrics: {e}", exc_info=True)
            return web.Response(
                text=f"Error generating metrics: {e}",
                status=500,
            )
    
    async def health_handler(self, request: web.Request) -> web.Response:
        """
        Handle health check requests.
        
        Args:
            request: HTTP request
        
        Returns:
            HTTP response with health status
        """
        return web.Response(
            text="OK",
            status=200,
        )
    
    async def start(self) -> None:
        """
        Start the metrics server.
        
        Raises:
            RuntimeError: If server is already running
        """
        if self._running:
            raise RuntimeError("Metrics server is already running")
        
        try:
            # Create application
            self.app = web.Application()
            
            # Add routes
            self.app.router.add_get("/metrics", self.metrics_handler)
            self.app.router.add_get("/health", self.health_handler)
            
            # Create runner
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            # Create site
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            self._running = True
            
            logger.info(
                f"Metrics server started successfully on http://{self.host}:{self.port}"
            )
            logger.info(f"Metrics endpoint: http://{self.host}:{self.port}/metrics")
        
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}", exc_info=True)
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """
        Stop the metrics server.
        """
        if not self._running:
            logger.debug("Metrics server is not running")
            return
        
        try:
            logger.info("Stopping metrics server")
            
            # Stop site
            if self.site:
                await self.site.stop()
                self.site = None
            
            # Cleanup runner
            if self.runner:
                await self.runner.cleanup()
                self.runner = None
            
            self.app = None
            self._running = False
            
            logger.info("Metrics server stopped successfully")
        
        except Exception as e:
            logger.error(f"Error stopping metrics server: {e}", exc_info=True)
    
    def is_running(self) -> bool:
        """
        Check if the metrics server is running.
        
        Returns:
            True if running, False otherwise
        """
        return self._running


async def run_metrics_server(host: str = "0.0.0.0", port: int = 9109) -> None:
    """
    Run the metrics server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
    """
    server = MetricsServer(host=host, port=port)
    
    try:
        await server.start()
        
        # Keep server running
        while server.is_running():
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping metrics server")
    
    finally:
        await server.stop()


if __name__ == "__main__":
    # Run metrics server standalone
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    asyncio.run(run_metrics_server())

