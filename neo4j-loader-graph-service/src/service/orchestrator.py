"""
Service orchestrator for Neo4j Loader Graph Service.
Manages service lifecycle and coordinates all components.
"""

import asyncio
import signal
import time
from typing import Optional
import structlog

from ..clients.neo4j_client import neo4j_client
from ..kafka.kafka_consumer import kafka_consumer
from ..schema.schema_manager import schema_manager
from ..loaders.stream_loader import stream_loader
from ..analytics.centrality import centrality_computer
from ..analytics.clustering import clustering_detector
from ..validation.graph_validator import graph_validator
from ..service.message_router import message_router
from ..config import config
from ..metrics import initialize_service_info

logger = structlog.get_logger(__name__)


class ServiceOrchestrator:
    """
    Orchestrates the Neo4j Loader Graph Service.
    """

    def __init__(self):
        """Initialize service orchestrator."""
        self.running = False
        self.analytics_task: Optional[asyncio.Task] = None
        self.flush_task: Optional[asyncio.Task] = None
        self.consumer_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """
        Start the service.
        """
        logger.info("service_starting", service="neo4j-loader-graph-service")
        
        try:
            # Initialize service info metrics
            initialize_service_info()
            
            # Connect to Neo4j
            logger.info("connecting_to_neo4j")
            neo4j_client.connect()
            
            # Initialize Neo4j schema
            logger.info("initializing_neo4j_schema")
            schema_manager.initialize_schema()
            
            # Connect to Kafka
            logger.info("connecting_to_kafka")
            kafka_consumer.connect()
            
            # Register message handler
            kafka_consumer.register_handler(message_router.route_message)
            
            # Set running flag
            self.running = True
            
            # Start background tasks
            self.flush_task = asyncio.create_task(self._flush_loop())
            self.analytics_task = asyncio.create_task(self._analytics_loop())
            self.consumer_task = asyncio.create_task(self._consumer_loop())
            
            logger.info("service_started", service="neo4j-loader-graph-service")
            
        except Exception as e:
            logger.error("service_start_failed", error=str(e))
            raise

    async def stop(self) -> None:
        """
        Stop the service.
        """
        logger.info("service_stopping", service="neo4j-loader-graph-service")
        
        try:
            # Set running flag to False
            self.running = False
            
            # Stop Kafka consumer
            logger.info("stopping_kafka_consumer")
            kafka_consumer.stop()
            
            # Cancel background tasks
            if self.consumer_task:
                self.consumer_task.cancel()
            if self.flush_task:
                self.flush_task.cancel()
            if self.analytics_task:
                self.analytics_task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(
                self.consumer_task,
                self.flush_task,
                self.analytics_task,
                return_exceptions=True,
            )
            
            # Flush remaining buffers
            logger.info("flushing_remaining_buffers")
            stream_loader.flush_all()
            
            # Close Kafka consumer
            logger.info("closing_kafka_consumer")
            kafka_consumer.close()
            
            # Close Neo4j client
            logger.info("closing_neo4j_client")
            neo4j_client.close()
            
            logger.info("service_stopped", service="neo4j-loader-graph-service")
            
        except Exception as e:
            logger.error("service_stop_failed", error=str(e))
            raise

    async def _consumer_loop(self) -> None:
        """
        Consumer loop for processing Kafka messages.
        """
        logger.info("consumer_loop_started")
        
        try:
            while self.running:
                # Consume messages (blocking with timeout)
                kafka_consumer.consume_messages(timeout=1.0)
                await asyncio.sleep(0.1)  # Small sleep to yield control
                
        except asyncio.CancelledError:
            logger.info("consumer_loop_cancelled")
        except Exception as e:
            logger.error("consumer_loop_error", error=str(e))
            raise

    async def _flush_loop(self) -> None:
        """
        Periodic flush loop for stream buffers.
        """
        logger.info("flush_loop_started", interval_seconds=config.stream_flush_interval)
        
        try:
            while self.running:
                await asyncio.sleep(config.stream_flush_interval)
                
                if stream_loader.should_flush():
                    logger.debug("flushing_stream_buffers")
                    stream_loader.flush_all()
                    
        except asyncio.CancelledError:
            logger.info("flush_loop_cancelled")
        except Exception as e:
            logger.error("flush_loop_error", error=str(e))
            raise

    async def _analytics_loop(self) -> None:
        """
        Periodic analytics loop for centrality and clustering.
        """
        logger.info(
            "analytics_loop_started",
            centrality_interval_hours=config.centrality_interval_hours,
            clustering_interval_hours=config.clustering_interval_hours,
        )
        
        last_centrality_time = time.time()
        last_clustering_time = time.time()
        
        try:
            while self.running:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = time.time()
                
                # Check if centrality computation is due
                centrality_interval_seconds = config.centrality_interval_hours * 3600
                if (current_time - last_centrality_time) >= centrality_interval_seconds:
                    logger.info("running_centrality_computation")
                    try:
                        # Compute centrality for all node types
                        for node_label in ["Article", "Group", "Entity", "Actor"]:
                            centrality_computer.compute_all_centrality_metrics(node_label)
                        last_centrality_time = current_time
                    except Exception as e:
                        logger.error("centrality_computation_failed", error=str(e))
                
                # Check if clustering detection is due
                clustering_interval_seconds = config.clustering_interval_hours * 3600
                if (current_time - last_clustering_time) >= clustering_interval_seconds:
                    logger.info("running_clustering_detection")
                    try:
                        # Detect clusters for all node types
                        for node_label in ["Article", "Group", "Entity", "Actor"]:
                            clustering_detector.detect_and_analyze_communities(node_label)
                        last_clustering_time = current_time
                    except Exception as e:
                        logger.error("clustering_detection_failed", error=str(e))
                        
        except asyncio.CancelledError:
            logger.info("analytics_loop_cancelled")
        except Exception as e:
            logger.error("analytics_loop_error", error=str(e))
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Health check status
        """
        health = {
            "service": "neo4j-loader-graph-service",
            "status": "healthy",
            "components": {},
        }
        
        # Check Neo4j connection
        try:
            neo4j_health = neo4j_client.health_check()
            health["components"]["neo4j"] = {
                "status": "healthy" if neo4j_health["connected"] else "unhealthy",
                "details": neo4j_health,
            }
        except Exception as e:
            health["components"]["neo4j"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health["status"] = "unhealthy"
        
        # Check Kafka consumer
        try:
            consumer_lag = kafka_consumer.get_consumer_lag()
            health["components"]["kafka"] = {
                "status": "healthy",
                "lag": consumer_lag,
            }
        except Exception as e:
            health["components"]["kafka"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health["status"] = "unhealthy"
        
        return health

    def run(self) -> None:
        """
        Run the service (blocking).
        """
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.stop())
            )
        
        try:
            # Start service
            loop.run_until_complete(self.start())
            
            # Run until stopped
            loop.run_forever()
            
        except KeyboardInterrupt:
            logger.info("keyboard_interrupt_received")
        finally:
            # Stop service
            loop.run_until_complete(self.stop())
            loop.close()


# Global service orchestrator instance
orchestrator = ServiceOrchestrator()

